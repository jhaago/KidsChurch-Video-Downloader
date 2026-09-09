# YouTube Downloader V0.5

A desktop app for downloading **authorised** YouTube media as PowerPoint-friendly MP4 video, high-quality MP3 audio, or uncompressed WAV audio.

## Platforms

V0.5 now has automated builds for:

- Windows x64
- macOS Intel
- macOS Apple Silicon

The Windows and Mac versions use the same application code and the same MP4 / MP3 / WAV queue workflow.

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

### WAV Audio

- best available YouTube audio source
- PCM signed 16-bit
- 48 kHz
- stereo
- uncompressed

## Download queue

Paste a YouTube link, choose an output format, and click **Add to Queue**. The queue begins automatically and processes jobs one-by-one.

You can keep adding more links while the queue is working.

Queue controls:

- Cancel Current
- Remove Selected
- Clear Finished
- Open Save Folder

Cancelling the current item does not remove the remaining queue.

## Windows builds

GitHub Actions produces:

- `YouTubeDownloader-Windows-Installer`
- `YouTubeDownloader-Windows-Portable`

Installer:

    YouTubeDownloader_Setup_v0.5.0.exe

For a local Windows build:

    build_windows.bat

Then, with Inno Setup 6 installed:

    make_installer.bat

## macOS builds

GitHub Actions produces two separate Mac artifacts:

- `YouTubeDownloader-macOS-Intel`
- `YouTubeDownloader-macOS-AppleSilicon`

Each artifact contains:

- a `.dmg`
- a preserved `.app` ZIP

Choose **Intel** for an Intel Mac. Choose **AppleSilicon** for an M1/M2/M3/M4/M5-class Mac.

The Mac package contains:

- YouTube Downloader.app
- bundled yt-dlp
- bundled Deno
- bundled FFmpeg
- bundled ffprobe

Current Mac target is macOS 12 or later.

### Opening the current development Mac build

The development build is ad-hoc signed but is **not Apple notarized**. On first launch macOS may warn that it cannot verify the developer.

For testing:

1. Open the DMG.
2. Copy **YouTube Downloader.app** to Applications.
3. Control-click/right-click the app.
4. Choose **Open**.
5. Confirm **Open** if macOS asks.

A future public release should use an Apple Developer ID signature and notarization.

### Building locally on a Mac

Requirements:

- macOS 12+
- Python 3.12+
- Node 22+
- Internet access during the build

Run:

    chmod +x build_macos.sh prepare_tools_macos.sh
    ./build_macos.sh

The script automatically downloads architecture-correct versions of yt-dlp, Deno, FFmpeg and ffprobe, builds the app, applies an ad-hoc signature, and creates both ZIP and DMG packages.

Outputs appear in:

    macos_output/

## Mac architecture details

The official yt-dlp macOS executable is universal. Deno and the static FFmpeg tools are selected for the current Mac architecture.

The GitHub workflow uses dedicated Intel and Apple Silicon runners so both packages are built and checked natively rather than assuming one Mac binary will work everywhere.

## Important use note

Only download media you own or are authorised to download. The application does not implement DRM circumvention, browser-cookie extraction, account-login automation, or protected-stream bypassing.

## V0.5 cross-platform test checklist

Test a mixed queue containing:

- one MP4
- one MP3
- one WAV

On each platform confirm:

- Preview loads
- MP3 plays correctly
- WAV plays correctly
- MP4 contains picture and audio
- queue continues between different formats
- cancelling one job allows the next queued job to begin
- save folder is remembered after restarting

On macOS also confirm:

- app opens after the one-time Gatekeeper approval
- Intel/Apple Silicon package matches the Mac architecture
- MP4 plays in PowerPoint or the intended presentation software

See `THIRD_PARTY_NOTICES.md` for bundled-tool licensing notes.
