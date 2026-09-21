from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import time
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .hls import inspect_media_playlist, parse_master_playlist, select_stream
from .minno_browser import MinnoBrowserSession
from .progress import TransferProgressEstimator, TransferSnapshot


class MinnoError(RuntimeError):
    pass


class MinnoUnsupportedFormatError(MinnoError):
    pass


class MinnoPlaylistError(MinnoError):
    pass


class MinnoDownloadCancelled(MinnoError):
    pass


class MinnoTransferError(MinnoError):
    def __init__(self, message: str, *, auth_failure: bool = False):
        super().__init__(message)
        self.auth_failure = auth_failure


@dataclass(frozen=True)
class MinnoPreview:
    title: str
    duration: float
    max_height: int
    source: str = "Minno"


@dataclass(frozen=True)
class PreparedMinnoStream:
    title: str
    duration: float
    video_url: str
    audio_url: str
    headers: dict[str, str]
    video_codec: str | None
    audio_codec: str | None
    width: int | None
    height: int | None

    @property
    def is_powerpoint_compatible(self) -> bool:
        video = (self.video_codec or "").lower()
        audio = (self.audio_codec or "").lower()
        return (video.startswith("avc1") or video.startswith("h264")) and (
            audio.startswith("mp4a") or audio.startswith("aac")
        )


@dataclass(frozen=True)
class MinnoDownloadResult:
    path: Path
    needs_conversion: bool


def validate_output_format(output_format: str) -> None:
    if output_format != "MP4 Video":
        raise MinnoUnsupportedFormatError("Minno downloads currently support MP4 Video only.")


def _codec_pair(codecs: tuple[str, ...]) -> tuple[str | None, str | None]:
    video = next(
        (codec for codec in codecs if codec.lower().startswith(("avc1", "h264", "hev1", "hvc1", "vp09", "av01"))),
        None,
    )
    audio = next(
        (codec for codec in codecs if codec.lower().startswith(("mp4a", "aac", "opus", "vorbis"))),
        None,
    )
    return video, audio


class MinnoClient:
    def __init__(
        self,
        browser_session: MinnoBrowserSession,
        *,
        fetch_text: Callable[[str, Mapping[str, str]], str] | None = None,
        process_factory: Callable | None = None,
        status_callback: Callable[[str], None] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.browser_session = browser_session
        self._fetch_text = fetch_text or self._http_fetch_text
        self._process_factory = process_factory or subprocess.Popen
        self._status_callback = status_callback or (lambda _message: None)
        self._monotonic = monotonic

    @staticmethod
    def _http_fetch_text(url: str, headers: Mapping[str, str]) -> str:
        request = Request(url, headers=dict(headers), method="GET")
        try:
            with urlopen(request, timeout=20.0) as response:
                return response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            raise MinnoPlaylistError(f"Minno playlist request failed with HTTP {exc.code}.") from exc
        except URLError as exc:
            raise MinnoPlaylistError("Minno playlist request failed due to a network error.") from exc

    def prepare(
        self,
        page_url: str,
        max_height: int,
        *,
        cancel_requested: Callable[[], bool] | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> PreparedMinnoStream:
        cancel_requested = cancel_requested or (lambda: False)
        status_callback = status_callback or self._status_callback
        discovery = self.browser_session.discover(
            page_url,
            cancel_requested=cancel_requested,
            status_callback=status_callback,
        )
        status_callback("Minno stream discovered.")
        master_text = self._fetch_text(discovery.master_playlist_url, discovery.request_headers)
        master = parse_master_playlist(master_text, discovery.master_playlist_url)
        selection = select_stream(master, int(max_height))

        video_text = self._fetch_text(selection.video.uri, discovery.request_headers)
        video_info = inspect_media_playlist(video_text)
        audio_text = self._fetch_text(selection.audio.uri, discovery.request_headers)
        inspect_media_playlist(audio_text)

        video_codec, audio_codec = _codec_pair(selection.video.codecs)
        status_callback(
            f"Selected {selection.video.width or '?'}x{selection.video.height or '?'} video + "
            f"{selection.audio.language or selection.audio.name or 'audio'}."
        )
        return PreparedMinnoStream(
            title=discovery.title or "Minno episode",
            duration=video_info.duration_seconds,
            video_url=selection.video.uri,
            audio_url=selection.audio.uri,
            headers=dict(discovery.request_headers),
            video_codec=video_codec,
            audio_codec=audio_codec,
            width=selection.video.width,
            height=selection.video.height,
        )

    def preview(
        self,
        page_url: str,
        max_height: int = 1080,
        *,
        cancel_requested: Callable[[], bool] | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> MinnoPreview:
        prepared = self.prepare(
            page_url,
            max_height,
            cancel_requested=cancel_requested,
            status_callback=status_callback,
        )
        return MinnoPreview(
            title=prepared.title,
            duration=prepared.duration,
            max_height=prepared.height or int(max_height),
        )

    @staticmethod
    def _header_block(headers: Mapping[str, str]) -> str:
        return "".join(f"{key}: {value}\r\n" for key, value in headers.items())

    def _build_ffmpeg_command(
        self,
        prepared: PreparedMinnoStream,
        ffmpeg: str,
        target: Path,
        needs_conversion: bool,
    ) -> list[str]:
        command = [str(ffmpeg), "-y", "-hide_banner", "-loglevel", "warning"]
        header_block = self._header_block(prepared.headers)
        if header_block:
            command += ["-headers", header_block]
        command += ["-i", prepared.video_url]
        if header_block:
            command += ["-headers", header_block]
        command += ["-i", prepared.audio_url]
        command += [
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c", "copy",
        ]
        if not needs_conversion:
            command += ["-movflags", "+faststart"]
        command += ["-progress", "pipe:1", "-nostats", str(target)]
        return command

    @staticmethod
    def _terminate(process) -> None:
        if process is None:
            return
        try:
            if process.poll() is None:
                process.terminate()
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    def _run_transfer(
        self,
        prepared: PreparedMinnoStream,
        ffmpeg: str,
        target: Path,
        needs_conversion: bool,
        cancel_requested: Callable[[], bool],
        progress_callback: Callable[[TransferSnapshot], None],
        process_started_callback: Callable[[object], None],
    ) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        command = self._build_ffmpeg_command(prepared, ffmpeg, target, needs_conversion)
        process = self._process_factory(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        process_started_callback(process)
        estimator = TransferProgressEstimator(prepared.duration)
        out_time_seconds = 0.0
        total_size: int | None = None
        diagnostics: list[str] = []
        try:
            if cancel_requested():
                self._terminate(process)
                raise MinnoDownloadCancelled("Minno download cancelled.")
            for raw in process.stdout or ():
                if cancel_requested():
                    self._terminate(process)
                    raise MinnoDownloadCancelled("Minno download cancelled.")
                line = str(raw).strip()
                diagnostics.append(line)
                if len(diagnostics) > 80:
                    diagnostics.pop(0)
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key in {"out_time_us", "out_time_ms"}:
                    try:
                        out_time_seconds = max(0.0, float(value) / 1_000_000.0)
                    except ValueError:
                        pass
                elif key == "total_size":
                    try:
                        total_size = max(0, int(value))
                    except ValueError:
                        pass
                elif key == "progress":
                    snapshot = estimator.update(self._monotonic(), out_time_seconds, total_size)
                    progress_callback(snapshot)
            return_code = process.wait()
        finally:
            if cancel_requested() and process is not None:
                self._terminate(process)

        if return_code != 0:
            diagnostic_text = "\n".join(diagnostics).lower()
            auth_failure = any(marker in diagnostic_text for marker in (" 401", " 403", "unauthorized", "forbidden", "http error 401", "http error 403"))
            if auth_failure:
                raise MinnoTransferError("Minno transfer failed with HTTP 403/authorization expiry.", auth_failure=True)
            raise MinnoTransferError("Minno transfer failed.")

    def download(
        self,
        page_url: str,
        max_height: int,
        ffmpeg: str,
        output_path: Path,
        cancel_requested: Callable[[], bool],
        progress_callback: Callable[[TransferSnapshot], None],
        process_started_callback: Callable[[object], None],
    ) -> MinnoDownloadResult:
        output_path = Path(output_path)
        for attempt in range(2):
            if cancel_requested():
                raise MinnoDownloadCancelled("Minno download cancelled.")
            prepared = self.prepare(
                page_url,
                max_height,
                cancel_requested=cancel_requested,
                status_callback=self._status_callback,
            )
            needs_conversion = not prepared.is_powerpoint_compatible
            target = output_path.with_suffix(".mkv") if needs_conversion else output_path.with_suffix(".mp4")
            self._status_callback("Starting Minno download.")
            try:
                self._run_transfer(
                    prepared,
                    ffmpeg,
                    target,
                    needs_conversion,
                    cancel_requested,
                    progress_callback,
                    process_started_callback,
                )
                self._status_callback("Minno transfer complete.")
                return MinnoDownloadResult(path=target, needs_conversion=needs_conversion)
            except MinnoDownloadCancelled:
                target.unlink(missing_ok=True)
                raise
            except MinnoTransferError as exc:
                target.unlink(missing_ok=True)
                if exc.auth_failure and attempt == 0:
                    self._status_callback("Minno session link expired; refreshing stream…")
                    continue
                raise
        raise MinnoTransferError("Minno transfer failed.")
