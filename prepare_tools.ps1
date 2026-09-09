$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Tools = Join-Path $Root "tools"
$Temp = Join-Path $env:TEMP "KidsChurchVideoDownloaderTools"

New-Item -ItemType Directory -Force -Path $Tools | Out-Null
if (Test-Path $Temp) {
    Remove-Item -Recurse -Force $Temp
}
New-Item -ItemType Directory -Force -Path $Temp | Out-Null

Write-Host "Downloading latest yt-dlp..."
Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -OutFile (Join-Path $Tools "yt-dlp.exe")

Write-Host "Downloading latest Deno..."
$denoRelease = Invoke-RestMethod -Headers @{ "User-Agent" = "KidsChurch-Video-Downloader-build" } -Uri "https://api.github.com/repos/denoland/deno/releases/latest"
$denoAsset = $denoRelease.assets | Where-Object { $_.name -eq "deno-x86_64-pc-windows-msvc.zip" } | Select-Object -First 1

if (-not $denoAsset) {
    throw "Could not locate the Windows x64 Deno release asset."
}

$denoZip = Join-Path $Temp "deno.zip"
$denoExtract = Join-Path $Temp "deno"
Invoke-WebRequest -Uri $denoAsset.browser_download_url -OutFile $denoZip
Expand-Archive -Path $denoZip -DestinationPath $denoExtract -Force
Copy-Item (Join-Path $denoExtract "deno.exe") (Join-Path $Tools "deno.exe") -Force

Write-Host "Downloading latest FFmpeg Windows x64 GPL build..."
$ffmpegRelease = Invoke-RestMethod -Headers @{ "User-Agent" = "YouTube-Downloader-build" } -Uri "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
$ffmpegAsset = $ffmpegRelease.assets | Where-Object {
    $_.name -match "^ffmpeg-.*-win64-gpl\.zip$" -and
    $_.name -notmatch "-shared" -and
    $_.name -notmatch "-gpl-[0-9]"
} | Select-Object -First 1

if (-not $ffmpegAsset) {
    throw "Could not locate the latest Windows x64 GPL FFmpeg release asset."
}

Write-Host ("Using FFmpeg asset: " + $ffmpegAsset.name)
$ffmpegZip = Join-Path $Temp "ffmpeg.zip"
$ffmpegExtract = Join-Path $Temp "ffmpeg"
Invoke-WebRequest -Uri $ffmpegAsset.browser_download_url -OutFile $ffmpegZip
Expand-Archive -Path $ffmpegZip -DestinationPath $ffmpegExtract -Force

$ffmpegExe = Get-ChildItem -Path $ffmpegExtract -Filter "ffmpeg.exe" -Recurse | Select-Object -First 1
$ffprobeExe = Get-ChildItem -Path $ffmpegExtract -Filter "ffprobe.exe" -Recurse | Select-Object -First 1

if (-not $ffmpegExe -or -not $ffprobeExe) {
    throw "FFmpeg archive did not contain ffmpeg.exe and ffprobe.exe."
}

Copy-Item $ffmpegExe.FullName (Join-Path $Tools "ffmpeg.exe") -Force
Copy-Item $ffprobeExe.FullName (Join-Path $Tools "ffprobe.exe") -Force

Write-Host ""
Write-Host "Prepared tools:"
Get-Item (Join-Path $Tools "yt-dlp.exe"), (Join-Path $Tools "deno.exe"), (Join-Path $Tools "ffmpeg.exe"), (Join-Path $Tools "ffprobe.exe") |
    ForEach-Object { Write-Host ("  " + $_.Name + "  " + [math]::Round($_.Length / 1MB, 1) + " MB") }

Remove-Item -Recurse -Force $Temp
Write-Host ""
Write-Host "Tool preparation complete."
