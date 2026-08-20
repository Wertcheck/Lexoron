"""add logo/signature fields to firm_profiles

Revision ID: schritt3_005
Revises: schritt3_004
Create Date: 2026-08-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'schritt3_005'
down_revision: Union[str, Sequence[str], None] = 'schritt3_004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('firm_profiles', sa.Column('signatory_name', sa.String(length=255), nullable=True))
    op.add_column('firm_profiles', sa.Column('logo_path', sa.String(length=1024), nullable=True))
    op.add_column('firm_profiles', sa.Column('logo_original_filename', sa.String(length=255), nullable=True))
    op.add_column('firm_profiles', sa.Column('signature_path', sa.String(length=1024), nullable=True))
    op.add_column('firm_profiles', sa.Column('signature_original_filename', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('firm_profiles', 'signature_original_filename')
    op.drop_column('firm_profiles', 'signature_path')
    op.drop_column('firm_profiles', 'logo_original_filename')
    op.drop_column('firm_profiles', 'logo_path')
    op.drop_column('firm_profiles', 'signatory_name')
