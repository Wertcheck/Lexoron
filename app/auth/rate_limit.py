"""Rate-Limiting für Login-Versuche (Prompt 29).

Bewusst EIN einfacher, prozesslokaler In-Memory-Zähler statt einer
zusätzlichen Abhängigkeit (z. B. Redis-gestütztes `slowapi`) - passend
zur bestehenden Ein-Prozess-Architektur (SQLite, keine verteilte
Infrastruktur). Setzt bei jedem Neustart zurück - für ein internes
Kanzlei-Tool ein akzeptabler Kompromiss (siehe SECURITY_REVIEW.md,
Punkt 1: "für einen internen Pilotbetrieb nicht blockierend, aber
empfehlenswert früh einzuplanen").

Sperrt NACH E-Mail-Adresse (klassisches Brute-Force-Ziel: viele Versuche
gegen EIN Konto) UND zusätzlich nach IP-Adresse (verhindert, dass
dieselbe Quelle viele VERSCHIEDENE Konten durchprobiert - "Credential
Stuffing"/"Password Spraying").
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_WINDOW_SECONDS = 15 * 60  # 15 Minuten
DEFAULT_LOCKOUT_SECONDS = 15 * 60  # 15 Minuten Sperre nach Überschreiten


@dataclass
class _Bucket:
    failures: list[float] = field(default_factory=list)
    locked_until: float | None = None


class LoginRateLimiter:
    def __init__(
        self,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        lockout_seconds: float = DEFAULT_LOCKOUT_SECONDS,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def is_locked_out(self, key: str) -> bool:
        """Prüft, OHNE einen Versuch zu zählen - für die Prüfung VOR
        einem Login-Versuch."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                return False
            if bucket.locked_until is not None and now < bucket.locked_until:
                return True
            return False

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.setdefault(key, _Bucket())
            bucket.failures = [t for t in bucket.failures if now - t < self.window_seconds]
            bucket.failures.append(now)
            if len(bucket.failures) >= self.max_attempts:
                bucket.locked_until = now + self.lockout_seconds

    def record_success(self, key: str) -> None:
        with self._lock:
            self._buckets.pop(key, None)

    def reset(self) -> None:
        """Nur für Tests - leert den gesamten Zustand."""
        with self._lock:
            self._buckets.clear()


# Ein Singleton pro Prozess - dieselbe Instanz muss über alle Login-
# Anfragen hinweg verwendet werden, sonst würde jede Anfrage bei einem
# frischen Zähler starten.
login_rate_limiter = LoginRateLimiter()
