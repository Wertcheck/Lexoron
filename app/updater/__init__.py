"""Auto-Updater (Schritt 3): stumme Hintergrund-Prüfung auf neue Versionen.

Siehe app/updater/checker.py für die eigentliche Logik. Bewusst KEIN
automatischer Download/Installation - nur eine Ja/Nein-Information für
einen unaufdringlichen Hinweis im Dashboard, siehe
app/web/monitoring_router.py: update_badge.
"""

from app.updater.checker import CURRENT_APP_VERSION, UpdateCheckResult, check_for_update

__all__ = ["CURRENT_APP_VERSION", "UpdateCheckResult", "check_for_update"]
