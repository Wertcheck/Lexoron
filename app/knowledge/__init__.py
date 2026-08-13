"""Kanzlei-Wissensbasis (Prompt 12).

`KnowledgeItemService` kapselt Import, Versionierung, Freigabe und
Deaktivierung von `KnowledgeItem`s (Modell aus Prompt 04, um `source` und
Gültigkeitsbereich erweitert in Prompt 12). Die eigentliche Suche
(Volltext + semantisch, "approved"-Filter) wurde bereits in Prompt 11 als
`DocumentSearchService.search_knowledge_base()` gebaut - dieser Service
nutzt sie für die Indizierung nach Freigabe, baut sie aber nicht neu.

WICHTIGSTE REGEL (Konzept §5, wörtlich): "Inhalte dürfen erst nach
expliziter Freigabe (`approval_status == "approved"`) in Entwürfe
einfließen." Neu importiertes oder verändertes Wissen ist daher IMMER
`pending`, nie automatisch `approved`.
"""

from app.knowledge.schema import KnowledgeItemImport
from app.knowledge.service import KnowledgeItemService

__all__ = ["KnowledgeItemImport", "KnowledgeItemService"]
