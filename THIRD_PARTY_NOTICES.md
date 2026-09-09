# Third-party notices

Kids Church Video Downloader V0.2 is designed to ship with separate third-party executables beside the application.

## yt-dlp

Project: https://github.com/yt-dlp/yt-dlp

The Windows executable is downloaded from the official yt-dlp GitHub release during the build process. yt-dlp includes its own third-party licensing information in the official distribution.

## Deno

Project: https://github.com/denoland/deno

Deno is used as the JavaScript runtime required for full modern YouTube extraction support in yt-dlp. Deno is distributed under the MIT License.

## FFmpeg

Build source: https://github.com/BtbN/FFmpeg-Builds

FFmpeg project: https://ffmpeg.org/

The current build pipeline uses the Windows x64 GPL static build so that H.264 encoding through libx264 is available for the PowerPoint compatibility conversion.

This V0.2 repository is currently intended for private development and testing. Before wider public redistribution of compiled installers, the third-party license files and source-offer requirements for the exact bundled FFmpeg build should be packaged and reviewed.
