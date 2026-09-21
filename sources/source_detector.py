from enum import Enum
from urllib.parse import urlparse


class SourceType(str, Enum):
    YOUTUBE = "youtube"
    MINNO = "minno"
    UNKNOWN = "unknown"


def _is_host(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def classify_source(url: str) -> SourceType:
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return SourceType.UNKNOWN
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or parsed.scheme not in {"http", "https"}:
        return SourceType.UNKNOWN
    if host == "youtu.be" or _is_host(host, "youtube.com"):
        return SourceType.YOUTUBE
    if _is_host(host, "gominno.com"):
        return SourceType.MINNO
    return SourceType.UNKNOWN
