@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo Kids Church Video Downloader - Windows Build
echo ============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher "py" was not found.
    pause
    exit /b 1
)

if not exist ffmpeg.exe (
    echo ffmpeg.exe is missing from this folder.
    echo Copy a Windows ffmpeg.exe here before building.
    pause
    exit /b 1
)

py -m pip install -r requirements.txt
if errorlevel 1 goto :fail

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

py -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name KidsChurchVideoDownloader ^
  --collect-all yt_dlp ^
  main.py

if errorlevel 1 goto :fail

copy /y ffmpeg.exe "dist\KidsChurchVideoDownloader\ffmpeg.exe" >nul

echo.
echo Build complete:
echo dist\KidsChurchVideoDownloader\KidsChurchVideoDownloader.exe
echo.
pause
exit /b 0

:fail
echo.
echo Build failed.
pause
exit /b 1
