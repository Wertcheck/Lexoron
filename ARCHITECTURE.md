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

## 10. Offene Entscheidungen (bitte vor Prompt 02 bestätigen oder auswählen)

1. **Python-Version:** 3.12 (verfügbar) beibehalten oder auf 3.13.x wechseln?
2. **OCR-Engine:** z. B. Tesseract (lokal, kostenlos) vs. Cloud-OCR-Dienst? Datenschutzaspekt
   spricht für lokal.
3. **Mail-Provider zuerst:** IMAP (generisch, viele Anbieter) oder Microsoft Graph (falls
   Kanzlei M365 nutzt)?
4. **Such-/RAG-Layer:** einfache Volltextsuche (z. B. SQLite FTS5) zum Start, oder direkt ein
   Vektorspeicher (z. B. pgvector/Chroma)? Empfehlung: FTS5 zuerst, Vektor später ergänzen, um
   Komplexität am Anfang gering zu halten.
5. **Zielumgebung:** Entwicklungsrechner (macOS/Linux) oder von Anfang an Windows-Kanzlei-PC als
   Referenzumgebung für Installer-Tests?
6. **Datenbank Prototyp:** SQLite ausreichend für die ersten Phasen, oder direkt PostgreSQL
   aufsetzen (mehr Setup-Aufwand, aber näher an Produktivumgebung)?

## 11. Nächster Schritt

Nach Bestätigung/Auswahl der offenen Punkte 1–6: **Prompt 02 – Repository-Grundgerüst**
(minimales Python-Projektgerüst, `pyproject.toml`, `.env.example`, `README.md`, `CLAUDE.md`,
Teststruktur, lokaler Smoke-Test). Es werden dabei weiterhin keine KI-Logik und keine echten
Mandantendaten eingeführt.
