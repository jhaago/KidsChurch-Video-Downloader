# YouTube Downloader V0.5

A Windows desktop app for downloading **authorised** YouTube media as PowerPoint-friendly MP4 video, high-quality MP3 audio, or uncompressed WAV audio.

## New in V0.5

- Added **MP3 Audio** output.
- MP3 uses the best available source audio and converts it with FFmpeg to:
  - MP3
  - 320 kbps constant bitrate
  - 48 kHz
  - stereo
- Resolution selection is disabled for both MP3 and WAV jobs.
- The download queue can freely mix MP4, MP3 and WAV items.
- Queue quality now shows:
  - selected resolution for MP4
  - 320 kbps for MP3
  - PCM for WAV

## Output choices

### MP4 Video

- 1080p / 720p / 480p maximum resolution
- H.264 video
- AAC audio
- yuv420p pixel format
- fast-start metadata
- intended for reliable PowerPoint playback

### MP3 Audio

- best available YouTube audio source
- 320 kbps MP3
- 48 kHz
- stereo
- much smaller than WAV and suitable for normal playback

### WAV Audio

- best available YouTube audio source
- PCM signed 16-bit
- 48 kHz
- stereo
- uncompressed and highly compatible

## Download queue

Paste a YouTube link, choose an output format, and click **Add to Queue**. The queue begins automatically and processes jobs one-by-one.

You can keep adding more links while the queue is working.

Queue controls:

- Cancel Current
- Remove Selected
- Clear Finished
- Open Save Folder

Cancelling the current item does not remove the remaining queue.

## Important use note

Only download media you own or are authorised to download. The application does not implement DRM circumvention, browser-cookie extraction, account-login automation, or protected-stream bypassing.

## Automatic Windows build

Every push to `main` runs the GitHub Actions workflow:

    Build Windows Installer

It produces:

1. `YouTubeDownloader-Windows-Installer`
2. `YouTubeDownloader-Windows-Portable`

Installer:

    YouTubeDownloader_Setup_v0.5.0.exe

## Building locally

Run:

    build_windows.bat

Then, with Inno Setup 6 installed:

    make_installer.bat

The installer is created at:

    installer_output\YouTubeDownloader_Setup_v0.5.0.exe

## V0.5 test checklist

Test a mixed queue containing:

- one MP4
- one MP3
- one WAV

Confirm:

- MP3 plays correctly and reports approximately 320 kbps
- WAV plays correctly
- MP4 still embeds and plays correctly in PowerPoint
- queue continues automatically between different formats
- cancelling one job still allows the next queued job to begin

See `THIRD_PARTY_NOTICES.md` for bundled-tool licensing notes.
