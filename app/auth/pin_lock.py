"""PinLockService – App-Sperre / PIN-Lock (Schritt 3, Teil 2).

Bedrohungsmodell: eine fremde Person tritt kurz an einen unbeaufsichtigten,
noch angemeldeten Arbeitsplatz (Datenschutz am Schreibtisch) - NICHT ein
entschlossener Angreifer mit Werkzeugzugriff. Die PIN ist deshalb bewusst
ein SCHWÄCHERES, zusätzliches Geheimnis, kein Ersatz für das eigentliche
Passwort - `require_login` (app/auth/permissions.py) bleibt die einzige
echte Authentifizierungsgrenze; die Sperre blockiert nur den Zugriff
INNERHALB einer bereits authentifizierten Session.

Ohne eingerichtete PIN (`User.pin_hash is None`) ist die Funktion komplett
inaktiv - kein Sperren möglich, kein Inaktivitäts-Timer im UI (siehe
app/web/templates/base.html) - sonst gäbe es keinen Weg, sich je wieder zu
entsperren."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.models import User

MIN_PIN_LENGTH = 4
MAX_PIN_LENGTH = 8


class PinValidationError(Exception):
    pass


class PinLockService:
    def set_pin(self, db: Session, user: User, pin: str) -> None:
        if not pin.isdigit():
            raise PinValidationError("Die PIN darf nur Ziffern enthalten")
        if not (MIN_PIN_LENGTH <= len(pin) <= MAX_PIN_LENGTH):
            raise PinValidationError(
                f"Die PIN muss zwischen {MIN_PIN_LENGTH} und {MAX_PIN_LENGTH} Ziffern lang sein"
            )
        user.pin_hash = hash_password(pin)
        db.commit()

    def clear_pin(self, db: Session, user: User) -> None:
        """Entfernt die PIN UND hebt eine eventuell aktive Sperre auf -
        sonst könnte ein Nutzer sich nach dem Löschen der PIN nie wieder
        entsperren."""
        user.pin_hash = None
        user.is_locked = False
        db.commit()

    def lock(self, db: Session, user: User) -> None:
        if user.pin_hash is None:
            raise PinValidationError(
                "Ohne eingerichtete PIN kann die App nicht gesperrt werden "
                "(kein Weg, sich wieder zu entsperren)."
            )
        user.is_locked = True
        db.commit()

    def unlock(self, db: Session, user: User, pin: str) -> bool:
        if not verify_password(pin, user.pin_hash):
            return False
        user.is_locked = False
        db.commit()
        return True
