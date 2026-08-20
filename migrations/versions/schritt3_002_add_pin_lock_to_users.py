"""add pin_hash and is_locked to users

Revision ID: schritt3_002
Revises: schritt3_001
Create Date: 2026-08-20 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'schritt3_002'
down_revision: Union[str, Sequence[str], None] = 'schritt3_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('pin_hash', sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('is_locked')
        batch_op.drop_column('pin_hash')
