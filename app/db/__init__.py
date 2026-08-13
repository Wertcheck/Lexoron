"""Datenzugriffsschicht (Prompt 04).

Kapselt Engine/Session-Erzeugung hinter dieser Schicht, damit Modelle und
Geschaeftslogik nie direkt von SQLite oder PostgreSQL abhaengen - nur von
`DATABASE_URL` aus der zentralen Konfiguration (app/config). Der Wechsel
SQLite -> PostgreSQL erfordert damit keine Aenderung an Modellen oder
Business-Logik (siehe ARCHITECTURE.md §4/§10/§12).
"""

from .session import SessionLocal, engine, get_db

__all__ = ["SessionLocal", "engine", "get_db"]
