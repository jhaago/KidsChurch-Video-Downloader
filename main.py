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

APP_NAME = "Kids Church Video Downloader"
APP_VERSION = "0.2.0"

RESOLUTION_FORMATS = {
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
}

MEDIA_EXTENSIONS = {".mkv", ".mp4", ".webm", ".mov", ".m4v"}


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
    folder = base / "KidsChurchVideoDownloader"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "settings.json"


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name or "video"


def find_tool(name: str):
    suffix = ".exe" if os.name == "nt" else ""
    local = app_dir() / f"{name}{suffix}"
    if local.exists():
        return str(local)
    return shutil.which(name)


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


class DownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("840x680")
        self.root.minsize(760, 620)

        self.events = queue.Queue()
        self.worker = None
        self.active_process = None
        self.cancel_requested = False
        self.preview_info = None
        self.preview_url = None

        settings = self._load_settings()

        self.url_var = tk.StringVar()
        self.res_var = tk.StringVar(value=settings.get("resolution", "1080p"))
        if self.res_var.get() not in RESOLUTION_FORMATS:
            self.res_var.set("1080p")
        default_folder = settings.get("save_folder") or str(Path.home() / "Videos")
        self.folder_var = tk.StringVar(value=default_folder)

        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.preview_title_var = tk.StringVar(value="No video preview loaded.")
        self.preview_detail_var = tk.StringVar(value="")
        self.tools_var = tk.StringVar(value="Checking bundled tools…")

        self._build_ui()
        self._refresh_tool_status()
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
            text="Paste a video link, preview it, then create a PowerPoint-friendly MP4.",
            wraplength=790,
        ).pack(anchor="w", pady=(4, 18))

        url_frame = ttk.Frame(outer)
        url_frame.pack(fill="x")
        ttk.Label(url_frame, text="Video URL").grid(row=0, column=0, columnspan=2, sticky="w")
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        self.preview_btn = ttk.Button(url_frame, text="Preview", command=self._start_preview)
        self.preview_btn.grid(row=1, column=1, padx=(8, 0), pady=(4, 10))
        url_frame.columnconfigure(0, weight=1)
        self.url_entry.focus_set()
        self.url_entry.bind("<Return>", lambda _event: self._start_preview())

        preview = ttk.LabelFrame(outer, text="Video preview")
        preview.pack(fill="x", pady=(0, 14))
        ttk.Label(
            preview,
            textvariable=self.preview_title_var,
            font=("Segoe UI", 11, "bold"),
            wraplength=760,
        ).pack(anchor="w", padx=10, pady=(8, 2))
        ttk.Label(
            preview,
            textvariable=self.preview_detail_var,
            wraplength=760,
        ).pack(anchor="w", padx=10, pady=(0, 8))

        options = ttk.Frame(outer)
        options.pack(fill="x")

        ttk.Label(options, text="Maximum resolution").grid(row=0, column=0, sticky="w")
        ttk.Label(options, text="Save folder").grid(row=0, column=1, sticky="w", padx=(18, 0))

        self.res_combo = ttk.Combobox(
            options,
            textvariable=self.res_var,
            values=list(RESOLUTION_FORMATS.keys()),
            state="readonly",
            width=12,
        )
        self.res_combo.grid(row=1, column=0, sticky="w", pady=(4, 12))

        folder_row = ttk.Frame(options)
        folder_row.grid(row=1, column=1, sticky="ew", padx=(18, 0), pady=(4, 12))
        ttk.Entry(folder_row, textvariable=self.folder_var).pack(side="left", fill="x", expand=True)
        ttk.Button(folder_row, text="Browse…", command=self._browse).pack(side="left", padx=(8, 0))
        options.columnconfigure(1, weight=1)

        legal = ttk.LabelFrame(outer, text="Use")
        legal.pack(fill="x", pady=(0, 14))
        ttk.Label(
            legal,
            text=(
                "Use this app only for videos you own or are authorised to download. "
                "The app does not attempt to bypass DRM or protected streaming restrictions."
            ),
            wraplength=780,
        ).pack(anchor="w", padx=10, pady=8)

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x")
        self.download_btn = ttk.Button(buttons, text="Download PowerPoint MP4", command=self._start_download)
        self.download_btn.pack(side="left")
        self.cancel_btn = ttk.Button(buttons, text="Cancel", command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Open Save Folder", command=self._open_folder).pack(side="right")

        ttk.Progressbar(
            outer,
            variable=self.progress_var,
            maximum=100,
        ).pack(fill="x", pady=(18, 6))
        ttk.Label(outer, textvariable=self.status_var).pack(anchor="w")

        log_frame = ttk.LabelFrame(outer, text="Activity")
        log_frame.pack(fill="both", expand=True, pady=(14, 0))
        self.log = tk.Text(log_frame, height=9, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=8, pady=8)

        ttk.Label(
            outer,
            textvariable=self.tools_var,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(10, 0))

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

    def _set_busy(self, busy: bool, preview=False):
        self.download_btn.configure(state="disabled" if busy else "normal")
        self.preview_btn.configure(state="disabled" if busy else "normal")
        self.res_combo.configure(state="disabled" if busy else "readonly")
        self.cancel_btn.configure(state="normal" if busy else "disabled")
        if busy and preview:
            self.status_var.set("Loading video information…")

    def _start_preview(self):
        if self.worker and self.worker.is_alive():
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Video URL", "Paste a video URL first.")
            return

        tools = self._required_tools()
        if not tools:
            return

        self.cancel_requested = False
        self.progress_var.set(0)
        self.preview_title_var.set("Loading preview…")
        self.preview_detail_var.set("")
        self._set_busy(True, preview=True)
        self.worker = threading.Thread(
            target=self._preview_worker,
            args=(url, tools["yt-dlp"]),
            daemon=True,
        )
        self.worker.start()

    def _preview_worker(self, url, yt_dlp):
        try:
            info = self._fetch_metadata(url, yt_dlp)
            self.events.put(("preview", url, info))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _fetch_metadata(self, url, yt_dlp):
        cmd = [
            yt_dlp,
            "--no-playlist",
            "--skip-download",
            "--dump-single-json",
            "--no-warnings",
            url,
        ]
        proc = self._start_process(cmd, capture_stderr=True)
        stdout, stderr = proc.communicate()
        self.active_process = None

        if self.cancel_requested:
            raise RuntimeError("Operation cancelled by user.")
        if proc.returncode != 0:
            detail = (stderr or stdout or "").strip()
            raise RuntimeError(detail or "Could not read video information.")

        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("The video information returned by yt-dlp could not be read.") from exc

    def _start_download(self):
        if self.worker and self.worker.is_alive():
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Video URL", "Paste a video URL first.")
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
        self.cancel_requested = False
        self.progress_var.set(0)
        self.status_var.set("Starting download…")
        self._append_log(f"Starting: {url}")
        self._set_busy(True)

        cached_info = self.preview_info if self.preview_url == url else None
        self.worker = threading.Thread(
            target=self._download_worker,
            args=(url, output_dir, self.res_var.get(), tools, cached_info),
            daemon=True,
        )
        self.worker.start()

    def _download_worker(self, url, output_dir, resolution, tools, cached_info):
        temp_dir = Path(tempfile.mkdtemp(prefix="kc_video_"))
        title = None
        info = cached_info

        try:
            if info is None:
                try:
                    info = self._fetch_metadata(url, tools["yt-dlp"])
                    self.events.put(("preview", url, info))
                except Exception as exc:
                    self.events.put(("log", f"Preview information unavailable: {exc}"))

            if info:
                title = safe_filename(info.get("title") or "video")

            self.events.put(("status", "Downloading video and audio…"))

            progress_template = "download:KC_PROGRESS|%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s"
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
                RESOLUTION_FORMATS.get(resolution, RESOLUTION_FORMATS["1080p"]),
                "--merge-output-format",
                "mkv",
                "--output",
                str(temp_dir / "%(title).180B [%(id)s].%(ext)s"),
                "--print",
                "before_dl:KC_TITLE|%(title)s",
                "--print",
                "after_move:KC_FILE|%(filepath)s",
                url,
            ]

            proc = self._start_process(cmd, capture_stderr=False)
            downloaded_path = None

            for raw_line in proc.stdout:
                if self.cancel_requested:
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
                    message = f"Downloading… {pct:.1f}%"
                    if speed and speed != "N/A":
                        message += f"  •  {speed}"
                    if eta and eta != "N/A":
                        message += f"  •  ETA {eta}"
                    self.events.put(("progress", overall, message))
                elif line.startswith("KC_TITLE|"):
                    title = safe_filename(line.split("|", 1)[1])
                elif line.startswith("KC_FILE|"):
                    downloaded_path = Path(line.split("|", 1)[1])
                else:
                    self.events.put(("log", line))

            returncode = proc.wait()
            self.active_process = None
            if returncode != 0:
                raise RuntimeError("yt-dlp could not complete the download. See the activity log for details.")

            if self.cancel_requested:
                raise RuntimeError("Operation cancelled by user.")

            if not downloaded_path or not downloaded_path.exists():
                candidates = [
                    p
                    for p in temp_dir.rglob("*")
                    if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS
                ]
                if not candidates:
                    raise RuntimeError("The download finished, but the video file could not be located.")
                downloaded_path = max(candidates, key=lambda p: p.stat().st_size)

            if not title:
                title = safe_filename(downloaded_path.stem)

            output = output_dir / f"{title}.mp4"
            index = 2
            while output.exists():
                output = output_dir / f"{title} ({index}).mp4"
                index += 1

            duration = info.get("duration") if info else None
            self.events.put(("status", "Converting to PowerPoint-friendly H.264/AAC MP4…"))
            self.events.put(("log", f"Converting: {downloaded_path.name}"))
            self._convert_with_ffmpeg(downloaded_path, output, tools["ffmpeg"], duration)

            self.events.put(("progress", 100, "Complete"))
            self.events.put(("done", str(output)))
        except Exception as exc:
            self.events.put(("error", str(exc)))
        finally:
            self.active_process = None
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _convert_with_ffmpeg(self, source, output, ffmpeg, duration):
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

        proc = self._start_process(cmd, capture_stderr=True)

        while True:
            if self.cancel_requested:
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
                    self.events.put(("progress", overall, f"Converting MP4… {pct:.1f}%"))
                except (ValueError, ZeroDivisionError):
                    pass

        _, stderr = proc.communicate()
        self.active_process = None
        if proc.returncode != 0:
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

    def _cancel(self):
        self.cancel_requested = True
        self.status_var.set("Cancelling…")
        self._append_log("Cancel requested.")
        self._terminate_active_process()

    def _display_preview(self, url, info):
        self.preview_info = info
        self.preview_url = url

        title = info.get("title") or "Untitled video"
        uploader = info.get("uploader") or info.get("channel") or "Unknown channel"
        duration = duration_text(info.get("duration"))
        extractor = info.get("extractor_key") or info.get("extractor") or "Online video"

        self.preview_title_var.set(title)
        self.preview_detail_var.set(f"{uploader}  •  {duration}  •  {extractor}")

    def _process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]

                if kind == "progress":
                    _, pct, message = event
                    self.progress_var.set(max(0, min(100, pct)))
                    self.status_var.set(message)

                elif kind == "status":
                    self.status_var.set(event[1])

                elif kind == "log":
                    self._append_log(event[1])

                elif kind == "preview":
                    _, url, info = event
                    self._display_preview(url, info)

                elif kind == "done":
                    output = event[1]
                    self.status_var.set("Finished")
                    self._append_log(f"Saved: {output}")
                    self._set_busy(False)
                    messagebox.showinfo("Finished", f"Video saved as:\n{output}")

                elif kind == "error":
                    message = event[1]
                    cancelled = "cancelled" in message.lower()
                    self.status_var.set("Cancelled" if cancelled else "Failed")
                    self._append_log(message)
                    self._set_busy(False)
                    if not cancelled:
                        messagebox.showerror("Operation failed", message)

        except queue.Empty:
            pass

        if self.worker and not self.worker.is_alive():
            if str(self.download_btn["state"]) == "disabled":
                self._set_busy(False)
            if self.status_var.get() == "Loading video information…":
                self.status_var.set("Ready")

        self.root.after(100, self._process_events)

    def _on_close(self):
        self._save_settings()
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("Exit", "A download is still running. Cancel it and exit?"):
                return
            self.cancel_requested = True
            self._terminate_active_process()
        self.root.destroy()


def main():
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
