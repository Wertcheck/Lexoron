"""Strukturelle PII-Schutzwache für Logging-Aufrufe (Prompt 32).

Ergänzt die bisherigen, punktuellen Funde (Security Review Prompt 27,
Fehler-/Retry-System Prompt 31) um eine dauerhafte, automatisierte
Regressionsprüfung: durchsucht JEDEN `logger.*`-Aufruf im gesamten
`app/`-Quellcode nach Variablennamen, die typischerweise Mandanten-/
Dokumentinhalte tragen (z. B. `body_text`, `extracted_text`, `sachverhalt`,
`content`). Ein neuer Logging-Aufruf, der versehentlich einen dieser
Namen direkt interpoliert, lässt diesen Test fehlschlagen - BEVOR er in
Produktion Schaden anrichten kann.

WICHTIG, ehrlich benannt: das ist eine HEURISTIK (Namensmuster-Suche im
Quellcode), kein Laufzeit-Schutz und keine Garantie gegen JEDE Form von
PII-Leck (z. B. ein Fehlertext, der zufällig einen Namen enthält, wie in
Prompt 31 gefunden, wird dadurch NICHT erkannt - das erfordert weiterhin
sorgfältiges Code-Review). Sie fängt aber den häufigsten, am leichtesten
vermeidbaren Fehler ab: direktes Loggen einer bekannt-riskanten Variable.
"""

from __future__ import annotations

import re
from pathlib import Path

_FORBIDDEN_VARIABLE_NAMES = (
    "body_text",
    "extracted_text",
    "sachverhalt",
    "content",
    "instruction_text",
    "message_body",
    "draft_content",
    "document_text",
)

_LOGGER_CALL_RE = re.compile(
    r"logger\.(debug|info|warning|error|exception|critical)\((.*?)\)", re.DOTALL
)


def _iter_python_files() -> list[Path]:
    app_dir = Path(__file__).resolve().parent.parent / "app"
    return [p for p in app_dir.rglob("*.py") if "__pycache__" not in p.parts]


def test_no_logging_call_interpolates_known_sensitive_variable_names() -> None:
    violations: list[str] = []
    for path in _iter_python_files():
        source = path.read_text(encoding="utf-8")
        for match in _LOGGER_CALL_RE.finditer(source):
            call_body = match.group(2)
            for forbidden in _FORBIDDEN_VARIABLE_NAMES:
                if re.search(rf"\b{re.escape(forbidden)}\b", call_body):
                    line_number = source[: match.start()].count("\n") + 1
                    violations.append(f"{path}:{line_number} nutzt '{forbidden}'")

    assert not violations, (
        "Potenziell PII-haltige Variable(n) direkt in einem Logging-Aufruf "
        "gefunden:\n" + "\n".join(violations)
    )


def test_logging_module_documents_the_no_pii_rule() -> None:
    import app.observability.logging_config as module

    assert "personenbezogene" in module.__doc__ or "PII" in module.__doc__


def test_all_current_logger_calls_use_only_safe_identifiers() -> None:
    """Ergänzender, positiver Test: bestätigt, dass tatsächlich Logging-
    Aufrufe im Projekt existieren (verhindert, dass der obige Test durch
    eine versehentlich leere Suche stillschweigend immer gruen waere)."""
    total_calls = 0
    for path in _iter_python_files():
        source = path.read_text(encoding="utf-8")
        total_calls += len(_LOGGER_CALL_RE.findall(source))
    assert total_calls > 0
