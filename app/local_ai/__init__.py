"""Hardware-/Modell-Empfehlungslogik für die lokale KI (§67).

Bewusst getrennt von `app/ai_providers/` (das dortige `OllamaLocalLLMProvider`
SPRICHT mit einer bereits laufenden, bereits konfigurierten Ollama-Instanz -
dieses Paket hier entscheidet, WELCHES Modell auf WELCHER Hardware überhaupt
sinnvoll ist, BEVOR irgendetwas installiert oder aufgerufen wird). Struktur:

    HardwareDetector -> HardwareProfile
    ModelCatalog (statische, versionierbare Modell-Metadaten)
    HardwareProfile + ModelCatalog -> RecommendationEngine -> ModelRecommendation

Explizit NICHT Teil dieses Pakets (bewusst spätere, eigenständige Schritte):
Ollama-Installation, Windows-Installer, Silent-Setup, Modell-Download,
Auto-Start, Repair-/Update-System, Installer-/Einrichtungs-UI.
"""

from __future__ import annotations

from app.local_ai.hardware_detector import HardwareDetector, classify_hardware, has_capable_gpu
from app.local_ai.hardware_schema import HardwareClass, HardwareProfile
from app.local_ai.model_catalog import (
    MODEL_CATALOG,
    ModelCatalogEntry,
    RelativePerformanceClass,
    get_model_catalog,
)
from app.local_ai.ollama_installer import (
    DEFAULT_VERSION_POLICY,
    OllamaInstallResult,
    OllamaInstaller,
    OllamaVersionPolicy,
)
from app.local_ai.recommendation import (
    ModelEvaluation,
    ModelRecommendation,
    RecommendationEngine,
    RecommendationStatus,
)
from app.local_ai.setup_orchestrator import (
    LocalAiSetupService,
    LocalAiState,
    LocalAiStatus,
    SetupResult,
    SetupStage,
)

__all__ = [
    "HardwareDetector",
    "classify_hardware",
    "has_capable_gpu",
    "HardwareClass",
    "HardwareProfile",
    "MODEL_CATALOG",
    "ModelCatalogEntry",
    "RelativePerformanceClass",
    "get_model_catalog",
    "DEFAULT_VERSION_POLICY",
    "OllamaInstallResult",
    "OllamaInstaller",
    "OllamaVersionPolicy",
    "ModelEvaluation",
    "ModelRecommendation",
    "RecommendationEngine",
    "RecommendationStatus",
    "LocalAiSetupService",
    "LocalAiState",
    "LocalAiStatus",
    "SetupResult",
    "SetupStage",
]
