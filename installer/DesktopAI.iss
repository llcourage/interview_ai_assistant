; ========================================
; Desktop AI
; Inno Setup Installer Script
; ========================================

[Setup]
AppName=Desktop AI
AppVersion=1.0.0
AppPublisher=DesktopAI
AppPublisherURL=https://www.desktopai.org
DefaultDirName={pf}\DesktopAI
DefaultGroupName=DesktopAI
OutputBaseFilename=DesktopAI-Setup-1.0.0
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
DisableProgramGroupPage=yes
DisableWelcomePage=no
WizardImageFile=
WizardSmallImageFile=
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
SetupIconFile=
UninstallDisplayIcon={app}\Launcher.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; Launcher.exe
Source: "release_root\Launcher.exe"; DestDir: "{app}"; Flags: ignoreversion

; Backend directory (contains backend.exe and all dependencies)
Source: "release_root\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs

; Frontend static files (if exists)
Source: "release_root\ui\*"; DestDir: "{app}\ui"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{src}\release_root\ui'))

[Icons]
Name: "{group}\Desktop AI"; Filename: "{app}\Launcher.exe"
Name: "{group}\{cm:UninstallProgram,Desktop AI}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Desktop AI"; Filename: "{app}\Launcher.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Desktop AI"; Filename: "{app}\Launcher.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\Launcher.exe"; Description: "{cm:LaunchProgram,Desktop AI}"; Flags: nowait postinstall skipifsilent

[Code]
function DirExists(DirName: String): Boolean;
begin
  Result := DirExists(DirName);
end;

