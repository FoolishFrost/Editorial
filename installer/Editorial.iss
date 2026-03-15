; Editorial installer script (unsigned build)
; Build with: ISCC installer\Editorial.iss

#define MyAppName "Editorial"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Foolish Designs"
#define MyAppCreator "John Bowden"
#define MyAppSupportEmail "johnbowden@foolishdesigns.com"
#define MyAppExeName "Editorial.exe"

[Setup]
AppId={{B3E67E77-AC9A-4B70-95F2-047D0D1F9F99}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppContact={#MyAppCreator}
AppCopyright=Copyright (C) 2026 {#MyAppPublisher}
AppPublisherURL="mailto:{#MyAppSupportEmail}"
AppSupportURL="mailto:{#MyAppSupportEmail}"
AppUpdatesURL="https://github.com/FoolishFrost/Editorial/releases/latest"
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=Editorial-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoTextVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent








