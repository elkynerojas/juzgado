; Instalador de Control de Procesos (Inno Setup 6).
; Primero se construye la aplicación con PyInstaller; luego:
;   ISCC packaging\instalador.iss
; El instalador queda en dist\ControlProcesos-Setup-<versión>.exe

#define Nombre "Control de Procesos"
#define Version "1.1"
#define Desarrollador "RedSoft Developers"
#define Exe "ControlProcesos.exe"
#define Puerto "8765"
#define ReglaFirewall "Control de Procesos"

[Setup]
AppId={{6E2B1C7A-52D4-4C0B-9B1E-0B6C7D3A9F41}
AppName={#Nombre}
AppVersion={#Version}
AppPublisher={#Desarrollador}
AppContact=redsoftdevelopers@gmail.com
AppSupportPhone=+57 318 220 41 90
VersionInfoVersion={#Version}
VersionInfoCompany={#Desarrollador}
VersionInfoCopyright=Copyright (C) {#Desarrollador}
DefaultDirName={autopf}\ControlProcesos
DefaultGroupName={#Nombre}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#Exe}
OutputDir=..\dist
OutputBaseFilename=ControlProcesos-Setup-{#Version}
SetupIconFile=icono.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
Name: "firewall"; Description: "Permitir conexiones de otros equipos de la red (puerto {#Puerto}). Márquelo solo en el equipo servidor"; GroupDescription: "Equipo servidor:"; Flags: unchecked
Name: "inicio"; Description: "Iniciar con Windows, en segundo plano. Recomendado en el equipo servidor"; GroupDescription: "Equipo servidor:"; Flags: unchecked

[Dirs]
; La base de datos y los respaldos del servidor viven aquí; cualquier usuario del equipo debe poder escribir.
Name: "{commonappdata}\ControlProcesos"; Permissions: users-modify

[Files]
Source: "..\dist\ControlProcesos\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#Nombre}"; Filename: "{app}\{#Exe}"
Name: "{autodesktop}\{#Nombre}"; Filename: "{app}\{#Exe}"; Tasks: escritorio
Name: "{commonstartup}\{#Nombre}"; Filename: "{app}\{#Exe}"; Parameters: "--bandeja"; Tasks: inicio

[Run]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#ReglaFirewall}"""; Flags: runhidden; Tasks: firewall
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#ReglaFirewall}"" dir=in action=allow protocol=TCP localport={#Puerto} profile=private,domain"; Flags: runhidden; Tasks: firewall
Filename: "{app}\{#Exe}"; Description: "Abrir {#Nombre}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#ReglaFirewall}"""; Flags: runhidden; RunOnceId: "QuitarFirewall"

[Code]
// La ventana usa el motor de Microsoft Edge (WebView2). Viene con Windows 11 y con Windows 10 actualizado.
function TieneWebView2(): Boolean;
var
  Version: String;
begin
  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0'));
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not TieneWebView2() then
    Result := MsgBox('Este equipo no tiene Microsoft Edge WebView2, que la aplicación necesita para mostrar su ventana.' + #13#10 + #13#10 +
      'Instálelo desde https://developer.microsoft.com/microsoft-edge/webview2/ (Evergreen Bootstrapper) y vuelva a ejecutar este instalador.' + #13#10 + #13#10 +
      '¿Desea continuar de todas formas?', mbConfirmation, MB_YESNO) = IDYES;
end;
