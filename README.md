# KidsChurch Video Downloader

A cross-platform media downloader for **authorised** Kids Church use.

Current builds:

- **Windows / macOS desktop:** V0.7.0 — YouTube plus authorised unencrypted Minno HLS video
- **Android:** V0.3 — YouTube only

The desktop app includes a download queue. Android currently downloads one item at a time.

## Current features

### Desktop — Windows and macOS

- YouTube MP4 / MP3 / WAV downloads
- Minno MP4 downloads for authorised **unencrypted HLS** playback
- metadata preview
- MP4 quality ceiling: 1080p / 720p / 480p
- MP3: 320 kbps, 48 kHz stereo
- WAV: signed 16-bit PCM, 48 kHz stereo
- queued downloads and mixed YouTube/Minno queues
- cancel current download
- remove queued items
- clear finished items
- remembered save folder and output settings
- PowerPoint-friendly H.264/AAC MP4 conversion
- dedicated **Download Speed** and **Time Remaining** display while downloading
- completed queue rows show **Open Folder**
- separate remembered Minno browser session with **Refresh / Sign in** and **Sign out** controls

### Android V0.3

Android remains YouTube-only in this release.

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
- tap a completed file to use Android's normal **Open with…** chooser

---

# Desktop Minno workflow

V0.7.0 can download an authorised Minno video without manually opening DevTools or copying an `.m3u8` URL.

1. Paste the Minno episode URL into **KidsChurch Video Downloader**.
2. Choose the MP4 quality ceiling: 1080p, 720p, or 480p.
3. Select **Preview** or **Add to Queue**.
4. If Minno needs authentication, a dedicated Chrome/Edge window opens using a separate downloader profile.
5. Sign in directly on Minno's own page. If the downloader asks, press **Play** in that browser window so the authorised stream starts.
6. The app discovers the HLS master playlist, checks that the selected stream is unencrypted, selects the best video at or below your requested quality plus audio, and starts FFmpeg.
7. During transfer, the main window shows percentage, **Download Speed**, and **Time Remaining**.
8. The completed file is saved as an MP4 suitable for the existing Kids Church presentation workflow.

Minno audio-only MP3/WAV extraction is **not** supported in V0.7.0.

If a Minno stream uses active HLS encryption or DRM/protected playback, the downloader stops before transfer. It does not retrieve or use decryption keys.

## Minno account/session privacy

Minno authentication uses a dedicated Chromium profile stored in the app's local user-data directory under `KidsChurchVideoDownloader/minno-browser-profile`.

- The app does **not** import or inspect your normal Chrome profile.
- Your Minno password is entered directly into Minno and is not collected by the downloader.
- Signed media URLs, cookies, authentication headers, and session IDs are not written to the normal activity log.
- **Minno Account → Sign out** closes the downloader-managed browser and deletes the dedicated Minno profile.
- The saved Minno session persists across app restarts until Minno expires it or you sign out.

---

# How to install

You do **not** need Python, FFmpeg, Deno, yt-dlp, or Android Studio when using the packaged builds. Required runtime components are bundled except for the desktop Minno browser integration, which uses an installed Chromium-family browser.

For Minno on desktop, install one of the supported browsers:

- Windows: Google Chrome preferred; Microsoft Edge supported as fallback
- macOS: Google Chrome preferred; Microsoft Edge supported as fallback

The source files in this repository are not the installer. For normal use, download the latest successful build from **GitHub Actions**.

## Windows — V0.7.0

1. Open this repository on GitHub.
2. Select **Actions** → **Build Windows Installer**.
3. Open the latest run with a green check mark.
4. Under **Artifacts**, download **KidsChurchVideoDownloader-Windows-Installer**.
5. Extract the ZIP.
6. Run `KidsChurchVideoDownloader_Setup_v0.7.0.exe`.
7. Follow the installer and launch **KidsChurch Video Downloader**.

The V0.7.0 installer keeps the existing Windows AppId so it upgrades the previous desktop installation rather than intentionally creating an unrelated product. The existing `KidsChurchVideoDownloader` settings folder is also preserved.

### Windows SmartScreen

The private development build is not commercially code-signed, so Windows SmartScreen may warn about it. For a build you downloaded from this repository, use **More info → Run anyway** if you are comfortable proceeding. Do not disable Windows security globally.

## macOS — V0.7.0

There are separate Intel and Apple Silicon packages.

Check **Apple menu → About This Mac** and use:

- **AppleSilicon** for Apple M-series Macs
- **Intel** for Intel Macs

Then:

1. Open this repository on GitHub.
2. Select **Actions** → **Build macOS App**.
3. Open the latest run with a green check mark.
4. Download **KidsChurchVideoDownloader-macOS-AppleSilicon** or **KidsChurchVideoDownloader-macOS-Intel**.
5. Extract the artifact and open the included `.dmg`.
6. Copy **KidsChurch Video Downloader.app** to Applications.
7. On first launch, Control-click/right-click the app and choose **Open**.
8. Confirm **Open** if macOS asks.

The development Mac build is ad-hoc signed but is not Apple notarized.

## Android — V0.3

1. Open this repository on GitHub.
2. Select **Actions** → **Build Android APK**.
3. Open the latest run with a green check mark.
4. Under **Artifacts**, download **YouTubeDownloader-Android-v0.3**.
5. Extract the ZIP and install `app-debug.apk`.
6. Android may ask the browser or Files app for permission to **Install unknown apps**. Allow it for that app if you are comfortable installing this private test build.
7. Open **YouTube Downloader**.

You do not need to disable Android security globally.

---

# Desktop download queue

Queue rows show the media title, format, quality, status, and—once complete—an **Open Folder** action.

During active YouTube or Minno transfers, the Current Activity area shows percentage, live transfer speed, and estimated time remaining. During post-processing/conversion, network speed and ETA may show `—` because the network download has already completed.

The existing **Open Save Folder** button opens the currently selected save directory; the completed-row action opens the folder associated with that specific queued job.

---

# Output formats

## MP4 Video

Desktop output is presentation-friendly:

- MP4 container
- H.264 video
- AAC audio
- yuv420p when conversion is required
- fast-start metadata
- 1080p / 720p / 480p quality ceilings

For already compatible Minno H.264/AAC streams, FFmpeg can stream-copy the authorised HLS video/audio into the final MP4 without a full re-encode. Incompatible source codecs go through the existing H.264/AAC conversion path.

Android requests H.264 video + AAC audio directly where practical so the phone can merge streams without a costly full 1080p transcode.

## MP3 Audio

YouTube only in V0.7.0 desktop Minno support.

- 320 kbps
- 48 kHz stereo on desktop

## WAV Audio

YouTube only in V0.7.0 desktop Minno support.

- uncompressed PCM
- signed 16-bit / 48 kHz stereo on desktop

---

# GitHub Actions artifacts

Use the latest green run for each platform.

- Windows: **KidsChurchVideoDownloader-Windows-Installer**, **KidsChurchVideoDownloader-Windows-Portable**
- macOS: **KidsChurchVideoDownloader-macOS-Intel**, **KidsChurchVideoDownloader-macOS-AppleSilicon**
- Android: **YouTubeDownloader-Android-v0.3**

Historical red runs can remain visible during development; use the latest successful run.

---

# Building from source

Normal users should use the packaged builds above.

## Windows

Requirements: Windows 10/11 x64, Python 3.12+, internet access, and Chrome or Edge for Minno.

Run:

    build_windows.bat

Then install Inno Setup 6 and run:

    make_installer.bat

## macOS

Requirements: macOS 12+, Python 3.12+, Node 22+, internet access, and Chrome or Edge for Minno.

Run:

    chmod +x build_macos.sh prepare_tools_macos.sh
    ./build_macos.sh

## Android

The Kotlin / Jetpack Compose project is in `android/`. GitHub Actions builds the APK automatically; for local development, open the `android` directory in Android Studio.

---

# Authorised use

Only download media you own or are authorised to download and use.

The desktop Minno integration can launch a dedicated browser profile so the user can authenticate directly with Minno and discover the stream that Minno authorises for that session. It does not import normal browser cookies, retrieve decryption keys, circumvent DRM, or bypass protected playback.

See `THIRD_PARTY_NOTICES.md` for bundled component and licensing information.
