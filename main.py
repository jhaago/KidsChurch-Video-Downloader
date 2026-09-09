import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME = "YouTube Downloader"
APP_VERSION = "0.5.0"

RESOLUTION_FORMATS = {
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
}

OUTPUT_FORMATS = ("MP4 Video", "MP3 Audio", "WAV Audio")
MEDIA_EXTENSIONS = {
    ".mkv", ".mp4", ".webm", ".mov", ".m4v",
    ".m4a", ".aac", ".opus", ".ogg", ".mp3", ".wav"
}
FINISHED_STATES = {"Complete", "Failed", "Cancelled"}


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def settings_file() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    # Keep the existing settings folder so V0.3 preferences survive the rename.
    folder = base / "KidsChurchVideoDownloader"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "settings.json"


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name or "media"


def find_tool(name: str):
    suffix = ".exe" if os.name == "nt" else ""
    filename = f"{name}{suffix}"
    for candidate in (app_dir() / filename, app_dir() / "tools" / filename):
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def tool_environment():
    env = os.environ.copy()
    extra = [str(app_dir()), str(app_dir() / "tools")]
    env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def no_window_flags():
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def duration_text(seconds):
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return "Unknown"
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def short_url(url):
    clean = url.strip()
    return clean if len(clean) <= 72 else clean[:69] + "..."


class DownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("960x800")
        self.root.minsize(840, 720)

        self.events = queue.Queue()
        self.preview_worker = None
        self.queue_worker = None
        self.active_process = None
        self.operation_cancel_requested = False

        self.jobs = []
        self.jobs_lock = threading.Lock()
        self.job_counter = 0
        self.current_job_id = None

        self.preview_info = None
        self.preview_url = None

        settings = self._load_settings()

        self.url_var = tk.StringVar()
        self.res_var = tk.StringVar(value=settings.get("resolution", "1080p"))
        if self.res_var.get() not in RESOLUTION_FORMATS:
            self.res_var.set("1080p")

        saved_output_format = settings.get("output_format", "MP4 Video")
        if saved_output_format not in OUTPUT_FORMATS:
            saved_output_format = "MP4 Video"
        self.output_format_var = tk.StringVar(value=saved_output_format)

        default_folder = settings.get("save_folder") or str(Path.home() / "Videos")
        self.folder_var = tk.StringVar(value=default_folder)

        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.preview_title_var = tk.StringVar(value="No video preview loaded.")
        self.preview_detail_var = tk.StringVar(value="")
        self.tools_var = tk.StringVar(value="Checking bundled tools…")

        self._build_ui()
        self._refresh_tool_status()
        self._apply_output_format_state()
        self._refresh_controls()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._process_events)

    def _load_settings(self):
        try:
            return json.loads(settings_file().read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_settings(self):
        data = {
            "save_folder": self.folder_var.get().strip(),
            "resolution": self.res_var.get(),
            "output_format": self.output_format_var.get(),
        }
        try:
            settings_file().write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text=APP_NAME,
            font=("Segoe UI", 21, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            outer,
            text=(
                "Paste YouTube links and add them to the queue. Download as a "
                "PowerPoint-friendly MP4 video, high-quality MP3 audio, or uncompressed WAV audio."
            ),
            wraplength=900,
        ).pack(anchor="w", pady=(4, 16))

        url_frame = ttk.Frame(outer)
        url_frame.pack(fill="x")
        ttk.Label(url_frame, text="YouTube URL").grid(row=0, column=0, columnspan=3, sticky="w")
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        self.preview_btn = ttk.Button(url_frame, text="Preview", command=self._start_preview)
        self.preview_btn.grid(row=1, column=1, padx=(8, 0), pady=(4, 10))
        self.add_queue_btn = ttk.Button(url_frame, text="Add to Queue", command=self._queue_current_url)
        self.add_queue_btn.grid(row=1, column=2, padx=(8, 0), pady=(4, 10))
        url_frame.columnconfigure(0, weight=1)
        self.url_entry.focus_set()
        self.url_entry.bind("<Return>", lambda _event: self._queue_current_url())

        preview = ttk.LabelFrame(outer, text="Media preview")
        preview.pack(fill="x", pady=(0, 12))
        ttk.Label(
            preview,
            textvariable=self.preview_title_var,
            font=("Segoe UI", 11, "bold"),
            wraplength=880,
        ).pack(anchor="w", padx=10, pady=(7, 2))
        ttk.Label(
            preview,
            textvariable=self.preview_detail_var,
            wraplength=880,
        ).pack(anchor="w", padx=10, pady=(0, 7))

        options = ttk.Frame(outer)
        options.pack(fill="x")

        ttk.Label(options, text="Output format").grid(row=0, column=0, sticky="w")
        ttk.Label(options, text="Maximum resolution").grid(row=0, column=1, sticky="w", padx=(18, 0))
        ttk.Label(options, text="Save folder").grid(row=0, column=2, sticky="w", padx=(18, 0))

        self.output_format_combo = ttk.Combobox(
            options,
            textvariable=self.output_format_var,
            values=OUTPUT_FORMATS,
            state="readonly",
            width=15,
        )
        self.output_format_combo.grid(row=1, column=0, sticky="w", pady=(4, 10))
        self.output_format_combo.bind("<<ComboboxSelected>>", self._on_output_format_changed)

        self.res_combo = ttk.Combobox(
            options,
            textvariable=self.res_var,
            values=list(RESOLUTION_FORMATS.keys()),
            state="readonly",
            width=12,
        )
        self.res_combo.grid(row=1, column=1, sticky="w", padx=(18, 0), pady=(4, 10))

        folder_row = ttk.Frame(options)
        folder_row.grid(row=1, column=2, sticky="ew", padx=(18, 0), pady=(4, 10))
        ttk.Entry(folder_row, textvariable=self.folder_var).pack(side="left", fill="x", expand=True)
        ttk.Button(folder_row, text="Browse…", command=self._browse).pack(side="left", padx=(8, 0))
        options.columnconfigure(2, weight=1)

        queue_frame = ttk.LabelFrame(outer, text="Download queue")
        queue_frame.pack(fill="both", expand=True, pady=(2, 12))

        queue_table = ttk.Frame(queue_frame)
        queue_table.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        self.queue_tree = ttk.Treeview(
            queue_table,
            columns=("title", "format", "quality", "status"),
            show="headings",
            height=7,
            selectmode="extended",
        )
        self.queue_tree.heading("title", text="Media")
        self.queue_tree.heading("format", text="Format")
        self.queue_tree.heading("quality", text="Quality")
        self.queue_tree.heading("status", text="Status")
        self.queue_tree.column("title", width=500, minwidth=260, stretch=True)
        self.queue_tree.column("format", width=105, minwidth=90, stretch=False, anchor="center")
        self.queue_tree.column("quality", width=85, minwidth=70, stretch=False, anchor="center")
        self.queue_tree.column("status", width=125, minwidth=105, stretch=False, anchor="center")

        scrollbar = ttk.Scrollbar(queue_table, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=scrollbar.set)
        self.queue_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        queue_buttons = ttk.Frame(queue_frame)
        queue_buttons.pack(fill="x", padx=8, pady=(0, 8))
        self.cancel_btn = ttk.Button(queue_buttons, text="Cancel Current", command=self._cancel_current)
        self.cancel_btn.pack(side="left")
        ttk.Button(queue_buttons, text="Remove Selected", command=self._remove_selected).pack(side="left", padx=(8, 0))
        ttk.Button(queue_buttons, text="Clear Finished", command=self._clear_finished).pack(side="left", padx=(8, 0))
        ttk.Button(queue_buttons, text="Open Save Folder", command=self._open_folder).pack(side="right")

        ttk.Progressbar(
            outer,
            variable=self.progress_var,
            maximum=100,
        ).pack(fill="x", pady=(2, 5))
        ttk.Label(outer, textvariable=self.status_var).pack(anchor="w")

        activity = ttk.LabelFrame(outer, text="Activity")
        activity.pack(fill="both", expand=True, pady=(10, 0))
        self.log = tk.Text(activity, height=7, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=8, pady=8)

        legal = ttk.Label(
            outer,
            text=(
                "Use only for videos/audio you own or are authorised to download. "
                "The app does not attempt to bypass DRM or protected streaming restrictions."
            ),
            wraplength=900,
        )
        legal.pack(anchor="w", pady=(8, 0))

        ttk.Label(
            outer,
            textvariable=self.tools_var,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(5, 0))

    def _refresh_tool_status(self):
        states = []
        for label, executable in (("yt-dlp", "yt-dlp"), ("FFmpeg", "ffmpeg"), ("Deno", "deno")):
            states.append(f"{label}: {'OK' if find_tool(executable) else 'missing'}")
        self.tools_var.set("  |  ".join(states))

    def _required_tools(self):
        tools = {
            "yt-dlp": find_tool("yt-dlp"),
            "ffmpeg": find_tool("ffmpeg"),
            "deno": find_tool("deno"),
        }
        missing = [name for name, path in tools.items() if not path]
        if missing:
            messagebox.showerror(
                "Required tools missing",
                "This build is missing: "
                + ", ".join(missing)
                + ".\n\nUse the packaged Windows build, or run prepare_tools.ps1 when developing from source.",
            )
            return None
        return tools

    def _preview_busy(self):
        return bool(self.preview_worker and self.preview_worker.is_alive())

    def _queue_busy(self):
        return bool(self.queue_worker and self.queue_worker.is_alive())

    def _on_output_format_changed(self, _event=None):
        self._apply_output_format_state()
        self._save_settings()

    def _apply_output_format_state(self):
        if self.output_format_var.get() == "MP4 Video":
            self.res_combo.configure(state="readonly")
        else:
            self.res_combo.configure(state="disabled")

    def _refresh_controls(self):
        preview_busy = self._preview_busy()
        queue_busy = self._queue_busy()

        self.preview_btn.configure(state="disabled" if preview_busy or queue_busy else "normal")
        self.add_queue_btn.configure(state="disabled" if preview_busy else "normal")
        self.cancel_btn.configure(
            state="normal" if preview_busy or self.current_job_id is not None else "disabled"
        )

    def _browse(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get() or str(Path.home()))
        if folder:
            self.folder_var.set(folder)
            self._save_settings()

    def _open_folder(self):
        folder = Path(self.folder_var.get()).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as exc:
            messagebox.showerror("Open folder", str(exc))

    def _append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _start_preview(self):
        if self._preview_busy() or self._queue_busy():
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("YouTube URL", "Paste a YouTube URL first.")
            return

        tools = self._required_tools()
        if not tools:
            return

        self.operation_cancel_requested = False
        self.progress_var.set(0)
        self.preview_title_var.set("Loading preview…")
        self.preview_detail_var.set("")
        self.status_var.set("Loading video information…")

        self.preview_worker = threading.Thread(
            target=self._preview_worker,
            args=(url, tools),
            daemon=True,
        )
        self.preview_worker.start()
        self._refresh_controls()

    def _preview_worker(self, url, tools):
        try:
            info = self._fetch_metadata(url, tools)
            self.events.put(("preview", url, info))
        except Exception as exc:
            self.events.put(("preview_error", str(exc)))

    def _fetch_metadata(self, url, tools):
        cmd = [
            tools["yt-dlp"],
            "--no-playlist",
            "--skip-download",
            "--dump-single-json",
            "--no-warnings",
            url,
        ]
        proc = self._start_process(cmd, capture_stderr=True)
        stdout, stderr = proc.communicate()
        self.active_process = None

        if self.operation_cancel_requested:
            raise RuntimeError("Operation cancelled by user.")
        if proc.returncode != 0:
            detail = (stderr or stdout or "").strip()
            raise RuntimeError(detail or "Could not read video information.")

        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("The video information returned by yt-dlp could not be read.") from exc

    def _queue_current_url(self):
        if self._preview_busy():
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("YouTube URL", "Paste a YouTube URL first.")
            return

        tools = self._required_tools()
        if not tools:
            return

        output_dir = Path(self.folder_var.get()).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Save folder", f"Could not use that folder:\n{exc}")
            return

        self._save_settings()
        cached_info = self.preview_info if self.preview_url == url else None
        display_title = (
            cached_info.get("title")
            if cached_info and cached_info.get("title")
            else short_url(url)
        )

        output_format = self.output_format_var.get()
        if output_format == "MP4 Video":
            quality = self.res_var.get()
        elif output_format == "MP3 Audio":
            quality = "320 kbps"
        else:
            quality = "PCM"

        self.job_counter += 1
        job = {
            "id": self.job_counter,
            "url": url,
            "resolution": self.res_var.get(),
            "output_format": output_format,
            "output_dir": output_dir,
            "title": display_title,
            "status": "Queued",
            "info": cached_info,
        }

        with self.jobs_lock:
            self.jobs.append(job)

        self.queue_tree.insert(
            "",
            "end",
            iid=str(job["id"]),
            values=(job["title"], output_format.replace(" Video", "").replace(" Audio", ""), quality, job["status"]),
        )

        self._append_log(f"Queued {output_format}: {display_title}")
        self.url_var.set("")
        self.preview_info = None
        self.preview_url = None
        self.preview_title_var.set("No video preview loaded.")
        self.preview_detail_var.set("")
        self.url_entry.focus_set()

        self._ensure_queue_worker(tools)
        self._refresh_controls()

    def _ensure_queue_worker(self, tools=None):
        if self._queue_busy():
            return

        with self.jobs_lock:
            has_queued = any(job["status"] == "Queued" for job in self.jobs)

        if not has_queued:
            return

        tools = tools or self._required_tools()
        if not tools:
            return

        self.queue_worker = threading.Thread(
            target=self._queue_runner,
            args=(tools,),
            daemon=True,
        )
        self.queue_worker.start()
        self._refresh_controls()

    def _claim_next_job(self):
        with self.jobs_lock:
            for job in self.jobs:
                if job["status"] == "Queued":
                    job["status"] = "Running"
                    return job
        return None

    def _set_job_status(self, job_id, status):
        with self.jobs_lock:
            for job in self.jobs:
                if job["id"] == job_id:
                    job["status"] = status
                    break

    def _queue_runner(self, tools):
        while True:
            job = self._claim_next_job()
            if job is None:
                break

            self.current_job_id = job["id"]
            self.operation_cancel_requested = False
            self.events.put(("job_status", job["id"], "Running"))
            self.events.put(("log", f"Starting {job['output_format']}: {job['url']}"))

            try:
                output = self._download_job(job, tools)
                self._set_job_status(job["id"], "Complete")
                self.events.put(("job_done", job["id"], output))
            except Exception as exc:
                cancelled = self.operation_cancel_requested or "cancelled" in str(exc).lower()
                state = "Cancelled" if cancelled else "Failed"
                self._set_job_status(job["id"], state)
                self.events.put(("job_error", job["id"], state, str(exc)))
            finally:
                self.active_process = None
                self.current_job_id = None
                self.operation_cancel_requested = False

        self.events.put(("queue_idle",))

    def _download_job(self, job, tools):
        temp_dir = Path(tempfile.mkdtemp(prefix="youtube_downloader_"))
        title = None
        info = job.get("info")
        is_wav = job["output_format"] == "WAV Audio"
        is_mp3 = job["output_format"] == "MP3 Audio"
        is_audio = is_wav or is_mp3

        try:
            if info is None:
                try:
                    info = self._fetch_metadata(job["url"], tools)
                    self.events.put(("job_metadata", job["id"], info))
                except Exception as exc:
                    if self.operation_cancel_requested:
                        raise
                    self.events.put(("log", f"Preview information unavailable: {exc}"))

            if info:
                title = safe_filename(info.get("title") or "media")
                self.events.put(("job_title", job["id"], info.get("title") or title))

            if is_audio:
                audio_label = "MP3" if is_mp3 else "WAV"
                self.events.put(("job_progress", job["id"], 0, f"Downloading best available audio for {audio_label}…"))
                format_expression = "bestaudio/best"
            else:
                self.events.put(("job_progress", job["id"], 0, "Downloading video and audio…"))
                format_expression = RESOLUTION_FORMATS.get(
                    job["resolution"], RESOLUTION_FORMATS["1080p"]
                )

            progress_template = (
                "download:KC_PROGRESS|%(progress._percent_str)s|"
                "%(progress._speed_str)s|%(progress._eta_str)s"
            )
            cmd = [
                tools["yt-dlp"],
                "--no-playlist",
                "--windows-filenames",
                "--newline",
                "--progress",
                "--progress-template",
                progress_template,
                "--ffmpeg-location",
                str(Path(tools["ffmpeg"]).parent),
                "--format",
                format_expression,
                "--output",
                str(temp_dir / "%(title).180B [%(id)s].%(ext)s"),
                "--print",
                "before_dl:KC_TITLE|%(title)s",
                "--print",
                "after_move:KC_FILE|%(filepath)s",
            ]

            if not is_audio:
                cmd.extend(["--merge-output-format", "mkv"])

            cmd.append(job["url"])

            proc = self._start_process(cmd, capture_stderr=False)
            downloaded_path = None

            for raw_line in proc.stdout:
                if self.operation_cancel_requested:
                    self._terminate_active_process()
                    raise RuntimeError("Operation cancelled by user.")

                line = raw_line.strip()
                if not line:
                    continue

                if line.startswith("KC_PROGRESS|"):
                    parts = line.split("|", 3)
                    pct = 0.0
                    if len(parts) > 1:
                        try:
                            pct = float(parts[1].replace("%", "").strip())
                        except ValueError:
                            pct = 0.0
                    speed = parts[2].strip() if len(parts) > 2 else ""
                    eta = parts[3].strip() if len(parts) > 3 else ""
                    overall = min(75.0, max(0.0, pct * 0.75))
                    label = "Downloading audio" if is_audio else "Downloading"
                    message = f"{label}… {pct:.1f}%"
                    if speed and speed != "N/A":
                        message += f"  •  {speed}"
                    if eta and eta != "N/A":
                        message += f"  •  ETA {eta}"
                    self.events.put(("job_progress", job["id"], overall, message))
                elif line.startswith("KC_TITLE|"):
                    raw_title = line.split("|", 1)[1]
                    title = safe_filename(raw_title)
                    self.events.put(("job_title", job["id"], raw_title))
                elif line.startswith("KC_FILE|"):
                    downloaded_path = Path(line.split("|", 1)[1])
                else:
                    self.events.put(("log", line))

            returncode = proc.wait()
            self.active_process = None
            if returncode != 0:
                if self.operation_cancel_requested:
                    raise RuntimeError("Operation cancelled by user.")
                raise RuntimeError(
                    "yt-dlp could not complete the download. See the activity log for details."
                )

            if self.operation_cancel_requested:
                raise RuntimeError("Operation cancelled by user.")

            if not downloaded_path or not downloaded_path.exists():
                candidates = [
                    p
                    for p in temp_dir.rglob("*")
                    if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS
                ]
                if not candidates:
                    raise RuntimeError(
                        "The download finished, but the media file could not be located."
                    )
                downloaded_path = max(candidates, key=lambda p: p.stat().st_size)

            if not title:
                title = safe_filename(downloaded_path.stem)

            if is_mp3:
                extension = ".mp3"
            elif is_wav:
                extension = ".wav"
            else:
                extension = ".mp4"
            output = job["output_dir"] / f"{title}{extension}"
            index = 2
            while output.exists():
                output = job["output_dir"] / f"{title} ({index}){extension}"
                index += 1

            duration = info.get("duration") if info else None

            if is_mp3:
                self.events.put(
                    ("job_progress", job["id"], 75, "Converting to 320 kbps MP3 audio…")
                )
                self.events.put(("log", f"Converting MP3: {downloaded_path.name}"))
                self._convert_to_mp3(
                    downloaded_path,
                    output,
                    tools["ffmpeg"],
                    duration,
                    job["id"],
                )
            elif is_wav:
                self.events.put(
                    ("job_progress", job["id"], 75, "Converting to uncompressed WAV audio…")
                )
                self.events.put(("log", f"Converting WAV: {downloaded_path.name}"))
                self._convert_to_wav(
                    downloaded_path,
                    output,
                    tools["ffmpeg"],
                    duration,
                    job["id"],
                )
            else:
                self.events.put(
                    (
                        "job_progress",
                        job["id"],
                        75,
                        "Converting to PowerPoint-friendly H.264/AAC MP4…",
                    )
                )
                self.events.put(("log", f"Converting MP4: {downloaded_path.name}"))
                self._convert_to_mp4(
                    downloaded_path,
                    output,
                    tools["ffmpeg"],
                    duration,
                    job["id"],
                )

            return str(output)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _convert_to_mp4(self, source, output, ffmpeg, duration, job_id):
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-progress",
            "pipe:1",
            "-nostats",
            str(output),
        ]
        self._run_ffmpeg_conversion(cmd, duration, job_id, "Converting MP4")

    def _convert_to_mp3(self, source, output, ffmpeg, duration, job_id):
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "320k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-progress",
            "pipe:1",
            "-nostats",
            str(output),
        ]
        self._run_ffmpeg_conversion(cmd, duration, job_id, "Converting MP3")

    def _convert_to_wav(self, source, output, ffmpeg, duration, job_id):
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-c:a",
            "pcm_s16le",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-progress",
            "pipe:1",
            "-nostats",
            str(output),
        ]
        self._run_ffmpeg_conversion(cmd, duration, job_id, "Converting WAV")

    def _run_ffmpeg_conversion(self, cmd, duration, job_id, label):
        proc = self._start_process(cmd, capture_stderr=True)

        while True:
            if self.operation_cancel_requested:
                self._terminate_active_process()
                raise RuntimeError("Operation cancelled by user.")

            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue

            line = line.strip()
            if line.startswith("out_time_us=") and duration:
                try:
                    seconds = int(line.split("=", 1)[1]) / 1_000_000
                    pct = min(100.0, seconds / float(duration) * 100)
                    overall = 75.0 + pct * 0.25
                    self.events.put(
                        ("job_progress", job_id, overall, f"{label}… {pct:.1f}%")
                    )
                except (ValueError, ZeroDivisionError):
                    pass

        _, stderr = proc.communicate()
        self.active_process = None
        if proc.returncode != 0:
            if self.operation_cancel_requested:
                raise RuntimeError("Operation cancelled by user.")
            detail = (stderr or "").strip()
            raise RuntimeError(f"FFmpeg conversion failed.\n{detail}".strip())

    def _start_process(self, cmd, capture_stderr=False):
        creationflags = no_window_flags()
        if os.name == "nt":
            creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE if capture_stderr else subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            env=tool_environment(),
        )
        self.active_process = proc
        return proc

    def _terminate_active_process(self):
        proc = self.active_process
        if not proc or proc.poll() is not None:
            return

        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=no_window_flags(),
                    check=False,
                )
            else:
                proc.terminate()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _cancel_current(self):
        if self._preview_busy():
            self.operation_cancel_requested = True
            self.status_var.set("Cancelling preview…")
            self._terminate_active_process()
            return

        if self.current_job_id is None:
            return

        self.operation_cancel_requested = True
        self.status_var.set("Cancelling current download…")
        self._append_log("Cancel requested for current download.")
        self._terminate_active_process()

    def _find_job(self, job_id):
        with self.jobs_lock:
            for job in self.jobs:
                if job["id"] == job_id:
                    return job
        return None

    def _remove_selected(self):
        selections = list(self.queue_tree.selection())
        if not selections:
            return

        blocked = False
        remove_ids = []

        with self.jobs_lock:
            for iid in selections:
                job_id = int(iid)
                job = next((item for item in self.jobs if item["id"] == job_id), None)
                if not job:
                    continue
                if job["status"] == "Running":
                    blocked = True
                    continue
                remove_ids.append(job_id)

            if remove_ids:
                self.jobs = [job for job in self.jobs if job["id"] not in remove_ids]

        for job_id in remove_ids:
            iid = str(job_id)
            if self.queue_tree.exists(iid):
                self.queue_tree.delete(iid)

        if blocked:
            messagebox.showinfo(
                "Download in progress",
                "The currently running item cannot be removed. Use Cancel Current first.",
            )

    def _clear_finished(self):
        with self.jobs_lock:
            remove_ids = [
                job["id"] for job in self.jobs if job["status"] in FINISHED_STATES
            ]
            self.jobs = [
                job for job in self.jobs if job["status"] not in FINISHED_STATES
            ]

        for job_id in remove_ids:
            iid = str(job_id)
            if self.queue_tree.exists(iid):
                self.queue_tree.delete(iid)

    def _update_tree(self, job_id, title=None, status=None):
        iid = str(job_id)
        if not self.queue_tree.exists(iid):
            return

        values = list(self.queue_tree.item(iid, "values"))
        while len(values) < 4:
            values.append("")

        if title is not None:
            values[0] = title
        if status is not None:
            values[3] = status

        self.queue_tree.item(iid, values=values)

    def _display_preview(self, url, info):
        self.preview_info = info
        self.preview_url = url

        title = info.get("title") or "Untitled video"
        uploader = info.get("uploader") or info.get("channel") or "Unknown channel"
        duration = duration_text(info.get("duration"))
        extractor = info.get("extractor_key") or info.get("extractor") or "Online video"

        self.preview_title_var.set(title)
        self.preview_detail_var.set(f"{uploader}  •  {duration}  •  {extractor}")

    def _queue_summary(self):
        with self.jobs_lock:
            counts = {}
            for job in self.jobs:
                counts[job["status"]] = counts.get(job["status"], 0) + 1
        return counts

    def _process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]

                if kind == "log":
                    self._append_log(event[1])

                elif kind == "preview":
                    _, url, info = event
                    self._display_preview(url, info)
                    self.progress_var.set(0)
                    self.status_var.set("Preview ready")

                elif kind == "preview_error":
                    message = event[1]
                    cancelled = "cancelled" in message.lower()
                    self.status_var.set("Cancelled" if cancelled else "Preview failed")
                    if not cancelled:
                        self._append_log(message)
                        messagebox.showerror("Preview failed", message)

                elif kind == "job_metadata":
                    _, job_id, info = event
                    job = self._find_job(job_id)
                    if job:
                        job["info"] = info

                elif kind == "job_title":
                    _, job_id, title = event
                    job = self._find_job(job_id)
                    if job:
                        job["title"] = title
                    self._update_tree(job_id, title=title)

                elif kind == "job_status":
                    _, job_id, state = event
                    self._update_tree(job_id, status=state)
                    self.progress_var.set(0)
                    self.status_var.set("Starting next queued download…")
                    self._refresh_controls()

                elif kind == "job_progress":
                    _, job_id, pct, message = event
                    if job_id == self.current_job_id:
                        self.progress_var.set(max(0, min(100, pct)))
                        self.status_var.set(message)

                elif kind == "job_done":
                    _, job_id, output = event
                    self._update_tree(job_id, status="Complete")
                    self.progress_var.set(100)
                    self.status_var.set("Saved: " + Path(output).name)
                    self._append_log(f"Saved: {output}")

                elif kind == "job_error":
                    _, job_id, state, message = event
                    self._update_tree(job_id, status=state)
                    self.status_var.set(state)
                    if state == "Failed":
                        self._append_log(f"Failed: {message}")
                    else:
                        self._append_log("Current download cancelled.")

                elif kind == "queue_idle":
                    counts = self._queue_summary()
                    complete = counts.get("Complete", 0)
                    failed = counts.get("Failed", 0)
                    cancelled = counts.get("Cancelled", 0)
                    pending = counts.get("Queued", 0)

                    if pending:
                        self.root.after(150, self._ensure_queue_worker)
                    else:
                        parts = [f"{complete} complete"]
                        if failed:
                            parts.append(f"{failed} failed")
                        if cancelled:
                            parts.append(f"{cancelled} cancelled")
                        self.status_var.set("Queue finished — " + ", ".join(parts))
                        if complete or failed or cancelled:
                            self._append_log("Queue finished — " + ", ".join(parts))
                    self._refresh_controls()

        except queue.Empty:
            pass

        self._refresh_controls()
        self.root.after(100, self._process_events)

    def _on_close(self):
        self._save_settings()
        active = self._preview_busy() or self._queue_busy()
        if active:
            if not messagebox.askyesno(
                "Exit",
                "Downloads are still running. Cancel the current work and exit?",
            ):
                return
            self.operation_cancel_requested = True
            self._terminate_active_process()
        self.root.destroy()


def main():
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
