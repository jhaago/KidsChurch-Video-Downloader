# YouTube Downloader

A cross-platform app for downloading **authorised** YouTube media as MP4 video, MP3 audio, or WAV audio.

Current builds:

- **Windows / macOS desktop:** V0.6.5
- **Android:** V0.3

The desktop app includes a download queue. Android currently downloads one item at a time.

## Current features

### All platforms

- MP4 video
- MP3 audio
- WAV audio
- download progress
- **live download speed**
- **estimated time remaining**
- refined play/download app icon
- only intended for media you own or are authorised to download

### Desktop — Windows and macOS

- metadata preview
- MP4 quality: 1080p / 720p / 480p
- MP3: 320 kbps, 48 kHz stereo
- WAV: signed 16-bit PCM, 48 kHz stereo
- queued downloads and mixed-format queues
- cancel current download
- remove queued items
- clear finished items
- remembered save folder and output settings
- PowerPoint-friendly H.264/AAC MP4 conversion
- dedicated **Download Speed** and **Time Remaining** display while downloading
- each completed queue row shows **Open Folder**; click it to open the folder used for that specific download

### Android V0.3

- native Kotlin / Jetpack Compose app
- MP4: 1080p / 720p / 480p
- MP3: 320 kbps
- WAV: uncompressed PCM
- paste a YouTube URL
- **YouTube → Share → YouTube Downloader**
- progress, **download speed**, and **time remaining** shown together
- cancel current download
- automatic yt-dlp stable update check before the first download of each launch
- saves to **Downloads/YouTube Downloader**
- after completion, tap the file and Android shows its normal **Open with…** chooser so you can select the video player, music player, editor, or other compatible app

---

# How to install

You do **not** need Python, FFmpeg, Deno, yt-dlp, Android Studio, or other developer tools when using the packaged builds. The required components are bundled into each platform package.

The source files in this repository are not the installer. For normal use, download the latest successful build from **GitHub Actions**.

## Android — V0.3

1. Open this repository on GitHub.
2. Select **Actions**.
3. Select **Build Android APK**.
4. Open the most recent run with a **green check mark**.
5. Under **Artifacts**, download **YouTubeDownloader-Android-v0.3**.
6. Extract the ZIP.
7. Install `app-debug.apk`.
8. Android may ask the browser or Files app for permission to **Install unknown apps**. Allow it for that app if you are comfortable installing this private test build.
9. Open **YouTube Downloader**.

You do not need to disable Android security globally.

### Using Android

Paste a URL or use **YouTube → Share → YouTube Downloader**, choose MP4 / MP3 / WAV, choose video quality when relevant, then start the download.

During the transfer, the status card shows:

- Progress
- Download Speed
- Time left

Completed files are saved to **Downloads/YouTube Downloader**. Tap the finished file card to show Android's **Open with…** chooser.

---

## Windows — V0.6.5

1. Open this repository on GitHub.
2. Select **Actions**.
3. Select **Build Windows Installer**.
4. Open the latest run with a **green check mark**.
5. Under **Artifacts**, download **YouTubeDownloader-Windows-Installer**.
6. Extract the ZIP.
7. Run `YouTubeDownloader_Setup_v0.6.5.exe`.
8. Follow the installer and launch **YouTube Downloader**.

### Windows SmartScreen

The private development build is not commercially code-signed, so Windows SmartScreen may warn about it. For a build you downloaded from this repository, use **More info → Run anyway** if you are comfortable proceeding. Do not disable Windows security globally.

---

## macOS — V0.6.5

There are separate Intel and Apple Silicon packages.

Check **Apple menu → About This Mac** and use:

- **AppleSilicon** for Apple M-series Macs
- **Intel** for Intel Macs

Then:

1. Open this repository on GitHub.
2. Select **Actions**.
3. Select **Build macOS App**.
4. Open the latest run with a **green check mark**.
5. Download **YouTubeDownloader-macOS-AppleSilicon** or **YouTubeDownloader-macOS-Intel**.
6. Extract the artifact.
7. Open the included `.dmg`.
8. Copy **YouTube Downloader.app** to Applications.
9. On first launch, Control-click/right-click the app and choose **Open**.
10. Confirm **Open** if macOS asks.

The development Mac build is ad-hoc signed but is not Apple notarized.

---

# Desktop download queue

Queue rows show the media title, format, quality, status, and—once complete—an **Open Folder** action.

During the active download, the Current Activity area shows the percentage, live transfer speed, and yt-dlp ETA. During post-processing/conversion, speed and ETA may show `—` because the network download has already finished.

The existing **Open Save Folder** button remains available for opening the currently selected save directory generally; the completed-row action opens the folder associated with that specific queued job.

---

# Output formats

## MP4 Video

Desktop output is presentation-friendly:

- MP4 container
- H.264 video
- AAC audio
- yuv420p
- fast-start metadata
- 1080p / 720p / 480p

Android requests H.264 video + AAC audio directly where practical so the phone can merge streams without a costly full 1080p transcode.

## MP3 Audio

- 320 kbps
- 48 kHz stereo on desktop

## WAV Audio

- uncompressed PCM
- signed 16-bit / 48 kHz stereo on desktop

---

# GitHub Actions artifacts

Use the latest **green** run for each platform.

- Windows: **YouTubeDownloader-Windows-Installer**, **YouTubeDownloader-Windows-Portable**
- macOS: **YouTubeDownloader-macOS-Intel**, **YouTubeDownloader-macOS-AppleSilicon**
- Android: **YouTubeDownloader-Android-v0.3**

Historical red runs can remain visible from development attempts; use the latest successful run.

---

# Building from source

Normal users should use the packaged builds above.

## Windows

Requirements: Windows 10/11 x64, Python 3.12+, and internet access.

Run:

    build_windows.bat

Then install Inno Setup 6 and run:

    make_installer.bat

## macOS

Requirements: macOS 12+, Python 3.12+, Node 22+, and internet access.

Run:

    chmod +x build_macos.sh prepare_tools_macos.sh
    ./build_macos.sh

## Android

The Kotlin / Jetpack Compose project is in `android/`. GitHub Actions builds the APK automatically; for local development, open the `android` directory in Android Studio.

---

# Authorised use

Only download media you own or are authorised to download.

The application does not implement DRM circumvention, browser-cookie extraction, account-login automation, or protected-stream bypassing.

See `THIRD_PARTY_NOTICES.md` for bundled component and licensing information.
