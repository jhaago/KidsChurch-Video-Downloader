#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TOOLS="$ROOT/tools"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TOOLS"

ARCH="$(uname -m)"
case "$ARCH" in
  arm64) DENO_ARCH="aarch64" ;;
  x86_64) DENO_ARCH="x86_64" ;;
  *)
    echo "Unsupported macOS architecture: $ARCH"
    exit 1
    ;;
esac

echo "Preparing macOS tools for $ARCH..."

echo "Downloading official yt-dlp macOS universal executable..."
curl --fail --location --retry 3   "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"   --output "$TOOLS/yt-dlp"
chmod +x "$TOOLS/yt-dlp"

echo "Downloading Deno for $ARCH..."
DENO_ZIP="$TMP/deno.zip"
curl --fail --location --retry 3   "https://github.com/denoland/deno/releases/latest/download/deno-$DENO_ARCH-apple-darwin.zip"   --output "$DENO_ZIP"
unzip -q "$DENO_ZIP" -d "$TMP/deno"
cp "$TMP/deno/deno" "$TOOLS/deno"
chmod +x "$TOOLS/deno"

if ! command -v npm >/dev/null 2>&1; then
  echo "Node/npm is required to prepare static FFmpeg binaries."
  echo "Install Node 22+ and run this script again."
  exit 1
fi

echo "Downloading static FFmpeg and ffprobe for $ARCH..."
NPM_DIR="$TMP/npm"
mkdir -p "$NPM_DIR"
cd "$NPM_DIR"
npm init -y >/dev/null 2>&1
npm install --silent --no-audit --no-fund ffmpeg-static@5.3.0 @derhuerst/ffprobe-static@5.3.0

FFMPEG_PATH="$(node -e "process.stdout.write(require('ffmpeg-static'))")"
FFPROBE_PATH="$(node -e "process.stdout.write(require('@derhuerst/ffprobe-static'))")"

cp "$FFMPEG_PATH" "$TOOLS/ffmpeg"
cp "$FFPROBE_PATH" "$TOOLS/ffprobe"
chmod +x "$TOOLS/ffmpeg" "$TOOLS/ffprobe"

xattr -cr "$TOOLS" 2>/dev/null || true

echo "Verifying FFmpeg codecs required by the app..."
"$TOOLS/ffmpeg" -hide_banner -encoders 2>/dev/null | grep -q "libx264" || {
  echo "FFmpeg build does not include libx264."
  exit 1
}
"$TOOLS/ffmpeg" -hide_banner -encoders 2>/dev/null | grep -q "libmp3lame" || {
  echo "FFmpeg build does not include libmp3lame."
  exit 1
}

echo ""
echo "Prepared:"
file "$TOOLS/yt-dlp"
file "$TOOLS/deno"
file "$TOOLS/ffmpeg"
file "$TOOLS/ffprobe"
echo ""
"$TOOLS/yt-dlp" --version
"$TOOLS/deno" --version | head -n 1
"$TOOLS/ffmpeg" -version | head -n 1
echo "macOS tool preparation complete."
