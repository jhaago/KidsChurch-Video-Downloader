# YouTube Downloader V0.5

A simple desktop app for downloading **authorised** YouTube media as:

- **MP4 Video** — PowerPoint-friendly H.264/AAC video
- **MP3 Audio** — 320 kbps stereo
- **WAV Audio** — uncompressed 16-bit PCM stereo

It supports a download queue, so you can add several videos/audio tracks and let them process automatically.

---

# How to install

You do **not** need Python, FFmpeg, Deno, or yt-dlp installed on your computer when using the packaged builds. They are bundled with the app.

The source-code files in the repository are not the installer. The easiest way to install the app is to download a finished build from **GitHub Actions**.

## Windows

1. Open this repository on GitHub.
2. Click **Actions** near the top of the repository.
3. In the left-hand list, click **Build Windows Installer**.
4. Open the most recent run with a **green check mark**.
5. Scroll to the **Artifacts** section at the bottom.
6. Download **YouTubeDownloader-Windows-Installer**.
7. Windows will download a ZIP file. Extract/unzip it.
8. Inside, run:

       YouTubeDownloader_Setup_v0.5.0.exe

9. Follow the installer normally.
10. Launch **YouTube Downloader** from the Start menu or desktop shortcut.

### Windows security warning

Because this development build is not commercially code-signed yet, Windows SmartScreen may show a warning.

For your own test build, choose:

**More info → Run anyway**

Only do this for the build downloaded from this repository.

### Updating an existing Windows installation

You can normally run the newer installer over the existing version. Your remembered save-folder and output settings are stored separately and should remain available.

---

## macOS

There are **two Mac builds**. Choose the one that matches your Mac.

### First: check which Mac you have

Open:

**Apple menu → About This Mac**

Use:

- **AppleSilicon** if it says **Chip: Apple M1, M2, M3, M4, M5, etc.**
- **Intel** if it says **Processor: Intel**

### Download the Mac build

1. Open this repository on GitHub.
2. Click **Actions**.
3. In the left-hand list, click **Build macOS App**.
4. Open the most recent run with a **green check mark**.
5. Scroll to **Artifacts**.
6. Download one of:

   - **YouTubeDownloader-macOS-AppleSilicon**
   - **YouTubeDownloader-macOS-Intel**

7. Extract the downloaded ZIP.
8. Inside are two versions of the same build:

   - a **.dmg** — recommended for normal installation
   - an app ZIP — useful as a portable/archive copy

### Install from the DMG

1. Double-click the downloaded **.dmg**.
2. Copy **YouTube Downloader.app** to your **Applications** folder.
3. Open Applications.
4. The first time only, **Control-click/right-click YouTube Downloader**.
5. Choose **Open**.
6. If macOS asks again, choose **Open**.

After the first approved launch, you should be able to open it normally.

### Why macOS may show a warning

The current development build is ad-hoc signed but is **not Apple notarized**. That is why macOS may say it cannot verify the developer.

A future public release can use Apple Developer ID signing and notarization to remove most of this friction.

---

# How to use

1. Paste a YouTube URL.
2. Optionally click **Preview** to check the title/channel/duration.
3. Choose an output format:
   - **MP4 Video**
   - **MP3 Audio**
   - **WAV Audio**
4. For MP4, choose:
   - 1080p
   - 720p
   - 480p
5. Choose the save folder.
6. Click **Add to Queue**.
7. Paste another URL and repeat if needed.

The app processes queued items one-by-one automatically.

You can mix formats in one queue, for example:

- Video 1 → MP4 1080p
- Song 1 → MP3
- Song 2 → WAV
- Video 2 → MP4 720p

Queue controls include:

- **Cancel Current**
- **Remove Selected**
- **Clear Finished**
- **Open Save Folder**

Cancelling the current item does not remove the remaining queue.

---

# Output formats

## MP4 Video

The final MP4 is deliberately converted for reliable PowerPoint playback:

- MP4 container
- H.264 video
- AAC audio
- yuv420p pixel format
- fast-start metadata

Available maximum resolutions:

- 1080p
- 720p
- 480p

## MP3 Audio

- best available source audio is downloaded first
- converted to MP3 with FFmpeg
- 320 kbps
- 48 kHz
- stereo

This is the normal choice when you want audio only with a reasonably small file size.

## WAV Audio

- best available source audio is downloaded first
- converted to WAV
- signed 16-bit PCM
- 48 kHz
- stereo
- uncompressed

WAV files are much larger than MP3 files but are useful for editing and maximum compatibility.

---

# Supported builds

Automated GitHub Actions builds currently produce:

### Windows

- **YouTubeDownloader-Windows-Installer**
- **YouTubeDownloader-Windows-Portable**

### macOS

- **YouTubeDownloader-macOS-Intel**
- **YouTubeDownloader-macOS-AppleSilicon**

The Mac workflow builds and verifies Intel and Apple Silicon packages separately.

---

# If a build fails

Do not download an artifact from a failed/red workflow run.

Always choose the **latest green run**.

If GitHub has sent failure emails during development, those may relate to earlier intermediate builds. Check the latest workflow run before deciding that the current version is broken.

---

# Troubleshooting

## I cloned/downloaded the repository but cannot find the EXE

That is expected.

The repository mainly contains the **source code**. The finished Windows installer is produced by GitHub Actions.

Go to:

**Actions → Build Windows Installer → latest green run → Artifacts → YouTubeDownloader-Windows-Installer**

## My Mac says the app cannot be verified

Control-click/right-click the app and choose:

**Open → Open**

This is currently necessary because the development build is not Apple-notarized.

## The app says yt-dlp, Deno, or FFmpeg is missing

Make sure you are using the packaged installer/app downloaded from GitHub Actions rather than trying to run the source code directly.

## A YouTube download stops working later

YouTube changes frequently. The app uses yt-dlp and Deno specifically so the extraction engine can be updated independently as YouTube changes.

---

# Building from source

These instructions are for development only. Normal users should use the packaged builds above.

## Windows development build

Requirements:

- Windows 10/11 x64
- Python 3.12+
- internet access

Run:

    build_windows.bat

The script downloads yt-dlp, Deno, FFmpeg and ffprobe and builds the application.

To create the installer, install Inno Setup 6 and run:

    make_installer.bat

## macOS development build

Requirements:

- macOS 12+
- Python 3.12+
- Node 22+
- internet access

Run:

    chmod +x build_macos.sh prepare_tools_macos.sh
    ./build_macos.sh

The script prepares architecture-correct dependencies, builds **YouTube Downloader.app**, applies an ad-hoc signature, and creates both DMG and ZIP packages.

---

# Legal / authorised use

Only download media you own or are authorised to download.

The application does not implement DRM circumvention, browser-cookie extraction, account-login automation, or protected-stream bypassing.

See **THIRD_PARTY_NOTICES.md** for bundled component and licensing information.
