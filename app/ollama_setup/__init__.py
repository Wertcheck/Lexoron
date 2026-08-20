"""Geführter Ollama-Installations-/Update-Assistent - siehe
app/ollama_setup/service.py."""

from app.ollama_setup.service import (
    OLLAMA_WINDOWS_INSTALLER_URL,
    OllamaInstallerService,
    OllamaInstallProgress,
)

__all__ = [
    "OLLAMA_WINDOWS_INSTALLER_URL",
    "OllamaInstallerService",
    "OllamaInstallProgress",
]
