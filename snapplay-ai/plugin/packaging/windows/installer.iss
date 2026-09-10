; Inno Setup 6.3+ script for the VST3 installer. Every product value arrives as a
; preprocessor define from package.ps1 (/DProductName=... etc.); nothing is hard-coded here.
;
; Installs <ProductName>.vst3 (a bundle directory) into {commoncf64}\VST3, 64-bit only, with
; admin rights, an uninstaller under Program Files\<Publisher>\<ProductName>, and the licence
; text rendered from legal/eula.md plus THIRD_PARTY_LICENSES.md as the notices file. Signing: the release workflow signs the produced exe
; afterwards (sign.ps1 / Azure Artifact Signing); define SignTool for a local Inno-driven
; signing configuration instead.

#ifndef ProductName
  #error Pass /DProductName=... (see packaging/windows/package.ps1)
#endif
#ifndef ProductSlug
  #error Pass /DProductSlug=...
#endif
#ifndef Version
  #error Pass /DVersion=... (X.Y.Z or X.Y.Z-prerelease)
#endif
#ifndef VersionNumeric
  #error Pass /DVersionNumeric=X.Y.Z
#endif
#ifndef Publisher
  #error Pass /DPublisher=...
#endif
#ifndef PublisherUrl
  #error Pass /DPublisherUrl=...
#endif
#ifndef BundleId
  #error Pass /DBundleId=...
#endif
#ifndef CopyrightHolder
  #define CopyrightHolder Publisher
#endif
#ifndef SourceDir
  #error Pass /DSourceDir=<path to the built .vst3 bundle directory>
#endif
#ifndef LicenseFile
  #error Pass /DLicenseFile=<plain-text licence>
#endif
#ifndef NoticesFile
  #error Pass /DNoticesFile=<plain-text third-party notices>
#endif
#ifndef OutputDir
  #define OutputDir "dist"
#endif
#ifndef OutputBaseName
  #define OutputBaseName ProductSlug + "-" + Version + "-Windows-Setup"
#endif

[Setup]
AppId={#BundleId}.vst3
AppName={#ProductName}
AppVersion={#Version}
AppVerName={#ProductName} {#Version}
AppPublisher={#Publisher}
AppPublisherURL={#PublisherUrl}
AppSupportURL={#PublisherUrl}
AppUpdatesURL={#PublisherUrl}
AppCopyright=Copyright (C) {#CopyrightHolder}
VersionInfoVersion={#VersionNumeric}
VersionInfoProductName={#ProductName}
VersionInfoProductTextVersion={#Version}
VersionInfoCompany={#Publisher}
DefaultDirName={commoncf64}\VST3\{#ProductName}.vst3
DisableDirPage=yes
DisableProgramGroupPage=yes
DefaultGroupName={#ProductName}
UninstallFilesDir={commonpf64}\{#Publisher}\{#ProductName}
UninstallDisplayName={#ProductName} {#Version}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
MinVersion=10.0
LicenseFile={#LicenseFile}
InfoAfterFile={#NoticesFile}
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
#ifdef SignTool
SignTool={#SignTool}
SignedUninstaller=yes
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; Third-party notices beside the bundle (BSD/MIT/Apache components require them to ship).
Source: "{#NoticesFile}"; DestDir: "{commoncf64}\VST3"; DestName: "{#ProductName} Third-Party Notices.txt"; Flags: ignoreversion

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
