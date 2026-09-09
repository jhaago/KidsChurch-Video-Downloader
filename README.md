# Kids Church Video Downloader V0.3

A Windows-first desktop application for downloading **authorised** online video and creating predictable MP4 files suitable for embedding in PowerPoint.

## New in V0.3: download queue

You can now queue multiple videos without waiting for each one to finish.

Typical workflow:

1. Paste a video URL.
2. Optionally click **Preview**.
3. Choose the resolution and save folder.
4. Click **Add to Queue**.
5. Paste the next URL and repeat.

The queue starts automatically and processes items one-by-one. This is deliberate: sequential downloading/conversion is much more predictable on a church laptop than running several FFmpeg conversions simultaneously, while still letting you enter a whole batch at once.

The queue shows:

- video title / URL
- selected quality
- Queued / Running / Complete / Failed / Cancelled status

Queue controls include:

- **Cancel Current**
- **Remove Selected**
- **Clear Finished**
- **Open Save Folder**

Cancelling the current item does not discard the remaining queue; the next queued item continues automatically.

## Other V0.3 improvements

- The URL box stays available while the queue is working, so more videos can be added at any time.
- Each queued job remembers the resolution and destination folder selected when it was added.
- Preview metadata is reused when available.
- Bundled tool folders are explicitly added to the child-process PATH so yt-dlp can locate the bundled Deno runtime reliably.
- Source development also recognises tools stored in the repository's `tools` folder.

## Core features

- Windows desktop app
- 1080p / 720p / 480p maximum resolution
- Video preview:
  - title
  - channel/uploader
  - duration
  - extractor/site
- Remembers the last save folder and resolution
- Bundled yt-dlp
- Bundled Deno
- Bundled FFmpeg / ffprobe
- Download and conversion progress
- Automatic Windows installer builds with GitHub Actions
- Portable Windows build artifact

## Output format

The final file is deliberately normalised for PowerPoint:

- MP4 container
- H.264 video
- AAC audio
- yuv420p pixel format
- fast-start metadata

## Important use note

Only download media you own or are authorised to download. The application does not implement DRM circumvention, browser-cookie extraction, account-login automation, or protected-stream bypassing.

## Easiest way to get a test build

The repository contains a GitHub Actions workflow called:

    Build Windows Installer

Every push to `main` runs the Windows build automatically. The workflow produces:

1. `KidsChurchVideoDownloader-Windows-Installer`
2. `KidsChurchVideoDownloader-Windows-Portable`

For normal testing, download the installer artifact and run:

    KidsChurchVideoDownloader_Setup_v0.3.0.exe

## Building locally on Windows

Requirements:

- Windows 10/11 x64
- Python 3.12+
- Internet access during the build

Run:

    build_windows.bat

The script automatically downloads the current Windows versions of yt-dlp, Deno, FFmpeg and ffprobe, then builds:

    dist\KidsChurchVideoDownloader\KidsChurchVideoDownloader.exe

To create the installer, install Inno Setup 6 and run:

    make_installer.bat

The installer will appear in:

    installer_output\KidsChurchVideoDownloader_Setup_v0.3.0.exe

## V0.3 test checklist

Test the queue with three authorised videos:

- add all three before the first finishes
- verify each title appears in the queue
- verify they process automatically in order
- add a fourth while another item is running
- cancel one current download and confirm the next begins
- verify completed MP4 files contain picture and audio
- embed at least one result into PowerPoint and test it in slideshow mode
- restart the app and confirm the save folder is remembered

## Possible next features

- thumbnail preview
- drag-and-drop URLs
- paste multiple URLs at once
- audio-only mode
- start/end trimming
- reorder queued items
- optional limited parallel downloading
- faster no-transcode path for already-compatible media
- in-app component updater
- application icon and visual polish

See `THIRD_PARTY_NOTICES.md` for bundled-tool licensing notes.
