"""Rechtsquellen-Modul (Prompt 14).

`SourceProvider`-Abstraktion (Protocol, analog zu `MailProvider`/
`DocumentClassifier`) erlaubt mehrere Provider, wie im Konzept gefordert
("Die Architektur muss mehrere Provider erlauben"). Aktuell einziger
implementierter Provider: `ManualSourceProvider` - der Anwalt trägt Daten
selbst ein und bestätigt sie damit implizit. Automatisierte Provider
(Anbindung an juristische Datenbanken/Portale) sind bewusst NICHT Teil
dieses Prompts - das Konzept selbst hält fest, dass vor produktivem
Einsatz erst geklärt werden muss, welche Datenbanken/Portale die Kanzlei
nutzen darf (Lizenzen, API-Zugänge).

WICHTIGSTE REGEL (Konzept §6, wörtlich): "Die KI darf keine Quelle
erfinden." Deshalb entstehen `Source`-Einträge ausschließlich über
manuelle Eingabe (`SourceService.import_source`), nie automatisch/generiert.
"""

from app.sources.provider import ManualSourceProvider, SourceProvider
from app.sources.schema import SourceImport
from app.sources.service import SourceService

__all__ = [
    "SourceProvider",
    "ManualSourceProvider",
    "SourceImport",
    "SourceService",
]
