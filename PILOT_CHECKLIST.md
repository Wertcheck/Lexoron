# PILOT_CHECKLIST.md – Vor-Start-Checkliste (Prompt 44)

Diese Checkliste wird am Vortag des Pilot-Starts durchgearbeitet, um sicherzustellen,
dass alles Notwendige vorbereitet ist.

---

## A. System & Hardware (Tag -1)

- [ ] Windows 10/11 (64-Bit) verfügbar? (Workstation des Anwalts)
- [ ] RAM ≥4 GB installiert? (8 GB empfohlen)
- [ ] Speicher ≥500 MB frei? (für Datenbank + Dokumente)
- [ ] Internet-Konnektivität stabil? (`ping api.anthropic.com` funktioniert)
- [ ] Windows Firewall konfiguriert? (localhost:8000 nicht blockiert)

---

## B. Installation & Setup (Tag -1 bis -0.5)

- [ ] KanzleiAI-Setup-0.1.0.exe herunterladen (von Prompt 36)
- [ ] Installer ausführen:
  - [ ] Installationsordner: `C:\Program Files\KanzleiAI`
  - [ ] Datenverzeichnis automatisch: `C:\ProgramData\KanzleiAI`
- [ ] Installer **nicht** die App starten lassen (wir machen First-Run manuell)
- [ ] Admin-Desktop-Shortcut prüfen (für einfachen Start)

---

## C. First-Run Setup-Assistent (Tag 0, Morning)

- [ ] Terminal/Konsole öffnen: `cmd` oder PowerShell
- [ ] Zu Installationsordner wechseln: `cd "C:\Program Files\KanzleiAI"`
- [ ] Setup-Assistent starten: `kanzlei_ai.exe serve`
- [ ] Assistent-Fragen beantworten:
  - [ ] Admin-E-Mail eingeben: `anwalt@kanzlei.local` (Beispiel)
  - [ ] Admin-Passwort eingeben (oder leer lassen → Zufallspasswort generiert)
  - [ ] SESSION_SECRET_KEY wird automatisch generiert ✓
  - [ ] `.env` unter `C:\ProgramData\KanzleiAI\.env` geschrieben ✓
  - [ ] Migration (alembic upgrade head) läuft durch ✓
  - [ ] Admin-Nutzer angelegt ✓
  - [ ] Server startet unter `http://127.0.0.1:8000`

---

## D. Dashboard-Login & Passwort-Änderung (Tag 0)

- [ ] Browser öffnen: `http://127.0.0.1:8000/dashboard`
- [ ] Login mit Admin-E-Mail + (generiertem) Passwort
- [ ] Dashboard lädt → Inbox, Akten, etc. sichtbar
- [ ] Passwort-Änderungs-Dialog (erzwungen beim ersten Login)
- [ ] Neues Admin-Passwort setzen (sicher!)
- [ ] Nochmal Login mit neuem Passwort prüfen

---

## E. Konfiguration (Tag 0, Afternoon)

### E1: Scan-Ordner

- [ ] Scan-Eingabe-Ordner prüfen: `C:\ProgramData\KanzleiAI\data\intake`
- [ ] Testdatei (PDF) ablegen → System sollte aufnehmen
- [ ] Prüfen: Inbox zeigt neue Einträge ✓

### E2: Claude-API-Key (kritisch!)

- [ ] `.env`-Datei öffnen: `C:\ProgramData\KanzleiAI\.env`
- [ ] `ANTHROPIC_API_KEY` prüfen (sollte gesetzt sein)
- [ ] Falls leer oder fehlerhaft:
  - [ ] Anthropic-Dashboard öffnen (https://console.anthropic.com)
  - [ ] API-Key erzeugen/kopieren
  - [ ] In `.env` eintragen: `ANTHROPIC_API_KEY=sk_...`
  - [ ] Server neu starten (kanzlei_ai.exe serve)
- [ ] Test: Dashboard → Einstellungen → Systemstatus → Claude API Status prüfen

### E3: E-Mail-Integration (Optional)

- [ ] Falls E-Mail-Ingestion gewünscht:
  - [ ] Dashboard → Einstellungen → Integrationen
  - [ ] IMAP-Server, Benutzername, Passwort eingeben
  - [ ] "Test-Verbindung" klicken
- [ ] Falls nicht gewünscht → überspringen (nicht erforderlich für Pilot-Erfolg)

### E4: Logging (Optional)

- [ ] Dashboard → Einstellungen → System
- [ ] Log-Level auf `INFO` setzen (Standard)
- [ ] Ggf. `LOG_FILE_PATH` auf `C:\ProgramData\KanzleiAI\kanzlei_ai.log` setzen

---

## F. Benutzer & Rollen (Tag 0, Evening)

- [ ] Ggf. zusätzliche Anwälte hinzufügen (falls mehrere im Pilot):
  - [ ] Dashboard → Einstellungen → Nutzer
  - [ ] "Neuer Nutzer" → E-Mail + Rolle (Attorney) → Speichern
  - [ ] Neuer Nutzer erhält Login-Link (per E-Mail)
- [ ] Falls nur ein Anwalt: Admin-Account reicht aus

---

## G. Testlauf (Tag 0, Evening oder Tag 1 Morning)

- [ ] Kompletter Mini-Workflow durchspielen:
  - [ ] Test-PDF in Scan-Ordner legen
  - [ ] Intake durchlaufen (Inbox zeigt Eintrag)
  - [ ] Klassifikation prüfen (manuell korrekt?)
  - [ ] Aktenzuordnung prüfen (existierende Akte oder neue?)
  - [ ] "Entwurf generieren" klicken
    - [ ] Claude API wird aufgerufen (dauert ~2–5 Sekunden)
    - [ ] Entwurf erscheint in Überprüfungs-Pane
    - [ ] Review-Findings prüfen (Rechtsquellen, offene Punkte)
  - [ ] Entwurf genehmigen oder mit Anmerkung zurückgeben
  - [ ] Status auf "approved" prüfen

- [ ] Wenn alle Schritte funktionieren → **GO für Pilot-Start!**
- [ ] Wenn Fehler auftreten:
  - [ ] Logs prüfen (`kanzlei_ai.log`)
  - [ ] Typische Fehler?
    - [ ] Claude API nicht konfiguriert → Key nochmal prüfen
    - [ ] OCR schlägt fehl → Tesseract nicht installiert (Optional für Pilot)
    - [ ] Datenbank-Fehler → Support anfordern
  - [ ] Fehler beheben vor Pilot-Start

---

## H. Backups & Notfall-Plan (Tag 0, Night)

- [ ] Backup des gesamten Installationsordners machen:
  - [ ] `C:\Program Files\KanzleiAI` → externe Festplatte kopieren
- [ ] Backup des Datenverzeichnisses machen:
  - [ ] `C:\ProgramData\KanzleiAI` → externe Festplatte kopieren
- [ ] Notfall-Kontakt festlegen (falls Fragen während Pilot):
  - [ ] Entwickler-Kontakt (E-Mail/Chat)
  - [ ] Falls nicht verfügbar → Support-Dokumentation (PILOT_PLAYBOOK.md)

---

## I. Anwalt-Einweisung (Tag 1, Morning)

- [ ] Anwalt sitzt am System
- [ ] **Walkthrough (30–60 Min):**
  - [ ] Dashboard-Navigation (Inbox → Akten → Entwürfe)
  - [ ] Scan-Ordner (wohin Dokumente legen)
  - [ ] Entwurf-Workflow (Klassifikation → Entwurf → Review → Freigabe)
  - [ ] Feedback-Sammlung (wie Erfahrungen notieren)
  - [ ] Notfall-Kontakt (wen anrufen bei Problemen)
- [ ] Anwalt testet einen echten Workflow alleine
- [ ] Fragen klären

---

## J. Go/No-Go Entscheidung (Tag 1, Noon)

- [ ] **Checkliste A–I vollständig?**
  - [ ] JA → Alle Häkchen gesetzt? → **GO für Pilot-Start**
  - [ ] NEIN → Fehler beheben, dann erneut prüfen

- [ ] **System-Funktionalität:**
  - [ ] Dashboard lädt ohne Fehler
  - [ ] Claude API funktioniert (Test-Entwurf generiert)
  - [ ] Logs zeigen keine kritischen Fehler
  - [ ] Backup vorhanden

- [ ] **Anwalt bereit:**
  - [ ] Einweisung erhalten + verstanden
  - [ ] Erste echte Aufgaben bereitet vor (3–5 Akten zum Verarbeiten)
  - [ ] Feedback-Prozess klar (tägliche Notizen, wöchentliche Reviews)

---

## K. Pilot-Start! (Tag 1, PM oder Tag 2, AM)

- [ ] **Server läuft kontinuierlich oder nur bei Bedarf:**
  - [ ] Empfehlung: Server morgens starten, abends stoppen (für Backup)
  - [ ] Alternative: Im Hintergrund laufen lassen (braucht Monitoring)

- [ ] **Anwalt beginnt mit echten Workflows**
  - [ ] 10 Akten zu verarbeiten (mind. über 2–4 Wochen)
  - [ ] 5+ Entwürfe zu generieren
  - [ ] Täglich Feedback notieren

- [ ] **Entwicklung in Bereitschaft:**
  - [ ] Kontakt prüfen regelmäßig (tägliche Status-Updates bei Bedarf)
  - [ ] Logs von Anwalt sammeln (Ende jeder Woche)
  - [ ] Kritische Fehler: Sofort eskalieren

---

## L. Wöchentliche Checkpoints (Wochen 1–4)

**Jede Woche:**

- [ ] Montag 9 AM: Feedback-Call mit Anwalt (15 Min)
  - [ ] Wie läuft's? Bugs aufgetaucht?
  - [ ] Woran arbeitet er diese Woche?
- [ ] Donnerstag Abend: Backup machen (Dashboard → Backup-Button oder manuell)
- [ ] Freitag 5 PM: Logs sammeln & Statistiken aus Dashboard exportieren
  - [ ] Systemstatus (API-Aufrufe, Kosten, Fehler)

---

## M. Pilot-Abschluss-Vorbereitung (Tag 25–28)

- [ ] Wurden Erfolgskriterien erreicht? (Siehe PILOT_PLAYBOOK.md §5.1)
  - [ ] ≥10 Akten: __ von 10 (Zahl eintragen)
  - [ ] ≥5 Entwürfe: __ von 5 (Zahl eintragen)
  - [ ] Keine kritischen DB-Fehler: ✓/✗
  - [ ] Claude API funktioniert: ✓/✗
  - [ ] Klassifikation >50% korrekt: ✓/✗ (Anwalt-Einschätzung)
  - [ ] Keine Versand-Fehler: ✓/✗
  - [ ] Audit-Trail nachvollziehbar: ✓/✗

- [ ] Quantitatives Feedback sammeln:
  - [ ] Logs exportieren (Gesamt-Statistiken)
  - [ ] Qualitätsbewertungen exportieren (Prompt 43)
  - [ ] Anwalts-Notizen kompilieren

- [ ] Qualitatives Feedback:
  - [ ] "Was hat gut funktioniert?"
  - [ ] "Was war frustrierend?"
  - [ ] "Fehlerhafte Szenarien notieren"

- [ ] Pilot-Report schreiben (für Prompt 45)

---

**✅ Nach Abschluss dieser Checkliste → Pilot kann beginnen!**

**Probleme während Pilot → PILOT_PLAYBOOK.md, Abschnitt "Fehlerbehandlung"**

**Nach Pilot-Ende → PILOT_PLAYBOOK.md, Abschnitt "Übergabe an Prompt 45"**
