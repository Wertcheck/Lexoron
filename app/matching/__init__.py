"""Aktenzuordnung / Matter-Matching (Prompt 09).

Kombiniert deterministische Signale (Aktenzeichen, bekannte
E-Mail-Adressen, bekannte Beteiligte) mit einem einfachen, platzhalterhaften
Text-Ähnlichkeits-Signal (siehe Moduldocstring in matcher.py - kein
LLM/keine echten Embeddings, das bleibt konsistent mit der bisherigen
"Platzhalter zuerst"-Entscheidung und der noch offenen RAG-Layer-Frage aus
Prompt 11/12). Schwellenwerte entscheiden zwischen automatischer Zuordnung,
Vorlage zur manuellen Prüfung und "keine Zuordnung". Jede Entscheidung wird
nachvollziehbar protokolliert (AuditEvent).
"""

from app.matching.matcher import MatterMatchingService
from app.matching.schema import MatchCandidate, MatchResult
from app.matching.service import MatterAssignmentService

__all__ = [
    "MatterMatchingService",
    "MatterAssignmentService",
    "MatchCandidate",
    "MatchResult",
]
