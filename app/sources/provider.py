"""SourceProvider – Protocol + einzige aktuelle Implementierung (manuell).

Erlaubt laut Konzept "mehrere Provider" - die Abstraktion ist bewusst so
gehalten, dass ein späterer automatisierter Provider (z. B. Anbindung an
eine juristische Datenbank) `SourceProvider` implementieren kann, ohne
`SourceService` zu ändern. Ein solcher Provider ist aktuell NICHT gebaut -
das erfordert erst eine Geschäftsentscheidung (Lizenzen/API-Zugänge, siehe
Konzept §6), die noch nicht getroffen wurde.

`ManualSourceProvider.resolve()` reichert NICHTS automatisch an - er gibt
exakt das zurück, was der Anwalt eingegeben hat. Das ist bewusst so:
"Die KI darf keine Quelle erfinden" gilt auch für Provider - ein Provider
darf nur bestätigen/anreichern, was er tatsächlich verifizieren konnte,
nie Werte erfinden.
"""

from __future__ import annotations

from typing import Protocol

from app.sources.schema import SourceImport


class SourceProvider(Protocol):
    name: str

    def resolve(self, data: SourceImport) -> SourceImport:
        """Nimmt Quellendaten entgegen und gibt sie zurück - ggf.
        angereichert/validiert, falls der Provider das leisten kann.
        Darf NIEMALS Werte erfinden, die nicht tatsächlich verifiziert
        wurden."""
        ...


class ManualSourceProvider:
    """Der Anwalt trägt die Daten selbst ein - keine automatische
    Anreicherung, reine Übernahme."""

    name = "manual"

    def resolve(self, data: SourceImport) -> SourceImport:
        return data
