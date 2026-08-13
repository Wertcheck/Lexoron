"""Akten-Such-/Kontextschicht (Prompt 11).

Unterstützt exakte Metadatenfilter, Volltextsuche und semantische
(Vektor-)Suche - kombiniert ("hybrid"). WICHTIGSTE REGEL (Konzept Prompt 11
wörtlich): "Der Context-Agent darf nur Dokumente aus der aktuellen Akte
oder ausdrücklich freigegebene globale Wissensquellen abrufen." Diese
Isolation ist strukturell im Service verankert: Dokumentensuche verlangt
zwingend eine `matter_id`, es gibt keine Methode für eine
aktenübergreifende Dokumentensuche. Wissensbasis-Suche ist getrennt und
liefert ausschließlich freigegebene (`approval_status == "approved"`)
`KnowledgeItem`s.

Embeddings laufen lokal über `fastembed` (ONNX-Runtime, kein PyTorch/CUDA
nötig) - keine Mandantendaten verlassen dafür die Kanzlei-Umgebung.
"""

from app.search.embeddings import EmbeddingProvider, FastEmbedProvider
from app.search.schema import SearchResult
from app.search.service import DocumentSearchService

__all__ = [
    "EmbeddingProvider",
    "FastEmbedProvider",
    "SearchResult",
    "DocumentSearchService",
]
