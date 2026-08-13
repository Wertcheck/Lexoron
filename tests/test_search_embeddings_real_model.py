"""Test fuer app/search/embeddings.py mit dem ECHTEN Modell (Prompt 11).

Dieser Test laedt tatsaechlich das konfigurierte Embedding-Modell. In der
Claude-Sandbox ist der Zugriff auf huggingface.co netzwerkseitig nicht
freigegeben (analog zur Python-3.13-Einschraenkung, siehe ARCHITECTURE.md)
- der Test wird dann uebersprungen (`pytest.skip`) statt faelschlich als
Fehlschlag gewertet zu werden. Auf dem Windows-Zielsystem des Anwalts mit
normalem Internetzugang sollte dieser Test tatsaechlich durchlaufen -
genau das ist die finale Verifikation, die dort noch aussteht.
"""

import pytest

from app.config import get_settings
from app.search.embeddings import FastEmbedProvider


def test_real_embedding_model_produces_similar_vectors_for_similar_text() -> None:
    provider = FastEmbedProvider(model_name=get_settings().embedding_model_name)
    try:
        vector_a = provider.embed("Der Mietvertrag wurde fristgerecht gekündigt.")
        vector_b = provider.embed("Die Kündigung des Mietvertrags erfolgte rechtzeitig.")
        vector_c = provider.embed("Die Kaffeemaschine in der Küche ist kaputt.")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(
            f"Echtes Embedding-Modell konnte nicht geladen werden (vermutlich "
            f"fehlender Netzwerkzugriff auf huggingface.co in dieser Umgebung, "
            f"siehe ARCHITECTURE.md §21): {exc}"
        )

    from app.search.utils import cosine_similarity

    similar_score = cosine_similarity(vector_a, vector_b)
    dissimilar_score = cosine_similarity(vector_a, vector_c)

    assert similar_score > dissimilar_score
