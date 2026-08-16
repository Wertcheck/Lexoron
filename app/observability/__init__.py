"""Logging/Monitoring (Prompt 32).

Zentrale, PII-sichere Logging-Konfiguration (`logging_config.py`) und
Systemstatus-Ansicht für das Dashboard (`app/web/monitoring_router.py`).
"""

from app.observability.logging_config import configure_logging

__all__ = ["configure_logging"]
