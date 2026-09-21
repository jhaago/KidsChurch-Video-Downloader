# Minno Desktop Download Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-class Minno video downloading to the Windows/macOS desktop app, using a remembered dedicated Minno browser session to discover authorised unencrypted HLS streams and FFmpeg to save presentation-friendly MP4 files with progress, live download speed, and ETA.

**Architecture:** Keep `main.py` responsible for the Tkinter UI and queue, but route URLs through focused source modules. Minno discovery runs in an installed Chromium-family browser using a dedicated profile plus Chrome DevTools Protocol (CDP); HLS parsing/validation is pure Python; FFmpeg performs the actual media transfer/mux and feeds the same desktop progress UI already used by YouTube jobs.

**Tech Stack:** Python 3.12+, Tkinter, standard-library `urllib`, `subprocess`, `dataclasses`, `unittest`, `websocket-client>=1.8,<2`, yt-dlp/Deno for the unchanged YouTube path, bundled FFmpeg/ffprobe for media work, PyInstaller, Inno Setup, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-22-minno-desktop-download-design.md`

## Global Constraints

- First Minno release is Windows/macOS desktop only; Android Minno support is deferred.
- Minno supports MP4 video only in this release; YouTube keeps MP4/MP3/WAV.
- Minno streams must be ordinary unencrypted HLS. Any active `#EXT-X-KEY` / `#EXT-X-SESSION-KEY` with `METHOD` other than `NONE`, SAMPLE-AES, Widevine, FairPlay, or equivalent protected playback is rejected before FFmpeg transfer.
- The app must not retrieve or use decryption keys.
- Minno authentication happens on Minno's own page in a dedicated Chromium profile; credentials are never collected by the app.
- Do not log passwords, cookies, auth headers, signed HLS URLs, or session IDs.
- Minno browser session state lives in the application's user-data directory, not `settings.json` and not the repository.
- The first version relies on an installed Chromium-family browser; do not bundle Chromium.
- Preserve the existing desktop queue states and current YouTube download behaviour.
- Reuse the existing desktop Download Speed and Time Remaining fields for Minno.
- Windows support remains Windows 10/11 x64 with Python 3.12+ for source builds; macOS support remains macOS 12+ with Python 3.12+ and Node 22+ for source builds.

## Review Focus

- A Minno URL with a signed query string must never appear verbatim in logs or exception text shown to the user; Task 3 tests redaction and Task 7 routes all Minno log output through it.
- A valid master playlist with no rendition at or below the selected ceiling must fail clearly instead of silently selecting a higher quality; Task 2 tests this boundary.
- An audio group containing several languages/default flags must consistently prefer English, then DEFAULT, then the first usable track; Task 2 pins the ordering.
- Closing/cancelling while the login browser is open must terminate only the downloader-managed browser process and retain the persistent profile; Task 5 tests cancellation state and Task 7 manually verifies it.
- A stale signed HLS URL returning 401/403 must trigger exactly one fresh discovery attempt, then fail cleanly without an infinite retry loop; Task 6 tests the retry count.

---

## File Structure

Create these focused modules instead of expanding `main.py` with browser/HLS internals:

```text
sources/
    __init__.py
    source_detector.py   # YouTube / Minno / unknown classification
    hls.py               # playlist parsing, protection gate, rendition/audio selection
    progress.py          # redaction + Minno FFmpeg progress/speed/ETA estimation
    cdp.py               # small synchronous CDP websocket client
    minno_browser.py     # Chromium discovery/profile/session lifecycle
    minno.py             # Minno preview/preparation/download coordinator

tests/
    fixtures/
        minno_master.m3u8
        minno_video.m3u8
        minno_audio.m3u8
        protected_aes128.m3u8
        protected_sample_aes.m3u8
    test_source_detector.py
    test_hls.py
    test_progress.py
    test_cdp.py
    test_minno_browser.py
    test_minno.py
```

Keep tests on built-in `unittest` so test support does not add a runtime dependency. Add only `websocket-client>=1.8,<2` to `requirements.txt` for CDP.

---

### Task 1: Add source classification and establish the test harness

**Files:**
- Create: `sources/__init__.py`
- Create: `sources/source_detector.py`
- Create: `tests/__init__.py`
- Create: `tests/test_source_detector.py`

**Interfaces:**
- Produces: `SourceType` enum with values `YOUTUBE`, `MINNO`, `UNKNOWN`.
- Produces: `classify_source(url: str) -> SourceType`.
- Later tasks consume the enum/string value when previewing and queueing jobs.

- [ ] **Step 1: Write failing source-classification tests**

```python
import unittest
from sources.source_detector import SourceType, classify_source


class SourceDetectorTests(unittest.TestCase):
    def test_youtube_hosts(self):
        for url in (
            "https://www.youtube.com/watch?v=abc",
            "https://youtu.be/abc",
            "https://music.youtube.com/watch?v=abc",
        ):
            with self.subTest(url=url):
                self.assertEqual(SourceType.YOUTUBE, classify_source(url))

    def test_minno_hosts(self):
        for url in (
            "https://gominno.com/watch/example",
            "https://kids.gominno.com/example",
            "https://app.gominno.com/watch/example?foo=bar",
        ):
            with self.subTest(url=url):
                self.assertEqual(SourceType.MINNO, classify_source(url))

    def test_lookalike_domains_are_unknown(self):
        for url in (
            "https://gominno.com.evil.example/watch/1",
            "https://notyoutube.com/watch?v=1",
            "not a url",
            "",
        ):
            with self.subTest(url=url):
                self.assertEqual(SourceType.UNKNOWN, classify_source(url))
```

- [ ] **Step 2: Run the test and verify it fails because the module does not exist**

Run:

```bash
python -m unittest tests.test_source_detector -v
```

Expected: import failure for `sources.source_detector`.

- [ ] **Step 3: Implement strict host-based classification**

Use `urllib.parse.urlparse`; lowercase/strip the hostname; accept `youtube.com` and subdomains, `youtu.be`, and `gominno.com` plus subdomains. Do not classify by substring search.

```python
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
```

- [ ] **Step 4: Run the tests**

Run:

```bash
python -m unittest tests.test_source_detector -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add sources tests/test_source_detector.py tests/__init__.py
git commit -m "feat: classify YouTube and Minno sources"
```

---

### Task 2: Implement HLS parsing, quality/audio selection, duration, and the protection gate

**Files:**
- Create: `sources/hls.py`
- Create: `tests/test_hls.py`
- Create: `tests/fixtures/minno_master.m3u8`
- Create: `tests/fixtures/minno_video.m3u8`
- Create: `tests/fixtures/minno_audio.m3u8`
- Create: `tests/fixtures/protected_aes128.m3u8`
- Create: `tests/fixtures/protected_sample_aes.m3u8`

**Interfaces:**
- Produces immutable dataclasses `HlsVariant`, `HlsAudioTrack`, `HlsMasterPlaylist`, `HlsMediaInfo`, `HlsSelection`.
- Produces `parse_master_playlist(text: str, base_url: str) -> HlsMasterPlaylist`.
- Produces `inspect_media_playlist(text: str) -> HlsMediaInfo`.
- Produces `select_stream(master: HlsMasterPlaylist, max_height: int, preferred_language: str = "en") -> HlsSelection`.
- Raises `ProtectedStreamError` for any active encryption/protection.
- Raises `NoUsableStreamError` when no valid video/audio combination exists.

- [ ] **Step 1: Record sanitised fixtures matching the proven Minno shape**

Use a master fixture with 360/540/720/1080 variants and a separate audio group. URLs must use `https://media.example.invalid/...` with no real tokens. Include quoted CODECS attributes containing commas so the attribute parser is exercised.

Example core lines:

```text
#EXTM3U
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="English",LANGUAGE="en",DEFAULT=YES,AUTOSELECT=YES,URI="audio300_134826.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=640x360,CODECS="avc1.64001e,mp4a.40.2",AUDIO="audio"
video_1000000.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=3499968,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",AUDIO="audio"
video_3499968.m3u8
```

Media fixtures should contain `#EXT-X-PLAYLIST-TYPE:VOD`, `#EXT-X-MAP`, multiple `#EXTINF` entries, and no keys. Protected fixtures must contain AES-128 and SAMPLE-AES key lines respectively.

- [ ] **Step 2: Write failing parser/selection/protection tests**

Cover:

```python
self.assertEqual(4, len(master.variants))
self.assertEqual(1080, select_stream(master, 1080).video.height)
self.assertEqual(720, select_stream(master, 720).video.height)
self.assertEqual(540, select_stream(master, 600).video.height)
self.assertEqual("en", select_stream(master, 1080).audio.language)
self.assertAlmostEqual(6.0, inspect_media_playlist(video_text).duration_seconds)
```

Also assert:

- 480p ceiling with only 540p+ variants raises `NoUsableStreamError`.
- English is preferred even when another language is marked DEFAULT.
- If English is absent, DEFAULT is preferred.
- If neither language nor DEFAULT resolves, first usable audio track is selected.
- Master playlist `#EXT-X-SESSION-KEY:METHOD=AES-128` is rejected.
- Media playlist `#EXT-X-KEY:METHOD=AES-128` is rejected.
- SAMPLE-AES, FairPlay-style `KEYFORMAT="com.apple.streamingkeydelivery"`, or strings containing Widevine are rejected.
- `METHOD=NONE` is allowed.

- [ ] **Step 3: Run tests and verify failure**

```bash
python -m unittest tests.test_hls -v
```

Expected: module/functions missing.

- [ ] **Step 4: Implement a small HLS parser with quoted-attribute support**

Do not add a general HLS dependency. Implement `_parse_attribute_list()` with a character scanner that splits commas only when outside quotes, then use `urljoin(base_url, relative_uri)` for all media URLs.

Dataclass shape:

```python
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
class HlsSelection:
    video: HlsVariant
    audio: HlsAudioTrack
```

Protection check rule: if an `EXT-X-KEY` or `EXT-X-SESSION-KEY` has `METHOD` missing or anything except `NONE`, raise `ProtectedStreamError`; also reject SAMPLE-AES/Widevine/FairPlay markers case-insensitively.

- [ ] **Step 5: Run the tests**

```bash
python -m unittest tests.test_hls -v
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add sources/hls.py tests/test_hls.py tests/fixtures
git commit -m "feat: parse and validate Minno HLS streams"
```

---

### Task 3: Add sensitive-data redaction and stable FFmpeg transfer metrics

**Files:**
- Create: `sources/progress.py`
- Create: `tests/test_progress.py`

**Interfaces:**
- Produces `redact_sensitive(text: str) -> str`.
- Produces `format_bytes_per_second(value: float | None) -> str`.
- Produces `format_eta(seconds: float | None) -> str`.
- Produces `TransferSnapshot(percent: float, speed_bps: float | None, eta_seconds: float | None)`.
- Produces `TransferProgressEstimator(duration_seconds: float, window_seconds: float = 8.0)` with `update(wall_time: float, media_seconds: float, total_size_bytes: int | None) -> TransferSnapshot`.

- [ ] **Step 1: Write failing tests**

Test that a line such as:

```text
https://cdn.example.invalid/index.m3u8?sessionId=abc123&token=secret
```

becomes a safe string that keeps the host/path but replaces the query with `<redacted>`. Also redact values following header names `Cookie:`, `Authorization:`, `X-Playback-Token:` and obvious `sessionId=`/`token=` fragments appearing outside a URL.

For progress, feed samples:

```python
est = TransferProgressEstimator(100.0, window_seconds=8.0)
first = est.update(0.0, 0.0, 0)
second = est.update(5.0, 20.0, 10_000_000)
```

Assert approximately 20% progress, ~2,000,000 B/s, and ~20 seconds ETA. Add a test where `total_size_bytes` is absent: percent and ETA still work while speed is `None`. Add a regression test that decreasing/corrupt media times do not create a negative ETA.

- [ ] **Step 2: Run and confirm failure**

```bash
python -m unittest tests.test_progress -v
```

- [ ] **Step 3: Implement rolling-window estimation**

Keep a `deque` of `(wall_time, media_seconds, total_size_bytes)` samples and discard samples older than `window_seconds`. Compute network/output speed from byte delta over wall delta. Compute processing rate from media-time delta over wall delta; ETA = remaining media seconds / processing rate. Do not emit speed/ETA until at least two valid samples exist.

- [ ] **Step 4: Run tests**

```bash
python -m unittest tests.test_progress -v
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add sources/progress.py tests/test_progress.py
git commit -m "feat: add safe Minno progress and redaction helpers"
```

---

### Task 4: Implement a minimal synchronous CDP client

**Files:**
- Create: `sources/cdp.py`
- Create: `tests/test_cdp.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces `CdpConnection(ws_url: str, websocket_factory=...)`.
- Produces `call(method: str, params: dict | None = None, timeout: float = 10.0) -> dict`.
- Produces `iter_events(timeout: float = 0.25)` yielding `(method: str, params: dict)`.
- Produces `close()`.
- Later `minno_browser.py` owns browser lifecycle and uses this class only for protocol messages.

- [ ] **Step 1: Add the runtime dependency**

Append exactly:

```text
websocket-client>=1.8,<2
```

to `requirements.txt`.

- [ ] **Step 2: Write failing protocol tests with a fake websocket**

The fake websocket should queue JSON strings. Assert that `call("Network.enable")` sends `{"id": 1, "method": "Network.enable", "params": {}}`, ignores unrelated events until response ID 1 arrives, and preserves those events for `iter_events()`. Add tests for protocol error responses and timeouts.

- [ ] **Step 3: Run and verify failure**

```bash
python -m unittest tests.test_cdp -v
```

- [ ] **Step 4: Implement `CdpConnection`**

Use `websocket.create_connection(ws_url, timeout=..., suppress_origin=True)`. Maintain a monotonically increasing request ID and an internal event queue. Never print received payloads because CDP network events may contain signed URLs or headers.

- [ ] **Step 5: Run tests**

```bash
python -m unittest tests.test_cdp -v
```

- [ ] **Step 6: Run the entire suite**

```bash
python -m unittest discover -s tests -v
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt sources/cdp.py tests/test_cdp.py
git commit -m "feat: add Chromium DevTools protocol client"
```

---

### Task 5: Implement the dedicated Minno Chromium profile and stream discovery

**Files:**
- Create: `sources/minno_browser.py`
- Create: `tests/test_minno_browser.py`

**Interfaces:**
- Produces `BrowserInfo(name: str, executable: Path)`.
- Produces `MinnoDiscovery(page_url: str, title: str, master_playlist_url: str, request_headers: dict[str, str])`.
- Produces `find_supported_browser(platform_name: str | None = None, environ: Mapping[str, str] | None = None) -> BrowserInfo | None`.
- Produces `MinnoBrowserSession(profile_dir: Path, browser: BrowserInfo | None = None)` with:
  - `discover(page_url, cancel_requested, status_callback, timeout_seconds=180) -> MinnoDiscovery`
  - `open_account_window(url="https://kids.gominno.com/") -> subprocess.Popen`
  - `close_managed_browser() -> None`
  - `sign_out() -> None`
  - `profile_exists() -> bool`

- [ ] **Step 1: Write failing browser-locator and lifecycle tests**

Inject environment/path checks rather than depending on the test machine. Cover Windows priority Chrome then Edge, macOS Chrome path, no-browser error, profile existence, and `sign_out()` refusing to delete the profile until the managed process has been closed.

Add discovery tests with a fake CDP object that emits:

```text
Network.requestWillBeSent -> https://media.example.invalid/video_3499968.m3u8
Network.requestWillBeSent -> https://media.example.invalid/index.m3u8?sessionId=secret
```

The fake HTTP probe for the second URL returns text containing `#EXT-X-STREAM-INF`, so discovery must select it as the master playlist rather than the rendition playlist. Assert that only safe headers (`User-Agent`, `Referer`, and `Origin` when present) are returned; cookies/auth headers must not be persisted in the result.

Add a cancellation test where `cancel_requested()` flips true before discovery finishes; assert browser close is requested but `profile_dir` remains.

- [ ] **Step 2: Run and verify failure**

```bash
python -m unittest tests.test_minno_browser -v
```

- [ ] **Step 3: Implement browser discovery paths**

Windows candidates, in order:

```text
%PROGRAMFILES%\Google\Chrome\Application\chrome.exe
%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe
%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe
%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe
%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe
```

macOS candidates, in order:

```text
/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge
```

- [ ] **Step 4: Implement isolated Chromium launch**

Reserve a localhost port using a temporary socket, then launch the selected browser with:

```text
--remote-debugging-address=127.0.0.1
--remote-debugging-port=<port>
--user-data-dir=<profile_dir>
--no-first-run
--no-default-browser-check
--autoplay-policy=no-user-gesture-required
--new-window
<page_url>
```

Never attach to the user's normal Chrome profile. Poll `http://127.0.0.1:<port>/json/list` until the Minno page target appears, then connect to its `webSocketDebuggerUrl` with `CdpConnection`.

- [ ] **Step 5: Implement safe stream discovery**

Enable `Network`, `Page`, and `Runtime`. Watch requests ending in/containing `.m3u8`; probe each candidate with `urllib.request` using only safe copied headers. A master is one whose body includes `#EXT-X-STREAM-INF`. Obtain the title with `Runtime.evaluate` using `document.querySelector('meta[property="og:title"]')?.content || document.title`.

Every few seconds attempt the generic, non-site-specific playback nudge:

```javascript
(() => { const v = document.querySelector('video'); if (v) { v.muted = true; v.play().catch(() => {}); } })()
```

After 12 seconds without a playlist, call `status_callback("Sign in to Minno and press Play in the browser window…")`; continue waiting up to 180 seconds. This is the only manual interaction fallback—no DevTools or copying URLs.

- [ ] **Step 6: Run tests**

```bash
python -m unittest tests.test_minno_browser -v
```

- [ ] **Step 7: Commit**

```bash
git add sources/minno_browser.py tests/test_minno_browser.py
git commit -m "feat: discover Minno HLS through dedicated browser session"
```

---

### Task 6: Build the Minno coordinator, FFmpeg command, retry logic, and MP4 compatibility decision

**Files:**
- Create: `sources/minno.py`
- Create: `tests/test_minno.py`

**Interfaces:**
- Consumes: `MinnoBrowserSession`, HLS parser/selector, transfer estimator, FFmpeg executable path.
- Produces `MinnoPreview(title: str, duration: float, max_height: int, source: str = "Minno")`.
- Produces `PreparedMinnoStream(title, duration, video_url, audio_url, headers, video_codec, audio_codec, width, height)`.
- Produces `validate_output_format(output_format: str) -> None` raising `MinnoUnsupportedFormatError` unless `MP4 Video`.
- Produces `MinnoClient.preview(page_url, max_height=1080, ...) -> MinnoPreview`.
- Produces `MinnoClient.prepare(page_url, max_height, ...) -> PreparedMinnoStream`.
- Produces `MinnoClient.download(page_url, max_height, ffmpeg, output_path, cancel_requested, progress_callback, process_started_callback) -> Path`.

- [ ] **Step 1: Write failing coordinator tests**

Use dependency injection for discovery, HTTP fetch, and process runner. Cover:

- MP3/WAV rejected immediately.
- Preview chooses max advertised height and duration from the selected media playlist.
- `prepare(..., 720)` selects 720p even when 1080p exists.
- Protection in master, video, or audio playlist raises before any FFmpeg process is launched.
- No audio raises `NoUsableStreamError`.
- FFmpeg command uses two direct HLS inputs (selected video and audio) with explicit maps `0:v:0` and `1:a:0`, `-progress pipe:1`, `-nostats` and no signed URL in a log callback.
- If source codecs include H.264/`avc1` and AAC/`mp4a`, use `-c copy -movflags +faststart` for the transfer output.
- If codecs are unknown/incompatible, produce a temporary `.mkv` via stream copy and report `needs_conversion=True` so `main.py` can use its existing H.264/AAC conversion routine.
- One simulated FFmpeg 403 causes one re-discovery and retry; a second 403 fails. Assert discovery count == 2.
- Cancellation terminates the active process and raises a cancellation error.

- [ ] **Step 2: Run and verify failure**

```bash
python -m unittest tests.test_minno -v
```

- [ ] **Step 3: Implement HTTP playlist fetching**

Use `urllib.request.Request` with the safe request headers supplied by `MinnoDiscovery`. Set a conservative timeout such as 20 seconds. Never include the URL in raised user-facing errors; convert failures to messages like `Minno playlist request failed with HTTP 403.`

- [ ] **Step 4: Implement `prepare()`**

Sequence exactly:

```text
discover fresh master URL
fetch master
protection check master
parse master
select video/audio by ceiling
fetch selected video media playlist
protection check video
fetch selected audio media playlist
protection check audio
calculate duration from video playlist
return PreparedMinnoStream
```

- [ ] **Step 5: Implement FFmpeg transfer/progress parsing**

Run FFmpeg with stderr redirected to stdout so errors and `-progress` records can be handled in one loop. Parse key/value records including `out_time_us` (fallback `out_time_ms`), `total_size`, and `progress=continue/end`. Feed samples to `TransferProgressEstimator` using `time.monotonic()` and emit a snapshot callback.

Do not forward raw FFmpeg lines to the UI because they can contain signed URLs. Convert them to safe messages such as `Starting Minno download`, `Minno transfer failed with HTTP 403`, and `Minno transfer complete`.

- [ ] **Step 6: Implement single stale-URL retry**

Classify output containing `401`, `403`, `Unauthorized`, or `Forbidden` as an authentication/expiry failure. Delete the failed temporary file, re-run `prepare()` once to obtain fresh signed URLs, then retry. Any second failure propagates.

- [ ] **Step 7: Run tests and full suite**

```bash
python -m unittest tests.test_minno -v
python -m unittest discover -s tests -v
```

- [ ] **Step 8: Commit**

```bash
git add sources/minno.py tests/test_minno.py
git commit -m "feat: download validated Minno HLS with FFmpeg"
```

---

### Task 7: Integrate Minno into the desktop UI, queue, cancellation, account controls, speed, and ETA

**Files:**
- Modify: `main.py`

**Interfaces:**
- Consumes: `classify_source`, `MinnoClient`, `MinnoBrowserSession`, `redact_sensitive`.
- Existing queue event model remains the only way worker threads mutate visible progress/status.

- [ ] **Step 1: Extract the shared application-data folder helper**

Replace the duplicated folder construction in `settings_file()` with:

```python
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


def settings_file() -> Path:
    return app_data_dir() / "settings.json"
```

Create the persistent Minno profile at `app_data_dir() / "minno-browser-profile"`.

- [ ] **Step 2: Rename the desktop UI and bump the desktop version**

Set:

```python
APP_NAME = "KidsChurch Video Downloader"
APP_VERSION = "0.7.0"
```

Change helper text to `Paste a YouTube or Minno link below`. Keep the settings directory unchanged so existing user preferences survive.

- [ ] **Step 3: Construct Minno services once per app instance**

In `DownloaderApp.__init__`, create one `MinnoBrowserSession` and one `MinnoClient`. Add a `minno_session_var` string such as `Minno: not signed in`, `Minno: saved session`, `Minno: ready`, or `Minno: sign-in required`. Do not put secrets into settings.

- [ ] **Step 4: Add the Minno Account control**

Add a small `Minno Account` secondary button in the header. Clicking it opens a Tkinter `Toplevel` containing the current session status and two actions:

```text
Refresh / Sign in
Sign out
```

Refresh launches the dedicated profile at `https://kids.gominno.com/` and tells the user to close that browser window when login is complete. Sign out calls `close_managed_browser()` first, then `sign_out()`, then updates the status to `Minno: not signed in`.

- [ ] **Step 5: Route preview by source**

Change `_preview_worker` to classify the URL. YouTube continues calling existing `_fetch_metadata`. Minno calls `MinnoClient.preview`; translate the result into the existing preview shape:

```python
{
    "title": preview.title,
    "duration": preview.duration,
    "source": "Minno",
    "max_height": preview.max_height,
}
```

Unknown URLs raise `Unsupported URL. Paste a YouTube or Minno link.`. Preview detail text for Minno should include `Minno • 1:30:00 • up to 1080p` rather than yt-dlp-specific metadata.

- [ ] **Step 6: Validate format before queueing and store source type on the job**

At `_queue_current_url`, classify once and store:

```python
"source": source.value,
```

If source is Minno and `output_format_var` is not `MP4 Video`, show `Minno downloads currently support MP4 Video only.` and do not queue. Unknown URLs are rejected before a job is created.

- [ ] **Step 7: Dispatch downloads without changing the YouTube path**

Split the existing `_download_job` body into `_download_youtube_job(job, tools)` with behaviour unchanged, then make `_download_job` dispatch:

```python
if job["source"] == SourceType.MINNO.value:
    return self._download_minno_job(job, tools)
return self._download_youtube_job(job, tools)
```

The Minno method creates a temporary directory, selects a unique final filename, calls `MinnoClient.download`, and receives progress snapshots via callback.

- [ ] **Step 8: Feed Minno progress into the existing speed/ETA UI**

For each `TransferSnapshot`, queue an event carrying percent, formatted speed, formatted ETA, and text such as:

```text
Downloading Minno video… 53.8%  •  2.9 MB/s  •  ETA 11:42
```

Update `_process_events`/existing `job_progress` handling so the dedicated `speed_var` and `eta_var` fields receive explicit values for Minno rather than relying only on the current regex used for yt-dlp messages. Preserve the current YouTube parsing path.

- [ ] **Step 9: Reuse the existing conversion routine only when required**

If the Minno result is already H.264/AAC MP4, move it directly to the final output path after a faststart copy has completed. If `needs_conversion=True`, show `Downloading complete • converting to PowerPoint-friendly MP4…`, clear network speed/ETA, and call the existing `_convert_to_mp4` routine with the known duration.

- [ ] **Step 10: Wire cancellation through browser discovery and FFmpeg**

Pass `lambda: self.operation_cancel_requested` into Minno methods. When FFmpeg starts, `process_started_callback` assigns the process to `self.active_process`, allowing the existing terminate logic to work. Browser discovery checks the cancellation callback and closes only its managed browser process. `Cancel Current` must not delete `minno-browser-profile`.

- [ ] **Step 11: Ensure all Minno logging is sanitised**

Never log `job['url']` verbatim for Minno because the page URL itself may eventually carry transient parameters. Use safe messages such as:

```text
Starting MP4 Video: Minno episode
Minno stream discovered.
Selected 1920x1080 video + English audio.
Starting Minno download.
```

Route any Minno exception text through `redact_sensitive()` before placing it on the event queue.

- [ ] **Step 12: Run syntax and regression tests**

```bash
python -m py_compile main.py sources/*.py
python -m unittest discover -s tests -v
```

Expected: pass, with no changes under `android/`.

- [ ] **Step 13: Manual desktop smoke test from source**

Launch:

```bash
python main.py
```

Verify the existing YouTube Preview → Add to Queue → MP4 path still shows live speed and ETA. Then use a sanitised/controlled fixture or real authorised Minno page to confirm the Minno login window appears and cancellation closes it cleanly.

- [ ] **Step 14: Commit**

```bash
git add main.py
git commit -m "feat: integrate Minno into desktop queue and UI"
```

---

### Task 8: Add automated desktop tests to CI before packaging

**Files:**
- Modify: `.github/workflows/windows-build.yml`
- Modify: `.github/workflows/macos-build.yml`

**Interfaces:**
- No product interface changes.
- Build jobs must fail before PyInstaller packaging when unit tests fail.

- [ ] **Step 1: Add unit-test steps after dependency install and before packaging**

Windows:

```yaml
- name: Run desktop unit tests
  shell: pwsh
  run: python -m unittest discover -s tests -v
```

macOS: `build_macos.sh` currently installs dependencies internally, so either add a dependency-install/test step before invoking it or add the test invocation inside `build_macos.sh`. Prefer the workflow doing:

```yaml
- name: Install desktop Python dependencies
  run: python3 -m pip install -r requirements.txt

- name: Run desktop unit tests
  run: python3 -m unittest discover -s tests -v
```

and let `build_macos.sh` safely reinstall requirements afterward.

- [ ] **Step 2: Verify workflow syntax visually and run local suite**

```bash
python -m unittest discover -s tests -v
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/windows-build.yml .github/workflows/macos-build.yml
git commit -m "ci: run desktop tests before packaging"
```

---

### Task 9: Package V0.7.0 as KidsChurch Video Downloader without breaking the existing settings path

**Files:**
- Modify: `build_windows.bat`
- Modify: `make_installer.bat`
- Modify: `installer.iss`
- Modify: `build_macos.sh`
- Modify: `.github/workflows/windows-build.yml`
- Modify: `.github/workflows/macos-build.yml`
- Modify: `THIRD_PARTY_NOTICES.md`

**Interfaces:**
- Desktop visible app name: `KidsChurch Video Downloader`.
- Desktop version: `0.7.0`.
- Keep `AppId={{8B13D9C5-7E09-4C4F-A84E-CCF8C18AF497}` so Windows upgrades the existing install rather than creating an unrelated application.
- Keep the persistent settings path `KidsChurchVideoDownloader`.

- [ ] **Step 1: Rename Windows build output consistently**

Use PyInstaller name `KidsChurchVideoDownloader`; package folder `dist\KidsChurchVideoDownloader`; executable `KidsChurchVideoDownloader.exe`; installer output `KidsChurchVideoDownloader_Setup_v0.7.0.exe`. Update `make_installer.bat` checks and bundled-tool copy paths accordingly.

- [ ] **Step 2: Update Inno Setup while preserving upgrade identity**

Set:

```text
MyAppName = KidsChurch Video Downloader
MyAppVersion = 0.7.0
MyAppExeName = KidsChurchVideoDownloader.exe
DefaultDirName = {autopf}\KidsChurch Video Downloader
OutputBaseFilename = KidsChurchVideoDownloader_Setup_v0.7.0
```

Keep the existing AppId. Add an `[InstallDelete]` entry for old `YouTubeDownloader.exe`/old shortcuts so upgrades do not leave two launchers.

- [ ] **Step 3: Rename the macOS app and artifacts**

Set `APP_NAME="KidsChurch Video Downloader"` and use `KidsChurchVideoDownloader-macOS-$ARCH_LABEL-v0.7.0.zip/.dmg`. Preserve the existing bundle identifier for upgrade continuity unless macOS packaging proves it cannot; do not silently invent a new identity.

- [ ] **Step 4: Update workflow artifact verification paths/names**

Windows artifacts:

```text
KidsChurchVideoDownloader-Windows-Installer
KidsChurchVideoDownloader-Windows-Portable
```

macOS artifacts:

```text
KidsChurchVideoDownloader-macOS-Intel
KidsChurchVideoDownloader-macOS-AppleSilicon
```

Update path assertions to V0.7.0 names.

- [ ] **Step 5: Update third-party notices for `websocket-client`**

Add a section explaining that the Python `websocket-client` package is used only for local CDP communication with the downloader-managed Chromium instance and include its project/license information. Change the document heading copy from YouTube-only wording to KidsChurch Video Downloader.

- [ ] **Step 6: Run the test suite and local packaging syntax checks**

```bash
python -m py_compile main.py sources/*.py
python -m unittest discover -s tests -v
```

On Windows, run `build_windows.bat` and `make_installer.bat`; on macOS run `./build_macos.sh`.

- [ ] **Step 7: Commit**

```bash
git add build_windows.bat make_installer.bat installer.iss build_macos.sh .github/workflows/windows-build.yml .github/workflows/macos-build.yml THIRD_PARTY_NOTICES.md
git commit -m "build: package KidsChurch Video Downloader v0.7.0"
```

---

### Task 10: Update documentation for multi-source desktop use

**Files:**
- Modify: `README.md`

**Interfaces:**
- Documentation must distinguish desktop V0.7.0 from Android V0.3, which remains YouTube-only.

- [ ] **Step 1: Rewrite the top-level description**

Use wording equivalent to:

```text
# KidsChurch Video Downloader

A cross-platform media downloader for authorised Kids Church use. Desktop V0.7.0 supports YouTube plus authorised unencrypted Minno HLS video; Android V0.3 remains YouTube-only.
```

- [ ] **Step 2: Document Minno desktop workflow**

Explain: paste Minno URL → dedicated login browser opens if needed → sign in on Minno → press Play if the app asks → app discovers the HLS stream → selected quality downloads to MP4. State explicitly that Minno MP3/WAV are not supported in V0.7.0 and encrypted/DRM streams are refused.

- [ ] **Step 3: Document account/session behaviour and privacy**

State that Minno uses a separate persistent Chromium profile under the app's local user-data directory, does not import the user's ordinary Chrome profile, does not store the Minno password, and `Sign out` deletes that dedicated profile after closing the downloader-managed browser.

- [ ] **Step 4: Correct the existing Authorised use section**

Replace the old claim that the app does not implement account-login automation/browser integration with accurate wording: it does not circumvent DRM or import normal browser cookies, but desktop Minno support can launch a dedicated browser session for the user to authenticate directly with Minno.

- [ ] **Step 5: Update install/build artifact names and V0.7.0 instructions**

Keep Android instructions and V0.3 artifact name unchanged.

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: document Minno desktop downloads"
```

---

### Task 11: Perform end-to-end Windows verification with the proven Minno episode

**Files:**
- No source changes unless a defect is found; defects return to the owning task and receive a regression test before fixing.

**Interfaces:**
- This is the acceptance gate before macOS testing.

- [ ] **Step 1: Run automated verification**

```powershell
python -m py_compile main.py sources\*.py
python -m unittest discover -s tests -v
```

Expected: all pass.

- [ ] **Step 2: Build/install V0.7.0 on Windows**

Run `build_windows.bat`, then `make_installer.bat`, install the generated V0.7.0 installer, and launch it from the Start menu.

- [ ] **Step 3: Regress YouTube**

Download one short authorised YouTube MP4 and confirm preview, queue, progress, Download Speed, Time Remaining, cancellation, conversion and Open Folder still behave as V0.6.5 did.

- [ ] **Step 4: Test first-time Minno authentication**

Ensure no dedicated Minno profile exists (use the app's Sign out action rather than manual deletion). Paste the same authorised Minno episode manually proven on 2026-09-22. Confirm the dedicated browser appears; sign in on Minno; press Play only if prompted by the downloader. Confirm no DevTools/manual `.m3u8` copying is required.

- [ ] **Step 5: Verify stream/quality/output**

Choose 1080p and download. Confirm UI displays moving percent, live speed, and ETA; output contains 1920x1080 when that rendition remains available, audio is present, seeking works, and runtime matches the ~1h30 episode.

Use ffprobe if needed:

```powershell
ffprobe -v error -show_entries stream=codec_name,width,height -show_entries format=duration -of json "<downloaded file>"
```

Expected video codec H.264 (`h264`), audio AAC, 1920x1080 where still offered, and full duration.

- [ ] **Step 6: Verify remembered session**

Close/reopen the app, paste the episode again, and verify Minno can discover it using the saved dedicated profile without re-entering credentials unless Minno itself expired the session.

- [ ] **Step 7: Verify cancellation during both phases**

Cancel once while browser discovery/login is waiting and once during FFmpeg transfer. Confirm queue state becomes Cancelled, temporary media is removed, and the dedicated Minno profile remains available.

- [ ] **Step 8: Verify privacy/logging**

Inspect the full Activity log. Search visually for `sessionId=`, `token=`, `.m3u8?`, `Cookie:`, and `Authorization:`. None may expose values or signed URLs.

- [ ] **Step 9: Verify account Sign out**

Use Minno Account → Sign out. Confirm any managed browser closes, profile directory is removed, and the next Minno operation requests sign-in.

- [ ] **Step 10: Record acceptance result in the PR/branch notes**

Record Windows browser/version tested and whether playback required a manual Play click. Do not record credentials, cookies, or signed URLs.

---

### Task 12: Perform macOS package and Minno verification

**Files:**
- No source changes unless a defect is found; defects require a regression test.

**Interfaces:**
- Validate both macOS packaging architectures in CI; manual Minno test can be performed on the Mac hardware available to the project.

- [ ] **Step 1: Confirm GitHub Actions produces both macOS artifacts**

Expected green jobs: Intel and AppleSilicon. Each app must pass codesign verification and contain the bundled yt-dlp, Deno, FFmpeg and ffprobe executables plus Python websocket dependency inside the PyInstaller bundle.

- [ ] **Step 2: Install the appropriate DMG and run YouTube regression**

Confirm existing YouTube MP4 download still works with speed/ETA.

- [ ] **Step 3: Test Minno browser discovery**

With Google Chrome installed, paste the same authorised Minno episode. Confirm the dedicated profile opens, login persists, stream discovery succeeds, and the browser can be closed by the app after discovery.

- [ ] **Step 4: Download and validate the final MP4**

Confirm picture/audio/seeking/runtime and speed/ETA behaviour match Windows.

- [ ] **Step 5: Run final automated suite on the branch**

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile main.py sources/*.py
```

Expected: pass.

- [ ] **Step 6: Commit only if verification required a documented fix**

If no changes were needed, do not create an empty commit. If a defect was found, return to its owning task, add a regression test, implement the fix, rerun the suite, then commit with a specific message.

---

## Plan Self-Review Notes

- **Spec coverage:** source routing, remembered login/profile, account controls, CDP discovery, unencrypted-HLS safety gate, quality/audio selection, MP4-only Minno scope, progress/speed/ETA, queue/cancellation, stale-URL retry, privacy/redaction, Windows/macOS packaging, documentation, and manual acceptance are each assigned to explicit tasks.
- **Placeholder scan:** no implementation step relies on TBD/TODO language; browser paths, protocol behaviour, key function signatures, tests, build names and manual verification steps are specified.
- **Type consistency:** `SourceType`, HLS dataclasses, `MinnoDiscovery`, `PreparedMinnoStream`, `TransferSnapshot`, `MinnoBrowserSession`, and `MinnoClient` names are used consistently across producer/consumer tasks.
- **Review Focus coverage:** all five high-risk cases listed above have an owning automated or explicit manual test.
