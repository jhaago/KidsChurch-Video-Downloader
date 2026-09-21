from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import re
from urllib.parse import urlsplit, urlunsplit


_SENSITIVE_HEADER_RE = re.compile(r"(?im)^(Cookie|Authorization|X-Playback-Token)\s*:\s*.*$")
_TOKEN_RE = re.compile(r"(?i)\b(sessionId|token)\s*=\s*([^\s&]+)")
_URL_RE = re.compile(r"https?://[^\s]+")


def _redact_url(match: re.Match[str]) -> str:
    raw = match.group(0)
    trailing = ""
    while raw and raw[-1] in "),.;]":
        trailing = raw[-1] + trailing
        raw = raw[:-1]
    try:
        parts = urlsplit(raw)
    except ValueError:
        return match.group(0)
    if not parts.query:
        return raw + trailing
    safe = urlunsplit((parts.scheme, parts.netloc, parts.path, "<redacted>", parts.fragment))
    return safe + trailing


def redact_sensitive(text: str) -> str:
    safe = _URL_RE.sub(_redact_url, str(text))
    safe = _SENSITIVE_HEADER_RE.sub(lambda m: f"{m.group(1)}: <redacted>", safe)
    safe = _TOKEN_RE.sub(lambda m: f"{m.group(1)}=<redacted>", safe)
    return safe


def format_bytes_per_second(value: float | None) -> str:
    if value is None or value < 0:
        return "—"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} MB/s"
    if value >= 1_000:
        return f"{value / 1_000:.1f} KB/s"
    return f"{value:.0f} B/s"


def format_eta(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    total = max(0, int(round(seconds)))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


@dataclass(frozen=True)
class TransferSnapshot:
    percent: float
    speed_bps: float | None
    eta_seconds: float | None


class TransferProgressEstimator:
    def __init__(self, duration_seconds: float, window_seconds: float = 8.0):
        self.duration_seconds = max(0.0, float(duration_seconds))
        self.window_seconds = max(0.1, float(window_seconds))
        self._samples: deque[tuple[float, float, int | None]] = deque()

    def update(self, wall_time: float, media_seconds: float, total_size_bytes: int | None) -> TransferSnapshot:
        wall = float(wall_time)
        media = max(0.0, float(media_seconds))
        size = None if total_size_bytes is None else max(0, int(total_size_bytes))
        self._samples.append((wall, media, size))
        cutoff = wall - self.window_seconds
        while len(self._samples) > 2 and self._samples[0][0] < cutoff:
            self._samples.popleft()

        if self.duration_seconds > 0:
            percent = max(0.0, min(100.0, (media / self.duration_seconds) * 100.0))
        else:
            percent = 0.0

        speed_bps = None
        eta_seconds = None
        if len(self._samples) >= 2:
            first = self._samples[0]
            last = self._samples[-1]
            wall_delta = last[0] - first[0]
            if wall_delta > 0:
                if first[2] is not None and last[2] is not None and last[2] >= first[2]:
                    speed_bps = (last[2] - first[2]) / wall_delta
                media_delta = last[1] - first[1]
                if media_delta > 0 and self.duration_seconds > 0:
                    rate = media_delta / wall_delta
                    remaining = max(0.0, self.duration_seconds - media)
                    eta_seconds = remaining / rate if rate > 0 else None

        return TransferSnapshot(percent=percent, speed_bps=speed_bps, eta_seconds=eta_seconds)
