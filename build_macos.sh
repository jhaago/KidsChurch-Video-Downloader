#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

APP_NAME="YouTube Downloader"
BUNDLE_ID="com.jordanhaagensen.youtubedownloader"
ARCH="$(uname -m)"

if [[ "$ARCH" == "arm64" ]]; then
  ARCH_LABEL="AppleSilicon"
elif [[ "$ARCH" == "x86_64" ]]; then
  ARCH_LABEL="Intel"
else
  echo "Unsupported architecture: $ARCH"
  exit 1
fi

echo "=========================================="
echo "YouTube Downloader V0.6.4 - macOS $ARCH_LABEL"
echo "=========================================="
echo ""

python3 -c "import tkinter; print('Tkinter OK')"
python3 -m pip install -r requirements.txt
python3 -m py_compile main.py
python3 assets/generate_icons.py --platform macos

chmod +x prepare_tools_macos.sh
./prepare_tools_macos.sh

rm -rf build dist macos_output macos_package

python3 -m PyInstaller   --noconfirm   --clean   --windowed   --onedir   --name "$APP_NAME"   --icon assets/generated/youtube_downloader.icns   --osx-bundle-identifier "$BUNDLE_ID"   main.py

APP="dist/$APP_NAME.app"
MACOS_DIR="$APP/Contents/MacOS"

if [[ ! -d "$APP" ]]; then
  echo "PyInstaller did not create $APP"
  exit 1
fi

cp tools/yt-dlp "$MACOS_DIR/yt-dlp"
cp tools/deno "$MACOS_DIR/deno"
cp tools/ffmpeg "$MACOS_DIR/ffmpeg"
cp tools/ffprobe "$MACOS_DIR/ffprobe"
cp THIRD_PARTY_NOTICES.md "$MACOS_DIR/THIRD_PARTY_NOTICES.md"

chmod +x "$MACOS_DIR/yt-dlp" "$MACOS_DIR/deno" "$MACOS_DIR/ffmpeg" "$MACOS_DIR/ffprobe"

xattr -cr "$APP" 2>/dev/null || true

echo "Applying ad-hoc code signature..."
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"

echo "Verifying bundled tools..."
"$MACOS_DIR/yt-dlp" --version
"$MACOS_DIR/deno" --version | head -n 1
"$MACOS_DIR/ffmpeg" -version | head -n 1
"$MACOS_DIR/ffmpeg" -hide_banner -encoders 2>/dev/null | grep -q "libx264"
"$MACOS_DIR/ffmpeg" -hide_banner -encoders 2>/dev/null | grep -q "libmp3lame"

mkdir -p macos_output macos_package
cp -R "$APP" "macos_package/$APP_NAME.app"

ZIP_PATH="macos_output/YouTubeDownloader-macOS-$ARCH_LABEL-v0.6.4.zip"
DMG_PATH="macos_output/YouTubeDownloader-macOS-$ARCH_LABEL-v0.6.4.dmg"

echo "Creating app ZIP..."
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP_PATH"

echo "Creating DMG..."
hdiutil create   -volname "$APP_NAME"   -srcfolder macos_package   -ov   -format UDZO   "$DMG_PATH"

echo ""
echo "macOS build complete:"
echo "  $ZIP_PATH"
echo "  $DMG_PATH"
