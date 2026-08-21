' Start.vbs - startet Lexono ohne sichtbares Konsolenfenster (Schritt 3,
' "produktiver Piloteinsatz"; Local-First-Architektur 20.08., siehe
' ARCHITECTURE.md §60).
'
' WICHTIGE AUSNAHME (bewusst, kein Versehen): Beim ALLERERSTEN Start - wenn
' im persistenten Datenverzeichnis noch keine .env existiert - braucht der
' interaktive Setup-Assistent (E-Mail-/Passwort-Abfrage in der Konsole,
' siehe app/setup/wizard.py, run.py: cmd_setup) eine SICHTBARE Konsole.
' Eine von Anfang an versteckte Konsole würde dort unsichtbar auf eine
' Tastatureingabe warten, die nie ankommen kann - die App würde scheinbar
' "hängen", ohne dass der Anwalt/die Kanzleimitarbeiterin einen Hinweis
' bekäme. Deshalb: erster Start SICHTBAR (wie bisher), jeder weitere Start
' STUMM (Server-Logs stdout/stderr -> app.log neben diesem Skript).
'
' Ersetzt keinen bestehenden Mechanismus - ruft lediglich denselben Befehl
' auf, den auch die Startmenü-/Desktop-Verknüpfung (windows/installer.iss)
' verwendet, nur mit unterdrücktem Konsolenfenster.

Option Explicit

Dim objShell, objFSO, strScriptDir, strDataDir, strProgramData
Dim strEnvPath, strExePath, strPythonExe, strRunPy, strLogPath, strCommand
Dim strRedirectedCommand

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strLogPath = strScriptDir & "\app.log"

' Persistentes Datenverzeichnis - identische Ableitung wie
' app/setup/paths.py (resolve_data_dir): KANZLEI_AI_DATA_DIR-Override,
' sonst %PROGRAMDATA%\KanzleiAI.
strDataDir = objShell.ExpandEnvironmentStrings("%KANZLEI_AI_DATA_DIR%")
If strDataDir = "%KANZLEI_AI_DATA_DIR%" Then
    strProgramData = objShell.ExpandEnvironmentStrings("%PROGRAMDATA%")
    strDataDir = strProgramData & "\KanzleiAI"
End If
strEnvPath = strDataDir & "\.env"

' Gebündelte .exe (neben diesem Skript, z. B. nach der Installation)
' bevorzugt, sonst Entwicklungsbetrieb über die venv-Python-Installation
' im Projekt-Root (dieses Skript liegt dort - "Hauptverzeichnis").
strExePath = strScriptDir & "\kanzlei_ai.exe"
If Not objFSO.FileExists(strExePath) Then
    strExePath = strScriptDir & "\dist\kanzlei_ai\kanzlei_ai.exe"
End If

If objFSO.FileExists(strExePath) Then
    strCommand = """" & strExePath & """ serve"
Else
    strPythonExe = strScriptDir & "\.venv\Scripts\python.exe"
    strRunPy = strScriptDir & "\run.py"
    strCommand = """" & strPythonExe & """ """ & strRunPy & """ serve"
End If

If objFSO.FileExists(strEnvPath) Then
    ' Bereits eingerichtet: stummer Start, komplett verstecktes Fenster
    ' (0 = SW_HIDE), alle Server-Logs (stdout/stderr) landen in app.log.
    '
    ' strRedirectedCommand ist z. B.:
    '   "C:\...\python.exe" "C:\...\run.py" serve >> "C:\...\app.log" 2>&1
    strRedirectedCommand = strCommand & " >> """ & strLogPath & """ 2>&1"

    ' WICHTIG zur zusaetzlichen Aussen-Anfuehrung um strRedirectedCommand:
    ' bekannter cmd.exe-/c-Bug - beginnt die Befehlszeile nach /c mit einem
    ' Anfuehrungszeichen (hier: der zitierte .exe-Pfad), entfernt cmd.exe
    ' bei bestimmten Konstellationen faelschlich BEIDE aeusseren Anfuehrungs-
    ' zeichen (das oeffnende vor dem Programmpfad UND das schliessende nach
    ' dem Log-Pfad) und zerstoert damit die Befehlszeile - beobachtet und
    ' verifiziert waehrend der Umsetzung dieses Schritts (echter Testlauf:
    ' ohne das zusaetzliche aeussere Anfuehrungszeichenpaar bricht der Start
    ' kommentarlos ab, keine app.log entsteht). Der Standard-Workaround ist
    ' ein zusaetzliches, rein umschliessendes Anfuehrungszeichenpaar um die
    ' GESAMTE Befehlszeile - cmd.exe entfernt dann nur dieses aeusserste
    ' Paar, die eigentliche (bereits korrekt zitierte) Befehlszeile bleibt
    ' unangetastet.
    objShell.Run "cmd /c """ & strRedirectedCommand & """", 0, False
Else
    ' Allererster Start: Setup-Assistent braucht eine sichtbare,
    ' interaktive Konsole - NICHT verstecken (1 = normales Fenster).
    objShell.Run strCommand, 1, False
End If
