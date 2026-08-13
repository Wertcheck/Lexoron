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
      KnowledgeItem, WorkflowRun, AuditEvent, User/Role) + Migrationen (Alembic) + Tests –
      Sandbox-Smoke-Test unter Python 3.12 bestanden (19/19 Tests, inkl. Migration
      upgrade/downgrade); finaler Test auf dem Python-3.13-Zielsystem steht noch aus.

## Phase 2 – Eingang (Prompts 05–07)
- [ ] Scan-Ordner-Überwachung (Intake-Service, Hash, sicherer Intake-Bereich)
- [ ] Dokumentverarbeitung/OCR (Text/OCR getrennt von Original)
- [ ] E-Mail-Ingestion (ein Provider-Adapter, entkoppelt vom Workflow)

## Phase 3 – Aktenlogik (Prompts 08–10)
- [ ] Dokumentklassifikation (strukturiertes JSON-Schema, Konfidenz)
- [ ] Aktenzuordnung (deterministisch + semantisch, Schwellenwerte)
- [ ] Fristen-/Aufgabenanalyse (nie verbindlich ohne Prüfung)

## Phase 4 – Wissens- und Rechtslayer (Prompts 11–16)
- [ ] Akten-Such-/Kontextschicht (strikt aktenbezogen)
- [ ] Kanzlei-Wissensbasis (Freigabepflicht vor Nutzung)
- [ ] Feedback-Workflow des Anwalts (keine automatische Regelübernahme)
- [ ] Rechtsquellen-Modul (Metadaten, mehrere Provider)
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
