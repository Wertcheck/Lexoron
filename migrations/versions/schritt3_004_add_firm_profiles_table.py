"""add firm_profiles table

Revision ID: schritt3_004
Revises: schritt3_003
Create Date: 2026-08-20 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'schritt3_004'
down_revision: Union[str, Sequence[str], None] = 'schritt3_003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'firm_profiles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('firm_name', sa.String(length=255), nullable=False),
        sa.Column('street', sa.String(length=255), nullable=True),
        sa.Column('postal_code', sa.String(length=32), nullable=True),
        sa.Column('city', sa.String(length=128), nullable=True),
        sa.Column('phone', sa.String(length=64), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('updated_by_actor', sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('firm_profiles')
