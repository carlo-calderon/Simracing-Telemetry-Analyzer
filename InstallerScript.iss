; Script de Inno Setup para Simracing Telemetry Analyzer

[Setup]
AppName=Simracing Telemetry Analyzer
AppVersion=1.0.0
AppPublisher=CarcaldeF1
DefaultDirName={autopf}\Simracing Telemetry Analyzer
DefaultGroupName=Simracing Telemetry Analyzer
OutputDir=./dist
OutputBaseFilename=SimracingTelemetryAnalyzer_v1.0.0_setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Esta es la línea clave: copia todo el contenido de tu carpeta dist a la carpeta de instalación
Source: "C:\Users\carlo\develop\Simracing-Telemetry-Analyzer\dist\Simracing Telemetry Analyzer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Crea un icono en el Menú Inicio y en el Escritorio
Name: "{group}\Simracing Telemetry Analyzer"; Filename: "{app}\Simracing Telemetry Analyzer.exe"
Name: "{commondesktop}\Simracing Telemetry Analyzer"; Filename: "{app}\Simracing Telemetry Analyzer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Simracing Telemetry Analyzer.exe"; Description: "{cm:LaunchProgram,Simracing Telemetry Analyzer}"; Flags: nowait postinstall skipifsilent