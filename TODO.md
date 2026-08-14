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
- [x] Legal-Research-Workflow ("nicht ausreichend belegt" als expliziter Zustand) – deterministische
      Query-Generierung aus Aktenmetadaten, vollständiger Quellenbeleg pro Treffer, kein Finding
      ohne echte Source-Zeile, "nicht ausreichend belegt" explizit als bool+Text. Dabei einen
      echten Bug in der Suchschicht (Prompt 11) gefunden und behoben:
      `SearchResult.entity_type` erlaubte "Source" nicht. Sandbox-Testlauf mit echtem Python
      3.13.15 bestätigt: `205 passed, 1 skipped` (gesamt).
- [x] Prompt-/Policy-Layer (Trennung System/Kanzlei/Fall/Quellen/Nutzeranweisung) – fünf strikt
      getrennte, klar getaggte Abschnitte, matter_id als zwingender Parameter, Aktenisolation mit
      echten Testnamen verifiziert, Trust-Markierung als Vorbereitung auf Prompt 28, versionierte
      Kanzleiregeln (Policy-Modell). Noch kein LLM-Aufruf. Sandbox-Testlauf mit echtem Python
      3.13.15 bestätigt: `230 passed, 1 skipped` (gesamt). **Phase 4 (Wissens- und Rechtslayer)
      damit vollständig abgeschlossen.**

## Phase 4b – Privacy-by-Design / Claude API Boundary (zusätzlicher Schritt)

**Begründung für diesen zusätzlichen Schritt** (Konzept erlaubt das ausdrücklich: "Falls du
feststellst, dass ein zusätzlicher Schritt erforderlich ist, füge ihn logisch in den
Entwicklungsplan ein"): Der Anwalt hat nach Abschluss von Phase 4 eine verbindliche
Local-First-/Privacy-by-Design-Architekturvorgabe erteilt, die vor dem ersten Claude-API-Aufruf
(ursprünglich Prompt 17) umgesetzt werden muss. Siehe ARCHITECTURE.md §27 für das vollständige
Zielbild.

- [x] **Schritt 1: PII-Erkennung + Pseudonymisierung** (`app/privacy/`) – Regex-Detektoren für
      E-Mail/Telefon/IBAN/Steuer-ID/Aktenzeichen/Kundennummer/Vertragsnummer/Datum/Betrag/Adresse,
      `known_entities`-Mechanismus für Namen (zuverlässiger als Regex-Raten), Überlappungsauflösung,
      `Pseudonymizer` mit exakter Roundtrip-Rekonstruktion. Zwei echte Regex-Bugs gefunden und
      behoben (Betrag-Wortgrenze, IBAN-Restgruppe). Sandbox-Testlauf mit echtem Python 3.13.15
      bestätigt: `255 passed, 1 skipped` (gesamt).
- [x] **Schritt 2: Security-Check** (`app/privacy/security_check.py`) – alle 7 Prüfpunkte der
      Vorgabe abgedeckt, Zweck-Allowlist (nur Textproduktion), erneute PII-Prüfung nach
      Pseudonymisierung, Mapping-Text-Konsistenzprüfung, Heuristik für unbekannte Namen. **Echten
      Bug während der Entwicklung gefunden:** ursprüngliche Namens-Heuristik hätte praktisch jeden
      normalen deutschen Kanzleibrief blockiert (alle Substantive + Höflichkeitsform werden im
      Deutschen großgeschrieben, nicht nur Namen) – durch Stoppwortliste + wortbasiertes Scannen
      behoben. Sandbox-Testlauf mit echtem Python 3.13.15 bestätigt: `264 passed, 1 skipped`
      (gesamt).
- [x] **Schritt 3: `ClaudePrivacyGateway`-Orchestrierung** (`app/privacy/gateway.py`) –
      Allowlist-Payload-Schema (genau die 6 Vorgabe-Felder), alle Felder gemeinsam in einem
      Pseudonymizer-Durchgang für konsistente Platzhalter über Feldgrenzen hinweg, Blockierung
      erzeugt keine Payload, Struktur-Injection-Abwehr, lokale Rekonstruktion. Weiteren
      Fehlalarm der Namens-Heuristik gefunden und behoben (nummerierte Argumentationspunkte wie
      "Erster Punkt"). Sandbox-Testlauf mit echtem Python 3.13.15 bestätigt: `281 passed,
      1 skipped` (gesamt).
- [x] **Schritt 4: `LocalAIProvider`/`ClaudeWritingProvider`-Schnittstellen** (`app/ai_providers/`)
      – `RuleBasedLocalAIProvider` bündelt bestehende Services (Prompt 06/10/11/12) zu einer
      Draft-Vorbereitungsmethode, `ClaudeWritingProvider`-Protocol bewusst ohne konkrete
      Implementierung, `DraftGenerationOrchestrator` verbindet alles zum vollständigen Ablauf und
      hängt architektonisch geprüft ausschließlich von Protocols ab (kein SDK-Import). Sandbox-
      Testlauf mit echtem Python 3.13.15 bestätigt: `298 passed, 1 skipped` (gesamt).
- [x] **Schritt 5: Privacy-sichere API-Protokollierung** (`app/privacy/api_logger.py`,
      `app/models/api_call_log.py`) – eigenes schlankes Modell ohne Freitextfeld, nicht
      umkehrbarer Prompt-Hash, Security-Check-Gründe werden vor dem Loggen in inhaltsfreie
      Kategorien übersetzt (wichtiger während der Entwicklung vermiedener Fehler: die Gründe
      selbst enthalten teils die erkannte PII im Klartext), in Orchestrator verankert inkl.
      kontrolliertem Fehlerabfang. Sandbox-Testlauf mit echtem Python 3.13.15 bestätigt:
      `311 passed, 1 skipped` (gesamt). **Alle 5 Schritte der Privacy-Architektur damit
      abgeschlossen** – verbleibend nur noch der tatsächliche Claude-API-Aufruf (wartet auf
      Freigabe, verschmilzt mit Prompt 17).

### Offene Entscheidungen zu diesem Thema (noch mit dem Anwalt zu klären)

1. **Speicherort des Pseudonym-Mappings:** eigene DB-Tabelle (dauerhaft, auditierbar) oder rein
   In-Memory pro Anfrage-Zyklus (einfacher, aber keine Nachvollziehbarkeit nach Prozess-Neustart)?
2. **Schwellenwert für den Security-Check:** wie genau wird "nicht eindeutiges Ergebnis" (Punkt 6
   der Vorgabe) definiert – z. B. bei wie vielen/welcher Art nicht erkannter Muster wird blockiert?
3. **Umgang mit Telefonnummern-Formaten:** aktuelle Regex ist bewusst nicht erschöpfend (siehe
   ARCHITECTURE.md §27) – reicht das für den Security-Check, oder soll zusätzlich eine
   spezialisierte Bibliothek (z. B. `phonenumbers`) ergänzt werden?
4. **Anzeige/Bearbeitung nicht erkannter PII im Dashboard** (Prompt 22 kommt erst später) – wie
   soll die manuelle Prüfung bei blockierten Vorgängen konkret aussehen?

### Zweite Vorgabe (empfangen): Ollama für lokale KI-Aufgaben

Der Anwalt hat eine ergänzende Architekturvorgabe geliefert: **Ollama** mit lokalem
Open-Source-Modell soll perspektivisch die "lokale KI"-Aufgaben übernehmen (Dokumentenverständnis,
Zusammenfassung, Informationsextraktion, Aktenzuordnung, Kanzleiwissen-Abruf, Fristenerkennung) –
mit deutlich höherer inhaltlicher Qualität als die aktuellen Platzhalter-Heuristiken (Prompt
08–10). Details siehe ARCHITECTURE.md §27 (Abschnitt "Ergänzende Vorgabe: Ollama").

**Betrifft in erster Linie Schritt 4 (`LocalAIProvider`) dieser Phase.** Nicht sofort umgesetzt,
sondern dort aufgegriffen.

**Zusätzliche offene Entscheidungen daraus:**
5. **Hardware der Kanzlei:** CPU-only, wie viel RAM (16 GB vs. 32 GB), vorhandene NVIDIA-GPU? Das
   bestimmt direkt, welches Ollama-Modell überhaupt sinnvoll nutzbar ist.
6. **Welches konkrete Ollama-Modell** (z. B. je nach Hardware ein kleineres 7-8B-Modell oder ein
   größeres, falls Hardware es zulässt) – abhängig von Entscheidung 5.
7. **Umfang der Migration:** sollen die bestehenden Platzhalter-Module (Klassifikation Prompt 08,
   Matching Prompt 09, Fristenanalyse Prompt 10) komplett auf Ollama umgestellt werden, oder bleibt
   die deterministische Logik als schneller "erster Filter" bestehen und Ollama ergänzt nur dort,
   wo die Konfidenz aktuell niedrig ist (Hybrid-Ansatz)?

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
