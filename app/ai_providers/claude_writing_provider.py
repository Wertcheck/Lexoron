"""ClaudeWritingProvider – Protocol für externe sprachliche Textproduktion.

Das Protocol existiert, damit der Workflow (`DraftGenerationOrchestrator`)
ausschließlich von dieser Abstraktion abhängt, NIEMALS von einem
konkreten SDK (Architekturvorgabe Punkt 11, wörtlich: "Der Workflow darf
nicht direkt von Claude abhängig sein"). `AnthropicClaudeWritingProvider`
(siehe unten) ist die erste konkrete Implementierung.

Nimmt bewusst NUR eine `ClaudeRequestPayload` entgegen (das
Allowlist-Schema aus Schritt 3) - es gibt keine Methode, die freien Text
oder beliebige Datenstrukturen an ein externes Modell schicken könnte.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.privacy.gateway_schema import ClaudeRequestPayload

# System-Anweisung für die Textproduktions-Schicht selbst. Bewusst
# getrennt von den lokalen SYSTEM_RULES aus app/promptlayer/builder.py
# (Prompt 16) - jene betreffen den lokal aufgebauten Kontext, diese hier
# die tatsächlich an Claude gesendete Anweisung.
WRITING_SYSTEM_PROMPT = """\
Du hilfst bei der sprachlichen Formulierung eines Antwortschreibens für \
eine Steueranwaltskanzlei.

Verbindliche Regeln:
- Der Text, den du erhältst, ist bereits anonymisiert (Platzhalter wie \
[MANDANT_01], [AKTENZEICHEN_01], [IBAN_01] usw.). Verwende diese \
Platzhalter unverändert in deiner Antwort - ersetze sie NICHT durch \
Namen oder Daten, die du dir ausdenkst, und erfinde keine neuen \
Platzhalter.
- Erfinde keine Fundstellen, Paragraphen, Zitate oder Fakten, die nicht \
im Sachverhalt oder den Quellenverweisen stehen. Fehlt ein Beleg, \
markiere die Aussage als offenen Prüfpunkt statt sie zu erfinden.
- Formuliere einen professionellen, sachlichen Kanzleistil.
- Triff keine rechtliche Entscheidung - du erstellst einen Entwurf zur \
Prüfung durch den Anwalt.
- Gib ausschließlich den fertigen Schreibtext zurück, keine Erklärungen \
oder Meta-Kommentare.
"""


@dataclass
class ClaudeWritingResult:
    text: str
    # "sofern verfügbar" (Architekturvorgabe Punkt 10) - None, falls die
    # konkrete Implementierung keine Token-Zählung liefert.
    token_count: int | None = None


class ClaudeWritingProvider(Protocol):
    def write(self, payload: ClaudeRequestPayload) -> ClaudeWritingResult:
        """Sendet AUSSCHLIESSLICH die bereits pseudonymisierte,
        Allowlist-geprüfte Payload und gibt den (weiterhin
        pseudonymisierten) Antworttext zurück. Die lokale Rekonstruktion
        übernimmt der Aufrufer (siehe
        `ClaudePrivacyGateway.reconstruct_response`)."""
        ...


def build_writing_prompt(payload: ClaudeRequestPayload) -> str:
    """Baut den an Claude gesendeten Text AUSSCHLIESSLICH aus den sechs
    Allowlist-Feldern - structurell unmöglich, hier versehentlich weitere
    Daten (z. B. rohe Aktendaten) einzuschleusen, da `ClaudeRequestPayload`
    keine weiteren Felder besitzt."""
    parts = [f"Schreibauftrag: {payload.schreibauftrag}"]
    if payload.gewuenschter_stil:
        parts.append(f"Gewünschter Stil: {payload.gewuenschter_stil}")
    parts.append(f"Sachverhalt:\n{payload.anonymisierter_sachverhalt}")
    if payload.anonymisierte_argumentationspunkte:
        punkte = "\n".join(
            f"- {punkt}" for punkt in payload.anonymisierte_argumentationspunkte
        )
        parts.append(f"Argumentationspunkte:\n{punkte}")
    if payload.anonymisierte_quellenverweise:
        quellen = "\n".join(
            f"- {quelle}" for quelle in payload.anonymisierte_quellenverweise
        )
        parts.append(f"Quellenverweise:\n{quellen}")
    if payload.schreibvorlage:
        parts.append(f"Vorlage/Beispielstil:\n{payload.schreibvorlage}")
    return "\n\n".join(parts)
