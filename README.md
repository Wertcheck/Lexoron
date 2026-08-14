# Kanzlei-AI-Pipeline (Prototyp)

Konfigurierbare KI-gestützte Workflow-Plattform für eine Anwaltskanzlei. Siehe
`ARCHITECTURE.md` für die Zielarchitektur und `TODO.md` für den Entwicklungsplan
(Prompts 01–45). Verbindliche Projektregeln stehen in `CLAUDE.md`.

**Status:** frühe Entwicklungsphase (Prompt 02 – Repository-Grundgerüst). Es ist noch keine
Fachlogik (Aktenzuordnung, OCR, Mail, Rechtsquellen, KI-Entwürfe) enthalten.

## Voraussetzungen

- Python 3.13.x (Zielversion laut `CLAUDE.md`). Falls in der jeweiligen Umgebung nicht
  verfügbar, siehe Hinweis in `ARCHITECTURE.md` §10.

## Setup (lokal)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Starten

```bash
uvicorn app.main:app --reload
```

Danach ist ein Health-Check unter `GET /health` erreichbar, die JSON-API unter `/api/...`
(siehe `/docs` fuer die interaktive OpenAPI-Dokumentation) und das Dashboard unter
`GET /dashboard` (aktuell nur der Posteingang, `/dashboard/inbox`).

## Tests

```bash
pytest
```

## Wichtige Grundregeln

- Keine echten Mandantendaten in Entwicklung oder Tests.
- Keine Secrets im Repository (`.env` ist in `.gitignore`).
- Kein automatischer E-Mail-Versand, keine autonome rechtliche Entscheidung.

Details siehe `CLAUDE.md`.
