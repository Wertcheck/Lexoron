"""Setup-Skript: importiert die lokalen Gesetzes-Fixtures (BGB-/StGB-
Auszüge, app/laws/fixtures/*.json) in die digitale Gesetzesbibliothek.

    python scripts/import_law_fixtures.py

Idempotent (Upsert nach law_code+section_number, siehe
app/laws/service.py) - beliebig oft ausführbar, z. B. nach dem Ergänzen
weiterer Fixture-Dateien. Dieselbe Import-Funktion läuft zusätzlich als
lazy Bootstrap beim ersten Aufruf von /dashboard/laws, falls die
Bibliothek noch komplett leer ist (app/web/laws_router.py) - dieses
Skript ist der explizite, empfohlene Weg, um sie auch unabhängig vom
Dashboard-Aufruf zu befüllen bzw. zu aktualisieren."""

from __future__ import annotations

from app.db.session import SessionLocal
from app.laws.service import LawFixtureError, import_all_fixtures


def main() -> int:
    db = SessionLocal()
    try:
        try:
            results = import_all_fixtures(db)
        except LawFixtureError as exc:
            print(f"FEHLER: {exc}")
            return 1

        if not results:
            print("Keine Fixture-Dateien gefunden (app/laws/fixtures/*.json).")
            return 0

        for result in results:
            status = "neu angelegt" if result.law_created else "aktualisiert"
            print(
                f"{result.law_code}: Gesetzeswerk {status}, "
                f"{result.sections_created} Paragraph(en) neu, "
                f"{result.sections_updated} aktualisiert."
            )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
