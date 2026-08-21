"""ModelCatalog – zentrale, versionierbare Metadaten freigegebener lokaler
Modelle (§67).

Modelldaten (Name, Download-Groesse, Kontextlaenge) stammen von der
offiziellen Ollama-Modellseite (https://ollama.com/library/qwen3, Stand
21.08.) - `download_size_gb` fuer `qwen3:4b` zusaetzlich real durch einen
tatsaechlichen `ollama pull` in dieser Session bestaetigt (siehe
ARCHITECTURE.md §66). Ausschliesslich Modelle der `qwen3`-Familie (aktuell
über die konfigurierte Ollama-Runtime bezogen, siehe
app/ai_providers/ollama_provider.py) - keine Drittanbieter-/Fantasiewerte.

`min_ram_gb`/`recommended_ram_gb` sind eine dokumentierte, konservative
Faustregel (Download-/Diskgroesse als Naeherung fuer den GGUF-Speicherbedarf
im RAM plus Kontext-/OS-Overhead) - AUSDRUECKLICH KEINE von Ollama
veroeffentlichte offizielle Kennzahl (die Modellseite nennt keine
Mindest-RAM-Werte). `expected_performance_class` ist eine RELATIVE,
modellinterne Einordnung (kleinere Parameterzahl = grundsaetzlich
schneller als groessere, bei sonst gleicher Hardware) - KEINE gemessene
Token/Sekunde-Angabe (Vorgabe, woertlich: "Keine frei erfundenen Angaben
wie '20 tok/s'"). Die tatsaechliche, hardwareabhaengige Einordnung
(schnell/ausgewogen/langsam/sehr langsam) berechnet erst
`recommendation.py::RecommendationEngine` aus Modell + Hardware."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RelativePerformanceClass(str, Enum):
    """Rein modellinterne, relative Einordnung - siehe Moduldocstring."""

    FAST = "fast"
    BALANCED = "balanced"
    SLOW = "slow"


@dataclass(frozen=True)
class ModelCatalogEntry:
    model_name: str
    runtime: str
    tag: str
    download_size_gb: float
    context_length: int
    min_ram_gb: float
    recommended_ram_gb: float
    min_vram_gb: float
    recommended_vram_gb: float
    cpu_only_supported: bool
    gpu_supported: bool
    capability_profile: tuple[str, ...]
    strengths: tuple[str, ...]
    limitations: tuple[str, ...]
    expected_performance_class: RelativePerformanceClass
    # Niedrigere Zahl = wird bei gleichwertiger Eignung bevorzugt
    # empfohlen (siehe RecommendationEngine) - z. B. das kleinere von zwei
    # technisch gleichermassen "passenden" Modellen.
    recommendation_priority: int


def _ram_estimate(download_size_gb: float) -> tuple[float, float]:
    """Konservative Faustregel (siehe Moduldocstring): min = Downloadgroesse
    + ca. 30% Overhead (Kontext/Runtime) + 2 GB OS-Reserve, empfohlen =
    zusaetzlich 50% Sicherheitsmarge fuer fluessigeren Betrieb neben der
    restlichen Anwendung."""
    minimum = round(download_size_gb * 1.3 + 2, 1)
    recommended = round(download_size_gb * 1.3 + 4, 1)
    return minimum, recommended


_QWEN3_CAPABILITIES = (
    "lokale Textvorverarbeitung",
    "Klassifikation",
    "Zusammenfassung",
    "einfache Extraktion",
)
_QWEN3_LIMITATIONS = (
    "keine anspruchsvolle juristische Argumentation",
    "ersetzt nicht die Claude-Textproduktionsschicht",
    "keine eigenstaendige Rechtsberatung/Rechtsentscheidung",
)


def _qwen3_entry(
    tag: str,
    download_size_gb: float,
    context_length: int,
    performance_class: RelativePerformanceClass,
    priority: int,
) -> ModelCatalogEntry:
    min_ram, recommended_ram = _ram_estimate(download_size_gb)
    return ModelCatalogEntry(
        model_name="Qwen3",
        runtime="ollama",
        tag=f"qwen3:{tag}",
        download_size_gb=download_size_gb,
        context_length=context_length,
        min_ram_gb=min_ram,
        recommended_ram_gb=recommended_ram,
        # Grobe, ebenfalls dokumentierte Naeherung: VRAM-Bedarf fuer
        # vollstaendiges GPU-Offloading liegt in der Groessenordnung der
        # Downloadgroesse (quantisiertes GGUF) - proportionaler Aufschlag
        # statt fixer Offset, damit die Schaetzung ueber alle Modellgroessen
        # hinweg konsistent bleibt.
        min_vram_gb=round(download_size_gb * 1.1, 1),
        recommended_vram_gb=round(download_size_gb * 1.3, 1),
        cpu_only_supported=True,
        gpu_supported=True,
        capability_profile=_QWEN3_CAPABILITIES,
        strengths=(
            "läuft rein lokal, keine Cloud-Abhängigkeit für diesen Schritt",
            "unterstützt sowohl CPU-only- als auch GPU-beschleunigten Betrieb",
        ),
        limitations=_QWEN3_LIMITATIONS,
        expected_performance_class=performance_class,
        recommendation_priority=priority,
    )


# Reale Daten von https://ollama.com/library/qwen3 (Stand 21.08.) - siehe
# Moduldocstring. `qwen3:30b` als groesster hier aufgenommener Eintrag
# (Workstation-Klasse) - die noch groesseren Varianten (32b/235b) sind
# kein realistischer Kanzlei-PC-Anwendungsfall und bewusst nicht
# aufgenommen (siehe ARCHITECTURE.md §67, "keine ueberdimensionierte
# Katalogbreite ohne Produktbedarf").
MODEL_CATALOG: tuple[ModelCatalogEntry, ...] = (
    _qwen3_entry("0.6b", 0.523, 40_000, RelativePerformanceClass.FAST, priority=1),
    _qwen3_entry("1.7b", 1.4, 40_000, RelativePerformanceClass.FAST, priority=2),
    _qwen3_entry("4b", 2.5, 256_000, RelativePerformanceClass.BALANCED, priority=3),
    _qwen3_entry("8b", 5.2, 40_000, RelativePerformanceClass.BALANCED, priority=4),
    _qwen3_entry("14b", 9.3, 40_000, RelativePerformanceClass.SLOW, priority=5),
    _qwen3_entry("30b", 19.0, 256_000, RelativePerformanceClass.SLOW, priority=6),
)


def get_model_catalog() -> tuple[ModelCatalogEntry, ...]:
    """Einziger Zugriffspunkt auf den Katalog (statt `MODEL_CATALOG`
    projektweit direkt zu importieren) - erlaubt spaeter z. B. eine
    Versionierung/externe Konfigurierbarkeit einzuziehen, ohne
    Aufrufer anzupassen."""
    return MODEL_CATALOG
