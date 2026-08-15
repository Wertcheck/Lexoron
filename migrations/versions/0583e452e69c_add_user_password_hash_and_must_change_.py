"""add user password hash and must_change_password

Revision ID: 0583e452e69c
Revises: ceabf73d4cf4
Create Date: 2026-08-15 07:57:49.422638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0583e452e69c'
down_revision: Union[str, Sequence[str], None] = 'ceabf73d4cf4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Batch-Modus + server_default: SQLite erfordert fuer eine NOT-NULL-
    # Spalte ohne Default einen Wert fuer eventuell vorhandene Zeilen -
    # server_default sorgt dafuer, dass bestehende User-Zeilen (falls
    # vorhanden) einen gueltigen Wert erhalten, statt die Migration
    # fehlschlagen zu lassen.
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("password_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("must_change_password")
        batch_op.drop_column("password_hash")
