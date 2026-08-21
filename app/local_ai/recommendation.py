"""RecommendationEngine – berechnet aus `ModelCatalog` + `HardwareProfile`
eine nachvollziehbare Modellempfehlung (§67).

Unterscheidet ausdrücklich (Vorgabe, wörtlich) zwischen "technisch
lauffähig" und "für Lexoron sinnvoll empfohlen": ein Modell kann alle
Mindestanforderungen erfüllen und trotzdem nur als `MARGINAL` eingestuft
werden - vor allem auf `HardwareClass.LEGACY`-Systemen (siehe real
vermessener i7-3720QM-Fall, ARCHITECTURE.md §66: 247s für `qwen3:4b` sind
für einen interaktiven Dashboard-Aufruf nicht praxistauglich, obwohl das
Modell technisch fehlerfrei lief).

KEINE erfundenen Performance-Werte (Vorgabe, wörtlich: "Keine frei
erfundenen Angaben wie '20 tok/s'"): `performance_category` ist IMMER eine
der vier Kategorien schnell/ausgewogen/langsam/sehr langsam, nie eine
konkrete Zahl - abgeleitet aus der relativen Modellgröße
(`ModelCatalogEntry.expected_performance_class`) und der Hardwareklasse,
NICHT aus einem gemessenen Benchmark (mit der einen dokumentierten
Ausnahme: die reale i7-3720QM-Messung selbst, die genau bestätigt, warum
LEGACY-Systeme nie schneller als "langsam" eingestuft werden)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.local_ai.hardware_detector import has_capable_gpu
from app.local_ai.hardware_schema import HardwareClass, HardwareProfile
from app.local_ai.model_catalog import (
    ModelCatalogEntry,
    RelativePerformanceClass,
    get_model_catalog,
)


class RecommendationStatus(str, Enum):
    #: Beste verfügbare Wahl für diese Hardware - gutes Verhältnis aus
    #: Qualität, Geschwindigkeit und Ressourcenbedarf.
    RECOMMENDED = "recommended"
    #: Läuft zuverlässig, ist aber nicht die bevorzugte Wahl (z. B.
    #: langsamer oder ressourcenhungriger als die Empfehlung).
    SUPPORTED = "supported"
    #: Technisch lauffähig, aber NICHT empfohlen (z. B. auf Legacy-
    #: Hardware zu langsam für interaktive Nutzung).
    MARGINAL = "marginal"
    #: Erfüllt die Mindestanforderungen (RAM/VRAM) dieses Modells nicht.
    UNSUPPORTED = "unsupported"


_PERFORMANCE_CATEGORIES = ("schnell", "ausgewogen", "langsam", "sehr langsam")

# Ein Modell gilt erst dann als RECOMMENDED (nicht nur SUPPORTED), wenn
# die Hardware sein "empfohlenes" Anforderungsniveau mit spuerbarem
# Puffer uebertrifft - nicht nur knapp erreicht. Genau dieser Puffer ist
# der technische Kern von "Empfehlung != technisches Maximum" (Vorgabe):
# das GROESSTE Modell, das diesen Puffer noch erreicht, wird empfohlen -
# ein noch groesseres Modell, das die Hardware nur knapp/gar nicht mehr
# schafft, faellt automatisch auf SUPPORTED/MARGINAL zurueck.
_RECOMMENDED_HEADROOM_MULTIPLIER = 1.4


@dataclass(frozen=True)
class ModelEvaluation:
    entry: ModelCatalogEntry
    status: RecommendationStatus
    # Immer eine der vier Kategorien in `_PERFORMANCE_CATEGORIES` - siehe
    # Moduldocstring, warum hier nie eine konkrete Zahl steht.
    performance_category: str
    reason: str


@dataclass(frozen=True)
class ModelRecommendation:
    hardware_class: HardwareClass
    # None NUR, wenn wirklich kein einziges Katalogmodell mindestens
    # SUPPORTED erreicht (typischerweise HardwareClass.UNSUPPORTED).
    primary: ModelEvaluation | None
    # Alle uebrigen Katalogeintraege (inkl. UNSUPPORTED, mit Begruendung -
    # Transparenz statt stillem Weglassen), sortiert nach
    # recommendation_priority.
    alternatives: list[ModelEvaluation]


def _performance_category(
    entry: ModelCatalogEntry, hardware_class: HardwareClass, capable_gpu: bool
) -> str:
    """Rein qualitative, deterministische Ableitung - siehe Moduldocstring.
    LEGACY deckelt IMMER auf "langsam"/"sehr langsam" (reale Grundlage:
    §66)."""
    if hardware_class == HardwareClass.LEGACY:
        if entry.expected_performance_class == RelativePerformanceClass.FAST:
            return "langsam"
        return "sehr langsam"

    if capable_gpu or hardware_class in (HardwareClass.PERFORMANCE, HardwareClass.WORKSTATION):
        mapping = {
            RelativePerformanceClass.FAST: "schnell",
            RelativePerformanceClass.BALANCED: "schnell",
            RelativePerformanceClass.SLOW: "ausgewogen",
        }
    else:  # STANDARD, CPU-only
        mapping = {
            RelativePerformanceClass.FAST: "schnell",
            RelativePerformanceClass.BALANCED: "ausgewogen",
            RelativePerformanceClass.SLOW: "langsam",
        }
    return mapping[entry.expected_performance_class]


def _evaluate(entry: ModelCatalogEntry, profile: HardwareProfile) -> ModelEvaluation:
    capable_gpu = has_capable_gpu(profile)
    ram = profile.ram_total_gb
    vram = profile.vram_gb or 0.0
    performance_category = _performance_category(entry, profile.hardware_class, capable_gpu)

    if profile.hardware_class == HardwareClass.UNSUPPORTED:
        return ModelEvaluation(
            entry=entry,
            status=RecommendationStatus.UNSUPPORTED,
            performance_category=performance_category,
            reason=(
                f"Diese Maschine erfüllt die Mindestanforderung von 16 GB RAM für "
                f"eine unterstützte lokale KI-Installation nicht (erkannt: "
                f"{ram if ram is not None else 'unbekannt'} GB)."
            ),
        )

    if ram is None or ram < entry.min_ram_gb:
        return ModelEvaluation(
            entry=entry,
            status=RecommendationStatus.UNSUPPORTED,
            performance_category=performance_category,
            reason=(
                f"Benötigt mindestens ca. {entry.min_ram_gb} GB RAM, erkannt: "
                f"{ram if ram is not None else 'unbekannt'} GB."
            ),
        )

    meets_recommended_ram = ram >= entry.recommended_ram_gb
    meets_recommended_ram_with_headroom = (
        ram >= entry.recommended_ram_gb * _RECOMMENDED_HEADROOM_MULTIPLIER
    )
    meets_min_vram = capable_gpu and vram >= entry.min_vram_gb
    meets_recommended_vram = capable_gpu and vram >= entry.recommended_vram_gb
    meets_recommended_vram_with_headroom = (
        capable_gpu and vram >= entry.recommended_vram_gb * _RECOMMENDED_HEADROOM_MULTIPLIER
    )

    if profile.hardware_class == HardwareClass.LEGACY:
        # Nie RECOMMENDED auf Legacy-Hardware (siehe Moduldocstring) -
        # bestenfalls SUPPORTED fuer die kleinsten/schnellsten Modelle,
        # sonst MARGINAL.
        if entry.expected_performance_class == RelativePerformanceClass.FAST and meets_recommended_ram:
            return ModelEvaluation(
                entry=entry,
                status=RecommendationStatus.SUPPORTED,
                performance_category=performance_category,
                reason=(
                    "Ressourcenschonendstes verfügbares Modell - läuft auf dieser "
                    "älteren CPU-only-Hardware, aber spürbar langsamer als auf "
                    "moderner Hardware (siehe reale Messung auf vergleichbarem "
                    "System, ARCHITECTURE.md §66)."
                ),
            )
        return ModelEvaluation(
            entry=entry,
            status=RecommendationStatus.MARGINAL,
            performance_category=performance_category,
            reason=(
                "Technisch lauffähig, aber auf dieser älteren CPU-only-Hardware "
                "nicht für interaktive Nutzung empfohlen (reale Messung eines "
                "vergleichbaren Modells auf vergleichbarer Hardware: mehrere "
                "Minuten pro Anfrage, siehe ARCHITECTURE.md §66)."
            ),
        )

    if capable_gpu:
        if meets_recommended_vram_with_headroom and meets_recommended_ram_with_headroom:
            return ModelEvaluation(
                entry=entry,
                status=RecommendationStatus.RECOMMENDED,
                performance_category=performance_category,
                reason=(
                    "Reichlich RAM- und VRAM-Reserve für einen flüssigen, "
                    "GPU-beschleunigten Betrieb - gutes Verhältnis aus lokaler "
                    "Leistung und Ressourcenbedarf für diese Hardware."
                ),
            )
        if meets_min_vram and meets_recommended_ram:
            return ModelEvaluation(
                entry=entry,
                status=RecommendationStatus.SUPPORTED,
                performance_category=performance_category,
                reason=(
                    "Läuft mit der vorhandenen GPU, aber ohne die großzügige "
                    "Leistungsreserve der empfohlenen Wahl."
                ),
            )
        return ModelEvaluation(
            entry=entry,
            status=RecommendationStatus.MARGINAL,
            performance_category=performance_category,
            reason="Erfüllt allenfalls die Mindestanforderung an RAM/VRAM, kaum Leistungsreserve.",
        )

    # CPU-only, nicht LEGACY (STANDARD/PERFORMANCE/WORKSTATION ohne
    # geeignete GPU).
    if meets_recommended_ram_with_headroom:
        return ModelEvaluation(
            entry=entry,
            status=RecommendationStatus.RECOMMENDED,
            performance_category=performance_category,
            reason="Reichlich RAM-Reserve - gutes Verhältnis aus lokaler Leistung und Ressourcenbedarf.",
        )
    if meets_recommended_ram:
        return ModelEvaluation(
            entry=entry,
            status=RecommendationStatus.SUPPORTED,
            performance_category=performance_category,
            reason="Läuft zuverlässig, aber ohne die großzügige RAM-Reserve der empfohlenen Wahl.",
        )
    return ModelEvaluation(
        entry=entry,
        status=RecommendationStatus.MARGINAL,
        performance_category=performance_category,
        reason="Erfüllt nur die Mindestanforderung an RAM, kaum Leistungsreserve.",
    )


class RecommendationEngine:
    def __init__(self, catalog: tuple[ModelCatalogEntry, ...] | None = None) -> None:
        self.catalog = catalog if catalog is not None else get_model_catalog()

    def recommend(self, profile: HardwareProfile) -> ModelRecommendation:
        """Deterministisch: derselbe `HardwareProfile` liefert IMMER
        dieselbe `ModelRecommendation` - keine Zufallskomponente, kein
        externer Zustand ausser dem statischen Katalog."""
        evaluations = [_evaluate(entry, profile) for entry in self.catalog]
        evaluations.sort(key=lambda e: e.entry.recommendation_priority)

        status_rank = {
            RecommendationStatus.RECOMMENDED: 0,
            RecommendationStatus.SUPPORTED: 1,
            RecommendationStatus.MARGINAL: 2,
            RecommendationStatus.UNSUPPORTED: 3,
        }
        best_rank = min(status_rank[e.status] for e in evaluations)

        primary: ModelEvaluation | None = None
        alternatives: list[ModelEvaluation] = []
        if best_rank < status_rank[RecommendationStatus.UNSUPPORTED]:
            # Unter mehreren gleichwertig eingestuften Modellen (z. B.
            # mehrere RECOMMENDED) gewinnt bewusst das GROESSTE
            # (hoechste recommendation_priority), nicht das kleinste -
            # "Empfehlung != technisches Maximum" bedeutet NICHT "immer
            # das kleinste Modell", sondern das groesste, das die
            # Hardware noch komfortabel (mit Puffer) traegt. Der
            # eigentliche Deckel gegen das technische Maximum liegt in
            # der strengeren RECOMMENDED-Schwelle in `_evaluate`
            # (`_RECOMMENDED_HEADROOM_MULTIPLIER`), nicht in dieser
            # Auswahl hier.
            candidates_at_best = [e for e in evaluations if status_rank[e.status] == best_rank]
            primary = max(candidates_at_best, key=lambda e: e.entry.recommendation_priority)
            alternatives = [e for e in evaluations if e is not primary]
        else:
            # Kein einziges Modell erreicht mindestens SUPPORTED - keine
            # Primaerempfehlung, alle Eintraege landen (mit Begruendung)
            # als "Alternativen" im UNSUPPORTED-Zustand.
            alternatives = evaluations

        return ModelRecommendation(
            hardware_class=profile.hardware_class,
            primary=primary,
            alternatives=alternatives,
        )
