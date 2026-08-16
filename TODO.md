# TODO.md – Umsetzungsplan

Reihenfolge und Prompts entsprechen dem Konzeptdokument (Abschnitt 18). Jede Phase wird erst
begonnen, wenn die vorherige abgeschlossen und (bei fachlichen Fragen) mit dem Anwalt/Auftraggeber
abgestimmt ist.

**Hinweis zum Produktziel (15.08., vom Anwalt mitgeteilt):** Das Programm soll nach erfolgreichem
Test in dieser ersten Kanzlei auch anderen Kanzleien angeboten werden. Aktuelle Architektur- und
Datenmodell-Entscheidungen gehen weiterhin von EINER Kanzlei pro Installation/Deployment aus
(kein `tenant_id`/Kanzlei-Entität im Datenmodell) - das ist bewusst so belassen, um die erste
Kanzlei nicht durch verfrühte Multi-Tenancy-Komplexität zu verzögern.

**Entscheidung zur Mehr-Kanzlei-Fähigkeit (16.08., vor Beginn Phase 8 abgestimmt):**
**Getrennte Installation je Kanzlei** - jede Kanzlei erhält eine eigene, unabhängige Installation
mit eigener Datenbank (kein `tenant_id`, kein gemeinsam genutzter Datenbestand zwischen
Kanzleien). Begründung: konsistent mit der bisherigen Architektur (SQLite als eingebettete
Datei, Windows-Installer als Zielformat, kein SaaS-/Cloud-Bezug); strukturell ausgeschlossenes
Cross-Tenant-Datenleck, da keine gemeinsame Infrastruktur zwischen Kanzleien existiert - kein
Mandantentrennungs-Fehler ist überhaupt möglich, wenn es keine gemeinsame gemeinsame
Datenschicht gibt. Folgen für Phase 8: "Multi-Kanzlei-Profile + Cross-Tenant-Tests" (weiter
unten) bedeutet in diesem Modell konkret: der Setup-/Konfigurationsassistent (Prompt 37)
unterstützt das einfache Aufsetzen einer NEUEN, unabhängigen Instanz für eine neue Kanzlei
(Branding, Klassifikationsschlüsselwörter, Policies als Installationszeit-Konfiguration) - NICHT
Laufzeit-Mandantentrennung innerhalb einer einzigen laufenden Anwendung. "Cross-Tenant-Tests"
werden entsprechend zu Tests, die beweisen, dass zwei unabhängige Installationen sich nicht
gegenseitig beeinflussen können (z. B. getrennte Datenverzeichnisse, keine geteilten Ressourcen) -
nicht Tests einer gemeinsamen Datenbank mit tenant_id-Filterung, die es in diesem Modell nicht
gibt. Lizenz-/Auslieferungsmodell (wie eine neue Installation praktisch verteilt wird) bleibt
weiterhin offen, wird bei Bedarf gesondert geklärt.

**Zurückgestellte Überlegung (16.08.): macOS-Version.** Für eine mögliche künftige Kanzlei
(nicht die aktuelle Pilot-Kanzlei) wurde die Frage nach einer nativen Version für Apple-
Rechner (macOS, nicht iOS) aufgeworfen. Einschätzung: technisch deutlich weniger Aufwand als
eine native iOS-App (die Anwendung selbst - FastAPI, SQLAlchemy, alle Abhängigkeiten - läuft
bereits plattformübergreifend ohne Codeänderung), aber ein eigener, dem Windows-Installer
(Prompt 36) vergleichbar aufwendiger Verpackungsweg: PyInstaller für macOS (muss auf einem
echten Mac laufen, kein Cross-Build aus Linux), `.app`-Bundle statt `.exe`, Code-Signierung/
Notarisierung durch Apple (erfordert eine kostenpflichtige Apple-Developer-Mitgliedschaft),
ggf. `.dmg`-Paketierung. Bewusst NICHT Teil des aktuellen Plans - wird erst relevant, wenn
tatsächlich eine Kanzlei mit Mac-Arbeitsplätzen ansteht, dann als eigener Prompt/eigene
Sitzung analog zu Prompt 36 (auf einem echten Mac, nicht in der Linux-Sandbox oder hier im
Chat).

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
      `311 passed, 1 skipped` (gesamt). Alle 5 Schritte der Privacy-Architektur damit
      abgeschlossen.
- [x] **Schritt 6: Echte Claude-API-Anbindung** (`app/ai_providers/anthropic_writing_provider.py`)
      – nach ausdrücklicher Freigabe durch den Anwalt umgesetzt ("API soll aus DSGVO-Gründen nur
      ohne Übermittlung von persönlichen Daten laufen"). `AnthropicClaudeWritingProvider` hat
      strukturell keinen Zugriff auf Mandantendaten-Modelle – bekommt ausschließlich die bereits
      pseudonymisierte Allowlist-Payload. `ClaudeWritingProvider`-Protocol um Token-Zählung
      erweitert. Getestet ausschließlich gegen gemockten Anthropic-Client (kein API-Key in der
      Sandbox vorhanden, echter API-Aufruf in einer Testsuite unpassend). Sandbox-Testlauf mit
      echtem Python 3.13.15 bestätigt: `317 passed, 1 skipped` (gesamt). **Echter
      End-to-End-Test mit echtem `ANTHROPIC_API_KEY` steht auf dem Zielsystem des Anwalts noch
      aus.**

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
- [x] Drafting-Service (kein Versand-Trigger) – kombiniert LocalAIProvider, LegalResearchService,
      Kanzleiwissen-Suche und die vollständige Privacy-Kette zu strukturierter Ausgabe
      (Entwurf/Quellenliste/offene Prüfungen/Unsicherheiten/verwendete Wissenselemente), Entwurf
      wird als Draft-Zeile persistiert, Blockierung erzeugt keinen Entwurf. Sandbox-Testlauf mit
      echtem Python 3.13.15 bestätigt: `332 passed, 1 skipped` (gesamt).
- [x] unabhängige Review-Engine – eigenes ClaudeReviewProvider-Protocol, kritischer System-Prompt,
      strukturierte Findings (7 Konzept-Kategorien + Schweregrad), erneute Pseudonymisierung des
      bereits rekonstruierten Draft.content vor jedem Review-Aufruf (wichtige, erst bei der
      Umsetzung sichtbar gewordene Erkenntnis), Findings persistiert, Draft-Status-Übergang zu
      legal_review. Sandbox-Testlauf mit echtem Python 3.13.15 bestätigt: `353 passed, 1 skipped`
      (gesamt).
- [x] Audit-Log (append-only) – AuditEvent existierte bereits seit Prompt 04 (durchgehend
      mitgeschrieben); jetzt append-only technisch erzwungen (AuditLogImmutableError bei
      Änderungs-/Löschversuch), automatische Längenbegrenzung, AuditLogService für aktenweise
      Abfrage. Ehrliche Lücke dokumentiert: "Ablage" noch nicht abgedeckt (kommt mit Prompt 35).
      Sandbox-Testlauf mit echtem Python 3.13.15 bestätigt: `368 passed, 1 skipped` (gesamt).
- [x] Workflow-State-Machine (definierte Übergänge) – WorkflowRun existierte seit Prompt 04, wurde
      aber nie tatsächlich verwendet; jetzt fester Übergangsgraph (ALLOWED_TRANSITIONS) +
      WorkflowStateMachine-Service, der jeden Übergang prüft und protokolliert. ARCHIVED terminal,
      ERROR von überall erreichbar, ungültige Übergänge ändern nichts. Sandbox-Testlauf mit echtem
      Python 3.13.15 bestätigt: `383 passed, 1 skipped` (gesamt). **Phase 5 (Antwort und
      Kontrolle) damit vollständig abgeschlossen.**

## Phase 6 – Dashboard (Prompts 21–25)

**Design-Referenz vom Anwalt erhalten** (Screenshot, 14.08.): Zeigt eine sehr passende Umsetzung,
strukturell deckungsgleich mit Konzept §4:
- **Seitenleiste** mit Dashboard/Inbox/Akten/Entwürfe zur Prüfung/Rechtsquellen/Kanzlei-Wissen/
  Postausgang/Einstellungen – bildet direkt auf unsere bereits gebauten Module ab (Prompt 07-19).
- **Split-Pane-Entwurfsansicht:** Originaldokument links, KI-Entwurf rechts – exakt wie im
  Konzept gefordert ("Originaleingang links / Entwurf rechts").
- **Separates Review-Findings-Panel** (passt zu Prompt 18, inkl. Schweregrad-Kennzeichnung).
- **Audit-Log-Panel** direkt in der Entwurfsansicht sichtbar (passt zu Prompt 19).
- **Aktionsleiste unten:** "Freigeben & Postausgang übergeben" / "Bearbeiten" / "Neu generieren" /
  "Zurückweisen" – exakt die im Konzept geforderten vier Aktionen.
- **Verwendete Rechtsquellen** als eigener Bereich unter dem Entwurf (passt zu Prompt 17,
  `source_list`).

Wird als Vorlage für Prompt 21-24 herangezogen, sobald diese Phase ansteht.

- [x] FastAPI-Backend (Inbox, Akten, Dokumente, Entwürfe, Quellen, Aufgaben, Einstellungen, Audit) –
      Prompt 21, 14.08. Neun Router unter `app/api/routers/`, Response-Schemas als Allowlist
      (`app/api/schemas.py`), bewusst nur lesend (GET), keine Authentifizierung (folgt Prompt 26).
      `/api/settings` per Test abgesichert: keine Secrets im Response. Sandbox-Testlauf mit echtem
      Python 3.13.15 bestätigt: `406 passed, 1 skipped` (gesamt), davon 23 neue API-Tests.
- [x] Dashboard-Inbox – Prompt 22, 15.08. Serverseitig gerendert (Jinja2 + lokal ausgeliefertes
      HTMX, kein CDN/kein Node.js-Build), Split-Pane (Liste links/Detail rechts), Filter
      (Alle/Nicht zugeordnet/Eingehend/Ausgehend) per HTMX-Partial ohne vollen Seiten-Reload.
      Akten-Tab-Badge (Signatur-Designelement) zeigt Aktenzeichen bzw. "nicht zugeordnet".
      Sidebar zeigt ehrlich alle 8 Bereiche, nur "Posteingang" tatsaechlich klickbar. Per
      Playwright-Screenshots visuell verifiziert. 19 neue Tests, 425/425 gesamt gruen.
- [x] Anwaltliche Anmerkungen (AttorneyInstructions) – Architekturerweiterung, vom Anwalt
      angefordert und freigegeben, 15.08. (kein nummerierter Plan-Prompt, ergänzt VOR
      Prompt 24). Neues Modell `AttorneyInstruction` (bewusst getrennt von `DraftFeedback` -
      Anmerkung = Arbeitsauftrag an die NÄCHSTE Version, Feedback = Bewertung/Position zu einer
      VORLIEGENDEN Version). `Draft.previous_version_id` löst den bisherigen Versionierungs-Bug
      (in-place-Überschreiben bei "approved_with_edits") strukturell: zentraler Helfer
      `app/drafting/versioning.py` ist die EINZIGE Stelle, die neue Draft-Zeilen anlegt.
      Privacy Gateway um siebtes Allowlist-Feld erweitert (`anonymisierte_anwaltliche_
      anmerkungen`), läuft durch denselben Pseudonymisierungsdurchlauf wie die übrigen sechs
      Felder. `WRITING_SYSTEM_PROMPT` verschärft: keine erfundene anwaltliche Position bei
      fehlender Anweisung. Dashboard-Entwurfsansicht (`/dashboard/drafts/{id}`, noch nicht über
      die Sidebar verlinkt - keine Listenansicht, das bleibt Prompt 24) mit Versions-Zeitleiste,
      Anmerkungs-Panel (beide Aktionen), manueller Bearbeitung. Ein echter Bug beim Bauen
      gefunden+behoben: "Anmerkung speichern" baute unnötig den vollen `DraftingService` auf und
      scheiterte dadurch ohne konfigurierten Claude-API-Key, obwohl dafür keine Claude-Anbindung
      nötig ist. 39 neue Tests (Gateway, Versionierung, AttorneyInstructionService, Web-Router),
      463/463 gesamt grün. Siehe ARCHITECTURE.md §35 für Details und offene Punkte.
- [ ] Akte-Ansicht
- [x] Entwurfsprüfung (Original/Entwurf, Quellen, Findings, Versionsvergleich) – Prompt 24,
      15.08. Listenansicht (`/dashboard/drafts`, Status-Filter, "nur aktuellste Version"),
      Sidebar jetzt verlinkt. Detailansicht erweitert: Original-Nachricht/-Dokumente links,
      Entwurf rechts (wie Design-Referenz), Quellen-/Kanzleiwissen-Panel, Review-Findings-Panel
      (mit Auslöse-Button), Audit-Log-Panel, Aktionsleiste (Freigeben & Postausgang übergeben /
      Neu generieren / Zurückweisen). Echte Lücke gefunden+geschlossen: `DraftSourceLink`/
      `DraftKnowledgeItemLink` persistieren erstmals, welche Quellen/Wissenselemente TATSÄCHLICH
      für eine Version verwendet wurden (vorher nur transient). `AttorneyInstruction` in die
      aktenweite Audit-Abfrage aufgenommen (war vorher unsichtbar). 23 neue Tests
      (5 Drafting-Service, 18 Web-Router), 485/485 gesamt grün. Offene Punkte: kein UI-Trigger
      im Posteingang, um aus einer Nachricht direkt einen Entwurf zu erstellen (Entwürfe
      entstehen bisher nur programmatisch/direkt); "Freigeben & Postausgang übergeben" markiert
      nur den Status - eine echte Postausgang-Übergabe folgt erst Prompt 25. Siehe
      ARCHITECTURE.md §36.
- [x] Postausgang (kein automatischer Versand) – Prompt 25, 15.08. Neues Modell `OutboxEntry`
      (Warteschlange, status pending/sent) + `OutboxService` (add_to_outbox/mark_as_sent) -
      dieselbe architektonische Grundregel wie beim `MailProvider` (Prompt 07): STRUKTURELL
      keine Versandfähigkeit (kein SMTP, kein Aufruf einer Versand-API im gesamten Modul, per
      Test abgesichert). "Freigeben & Postausgang übergeben" (Prompt 24) übergibt jetzt
      automatisch in den Postausgang; "Als versendet markieren" bestätigt nur eine bereits
      AUSSERHALB des Systems erfolgte manuelle Handlung. Listenansicht `/dashboard/outbox`
      (Wartend/Versendet/Alle), Sidebar verlinkt. Ein echter Bug beim Bauen gefunden+behoben:
      zweifaches "Als versendet markieren" (z. B. Doppelklick) crashte zunächst mit 500 statt
      sauber abzufangen. 19 neue Tests (9 Service, 10 Web-Router), 504/504 gesamt grün. Siehe
      ARCHITECTURE.md §37. **Phase 6 (Dashboard) damit vollständig abgeschlossen.**

## Phase 7 – Sicherheit und Produktisierung (Prompts 26–35)
- [x] Rollen/Berechtigungen (Admin, Anwalt, Mitarbeiter) – Prompt 26, 15.08. Session-basierte
      Authentifizierung (signierte 8h-Cookies, Argon2-Hashing), feste Rechte-Matrix exakt nach
      Vorgabe des Anwalts, CSRF-Schutz auf jeder mutierenden Aktion, serverseitige Durchsetzung
      unabhängig vom UI (kein ausgeblendeter Button als Berechtigungsprüfung). Alle `/api/...`-
      Endpunkte jetzt login-pflichtig. Freitext-"Ihr Kürzel/E-Mail" komplett aus allen
      Formularen entfernt - Actor kommt ausschließlich aus der Session. Admin-Nutzerverwaltung,
      Setup-Skript für initialen Admin (Passwort nie im Code, erzwungene Änderung). Ein
      wichtiger Bug gefunden+behoben: `Secure`-Cookie-Flag verhinderte Sessions über HTTP
      (Dev/Test) - jetzt automatisch abgeleitet aus `app_env` (gleiches Muster wie Secret Key).
      52 neue Auth-Tests (alle 18 vom Anwalt geforderten Szenarien abgedeckt), 541/541 gesamt
      grün. Siehe ARCHITECTURE.md §38 für Details, Rechte-Matrix-Bestätigung und offene
      Sicherheitspunkte.
- [x] Security Review + SECURITY.md – Prompt 27, 15.08. Vollständiger Bericht in
      `SECURITY_REVIEW.md`. Zwei KRITISCHE, bis dahin unentdeckte Schwachstellen gefunden und
      behoben: (1) Path Traversal über E-Mail-Anhang-Dateinamen - erlaubte beliebiges
      Dateischreiben ausserhalb des Speicherverzeichnisses, aus der Ferne ohne
      Authentifizierung auslösbar; (2) PII-Leck über Redirect-URL/Referer-Header bei
      blockierten Claude-Anfragen (erkannte Namen landeten im Klartext in der URL, damit
      potenziell im Referer-Header an Google Fonts). Zusätzlich behoben: Symlink-Angriff auf
      den überwachten Scan-Ordner. Anti-Prompt-Injection-Klausel in beide System-Prompts
      (Writing/Review) ergänzt - deckt strukturell alle 5 geforderten Kanäle (E-Mail/PDF/OCR/
      Rechtsquellen/Kanzlei-Wissen) gleichzeitig ab, da alle durch dieselben Payload-Felder
      laufen (per Test bewiesen). Die 5 aus Prompt 26 mitgebrachten offenen Punkte einzeln
      neu bewertet (Risiko Prototyp/Produktiv, Fix, Priorität, Pilot- vs. Produktiv-Gate) -
      keiner blockiert einen internen Pilotbetrieb, mehrere sind vor echtem
      Produktiv-/Mehrkanzlei-Einsatz zwingend. 12 neue Angriffssimulationstests, 553/553
      gesamt grün. Siehe SECURITY_REVIEW.md für die vollständige Bewertung.
- [x] Prompt-Injection-Schutz + Tests mit manipulierten Dokumenten – Prompt 28, 15.08.
      Baut auf Prompt 27 auf: End-to-End-Beweis mit einer ECHTEN, per PyMuPDF erzeugten PDF-
      Datei mit eingebettetem Injection-Text (nicht nur ein simulierter String) durch die
      tatsächliche Extraktions-/Kontext-/Gateway-Pipeline. Positiver Nebenfund: laute,
      grossgeschriebene Injection-Versuche werden bereits von der bestehenden PII-Heuristik
      abgefangen (fail-closed, bevor Claude erreicht wird). Zusätzlich gefunden+behoben:
      keine Obergrenze für die Anzahl der in den Sachverhalt einbezogenen Dokumente (Kosten-/
      DoS-Amplifikation über viele kleine Anhänge möglich) - auf 30 neueste Dokumente
      begrenzt. OCR-Artefakt-Simulation, manipulierte externe Quelle, kombinierter E-Mail-
      Body+Anhang-Angriff ebenfalls getestet. 12 neue Tests, 565/565 gesamt grün. Siehe
      SECURITY_REVIEW.md, Abschnitt 2.1 und "Ergänzung Prompt 28".
- [x] Nachtrag (außerhalb der Prompt-Reihenfolge, vorgezogen), 15.08.: Rate-Limiting beim
      Login + Session-Sofortwiderruf bei Passwortänderung. Auf Wunsch des Anwalts vorgezogen,
      da der Pilotbetrieb mit ECHTEN Mandantendaten stattfinden wird (beide Punkte waren im
      Security Review als "vor Pilotbetrieb mit echten Daten empfehlenswert" bzw. "vor
      öffentlichem Zugriff zwingend" bewertet, Netzwerkerreichbarkeit des Pilotbetriebs zum
      jetzigen Zeitpunkt nicht final entschieden - daher defensiv vorgezogen statt auf die
      Netzwerkentscheidung zu warten). Wichtige Korrektur dabei entdeckt: die ursprüngliche
      Einschätzung "Deaktivierung wirkt erst nach bis zu 8h" war zu pessimistisch - wirkt
      bereits seit Prompt 26 sofort (jede Anfrage lädt den Nutzer frisch aus der DB). Die
      tatsächliche Lücke war enger: ein gestohlenes Cookie überlebte eine Passwortänderung
      unverändert - behoben über `User.sessions_invalidated_after`. Prozesslokaler
      In-Memory-Rate-Limiter (kein Redis) sperrt nach 5 Fehlversuchen für 15 Minuten, sowohl
      pro E-Mail als auch pro IP. Neue Admin-Aktion "Sessions beenden" (ohne Passwortzwang).
      2FA und die produktionsweite Härtung (öffentliche Erreichbarkeit) bewusst weiterhin
      zurückgestellt - siehe SECURITY_REVIEW.md für die aktualisierte Bewertung. 13 neue
      Tests, 578/578 gesamt grün.
- [x] Synthetischer Testdaten-Simulator – Prompt 29, 15.08. Neues Modul `app/synthetic_data/`
      mit `SyntheticDataGenerator`: erzeugt vollständig fiktive, aber realistische Kanzlei-
      Fälle (Mandant + Akte + eingehende Nachricht + Dokument + ggf. Frist) über 6 verschiedene
      Fallszenarien (Einspruch Steuerbescheid, Betriebsprüfung, Umsatzsteuer-Nachschau, Mahnung,
      Vertragsprüfung, Kündigungswiderspruch). Deterministisch bei gesetztem Seed (wichtig für
      den reproduzierbaren Qualitäts-Benchmark aus Prompt 30) - ruft an keiner Stelle die
      Claude API auf. CLI-Skript `scripts/seed_synthetic_data.py --count N --seed S`. Ein
      echter Bug während der Entwicklung gefunden+behoben: `Matter.reference_number` trägt
      eine UNIQUE-Constraint - ohne Kollisionsprüfung hätte wiederholte Generator-Nutzung
      gegen dieselbe Datenbank irgendwann fehlschlagen können; jetzt aktive Prüfung+Retry.
      Per Browser-Screenshot verifiziert (20 synthetische Fälle im Posteingang, ausschließlich
      `.invalid`-Testdomain, keine Ähnlichkeit zu echten Personen). 13 neue Tests, 591/591
      gesamt grün.
- [x] End-to-End-Test – Prompt 30, 15.08. EINE durchgängige Fallreise über die gesamte, in
      Prompts 04-29 gebaute Kette hinweg, über die ECHTE HTTP-/Dashboard-Schicht (nicht durch
      isolierte Service-Aufrufe wie sonst üblich): synthetischer Fall (Prompt 29) → Entwurf
      erstellen → Original/Entwurf/Quellen/Findings/Audit ansehen → Anmerkung speichern →
      Anmerkung anwenden (neue Version) → Review-Engine-Prüfung → manuelle Bearbeitung (weitere
      Version) → Rollentrennung mitten in der echten Reise geprüft (Mitarbeiter kann NICHT
      freigeben) → Freigabe → automatische Postausgang-Übergabe → als versendet markieren →
      lückenloser Audit-Trail über die gesamte Reise verifiziert → Cross-Matter-Isolation
      geprüft. Bedeutender Fund dabei: die PII-Heuristik aus dem Security Check blockiert 4 von
      6 realistischen synthetischen Szenarien fälschlich (deutsche Rechts-/Verwaltungsbegriffe
      + Gesetzesabkürzungen lösen das "zwei Großbuchstaben-Wörter"-Muster aus) - kein
      Datenschutzrisiko (fail-closed), aber ein spürbarer Nutzbarkeits-Fund für den
      Pilotbetrieb, dauerhaft per Test festgehalten. Siehe SECURITY_REVIEW.md, Abschnitt 2.9.
      3 neue Tests, 594/594 gesamt grün.
- [x] Fehler-/Retry-System – Prompt 31, 15.08. Neues Modell `ProcessingError` (unter
      `app/models/`, konsistent mit Projektkonvention) + `RetryService` mit exponentiellem
      Backoff (Basis 120s, Faktor 4: ~2/8/32 Min.), max. 3 Versuche (konfigurierbar), danach
      `failed_permanent` (kein automatischer Retry mehr - kein Endlosschleifen-Risiko, per Test
      bewiesen). Verdrahtet in `DocumentProcessingService` (OCR) und `IntakeWatcher` (Intake) -
      die beiden Stellen, die laut bestehender Doku explizit auf Prompt 31 warteten.
      Parallelitätsschutz über einen "retrying"-Zwischenstatus (kein doppelter Ausführungs-
      versuch bei Doppelklick/gleichzeitigem Skriptlauf). Dashboard-Ansicht `/dashboard/errors`
      (alle drei Rollen, manueller "Jetzt erneut versuchen"-Button, CSRF-geschützt) + CLI-
      Skript `scripts/retry_failed_items.py` (periodischer Lauf ohne Hintergrunddienst, z. B.
      Windows-Aufgabenplanung) - beide nutzen dieselbe `execute_retry`-Dispatch-Logik. **Zwei
      echte, im Zuge der Absicherung gefundene und behobene PII-Lecks:** (1) die OCR-
      Fehlermeldung enthielt den vollen gespeicherten Dateipfad, der den ursprünglichen
      (potenziell personenbezogenen) Dateinamen aus einem E-Mail-Anhang trug; (2) selbst nach
      dem ersten Fix blieb die zugrunde liegende PyMuPDF-Exception selbst pfadhaltig - beide
      Fälle jetzt auf den reinen Exception-Typnamen reduziert. Zusätzlich gefunden+behoben:
      `extract_text()` war nicht gegen fehlende/beschädigte Dateien abgesichert und hätte die
      gesamte Verarbeitung unkontrolliert abstürzen lassen statt sie dem neuen Fehler-/Retry-
      System zu übergeben. 38 neue Tests (25 Service-Ebene, 13 Web-Ebene), 632/632 gesamt grün.
      Siehe ARCHITECTURE.md §40.
- [x] Logging/Monitoring (ohne sensible Inhalte) – Prompt 32, 16.08. Zentrale Logging-
      Konfiguration (`app/observability/logging_config.py`, in `app/main.py`-Lifespan
      eingebunden) - vorher konfigurierte KEIN Modul das Python-Logging zentral (INFO-Logs
      gingen schlicht verloren). Konsole immer, optionale rotierende Log-Datei
      (`LOG_FILE_PATH`), Drittanbieter-Logger (watchdog/urllib3/httpx) auf WARNING gedrosselt.
      Admin-only Systemstatus-Seite `/dashboard/monitoring` (Fehler-/Retry-Zähler, Nutzerzahlen,
      Audit-Aktivität 24h, reine Ja/Nein-Konfigurationsstatus - nie Secrets). Operative Log-
      Zeilen ergänzt (Login-Rate-Limit-Sperren, RetryService). **Zwei echte PII-Lecks
      gefunden+behoben:** `ProcessingError`/`AuditEvent` für `IntakeFile`-Fehler nutzten den
      vollen Quelldateipfad als `entity_id` - anders als bei `Document` (UUID) trägt dieser
      Pfad den unveränderten ursprünglichen Dateinamen und könnte einen echten Namen enthalten;
      betraf sowohl das neue operative Log als auch rückwirkend den bereits aus Prompt 31
      bestehenden Audit-Text. Neue strukturelle Regressionswache
      (`test_no_logging_call_interpolates_known_sensitive_variable_names`) durchsucht
      dauerhaft alle `logger.*`-Aufrufe im Quellcode nach riskanten Variablennamen. 22 neue
      Tests (7 Logging-Konfiguration, 3 PII-Schutzwache, 6 Monitoring-Web-Layer, plus indirekt
      abgedeckte Retry-Service-Anpassungen), 648/648 gesamt grün. Siehe ARCHITECTURE.md §41.
- [x] KI-Kostenkontrolle – Prompt 33, 16.08. Neues Modul `app/cost_control/`: `pricing.py`
      (Kostenschätzung pro Modell, USD/Million Token, bevorzugt genaue Input-/Output-
      Aufteilung, fällt sonst auf ein geschätztes Verhältnis zurück - ausdrücklich als
      Schätzung markiert, keine exakte Abrechnung) + `CostControlService` (`check_before_call`
      wird VOR jedem kostenpflichtigen Claude-Aufruf geprüft, blockiert bei konfiguriertem und
      erreichtem Monatsbudget). `ApiCallLog` (Prompt 21) erweitert um `input_tokens`,
      `output_tokens`, `estimated_cost_usd`. **Echter, bis dahin bestehender Tracking-Gap
      geschlossen:** die Review-Engine hat bislang GAR KEINE Tokens/Kosten getrackt (nur
      Drafting) - jetzt symmetrisch für beide Pfade. Budget-Blockierung end-to-end bewiesen:
      der WritingProvider wird bei ausgeschöpftem Budget nachweislich gar nicht erst
      aufgerufen. Kostenanzeige in der Admin-Systemstatus-Seite (Prompt 32) ergänzt -
      laufender Monat, Gesamt, Budget-Auslastung in %, klar als Schätzung gekennzeichnet.
      41 neue Tests (22 Service-/Pricing-Ebene inkl. 3 echte Integrationstests gegen
      DraftingService, 6 Web-Layer für die erweiterte Monitoring-Seite indirekt), 670/670
      gesamt grün. Siehe ARCHITECTURE.md §42.
- [x] ModelProvider-Abstraktion – Prompt 34, 16.08. Neues Modul `app/ai_providers/factory.py`:
      einzige Stelle im Projekt, die `settings.llm_provider` tatsächlich zur Provider-AUSWAHL
      nutzt. **Echte, seit Prompt 03 bestehende Lücke geschlossen:** `llm_provider` existierte
      bereits als Konfigurationsfeld, wurde aber nie ausgewertet - `app/web/service_factory.py`
      baute `AnthropicClaudeWritingProvider`/`AnthropicClaudeReviewProvider` fest verdrahtet,
      unabhängig vom Einstellungswert (faktisch nur ein Anzeigefeld in der Settings-API).
      `DraftingService`/`ReviewEngine` kennen weiterhin nur die bestehenden Protokolle - ein
      künftiger zweiter Provider (z. B. lokales Modell via Ollama, weiterhin bewusst NICHT
      umgesetzt, siehe unten) würde ausschließlich in der neuen Factory ergänzt, ohne
      Drafting-/Review-Schicht oder Dashboard-Router anzufassen. `service_factory.py` auf
      2 Zeilen Aufruf statt dupliziertem Konstruktionscode reduziert; alter Exception-Name
      (`WritingProviderNotConfiguredError`) als Alias erhalten - keine Änderung an bestehenden
      Importen/Tests nötig. 9 neue Tests, 679/679 gesamt grün. Siehe ARCHITECTURE.md §43.
      **Bewusst NICHT umgesetzt:** ein zweiter, echter Provider (Ollama) - bleibt weiterhin
      eine offene Entscheidung, siehe unten "Offene Entscheidung: Ollama".
- [x] Export/Backup – Prompt 35, 16.08. Zwei getrennte, komplementäre Funktionen:
      `app/backup/` (`BackupService`) - vollständige Systemsicherung als ZIP: konsistenter
      SQLite-Snapshot (über die native `sqlite3`-Backup-API, nicht bloßes Dateikopieren -
      garantiert Konsistenz auch bei einer theoretisch gleichzeitig laufenden Schreib-
      transaktion) + beide Dokumentenspeicher-Verzeichnisse (Intake, Mail-Anhänge).
      `app/export/` (`MatterExportService`) - strukturierter Export EINER Akte (Nachrichten,
      Dokumente, alle Entwurfsversionen, Anmerkungen, Fristen, Postausgang-Status,
      Audit-Trail) als ZIP mit menschenlesbarem JSON-Manifest + Original-Dokumentkopien -
      relevant für DSGVO-Auskunftsersuchen (Art. 15/20) und Aktenschließung. Beide
      Archivtypen ausdrücklich als "genauso schützenswert wie die Produktionsdatenbank"
      gekennzeichnet (unpseudonymisierte Inhalte). CLI-Skript `scripts/create_backup.py`
      + Admin-only Dashboard-Seite `/dashboard/backup` mit Download-Buttons für beide
      Funktionen - per echtem Browser-Download-Klick verifiziert (nicht nur Backend-Test).
      29 neue Tests (15 Service-Ebene inkl. Konsistenz-Wiederherstellungsprobe, 14 Web-Ebene),
      708/708 gesamt grün. Siehe ARCHITECTURE.md §44.

**Phase 7 (Sicherheit und Produktisierung, Prompts 26-35) damit vollständig abgeschlossen.**

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
