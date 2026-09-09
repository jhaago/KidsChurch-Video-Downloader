# Kids Church Video Downloader V0.1

A small Windows-first desktop application for downloading **authorised** online video and producing a predictable MP4 suitable for PowerPoint.

## V0.1 features

- Paste a video URL
- 1080p / 720p / 480p maximum resolution
- Choose save folder
- Download progress
- Cancel
- Automatic conversion to:
  - MP4 container
  - H.264 video
  - AAC audio
  - yuv420p pixel format
  - fast-start metadata
- Avoids overwriting existing files
- Opens the destination folder
- Does not use browser cookies or attempt DRM bypass

## Important use note

Only download media you own or are authorised to download. This project intentionally does not implement DRM circumvention, browser-cookie extraction, account-login automation, or protected-stream bypassing.

## Development setup (Windows)

1. Install Python 3.12+.
2. Install FFmpeg and make sure `ffmpeg.exe` is available on PATH.
3. Open Command Prompt in this folder.
4. Run:

    py -m pip install -r requirements.txt

5. Start the app:

    py main.py

## Packaging as a Windows EXE

For the most reliable standalone build:

1. Download a Windows FFmpeg build.
2. Copy `ffmpeg.exe` into this project folder.
3. Run:

    build_windows.bat

The built application will appear in:

    dist\KidsChurchVideoDownloader\

The build script copies `ffmpeg.exe` beside the EXE.

## YouTube note

YouTube changes its delivery/player systems regularly. yt-dlp is deliberately kept as a replaceable dependency so the downloader engine can be updated without rewriting the UI.

Some YouTube formats/player challenges may also require a supported JavaScript runtime on a given yt-dlp release. That packaging can be added in the next version after testing V0.1 on the target Windows machine.

## Next recommended features

- Video metadata preview / thumbnail
- Download queue
- Start/end trim controls
- Audio-only mode
- Remember last save folder
- App settings
- Built-in yt-dlp update check
- Bundled JavaScript runtime if required for reliable YouTube extraction
- Proper installer (Inno Setup or MSIX)

## Creating the normal Windows installer

After `build_windows.bat` succeeds:

1. Install Inno Setup 6.
2. Run:

    make_installer.bat

3. The finished installer will appear in:

    installer_output\KidsChurchVideoDownloader_Setup_v0.1.0.exe

That installer creates a normal Windows application entry and optional desktop shortcut.
