@echo off
setlocal
cd /d "%~dp0"

if not exist "dist\YouTubeDownloader\YouTubeDownloader.exe" (
    echo The application has not been built yet.
    echo Run build_windows.bat first.
    pause
    exit /b 1
)

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not exist "%ISCC%" (
    echo Inno Setup 6 was not found.
    echo Install Inno Setup 6, then run this file again.
    pause
    exit /b 1
)

"%ISCC%" installer.iss
if errorlevel 1 (
    echo Installer build failed.
    pause
    exit /b 1
)

echo.
echo Installer created in installer_output\
echo.
pause
