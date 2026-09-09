import os
import sys
import re
import shutil
import queue
import threading
import subprocess
import tempfile
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

APP_NAME = "Kids Church Video Downloader"
APP_VERSION = "0.1.0"

RESOLUTION_FORMATS = {
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
}

def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name or "video"

def find_binary(name: str):
    local = app_dir() / (name + (".exe" if os.name == "nt" else ""))
    if local.exists():
        return str(local)
    return shutil.which(name)

class DownloaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("780x560")
        self.root.minsize(720, 520)

        self.events = queue.Queue()
        self.worker = None
        self.cancel_requested = False

        self.url_var = tk.StringVar()
        self.res_var = tk.StringVar(value="1080p")
        self.folder_var = tk.StringVar(value=str(Path.home() / "Videos"))
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.title_var = tk.StringVar(value="")

        self._build_ui()
        self.root.after(100, self._process_events)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text=APP_NAME,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")

        ttk.Label(
            outer,
            text="Download authorised online video and create a PowerPoint-friendly MP4 (H.264 + AAC).",
            wraplength=720
        ).pack(anchor="w", pady=(4, 18))

        form = ttk.Frame(outer)
        form.pack(fill="x")

        ttk.Label(form, text="Video URL").grid(row=0, column=0, sticky="w")
        url_entry = ttk.Entry(form, textvariable=self.url_var)
        url_entry.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        url_entry.focus_set()

        ttk.Label(form, text="Maximum resolution").grid(row=2, column=0, sticky="w")
        res_combo = ttk.Combobox(
            form,
            textvariable=self.res_var,
            values=list(RESOLUTION_FORMATS.keys()),
            state="readonly",
            width=12
        )
        res_combo.grid(row=3, column=0, sticky="w", pady=(4, 12))

        ttk.Label(form, text="Save folder").grid(row=4, column=0, sticky="w")
        folder_entry = ttk.Entry(form, textvariable=self.folder_var)
        folder_entry.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 12))
        ttk.Button(form, text="Browse…", command=self._browse).grid(
            row=5, column=2, sticky="ew", padx=(8, 0), pady=(4, 12)
        )

        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        legal = ttk.LabelFrame(outer, text="Use")
        legal.pack(fill="x", pady=(4, 14))
        ttk.Label(
            legal,
            text=(
                "Use this app only for videos you own or are authorised to download. "
                "It does not attempt to bypass DRM or protected streaming restrictions."
            ),
            wraplength=710
        ).pack(anchor="w", padx=10, pady=8)

        btns = ttk.Frame(outer)
        btns.pack(fill="x")

        self.download_btn = ttk.Button(btns, text="Download MP4", command=self._start_download)
        self.download_btn.pack(side="left")

        self.cancel_btn = ttk.Button(btns, text="Cancel", command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=(8, 0))

        ttk.Button(btns, text="Open Save Folder", command=self._open_folder).pack(side="right")

        ttk.Progressbar(
            outer,
            variable=self.progress_var,
            maximum=100
        ).pack(fill="x", pady=(18, 6))

        ttk.Label(outer, textvariable=self.status_var).pack(anchor="w")

        self.title_label = ttk.Label(
            outer,
            textvariable=self.title_var,
            wraplength=720,
            font=("Segoe UI", 10, "italic")
        )
        self.title_label.pack(anchor="w", pady=(8, 0))

        log_frame = ttk.LabelFrame(outer, text="Activity")
        log_frame.pack(fill="both", expand=True, pady=(14, 0))

        self.log = tk.Text(log_frame, height=10, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=8, pady=8)

    def _browse(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get() or str(Path.home()))
        if folder:
            self.folder_var.set(folder)

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

    def _set_busy(self, busy: bool):
        self.download_btn.configure(state="disabled" if busy else "normal")
        self.cancel_btn.configure(state="normal" if busy else "disabled")

    def _start_download(self):
        if self.worker and self.worker.is_alive():
            return

        if yt_dlp is None:
            messagebox.showerror(
                "Missing dependency",
                "yt-dlp is not installed.\n\nRun: pip install -r requirements.txt"
            )
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Video URL", "Paste a video URL first.")
            return

        output_dir = Path(self.folder_var.get()).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Save folder", f"Could not use that folder:\n{exc}")
            return

        ffmpeg = find_binary("ffmpeg")
        if not ffmpeg:
            messagebox.showerror(
                "FFmpeg required",
                "FFmpeg was not found.\n\n"
                "For development, install FFmpeg and add it to PATH.\n"
                "For the packaged app, place ffmpeg.exe beside the program."
            )
            return

        self.cancel_requested = False
        self.progress_var.set(0)
        self.title_var.set("")
        self.status_var.set("Starting…")
        self._append_log(f"Starting: {url}")
        self._set_busy(True)

        self.worker = threading.Thread(
            target=self._download_worker,
            args=(url, output_dir, self.res_var.get(), ffmpeg),
            daemon=True
        )
        self.worker.start()

    def _cancel(self):
        self.cancel_requested = True
        self.status_var.set("Cancelling…")
        self._append_log("Cancel requested.")

    def _download_worker(self, url: str, output_dir: Path, resolution: str, ffmpeg: str):
        temp_dir = Path(tempfile.mkdtemp(prefix="kc_video_"))
        try:
            def progress_hook(d):
                if self.cancel_requested:
                    raise RuntimeError("Download cancelled by user.")

                status = d.get("status")
                if status == "downloading":
                    downloaded = d.get("downloaded_bytes") or 0
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    pct = (downloaded / total * 100) if total else 0
                    speed = d.get("speed")
                    eta = d.get("eta")
                    msg = f"Downloading… {pct:.1f}%"
                    if speed:
                        msg += f"  •  {speed/1024/1024:.1f} MB/s"
                    if eta is not None:
                        msg += f"  •  ETA {eta}s"
                    self.events.put(("progress", pct, msg))
                elif status == "finished":
                    self.events.put(("status", "Download complete. Preparing MP4…"))

            ydl_opts = {
                "format": RESOLUTION_FORMATS.get(resolution, RESOLUTION_FORMATS["1080p"]),
                "outtmpl": str(temp_dir / "%(title).180B [%(id)s].%(ext)s"),
                "merge_output_format": "mkv",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [progress_hook],
                "ffmpeg_location": str(Path(ffmpeg).parent),
                "restrictfilenames": False,
                # Avoid any credential/cookie automation in V0.1.
                "cookiefile": None,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            if self.cancel_requested:
                raise RuntimeError("Download cancelled by user.")

            title = safe_filename(info.get("title") or "video")
            self.events.put(("title", title))

            candidates = [
                p for p in temp_dir.iterdir()
                if p.is_file() and p.suffix.lower() in {".mkv", ".mp4", ".webm", ".mov", ".m4v"}
            ]
            if not candidates:
                raise RuntimeError("The download finished, but the video file could not be located.")

            source = max(candidates, key=lambda p: p.stat().st_size)
            output = output_dir / f"{title}.mp4"
            index = 2
            while output.exists():
                output = output_dir / f"{title} ({index}).mp4"
                index += 1

            self.events.put(("status", "Converting to PowerPoint-friendly H.264/AAC MP4…"))
            self.events.put(("log", f"Converting: {source.name}"))

            cmd = [
                ffmpeg,
                "-hide_banner",
                "-loglevel", "error",
                "-y",
                "-i", str(source),
                "-map", "0:v:0",
                "-map", "0:a:0?",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                str(output)
            ]

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )

            while proc.poll() is None:
                if self.cancel_requested:
                    proc.terminate()
                    raise RuntimeError("Download cancelled by user.")
                threading.Event().wait(0.2)

            _, stderr = proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"FFmpeg conversion failed:\n{stderr.strip()}")

            self.events.put(("progress", 100, "Complete"))
            self.events.put(("done", str(output)))

        except Exception as exc:
            self.events.put(("error", str(exc)))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]

                if kind == "progress":
                    _, pct, msg = event
                    self.progress_var.set(max(0, min(100, pct)))
                    self.status_var.set(msg)

                elif kind == "status":
                    self.status_var.set(event[1])

                elif kind == "title":
                    self.title_var.set(event[1])

                elif kind == "log":
                    self._append_log(event[1])

                elif kind == "done":
                    output = event[1]
                    self.status_var.set("Finished")
                    self._append_log(f"Saved: {output}")
                    self._set_busy(False)
                    messagebox.showinfo("Finished", f"Video saved as:\n{output}")

                elif kind == "error":
                    msg = event[1]
                    self.status_var.set("Cancelled" if "cancelled" in msg.lower() else "Failed")
                    self._append_log(msg)
                    self._set_busy(False)
                    if "cancelled" not in msg.lower():
                        messagebox.showerror("Download failed", msg)

        except queue.Empty:
            pass

        self.root.after(100, self._process_events)

def main():
    root = tk.Tk()
    try:
        root.iconname(APP_NAME)
    except Exception:
        pass
    DownloaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
