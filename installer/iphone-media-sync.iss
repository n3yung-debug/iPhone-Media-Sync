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

[Code]
{ --- Apple Mobile Device Support bootstrap ---------------------------------
  The app needs Apple Mobile Device Support (the usbmuxd service + USB driver)
  to talk to an iPhone. We can't legally redistribute Apple's installer, so if
  it's missing we download Apple's OFFICIAL iTunes installer and run it (it
  contains Apple Mobile Device Support). The user consents first.
}

const
  AMDS_SERVICE_KEY = 'SYSTEM\CurrentControlSet\Services\Apple Mobile Device Service';
  ITUNES_URL = 'https://www.apple.com/itunes/download/win64';

function AppleMobileDeviceSupportInstalled(): Boolean;
begin
  Result := RegKeyExists(HKLM, AMDS_SERVICE_KEY);
end;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  Result := True;
end;

procedure EnsureAppleMobileDeviceSupport();
var
  ResultCode: Integer;
  Installer: String;
begin
  if AppleMobileDeviceSupportInstalled() then
    exit;

  if MsgBox('iPhone Media Sync needs "Apple Mobile Device Support" (Apple''s USB'
      + ' driver and service) to communicate with your iPhone, and it is not'
      + ' installed yet.' + #13#10#13#10
      + 'Download it now from Apple? This downloads Apple''s official installer'
      + ' and runs it. (Choose No to install it yourself later.)',
      mbConfirmation, MB_YESNO) <> IDYES then
    exit;

  Installer := ExpandConstant('{tmp}\iTunes64Setup.exe');
  try
    DownloadTemporaryFile(ITUNES_URL, 'iTunes64Setup.exe', '', @OnDownloadProgress);
  except
    MsgBox('Could not download Apple Mobile Device Support automatically.'
        + #13#10 + 'Please install iTunes from https://www.apple.com/itunes/'
        + ' (the desktop installer, not the Microsoft Store version).',
        mbError, MB_OK);
    exit;
  end;

  if not Exec(Installer, '', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    MsgBox('Could not launch the Apple installer. Please install iTunes from'
        + ' https://www.apple.com/itunes/ manually.', mbError, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    EnsureAppleMobileDeviceSupport();
end;

