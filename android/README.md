# YouTube Downloader — Android V0.3

Native Android version of YouTube Downloader.

## V0.3 features

Output modes:

- **MP4 Video** — 1080p / 720p / 480p
- **MP3 Audio** — 320 kbps
- **WAV Audio** — uncompressed PCM

The app also includes:

- native Kotlin / Jetpack Compose UI
- polished adaptive launcher icon
- paste a YouTube URL
- **YouTube → Share → YouTube Downloader** share target
- progress percentage
- **live download speed**
- **estimated time remaining**
- cancellation
- Android MediaStore publishing
- output to **Downloads/YouTube Downloader**
- automatic yt-dlp stable update check before the first download of each launch
- installed yt-dlp version displayed in the status card
- READY / DOWNLOADING / COMPLETE / FAILED status badge
- completed file card with **OPEN WITH…** action

## Download metrics

While yt-dlp is transferring media, the status section shows three separate values:

- Progress
- Speed
- Time left

Speed is read from yt-dlp's live download output. ETA is supplied by the Android yt-dlp wrapper. During merging or audio conversion, the network transfer may already be finished, so speed and time left can show `—`.

## Opening a completed file

After a download completes, tap its finished-file card. V0.3 deliberately launches Android's **Open with…** chooser rather than silently forcing a particular player.

That lets you choose any compatible installed app for the file type, such as a video player, music player, editor, file manager, or sharing-capable media app.

## MP4 compatibility approach

The desktop app can afford to fully transcode video to a presentation-friendly final file. On a phone, full 1080p transcoding is much more expensive in battery, heat, and time.

Android therefore prefers H.264 video plus AAC audio from YouTube and merges those streams into MP4 when available. This provides broad compatibility without unnecessarily re-encoding the whole video.

## yt-dlp update behaviour

The first Android phone test exposed an HTTP 403 issue caused by an older bundled yt-dlp build. The app checks the official stable yt-dlp release before the first download of each launch and displays the active engine version for troubleshooting.

## Install

1. Open the repository on GitHub.
2. Go to **Actions**.
3. Select **Build Android APK**.
4. Open the latest green run.
5. Download **YouTubeDownloader-Android-v0.3**.
6. Extract the ZIP.
7. Install `app-debug.apk`.

Android may require permission for the browser or Files app to install unknown apps because this is a private debug APK.

## Test checklist

Use media you are authorised to download.

1. MP3 download
2. WAV download
3. MP4 480p
4. MP4 720p
5. MP4 1080p
6. confirm **Speed** changes during download
7. confirm **Time left** is populated during download
8. YouTube → Share → YouTube Downloader
9. cancel during a download
10. duplicate filename handling
11. verify files appear in **Downloads/YouTube Downloader**
12. tap a completed file
13. confirm Android displays the **Open with…** chooser
14. choose a compatible app and play/open the file

If a download fails, capture the full error shown in the status card and the displayed yt-dlp engine version.

## Planned next phase

- metadata/title preview
- download queue
- foreground service for long/background downloads
- persistent notification progress
- output-folder selection
- signed release APK/AAB

## Technical stack

- Android API 24+
- Kotlin
- Jetpack Compose
- youtubedl-android 0.18.1
- yt-dlp updated on-device to current stable
- QuickJS
- FFmpeg
- Android MediaStore

## Distribution note

This APK is currently for private development/testing. Licensing and redistribution obligations for bundled GPL components must be reviewed before public distribution or app-store publication.
