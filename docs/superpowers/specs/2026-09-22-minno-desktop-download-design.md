# Minno Desktop Download Integration Design

Date: 2026-09-22
Repository: `jhaago/KidsChurch-Video-Downloader`
Branch: `design/minno-desktop-download`

## Intent

Extend the existing desktop KidsChurch Video Downloader so it can download authorised Minno video streams for offline Kids Church use while preserving the existing YouTube workflow. The first Minno release targets Windows and macOS desktop only. Android is explicitly deferred until the desktop flow is proven.

Success means a user can paste a Minno episode URL, authenticate through a normal Minno login window, queue the episode, download the best available stream up to the selected quality, and receive a presentation-friendly MP4 with visible progress, download speed, and estimated time remaining.

The app must not attempt to defeat DRM or protected encryption. If Minno changes a stream to use encryption/DRM, the app stops and reports that the stream is unsupported.

## Current Application Context

The desktop app is a Tkinter application in `main.py`. It already provides:

- URL preview and queueing
- YouTube download through `yt-dlp`
- FFmpeg-based conversion to presentation-friendly MP4
- MP3/WAV extraction for YouTube
- cancellation
- progress display
- download speed display
- time remaining display
- activity log
- Windows and macOS packaging

Minno support should reuse this existing queue and progress model rather than introduce a parallel UI.

## Source Routing

Introduce an explicit source classification layer before preview/download work begins.

Supported source classes:

- `youtube`
- `minno`
- `unknown`

YouTube URLs continue through the existing `yt-dlp` flow unchanged.

Minno URLs use a dedicated Minno discovery/download flow.

Unknown URLs should receive the existing unsupported/invalid URL treatment rather than being guessed as Minno.

## Desktop User Experience

The main desktop window remains visually consistent with the current application.

Change the input hint from YouTube-only wording to multi-source wording, for example:

> Paste a YouTube or Minno link below

Rename the desktop product heading from `YouTube Downloader` to `KidsChurch Video Downloader` so the UI matches the broader repository purpose.

### First Minno Use

When the user previews or queues a Minno URL and there is no valid Minno session:

1. Launch a dedicated Chromium-based browser window using a Minno-specific persistent profile directory.
2. Navigate to the requested Minno episode.
3. Allow the user to sign in normally on Minno's own page.
4. Observe network requests through the Chrome DevTools Protocol (CDP).
5. Detect the authorised HLS master playlist (`index.m3u8`).
6. Save only the browser profile/session state needed for subsequent Minno use.
7. Return control to the normal preview/queue workflow.

The app must never collect or log the user's Minno password.

### Subsequent Minno Use

If the stored browser session remains valid, Minno preview/download should normally require no login interaction.

If the session has expired, reopen the Minno browser window and let the user authenticate again.

### Minno Account Control

Add a small Minno account control to the desktop app with:

- current Minno session status
- Refresh session
- Sign out

Signing out first closes any downloader-managed Minno browser process, then removes the dedicated Minno browser profile/session data used by the downloader.

## Browser Integration

Do not embed a full browser engine inside Tkinter for the first release.

Use an installed Chromium-family browser launched with a dedicated profile and remote-debugging endpoint, then communicate with it using CDP.

Preferred browser order:

### Windows

1. Google Chrome
2. Microsoft Edge

### macOS

1. Google Chrome
2. another supported Chromium-family browser if available

If no supported browser exists, show a clear user-facing requirement instead of failing silently.

The dedicated Minno browser profile must live in the application's user-data/config area and must not be stored in the repository.

## Network Discovery

The Minno discovery component has one responsibility: obtain an authorised HLS master playlist URL from the user's authenticated browser session.

It should:

- subscribe to browser network events
- navigate to the requested Minno episode
- detect requests whose URL/path indicates an HLS master playlist
- prefer `index.m3u8` or equivalent master-playlist responses
- capture enough request context for FFmpeg to retrieve the same authorised stream if headers or cookies are required
- avoid writing session IDs, signed URLs, cookies, or tokens to the activity log

The discovery component should return a structured result rather than directly performing the download.

Example conceptual result:

```text
MinnoStreamInfo
- page_url
- title
- duration
- master_playlist_url
- request_headers
- available_video_renditions
- available_audio_tracks
- available_subtitles
```

Only fields actually needed by the first release should be implemented.

## HLS Inspection and Safety Gate

Before downloading, inspect both the master playlist and selected media playlists.

The first release supports only unencrypted HLS. Reject the stream if any selected playlist contains an active `#EXT-X-KEY` declaration where `METHOD` is not `NONE`, or otherwise indicates protected/licence-based playback such as SAMPLE-AES, Widevine, FairPlay, or equivalent DRM.

This deliberately treats even technically downloadable AES-encrypted HLS as unsupported in the first release. The downloader will not retrieve or use decryption keys.

This safety gate is mandatory and must run before FFmpeg is asked to download media.

## Quality Selection

Respect the existing desktop quality selector.

For Minno MP4 downloads:

- 1080p means best available video rendition with height <= 1080
- 720p means best available video rendition with height <= 720
- 480p means best available video rendition with height <= 480

If the exact resolution is unavailable, automatically select the best available rendition below the requested ceiling.

Select the English audio track where one is present. If only one audio track exists, use it.

If no usable audio track can be identified, fail the job instead of silently producing a video-only file.

Subtitles are not required for the first release.

## Download Pipeline

For Minno jobs:

1. Discover a fresh authorised master playlist URL.
2. Inspect the master and chosen media playlists.
3. Reject encrypted/DRM-protected streams.
4. Select the requested video quality and audio track.
5. Run FFmpeg to download and mux the stream.
6. Produce a temporary media file.
7. Reuse the existing final MP4 preparation path where needed to guarantee a PowerPoint-friendly H.264/AAC MP4.
8. Move/save the final MP4 through the existing queue/output-folder logic.

The implementation should avoid unnecessary re-encoding when the source is already presentation-compatible, but correctness and compatibility take precedence over speed.

## Output Scope

For the first Minno release:

- MP4 Video: supported
- MP3 Audio: not supported for Minno
- WAV Audio: not supported for Minno

The UI should clearly disable or reject Minno audio-only output selections rather than failing late.

YouTube retains its current MP4/MP3/WAV functionality.

## Progress, Download Speed, and ETA

Minno must use the same desktop activity area already used by YouTube jobs.

During Minno transfer, display:

- percent complete
- download speed
- estimated time remaining
- cancellation state

FFmpeg should be launched with machine-readable `-progress` output.

Percent complete should be based on FFmpeg media output time compared with the known HLS duration. Download speed should be calculated from growth of the temporary output file (or FFmpeg `total_size` when available) over wall-clock time, using a short rolling window. ETA should primarily use remaining media duration divided by FFmpeg's observed processing speed, with the rolling transfer rate available as a fallback when needed. This avoids pretending that media-time progress and network bytes are the same quantity.

The UI should tolerate the first few seconds having no ETA while enough samples are collected.

Example:

```text
Downloading Minno video… 53.8%
DOWNLOAD SPEED     2.9 MB/s
TIME REMAINING     11:42
```

When moving into any final conversion step, the status text should make clear that downloading is complete and conversion is occurring. Speed/ETA may then switch to conversion progress rather than network transfer metrics.

## Queue Integration

Minno and YouTube jobs can coexist in the same queue.

Each queued job should retain its source type so the queue runner can dispatch to the appropriate implementation.

Example conceptual job additions:

```text
source: youtube | minno
url: ...
output_format: ...
resolution: ...
```

The existing queue states remain:

- Queued
- Running
- Complete
- Failed
- Cancelled

## Cancellation

The existing Cancel Current behaviour must work for Minno jobs.

Cancellation may need to terminate either:

- the discovery/browser operation, or
- the active FFmpeg process

Temporary files should be cleaned up after cancellation.

The persistent Minno browser profile should not be removed when an individual download is cancelled.

## Error Handling

Handle the following cases explicitly:

### Session expired

Reopen the Minno browser window and allow the user to sign in again, then retry discovery.

### No stream detected

Report that no playable Minno stream was found for the episode.

### Signed HLS URL expires

Refresh the episode and obtain a fresh stream URL once before failing the job.

### Encryption or DRM detected

Stop before download and report that the stream uses unsupported protected playback.

### Selected quality unavailable

Use the best available quality below the user's requested ceiling.

### Audio unavailable

Fail with a clear message rather than creating a silent file.

### FFmpeg network failure

Fail the job cleanly, retain no misleading completed MP4, and allow a normal retry.

### Browser unavailable

Explain which supported browser is required.

## Security and Privacy

The Minno browser profile is local user data and must be excluded from source control.

Do not log:

- Minno passwords
- cookies
- signed media URLs
- session IDs
- authentication headers

Activity-log messages should use redacted descriptions such as:

```text
Minno stream discovered.
Selected 1920x1080 video + English audio.
Starting Minno download.
```

rather than printing the full HLS URL.

## Code Structure

The current `main.py` is already large, so Minno support should not be implemented as a large block of additional networking/browser code inside that file.

Prefer focused modules such as:

```text
main.py
sources/
    __init__.py
    source_detector.py
    minno.py
    minno_browser.py
    hls.py
```

Responsibilities:

### `source_detector.py`

Classify user URLs as YouTube, Minno, or unknown.

### `minno_browser.py`

Find supported Chromium browser, manage dedicated profile, launch debugging session, navigate/login, observe network traffic, and return the authorised HLS URL/context.

### `hls.py`

Parse playlists, identify renditions/audio, perform encryption/DRM checks, and select the correct rendition.

### `minno.py`

Coordinate discovery, HLS validation, FFmpeg command construction, progress reporting, retry behaviour, and result handling.

### `main.py`

Remain responsible for application UI, queue coordination, shared settings, and dispatching to source handlers.

Exact filenames may change during planning if the existing code structure suggests a cleaner boundary, but the separation of responsibilities should remain.

## Settings

Extend the existing app settings only for user-visible preferences. Do not serialize secrets into `settings.json`.

Minno session state should live inside the dedicated Chromium profile rather than being copied into normal app settings.

## Packaging

Windows and macOS builds must continue bundling or locating FFmpeg as they do today.

The Minno browser integration should rely on an installed supported Chromium browser for the first version rather than bundling Chromium into the installer.

Packaging scripts may need updates if a CDP/WebSocket Python dependency is introduced.

## Testing

### Unit tests

Cover at minimum:

- source URL classification
- HLS master-playlist parsing
- rendition selection for 1080p/720p/480p ceilings
- audio-track selection
- DRM/encryption detection
- signed URL/session-token redaction
- rolling download-speed calculation
- ETA calculation
- Minno output-format validation

### Integration tests

Use recorded/sanitised unencrypted HLS fixtures to test:

- master + video + audio parsing
- FFmpeg command construction
- progress parsing
- cancellation
- retry after an expired stream URL

### Manual end-to-end tests

On Windows first, then macOS:

1. Verify existing YouTube preview/download remains unchanged.
2. Paste a Minno episode URL while signed out.
3. Confirm the dedicated login browser appears.
4. Sign in and verify the session is remembered.
5. Preview/download the same Minno episode that was manually proven on 2026-09-22.
6. Confirm best video up to 1080p plus audio is selected.
7. Confirm percent, speed, and ETA update during download.
8. Confirm cancellation works.
9. Confirm completed MP4 has picture, audio, seeking, and full runtime.
10. Confirm tokens/signed URLs are absent from logs.
11. Confirm a protected/encrypted fixture is rejected before download.
12. Restart the app and verify the Minno session remains usable.

## Deferred Work

Not part of this implementation:

- Android Minno support
- Minno MP3/WAV extraction
- subtitle download
- batch/series Minno download
- bundled Chromium browser
- encrypted/DRM/protected-stream handling
- automatic account credential storage

## Acceptance Criteria

The desktop feature is complete when:

1. Existing YouTube functionality continues to work.
2. A user can paste a Minno episode URL and authenticate through a dedicated browser window.
3. Authentication is remembered locally across app restarts until it expires or the user signs out.
4. The app discovers a valid unencrypted HLS stream without requiring DevTools/manual `.m3u8` copying.
5. The app rejects encrypted/DRM-protected streams.
6. The chosen Minno MP4 uses the best available video at or below the selected quality and includes audio.
7. Progress, download speed, and ETA are visible during the transfer.
8. Cancellation works and cleans temporary files.
9. The final MP4 plays correctly, contains audio, seeks correctly, and is suitable for the existing Kids Church presentation workflow.
10. Authentication tokens, cookies, session IDs, and signed stream URLs are not exposed in normal logs.
