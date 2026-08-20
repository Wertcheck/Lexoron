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

' Lokaler Ollama-Dienst-Check (Local-First-Architektur) - rein informativ,
' best-effort: schreibt EINE Zeile nach app.log, BEVOR der eigentliche
' Server startet. Der Server selbst fuehrt beim Start UNABHAENGIG davon
' dieselbe Pruefung erneut durch, dort gegen die tatsaechlich konfigurierte
' OLLAMA_BASE_URL aus der .env (siehe app/main.py: _run_silent_ollama_check)
' - dieser Check hier deckt nur den Standardport ab und dient als frueher,
' zusaetzlicher Log-Eintrag, falls der Server aus irgendeinem Grund gar
' nicht erst bis zu seiner eigenen Pruefung kommt. Blockiert/verzoegert den
' eigentlichen App-Start NIE (kurzer Timeout, On Error Resume Next) - eine
' nicht erreichbare lokale Ollama-Instanz ist ein normaler, erwarteter
' Zustand (Ollama evtl. noch nicht gestartet), kein Fehlerfall, der den
' restlichen Ablauf abbrechen duerfte.
CheckOllamaAndLog strLogPath

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

' Prueft den lokalen Ollama-Standardport (Local-First-Architektur, siehe
' ARCHITECTURE.md §60) und haengt EINE Ergebniszeile an app.log an -
' NIEMALS ein Fehler, der WScript.Run oben verhindern duerfte (On Error
' Resume Next umschliesst den gesamten HTTP-Versuch UND den Logschreibzugriff).
Sub CheckOllamaAndLog(strLogFilePath)
    Dim objHttp, objLogFile, strStatusLine

    On Error Resume Next
    Set objHttp = CreateObject("WinHttp.WinHttpRequest.5.1")
    If Err.Number = 0 Then
        objHttp.SetTimeouts 1000, 1000, 1500, 1500
        objHttp.Open "GET", "http://localhost:11434/api/tags", False
        objHttp.Send
        If Err.Number = 0 And objHttp.Status = 200 Then
            strStatusLine = "[Start.vbs] Ollama erreichbar (http://localhost:11434)."
        Else
            strStatusLine = "[Start.vbs] Ollama nicht erreichbar - AI_MODE=LOCAL_ONLY " & _
                "Entwuerfe/Pruefungen schlagen fehl, bis der Dienst laeuft."
        End If
    Else
        strStatusLine = "[Start.vbs] Ollama-Check uebersprungen (WinHTTP nicht verfuegbar)."
    End If
    Err.Clear

    Set objLogFile = objFSO.OpenTextFile(strLogFilePath, 8, True)
    If Err.Number = 0 Then
        objLogFile.WriteLine Now & " " & strStatusLine
        objLogFile.Close
    End If
    On Error Goto 0
End Sub
