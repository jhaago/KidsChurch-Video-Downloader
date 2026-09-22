from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox, ttk

import main as legacy
from sources.minno import MinnoClient
from sources.minno_browser import MinnoBrowserSession
from sources.progress import TransferSnapshot, format_bytes_per_second, format_eta, redact_sensitive
from sources.source_detector import SourceType, classify_source

APP_NAME = "KidsChurch Video Downloader"
APP_VERSION = "0.7.0"


def app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    folder = base / "KidsChurchVideoDownloader"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def resolution_height(value: str) -> int:
    try:
        height = int(str(value).strip().lower().removesuffix("p"))
    except (TypeError, ValueError):
        return 1080
    return height if height in {480, 720, 1080} else 1080


def output_extension(output_format: str) -> str:
    if output_format == "MP3 Audio":
        return ".mp3"
    if output_format == "WAV Audio":
        return ".wav"
    return ".mp4"


def resolve_save_name(custom_name: str, fallback: str) -> str:
    requested = str(custom_name or "").strip()
    base = requested or str(fallback or "media").strip() or "media"
    return legacy.safe_filename(base)


def unique_output_path(folder: Path, title: str, extension: str = ".mp4") -> Path:
    folder = Path(folder)
    title = legacy.safe_filename(title)
    candidate = folder / f"{title}{extension}"
    index = 2
    while candidate.exists():
        candidate = folder / f"{title} ({index}){extension}"
        index += 1
    return candidate


def format_minno_progress(
    snapshot: TransferSnapshot,
    media_label: str = "video",
) -> tuple[float, str]:
    transfer_pct = max(0.0, min(100.0, float(snapshot.percent)))
    overall_pct = transfer_pct if media_label == "audio" else transfer_pct * 0.75
    text = f"Downloading Minno {media_label}… {transfer_pct:.1f}%"
    speed = format_bytes_per_second(snapshot.speed_bps)
    eta = format_eta(snapshot.eta_seconds)
    if speed != "—":
        text += f"  •  {speed}"
    if eta != "—":
        text += f"  •  ETA {eta}"
    return overall_pct, text


class MultiSourceDownloaderApp(legacy.DownloaderApp):
    def __init__(self, root: tk.Tk):
        legacy.APP_NAME = APP_NAME
        legacy.APP_VERSION = APP_VERSION
        self.minno_session_var = tk.StringVar(master=root, value="Minno: not signed in")
        self.save_as_var = tk.StringVar(master=root, value="")
        self.minno_browser_session: MinnoBrowserSession | None = None
        self.minno_client: MinnoClient | None = None
        super().__init__(root)
        self.minno_browser_session = MinnoBrowserSession(app_data_dir() / "minno-browser-profile")
        self.minno_client = MinnoClient(
            self.minno_browser_session,
            process_factory=self._minno_process_factory,
            status_callback=self._minno_status_callback,
        )
        self._refresh_minno_session_status()

    def _build_ui(self):
        super()._build_ui()
        self._replace_static_label("Paste a YouTube link below", "Paste a YouTube or Minno link below")

        preview_card = self._find_label_parent("PREVIEW")
        if preview_card is not None:
            save_row = ttk.Frame(preview_card, style="Card.TFrame")
            save_row.pack(fill="x", pady=(10, 0))
            ttk.Label(save_row, text="SAVE AS", style="MutedCard.TLabel").pack(side="left")
            ttk.Entry(save_row, textvariable=self.save_as_var).pack(
                side="left", fill="x", expand=True, padx=(12, 0)
            )

        footer = self._find_label_parent("Only download media you own or are authorised to use.")
        if footer is not None:
            ttk.Button(
                footer,
                text="Minno Account",
                style="Secondary.TButton",
                command=self._open_minno_account_dialog,
            ).pack(side="right", padx=(12, 0))
            ttk.Label(
                footer,
                textvariable=self.minno_session_var,
                style="Muted.TLabel",
            ).pack(side="right", padx=(12, 0))

    def _walk_widgets(self, widget):
        for child in widget.winfo_children():
            yield child
            yield from self._walk_widgets(child)

    def _replace_static_label(self, old: str, new: str) -> None:
        for widget in self._walk_widgets(self.root):
            if isinstance(widget, ttk.Label):
                try:
                    if widget.cget("text") == old:
                        widget.configure(text=new)
                except tk.TclError:
                    pass

    def _find_label_parent(self, text: str):
        for widget in self._walk_widgets(self.root):
            if isinstance(widget, ttk.Label):
                try:
                    if widget.cget("text") == text:
                        return widget.master
                except tk.TclError:
                    pass
        return None

    def _refresh_minno_session_status(self) -> None:
        session = self.minno_browser_session
        if session is not None and session.profile_exists():
            self.minno_session_var.set("Minno: saved session")
        else:
            self.minno_session_var.set("Minno: not signed in")

    def _open_minno_account_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Minno Account")
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Minno Account", style="Section.TLabel").pack(anchor="w")
        ttk.Label(frame, textvariable=self.minno_session_var).pack(anchor="w", pady=(6, 10))
        ttk.Label(
            frame,
            text=(
                "Sign in directly on Minno in the browser window. This downloader uses a separate "
                "browser profile and does not read your normal Chrome profile."
            ),
            wraplength=430,
        ).pack(anchor="w", pady=(0, 12))
        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        ttk.Button(actions, text="Refresh / Sign in", command=self._minno_sign_in).pack(side="left")
        ttk.Button(actions, text="Sign out", command=self._minno_sign_out).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Close", command=dialog.destroy).pack(side="right")

    def _minno_sign_in(self) -> None:
        if self.minno_browser_session is None:
            return
        try:
            self.minno_browser_session.open_account_window()
            self.minno_session_var.set("Minno: sign-in browser open")
            messagebox.showinfo(
                "Minno sign in",
                "Sign in to Minno in the browser window. When you are finished, you can close that browser window. The separate session will be kept for future downloads.",
            )
        except Exception as exc:
            messagebox.showerror("Minno Account", redact_sensitive(str(exc)))

    def _minno_sign_out(self) -> None:
        if self.minno_browser_session is None:
            return
        try:
            self.minno_browser_session.sign_out()
            self.minno_session_var.set("Minno: not signed in")
        except Exception as exc:
            messagebox.showerror("Minno Account", redact_sensitive(str(exc)))

    def _minno_status_callback(self, message: str) -> None:
        self.events.put(("log", redact_sensitive(message)))

    @staticmethod
    def _minno_process_factory(command, **kwargs):
        creationflags = legacy.no_window_flags()
        if os.name == "nt":
            creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP
        kwargs.setdefault("creationflags", creationflags)
        kwargs.setdefault("env", legacy.tool_environment())
        kwargs.setdefault("encoding", "utf-8")
        kwargs.setdefault("errors", "replace")
        return subprocess.Popen(command, **kwargs)

    def _preview_worker(self, url, tools):
        source = classify_source(url)
        try:
            if source == SourceType.YOUTUBE:
                info = self._fetch_metadata(url, tools)
            elif source == SourceType.MINNO:
                if self.minno_client is None:
                    raise RuntimeError("Minno support is not ready.")
                preview = self.minno_client.preview(
                    url,
                    max_height=resolution_height(self.res_var.get()),
                    cancel_requested=lambda: self.operation_cancel_requested,
                    status_callback=self._minno_status_callback,
                )
                info = {
                    "title": preview.title,
                    "duration": preview.duration,
                    "source": "Minno",
                    "max_height": preview.max_height,
                }
            else:
                raise RuntimeError("Unsupported URL. Paste a YouTube or Minno link.")
            self.events.put(("preview", url, info))
        except Exception as exc:
            message = redact_sensitive(str(exc)) if source == SourceType.MINNO else str(exc)
            self.events.put(("preview_error", message))

    def _display_preview(self, url, info):
        if info.get("source") != "Minno":
            super()._display_preview(url, info)
            self.save_as_var.set(info.get("title") or "")
            return
        self.preview_info = info
        self.preview_url = url
        title = info.get("title") or "Minno episode"
        self.preview_title_var.set(title)
        self.preview_detail_var.set(
            f"Minno  •  {legacy.duration_text(info.get('duration'))}  •  up to {info.get('max_height') or 1080}p"
        )
        self.save_as_var.set(title)
        self.minno_session_var.set("Minno: saved session")

    def _queue_current_url(self):
        if self._preview_busy():
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Video URL", "Paste a YouTube or Minno URL first.")
            return

        source = classify_source(url)
        if source == SourceType.UNKNOWN:
            messagebox.showerror("Unsupported URL", "Paste a YouTube or Minno link.")
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
        if cached_info and cached_info.get("title"):
            display_title = cached_info["title"]
        elif source == SourceType.MINNO:
            display_title = "Minno episode"
        else:
            display_title = getattr(legacy, "short_url", lambda value: value)(url)

        output_format = self.output_format_var.get()
        if output_format == "MP4 Video":
            quality = self.res_var.get()
        elif output_format == "MP3 Audio":
            quality = "320 kbps"
        else:
            quality = "PCM"

        requested_name = self.save_as_var.get().strip()
        self.job_counter += 1
        job = {
            "id": self.job_counter,
            "source": source.value,
            "url": url,
            "resolution": self.res_var.get(),
            "output_format": output_format,
            "output_dir": output_dir,
            "title": display_title,
            "save_name": requested_name,
            "status": "Queued",
            "info": cached_info,
        }
        with self.jobs_lock:
            self.jobs.append(job)

        self.queue_tree.insert(
            "",
            "end",
            iid=str(job["id"]),
            values=(
                display_title,
                output_format.replace(" Video", "").replace(" Audio", ""),
                quality,
                "Queued",
                "",
            ),
            tags=("Queued",),
        )
        self._refresh_queue_count()
        if source == SourceType.MINNO:
            self._append_log(f"Queued {output_format}: Minno episode")
        else:
            self._append_log(f"Queued {output_format}: {display_title}")

        self.url_var.set("")
        self.save_as_var.set("")
        self.preview_info = None
        self.preview_url = None
        self.preview_title_var.set("No video preview loaded.")
        self.preview_detail_var.set("")
        self.url_entry.focus_set()
        self._ensure_queue_worker(tools)
        self._refresh_controls()

    def _queue_runner(self, tools):
        while True:
            job = self._claim_next_job()
            if job is None:
                break
            self.current_job_id = job["id"]
            self.operation_cancel_requested = False
            self.events.put(("job_status", job["id"], "Running"))
            if job.get("source") == SourceType.MINNO.value:
                self.events.put(("log", f"Starting {job['output_format']}: Minno episode"))
            else:
                self.events.put(("log", f"Starting {job['output_format']}: {job['url']}"))
            try:
                output = self._download_job(job, tools)
                self._set_job_status(job["id"], "Complete")
                self.events.put(("job_done", job["id"], output))
            except Exception as exc:
                message = redact_sensitive(str(exc)) if job.get("source") == SourceType.MINNO.value else str(exc)
                cancelled = self.operation_cancel_requested or "cancelled" in message.lower()
                state = "Cancelled" if cancelled else "Failed"
                self._set_job_status(job["id"], state)
                self.events.put(("job_error", job["id"], state, message))
            finally:
                self.active_process = None
                self.current_job_id = None
                self.operation_cancel_requested = False
        self.events.put(("queue_idle",))

    def _download_job(self, job, tools):
        if job.get("source") == SourceType.MINNO.value:
            return self._download_minno_job(job, tools)

        output = Path(super()._download_job(job, tools))
        custom_name = str(job.get("save_name") or "").strip()
        if not custom_name:
            return str(output)

        desired_title = resolve_save_name(custom_name, output.stem)
        if desired_title == output.stem:
            return str(output)
        renamed = unique_output_path(output.parent, desired_title, output.suffix)
        shutil.move(str(output), str(renamed))
        return str(renamed)

    def _download_minno_job(self, job, tools):
        if self.minno_client is None:
            raise RuntimeError("Minno support is not ready.")
        temp_dir = Path(tempfile.mkdtemp(prefix="minno_downloader_"))
        try:
            output_format = job["output_format"]
            is_audio = output_format in {"MP3 Audio", "WAV Audio"}
            temporary_output = temp_dir / "minno-transfer.mp4"

            def on_progress(snapshot: TransferSnapshot):
                pct, text = format_minno_progress(
                    snapshot,
                    media_label="audio" if is_audio else "video",
                )
                self.events.put(("job_progress", job["id"], pct, text))

            def on_process_started(process):
                self.active_process = process

            result = self.minno_client.download(
                job["url"],
                resolution_height(job["resolution"]),
                tools["ffmpeg"],
                temporary_output,
                output_format=output_format,
                cancel_requested=lambda: self.operation_cancel_requested,
                progress_callback=on_progress,
                process_started_callback=on_process_started,
            )
            self.active_process = None

            display_title = result.title or "Minno episode"
            self.events.put(("job_title", job["id"], display_title))
            clean_title = resolve_save_name(job.get("save_name", ""), display_title)
            output = unique_output_path(
                job["output_dir"],
                clean_title,
                output_extension(output_format),
            )

            if result.needs_conversion:
                self.events.put(
                    (
                        "job_progress",
                        job["id"],
                        75.0,
                        "Downloading complete  •  converting to PowerPoint-friendly MP4…",
                    )
                )
                self._convert_to_mp4(result.path, output, tools["ffmpeg"], result.duration, job["id"])
            else:
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(result.path), str(output))
                self.events.put(("job_progress", job["id"], 100.0, "Minno download complete"))
            return str(output)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

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
        if self.minno_browser_session is not None:
            self.minno_browser_session.close_managed_browser()
        self.root.destroy()


def main():
    root = tk.Tk()
    MultiSourceDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
