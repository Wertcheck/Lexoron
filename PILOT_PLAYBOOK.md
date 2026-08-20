# PILOT_PLAYBOOK.md – Lexono Pilotbetrieb (2–4 Wochen)

**Stand:** Prompt 44, 17.08.2026  
**Phase:** 8 (Kanzlei-Produkt), finale operative Vorbereitung vor finaler Review (Prompt 45)

## Übersicht

Dieses Playbook dokumentiert die praktische Durchführung des 2–4-wöchigen Pilotbetriebs
mit der ersten Kanzlei. Es ist KEINE neue Feature-Entwicklung, sondern Operationalisierung
des bis Prompt 43 fertiggestellten Systems.

**Zustand des Systems:**
- ✅ Core-Funktionalität vollständig (Intake bis Outbox, KI-Entwürfe, Review, Freigabe)
- ✅ Sicherheit/Audit/Logging implementiert
- ✅ Windows-Installer + Setup-Assistent funktionsfähig
- ✅ Anwalts-Feedbackschleife (Post-Release-Bewertung)
- ✅ 783/783 Tests grün (inkl. Prompt 40–42 aus Claude Code)
- ⏳ Dashboard-Integration für Bewertungs-UI noch offen (Prompt 43)

## 1. Vor dem Pilotstart: Installation & First-Run (Tag 0)

### 1.1 Hardware/Betriebssystem-Anforderungen

**Zielumgebung:**
- Windows 10/11 (64-Bit) auf lokaler Workstation des Anwalts
- CPU: Modern (2020+), 2+ Kerne
- RAM: ≥4 GB (8 GB empfohlen)
- Speicher: ≥500 MB frei (für Datenbank + Dokumente)
- Netzwerk: Lokal nur – keine Internet-Verbindung erforderlich (außer Claude API)
- Internet: Stabil, für Claude API-Aufrufe (Anthropic) erforderlich

**Vorkonfiguration:**
- Internet-Konnektivität zum Claude-API-Endpunkt testen (z. B. `ping api.anthropic.com`)
- Python 3.13.x-Anforderung bereits im Installer geprüft (siehe `run.py`)
- Windows Firewall: ggf. localhost:8000 (der Browser-Port) nicht blockieren

### 1.2 Installation aus Installer

```bash
# 1. Lexono_Setup.exe ausführen (von Prompt 36; %LocalAppData% seit Schritt 3)
# 2. Standard-Installationspfad: %LocalAppData%\Lexono (keine Admin-Rechte nötig)
# 3. Datenverzeichnis: C:\ProgramData\KanzleiAI (automatisch angelegt)
#
# Der Installer startet die App nicht automatisch.
```

### 1.3 First-Run: Setup-Assistent

```bash
# Im Installationsordner (oder über Shortcut) starten:
# kanzlei_ai.exe serve
#
# Ablauf:
# 1. Ist .env vorhanden?
#    - JA: Server startet direkt unter http://127.0.0.1:8000
#    - NEIN: Setup-Assistent startet (interaktive Konsole)
#
# 2. Setup-Assistent (beim allerersten Start):
#    - Fragt Admin-E-Mail ein (z. B. anwalt@kanzlei.local)
#    - Fragt (optional) Admin-Passwort (sonst Zufallspasswort generiert)
#    - Generiert SESSION_SECRET_KEY automatisch
#    - Schreibt .env unter C:\ProgramData\KanzleiAI\.env
#    - Führt Migration (alembic upgrade head) aus
#    - Legt Admin-Nutzer an (mit Passwort-Änderungszwang beim Login)
#    - Startet Server
#
# 3. Im Browser:
#    → http://127.0.0.1:8000/dashboard/login
#    → Anmelden mit Admin-E-Mail + (generiertem oder eingegeben Passwort)
#    → Passwort ändern (erzwungen beim ersten Login)
#    → Dashboard: Inbox, Akten, Dokumente, Entwürfe, Quellen, Einstellungen
```

**Wichtig nach Setup:**
- Admin-Passwort ändern (wird erzwungen)
- Optional: zusätzliche Benutzer/Anwälte anlegen (Einstellungen → Nutzer)
- Optional: Klassifikations-Keywords konfigurieren (falls Kanzleiprofil mit eigenen
  Keywords gewünscht – siehe PROMPT38_ANALYSIS.md für geplante Erweiterung)

### 1.4 Einmalige Konfiguration

**Scan-Ordner:**
- Standard-Eingabeordner (für Intake): `C:\ProgramData\KanzleiAI\data\intake`
- Dieser Ordner wird vom System monitort (Watchdog)
- PDFs/Docx in diesen Ordner legen → automatisch aufgenommen

**E-Mail-Konfiguration (Optional, falls E-Mail-Ingestion genutzt werden soll):**
- Einstellungen → Integrationen → IMAP
- IMAP-Server, Benutzername, Passwort eingeben
- Das System fragt bei jedem Start nach neuen E-Mails (kein Hintergrund-Daemon)

**Claude-API-Key:**
- Ist bereits in `.env` (bei Setup-Assistent) vorkonfiguriert
- Default: `ANTHROPIC_API_KEY` wird erwartet
- Falls fehlerhaft oder abgelaufen → Server startet, aber KI-Aufrufe scheitern
  mit klarer Fehlermeldung

**Logging:**
- Logs landen in: `C:\ProgramData\KanzleiAI\kanzlei_ai.log` (falls `LOG_FILE_PATH` gesetzt)
- Sinnvolle Log-Level für Pilot: `INFO` (Standard) oder `DEBUG` für Troubleshooting

## 2. Betriebsphase: Tägliche Nutzung (Tage 1–28)

### 2.1 Systemstart & -überwachung

**Täglich morgens:**
```bash
# Server starten (falls nicht permanent laufen):
# kanzlei_ai.exe serve
#
# Im Browser: http://127.0.0.1:8000/dashboard
# (Bei Bedarf: Passwort-basierter Login, Session ≥8h gültig)
```

**Permanenter Betrieb:**
- Das System ist als Einzelinstallation auf einer Workstation ausgelegt
- Nicht als Windows-Dienst registriert (würde Hintergrundbetrieb bedeuten)
- Falls permanente Verfügbarkeit gewünscht → zusätzlicher Schritt (außerhalb
  Prompt 44; siehe ARCHITECTURE.md §45 offene Punkte)

**Health-Check:**
```bash
# Schneller Liveness-Check (kein Login nötig):
# GET http://127.0.0.1:8000/health
# Sollte {"status": "ok"} zurückgeben
```

### 2.2 Tägliche Workflows

**Eingang verarbeiten:**
1. Dokumente in `C:\ProgramData\KanzleiAI\data\intake` ablegen
2. System nimmt automatisch auf (via Watchdog)
3. Dashboard → Inbox: Neue Einträge erscheinen
4. Klassifikation + Aktenzuordnung automatisch oder manuell prüfen

**Entwurf erstellen:**
1. Inbox-Eintrag öffnen
2. "Entwurf generieren" (Claude API wird aufgerufen)
3. Entwurf in Überprüfungs-Pane laden
4. Review-Findings prüfen (Rechtsquellen, offene Punkte)
5. Entwurf genehmigen oder mit Anmerkungen zurückgeben

**Nach Freigabe:**
1. Entwurf im Status "approved"
2. Optional: In Postausgang verschieben (noch kein automatischer Versand!)
3. Optional: Später Qualitätsbewertung abgeben (Prompt 43 API,
   Dashboard-UI noch in Arbeit)

### 2.3 Fehlerbehandlung während Pilotbetrieb

**Häufige Fehler:**

| Problem | Symptom | Lösung |
|---------|---------|--------|
| Claude API Key ungültig | "AuthenticationError" in Logs | KEY in `.env` prüfen, ggf. aktualisiert generieren |
| Dokument zu groß | Intake schlägt fehl | PDF >100 MB teilen, nacheinander upload |
| OCR nicht verfügbar | Text-Extraktion schlägt fehl | Tesseract nicht installiert (siehe ARCHITECTURE.md §15) |
| Datenbank korrupt | Server startet nicht | `alembic downgrade base` + `upgrade head` (Reset) |
| Benutzer vergisst Passwort | Login unmöglich | Admin-Nutzer: `scripts/create_admin.py` (neue Instanz) |
| Postausgang-Versand versucht | Unerwünschter Versand | Feature ist deaktiviert (Default) – sollte nicht vorkommen |

**Supportlogs sammeln:**
```bash
# Für Troubleshooting: Log-Datei prüfen
# cat C:\ProgramData\KanzleiAI\kanzlei_ai.log | tail -50
#
# WICHTIG: Logs können Mandantennamen/Details enthalten
# → Nur anonymisiert/mit Anwalt weitergeben
```

### 2.4 Feedback-Sammlung (kritisch für Prompt 45)

**Täglich:**
- Anwalt notiert Beobachtungen (ggf. in einem Google Doc oder lokalen Textdatei):
  - "Entwurf war zu allgemein" / "Gute Erfassung des Sachverhalts"
  - "Recherche-Funktion half" / "Klassifikation war falsch"
  - Performance: "Dauerte 2 Sekunden" / "Sehr schnell"
  - UI-Irritationen: "Button war unklar" / "Ablauf logisch"

**Wöchentlich (optional):**
- Strukturiertes Feedback (z. B. via Fragebogen) abrufen
- Kritische Fehler dokumentieren (mit Screenshots)
- Fehlgeschlagene KI-Aufrufe notieren (für Kosten-/Performance-Analyse)

**API-Statistiken nutzen:**
```bash
# Dashboard → Einstellungen → Admin → Systemstatus
# (Prompt 32/33)
# - Anzahl Entwürfe, Bewertungen, API-Aufrufe
# - Token-Verbrauch, Kosten-Schätzung
# - Fehlerrate nach Dokumenttyp
```

## 3. Monitoring & Observability

### 3.1 Logs und Audit-Trail

**Alle relevanten Aktionen werden auditiert:**
- Entwurf erstellt (Prompt, Token, Nutzer)
- Entwurf genehmigt/abgelehnt (Nutzer, Zeitstempel)
- Bewertung abgegeben (Nutzer, Skalen, Kommentar)
- Fehler bei Verarbeitung (Kategorie, Details)

**Log-Pfade:**
- Operative Logs: `C:\ProgramData\KanzleiAI\kanzlei_ai.log`
- Audit-Trail: Datenbank-Tabelle `audit_events` (im Dashboard nicht vollständig
  sichtbar, aber über SQL/Backup exportierbar)

**Log-Format:**
```
2026-08-17T09:15:32.456Z [INFO] Draft generiert: draft_id=abc123, matter_id=m1, tokens_in=150, tokens_out=280
2026-08-17T09:16:01.123Z [INFO] Draft genehmigt: draft_id=abc123, actor=attorney1
2026-08-17T10:02:44.789Z [ERROR] OCR fehlgeschlagen: document_id=doc123, reason=Tesseract nicht verfügbar
```

### 3.2 Kosten-Überwachung

**Claude-API-Kosten (Anthropic):**
- Budget-Limit pro Monat konfigurierbar (Einstellungen → Kostensteuerung)
- System blockiert Entwurf-Anfragen automatisch, wenn Budget erreicht
- Geschätzte Kosten pro Aufruf werden in Logs getracked

**Kommando für Kosten-Report:**
```bash
# (Noch nicht implementiert, aber via SQL möglich:)
# SELECT SUM(estimated_cost_usd) FROM api_call_logs WHERE created_at > DATE_SUB(NOW(), 1 MONTH);
```

### 3.3 Performance-Metriken

**Im Dashboard sichtbar:**
- Durchschnittliche Zeit für Dokumentaufnahme
- Durchschnittliche Zeit für Entwurf-Generierung
- Fehlerquote nach Dokumenttyp
- Top-5 Klassifikations-Kategorien (häufig vs. selten)

**Für Deep-Dive-Analyse:**
```bash
# Datenbankabfrage (direkt in SQLite oder per Export):
# - Anzahl erfolgreiche vs. fehlgeschlagene Aufnahmen
# - Durchschnittliche Entwurfs-Länge pro Dokumenttyp
# - Bewertungs-Durchschnitte pro Anwalt
```

## 4. Notfall-Verfahren

### 4.1 Backup vor dem Pilotstart

**Automatisches Backup vor der Installation nicht vorgesehen** – aber:
```bash
# Manuell vor Pilot-Start empfohlen:
# Vollständige Sicherung des Installationsordners
# %LocalAppData%\Lexono\  →  externe Festplatte / Cloud
#
# Datenverzeichnis ist größer und wichtiger:
# C:\ProgramData\KanzleiAI\  →  besonders Database + Dokumente
```

**Während des Pilotbetriebs:**
```bash
# Wöchentlich (optional):
# Dashboard → Einstellungen → Admin → Backup erstellen
# (Prompt 35: BackupService → ZIP mit DB + Dokumente)
# Datei: kanzlei_ai_backup_2026-08-24.zip
```

### 4.2 Restore nach Fehler

**Falls Datenbank korrupt:**
```bash
# 1. Server stoppen
# 2. Backup-ZIP entpacken (falls vorhanden)
# 3. Dateien überschreiben (C:\ProgramData\KanzleiAI\data\...)
# 4. Server neu starten
```

**Falls Konfiguration fehlerhaft:**
```bash
# 1. .env sichern (falls wichtige Keys drin)
# 2. .env löschen
# 3. Server starten → Setup-Assistent läuft erneut
# 4. Neue Konfiguration eingeben
```

**Kein automatisches Rollback** – Pilotbetrieb bedeutet aktive Überwachung.

### 4.3 Abbruch des Pilotbetriebs

Falls kritische Fehler auftreten, die den Betrieb unmöglich machen:
1. System stoppen
2. Backup aus Tag N-1 zurückfahren (falls vorhanden)
3. Logs sammeln (mit Anwalt Genehmigung)
4. Feedback an Entwicklung (Prompt 45 wird dann Findings bewerten)

## 5. Pilot-Abschluss-Kriterien (Ende Woche 2–4)

### 5.1 Erfolgskriterien: Muss erfüllt sein

- [ ] Mindestens 10 Mandanten-Akten verarbeitet
- [ ] Mindestens 5 Entwürfe generiert und genehmigt (min. 1 pro Akte)
- [ ] Keine kritischen Datenbank-Fehler (Auditable Logs zeigen Success)
- [ ] Claude API-Integration funktioniert (Entwürfe sind qualitativ sinnvoll)
- [ ] Klassifikation arbeitet mit >50% Korrektheit (Anwalt-Validierung)
- [ ] Keine unerwollten Versand-Aktionen (Outbox bleibt nicht-autonom)
- [ ] Audit-Trail ist nachvollziehbar (Logs zeigen alle Schritte)

### 5.2 Optionale Verbesserungs-Kriterien

- [ ] Durchschnittliche Entwurfs-Generierung <10 Sekunden
- [ ] Mindestens 20 Qualitätsbewertungen abgegeben (Prompt 43)
- [ ] Keine Tesseract-Fehler (OCR für alle Text-PDF)
- [ ] Benutzer-Interface ist intuitiv (Anwalt meldet keine Verwirrtheit)
- [ ] E-Mail-Ingestion (falls konfiguriert) funktioniert

### 5.3 Go/No-Go Entscheidung

**GO für Prompt 45 (Finales Review):**
- Erfolgskriterien ✅ erfüllt
- Keine blockierenden Bugs
- Anwalt gibt grünes Licht für Abschluss

**NO-GO:**
- Erfolgskriterium nicht erfüllt → Bug fixes nötig
- Kritischer Fehler gefunden → Rückfahrt zu letztem stabilen Stand
- Pilot verlängert oder Neuevaluation mit Entwicklung

## 6. Übergabe an Prompt 45 (Finales Review)

Am Ende des Pilotbetriebs:

**Artefakte für Prompt 45:**
1. **Pilot-Report** (1–2 Seiten):
   - Erfolgskriterien: Erfüllt? Ja/Nein
   - Kritische Findings während Pilot
   - Kumulativer Anwalts-Feedback
   - Empfehlungen für Freigabe/Nachbesserung

2. **Quantitatives Feedback:**
   - Anzahl verarbeitete Akten/Dokumente
   - Anzahl generierte Entwürfe (erfolgreich/fehlgeschlagen)
   - Durchschnittliche Performance-Metriken
   - Fehlerquote pro Komponente

3. **Qualitatives Feedback:**
   - Anwalts-Kommentare (anonymisiert wenn nötig)
   - "Was war hilfreich?" / "Was war frustrierend?"
   - Gewünschte Features/Verbesserungen für Zukunft

4. **Logs & Audit-Trail:**
   - `kanzlei_ai.log` (anonymisiert)
   - Statistiken aus Admin-Dashboard exportiert
   - Beispiel-Entwürfe (mit Anwalt-Genehmigung)

5. **Finale Sicherheits-Checkliste:**
   - Keine Mandantendaten außerhalb Datenverzeichnis
   - Passwörter nicht in Logs geleaked
   - Session-Secrets korrekt gesetzt
   - API-Keys nicht in Git/Backups

---

**Nächster Schritt:** Prompt 45 bewertet diese Artefakte und schließt das Projekt ab.
