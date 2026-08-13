"""Zentrales Konfigurationssystem (Prompt 03).

Stellt eine einzige, validierte Settings-Quelle fuer die gesamte Anwendung
bereit. Enthaelt bewusst generische Platzhalter fuer Bereiche, deren
eigentliche fachliche Logik erst in spaeteren Prompts entsteht (OCR, Mail,
LLM, Rechtsquellen, Freigaberegeln, Vorlagen, Aufbewahrung) - siehe TODO.md.
Es findet hier noch keine architektonische Festlegung fuer diese Bereiche
statt.
"""

from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
