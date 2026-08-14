"""ClaudePrivacyGateway – der EINZIGE erlaubte Weg Richtung Claude API
(Architekturvorgabe Punkt 3, wörtlich).

WICHTIGE DESIGN-ENTSCHEIDUNG: Alle Payload-Felder (Sachverhalt,
Argumentationspunkte, Quellenverweise, Vorlage) werden GEMEINSAM in
EINEM Pseudonymizer-Aufruf verarbeitet, nicht Feld für Feld separat.
Grund: Der Pseudonymizer vergibt Platzhalter-Nummern pro Aufruf neu
(siehe pseudonymizer.py) - würde man Felder einzeln pseudonymisieren,
könnte derselbe Name in zwei Feldern zwei unterschiedliche Platzhalter
bekommen (z. B. "Max Mustermann" im Sachverhalt als [MANDANT_01], aber
in einem Argumentationspunkt fälschlich erneut als [MANDANT_01] einer
ANDEREN Person). Durch das Zusammenführen in einen Text (mit eindeutigen,
kollisionssicheren Trennmarkierungen) VOR der Pseudonymisierung bleiben
Platzhalter über die gesamte Anfrage hinweg konsistent.

Ablauf (= der in der Vorgabe geforderte Datenfluss):
LOCAL DATA -> lokale Analyse (bereits erledigt, Ergebnis wird übergeben)
  -> ClaudePrivacyGateway.prepare_request()
      -> Zusammenführen + Pseudonymisierung
      -> SecurityCheckService (Schritt 2)
      -> bei Durchfall: GatewayResult(allowed=False), KEIN Payload
      -> bei Erfolg: GatewayResult(allowed=True, payload=...)
  -> [Schritt 4: ClaudeWritingProvider sendet NUR bei allowed=True]
  -> Claude API (noch nicht angebunden)
  -> ClaudePrivacyGateway.reconstruct_response() -> lokaler Klartext
"""

from __future__ import annotations

import re

from app.privacy.gateway_schema import ClaudeRequestPayload, GatewayResult
from app.privacy.pseudonymizer import PseudonymMapping, Pseudonymizer
from app.privacy.security_check import SecurityCheckService

# Interne, kollisionsarme Trennmarkierungen - werden NIE an Claude
# gesendet, dienen nur dem Zusammenfuehren/Aufteilen innerhalb des
# Gateways. "@@...@@" ist in normalem Kanzlei-Schriftverkehr praktisch
# nie vorhanden.
_SEP_SACHVERHALT = "@@GATEWAY_SACHVERHALT@@"
_SEP_ARGUMENTE = "@@GATEWAY_ARGUMENTE@@"
_SEP_QUELLEN = "@@GATEWAY_QUELLEN@@"
_SEP_VORLAGE = "@@GATEWAY_VORLAGE@@"
_SEP_LIST_ITEM = "@@GATEWAY_ITEM@@"

_ALL_MARKERS = (
    _SEP_SACHVERHALT,
    _SEP_ARGUMENTE,
    _SEP_QUELLEN,
    _SEP_VORLAGE,
    _SEP_LIST_ITEM,
)


def _sanitize_input(text: str) -> str:
    """Entfernt zufällige/absichtliche Vorkommen der internen
    Trennmarkierungen aus Eingabetext (Verteidigung gegen einen
    Struktur-Injection-Versuch, der die Feldaufteilung durcheinander
    bringen könnte)."""
    result = text
    for marker in _ALL_MARKERS:
        result = result.replace(marker, "[ENTFERNT]")
    return result


class ClaudePrivacyGateway:
    def __init__(
        self,
        pseudonymizer: Pseudonymizer | None = None,
        security_check: SecurityCheckService | None = None,
    ) -> None:
        self.pseudonymizer = pseudonymizer or Pseudonymizer()
        self.security_check = security_check or SecurityCheckService()

    def prepare_request(
        self,
        *,
        purpose: str,
        sachverhalt: str,
        argumentationspunkte: list[str] | None = None,
        quellenverweise: list[str] | None = None,
        stil: str | None = None,
        vorlage: str | None = None,
        known_entities: dict[str, list[str]] | None = None,
    ) -> GatewayResult:
        """Baut eine sendefertige, pseudonymisierte Payload - oder
        blockiert (siehe GatewayResult.allowed). Ruft selbst KEINE Claude
        API auf (das übernimmt erst Schritt 4)."""
        argumentationspunkte = argumentationspunkte or []
        quellenverweise = quellenverweise or []

        combined = self._build_combined_text(
            sachverhalt, argumentationspunkte, quellenverweise, vorlage
        )

        pseudonymized_combined, mappings = self.pseudonymizer.pseudonymize(
            combined, known_entities=known_entities
        )

        check_result = self.security_check.check(
            pseudonymized_combined, mappings, purpose=purpose
        )
        if not check_result.passed:
            return GatewayResult(
                allowed=False,
                purpose=purpose,
                payload=None,
                mappings=mappings,
                reasons=check_result.reasons,
            )

        (
            pseudo_sachverhalt,
            pseudo_argumente,
            pseudo_quellen,
            pseudo_vorlage,
        ) = self._split_combined_text(pseudonymized_combined)

        payload = ClaudeRequestPayload(
            schreibauftrag=purpose,
            gewuenschter_stil=stil,
            anonymisierter_sachverhalt=pseudo_sachverhalt,
            anonymisierte_argumentationspunkte=pseudo_argumente,
            anonymisierte_quellenverweise=pseudo_quellen,
            schreibvorlage=pseudo_vorlage,
        )

        return GatewayResult(
            allowed=True, purpose=purpose, payload=payload, mappings=mappings, reasons=[]
        )

    def reconstruct_response(
        self, claude_response_text: str, mappings: list[PseudonymMapping]
    ) -> str:
        """Lokale Rückführung: Platzhalter im Claude-Antworttext werden
        durch die Originalwerte ersetzt. Rein lokal, kein Netzwerkzugriff."""
        return self.pseudonymizer.reconstruct(claude_response_text, mappings)

    @staticmethod
    def _build_combined_text(
        sachverhalt: str,
        argumentationspunkte: list[str],
        quellenverweise: list[str],
        vorlage: str | None,
    ) -> str:
        clean_sachverhalt = _sanitize_input(sachverhalt)
        clean_argumente = [_sanitize_input(a) for a in argumentationspunkte]
        clean_quellen = [_sanitize_input(q) for q in quellenverweise]
        clean_vorlage = _sanitize_input(vorlage) if vorlage else ""

        parts = [
            _SEP_SACHVERHALT,
            clean_sachverhalt,
            _SEP_ARGUMENTE,
            _SEP_LIST_ITEM.join(clean_argumente),
            _SEP_QUELLEN,
            _SEP_LIST_ITEM.join(clean_quellen),
            _SEP_VORLAGE,
            clean_vorlage,
        ]
        return "\n".join(parts)

    @staticmethod
    def _split_combined_text(
        combined: str,
    ) -> tuple[str, list[str], list[str], str | None]:
        pattern = re.compile(
            rf"{re.escape(_SEP_SACHVERHALT)}\n(.*?)\n{re.escape(_SEP_ARGUMENTE)}\n"
            rf"(.*?)\n{re.escape(_SEP_QUELLEN)}\n(.*?)\n{re.escape(_SEP_VORLAGE)}\n(.*)",
            re.DOTALL,
        )
        match = pattern.match(combined)
        if not match:
            raise ValueError(
                "Interner Fehler: pseudonymisierter Text konnte nicht in "
                "Felder zurückgeteilt werden - Trennmarkierungen wurden "
                "möglicherweise durch die Pseudonymisierung verändert."
            )

        sachverhalt_text, argumente_text, quellen_text, vorlage_text = match.groups()

        argumente = (
            argumente_text.split(_SEP_LIST_ITEM) if argumente_text else []
        )
        quellen = quellen_text.split(_SEP_LIST_ITEM) if quellen_text else []
        vorlage = vorlage_text if vorlage_text else None

        return sachverhalt_text, argumente, quellen, vorlage
