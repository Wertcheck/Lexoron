"""seed default roles admin anwalt mitarbeiter

Revision ID: 4e15e8bb50a1
Revises: 0583e452e69c
Create Date: 2026-08-15 07:58:09.760520

"""
"""Seed-Daten statt fest verdrahteter Rollenlogik im Code (siehe
app/models/role.py) - die drei vom Anwalt vorgegebenen Rollen werden hier
als gewöhnliche Datenbankzeilen angelegt, damit spätere kanzleispezifische
Rollen ohne Codeänderung ergänzt werden können.

Verwendet `sa.table`/`sa.column` statt der ORM-Modelle (Alembic-
Empfehlung) - Migrationen dürfen nicht von einem sich später ändernden
ORM-Modell abhängen.
"""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4e15e8bb50a1'
down_revision: Union[str, Sequence[str], None] = '0583e452e69c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Feste UUIDs (nicht bei jedem Migrationslauf neu erzeugt) - macht die
# Migration deterministisch wiederholbar/nachvollziehbar.
_ADMIN_ID = "11111111-1111-4111-8111-111111111111"
_ANWALT_ID = "22222222-2222-4222-8222-222222222222"
_MITARBEITER_ID = "33333333-3333-4333-8333-333333333333"

roles_table = sa.table(
    "roles",
    sa.column("id", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
)


def upgrade() -> None:
    """Upgrade schema."""
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        roles_table,
        [
            {
                "id": _ADMIN_ID,
                "name": "Admin",
                "description": (
                    "Vollständiger Zugriff inkl. Nutzer- und Rollenverwaltung, "
                    "siehe app/auth/permissions.py"
                ),
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": _ANWALT_ID,
                "name": "Anwalt",
                "description": "Vollständiger fachlicher Workflow, keine Nutzerverwaltung",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": _MITARBEITER_ID,
                "name": "Mitarbeiter",
                "description": (
                    "Lesen, Anmerkungen erstellen, manuelle Bearbeitung - keine "
                    "Freigabe/Neugenerierung/Versand"
                ),
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        roles_table.delete().where(
            roles_table.c.id.in_([_ADMIN_ID, _ANWALT_ID, _MITARBEITER_ID])
        )
    )
