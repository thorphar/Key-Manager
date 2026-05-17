; Inno Setup script — version and payload path are passed from CI:
;   iscc installer/KeyManager.iss /DAppVersion=1.2.3 /DSourceDir=..\dist

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#ifndef SourceDir
  #define SourceDir "..\dist"
#endif

#define AppName "Key Manager"
#define AppExe "KeyManager-" + AppVersion + ".exe"
#define OutputBase "KeyManager-" + AppVersion + "-setup"

[Setup]
AppId={{A8F3C2E1-9B4D-4F6A-8C1E-2D5F9A8B3C4E}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
DefaultDirName={autopf}\Key Manager
DefaultGroupName={#AppName}
OutputDir=..\dist
OutputBaseFilename={#OutputBase}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "{#SourceDir}\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
