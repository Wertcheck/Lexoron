# ARCHITECTURE.md – KI-gestützte Kanzlei-Pipeline

Status: Entwurf nach Schritt 1 (Projektstart und Bestandsaufnahme)
Basis: `Anwaltskanzlei_AI_Pipeline_Claude_Code_Konzept` (Konzeptdokument)

## 1. Ausgangslage (Bestandsaufnahme)

- Repository ist aktuell leer (Neuanlage).
- Umgebung: Python 3.12 (Konzept empfiehlt 3.13.x – siehe offene Entscheidung 1), git verfügbar,
  kein bestehendes Datenbankschema, keine bestehenden Secrets/Configs.
- Es existieren noch keine produktiven Dateien. Diese Datei und `TODO.md` sind die ersten Artefakte.
- Es wurden **keine Mandantendaten, Secrets oder produktiven Inhalte** in diesem Repository angelegt
  oder verändert.

## 2. Zielbild (aus Konzept übernommen)

Workflow-System für eine Anwaltskanzlei:
Eingang → Erfassung → Klassifikation → Aktenzuordnung → Kontextaufbau → Rechtsquellenprüfung →
Entwurf → Prüfung → Freigabe → Ablage → optionaler Versand.

Grundsatz: **Automatisierung ja, autonome rechtliche Entscheidung nein.** Kein automatischer
Versand ohne menschliche Freigabe.

## 3. Architekturschichten

| Schicht | Zweck |
|---|---|
| Frontend/Dashboard | Inbox, Akten, Aufgaben, Entwürfe, Quellen, Einstellungen |
| Backend (FastAPI) | zentrale Anwendungs-/API-Schicht |
| Workflow Engine | State Machine je Vorgang (siehe §6) |
| Ingestion | E-Mail- und Dateieingänge (Watchdog, IMAP/Graph) |
| Document Processing | OCR, Textextraktion, Klassifikation, Metadaten |
| Case/Matter Layer | Mandanten, Akten, Beteiligte, Vorgänge |
| Knowledge/RAG | freigegebenes Kanzleiwissen, frühere Schriftsätze |
| Legal Sources | Gesetze/Rechtsprechung, strikt getrennt von Mandantenwissen |
| LLM Layer | Claude API, hinter einer `ModelProvider`-Abstraktion |
| Audit Layer | unveränderliche Ereignisprotokolle |
| Storage | Dateisystem + relationale DB (SQLite Dev / PostgreSQL Prod) + Suchindex |

## 4. Technologieentscheidungen

- **Sprache/Framework:** Python 3.12 (verfügbar) statt der im Konzept genannten 3.13.x – siehe
  offene Entscheidung 1. FastAPI + Pydantic + SQLAlchemy.
- **DB:** SQLite für lokale Entwicklung/Prototyp, PostgreSQL als produktive Option (per Config
  austauschbar, kein hartes Vendor-Lock-in im Code).
- **Dateiüberwachung:** `watchdog` (rekursives Monitoring, geeignet für Scan-Eingang).
- **OCR:** austauschbare Komponente hinter einer Schnittstelle (konkretes Paket = offene
  Entscheidung 2).
- **Mail:** Provider-Adapter-Pattern (IMAP zuerst oder Microsoft Graph zuerst = offene
  Entscheidung 3), Workflow bleibt vom konkreten Adapter entkoppelt.
- **LLM:** Claude API über eine `ModelProvider`-Schnittstelle, damit kein Workflow-Code direkt an
  ein Modell gebunden ist.
- **Secrets:** ausschließlich über `.env`/Environment-Variablen, niemals im Repository.

## 5. Datenmodell (Kernentitäten, aus Konzept §7)

`Client, Matter, Party, Message, Document, Task, Deadline, Draft, Source, KnowledgeItem,
WorkflowRun, AuditEvent, User/Role`

Prinzip: Das Dateisystem enthält Originale/Exporte; die Datenbank führt Beziehungen und Status.
Rechtsquellen (`Source`) werden strikt getrennt von Mandanten-/Aktendaten geführt.

## 6. Workflow-Zustände (aus Konzept, Prompt 20)

```
RECEIVED → PROCESSING → NEEDS_CLASSIFICATION → NEEDS_MATTER_MATCH →
READY_FOR_REVIEW → DRAFTED → LEGAL_REVIEW → APPROVED → ARCHIVED →
OUTBOX_READY
              (ERROR ist von jedem Zustand aus erreichbar)
```
Nur definierte Übergänge sind erlaubt; jeder Übergang wird auditiert.

## 7. Sicherheits- und Isolationsprinzipien (verbindlich für alle folgenden Schritte)

1. Mandantendaten werden standardmäßig lokal/kontrolliert verarbeitet; an externe APIs (Claude)
   gehen nur die für die jeweilige Aufgabe notwendigen Inhalte.
2. Dokument-/E-Mail-Inhalte sind **untrusted input** – sie dürfen niemals Systemregeln, Tools oder
   Berechtigungen überschreiben (Prompt-Injection-Schutz technisch UND im Prompt-Layer).
3. Aktenkontext ist strikt pro Akte isoliert; Retrieval darf nie über die Akten-/Berechtigungsgrenze
   hinweg mischen.
4. Rechtsquellen dürfen nie erfunden werden; fehlender Beleg wird als offener Prüfpunkt markiert,
   nie stillschweigend übergangen.
5. Kein automatischer Versand ohne explizite menschliche Freigabe (Default: deaktiviert).
6. Secrets nie in Code, Logs oder Git.
7. Jede wesentliche KI-Aktion ist über das Audit-Log nachvollziehbar (Quelle, Version, Zeitpunkt).

## 8. Konfigurierbarkeit statt fest verdrahtetem Workflow

Alle veränderlichen Aspekte (überwachte Ordner, Mailprovider, Dokumenttypen, Aktenerkennung,
Freigaberegeln, Rechtsquellen, Vorlagen, Nutzer/Rollen) laufen über ein zentrales
Konfigurationssystem, nicht über Codeänderungen. Ziel: mehrere Kanzlei-Profile bei gleichem Kern.

## 9. Annahmen (explizit, zur Bestätigung)

- A1: Entwicklung erfolgt zunächst als lokaler Web-Stack (FastAPI + Browser-Dashboard), nicht als
  natives Desktop-Programm.
- A2: Erste Version bedient **einen** Mandanten-/Kanzleikontext produktiv; Multi-Kanzlei-Profile
  (Prompt 38) sind vorbereitet, aber nicht Teil des MVP.
- A3: Für den Prototyp wird ausschließlich mit synthetischen Testdaten gearbeitet (keine echten
  Mandantendaten, auch nicht anonymisiert).
- A4: Python 3.12 wird verwendet (statt 3.13.x aus dem Konzept), sofern nicht anders gewünscht.
- A5: Es wird zunächst **ein** E-Mail-Provider-Adapter gebaut, nicht mehrere parallel.

## 10. Entscheidungen und offene Punkte

### Bestätigt (Stand Prompt 02)

1. **Python-Version:** verbindliche Zielversion ist **3.13.x** (auf dem Windows-Entwicklungsrechner
   des Anwalts vorhanden). `pyproject.toml` setzt `requires-python = ">=3.13"`.
   - **Update (nach Prompt 05):** Die Claude-Sandbox verfügt inzwischen ebenfalls über echtes
     Python 3.13.15 (offizieller `astral-sh/python-build-standalone`-Build, bezogen über
     GitHub-Releases, keine feste URL im Repository). Ab sofort läuft der Sandbox-Testlauf mit
     `.venv313` und damit ohne den zuvor nötigen `--ignore-requires-python`-Workaround. Frühere
     Sandbox-Testläufe (Prompt 02–05) liefen noch mit Python 3.12 im Workaround-Modus und wurden
     zusätzlich final auf dem Windows-Zielsystem bestätigt; ab dem nächsten Prompt gilt ein
     Sandbox-Testlauf mit `.venv313` als vollwertiger 3.13-Test, ergänzend zur weiterhin
     empfohlenen Verifikation auf dem Windows-Zielsystem des Anwalts.
   - **Finaler Test bestanden:** Auf dem Windows-Zielsystem des Anwalts (Python 3.13.15)
     wurden Installation (`pip install -e ".[dev]"`) und Tests (`pytest`) erfolgreich und ohne
     jeden Workaround durchgeführt: `2 passed`. Damit ist Prompt 02 vollständig
     abgeschlossen.
2. **Datenbank:** SQLite für den Prototyp. Die Datenzugriffsschicht wird (ab Prompt 03/04, via
   SQLAlchemy + konfigurierbarer `DATABASE_URL`) von Anfang an so abstrahiert, dass später
   PostgreSQL ohne Neuentwicklung von Datenmodell oder Geschäftslogik möglich ist.
3. **OCR-Engine:** **Tesseract** (lokal, kostenlos, datenschutzfreundlich), umgesetzt in
   Prompt 06 über `pytesseract`.
4. **Mail-Provider zuerst:** **IMAP** (generisch, funktioniert mit den meisten Anbietern),
   umgesetzt in Prompt 07 über `imaplib`. Microsoft Graph kann bei Bedarf später als weiterer
   `MailProvider` ergänzt werden.
5. **Such-/RAG-Layer:** **Vektorspeicher** (nicht nur FTS5) – der Anwalt hat sich bewusst für
   echte semantische Suche entschieden, da reine Volltextsuche für "ähnliche frühere Fälle"/
   Wissensbausteine zu limitiert wäre. Umgesetzt in Prompt 11 über lokale Embeddings
   (`fastembed`, großes mehrsprachiges Modell), kombiniert mit Metadatenfiltern und Volltext
   (Hybrid-Suche) statt einer reinen Vektorlösung.

### Weiterhin bewusst offen (werden an vorgesehener Stelle im Plan entschieden)

6. **Zielumgebung für Installer-Tests** – relevant ab Prompt 36.

## 12. Konfigurationssystem (Stand Prompt 03)

Implementiert als `app/config/settings.py` (`pydantic-settings`), geladen über eine gecachte
`get_settings()`-Funktion. Wichtigste Eigenschaften:

- **Sichere Defaults:** `require_human_approval_before_send=True`, `retention_days=0` (keine
  automatische Löschung), `ocr_enabled=False`.
- **Validierung:** negative `retention_days`, leere Ordner-/Quelleneinträge und falsche Typen
  führen zu einem klaren `ValidationError` statt stillschweigend akzeptiert zu werden.
- **Secrets:** `mail_password` und `anthropic_api_key` sind `SecretStr` – erscheinen nicht in
  `str()`/`repr()` der Settings (z. B. beim versehentlichen Loggen).
- **DB-Abstraktion bestätigt:** Wechsel SQLite → PostgreSQL erfolgt ausschließlich über
  `DATABASE_URL`, ohne Codeänderung (per Test abgesichert).
- **Bewusste Platzhalter ohne Festlegung:** Felder für Mail, OCR, LLM, Rechtsquellen,
  Vorlagen und Freigaberegeln sind generisch gehalten; die eigentliche fachliche Logik/das
  endgültige Schema entsteht erst in den jeweils zuständigen späteren Prompts.

## 13. Datenmodell (Stand Prompt 04)

Implementiert als SQLAlchemy-2.0-Modelle in `app/models/`, Migrationen über Alembic in
`migrations/` (nutzt dieselbe `DATABASE_URL`-Abstraktion wie die Anwendung selbst – kein
Secret/keine feste URL in `alembic.ini`).

- **IDs:** UUID4 als String (nicht auto-increment), über `UUIDPrimaryKeyMixin`.
- **Zeitstempel:** `created_at`/`updated_at` auf jeder Entität außer `AuditEvent` (siehe unten).
- **Isolation:** `Matter` ist die zentrale Isolationseinheit; aktenbezogene Entitäten
  (`Party, Message, Document, Task, Deadline, Draft, WorkflowRun`) referenzieren `matter_id`.
  `Message`/`Document` erlauben `matter_id = NULL`, solange der Workflow-Zustand
  `NEEDS_MATTER_MATCH` noch nicht aufgelöst ist. Ein erster, rudimentärer Isolationstest
  (`test_matters_of_different_clients_stay_isolated`) ist vorhanden; die vollständige
  Isolationsprüfung (Retrieval, KI-Kontext, Cross-Tenant-Zugriffstests) folgt planmäßig erst
  in Prompt 41.
- **Original vs. Metadaten:** `Document.file_path` (Original im Dateisystem) ist strikt getrennt
  von `Document.extracted_text` (erst ab Prompt 06 befüllt) – siehe Konzept §7.
- **Rechtsquellen strikt getrennt:** `Source` hat keine `matter_id`, keine Verbindung zu
  Mandantendaten (siehe Konzept §6).
- **Sichere Defaults:** `KnowledgeItem.approval_status="pending"`, `Source.approval_level=
  "entwurf"`, `Deadline.review_status="unreviewed"` – nichts gilt automatisch als freigegeben
  oder bestätigt.
- **Versionierung:** `Draft.version`, `KnowledgeItem.version` als Integer, beginnend bei 1.
- **AuditEvent bewusst ohne `updated_at`** (kein `TimestampMixin`, nur `created_at`) – append-only
  laut Grundregel; Anwendungscode darf Einträge nicht nachträglich ändern.
- **Workflow-Status:** `WorkflowRun.status` als freier String, beschränkt auf die in §6
  festgelegte Zustandsmenge (`VALID_WORKFLOW_STATUSES`); die eigentliche State-Machine mit
  erlaubten Übergängen entsteht erst in Prompt 20.
- **Migration verifiziert:** `alembic upgrade head` / `downgrade base` / erneut `upgrade head`
  erfolgreich getestet (manuell und automatisiert über `tests/test_migrations.py`).

## 14. Scan-Ordner-Überwachung / Intake (Stand Prompt 05)

Implementiert in `app/ingestion/`:

- **`stability.py`:** `wait_until_stable()` verhindert, dass eine noch geschriebene Datei
  (z. B. langsamer Scanner/Netzlaufwerk) vorzeitig verarbeitet wird – prüft wiederholt die
  Dateigröße, bis sie über mehrere Prüfungen hinweg unverändert bleibt.
- **`intake.py` (`IntakeService`):** kopiert (nicht verschiebt) eine stabile Datei in einen
  konfigurierbaren Intake-Bereich (`INTAKE_STORAGE_DIR`, Default `data/intake`), berechnet einen
  SHA-256-Hash, legt einen `Document`-Datensatz an (`matter_id` bewusst `None` – Aktenzuordnung
  folgt erst in Prompt 09) und schreibt ein begleitendes `AuditEvent`. Bei Fehlern (Datei nicht
  stabil/nicht mehr vorhanden) wird `IntakeError` geworfen; es entsteht dann weder eine Kopie
  noch ein Datenbankeintrag.
- **`watcher.py` (`IntakeWatcher`):** überwacht die konfigurierten `INTAKE_WATCHED_FOLDERS`
  rekursiv über `watchdog` und übergibt neu erkannte Dateien an den `IntakeService`. Nicht
  existierende Ordner werden übersprungen (Warnung statt Absturz); Fehler bei einzelnen Dateien
  brechen die Überwachung der übrigen nicht ab (vollständiges Fehler-/Retry-System folgt in
  Prompt 31).
- **Bewusst nicht enthalten:** Textextraktion/OCR (Prompt 06), Aktenzuordnung (Prompt 09),
  Klassifikation (Prompt 08).
- **Getestet:** Hash-Korrektheit, Stabilitätsprüfung inkl. simuliertem langsamem Schreibvorgang,
  Original bleibt beim Kopieren unangetastet, Namenskollisionen im Intake-Bereich werden
  vermieden, Audit-Event wird erzeugt, echter End-to-End-Test mit tatsächlichen
  Dateisystem-Events.

## 15. Dokumentverarbeitung und OCR (Stand Prompt 06)

Implementiert in `app/documents/`:

- **`extraction.py`:** direkte Textextraktion aus PDF (PyMuPDF), DOCX (python-docx) und TXT.
  Bilddateien (`.png/.jpg/.tif/...`) gelten immer als OCR-Kandidat. Ein konfigurierbarer
  Schwellenwert (`MIN_EXTRACTED_TEXT_LENGTH`, Default 20 Zeichen) verhindert, dass minimale
  Textreste (z. B. eine einzelne eingebettete Kopfzeile) fälschlich als "vollständiger Text"
  gelten. Unbekannte Formate werden erkannt und markiert, ohne die Verarbeitung abzubrechen.
- **`ocr.py`:** OCR über **Tesseract** (Entscheidung aus ARCHITECTURE.md §10 bestätigt), via
  `pytesseract`. PDF-Seiten werden über PyMuPDF gerastert (kein zusätzliches Tool wie Poppler
  nötig). Sprachen konfigurierbar (`OCR_LANGUAGES`, Default `deu+eng`). Optionaler expliziter
  Pfad zur Tesseract-Programmdatei (`TESSERACT_CMD`) für Umgebungen, in denen Tesseract nicht
  automatisch im PATH liegt (v. a. Windows).
- **`service.py` (`DocumentProcessingService`):** orchestriert Extraktion + OCR und aktualisiert
  `Document.extracted_text`/`Document.ocr_status`. **Sicherer Default:** Ist OCR global
  deaktiviert (`OCR_ENABLED=false`, Standardeinstellung), bleibt ein Scan-Dokument im Status
  `pending` – es gilt **nie** stillschweigend als erledigt. `file_path` (Original) wird nie
  verändert. Jede Verarbeitung erzeugt ein begleitendes `AuditEvent`.
- **Neuer Dokumentstatus:** `unsupported_format` ergänzt die in Prompt 04 vorgesehene Statusmenge
  (`not_needed/pending/done/failed`) – siehe aktualisierten Kommentar in `app/models/document.py`.
- **Bewusst nicht enthalten:** jede Form inhaltlicher/juristischer Interpretation des extrahierten
  Texts – reine technische Extraktion. Klassifikation folgt in Prompt 08.
- **Setup-Hinweis für den Anwalt (Windows):** Tesseract OCR ist eine externe Programmdatei, keine
  Python-Bibliothek – muss separat installiert werden (z. B. über den offiziellen
  Tesseract-Windows-Installer), sonst schlägt OCR mit `OcrError` fehl, auch bei
  `OCR_ENABLED=true`. Pfad ggf. über `TESSERACT_CMD` in `.env` setzen.
- **Getestet:** Textextraktion aus echtem PDF/DOCX-Text, Erkennung von OCR-Bedarf bei
  gescannten/leeren PDFs und Bilddateien, echte Tesseract-Ausführung (kein Mock) gegen
  synthetische Testbilder, sicherer Pending-Default bei deaktiviertem OCR, Format nicht
  unterstützt wird erkannt statt abzustürzen, Original bleibt unverändert, Audit-Event wird
  erzeugt.

## 16. E-Mail-Ingestion (Stand Prompt 07)

Implementiert in `app/mail/`, als **Provider-Abstraktion, entkoppelt vom Workflow**
(Konzept-Vorgabe für Prompt 07):

- **`base.py`:** `MailProvider` ist ein `Protocol` mit genau einer Methode
  (`fetch_new_messages`). Es existiert strukturell **keine Sende-Methode** – automatischer
  Versand ist über diese Abstraktion nicht nur konfigurativ deaktiviert, sondern auf
  Code-Ebene unmöglich (per Test abgesichert: `test_mail_provider_has_no_send_capability`,
  `test_imap_provider_has_no_send_method`).
- **`parsing.py`:** reines, netzwerkunabhängiges Parsing roher E-Mail-Bytes (Absender,
  Empfänger, Betreff inkl. RFC-2047-Dekodierung für Umlaute, Message-ID, Datum, Body-Text
  bevorzugt `text/plain`, Anhänge einzeln extrahiert).
- **`imap_provider.py` (`ImapMailProvider`):** konkreter, erster Provider (Entscheidung aus
  ARCHITECTURE.md §10 bestätigt: IMAP zuerst). Nutzt nur `imaplib` aus der
  Python-Standardbibliothek, ruft ausschließlich `UNSEEN`-Nachrichten ab, markiert sie optional
  als gelesen (`MAIL_MARK_SEEN`).
- **`service.py` (`MailIngestionService`):** überführt abgerufene Nachrichten in `Message`-
  Datensätze; **Anhänge werden einzeln als eigene `Document`-Einträge gespeichert**, nicht als
  Teil des Nachrichtentexts (analog zum Scan-Intake aus Prompt 05). Deduplizierung über
  `external_message_id`, damit dieselbe Nachricht nie doppelt als `Message` landet. `matter_id`
  bleibt `None` (Aktenzuordnung folgt in Prompt 09). Jede Erfassung erzeugt ein `AuditEvent`.
- **Bewusst nicht enthalten:** jede Form von automatischer Antwort oder Versand (siehe oben),
  Aktenzuordnung (Prompt 09), inhaltliche Klassifikation (Prompt 08).
- **Weitere Provider (z. B. Microsoft Graph):** können später als zusätzliche
  `MailProvider`-Implementierung ergänzt werden, ohne `MailIngestionService` oder den Workflow
  zu ändern.
- **Getestet:** Parsing synthetischer Nachrichten (inkl. Umlaute, mehrere Anhänge, fehlende
  Message-ID), `MailIngestionService` gegen einen Fake-Provider (kein echter Mailserver nötig),
  Deduplizierung, Anhang-Speicherung getrennt vom Original-Nachrichtentext, `ImapMailProvider`
  gegen eine gemockte IMAP-Verbindung (Login/Select/Search/Fetch/Mark-Seen/Logout-Ablauf sowie
  Nur-Lese-Zugriff verifiziert).

## 17. Dokumentklassifikation (Stand Prompt 08)

Implementiert in `app/classification/`. **Bewusst noch ohne LLM** (Entscheidung mit dem Anwalt
abgestimmt: Platzhalter zuerst, echte Modell-Anbindung erst mit Prompt 17/34 – siehe auch die
Diskussion zu lokalem vs. Cloud-LLM weiter unten in diesem Dokument bzw. im Chatverlauf).

- **`schema.py` (`ClassificationResult`):** striktes Pydantic-Schema – `document_type` nur aus
  einer festen Menge (`ALLOWED_DOCUMENT_TYPES`, kein Freitext), `confidence` zwingend zwischen 0
  und 1, `reasoning` darf nicht leer sein. `requires_manual_review(threshold)` kapselt die Logik
  "Konfidenz unter Schwelle → keine automatische Aktenzuordnung erlaubt" (relevant ab Prompt 09).
- **`classifier.py`:** `DocumentClassifier` ist ein `Protocol` (analog zu `MailProvider`), damit
  eine spätere LLM-Implementierung diese Abstraktion ersetzen kann, ohne Service oder Schema zu
  ändern. `PlaceholderDocumentClassifier` ist eine reine Keyword-/Regex-Heuristik – **kein LLM,
  kein ML** – mit hart gedeckelter, absichtlich niedriger Konfidenz (max. 0.4), damit dieser
  Platzhalter niemals fälschlich als "sicher genug" gilt.
- **`service.py` (`ClassificationService`):** setzt auf `Document.extracted_text` (Prompt 06)
  auf. Ohne extrahierten Text (z. B. OCR noch ausstehend) wird die Klassifikation übersprungen
  und protokolliert, statt zu raten. Ergebnis wird sowohl in einzelnen Spalten (für Filterung)
  als auch vollständig als JSON (`classification_result_json`, für Nachvollziehbarkeit) auf
  `Document` gespeichert. Jede Klassifikation erzeugt ein `AuditEvent` inkl. Hinweis, ob manuelle
  Prüfung erforderlich ist.
- **Migration:** `add document classification fields` – 6 neue, nullable Spalten auf
  `documents` (upgrade/downgrade verifiziert).
- **Konfigurierbar:** `CLASSIFICATION_LOW_CONFIDENCE_THRESHOLD` (Default 0.6).
- **Bewusst nicht enthalten:** echte Themenzusammenfassung, echte Namens-/Beteiligtenerkennung
  (beides liefert der Platzhalter nicht – erst mit LLM sinnvoll möglich), jede automatische
  Aktenzuordnung (Prompt 09).
- **Getestet:** Schema-Validierung (unbekannter Typ/außerhalb Wertebereich/leere Begründung
  jeweils abgelehnt), Keyword-Erkennung für alle Dokumenttypen, Konfidenz bleibt in jedem Fall
  niedrig, Aktenzeichen-Erkennung per Regex, Service-Verhalten bei fehlendem Text (Skip statt
  Rateergebnis), Persistierung inkl. JSON-Serialisierung, Audit-Eintrag dokumentiert
  Prüfbedarf.

## 18. Notiz für spätere Prompts: API-Nutzung für Review-Engine (Prompt 18)

Festgehalten am 2026-08-13, zur Umsetzung erst bei Prompt 18 relevant: Für die **Review-Engine**
(unabhängige Prüfung KI-generierter Antwortentwürfe auf fehlende Fakten, Widersprüche, unbelegte
Rechtsbehauptungen etc.) hat der Anwalt bestätigt, dass seine eigene **Anthropic-API** (Claude)
genutzt werden darf – unabhängig von der noch offenen Cloud-vs.-lokal-Entscheidung für die
eigentliche Drafting-Logik (Prompt 17/34, siehe ARCHITECTURE.md-Diskussion zu lokalen LLMs).

Das ändert nichts an der aktuellen Umsetzungsreihenfolge (Prompt 09 als Nächstes) – dient nur
als Gedächtnisstütze, damit diese Präferenz beim Erreichen von Prompt 17/18 nicht neu erfragt
werden muss. Die konkrete Ausgestaltung (z. B. ob Review-Engine und Drafting denselben oder
unterschiedliche Provider nutzen) wird erst dort entschieden.

## 19. Aktenzuordnung / Matter-Matching (Stand Prompt 09)

Implementiert in `app/matching/`:

- **`schema.py` (`MatchResult`/`MatchCandidate`):** striktes Schema; `decision` nur aus
  `{auto_assigned, needs_review, no_match}`.
- **`matcher.py` (`MatterMatchingService`):** reine, DB-lesende Bewertungslogik. Kombiniert vier
  gewichtete Signale: Aktenzeichen-Exakttreffer (0.9 – bewusst hoch, da ein eindeutiges
  Aktenzeichen für sich allein genügen soll), bekannte E-Mail-Adresse (0.3), unscharfer
  Beteiligten-Namens-Treffer (0.2), sowie eine **Platzhalter**-Themenähnlichkeit über `difflib`
  (0.1 – **kein Embedding/keine echte Semantik**, bewusst konsistent mit der noch offenen
  RAG-Layer-Entscheidung aus Prompt 11/12). Ambiguität (zwei Top-Kandidaten mit fast gleichem
  Score) verhindert automatische Zuordnung selbst bei hohem Score.
- **`service.py` (`MatterAssignmentService`):** wendet ein `MatchResult` tatsächlich an –
  setzt `matter_id` auf `Message` **und kaskadiert auf alle zugehörigen `Document`-Anhänge** nur
  bei `auto_assigned`. **Wichtige Kopplung an Prompt 08:** Hat auch nur eines der zugehörigen
  Dokumente keine oder eine zu niedrige Klassifikationskonfidenz
  (`CLASSIFICATION_LOW_CONFIDENCE_THRESHOLD`), wird eine automatische Zuordnung verhindert,
  selbst bei sehr hohem Matching-Score – direkte Umsetzung der Konzeptvorgabe aus Prompt 08
  ("Bei geringer Sicherheit darf keine automatische Aktenzuordnung erfolgen"). Jede Entscheidung
  erzeugt ein `AuditEvent` (`matter_match_auto_assigned`/`_needs_review`/`_no_match`).
- **Konfigurierbar:** `MATCHING_AUTO_ASSIGN_THRESHOLD` (Default 0.85), `MATCHING_REVIEW_THRESHOLD`
  (Default 0.4, darf laut Validierung nicht über der Auto-Schwelle liegen).
- **Bewusst nicht enthalten:** eine manuelle Zuordnungs-Inbox/UI (das ist Dashboard, Prompt 22) –
  `needs_review`/`no_match`-Fälle sind über `AuditEvent` nachvollziehbar, aber es gibt noch keine
  Oberfläche dafür.
- **Getestet:** alle vier Signale einzeln und in Kombination, Auto-Zuordnung bei eindeutigem
  Aktenzeichen, Ambiguität verhindert Auto-Zuordnung trotz (künstlich abgesenkter) überschrittener
  Schwelle, fehlende/niedrige Klassifikationskonfidenz blockiert Auto-Zuordnung, Kaskade auf
  Dokument-Anhänge, Nachrichten ganz ohne Anhänge können weiterhin automatisch zugeordnet werden,
  Audit-Eintrag wird erzeugt.

## 20. Fristen- und Aufgabenanalyse (Stand Prompt 10)

Implementiert in `app/deadlines/`. Nutzt das bereits in Prompt 04 angelegte `Deadline`-Modell
vollständig (keine Migration nötig).

- **`schema.py` (`ExtractedDeadline`):** striktes Schema mit `source_text` (Textstelle),
  `raw_date_text` (Rohtext der Datums-/Fristangabe), optionalem `due_date`, `confidence` und
  nicht-leerer `reasoning`.
- **`extractor.py`:** `DeadlineExtractor`-Protocol + `PlaceholderDeadlineExtractor` – erkennt
  absolute Daten (`15.03.2027` sowie `15. März 2027`) und relative Fristangaben
  (`binnen zwei Wochen`, `innerhalb von 14 Tagen`, ohne auflösbares `due_date` mangels
  Bezugsdatum). **Konfidenz hängt vom Kontext ab:** ein Datum in der Nähe eines
  Fristen-Schlüsselworts ("Frist", "bis zum", "spätestens", "binnen", "innerhalb", "Termin")
  erhält moderate Platzhalter-Konfidenz (0.5), ein "nacktes" Datum ohne solchen Kontext (z. B.
  ein reines Referenzdatum wie "Ihr Schreiben vom …") nur 0.15 – bewusst niedrig, da es sich
  ebenso gut um kein Fristdatum handeln kann. Kein LLM, keine echte Fristenberechnung nach
  Fristenrecht (Wochenend-/Feiertagsregeln, Zustellfiktionen) – das bleibt Aufgabe des Anwalts.
- **`service.py` (`DeadlineAnalysisService`):** setzt sowohl `Document.extracted_text`
  (Prompt 06) als auch `Document.matter_id` (Prompt 09) voraus – ohne Aktenzuordnung kann keine
  `Deadline` erzeugt werden (`Deadline.matter_id` ist nicht nullable). Beide Fälle (kein Text /
  keine Akte) werden übersprungen und protokolliert statt zu raten. **`review_status` wird vom
  Service nie gesetzt** – der Modell-Default `"unreviewed"` (Prompt 04) bleibt für jede erzeugte
  Frist bestehen, direkte Umsetzung der Konzeptvorgabe "keine Frist endgültig als verbindlich
  markieren". Jede Analyse erzeugt ein `AuditEvent`.
- **Bewusst nicht enthalten (Scoping-Entscheidung):** separate `Task`-Erzeugung für erkannten
  "Handlungsbedarf" – das Konzept nennt für Prompt 10 nur konkrete Pflichtfelder für Fristen,
  nicht für Aufgaben. `Task` existiert als Modell (Prompt 04) und kann bei Bedarf in einem
  späteren Schritt an diese Analyse angebunden werden. Eine manuelle Prüf-Inbox für
  `review_status="unreviewed"` (Dashboard-UI) ist Teil von Prompt 22, nicht dieses Prompts.
- **Getestet:** Datumsformate (numerisch, Monatsname), relative Fristen ohne Datum,
  Konfidenz-Abstufung je nach Schlüsselwort-Nähe, ungültige Daten werden nicht durchgereicht,
  mehrere Treffer in einem Dokument, Service-Skip-Verhalten bei fehlendem Text/fehlender
  Aktenzuordnung, `review_status` bleibt in jedem Fall `"unreviewed"`, Audit-Ereignisse.

## 21. Akten-Such-/Kontextschicht (Stand Prompt 11)

**Hinweis zur Entstehung:** Ein Teil dieser Umsetzung entstand in einem Gesprächsabschnitt, der
durch automatische Konversations-Zusammenfassung für mich zwischenzeitlich nicht mehr direkt
einsehbar war. Ich habe den vorgefundenen Code vollständig geprüft, dokumentiert und die
Modellwahl nachträglich mit dem Anwalt abgestimmt (siehe unten), bevor ich sie als abgeschlossen
markiert habe.

Implementiert in `app/search/` + `app/models/embedding.py`:

- **Technologieentscheidung (aktualisiert):** `fastembed` (ONNX-Runtime) statt
  `sentence-transformers` (PyTorch) – bewusst, weil `sentence-transformers` transitiv volle
  PyTorch-/CUDA-Bibliotheken mitinstalliert (mehrere GB, GPU-Support hier nie benötigt). Modell:
  **`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`** (großes, mehrsprachiges
  Modell, ~1 GB, bewusst statt der kleineren MiniLM-Variante gewählt – bessere Qualität war dem
  Anwalt wichtiger als Downloadgröße). Läuft nach einmaligem Modell-Download vollständig offline,
  reine CPU-Inferenz.
- **`models/embedding.py` (`Embedding`):** generische Tabelle (`entity_type`/`entity_id`) statt
  einer reinen `Document`-Bindung – funktioniert bereits jetzt für `Document` UND ist vorbereitet
  für `KnowledgeItem` (Prompt 12), ohne spätere Schemaänderung. Vektor als JSON-Array (Text)
  gespeichert – kein natives SQLite-Vektorformat, bewusst einfach für den Prototyp; bei starkem
  Datenwachstum später durch dedizierten Vektorspeicher ersetzbar, ohne die Such-API zu ändern.
- **`search/embeddings.py` (`EmbeddingProvider`/`FastEmbedProvider`):** Protocol-Abstraktion wie
  bei `MailProvider`/`DocumentClassifier`. Modell wird lazy geladen (erst bei erstem `embed()`-
  Aufruf), damit z. B. reine Konfigurationstests keinen Download auslösen.
- **`search/service.py` (`DocumentSearchService`):** **Kernregel strukturell erzwungen:**
  `search_within_matter()` verlangt zwingend `matter_id` – es gibt keine Methode für eine
  aktenübergreifende Dokumentensuche (per Test abgesichert:
  `test_no_matter_scoped_search_method_exists_without_matter_id`). Kombiniert Volltext-Substring-
  Treffer mit semantischer Cosine-Similarity zu einem gemeinsamen Score (`match_type`:
  `fulltext`/`semantic`/`hybrid`). `search_knowledge_base()` ist bewusst getrennt, liefert
  ausschließlich freigegebene (`approval_status == "approved"`) `KnowledgeItem`s und **niemals**
  Mandantendokumente – direkte Umsetzung der Konzeptvorgabe ("Context-Agent darf nur Dokumente
  aus der aktuellen Akte oder ausdrücklich freigegebene globale Wissensquellen abrufen").
- **`search/schema.py` (`SearchResult`):** jedes Ergebnis referenziert zwingend eine konkrete
  Entität (`entity_type`/`entity_id`), keine anonymen/generischen Treffer.
- **Getestet:** strikte Aktenisolation (auch bei identischem Text in zwei Akten), unzugeordnete
  Dokumente (`matter_id=None`) tauchen nie in einer Aktensuche auf, Metadatenfilter, Volltext- und
  semantische Treffer (über einen deterministischen `FakeEmbeddingProvider` in Tests – siehe
  unten), Wissensbasis-Suche liefert nie Dokumente und nie ungeprüftes Wissen, architektonischer
  Schutztest gegen künftige aktenübergreifende Suchmethoden.
- **Sandbox-Einschränkung (analog zu Python 3.13):** `huggingface.co` ist aus der Claude-Sandbox
  nicht erreichbar (`x-deny-reason: host_not_allowed`) – der echte Modell-Download konnte hier
  nicht verifiziert werden. Alle Kernlogik-Tests laufen daher gegen einen dokumentierten
  **Fake-Provider** (`tests/fake_embedding_provider.py`, deterministisches Bag-of-Words-Hashing,
  klar als Test-Fixture gekennzeichnet, niemals in Produktionscode verwendet). Ein echter Test
  (`tests/test_search_embeddings_real_model.py`) versucht das konfigurierte Modell zu laden und
  wird bei fehlendem Netzwerkzugriff übersprungen statt fälschlich als Fehlschlag gewertet –
  **dieser Test sollte auf dem Windows-Zielsystem des Anwalts tatsächlich durchlaufen und ist
  dort noch final zu verifizieren.**

## 22. Kanzlei-Wissensbasis (Stand Prompt 12)

Implementiert in `app/knowledge/`, aufbauend auf dem `KnowledgeItem`-Modell aus Prompt 04 und der
Suchschicht aus Prompt 11.

- **Modellerweiterung:** `source` (Herkunft), `valid_from`/`valid_until` (Gültigkeitsbereich),
  `created_by_user_id` ergänzen die Basisfelder aus Prompt 04. Migration nutzt bewusst Alembics
  Batch-Modus (`op.batch_alter_table`), da SQLite kein direktes `ALTER` von Fremdschlüssel-
  Constraints unterstützt – ohne Batch-Modus schlägt der Downgrade fehl.
- **`schema.py` (`KnowledgeItemImport`):** validiert Eingaben (nicht-leerer Titel/Inhalt,
  `valid_from` darf nicht nach `valid_until` liegen).
- **`service.py` (`KnowledgeItemService`):** vier Kernoperationen:
  - **Import:** immer `pending`, Version 1.
  - **Inhaltsänderung:** Version +1, Status **zwingend zurück auf `pending`** – eine frühere
    Freigabe gilt nie automatisch für neuen Inhalt weiter (Konzept §5 wörtlich umgesetzt).
  - **Freigabe:** setzt `approved` und **stößt die Indizierung** in der Suchschicht aus Prompt 11
    an (`DocumentSearchService.index_knowledge_item`), damit frisch freigegebenes Wissen sofort
    durchsuchbar ist.
  - **Deaktivierung:** setzt `deactivated`, verlangt eine **zwingende, nicht-leere Begründung**
    (`reason`). Kein zusätzliches Löschen des Embedding-Eintrags nötig – `search_knowledge_base`
    filtert ohnehin auf `approval_status == "approved"`.
  - **`list_items`:** metadatenbasiertes Filtern/Auflisten (Kategorie, Fachgebiet, Status,
    optional nur aktuell gültige Einträge) – für die spätere Verwaltungsoberfläche (Prompt 22),
    unabhängig von der semantischen Suche.
- **Rückwirkende Ergänzung an Prompt 11:** `search_knowledge_base` berücksichtigt jetzt zusätzlich
  den Gültigkeitsbereich – ein abgelaufener oder noch nicht gültiger, aber freigegebener
  Textbaustein wird nicht mehr zurückgegeben.
- **Bewusst nicht enthalten:** vollständige Versions-**historie** (Diff früherer Inhalte) – analog
  zu `Draft.version` wird nur die aktuelle Version gehalten, Änderungen sind über `AuditEvent`
  grob (Zeitpunkt, Versionssprung), nicht als vollständiger Inhalts-Diff nachvollziehbar.
- **Getestet:** Import-Defaults, Versionssprung + Status-Reset bei Inhaltsänderung, Freigabe löst
  Indizierung aus (per Test-Double verifiziert), Deaktivierung verlangt Begründung, Metadatenfilter,
  Gültigkeits-Filterung (abgelaufen / noch nicht gültig / aktuell gültig) sowohl im Service als auch
  in der Suchschicht.

## 23. Feedback des Anwalts (Stand Prompt 13)

Implementiert in `app/feedback/`, neues `DraftFeedback`-Modell (Migration mit Batch-Modus, da FK
auf `drafts`).

- **`DraftFeedback`:** speichert pro Feedback-Runde einen Schnappschuss (`original_content` vor
  der Aktion), optional `edited_content`, `comment` und `approval_status`
  (`approved`/`approved_with_edits`/`rejected`). Mehrere Feedback-Runden zu einem Draft bleiben
  als getrennte Einträge erhalten (keine Überschreibung), sodass die Änderungshistorie über
  mehrere Runden nachvollziehbar ist.
- **`DraftFeedbackService.record_feedback`:** aktualisiert bei `approved_with_edits` zusätzlich
  den `Draft` selbst (Version +1, wie im etablierten Versionierungsmuster), übernimmt den Status
  (`approved`/`rejected`) auf `Draft.status`. Rein protokollierend – **erzeugt niemals von sich
  aus Kanzleiwissen.**
- **`DraftFeedbackService.promote_to_knowledge`:** der laut Konzept geforderte **separate,
  explizite** Workflow "als Kanzleiwissen freigeben". Nutzt `KnowledgeItemService.import_item`
  (Prompt 12) – das Ergebnis ist immer ein neuer, weiterhin `pending` Wissenseintrag; auch eine
  bewusste Übernahme durchläuft die normale Freigabepflicht erneut.
- **Schema (`DraftFeedbackInput`):** `approved_with_edits` erfordert nicht-leeren
  `edited_content`; `rejected` erfordert einen nicht-leeren `comment` (Begründungspflicht).
- **Getestet:** einfache Freigabe ohne Inhaltsänderung, Freigabe mit Änderung (Versionssprung +
  Inhaltsübernahme), Ablehnung, Audit-Ereignisse, **Feedback allein erzeugt nie ein
  `KnowledgeItem`**, explizite Übernahme erzeugt `pending`-Eintrag mit Herkunftsverweis,
  Fallback auf Originalinhalt ohne Änderung, mehrere Feedback-Runden bleiben als getrennte
  Einträge mit korrektem Original-Schnappschuss erhalten.

## 24. Rechtsquellen-Modul (Stand Prompt 14)

**Hinweis zur Entstehung:** Wie bei Prompt 11 entstand auch dieser Teil in einem Abschnitt, der
durch Konversations-Zusammenfassung zwischenzeitlich für mich nicht einsehbar war. Vollständig
geprüft (Code, Migration, Tests) und für gut befunden, bevor ich ihn als abgeschlossen markiere.

Implementiert in `app/sources/`, aufbauend auf dem `Source`-Modell aus Prompt 04 (erweitert um
`document_date` und `provider_name`).

- **`SourceProvider`-Protocol + `ManualSourceProvider`:** Provider-Abstraktion analog zu
  `MailProvider`/`DocumentClassifier`, erlaubt wie im Konzept gefordert mehrere Provider. Aktuell
  einziger Provider: manuelle Eingabe durch den Anwalt – **automatisierte Anbindungen an
  juristische Datenbanken sind bewusst nicht Teil dieses Prompts**, da das Konzept selbst festhält,
  dass vorher geklärt werden muss, welche Datenbanken/Portale die Kanzlei nutzen darf (Lizenzen,
  API-Zugänge) – eine Geschäftsentscheidung, die noch nicht getroffen wurde.
- **Kernregel technisch durchgesetzt:** `ManualSourceProvider.resolve()` reichert nichts an,
  gibt exakt zurück, was eingegeben wurde – "Die KI darf keine Quelle erfinden" (Konzept §6)
  gilt auch für Provider, per Test abgesichert (`test_manual_provider_never_invents_fields`).
- **Quellenklassen erweitert um Steuerrecht-Spezifikum:** `"Verwaltungsanweisung"` als eigener
  Typ (nicht unter "Sonstiges") – BMF-Schreiben und vergleichbare Verwaltungsanweisungen sind in
  der steuerrechtlichen Praxis von zentraler Bedeutung (siehe Kanzlei-Kontext).
- **`SourceService`:** Import immer `entwurf`; `approve_source` → `freigegeben`; `mark_outdated`
  → `veraltet`, verlangt zwingende Begründung. **Wichtig:** eine als veraltet markierte Quelle
  bleibt in der Datenbank erhalten (nicht gelöscht) – "ein späteres Update darf nicht die
  historische Beurteilung eines alten Vorgangs überschreiben" (Konzept §6, Rechtsaktualität).
  `list_sources` filtert nach Typ/Freigabestatus/aktueller Gültigkeit, analog zu
  `KnowledgeItemService.list_items`.
- **Getestet:** Import mit Default-Status, Audit-Ereignisse, Freigabe, Als-veraltet-Markierung
  (inkl. Begründungspflicht und Erhalt in der DB), Filterung, striktes Schema (unbekannter Typ
  abgelehnt, `Verwaltungsanweisung` als gültiger Typ bestätigt), Provider erfindet nichts.

## 25. Legal-Research-Workflow (Stand Prompt 15)

Implementiert in `app/research/`, aufbauend auf Prompt 11 (Suchschicht) und Prompt 14
(Rechtsquellen).

- **Rückwirkende Erweiterung der Suchschicht:** `DocumentSearchService` um `index_source`/
  `search_sources` ergänzt (analog zu `index_knowledge_item`/`search_knowledge_base`) –
  durchsucht ausschließlich `approval_level == "freigegeben"`-Quellen, berücksichtigt
  Gültigkeitsbereich, unterstützt Filterung nach `source_type`. `SourceService.approve_source`
  stößt jetzt die Indizierung an (analog zu `KnowledgeItemService.approve`).
- **Bug gefunden und behoben:** `SearchResult.entity_type` validierte nur gegen
  `{Document, KnowledgeItem}` – `Source`-Treffer wurden dadurch mit einem `ValidationError`
  abgelehnt. Ergänzt, 7 zuvor fehlschlagende Tests danach grün.
- **Architektur-Schutztest angepasst:** Der Test, der sicherstellt, dass jede `search_`-Methode
  `matter_id` verlangt, hatte `search_sources` fälschlich als Verstoß gewertet – Ausnahmeliste um
  `search_sources` ergänzt (Rechtsquellen sind wie Kanzleiwissen bewusst global, nicht
  aktenbezogen).
- **`LegalResearchService.generate_queries_from_matter`:** deterministische Ableitung von
  Suchfragen aus `Matter.title`/`practice_area` – bewusst kein LLM (Konsistenz mit
  Prompt 08/09/10).
- **`LegalResearchService.research`:** fragt `search_sources` ab, reichert **jeden** Treffer mit
  dem vollständigen Quellenbeleg an (Titel, Fundstelle, URL, Dokumentdatum – nicht nur
  Score/Snippet). Verwaiste Embedding-Einträge (Quelle zwischenzeitlich gelöscht) werden
  übersprungen statt ein Ergebnis ohne echten Beleg zu liefern.
- **"Nicht ausreichend belegt" explizit:** `sufficiently_supported: bool` + `reasoning`-Text
  nennen das wörtlich, wenn kein Treffer die konfigurierte Schwelle
  (`RESEARCH_MIN_SCORE_FOR_SUFFICIENT`, Default 0.5) erreicht – auch wenn schwache Treffer
  vorhanden sind, aber nicht ausreichen.
- **`research_for_matter`:** führt alle generierten Suchfragen aus, protokolliert Ergebnis
  zusammenfassend als `AuditEvent` (Anzahl Anfragen, wie viele ausreichend belegt).
- **Getestet:** Query-Generierung inkl. Deduplizierung, vollständiger Quellenbeleg pro Treffer,
  kein Finding ohne tatsächlich existierende `Source`-Zeile, explizite "nicht ausreichend
  belegt"-Meldung bei fehlenden Treffern, "ausreichend belegt" bei starkem Treffer,
  Quellentyp-Filterung, `research_for_matter` mit Audit-Protokollierung.

## 26. Prompt-/Policy-Layer (Stand Prompt 16)

Implementiert in `app/promptlayer/` + neues `Policy`-Modell (Migration, kein `ALTER` auf
Bestandstabellen nötig).

- **`Policy`-Modell:** eigenes, einfaches Modell statt Wiederverwendung von `KnowledgeItem` –
  Policies sind Verhaltensregeln für die Entwurfserstellung (Schreibstil, Anrede), kein
  zitierfähiges Fachwissen. Versionierung analog zum etablierten Muster: neue Version statt
  Überschreiben, nur eine Version pro `name` gleichzeitig `is_active`, alte Versionen bleiben in
  der Datenbank erhalten.
- **`PolicyService`:** `create_version` (inkrementiert automatisch, deaktiviert Vorgänger,
  Audit-Event), `get_active_policy`.
- **`PromptContextBuilder.build_context`:** setzt fünf strikt getrennte Abschnitte zusammen –
  `system` (fest, versioniert über `SYSTEM_RULES_VERSION`), `kanzleiregeln` (aus aktiver
  `Policy`), `fallkontext` (Aktendaten), `rechtsquellen` (von Prompt 15 übergebener Text),
  `nutzeranweisung`. **Kernregel technisch durchgesetzt:** `matter_id` ist ein zwingender
  Parameter (kein Default, kein optionaler Wert), und **jede** Datenbankabfrage im Fallkontext
  (`Document`, `Deadline`, `Task`) filtert explizit danach – exakt dasselbe Muster wie
  `search_within_matter` (Prompt 11). Per Test abgesichert, dass Akte-A-Kontext niemals
  Akte-B-Daten enthält, selbst bei wörtlich ähnlichem Text.
- **Trust-Markierung als Vorbereitung auf Prompt 28 (Prompt-Injection-Schutz):** `system` und
  `nutzeranweisung` sind `is_trusted=True` (von Kanzlei/Anwalt kontrolliert); `fallkontext` und
  `rechtsquellen` sind `is_trusted=False` (stammen aus externen/Mandantendokumenten). Die
  festen Systemregeln selbst weisen bereits explizit darauf hin, dass Inhalt aus diesen beiden
  Abschnitten niemals als Anweisung behandelt werden darf.
- **`PromptContext.render()`:** baut eine klar mit Tags abgegrenzte Textstruktur
  (`<system>...</system>` usw.) – keine Vermischung von Anweisung und Daten in einem
  unstrukturierten Textblob.
- **Bewusst noch kein LLM-Aufruf:** Dieser Layer bereitet nur den Kontext vor; die eigentliche
  Modell-Anbindung folgt erst in Prompt 17/34.
- **Getestet:** Pflichtparameter `matter_id`/`user_instruction`, unbekannte Akte wird abgelehnt,
  alle fünf Abschnitte vorhanden, korrekte Trust-Markierung, **Aktenisolation mit echten
  Mandantennamen im Test verifiziert**, Fristen/offene Aufgaben im Fallkontext enthalten,
  aktive Policy wird korrekt eingebunden, fehlende Policy führt zu Platzhalter statt Absturz,
  Policy-Versionierung (Inkrementierung, Deaktivierung, unabhängige Namen, Erhalt alter
  Versionen), architektonischer Schutztest für die `matter_id`-Pflicht.

## 27. Privacy-by-Design / Claude API Boundary

**Status: Schritt 1 von mehreren umgesetzt.** Diese Architekturvorgabe kam vom Anwalt nach
Abschluss von Prompt 16, vor dem eigentlichen Beginn von Prompt 17 (Drafting-Service). Sie ist
laut Vorgabe **verbindlich für das gesamte Projekt** und darf bei künftigen Schritten nicht
stillschweigend umgangen werden.

### Grundprinzip

Local-First / Privacy-by-Design: Sämtliche sensiblen/personenbezogenen Mandatsdaten bleiben
grundsätzlich lokal. Die Claude API darf **ausschließlich für die sprachliche Textproduktion**
verwendet werden (Formulierung/Verbesserung/Korrektur eines bereits lokal inhaltlich
bestimmten Antwortschreibens) – niemals für Aktenanalyse, Aktenzuordnung, Rechtsrecherche,
Fristenbestimmung, Strategieentscheidungen oder Versand.

### Was bereits lokal ist (Bestandsaufnahme vor dieser Erweiterung)

Praktisch die gesamte bisher gebaute Pipeline erfüllt das Prinzip bereits, weil durchgehend
"Platzhalter/lokal zuerst" entschieden wurde: E-Mail-Ingestion (Prompt 07, IMAP), OCR
(Prompt 06, Tesseract), Klassifikation (Prompt 08), Aktenzuordnung (Prompt 09),
Fristenanalyse (Prompt 10), Suche/RAG (Prompt 11, fastembed), Wissensbasis (Prompt 12),
Rechtsquellen (Prompt 14/15), Datenbank (SQLite). **Es gab bislang keine Claude-API-Anbindung
im Projekt** – diese Vorgabe kommt also, bevor der erste API-Aufruf überhaupt gebaut wird.

### Geplanter Datenfluss (Zielbild, noch nicht vollständig umgesetzt)

```
Lokale Daten → Lokale Analyse (Prompt 08-16) → Antwortinhalt lokal bestimmt (Prompt 16)
  → ClaudePrivacyGateway
      → PII-Erkennung
      → Pseudonymisierung (Mapping NUR lokal)
      → Security-Check (7-Punkte-Liste) → bei Unklarheit: KEIN API-Aufruf
  → ClaudeWritingProvider (Allowlist-Payload)
  → Claude API
  → Antworttext (pseudonymisiert)
  → Lokale Entanonymisierung → Lokale Qualitätsprüfung → Draft → Dashboard → Anwaltsprüfung
```

### Bisher umgesetzt: PII-Erkennung + Pseudonymisierung (`app/privacy/`)

- **`detectors.py`:** Regex-basierte Erkennung für strukturierte Formate – E-Mail, Telefon
  (Format-Erkennung, nicht erschöpfend), IBAN (variable Länge, deutsche und andere
  EU-Formate), Steuer-ID (Formaterkennung, **kein** Prüfziffern-Algorithmus), Aktenzeichen,
  Kundennummer, Vertragsnummer, Datum (numerisch + Monatsname), Betrag, Adresse
  (Straße+Hausnummer, PLZ+Ort getrennt erkannt).
- **Namen werden NICHT per Regex geraten** (unzuverlässig ohne echtes NER-Modell) – stattdessen
  über `known_entities`: der Aufrufer übergibt bereits bekannte Werte aus strukturierten Daten
  (`Party.name`, `Client.name`), die dann exakt gesucht werden. Das ist zuverlässiger als
  generisches Namens-Raten, weil wir die relevanten Namen im Aktenkontext ohnehin bereits
  kennen.
- **Überlappungsauflösung:** bei sich überschneidenden Treffern gewinnt der längere/
  spezifischere Treffer.
- **`pseudonymizer.py` (`Pseudonymizer`):** ersetzt erkannte PII durch Platzhalter
  (`[MANDANT_01]`, `[GEGNER_01]`, `[IBAN_01]` usw.), gleicher Originalwert erhält innerhalb
  eines Aufrufs immer denselben Platzhalter. `reconstruct()` macht die Ersetzung rückgängig.
  **Reine, seiteneffektfreie Funktion** – kein DB-Zugriff, kein Netzwerkaufruf, keine
  Persistierung des Mappings an dieser Stelle.
- **Zwei echte Bugs gefunden und behoben** (manuelle Verifikation vor den formalen Tests):
  Betrag-Regex scheiterte an einer Wortgrenze nach "€" (kein Wortzeichen), IBAN-Regex verlangte
  fälschlich vierstellige Gruppen durchgehend und verlor dadurch die letzte, kürzere Restgruppe.
- **Getestet (deckt Vorgabe-Punkt 12 vollständig ab):** alle Kategorien einzeln, mehrere
  Personen in einem Text, verschachtelte PII in einem Satz, PII in Zitaten, PII in
  dateinamenartigem Text, absichtlich manipulierter Text/Prompt-Injection-Versuch (Detektor
  erkennt PII trotzdem korrekt, interpretiert aber nie den Text selbst), keine Falsch-Positive
  bei PII-freiem Text, Überlappungsauflösung, exakte Roundtrip-Rekonstruktion.

### Schritt 2: Security-Check (`app/privacy/security_check.py`)

- **`SecurityCheckService.check()`** deckt alle 7 Punkte der Vorgabe ab: Zweck-Allowlist
  (`ALLOWED_PURPOSES` – ausschließlich Textproduktions-Aufgaben wie `formulate_draft`,
  `improve_draft`, `optimize_style`, nie Analyse/Zuordnung/Recherche/Versand), erneute
  PII-Prüfung **auf dem bereits pseudonymisierten Text** (deckt unvollständige Pseudonymisierung
  auf), Abgleich Mapping↔Text (jeder Platzhalter muss tatsächlich im Text vorkommen), sowie eine
  Heuristik für möglicherweise nicht erkannte Namen.
- **Kernregel technisch durchgesetzt:** jeder gefundene Grund führt zu `passed=False` – es gibt
  keinen Modus, der Warnungen ignoriert und trotzdem grünes Licht gibt ("Bei einem nicht
  eindeutigen Ergebnis: KEIN API-AUFRUF").
- **Wichtiger, während der Entwicklung gefundener Bug:** Die ursprüngliche "zwei
  großgeschriebene Wörter"-Heuristik für Punkt 6 hätte in der Praxis fast **jeden** normalen
  deutschen Kanzleibrief blockiert – im Deutschen werden alle Substantive UND die
  Höflichkeitsform "Sie/Ihr" großgeschrieben, nicht nur Namen (anders als im Englischen). Ein
  Test mit einem realistischen, PII-freien Musterbrief deckte das auf. Behoben durch eine
  kuratierte Stoppwortliste häufiger Kanzlei-/Steuerrecht-Vokabeln, kombiniert mit
  wortbasiertem (statt regex-konsumierendem) Scannen, damit z. B. "Herrn Peter Müller" nicht
  durch den verbrauchten Titel "Herrn" das eigentliche Namenspaar "Peter Müller" verdeckt.
  **Ehrlich benannte Grenze:** Das bleibt eine Heuristik, keine echte NER-Erkennung – weder
  false positives noch false negatives sind ausgeschlossen. Eine zuverlässigere Lösung braucht
  ein echtes lokales Sprachmodell (siehe Ollama-Diskussion, TODO.md Schritt 4).
- **Getestet:** jeder der 7 Punkte einzeln (sauberer Fall besteht, unerlaubter Zweck blockiert,
  Rest-PII nach Pseudonymisierung blockiert, fehlender Platzhalter blockiert, unbekannter Name
  blockiert), Regressionstest gegen die gefundene Fehlalarm-Klasse, mehrere gleichzeitige
  Probleme werden alle gemeldet, Integrationstest mit echtem `Pseudonymizer`-Output.

### Schritt 3: `ClaudePrivacyGateway`-Orchestrierung (`app/privacy/gateway.py`)

- **`ClaudePrivacyGateway.prepare_request()`** ist der einzige vorgesehene Weg, aus lokalen Daten
  eine sendefertige `ClaudeRequestPayload` (Schritt-Allowlist-Schema, Vorgabe-Punkt 7) zu bauen:
  `schreibauftrag`, `gewuenschter_stil`, `anonymisierter_sachverhalt`,
  `anonymisierte_argumentationspunkte`, `anonymisierte_quellenverweise`, `schreibvorlage` – exakt
  die sechs von der Vorgabe genannten Felder, kein Freitext-Escape-Hatch für "sonstige Daten".
- **Wichtigste Design-Entscheidung:** Alle Felder werden **in einem einzigen
  Pseudonymizer-Aufruf gemeinsam** verarbeitet (über interne, kollisionsarme Trennmarkierungen
  zusammengeführt, danach wieder aufgeteilt) – nicht Feld für Feld separat. Grund: Der
  `Pseudonymizer` vergibt Platzhalter-Nummern pro Aufruf neu; bei getrennten Aufrufen hätte
  derselbe Name in zwei Feldern zwei unterschiedliche Platzhalter bekommen können. Per Test
  abgesichert, dass z. B. "Max Mustermann" im Sachverhalt UND in einem Argumentationspunkt
  denselben Platzhalter erhält.
- **Bei Blockierung (Security-Check aus Schritt 2 nicht bestanden) entsteht keine Payload** –
  `GatewayResult.payload` bleibt `None`, nur `reasons` ist gefüllt.
- **Verteidigung gegen Struktur-Injection:** Ein Text, der zufällig/absichtlich die internen
  Trennmarkierungen enthält, wird vor der Verarbeitung bereinigt (`[ENTFERNT]`) – verhindert,
  dass die Feldaufteilung durcheinandergebracht werden kann.
- **`reconstruct_response()`:** rein lokale Rückführung der Platzhalter in der (künftigen)
  Claude-Antwort.
- **Weiterer, während der Entwicklung gefundener Fehlalarm der Namens-Heuristik (Schritt 2)
  behoben:** nummerierte Argumentationspunkte ("Erster Punkt", "Zweiter Punkt" – typisch in
  Schriftsätzen) wurden fälschlich als mögliche Namen gewertet. Stoppliste um Ordnungswörter
  ergänzt.
- **Noch immer bewusst kein tatsächlicher Claude-API-Aufruf** – dieser Baustein bereitet nur vor
  und verarbeitet nach; der Versand selbst folgt erst mit `ClaudeWritingProvider` (Schritt 4).
- **Getestet:** Platzhalter-Konsistenz über Feldgrenzen hinweg (Kernanforderung), unterschiedliche
  Entitäten erhalten unterschiedliche Platzhalter, Blockierung bei unbekannter PII/unerlaubtem
  Zweck erzeugt keine Payload, exakte Rekonstruktion, korrekte Aufteilung mehrerer
  Argumente/Quellen, leere Listen korrekt behandelt, fehlende/vorhandene Vorlage, Struktur-
  Injection-Abwehr.

### Schritt 4: `LocalAIProvider`/`ClaudeWritingProvider` (`app/ai_providers/`)

- **`LocalAIProvider`-Protocol + `RuleBasedLocalAIProvider`:** bündelt bereits bestehende,
  getestete Bausteine (Document.extracted_text aus Prompt 06, Deadline aus Prompt 10,
  `search_knowledge_base` aus Prompt 11/12, Party-Rollen aus Prompt 04) zu **einer** Methode
  (`prepare_draft_context`), die direkt die von `ClaudePrivacyGateway.prepare_request`
  (Schritt 3) erwarteten Parameter liefert (Sachverhalt, Argumentationspunkte,
  Quellenverweise, bekannte Entitäten nach Kategorie). Keine neue Analyselogik – reine
  Bündelung. Party-Rollen werden tolerant zugeordnet (Gegner/Gericht/Anwalt/generisch
  Beteiligter), da `Party.role` in Prompt 04 bewusst Freitext ist. Strikte Aktenisolation wie
  überall im Projekt.
- **`ClaudeWritingProvider`-Protocol:** bewusst **ohne konkrete Implementierung**. Nimmt
  ausschließlich eine `ClaudeRequestPayload` entgegen – keine Methode für freien Text oder
  beliebige Daten. Der tatsächliche Claude-API-Aufruf bleibt der letzte, separate Schritt.
- **`DraftGenerationOrchestrator`:** verbindet `LocalAIProvider` → `ClaudePrivacyGateway` →
  `ClaudeWritingProvider` → Rekonstruktion zu einem vollständigen Ablauf – exakt das
  Pipeline-Diagramm aus der Vorgabe ("Local AI → ... → Draft Preparation → Privacy Gateway →
  ClaudeWritingProvider → Local Postprocessing"). Hängt **ausschließlich** von den drei
  Protocols ab, importiert kein konkretes SDK – per architektonischem Test abgesichert (prüft
  den Quellcode direkt auf verbotene Imports wie `anthropic`/`requests`/`httpx`).
- **Getestet:** Aggregation aus allen Quellen, Aktenisolation (identisches Muster wie
  `PromptContextBuilder`), Rollen-Zuordnung, Protocol-Form von `ClaudeWritingProvider`,
  vollständiger Orchestrator-Ablauf im Erfolgsfall (inkl. korrekter Rekonstruktion), Blockierung
  verhindert JEDEN Aufruf des Writing-Providers (weder bei unbekannter PII noch bei unerlaubtem
  Zweck wird er je erreicht), Architektur-Schutztest gegen SDK-Importe.

### Schritt 5: Privacy-sichere API-Protokollierung (`app/privacy/api_logger.py`, `app/models/api_call_log.py`)

- **`ApiCallLog`-Modell:** bewusst ein **eigenes, schlankes** Modell statt Wiederverwendung von
  `AuditEvent` – enthält ausschließlich die von der Vorgabe genannten sicheren Felder
  (`workflow_id`, `model`, `purpose`, `token_count`, `anonymized_prompt_id`, `result_status`,
  `error_status`) und **kein** generisches Freitextfeld, in dem sich Mandatsdaten verstecken
  könnten – per architektonischem Test abgesichert (`content`/`text`/`prompt`/`response`/
  `details`/`message` als Spaltennamen sind ausgeschlossen).
- **`compute_anonymized_prompt_id()`:** nicht umkehrbarer SHA-256-Hash der Payload – erlaubt
  Nachvollziehbarkeit ("war das derselbe Aufruf"), ohne den Inhalt zu speichern.
- **Wichtiger, während der Entwicklung bewusst vermiedener Fehler:** Die `reasons`-Texte aus dem
  Security-Check (Schritt 2) enthalten teils die tatsächlich erkannte PII im Klartext (z. B.
  *"Möglicherweise nicht erkannte Namen/Entitäten gefunden: ['Peter Müller']"* – der Name steht
  direkt im Grund!). Hätte man diese Gründe direkt geloggt, wäre über die Fehlerbehandlung genau
  die Information durchgesickert, die der Security-Check verhindern soll. Stattdessen übersetzt
  `categorize_block_reasons()` die Gründe **vor jeder Speicherung** in ein festes,
  inhaltsfreies Kategorie-Vokabular (`purpose_not_allowed`, `residual_pii_detected`,
  `mapping_inconsistency`, `unrecognized_entity_suspected`) – nie den Originaltext.
  `blocked_reasons` im `DraftGenerationResult` (für die Anzeige im späteren Dashboard) bleibt
  davon unberührt und weiterhin im Klartext – nur der **Log-Eintrag** ist bereinigt.
- **In `DraftGenerationOrchestrator` verankert:** jeder Aufruf (Erfolg/Blockierung/Fehler bei der
  Textproduktion) wird protokolliert. Ein Fehler im `ClaudeWritingProvider` wird abgefangen,
  protokolliert (ohne die Exception-Nachricht zu speichern – auch diese könnte Inhalte
  enthalten) und führt zu einem kontrollierten `DraftGenerationResult(success=False)` statt
  eines Absturzes.
- **Neue Konfiguration:** `CLAUDE_MODEL_NAME` (Default `claude-sonnet-5`) – nur für
  Protokollierungs-/Konfigurationszwecke, noch keine echte API-Anbindung.
- **Getestet:** Kategorisierung enthält nie den Originaltext (auch bei mehreren gleichzeitigen
  Gründen), deterministischer/kollisionsarmer Hash, alle drei Log-Pfade (Erfolg/Blockierung/
  Fehler) persistieren korrekt und ausschließlich sichere Felder, eine absichtlich Namen
  enthaltende Exception-Nachricht landet nachweislich nicht im Log, architektonischer Schutztest
  gegen Freitextfelder im Modell.

## Gesamtstatus: Privacy-by-Design/Claude-API-Boundary

**Alle 5 Schritte der vom Anwalt vorgegebenen Architekturerweiterung sind abgeschlossen, inklusive
der echten Claude-API-Anbindung** (siehe §28 am Ende dieses Dokuments für Details zur konkreten
Implementierung). Die komplette Kette (`RuleBasedLocalAIProvider` → `ClaudePrivacyGateway`
[Pseudonymisierung + Security-Check] → `AnthropicClaudeWritingProvider` → Protokollierung →
lokale Rekonstruktion) ist end-zu-Ende lauffähig und getestet.

### Noch NICHT umgesetzt (bewusst als separate, spätere Schritte)

1. ~~Security-Check~~ ✅ oben (Schritt 2, abgeschlossen)
2. ~~`ClaudePrivacyGateway`-Orchestrierung~~ ✅ oben (Schritt 3, abgeschlossen)
3. **Lokale Persistierung des Pseudonym-Mappings** (aktuell nur In-Memory-Rückgabewert) – wird
   erst benötigt, sobald tatsächlich ein API-Aufruf mit Anfrage/Antwort-Zyklus existiert
4. ~~`LocalAIProvider`/`ClaudeWritingProvider`-Schnittstellen~~ ✅ oben (Schritt 4, abgeschlossen)
5. ~~API-Protokollierung ohne personenbezogene Inhalte~~ ✅ oben (Schritt 5, abgeschlossen)
6. **Der tatsächliche Claude-API-Aufruf selbst** (verschmilzt mit Prompt 17, wartet auf
   ausdrückliche Freigabe)

Diese Reihenfolge folgt demselben Prinzip wie der gesamte bisherige Entwicklungsplan: jeder
Baustein einzeln, isoliert getestet, bevor der nächste darauf aufbaut.

### Ergänzende Vorgabe: Ollama für lokale KI-Aufgaben (empfangen, noch nicht umgesetzt)

Der Anwalt hat eine zweite Architekturvorgabe geliefert, die die "lokale KI"-Seite der Pipeline
konkretisiert: **Ollama** mit einem lokalen Open-Source-Modell soll perspektivisch die Aufgaben
übernehmen, die aktuell noch als einfache Platzhalter-Heuristiken laufen (Dokumentenverständnis,
Zusammenfassung, Informationsextraktion, Aktenzuordnung, Kanzleiwissen-Abruf,
Fristen-/Handlungsbedarf-Erkennung) – mit dem Ziel, echte inhaltliche Qualität lokal zu
erreichen, bevor überhaupt etwas an Claude geht. Genannt: Hardware-Abhängigkeit
(CPU/16 GB/32 GB/NVIDIA-GPU), Modellwahl passend zur vorhandenen Hardware.

**Einordnung:** Das betrifft in erster Linie den noch ausstehenden **Schritt 4
(`LocalAIProvider`/`ClaudeWritingProvider`)** dieser Phase sowie perspektivisch eine
Überarbeitung der bestehenden Platzhalter-Module (Prompt 08–10). Wird dort aufgegriffen, sobald
Schritt 4 ansteht – siehe TODO.md für den vollständigen Vermerk und die daraus resultierenden
offenen Entscheidungen (Hardware, Modellwahl).

## 28. Echte Claude-API-Anbindung (Stand: nach Freigabe durch den Anwalt)

Nach Abschluss aller 5 Privacy-Schritte hat der Anwalt die konkrete Umsetzung freigegeben, mit
der expliziten Vorgabe: **"Die API soll aus DSGVO-Gründen nur ohne die Übermittlung von
persönlichen Daten laufen."** Das war exakt das Ziel der gesamten vorherigen Architektur – dieser
Schritt setzt nur noch die letzte, bislang fehlende Verbindung um.

- **`AnthropicClaudeWritingProvider`** (`app/ai_providers/anthropic_writing_provider.py`): erste
  konkrete Implementierung von `ClaudeWritingProvider`, über das offizielle `anthropic`-SDK.
  **Struktureller (nicht nur konventioneller) Datenschutz:** Diese Klasse hat keinen Codepfad, der
  auf `Document`, `Matter`, `Message` oder andere Mandantendaten-Modelle zugreifen könnte – sie
  bekommt ausschließlich die bereits pseudonymisierte, durch den Security-Check geprüfte
  `ClaudeRequestPayload`. Der Datenfluss zu Mandantendaten endet bereits beim
  `ClaudePrivacyGateway` (Schritt 3), lange bevor dieser Provider überhaupt aufgerufen wird.
- **`build_writing_prompt()`:** baut den tatsächlich gesendeten Text ausschließlich aus den sechs
  Allowlist-Feldern der Payload – strukturell unmöglich, hier versehentlich weitere Daten
  einzuschleusen, da `ClaudeRequestPayload` keine weiteren Felder besitzt.
- **`WRITING_SYSTEM_PROMPT`:** weist Claude explizit an, Platzhalter wie `[MANDANT_01]`
  unverändert zu übernehmen (nicht zu "erraten" oder durch erfundene Namen zu ersetzen), keine
  Fundstellen/Fakten zu erfinden, und nur den fertigen Text ohne Meta-Kommentare zurückzugeben.
- **`ClaudeWritingProvider`-Protocol erweitert:** `write()` gibt jetzt `ClaudeWritingResult`
  (Text + optionale Token-Anzahl) statt nur `str` zurück – ermöglicht die in Schritt 5 vorgesehene
  Token-Protokollierung (`ApiCallLog.token_count`) mit echten Werten aus der API-Antwort.
- **API-Key-Handling:** wird ausschließlich zur Laufzeit aus `SecretStr.get_secret_value()`
  gelesen, nie geloggt. Per Test abgesichert, dass der Schlüssel nicht im gesendeten Prompt
  oder anderswo auftaucht.
- **Neue Konfiguration:** `CLAUDE_MAX_TOKENS` (Default 2000).
- **Getestet (ausschließlich gegen einen gemockten Anthropic-Client – kein echter API-Aufruf in
  der Sandbox, siehe unten):** Prompt-Aufbau enthält nur Allowlist-Felder, leere optionale Felder
  werden weggelassen, Token-Zählung aus der Antwort korrekt summiert, fehlende Nutzungsdaten
  führen nicht zum Absturz, API-Key erscheint nachweislich nicht im gesendeten Aufruf, leerer
  API-Key wird beim Erstellen sofort abgelehnt.
- **Wichtig – noch zu verifizieren:** Ein echter End-to-End-Test mit echtem `ANTHROPIC_API_KEY`
  konnte in dieser Sandbox nicht durchgeführt werden (kein Schlüssel vorhanden, und ein Testlauf
  gegen die echte API mit echten Kosten wäre in einer automatisierten Testsuite unpassend). Muss
  auf dem Zielsystem des Anwalts mit echtem Schlüssel final verifiziert werden.
