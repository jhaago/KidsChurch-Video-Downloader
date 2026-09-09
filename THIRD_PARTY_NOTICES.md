# Third-party notices

YouTube Downloader ships with separate third-party executables alongside the application runtime.

## yt-dlp

Project: https://github.com/yt-dlp/yt-dlp

Windows builds use the official `yt-dlp.exe` release. macOS builds use the official universal `yt-dlp_macos` release.

yt-dlp includes its own licensing and third-party information in the official distribution.

## Deno

Project: https://github.com/denoland/deno

Deno is used as the JavaScript runtime for modern YouTube extraction support in yt-dlp.

Windows uses the x64 Windows release. macOS builds use the architecture-correct Apple Darwin release for Intel or Apple Silicon.

Deno is distributed under the MIT License.

## FFmpeg / ffprobe

FFmpeg project: https://ffmpeg.org/

### Windows

The Windows build pipeline uses the x64 GPL static build from:

https://github.com/BtbN/FFmpeg-Builds

### macOS

The macOS build pipeline obtains architecture-specific static binaries through:

- https://www.npmjs.com/package/ffmpeg-static
- https://www.npmjs.com/package/@derhuerst/ffprobe-static

Those packages publish macOS Intel and Apple Silicon binaries sourced from established FFmpeg macOS builds.

The build verifies that FFmpeg includes both `libx264` and `libmp3lame`, which are required for the application's MP4 and MP3 output modes.

FFmpeg is also used for AAC audio in MP4 files and PCM WAV output.

## Redistribution status

This repository is currently intended for private development and testing. Before wider public redistribution of compiled installers/DMGs, the exact third-party license texts, GPL source-availability obligations, and Apple signing/notarization process should be packaged and reviewed.


## Android proof-of-concept

The Android proof-of-concept uses the youtubedl-android project:

https://github.com/yausername/youtubedl-android

Current Android dependency version: 0.18.1.

The Android library bundles yt-dlp/Python integration, QuickJS support and an FFmpeg package used for audio extraction/conversion. youtubedl-android is distributed under GPL-3.0.

The Android APK is currently for private development/testing. Licensing and redistribution obligations must be reviewed before any public app-store or general APK distribution.
