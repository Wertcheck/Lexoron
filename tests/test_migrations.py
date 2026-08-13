"""Test fuer die Alembic-Migration selbst (Prompt 04).

Prueft automatisiert, was zuvor manuell verifiziert wurde: die Migration
laesst sich auf eine frische SQLite-Datenbank anwenden und wieder
vollstaendig zurueckrollen, ohne Fehler.

Nutzt eine eigene, temporaere SQLite-Datei (nicht die konfigurierte
DATABASE_URL und nicht die Test-In-Memory-DB aus test_models.py), damit
dieser Test unabhaengig von lokalem Zustand ist.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config


def _alembic_config_for(db_path: Path) -> Config:
    project_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "migrations"))
    # Ueberschreibt die aus app.config geladene URL gezielt fuer den Test.
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def test_migration_upgrade_and_downgrade_succeed(tmp_path: Path) -> None:
    db_path = tmp_path / "migration_test.db"
    cfg = _alembic_config_for(db_path)

    command.upgrade(cfg, "head")
    assert db_path.exists()

    import sqlite3

    con = sqlite3.connect(str(db_path))
    tables = {
        row[0]
        for row in con.execute(
            "select name from sqlite_master where type='table'"
        ).fetchall()
    }
    con.close()

    expected_tables = {
        "clients",
        "matters",
        "parties",
        "messages",
        "documents",
        "tasks",
        "deadlines",
        "drafts",
        "sources",
        "knowledge_items",
        "workflow_runs",
        "audit_events",
        "users",
        "roles",
    }
    assert expected_tables.issubset(tables)

    # Muss vollstaendig zurueckrollbar sein.
    command.downgrade(cfg, "base")
