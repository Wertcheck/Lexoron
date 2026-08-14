# TODO.md – Umsetzungsplan

Reihenfolge und Prompts entsprechen dem Konzeptdokument (Abschnitt 18). Jede Phase wird erst
begonnen, wenn die vorherige abgeschlossen und (bei fachlichen Fragen) mit dem Anwalt/Auftraggeber
abgestimmt ist.

## Phase 0 – Projektstart (dieser Schritt)
- [x] Umgebung geprüft (Python 3.12, git vorhanden, Repo leer)
- [x] ARCHITECTURE.md angelegt
- [x] TODO.md angelegt
- [x] Offene Entscheidungen 1–6 (siehe ARCHITECTURE.md §10): Python 3.13.x und SQLite mit
      PostgreSQL-Abstraktion bestätigt; OCR/Mail/RAG/Zielumgebung bewusst noch offen

## Phase 1 – Technischer Kern (Prompts 01–04)
- [x] Repository-Grundgerüst (pyproject.toml, .env.example, README.md, CLAUDE.md, Teststruktur,
      Git-Repo, FastAPI-Health-Check) – finaler Test auf dem Python-3.13-Zielsystem (Windows,
      Python 3.13.15) erfolgreich bestätigt: `pytest` → 2 passed.
- [x] Konfigurationssystem (pydantic-settings, sichere Defaults, Validierung
      für ungültige Werte, Secrets als SecretStr, `DATABASE_URL`-Abstraktion
      SQLite→PostgreSQL bestätigt funktionsfähig). **Finaler Test auf dem
      Python-3.13-Zielsystem (Windows, Python 3.13.15) erfolgreich bestätigt:
      `pytest` → 11 passed, lokaler Start mit geladener `.env` funktioniert.**
- [x] Datenmodell (Client, Matter, Party, Message, Document, Task, Deadline, Draft, Source,
      KnowledgeItem, WorkflowRun, AuditEvent, User/Role) + Migrationen (Alembic) + Tests.
      **Finaler Test auf dem Python-3.13-Zielsystem (Windows, Python 3.13.15) erfolgreich
      bestätigt: `pytest` → 19 passed; `alembic upgrade head` erfolgreich angewendet.**

## Phase 2 – Eingang (Prompts 05–07)
- [x] Scan-Ordner-Überwachung (Intake-Service, Hash, sicherer Intake-Bereich, Watchdog-basierter
      Beobachter, Stabilitätsprüfung gegen unvollständig geschriebene Dateien). Sandbox-Testlauf
      erneut mit echtem Python 3.13.15 (`.venv313`) bestätigt: `31 passed`. Verifikation auf dem
      Windows-Zielsystem des Anwalts steht optional noch aus (Sandbox läuft jetzt bereits mit
      echtem 3.13, daher kein Blocker mehr für die weitere Entwicklung).
- [x] Dokumentverarbeitung/OCR (Text/OCR getrennt von Original) – PDF/DOCX/TXT-Textextraktion,
      Tesseract-OCR mit sicherem Pending-Default bei deaktiviertem OCR, Sandbox-Testlauf mit
      echtem Python 3.13.15 bestätigt: `48 passed` (gesamt). Windows-Verifikation optional;
      **wichtig: Tesseract muss auf dem Windows-Zielsystem separat installiert werden** (externe
      Programmdatei, keine Python-Bibliothek) – siehe ARCHITECTURE.md §15.
- [x] E-Mail-Ingestion (ein Provider-Adapter, entkoppelt vom Workflow) – IMAP-Provider,
      Provider-Abstraktion ohne jede Sende-Möglichkeit, Anhänge als eigene Document-Einträge,
      Deduplizierung über Message-ID. Sandbox-Testlauf mit echtem Python 3.13.15 bestätigt:
      `64 passed` (gesamt).

## Phase 3 – Aktenlogik (Prompts 08–10)
- [x] Dokumentklassifikation (strukturiertes JSON-Schema, Konfidenz) – striktes Pydantic-Schema,
      regelbasierter Platzhalter-Klassifikator (bewusst kein LLM, siehe ARCHITECTURE.md §17),
      Migration für neue Document-Spalten, Sandbox-Testlauf mit echtem Python 3.13.15 bestätigt:
      `84 passed` (gesamt). Echte LLM-Klassifikation folgt erst mit Prompt 17/34.
- [x] Aktenzuordnung (deterministisch + semantisch, Schwellenwerte) – vier gewichtete Signale
      (Aktenzeichen, E-Mail, Beteiligtenname, Themen-Platzhalter), Ambiguitätsschutz, Kopplung an
      Klassifikationskonfidenz aus Prompt 08, Sandbox-Testlauf mit echtem Python 3.13.15
      bestätigt: `100 passed` (gesamt).
- [x] Fristen-/Aufgabenanalyse (nie verbindlich ohne Prüfung) – Datums-/Keyword-Heuristik (kein
      LLM), Konfidenz je nach Kontext, review_status bleibt immer "unreviewed", erfordert
      bereits erfolgte Aktenzuordnung (Prompt 09). Sandbox-Testlauf mit echtem Python 3.13.15
      bestätigt: `118 passed` (gesamt). **Phase 3 (Aktenlogik) damit vollständig abgeschlossen.**

## Phase 4 – Wissens- und Rechtslayer (Prompts 11–16)
- [x] Akten-Such-/Kontextschicht (strikt aktenbezogen) – fastembed (ONNX, kein PyTorch/CUDA),
      großes mehrsprachiges Modell (`paraphrase-multilingual-mpnet-base-v2`), Metadatenfilter +
      Volltext + semantische Suche kombiniert (Hybrid), strukturell erzwungene Aktenisolation,
      generische Embedding-Tabelle bereits für Prompt 12 vorbereitet. Sandbox-Testlauf mit echtem
      Python 3.13.15 bestätigt: `141 passed, 1 skipped` (Skip = Netzwerkblock huggingface.co,
      analog zur Python-3.13-Situation – **echter Modelltest auf dem Windows-Zielsystem noch
      ausstehend**).
- [x] Kanzlei-Wissensbasis (Freigabepflicht vor Nutzung) – Import/Versionierung/Freigabe/
      Deaktivierung, Modell um Quelle/Gültigkeitsbereich erweitert, Freigabe stößt Indizierung an,
      Deaktivierung verlangt Begründung, Suchschicht (Prompt 11) berücksichtigt jetzt
      Gültigkeitsbereich. Sandbox-Testlauf mit echtem Python 3.13.15 bestätigt: `159 passed,
      1 skipped` (Skip weiterhin nur Netzwerkblock huggingface.co).
- [x] Feedback-Workflow des Anwalts (keine automatische Regelübernahme) – DraftFeedback-Modell mit
      Original-Schnappschuss, `record_feedback`/`promote_to_knowledge` bewusst getrennt, Feedback
      allein erzeugt nie Kanzleiwissen, explizite Übernahme bleibt `pending`. Sandbox-Testlauf mit
      echtem Python 3.13.15 bestätigt.
- [x] Rechtsquellen-Modul (Metadaten, mehrere Provider) – SourceProvider-Protocol +
      ManualSourceProvider (automatisierte Datenbank-Anbindung bewusst offen gelassen, siehe
      Konzept), Quellenklassen um "Verwaltungsanweisung" (BMF-Schreiben) für den steuerrechtlichen
      Kontext erweitert, veraltete Quellen bleiben in der DB erhalten. Sandbox-Testlauf mit echtem
      Python 3.13.15 bestätigt: `191 passed, 1 skipped` (gesamt, Skip weiterhin nur
      Netzwerkblock).
- [ ] Legal-Research-Workflow ("nicht ausreichend belegt" als expliziter Zustand)
- [ ] Prompt-/Policy-Layer (Trennung System/Kanzlei/Fall/Quellen/Nutzeranweisung)

## Phase 5 – Antwort und Kontrolle (Prompts 17–20)
- [ ] Drafting-Service (kein Versand-Trigger)
- [ ] unabhängige Review-Engine
- [ ] Audit-Log (append-only)
- [ ] Workflow-State-Machine (definierte Übergänge)

## Phase 6 – Dashboard (Prompts 21–25)
- [ ] FastAPI-Backend (Inbox, Akten, Dokumente, Entwürfe, Quellen, Aufgaben, Einstellungen, Audit)
- [ ] Dashboard-Inbox
- [ ] Akte-Ansicht
- [ ] Entwurfsprüfung (Original/Entwurf, Quellen, Findings, Versionsvergleich)
- [ ] Postausgang (kein automatischer Versand)

## Phase 7 – Sicherheit und Produktisierung (Prompts 26–35)
- [ ] Rollen/Berechtigungen (Admin, Anwalt, Mitarbeiter)
- [ ] Security Review + SECURITY.md
- [ ] Prompt-Injection-Schutz + Tests mit manipulierten Dokumenten
- [ ] Synthetischer Testdaten-Simulator
- [ ] End-to-End-Test
- [ ] Fehler-/Retry-System
- [ ] Logging/Monitoring (ohne sensible Inhalte)
- [ ] KI-Kostenkontrolle
- [ ] ModelProvider-Abstraktion
- [ ] Export/Backup

## Phase 8 – Kanzlei-Produkt (Prompts 36–45)
- [ ] Windows-Installer
- [ ] Setup-/Konfigurations-Assistent
- [ ] Multi-Kanzlei-Profile + Cross-Tenant-Tests
- [ ] Dokumentvorlagen (validierte Platzhalter)
- [ ] Production Readiness Review
- [ ] Mandantenfähigkeit/Datenisolation-Tests
- [ ] Qualitäts-Benchmark (≥20 synthetische Fälle)
- [ ] Anwalts-Feedbackschleife (Bewertung, nur Auswertung, kein Auto-Training)
- [ ] Pilotbetrieb (2–4 Wochen, nicht-autonom)
- [ ] Finaler Review + priorisierter Abschlussbericht

## Wiederkehrende Grundregeln (gelten für jede Phase)
- Keine echten Mandantendaten in Tests/Entwicklung.
- Keine Secrets in Code/Logs/Git.
- Dokumentinhalte = untrusted input.
- Rechtsquellen/Zitate nie erfinden; Unsicherheit markieren.
- Keine autonome rechtliche Entscheidung, kein autonomer Versand.
- Aktenkontext strikt isolieren.
- Jede wichtige KI-Aktion nachvollziehbar (Audit).
