; Inno Setup script for iPhone Media Sync.
; Packages the PyInstaller folder build (dist\iPhoneMediaSync\) into a single
; Setup .exe with Start-menu / desktop shortcuts and an uninstaller.
;
; Build (after running PyInstaller):
;   iscc /DMyAppVersion=1.1.0 installer\iphone-media-sync.iss
; Output:
;   installer\output\iPhoneMediaSync-Setup-<version>.exe

#define MyAppName "iPhone Media Sync"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppExeName "iPhoneMediaSync.exe"
#define MyAppPublisher "iPhone Media Sync"

[Setup]
; A stable AppId so upgrades replace the previous install cleanly.
AppId={{8B6F2C1E-4D3A-4E9B-9C2D-1A7F5E0B3C44}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\iPhoneMediaSync
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=iPhoneMediaSync-Setup-{#MyAppVersion}
SetupIconFile=..\assets\favicon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Everything PyInstaller produced in the folder build.
Source: "..\dist\iPhoneMediaSync\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
