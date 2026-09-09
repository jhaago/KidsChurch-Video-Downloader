@echo off
setlocal
cd /d "%~dp0"

echo ==================================================
echo Kids Church Video Downloader V0.2 - Windows Build
echo ==================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher "py" was not found.
    echo Install Python 3.12 or newer and try again.
    pause
    exit /b 1
)

echo Preparing yt-dlp, Deno and FFmpeg...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0prepare_tools.ps1"
if errorlevel 1 goto :fail

echo.
echo Installing Python build requirements...
py -m pip install -r requirements.txt
if errorlevel 1 goto :fail

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Building application...
py -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --onedir ^
  --name KidsChurchVideoDownloader ^
  main.py

if errorlevel 1 goto :fail

copy /y "tools\yt-dlp.exe" "dist\KidsChurchVideoDownloader\yt-dlp.exe" >nul
copy /y "tools\deno.exe" "dist\KidsChurchVideoDownloader\deno.exe" >nul
copy /y "tools\ffmpeg.exe" "dist\KidsChurchVideoDownloader\ffmpeg.exe" >nul
copy /y "tools\ffprobe.exe" "dist\KidsChurchVideoDownloader\ffprobe.exe" >nul
copy /y "THIRD_PARTY_NOTICES.md" "dist\KidsChurchVideoDownloader\THIRD_PARTY_NOTICES.md" >nul

echo.
echo Build complete:
echo dist\KidsChurchVideoDownloader\KidsChurchVideoDownloader.exe
echo.
echo Run make_installer.bat to create the normal Windows installer.
echo.
pause
exit /b 0

:fail
echo.
echo Build failed.
pause
exit /b 1
