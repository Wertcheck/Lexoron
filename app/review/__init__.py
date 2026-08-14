"""Review-Engine (Prompt 18).

Prüft einen bereits erstellten `Draft` unabhängig auf: fehlende Fakten,
Widersprüche, unbelegte Rechtsbehauptungen, fehlende Quellen, Fristen,
Platzhalter und formale Fehler (Konzept, wörtlich). Gibt strukturierte
Findings mit Schweregrad zurück.

WICHTIGE UNABHÄNGIGKEITS-ANFORDERUNG (Konzept, wörtlich): "Die Review-
Engine soll nicht einfach den Drafting-Agent bestätigen." Umgesetzt durch:
- Eigener `ClaudeReviewProvider` (nicht derselbe Codepfad wie
  `ClaudeWritingProvider`), eigener kritischer System-Prompt.
- Der Entwurf wird wie ein GANZ NEUER Text behandelt und erneut vollständig
  durch den Privacy Gateway geschleust - der `Draft.content` enthält zu
  diesem Zeitpunkt bereits REKONSTRUIERTE, echte Mandantendaten (siehe
  app/drafting/service.py), muss also für den Review-Aufruf ERNEUT
  pseudonymisiert werden. Kein Datenpfad in diesem Modul überspringt den
  Gateway.
"""

from app.review.engine import ReviewEngine
from app.review.provider import ClaudeReviewProvider
from app.review.schema import Finding, ReviewOutcome, ReviewResult

__all__ = [
    "ReviewEngine",
    "ClaudeReviewProvider",
    "Finding",
    "ReviewResult",
    "ReviewOutcome",
]
