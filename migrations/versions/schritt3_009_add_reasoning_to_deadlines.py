"""add reasoning to deadlines

Revision ID: schritt3_009
Revises: schritt3_008
Create Date: 2026-08-20 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'schritt3_009'
down_revision: Union[str, Sequence[str], None] = 'schritt3_008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('deadlines', sa.Column('reasoning', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('deadlines', 'reasoning')
