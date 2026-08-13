"""Test-Fixture: deterministischer Fake-Embedding-Provider.

WICHTIG: Das ist KEIN echtes Embedding-Modell, sondern eine simple,
deterministische Bag-of-Words-Hashing-Heuristik NUR für Tests. Sie erzeugt
für Texte mit gemeinsamen Wörtern ähnliche Vektoren (genug, um Cosine-
Similarity-Logik zu testen), ohne einen echten Modell-Download zu
benötigen. Produktionscode nutzt ausschließlich `FastEmbedProvider`
(app/search/embeddings.py) mit einem echten lokalen Modell.
"""

from __future__ import annotations

import hashlib

_VECTOR_DIMENSIONS = 32


class FakeEmbeddingProvider:
    model_name = "fake-test-embedding-v1"

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * _VECTOR_DIMENSIONS
        words = text.lower().split()
        if not words:
            return vector
        for word in words:
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            index = digest[0] % _VECTOR_DIMENSIONS
            vector[index] += 1.0
        return vector
