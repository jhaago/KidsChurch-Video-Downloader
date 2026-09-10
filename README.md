# YouTube Downloader

A cross-platform desktop and Android app for downloading **authorised** YouTube media.

Current builds:

- **Windows / macOS desktop:** V0.6.4
- **Android:** V0.2.1

Available output formats:

- **MP4 Video**
- **MP3 Audio**
- **WAV Audio**

The desktop app includes a download queue. Android V0.2.1 currently downloads one item at a time; queue/background support is planned next.

## Refined app icon

All packages use the same dark/red play-and-download visual identity.

V0.2.1 / V0.6.4 refines the icon after real-device launcher testing showed that the original mark sat too close to Android's adaptive-icon mask. The play/download artwork is now smaller, better centred, and kept inside the safe zone so the arrow/tray is not clipped on Samsung and other rounded-square launchers.

- Android uses a safe-zone-aware adaptive launcher icon.
- Windows generates a matching `.ico` during packaging.
- macOS generates a matching `.icns` during packaging.

The desktop icon files are generated from `assets/generate_icons.py` so Windows and Mac remain visually consistent.

---

# How to install

You do **not** need Python, FFmpeg, Deno, yt-dlp, Android Studio, or other developer tools when using the packaged builds. Required download/conversion components are bundled into each platform build.

The source-code files in the repository are not the installer. The easiest way to install the app is to download a finished build from **GitHub Actions**.

## Android — V0.2.1

Android V0.2.1 supports:

- **MP4 Video**
  - 1080p
  - 720p
  - 480p
  - H.264 video + AAC audio selection for broad compatibility
- **MP3 Audio**
  - 320 kbps
- **WAV Audio**
  - uncompressed PCM
- paste a YouTube URL
- **YouTube app → Share → YouTube Downloader**
- progress and ETA
- cancellation
- automatic yt-dlp stable update check before the first download of each launch
- saving to **Downloads/YouTube Downloader**
- **tap a completed file to open it in Android's normal/default app for that file type**

### Install the Android APK

1. Open this repository on GitHub.
2. Click **Actions**.
3. Select **Build Android APK**.
4. Open the most recent run with a **green check mark**.
5. Scroll to **Artifacts**.
6. Download **YouTubeDownloader-Android-v0.2.1**.
7. Extract the downloaded ZIP.
8. Install:

       app-debug.apk

9. Android may ask the browser/files app for permission to **Install unknown apps**. Allow that permission for the app you are installing from if you are comfortable installing this private test build.
10. Open **YouTube Downloader**.

You do **not** need to disable Android security globally.

### Use Android V0.2

1. Paste a YouTube URL, or use:

   **YouTube → Share → YouTube Downloader**

2. Choose:
   - MP4
   - MP3
   - WAV
3. For MP4, choose:
   - 1080p
   - 720p
   - 480p
4. Tap the download button.
5. The completed file is saved under:

   **Downloads/YouTube Downloader**

6. Tap the completed filename in the status card to open it. Android hands the file to the normal app associated with that type (video player, music player, editor, etc.).

The status panel shows **READY**, **DOWNLOADING**, **COMPLETE**, or **FAILED** and also displays the active yt-dlp engine version once checked.

---

## Windows — V0.6.4

1. Open this repository on GitHub.
2. Click **Actions**.
3. Click **Build Windows Installer**.
4. Open the latest run with a **green check mark**.
5. Scroll to **Artifacts**.
6. Download **YouTubeDownloader-Windows-Installer**.
7. Extract the ZIP.
8. Run:

       YouTubeDownloader_Setup_v0.6.4.exe

9. Follow the installer.
10. Launch **YouTube Downloader** from the Start menu or desktop shortcut.

### Windows SmartScreen

The private development build is not commercially code-signed yet, so Windows SmartScreen may warn about it.

For a build you downloaded from this repository:

**More info → Run anyway**

Do not disable Windows security globally.

---

## macOS — V0.6.4

There are separate Intel and Apple Silicon packages.

### Check your Mac

Open:

**Apple menu → About This Mac**

Use:

- **AppleSilicon** for Apple M-series Macs
- **Intel** for Intel Macs

### Install

1. Open this repository on GitHub.
2. Click **Actions**.
3. Click **Build macOS App**.
4. Open the latest run with a **green check mark**.
5. Download either:
   - **YouTubeDownloader-macOS-AppleSilicon**
   - **YouTubeDownloader-macOS-Intel**
6. Extract the artifact.
7. Open the included `.dmg`.
8. Copy **YouTube Downloader.app** to Applications.
9. On first launch, Control-click/right-click the app and choose **Open**.
10. Confirm **Open** if macOS asks.

The current development Mac build is ad-hoc signed but is not Apple notarized.

---

# Desktop features

The Windows and macOS V0.6.4 desktop versions support:

- preview metadata
- MP4 / MP3 / WAV output
- MP4 quality selection
- queued downloads
- mixed-format queues
- cancel current download
- remove queued items
- clear finished items
- remembered save folder and output settings
- presentation-friendly H.264/AAC MP4 conversion

## Desktop output formats

### MP4 Video

- MP4 container
- H.264 video
- AAC audio
- yuv420p
- fast-start metadata
- 1080p / 720p / 480p

### MP3 Audio

- 320 kbps
- 48 kHz stereo

### WAV Audio

- signed 16-bit PCM
- 48 kHz stereo
- uncompressed

---

# GitHub Actions builds

Current automated build artifacts:

### Windows

- **YouTubeDownloader-Windows-Installer**
- **YouTubeDownloader-Windows-Portable**

### macOS

- **YouTubeDownloader-macOS-Intel**
- **YouTubeDownloader-macOS-AppleSilicon**

### Android

- **YouTubeDownloader-Android-v0.2.1**

Always use the most recent **green** workflow run.

Historical red runs may remain visible from earlier development attempts; they do not mean the latest build is broken.

---

# Building from source

Normal users should use the packaged builds above.

## Windows

Requirements:

- Windows 10/11 x64
- Python 3.12+
- internet access

Run:

    build_windows.bat

Then install Inno Setup 6 and run:

    make_installer.bat

The build process generates the Windows icon automatically.

## macOS

Requirements:

- macOS 12+
- Python 3.12+
- Node 22+
- internet access

Run:

    chmod +x build_macos.sh prepare_tools_macos.sh
    ./build_macos.sh

The build process generates the macOS icon automatically.

## Android

The native Kotlin / Jetpack Compose source is in:

    android/

GitHub Actions builds the APK automatically. For local development, open the `android` folder in Android Studio.

---

# Authorised use

Only download media you own or are authorised to download.

The application does not implement DRM circumvention, browser-cookie extraction, account-login automation, or protected-stream bypassing.

See **THIRD_PARTY_NOTICES.md** for bundled component and licensing information.
