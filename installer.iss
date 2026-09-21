#define MyAppName "KidsChurch Video Downloader"
#define MyAppVersion "0.7.0"
#define MyAppPublisher "Jordan Haagensen"
#define MyAppExeName "KidsChurchVideoDownloader.exe"

[Setup]
AppId={{8B13D9C5-7E09-4C4F-A84E-CCF8C18AF497}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\KidsChurch Video Downloader
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=KidsChurchVideoDownloader_Setup_v0.7.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
SetupIconFile=assets\generated\youtube_downloader.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[InstallDelete]
Type: files; Name: "{app}\YouTubeDownloader.exe"
Type: files; Name: "{autoprograms}\YouTube Downloader.lnk"
Type: files; Name: "{autodesktop}\YouTube Downloader.lnk"

[Files]
Source: "dist\KidsChurchVideoDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
