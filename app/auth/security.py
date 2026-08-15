"""Passwort-Hashing (Prompt 26).

Argon2id über `argon2-cffi` (aktiver, moderner Standard - Gewinner der
Password Hashing Competition, empfohlen von OWASP). Bewusst DIREKT über
die Bibliothek statt über `passlib` (dessen Argon2-Backend-Wartung
unsicher ist) - eine einzige, dünne Schicht um `argon2.PasswordHasher`.

GRUNDREGEL: Ein Klartext-Passwort existiert nur so lange als Python-
String, wie es für den Hash-/Verify-Aufruf unbedingt nötig ist - es wird
an KEINER Stelle geloggt, in eine Exception-Message eingebettet oder
sonst irgendwo persistiert. `hash_password`/`verify_password` sind die
EINZIGEN Funktionen im Projekt, die mit einem Klartext-Passwort in
Berührung kommen.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """Erzeugt einen Argon2id-Hash. Der Rückgabewert ist sicher
    persistierbar (enthält Salt + Parameter, wie bei Argon2 üblich)."""
    if not plain_password:
        raise ValueError("Passwort darf nicht leer sein")
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str | None) -> bool:
    """Prüft ein Klartext-Passwort gegen einen gespeicherten Hash.

    Gibt bei JEDEM Fehler (falsches Passwort, fehlender/ungültiger Hash)
    einheitlich `False` zurück - kein Unterschied in Timing-relevanter
    Fehlerbehandlung zwischen "Nutzer existiert nicht" und "Passwort
    falsch" (verhindert User-Enumeration über Fehlerverhalten, siehe
    AuthService.authenticate)."""
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Erlaubt, Hashes bei veralteten Argon2-Parametern transparent zu
    erneuern (z. B. nach einem künftigen Sicherheits-Update der
    Hash-Parameter) - aktuell an keiner Stelle zwingend aufgerufen, aber
    vorbereitet für AuthService.authenticate."""
    return _hasher.check_needs_rehash(password_hash)
