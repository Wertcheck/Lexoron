"""Unit-Tests für app/auth/security.py und app/auth/session.py (Prompt 26).

Deckt aus der geforderten Testliste insbesondere ab:
- #17 Session läuft nach Ablauf ab
- #18 Passwort wird niemals als Klartext gespeichert
"""

from __future__ import annotations

import time

import pytest

from app.auth.security import hash_password, needs_rehash, verify_password
from app.auth.session import create_session_token, read_session_token
from app.config import Settings


def _dev_settings(**overrides) -> Settings:
    return Settings(app_env="development", **overrides)


# --- Passwort-Hashing (#18) ---


def test_hash_password_never_equals_plaintext() -> None:
    hashed = hash_password("MeinSicheresPasswort123")
    assert hashed != "MeinSicheresPasswort123"
    assert "MeinSicheresPasswort123" not in hashed


def test_hash_password_produces_argon2_hash() -> None:
    hashed = hash_password("MeinSicheresPasswort123")
    assert hashed.startswith("$argon2")


def test_hash_password_is_salted_different_each_time() -> None:
    """Zwei Hashes desselben Passworts müssen sich unterscheiden (Salt) -
    verhindert, dass gleiche Passwörter an gleichen Hashes erkennbar sind."""
    h1 = hash_password("MeinSicheresPasswort123")
    h2 = hash_password("MeinSicheresPasswort123")
    assert h1 != h2


def test_verify_password_accepts_correct_password() -> None:
    hashed = hash_password("MeinSicheresPasswort123")
    assert verify_password("MeinSicheresPasswort123", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("MeinSicheresPasswort123")
    assert verify_password("FalschesPasswort", hashed) is False


def test_verify_password_rejects_none_hash_without_crashing() -> None:
    """Ein Nutzer ohne password_hash (z. B. zukünftiger SSO-Nutzer) darf
    NIE zu einem Absturz führen - immer sauber False."""
    assert verify_password("irgendwas", None) is False


def test_verify_password_rejects_malformed_hash_without_crashing() -> None:
    assert verify_password("irgendwas", "kein-echter-argon2-hash") is False


def test_hash_password_rejects_empty_password() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_needs_rehash_false_for_freshly_created_hash() -> None:
    hashed = hash_password("MeinSicheresPasswort123")
    assert needs_rehash(hashed) is False


# --- Session-Tokens (#17) ---


def test_session_token_roundtrip_returns_correct_user_id() -> None:
    settings = _dev_settings()
    token, csrf = create_session_token("user-123", settings)

    payload = read_session_token(token, settings)

    assert payload is not None
    assert payload["user_id"] == "user-123"
    assert payload["csrf"] == csrf


def test_session_token_rejects_tampered_signature() -> None:
    settings = _dev_settings()
    token, _csrf = create_session_token("user-123", settings)
    tampered = token[:-4] + ("0" * 4)

    assert read_session_token(tampered, settings) is None


def test_session_expires_after_max_age() -> None:
    """Kern der Anforderung #17: eine Session, die älter als
    `session_max_age_seconds` ist, wird als ungültig behandelt - geprüft
    über eine sehr kleine max_age (0 Sekunden), damit der Test nicht 8
    Stunden warten muss."""
    settings = _dev_settings(session_max_age_seconds=1)
    token, _csrf = create_session_token("user-123", settings)

    time.sleep(1.2)

    expired_settings = _dev_settings(session_max_age_seconds=1)
    assert read_session_token(token, expired_settings) is None


def test_session_still_valid_within_max_age() -> None:
    settings = _dev_settings(session_max_age_seconds=3600)
    token, _csrf = create_session_token("user-123", settings)

    assert read_session_token(token, settings) is not None


def test_each_session_gets_a_different_csrf_token() -> None:
    settings = _dev_settings()
    _token1, csrf1 = create_session_token("user-123", settings)
    _token2, csrf2 = create_session_token("user-123", settings)
    assert csrf1 != csrf2


def test_read_session_token_rejects_garbage_input() -> None:
    settings = _dev_settings()
    assert read_session_token("völlig-ungültiges-token", settings) is None
