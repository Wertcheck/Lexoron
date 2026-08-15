"""Authentifizierung, Rollen, Berechtigungen (Prompt 26).

Session-basiert (signierte, zeitgestempelte Cookies, kein Server-Side-
Store), Argon2-Passwort-Hashing, feste Rechte-Matrix für die drei
Kanzlei-Rollen (Admin/Anwalt/Mitarbeiter, als DB-Seed-Daten angelegt -
siehe app/models/role.py). Siehe app/auth/permissions.py für die
vollständige Rechte-Matrix und die serverseitige Durchsetzung.
"""

from app.auth.service import AuthService, UserAlreadyExistsError, UserService

__all__ = ["AuthService", "UserService", "UserAlreadyExistsError"]
