"""ApiCallLog – Protokoll externer API-Aufrufe (Architekturvorgabe Punkt 10).

WICHTIG: Bewusst ein EIGENES, schlankes Modell statt Wiederverwendung von
`AuditEvent` - `AuditEvent.details` ist ein generisches Freitextfeld, das
anderswo im Projekt bewusst kurze Kontextinformationen aufnimmt, aber
keine strukturelle Garantie gegen personenbezogene Inhalte bietet. Dieses
Modell hat ABSICHTLICH nur die von der Vorgabe genannten, sicheren Felder
- kein Freitextfeld, in dem sich Mandatsdaten verstecken könnten.

Append-only wie `AuditEvent`: nur `created_at`, kein `updated_at`.

NIEMALS in diesem Modell gespeichert (Vorgabe, wörtlich): vollständige
Prompts mit Mandantendaten, vollständige Claude-Antworten mit
personenbezogenen Daten, API-Keys, vollständige Akteninhalte.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApiCallLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "api_call_logs"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    # Bezug zum Vorgang (z. B. matter_id) - KEINE Mandantendaten, nur eine ID.
    workflow_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Prompt 33: getrennte Input-/Output-Zaehlung, wo verfuegbar - erlaubt
    # eine genauere Kostenschaetzung als die reine Gesamtzahl (siehe
    # app/cost_control/pricing.py). Nullable, da nicht jeder Provider/
    # jeder aeltere Log-Eintrag diese Aufteilung kennt.
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Zum Zeitpunkt des Log-Eintrags geschaetzte Kosten in USD (siehe
    # app/cost_control/pricing.py) - bewusst zum Schreibzeitpunkt berechnet
    # und gespeichert (nicht bei jeder Abfrage neu berechnet), damit sich
    # eine spaetere Preislisten-Aktualisierung nicht rueckwirkend auf
    # bereits geloggte, historische Auftraege auswirkt.
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Nicht-umkehrbarer Hash der Payload - erlaubt Nachvollziehbarkeit
    # ("war das derselbe Aufruf wie in Log X"), ohne den Inhalt zu speichern.
    anonymized_prompt_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # success / blocked / error
    result_status: Mapped[str] = mapped_column(String(32), nullable=False)
    # NUR feste, inhaltsfreie Kategorie-Codes (siehe app/privacy/api_logger.py)
    # - NIEMALS die tatsaechlichen Security-Check-Gruende im Klartext, da
    # diese potenziell die erkannte PII selbst enthalten koennten.
    error_status: Mapped[str | None] = mapped_column(String(128), nullable=True)
