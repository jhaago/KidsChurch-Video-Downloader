# YouTube Downloader — Android V0.1 Proof of Concept

This folder contains the first native Android version of YouTube Downloader.

## Purpose of V0.1

The first Android milestone is deliberately narrow:

**YouTube URL → 320 kbps MP3 → Android Downloads folder**

The goal is to prove that the on-device extraction and conversion stack works reliably on a real Android phone before adding the full desktop feature set.

## Current features

- native Kotlin / Jetpack Compose app
- dark interface matching the desktop direction
- paste a YouTube URL
- Android share target:
  - YouTube app
  - Share
  - YouTube Downloader
- MP3 download
- 320 kbps audio conversion
- progress and ETA
- cancellation
- Android MediaStore publishing
- output folder:
  - Downloads/YouTube Downloader

## Android engine

V0.1 uses:

- youtubedl-android 0.18.1
- bundled yt-dlp/Python integration
- bundled QuickJS support for modern YouTube JavaScript challenges
- bundled FFmpeg support for MP3 extraction/conversion

The source media is first processed in the app's temporary storage. The completed MP3 is then published through Android MediaStore into the public Downloads folder. This avoids relying on broad storage permissions on modern Android.

## Requirements

- Android 7.0 / API 24 or newer
- arm64-v8a or x86_64 device
- internet access

The primary real-device target is modern arm64 Android phones, including current Samsung Galaxy devices.

## Install the test APK

The easiest route is the repository's GitHub Actions build:

1. Go to the repository.
2. Open Actions.
3. Select **Build Android APK**.
4. Open the latest successful run.
5. Download **YouTubeDownloader-Android-POC**.
6. Extract the artifact ZIP.
7. Install **app-debug.apk** on the phone.

Because this is a private debug build, Android may require permission for the browser/files app to install unknown apps.

## Test plan

For the first real-phone test:

1. Launch YouTube Downloader.
2. Paste a short authorised YouTube URL.
3. Tap **Download MP3 • 320 kbps**.
4. Confirm the progress indicator moves.
5. Confirm the download completes.
6. Open the phone's Downloads folder.
7. Confirm the MP3 exists in:
   - Downloads/YouTube Downloader
8. Play the MP3.
9. Repeat using:
   - YouTube app → Share → YouTube Downloader
10. Test Cancel during a download.

If extraction fails, capture the error text shown in the app.

## Planned next Android phases

After V0.1 works on a real device:

1. metadata preview
2. MP4 video
3. WAV audio
4. MP4 quality selection
5. queue
6. foreground/background download service
7. persistent notification progress
8. output-folder selection
9. update handling for yt-dlp
10. release-signed APK/AAB packaging

## Building locally

The project uses Gradle and Android SDK 35.

GitHub Actions builds with:

- JDK 17
- Gradle 8.9
- Android SDK 35
- Build Tools 35.0.0

Open the `android` directory as a project in Android Studio, or build from a machine with the required SDK/Gradle environment.

## Distribution note

This APK is currently for private testing. The Android dependency stack includes GPL-licensed components. Licensing and redistribution obligations must be reviewed before public distribution or app-store publication.
