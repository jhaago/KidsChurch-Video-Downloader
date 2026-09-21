from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin


class ProtectedStreamError(RuntimeError):
    pass


class NoUsableStreamError(RuntimeError):
    pass


@dataclass(frozen=True)
class HlsVariant:
    uri: str
    bandwidth: int | None
    width: int | None
    height: int | None
    codecs: tuple[str, ...]
    audio_group: str | None


@dataclass(frozen=True)
class HlsAudioTrack:
    uri: str
    group_id: str | None
    language: str | None
    name: str | None
    is_default: bool


@dataclass(frozen=True)
class HlsMasterPlaylist:
    variants: tuple[HlsVariant, ...]
    audio_tracks: tuple[HlsAudioTrack, ...]


@dataclass(frozen=True)
class HlsMediaInfo:
    duration_seconds: float
    is_protected: bool = False


@dataclass(frozen=True)
class HlsSelection:
    video: HlsVariant
    audio: HlsAudioTrack


def _parse_attribute_list(text: str) -> dict[str, str]:
    parts: list[str] = []
    current: list[str] = []
    quoted = False
    escape = False
    for ch in text:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\" and quoted:
            current.append(ch)
            escape = True
            continue
        if ch == '"':
            quoted = not quoted
            current.append(ch)
            continue
        if ch == "," and not quoted:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())

    result: dict[str, str] = {}
    for part in parts:
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        result[key.strip().upper()] = value
    return result


def _check_protection(text: str) -> None:
    lower = text.lower()
    if "widevine" in lower or "com.apple.streamingkeydelivery" in lower or "fairplay" in lower:
        raise ProtectedStreamError("Protected or encrypted HLS is not supported.")
    for raw in text.splitlines():
        line = raw.strip()
        upper = line.upper()
        if upper.startswith("#EXT-X-KEY:") or upper.startswith("#EXT-X-SESSION-KEY:"):
            attrs = _parse_attribute_list(line.split(":", 1)[1])
            method = attrs.get("METHOD")
            if method is None or method.upper() != "NONE":
                raise ProtectedStreamError("Protected or encrypted HLS is not supported.")


def _as_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_master_playlist(text: str, base_url: str) -> HlsMasterPlaylist:
    _check_protection(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    audio_tracks: list[HlsAudioTrack] = []
    variants: list[HlsVariant] = []

    for line in lines:
        if line.upper().startswith("#EXT-X-MEDIA:"):
            attrs = _parse_attribute_list(line.split(":", 1)[1])
            if attrs.get("TYPE", "").upper() != "AUDIO" or not attrs.get("URI"):
                continue
            audio_tracks.append(
                HlsAudioTrack(
                    uri=urljoin(base_url, attrs["URI"]),
                    group_id=attrs.get("GROUP-ID"),
                    language=(attrs.get("LANGUAGE") or None),
                    name=(attrs.get("NAME") or None),
                    is_default=attrs.get("DEFAULT", "NO").upper() == "YES",
                )
            )

    for idx, line in enumerate(lines):
        if not line.upper().startswith("#EXT-X-STREAM-INF:"):
            continue
        attrs = _parse_attribute_list(line.split(":", 1)[1])
        uri = None
        for candidate in lines[idx + 1 :]:
            if candidate.startswith("#"):
                continue
            uri = candidate
            break
        if not uri:
            continue
        width = height = None
        resolution = attrs.get("RESOLUTION")
        if resolution and "x" in resolution.lower():
            try:
                w, h = resolution.lower().split("x", 1)
                width, height = int(w), int(h)
            except ValueError:
                width = height = None
        codecs = tuple(c.strip() for c in attrs.get("CODECS", "").split(",") if c.strip())
        variants.append(
            HlsVariant(
                uri=urljoin(base_url, uri),
                bandwidth=_as_int(attrs.get("BANDWIDTH")),
                width=width,
                height=height,
                codecs=codecs,
                audio_group=attrs.get("AUDIO"),
            )
        )

    return HlsMasterPlaylist(tuple(variants), tuple(audio_tracks))


def inspect_media_playlist(text: str) -> HlsMediaInfo:
    _check_protection(text)
    duration = 0.0
    for raw in text.splitlines():
        line = raw.strip()
        if line.upper().startswith("#EXTINF:"):
            value = line.split(":", 1)[1].split(",", 1)[0].strip()
            try:
                duration += float(value)
            except ValueError:
                continue
    return HlsMediaInfo(duration_seconds=duration, is_protected=False)


def select_stream(master: HlsMasterPlaylist, max_height: int, preferred_language: str = "en") -> HlsSelection:
    candidates = [v for v in master.variants if v.height is not None and v.height <= max_height]
    if not candidates:
        raise NoUsableStreamError(f"No video rendition is available at or below {max_height}p.")
    video = max(candidates, key=lambda v: (v.height or 0, v.bandwidth or 0))

    tracks = [a for a in master.audio_tracks if video.audio_group is None or a.group_id == video.audio_group]
    if not tracks:
        raise NoUsableStreamError("No usable audio track was found.")

    preferred = preferred_language.lower()
    audio = next(
        (a for a in tracks if (a.language or "").lower() == preferred or (a.language or "").lower().startswith(preferred + "-")),
        None,
    )
    if audio is None:
        audio = next((a for a in tracks if a.is_default), None)
    if audio is None:
        audio = tracks[0]
    return HlsSelection(video=video, audio=audio)
