"""EmbeddingProvider – Protocol + lokale Implementierung über `fastembed`.

`fastembed` (ONNX-Runtime) statt `sentence-transformers` (PyTorch), da
letzteres transitiv volle CUDA-Bibliotheken mitinstalliert - unnötig, da
für Embeddings reine CPU-Inferenz völlig ausreicht (siehe pyproject.toml-
Kommentar). Das Modell wird beim ersten Gebrauch lazy geladen (nicht beim
Erzeugen der Instanz), damit z. B. Tests, die keine echten Embeddings
brauchen, nicht unnötig einen Modell-Download auslösen.
"""

from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    model_name: str

    def embed(self, text: str) -> list[float]: ...


class FastEmbedProvider:
    """Lokales Embedding über `fastembed`. Lädt das Modell beim ersten
    Aufruf von `embed()` herunter (einmalig, danach aus lokalem Cache) -
    siehe README/ARCHITECTURE.md für den Hinweis zum benötigten
    Internetzugang beim allerersten Start."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    def _ensure_model_loaded(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._ensure_model_loaded()
        # fastembed().embed() liefert einen Generator von numpy-Arrays;
        # bei einem einzelnen Text genau ein Element.
        (vector,) = model.embed([text])
        return vector.tolist()
