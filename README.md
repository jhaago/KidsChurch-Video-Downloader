# YouTube Downloader V0.4

A Windows desktop app for downloading **authorised** YouTube media and saving it either as a PowerPoint-friendly MP4 video or an uncompressed WAV audio file.

## New in V0.4

- App title changed from **Kids Church Video Downloader** to **YouTube Downloader**
- Added **WAV Audio** output
- Added an **Output format** selector:
  - MP4 Video
  - WAV Audio
- WAV jobs download the best available audio stream and convert it to:
  - WAV container
  - 16-bit PCM
  - 48 kHz
  - stereo
- Resolution selection is automatically disabled when WAV Audio is selected
- Queue now shows the chosen output format as well as quality/status
- Existing V0.3 save-folder and resolution preferences are retained after upgrading

## Download queue

You can queue multiple items without waiting for the current one to finish.

Typical workflow:

1. Paste a YouTube URL.
2. Optionally click **Preview**.
3. Select **MP4 Video** or **WAV Audio**.
4. For MP4, choose 1080p / 720p / 480p.
5. Choose the save folder.
6. Click **Add to Queue**.
7. Paste the next URL and repeat.

Downloads run automatically one-by-one. This keeps resource use predictable while still allowing a whole batch to be entered quickly.

Queue controls:

- Cancel Current
- Remove Selected
- Clear Finished
- Open Save Folder

Cancelling the current item does not discard the rest of the queue.

## MP4 output

MP4 files are normalised for PowerPoint compatibility:

- MP4 container
- H.264 video
- AAC audio
- yuv420p pixel format
- fast-start metadata

## WAV output

WAV files are converted to:

- WAV container
- PCM signed 16-bit little-endian
- 48 kHz sample rate
- 2-channel stereo

This produces large but highly compatible, uncompressed audio files.

## Important use note

Only download media you own or are authorised to download. The application does not implement DRM circumvention, browser-cookie extraction, account-login automation, or protected-stream bypassing.

## Automatic Windows build

Every push to `main` runs the GitHub Actions workflow:

    Build Windows Installer

It produces:

1. `YouTubeDownloader-Windows-Installer`
2. `YouTubeDownloader-Windows-Portable`

The installer filename is:

    YouTubeDownloader_Setup_v0.4.0.exe

## Building locally

Requirements:

- Windows 10/11 x64
- Python 3.12+
- Internet access during the build

Run:

    build_windows.bat

The script downloads yt-dlp, Deno, FFmpeg and ffprobe and creates:

    dist\YouTubeDownloader\YouTubeDownloader.exe

After installing Inno Setup 6, run:

    make_installer.bat

The installer is created at:

    installer_output\YouTubeDownloader_Setup_v0.4.0.exe

## V0.4 test checklist

Try at least:

- one MP4 video
- one WAV audio download
- a mixed queue containing both MP4 and WAV jobs
- add another job while the queue is running
- confirm WAV plays correctly in Windows
- confirm MP4 still embeds and plays correctly in PowerPoint
- cancel one item and confirm the next item continues

See `THIRD_PARTY_NOTICES.md` for bundled-tool licensing notes.
