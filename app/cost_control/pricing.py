"""Preisschätzung für Claude-API-Aufrufe (Prompt 33).

WICHTIG, ehrlich benannt: dies ist eine SCHÄTZUNG auf Basis öffentlich
bekannter Preislisten (Stand Wissensstand, siehe `_PRICING_USD_PER_MILLION`
unten) - keine exakte Abrechnung. Die tatsächliche Abrechnung erfolgt
ausschließlich durch Anthropic selbst; diese Schätzung dient der
internen Kostenkontrolle/Budgetwarnung, nicht als Ersatz für die echte
Rechnung. Preise ändern sich gelegentlich - `_PRICING_USD_PER_MILLION`
ist bewusst an einer einzigen, leicht auffindbaren Stelle zentralisiert,
um zukünftige Aktualisierungen einfach zu halten.

`ApiCallLog.token_count` (Prompt 21) speichert nur die GESAMTZAHL
(Input+Output kombiniert), da `ClaudeWritingResult`/`ReviewResult` diese
Aufteilung bislang nicht getrennt führten. Für eine genauere Schätzung
wird - wo verfügbar - `input_tokens`/`output_tokens` getrennt genutzt
(Prompt 33 ergänzt diese optionalen Felder); ist nur die Gesamtzahl
bekannt (ältere Einträge, oder ein Provider ohne Aufteilung), wird ein
geschätztes Eingabe/Ausgabe-Verhältnis (siehe `_DEFAULT_INPUT_OUTPUT_SPLIT`)
angenommen - weniger genau, aber besser als keine Schätzung.
"""

from __future__ import annotations

from dataclasses import dataclass

_PRICING_USD_PER_MILLION: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (3.0, 15.0),
    "claude-opus-4-8": (15.0, 75.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
    "claude-fable-5": (3.0, 15.0),
    "claude-mythos-5": (3.0, 15.0),
}
_DEFAULT_PRICING = (15.0, 75.0)  # konservativ: Opus-Niveau, falls Modell unbekannt

_DEFAULT_INPUT_OUTPUT_SPLIT = (0.75, 0.25)


@dataclass(frozen=True)
class CostEstimate:
    usd: float
    is_exact_split: bool  # True, wenn input_tokens/output_tokens vorlagen


def _pricing_for_model(model: str) -> tuple[float, float]:
    return _PRICING_USD_PER_MILLION.get(model, _DEFAULT_PRICING)


def estimate_cost_usd(
    model: str,
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
) -> CostEstimate | None:
    """Schätzt die Kosten eines einzelnen API-Aufrufs in USD.

    Bevorzugt `input_tokens`/`output_tokens` (genau), fällt auf
    `total_tokens` mit einer angenommenen Aufteilung zurück (ungenau,
    aber besser als nichts). Gibt `None` zurück, wenn gar keine
    Token-Information vorliegt (z. B. ein blockierter oder fehlgeschlagener
    Aufruf, der nie tatsächlich Tokens verbraucht hat)."""
    input_price, output_price = _pricing_for_model(model)

    if input_tokens is not None and output_tokens is not None:
        usd = (input_tokens / 1_000_000) * input_price + (
            output_tokens / 1_000_000
        ) * output_price
        return CostEstimate(usd=usd, is_exact_split=True)

    if total_tokens is not None:
        input_share, output_share = _DEFAULT_INPUT_OUTPUT_SPLIT
        estimated_input = total_tokens * input_share
        estimated_output = total_tokens * output_share
        usd = (estimated_input / 1_000_000) * input_price + (
            estimated_output / 1_000_000
        ) * output_price
        return CostEstimate(usd=usd, is_exact_split=False)

    return None
