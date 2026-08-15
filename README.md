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

Vor dem ersten Start (einmalig) den initialen Admin-Nutzer anlegen:

```bash
alembic upgrade head
ADMIN_EMAIL=admin@example.test python scripts/create_admin.py
```

Ohne `ADMIN_INITIAL_PASSWORD` wird ein sicheres Zufallspasswort erzeugt und einmalig auf der
Konsole angezeigt - notieren, es wird nicht erneut angezeigt. Beim ersten Login wird eine
Passwortänderung erzwungen.

```bash
uvicorn app.main:app --reload
```

Danach ist ein Health-Check unter `GET /health` erreichbar (ohne Login), die JSON-API unter
`/api/...` (Login erforderlich, siehe `/docs` fuer die interaktive OpenAPI-Dokumentation) und
das Dashboard unter `GET /dashboard` - startet mit `/dashboard/login`.

## Tests

```bash
pytest
```

## Wichtige Grundregeln

- Keine echten Mandantendaten in Entwicklung oder Tests.
- Keine Secrets im Repository (`.env` ist in `.gitignore`).
- Kein automatischer E-Mail-Versand, keine autonome rechtliche Entscheidung.

Details siehe `CLAUDE.md`.
