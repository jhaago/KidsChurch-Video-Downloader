# Kids Church Video Downloader V0.2

A Windows-first desktop application for downloading **authorised** online video and creating a predictable MP4 suitable for embedding in PowerPoint.

## What V0.2 adds

- Uses the official standalone **yt-dlp.exe** instead of embedding the Python yt-dlp package
- Bundles **Deno** for current YouTube JavaScript challenge support
- Bundles **FFmpeg / ffprobe**
- Video preview before downloading:
  - title
  - channel/uploader
  - duration
  - extractor/site
- Remembers the last save folder and resolution
- More robust cancellation of yt-dlp and FFmpeg child processes
- Download and conversion progress
- Automatic GitHub Actions Windows build
- Normal Inno Setup installer
- Portable Windows build artifact

## Output format

The final file is deliberately normalised for PowerPoint:

- MP4 container
- H.264 video
- AAC audio
- yuv420p pixel format
- fast-start metadata

V0.2 always performs the final compatibility conversion rather than trusting the codec/container supplied by the source site.

## Important use note

Only download media you own or are authorised to download. The application does not implement DRM circumvention, browser-cookie extraction, account-login automation, or protected-stream bypassing.

## Easiest way to get a test build

The repository contains a GitHub Actions workflow called:

    Build Windows Installer

Every push to `main` runs the Windows build automatically. The workflow produces two downloadable artifacts:

1. `KidsChurchVideoDownloader-Windows-Installer`
2. `KidsChurchVideoDownloader-Windows-Portable`

For normal testing, download the installer artifact and run:

    KidsChurchVideoDownloader_Setup_v0.2.0.exe

## Building locally on Windows

Requirements:

- Windows 10/11 x64
- Python 3.12+
- Internet access during the build

Run:

    build_windows.bat

The script automatically runs `prepare_tools.ps1`, which downloads the current Windows versions of:

- yt-dlp
- Deno
- FFmpeg
- ffprobe

It then builds:

    dist\KidsChurchVideoDownloader\KidsChurchVideoDownloader.exe

To create the installer, install Inno Setup 6 and run:

    make_installer.bat

The installer will appear in:

    installer_output\KidsChurchVideoDownloader_Setup_v0.2.0.exe

## Bundled-tool architecture

The installed folder contains separate executables:

    KidsChurchVideoDownloader.exe
    yt-dlp.exe
    deno.exe
    ffmpeg.exe
    ffprobe.exe

Keeping these components separate is deliberate. YouTube changes frequently, and this architecture lets the downloader engine/runtime be updated without redesigning the desktop UI.

## Current V0.2 test goals

Before adding more features, test the packaged app with several authorised video links and verify:

- Preview loads correctly
- 1080p, 720p and 480p selections work
- Audio is present
- Final MP4 embeds and plays correctly in PowerPoint
- Cancel stops both download and conversion
- Save folder is remembered after restarting
- Filenames containing punctuation do not break the download
- A second download with the same title does not overwrite the first

## Likely V0.3 features

After the first real Windows tests:

- thumbnail preview
- download queue
- audio-only mode
- start/end trimming
- faster no-transcode path when the source is already PowerPoint-compatible
- in-app component/version display
- updater for yt-dlp/Deno components
- application icon and visual polish

See `THIRD_PARTY_NOTICES.md` for the current bundled-tool licensing notes.
