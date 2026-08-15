"""ApiCallLogger – protokolliert externe API-Aufrufe ohne personenbezogene
Inhalte (Architekturvorgabe Punkt 10).

WICHTIGE, während der Entwicklung bewusst vermiedene Falle: Die
`reasons`-Texte aus `SecurityCheckResult` (Schritt 2) enthalten teils die
tatsächlich erkannten, potenziell sensiblen Werte im Klartext (z. B.
"Möglicherweise nicht erkannte Namen/Entitäten gefunden: ['Peter Müller']"
- der Name selbst steht im Grund!). Würde man diese Gründe direkt in
`ApiCallLog.error_status` speichern, würde genau die Information, die der
Security-Check verhindern soll, im Log landen - ein klassischer
"Fehlerbehandlung umgeht die eigentliche Schutzmaßnahme"-Fehler.

Deshalb übersetzt `categorize_block_reasons()` die Gründe in eine feste,
inhaltsfreie Kategorie-Vokabular (siehe `_BLOCK_CATEGORIES`), BEVOR
irgendetwas geloggt wird. Nur diese Kategorien landen in der Datenbank.
"""

from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from app.models import ApiCallLog
from app.privacy.gateway_schema import ClaudeRequestPayload

# Feste, inhaltsfreie Kategorien - werden anhand von Textmustern in den
# Security-Check-Gründen erkannt, OHNE die Gründe selbst zu speichern.
_BLOCK_CATEGORIES = (
    ("Zweck", "purpose_not_allowed"),
    ("weiterhin erkennbare Muster", "residual_pii_detected"),
    ("Platzhalter", "mapping_inconsistency"),
    ("nicht erkannte Namen", "unrecognized_entity_suspected"),
)


def categorize_block_reasons(reasons: list[str]) -> str | None:
    """Übersetzt Security-Check-Gründe in inhaltsfreie Kategorie-Codes.

    Gibt NIEMALS die Original-Gründe zurück - nur eine kommagetrennte
    Liste bekannter Kategorien, oder "unknown_block_reason" falls keine
    der bekannten Kategorien zutrifft.
    """
    if not reasons:
        return None

    matched_categories: list[str] = []
    for reason in reasons:
        for pattern, category in _BLOCK_CATEGORIES:
            if pattern in reason and category not in matched_categories:
                matched_categories.append(category)

    if not matched_categories:
        return "unknown_block_reason"
    return ",".join(matched_categories)


_FRIENDLY_BLOCK_MESSAGES: dict[str, str] = {
    "purpose_not_allowed": "Der angeforderte Zweck ist nicht freigegeben.",
    "residual_pii_detected": (
        "Es wurden nach der Pseudonymisierung weiterhin erkennbare Muster gefunden."
    ),
    "mapping_inconsistency": "Interner Konsistenzfehler bei der Pseudonymisierung.",
    "unrecognized_entity_suspected": (
        "Im Text wurden möglicherweise nicht erkannte Namen/Daten gefunden."
    ),
    "unknown_block_reason": "Die Anfrage wurde aus Datenschutzgründen blockiert.",
}


def friendly_block_message(reasons: list[str]) -> str:
    """Wie `categorize_block_reasons`, aber als für den Anwalt lesbarer
    Satz statt Kategorie-Codes - WICHTIG (Security Review, Prompt 27,
    gefundene Schwachstelle): darf NIEMALS die rohen `reasons` selbst
    zurückgeben oder enthalten. Diese können laut Modul-Docstring oben
    tatsächlich erkannte, sensible Werte im Klartext enthalten (z. B.
    einen erkannten Namen). Roh angezeigt (insbesondere in einer
    Redirect-URL, siehe app/web/drafts_router.py) würden diese Werte
    sonst per Referer-Header an extern geladene Ressourcen (z. B. Google
    Fonts) durchsickern oder in Web-Server-Zugriffslogs landen - genau
    die Art Leck, die die gesamte Privacy-Gateway-Architektur verhindern
    soll. Siehe
    tests/test_security_review.py::test_blocked_reason_never_leaks_pii_into_redirect_url.
    """
    categories = categorize_block_reasons(reasons)
    if categories is None:
        return "Unbekannter Fehler."
    messages = [
        _FRIENDLY_BLOCK_MESSAGES.get(cat, "Blockiert aus Datenschutzgründen.")
        for cat in categories.split(",")
    ]
    # dedupliziert, Reihenfolge erhalten
    seen: list[str] = []
    for msg in messages:
        if msg not in seen:
            seen.append(msg)
    return " ".join(seen)


def compute_anonymized_prompt_id(payload: ClaudeRequestPayload) -> str:
    """Nicht-umkehrbarer Hash der (bereits pseudonymisierten) Payload -
    für Nachvollziehbarkeit ('war das derselbe Aufruf'), ohne den Inhalt
    zu speichern. SHA-256 ist praktisch nicht umkehrbar."""
    payload_json = json.dumps(payload.model_dump(), sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()[:16]


class ApiCallLogger:
    def log_success(
        self,
        db: Session,
        *,
        workflow_id: str | None,
        model: str,
        purpose: str,
        payload: ClaudeRequestPayload,
        token_count: int | None = None,
    ) -> ApiCallLog:
        log_entry = ApiCallLog(
            workflow_id=workflow_id,
            model=model,
            purpose=purpose,
            token_count=token_count,
            anonymized_prompt_id=compute_anonymized_prompt_id(payload),
            result_status="success",
            error_status=None,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    def log_blocked(
        self,
        db: Session,
        *,
        workflow_id: str | None,
        model: str,
        purpose: str,
        reasons: list[str],
    ) -> ApiCallLog:
        log_entry = ApiCallLog(
            workflow_id=workflow_id,
            model=model,
            purpose=purpose,
            token_count=None,
            anonymized_prompt_id=None,  # keine Payload vorhanden - wurde blockiert
            result_status="blocked",
            error_status=categorize_block_reasons(reasons),
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    def log_error(
        self,
        db: Session,
        *,
        workflow_id: str | None,
        model: str,
        purpose: str,
        payload: ClaudeRequestPayload | None = None,
    ) -> ApiCallLog:
        log_entry = ApiCallLog(
            workflow_id=workflow_id,
            model=model,
            purpose=purpose,
            token_count=None,
            anonymized_prompt_id=(
                compute_anonymized_prompt_id(payload) if payload else None
            ),
            result_status="error",
            # Bewusst KEINE Exception-Nachricht gespeichert - koennte
            # ebenfalls Inhalte enthalten (z. B. bei einem Parsing-Fehler
            # mit Textausschnitt in der Fehlermeldung).
            error_status="writing_provider_exception",
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
