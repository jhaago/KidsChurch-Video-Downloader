# YouTube Downloader — Android V0.2.2

Native Android version of YouTube Downloader.

## V0.2.2 features

Android V0.2.2 supports three output modes:

- **MP4 Video**
  - 1080p
  - 720p
  - 480p
  - prefers H.264 video and AAC audio so the result is broadly compatible without forcing a full phone-side video transcode
- **MP3 Audio**
  - 320 kbps
- **WAV Audio**
  - uncompressed PCM

It also includes:

- native Kotlin / Jetpack Compose UI
- polished adaptive launcher icon
- YouTube URL paste
- Android share target:
  - YouTube
  - Share
  - YouTube Downloader
- progress and ETA
- cancellation
- Android MediaStore publishing
- output to:
  - Downloads/YouTube Downloader
- completed download card is tappable and opens the file through Android's normal/default file-type handler
- yt-dlp stable update check before the first download of each launch
- installed yt-dlp version shown in the status card
- clear READY / DOWNLOADING / COMPLETE / FAILED status badge

## V0.2.2 icon refinement

Real-device testing on a Samsung launcher showed that the earlier icon artwork was too close to the adaptive-icon mask and looked clipped/unrefined.

V0.2.2 switches to the newer approved visual direction:

- soft white rounded tile
- red play panel
- white play symbol
- white download arrow/tray
- extra safe-zone padding so the artwork stays clean under rounded-square, circular and other launcher masks

## Opening a completed download

After an MP4, MP3 or WAV finishes, the completed file appears as a tappable card in the status section.

Tapping the card sends the file to Android with the correct MIME type using the normal `ACTION_VIEW` flow. Android then opens the file in the phone's default/available app for that type rather than playing it inside YouTube Downloader.

Examples:

- MP4 → video player/gallery app
- MP3 → music/audio player
- WAV → audio player/editor

If Android has more than one suitable app and no default is set, Android may show its normal app chooser.

## Why MP4 prefers H.264/AAC

The desktop app can afford to fully transcode downloaded video to its final PowerPoint-friendly format.

On a phone, full 1080p video transcoding is much more expensive in battery, heat and time. Android therefore asks YouTube/yt-dlp for H.264 video plus AAC audio directly and merges those streams into MP4.

That gives a fast path to a broadly compatible MP4 without unnecessarily re-encoding the whole video.

## yt-dlp update behaviour

The first V0.1 phone test exposed an HTTP 403 issue caused by an older bundled yt-dlp build.

V0.1.1 fixed this by updating yt-dlp to the current stable release before the first download of each app launch. V0.2.2 retains that behaviour.

## Install

1. Open the repository on GitHub.
2. Go to **Actions**.
3. Select **Build Android APK**.
4. Open the latest green run.
5. Download **YouTubeDownloader-Android-v0.2.2**.
6. Extract the ZIP.
7. Install **app-debug.apk**.

Android may require permission for the browser/files app to install unknown apps because this is a private debug APK.

## Test checklist

Use media you are authorised to download.

Test:

1. MP3 download
2. WAV download
3. MP4 480p
4. MP4 720p
5. MP4 1080p
6. YouTube → Share → YouTube Downloader
7. Cancel during a download
8. duplicate filename handling
9. verify completed files appear in:
   - Downloads/YouTube Downloader
10. tap each completed file inside YouTube Downloader
11. confirm Android opens it in the normal/default app for MP4, MP3 or WAV
12. check the refined launcher icon on the phone's home/app screen

If a download fails, capture the full error shown in the status card and the displayed yt-dlp engine version.

## Planned next phase

After V0.2.2 real-device testing:

1. metadata/title preview
2. download queue
3. foreground service for long/background downloads
4. persistent notification progress
5. output-folder selection
6. signed release APK/AAB

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
