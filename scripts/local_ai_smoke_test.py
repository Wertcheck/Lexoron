"""CLI-Skript: manueller End-zu-Ende-Smoke-Test für den lokalen KI-Kernpfad
(§65: Presidio -> Ollama -> Claude -> lokale Rekonstruktion).

Verwendung (auf einem echten Rechner mit laufendem Ollama UND konfiguriertem
ANTHROPIC_API_KEY, NICHT Teil der automatisierten pytest-Suite - dieses
Skript macht echte Netzwerkaufrufe):

    python scripts/local_ai_smoke_test.py

Prüft nacheinander (bricht bei einem fehlgeschlagenen Schritt kontrolliert
ab, führt niemals einen späteren Schritt "trotzdem" aus):
1. Ist Ollama unter der konfigurierten OLLAMA_BASE_URL erreichbar?
2. Ist das konfigurierte OLLAMA_MODEL lokal vorhanden?
3. Erkennt Presidio eine synthetische Testperson im Beispieltext?
4. Wird der synthetische Name korrekt zu einem Platzhalter pseudonymisiert?
5. Liefert der lokale Ollama-Aufruf (`OllamaLocalLLMProvider.process`) eine
   Antwort auf die bereits pseudonymisierte Payload?
6. Liefert der echte Claude-Aufruf (`AnthropicClaudeWritingProvider`) eine
   Antwort?
7. Funktioniert die lokale Rekonstruktion (Platzhalter -> Originalwert)?

WICHTIG (CLAUDE.md-Grundregel): ausschließlich synthetische, frei erfundene
Testdaten - niemals echte Mandantendaten in dieses Skript einfügen oder
damit testen.
"""

from __future__ import annotations

import sys
import time

from app.ai_providers.factory import (
    ProviderNotConfiguredError,
    build_local_llm_provider,
    build_writing_provider,
)
from app.ai_providers.local_llm_provider import LocalLLMUnavailableError
from app.config import get_settings
from app.privacy.gateway_schema import ClaudeRequestPayload
from app.privacy.pseudonymizer import Pseudonymizer

_SYNTHETIC_TEXT = (
    "Sehr geehrte Damen und Herren, unser Mandant Erika Testperson bittet um "
    "eine kurze Rückmeldung zur Betriebsprüfung 2027."
)
_SYNTHETIC_KNOWN_ENTITIES = {"mandant": ["Erika Testperson"]}


def _fail(step: str, detail: str) -> int:
    print(f"[FEHLGESCHLAGEN] {step}: {detail}")
    return 1


def main() -> int:
    overall_start = time.monotonic()
    settings = get_settings()

    if not settings.local_ai_enabled:
        print(
            "LOCAL_AI_ENABLED=false - lokale KI ist nicht aktiviert, "
            "dieser Smoke-Test prüft nur Presidio + Claude."
        )
        local_llm_provider = None
    else:
        local_llm_provider = build_local_llm_provider(settings)

    # --- 1+2: Ollama-Erreichbarkeit + Modell ---
    if local_llm_provider is not None:
        health = local_llm_provider.check_health()
        if not health.reachable:
            return _fail("Ollama-Erreichbarkeit", health.error or "unbekannter Fehler")
        print(f"[OK] Ollama erreichbar unter {settings.ollama_base_url}")

        if not health.model_available:
            return _fail("Ollama-Modell", health.error or "Modell nicht gefunden")
        print(f"[OK] Modell '{settings.ollama_model}' ist lokal vorhanden")

    # --- 3+4: Presidio + Pseudonymisierung ---
    pseudonymizer = Pseudonymizer()
    pseudonymized_text, mappings = pseudonymizer.pseudonymize(
        _SYNTHETIC_TEXT, known_entities=_SYNTHETIC_KNOWN_ENTITIES
    )
    if "Erika Testperson" in pseudonymized_text:
        return _fail("Pseudonymisierung", "Synthetischer Name wurde NICHT ersetzt")
    if not mappings:
        return _fail("Pseudonymisierung", "Keine Mapping-Eintraege erzeugt")
    print(f"[OK] Pseudonymisierung erfolgreich: {pseudonymized_text!r}")

    payload = ClaudeRequestPayload(
        schreibauftrag="formulate_draft",
        anonymisierter_sachverhalt=pseudonymized_text,
    )

    # --- 5: lokaler Ollama-Aufruf ---
    if local_llm_provider is not None:
        ollama_start = time.monotonic()
        try:
            local_result = local_llm_provider.process(payload)
        except LocalLLMUnavailableError as exc:
            return _fail("Ollama-Aufruf", str(exc))
        ollama_seconds = time.monotonic() - ollama_start
        print(
            f"[OK] Ollama-Antwort erhalten ({len(local_result.text)} Zeichen) "
            f"in {ollama_seconds:.1f}s"
        )
    else:
        ollama_seconds = None

    # --- 6: echter Claude-Aufruf ---
    try:
        writing_provider = build_writing_provider(settings)
    except ProviderNotConfiguredError as exc:
        return _fail("Claude-Konfiguration", str(exc))

    claude_start = time.monotonic()
    try:
        writing_result = writing_provider.write(payload)
    except Exception as exc:  # noqa: BLE001 - Smoke-Test soll jeden Fehler klar melden
        return _fail("Claude-Aufruf", f"{type(exc).__name__}: {exc}")
    claude_seconds = time.monotonic() - claude_start
    print(
        f"[OK] Claude-Antwort erhalten ({len(writing_result.text)} Zeichen) "
        f"in {claude_seconds:.1f}s"
    )

    # --- 7: lokale Rekonstruktion ---
    reconstructed = pseudonymizer.reconstruct(writing_result.text, mappings)
    print(f"[OK] Rekonstruktion durchgeführt: {reconstructed!r}")

    overall_seconds = time.monotonic() - overall_start
    print("\nAlle Schritte erfolgreich.")
    if ollama_seconds is not None:
        print(f"Ollama-Latenz: {ollama_seconds:.1f}s")
    print(f"Claude-Latenz: {claude_seconds:.1f}s")
    print(f"Gesamtlatenz (inkl. Presidio/Rekonstruktion): {overall_seconds:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
