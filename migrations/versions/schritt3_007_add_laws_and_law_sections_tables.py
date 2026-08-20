"""add laws and law_sections tables

Revision ID: schritt3_007
Revises: schritt3_006
Create Date: 2026-08-20 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'schritt3_007'
down_revision: Union[str, Sequence[str], None] = 'schritt3_006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'laws',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_table(
        'law_sections',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('law_code', sa.String(length=32), nullable=False),
        sa.Column('section_number', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=False),
        sa.Column('last_updated', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(['law_code'], ['laws.code']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('law_code', 'section_number', name='uq_law_sections_law_code_section_number'),
    )
    op.create_index(
        op.f('ix_law_sections_law_code'), 'law_sections', ['law_code'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_law_sections_law_code'), table_name='law_sections')
    op.drop_table('law_sections')
    op.drop_table('laws')
