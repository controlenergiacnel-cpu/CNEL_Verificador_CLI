[Setup]
AppName=CNEL_Verificador_CLI
AppVersion=1.0.0
DefaultDirName={pf}\CNEL_Verificador_CLI
DefaultGroupName=CNEL
OutputBaseFilename=CNEL_Verificador_CLI_Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\dist\CNEL_Verificador_CLI.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\CNEL Verificador CLI"; Filename: "{app}\CNEL_Verificador_CLI.exe"
Name: "{commondesktop}\CNEL Verificador CLI"; Filename: "{app}\CNEL_Verificador_CLI.exe"
