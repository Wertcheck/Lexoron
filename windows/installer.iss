; Inno-Setup-Skript für die Windows-Installation (Prompt 36).
;
; Voraussetzung: der PyInstaller-Build liegt bereits unter dist\kanzlei_ai\
; (siehe windows\kanzlei_ai.spec bzw. windows\build.ps1, das beide Schritte
; nacheinander ausführt). Übersetzen mit dem Inno-Setup-Compiler (ISCC.exe,
; Teil der kostenlosen Inno-Setup-Installation von jrsoftware.org):
;
;     iscc windows\installer.iss
;
; Installiert AUSSCHLIESSLICH den Programmordner (Code, Templates,
; statische Assets, Migrationsskripte) unter {autopf}\KanzleiAI - KEINE
; Mandantendaten. Konfiguration/Datenbank/Dokumente entstehen erst beim
; ersten Start des Setup-Assistenten (app/setup/, Prompt 37) unter
; %PROGRAMDATA%\KanzleiAI - bewusst getrennt vom Installationsverzeichnis,
; siehe ARCHITECTURE.md (Programminstallation vs. Anwendungsdaten).

#define MyAppName "Kanzlei-AI"
#define MyAppVersion "0.1.0"
#define MyAppExeName "kanzlei_ai.exe"
#define MyAppPublisher "Kanzlei AI Projekt"

[Setup]
AppId={{9F4B9E7A-2B1E-4C77-9C7C-3D9B5E5B0B21}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\KanzleiAI
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=KanzleiAI-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
; Erfordert Administratorrechte, weil das Standard-Installationsverzeichnis
; ({autopf} = "Program Files") das verlangt. Das persistente
; Datenverzeichnis (%PROGRAMDATA%\KanzleiAI, siehe app/setup/paths.py) wird
; NICHT hier angelegt, sondern erst beim ersten Programmstart durch den
; Setup-Assistenten selbst - der läuft unter dem Konto des Anwalts/der
; Kanzleimitarbeiter, nicht unter dem Installer-Administratorkonto.
PrivilegesRequired=admin
; Kein WizardImageFile/Branding an dieser Stelle - kanzleispezifisches
; Branding ist Teil der zurückgestellten "Multi-Kanzlei-Profile"-Frage
; (Prompt 38), siehe PROMPT38_ANALYSIS.md - hier bewusst NICHT vorweggenommen.

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Files]
Source: "..\dist\kanzlei_ai\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\{#MyAppName} deinstallieren"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} jetzt starten (öffnet beim allerersten Start den Setup-Assistenten in einem Konsolenfenster)"; Flags: postinstall nowait skipifsilent

; BEWUSST KEIN [UninstallDelete]-Abschnitt für %PROGRAMDATA%\KanzleiAI:
; dieses Verzeichnis enthält vollständige, unpseudonymisierte
; Mandanteninhalte (Datenbank, Dokumente) - eine Deinstallation darf das
; NIEMALS automatisch löschen. Eine bewusste Datenlöschung bleibt dem
; Betreiber vorbehalten (siehe ARCHITECTURE.md, Abschnitt zu Backup/Export,
; Prompt 35, wo dieselbe Sensibilität bereits dokumentiert ist).
