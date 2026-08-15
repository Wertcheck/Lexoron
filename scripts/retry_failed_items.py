"""CLI-Skript: wiederholt fällige, zuvor fehlgeschlagene Pipeline-Schritte
(Prompt 31).

Verwendung (z. B. per Windows-Aufgabenplanung alle 15 Minuten aufgerufen -
es gibt bewusst KEINEN eingebauten Scheduler/Hintergrunddienst, konsistent
mit der Ein-Prozess-Architektur des Projekts):

    python scripts/retry_failed_items.py

Wiederholt aktuell:
- OCR-Fehlschläge (`operation="ocr"`)
- Intake-Fehlschläge (`operation="intake"`)

Nutzt `RetryService.execute_retry` - DIESELBE Dispatch-Logik wie die
manuelle "Erneut versuchen"-Aktion im Dashboard (app/web/errors_router.py),
damit beide Wege garantiert dasselbe Verhalten haben. Respektiert das
Backoff-Zeitfenster (`ProcessingError.next_retry_at`) - ein Aufruf, bevor
die Wartezeit abgelaufen ist, wiederholt nichts.
"""

from __future__ import annotations

from app.db.session import SessionLocal
from app.errors import RetryService


def main() -> int:
    db = SessionLocal()
    retry_service = RetryService()

    try:
        due = retry_service.list_due_for_retry(db)
        if not due:
            print("Keine fälligen Wiederholungen.")
            return 0

        print(f"{len(due)} fällige Wiederholung(en) gefunden.")
        succeeded = 0
        still_failing = 0

        for error in due:
            try:
                success = retry_service.execute_retry(db, error)
            except ValueError as exc:
                print(f"  {error.operation} ({error.entity_id}): {exc}")
                continue
            if success:
                print(f"  [{error.operation}] {error.entity_id}: erfolgreich.")
                succeeded += 1
            else:
                print(
                    f"  [{error.operation}] {error.entity_id}: weiterhin fehlgeschlagen "
                    f"(Versuch {error.attempt_count}/{error.max_attempts})."
                )
                still_failing += 1

        print(f"Fertig: {succeeded} erfolgreich, {still_failing} weiterhin fehlgeschlagen.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
