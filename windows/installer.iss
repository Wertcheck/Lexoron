; Inno-Setup-Skript für die Windows-Installation (Prompt 36; App-Icon
; Prompt 47; Installation unter %LocalAppData% ohne Admin-Rechte Schritt 3).
;
; Voraussetzung: der PyInstaller-Build liegt bereits unter dist\kanzlei_ai\
; (siehe windows\kanzlei_ai.spec bzw. windows\build.ps1, das beide Schritte
; nacheinander ausführt). Übersetzen mit dem Inno-Setup-Compiler (ISCC.exe,
; Teil der kostenlosen Inno-Setup-Installation von jrsoftware.org):
;
;     iscc windows\installer.iss
;
; WICHTIG zu relativen Pfaden in dieser Datei: Inno Setup löst sie relativ
; zum Speicherort DIESES Skripts auf (windows\), nicht relativ zum
; Projekt-Root - daher unten "app_icon.ico" (liegt direkt daneben in
; windows\), NICHT "windows\app_icon.ico" (das würde windows\windows\...
; suchen und fehlschlagen). Aus demselben Grund referenziert [Files] oben
; bereits "..\dist\kanzlei_ai\*".
; Installiert AUSSCHLIESSLICH den Programmordner (Code, Templates,
; statische Assets, Migrationsskripte) unter %LocalAppData%\KanzleiAI (bis
; Prompt 36-Schritt 3 unter {autopf}\"Program Files") - KEINE Mandantendaten.
; Konfiguration/Datenbank/Dokumente entstehen erst beim ersten Start des
; Setup-Assistenten (app/setup/, Prompt 37) weiterhin unter
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
; Geaendert (Schritt 3, 20.08.): Installation je Windows-Benutzerkonto unter
; %LocalAppData%\KanzleiAI statt {autopf} ("Program Files") - Ziel laut
; Vorgabe: Updates ohne Windows-Administratorrechte moeglich, da
; %LocalAppData% vom jeweiligen Benutzerkonto selbst beschreibbar ist. Bricht
; bewusst mit der Prompt-36-Entscheidung (Program Files) - eine bereits
; unter Program Files installierte Pilot-Instanz muss vor der Installation
; dieser Version manuell deinstalliert werden (siehe RELEASE_NOTES.md),
; sonst entstehen zwei parallele Installationen.
DefaultDirName={localappdata}\KanzleiAI
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
; Fester Dateiname "KanzleiAI_Setup.exe" (bewusst OHNE Versionsnummer im
; Namen, auf ausdrücklichen Wunsch) - Kehrseite: ein neuer Build
; überschreibt in dist\installer\ den vorherigen, es liegen also nie
; mehrere Versionsstände parallel. Falls künftig mehrere Versionen
; nebeneinander aufbewahrt werden sollen (z. B. für ein Rollback), einfach
; wieder "KanzleiAI_Setup-{#MyAppVersion}" verwenden.
OutputBaseFilename=KanzleiAI_Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
; Geaendert (Schritt 3): "lowest" statt "admin" - keine UAC-Erhoehung mehr
; noetig, konsistent mit der Installation unter %LocalAppData% oben. Das
; persistente Datenverzeichnis (%PROGRAMDATA%\KanzleiAI, siehe
; app/setup/paths.py) bleibt unveraendert - dort war ohnehin nie eine
; Admin-Erhoehung fuer den Setup-Assistenten noetig (laeuft unter dem Konto
; des Anwalts/der Kanzleimitarbeiter).
PrivilegesRequired=lowest
; Anwendungssymbol fuer den Installer selbst (Setup.exe-Datei-Icon,
; Titelleiste, Add/Remove-Programme-Eintrag) - Prompt 47. Aktuell ein
; generierter Platzhalter (siehe windows/generate_placeholder_icon.py),
; kein echtes Kanzlei-/Produktlogo - siehe "Kein WizardImageFile/Branding"
; unten, dieselbe Einordnung gilt hier: austauschbar, sobald ein echtes
; Logo vorliegt, ohne dieses Skript sonst anzufassen.
SetupIconFile=app_icon.ico
; Kein WizardImageFile/Branding an dieser Stelle - kanzleispezifisches
; Branding ist Teil der zurückgestellten "Multi-Kanzlei-Profile"-Frage
; (Prompt 38), siehe PROMPT38_ANALYSIS.md - hier bewusst NICHT vorweggenommen.
; Icon fuer den Eintrag unter "Apps & Features"/"Programme und Funktionen" -
; ohne diese Zeile wuerde Windows dort ein generisches Deinstaller-Icon
; zeigen statt des tatsaechlichen App-Icons.
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Files]
Source: "..\dist\kanzlei_ai\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
; Startmenü-Verknüpfung ist immer da (siehe [Icons] unten, kein Task
; nötig). Desktop-Verknüpfung bleibt abwählbar (Task statt fester
; [Icons]-Zeile), ist aber seit dieser Anfrage ("Desktop- und
; Startmenü-Verknüpfungen anlegen") standardmäßig ANGEHAKT - vorher
; bewusst unchecked (nicht jeder wollte einen weiteren Desktop-Eintrag),
; jetzt Standardverhalten mit weiterhin vorhandener Abwahlmöglichkeit im
; Installationsassistenten.
Name: "desktopicon"; Description: "Desktop-Verknüpfung anlegen"; GroupDescription: "Zusätzliche Symbole:"

[Icons]
; IconFilename explizit gesetzt (Prompt 47) statt sich auf Inno Setups
; Standardverhalten zu verlassen (das ohne diese Angabe automatisch das in
; kanzlei_ai.exe eingebettete Icon - siehe windows/kanzlei_ai.spec,
; EXE(icon=...) - übernommen hätte, im Ergebnis identisch, hier aber
; ausdrücklich dokumentiert statt implizit).
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} jetzt starten (öffnet beim allerersten Start den Setup-Assistenten in einem Konsolenfenster)"; Flags: postinstall nowait skipifsilent

; BEWUSST KEIN [UninstallDelete]-Abschnitt für %PROGRAMDATA%\KanzleiAI:
; dieses Verzeichnis enthält vollständige, unpseudonymisierte
; Mandanteninhalte (Datenbank, Dokumente) - eine Deinstallation darf das
; NIEMALS automatisch löschen. Eine bewusste Datenlöschung bleibt dem
; Betreiber vorbehalten (siehe ARCHITECTURE.md, Abschnitt zu Backup/Export,
; Prompt 35, wo dieselbe Sensibilität bereits dokumentiert ist).
