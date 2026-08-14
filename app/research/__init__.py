"""Legal-Research-Workflow (Prompt 15).

Erzeugt aus einem Fallkontext (`Matter`) Suchfragen, fragt ausschließlich
freigegebene Rechtsquellen (`Source`, Prompt 14) über die Suchschicht
(Prompt 11) ab und liefert Ergebnisse MIT Quellenbelegen zurück - nie nur
einen rohen Text-Schnipsel ohne Herkunft.

WICHTIGSTE REGELN (Konzept Prompt 15, wörtlich):
- "Wenn keine ausreichende Quelle gefunden wird, muss das System 'nicht
  ausreichend belegt' melden." -> `LegalResearchResult.sufficiently_supported`
  plus expliziter Text in `reasoning`, niemals stillschweigend leer.
- "Niemals Fundstellen erfinden." -> jeder `LegalResearchFinding` verweist
  auf eine tatsächlich existierende `Source`-Zeile in der Datenbank: kein
  Ergebnis wird je aus einem Text generiert.

Bewusst noch ohne LLM (Konsistenz mit Prompt 08/09/10): Die
"Suchfragen-Erzeugung" ist eine einfache, deterministische Ableitung aus
Aktenmetadaten (Titel, Fachgebiet), keine KI-generierte Query-Formulierung.
"""

from app.research.schema import LegalResearchFinding, LegalResearchResult
from app.research.service import LegalResearchService

__all__ = ["LegalResearchFinding", "LegalResearchResult", "LegalResearchService"]
