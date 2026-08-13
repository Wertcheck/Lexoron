import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Projekt-Root zum Pfad hinzufuegen, damit "app" importierbar ist, egal von
# wo Alembic aufgerufen wird.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.db.session import _ensure_sqlite_directory_exists  # noqa: E402
from app.models import Base  # noqa: E402  (importiert alle Modelle)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadaten aller Modelle fuer Alembics Autogenerate.
target_metadata = Base.metadata

# DATABASE_URL kommt standardmaessig aus der zentralen Konfiguration
# (app.config.get_settings) - identische SQLite/PostgreSQL-Abstraktion wie
# im Rest der Anwendung, kein Secret im Repository. Ist bereits explizit
# eine sqlalchemy.url gesetzt (z. B. durch einen Test, der eine isolierte
# temporaere Datenbank verwenden moechte), wird diese respektiert und NICHT
# ueberschrieben.
if not config.get_main_option("sqlalchemy.url"):
    _database_url = get_settings().database_url
    _ensure_sqlite_directory_exists(_database_url)
    config.set_main_option("sqlalchemy.url", _database_url)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
