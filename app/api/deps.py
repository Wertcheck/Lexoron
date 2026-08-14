"""Gemeinsame Hilfsmittel fuer die API-Router (Prompt 21).

Bewusst minimal: nur Pagination-Parameter-Validierung und ein
einheitliches "nicht gefunden"-Verhalten. Keine Authentifizierung/
Autorisierung - siehe Hinweis in app/api/schemas.py.
"""

from __future__ import annotations

from typing import Annotated, TypeVar

from fastapi import HTTPException, Query
from sqlalchemy.orm import Session

# Bewusst begrenzt (max. 200 pro Seite): verhindert, dass ein Client durch
# einen unbeschraenkten `limit`-Wert versehentlich die gesamte Datenbank in
# einer Antwort abfragt.
LimitParam = Annotated[int, Query(ge=1, le=200)]
OffsetParam = Annotated[int, Query(ge=0)]

ModelT = TypeVar("ModelT")


def get_or_404(db: Session, model: type[ModelT], entity_id: str, label: str) -> ModelT:
    """Laedt einen Datensatz per Primaerschluessel oder wirft 404.

    `label` ist der deutsche Anzeigename fuer die Fehlermeldung (z. B.
    "Akte", "Dokument") - konsistent mit der uebrigen deutschsprachigen
    Fehlerbehandlung im Projekt.
    """
    obj = db.get(model, entity_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} nicht gefunden")
    return obj
