"""App-Einstiegspunkt (Prompt 02 – Repository-Grundgeruest).

Enthaelt bewusst nur ein Minimalgeruest mit einem Health-Check-Endpunkt.
Keine Konfiguration, kein Datenmodell, keine Ingestion, keine KI-Logik,
keine Mandanten-/Aktenlogik. Diese werden in den dafuer vorgesehenen
spaeteren Prompts (03 ff., siehe TODO.md) hinzugefuegt.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Kanzlei-AI-Pipeline",
    description=(
        "Konfigurierbare KI-gestuetzte Workflow-Plattform fuer eine "
        "Anwaltskanzlei (frueher Entwicklungsstand)."
    ),
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Einfacher Smoke-Test-Endpunkt: bestaetigt nur, dass die App laeuft."""
    return {"status": "ok"}
