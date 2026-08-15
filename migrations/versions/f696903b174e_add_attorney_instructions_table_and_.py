"""add attorney_instructions table and draft previous_version_id

Revision ID: f696903b174e
Revises: 60e278bf1d25
Create Date: 2026-08-15 01:08:42.646234

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f696903b174e'
down_revision: Union[str, Sequence[str], None] = '60e278bf1d25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('attorney_instructions',
    sa.Column('matter_id', sa.String(), nullable=False),
    sa.Column('draft_id', sa.String(), nullable=False),
    sa.Column('instruction_text', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('resulting_draft_id', sa.String(), nullable=True),
    sa.Column('actor', sa.String(length=128), nullable=False),
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['draft_id'], ['drafts.id'], ),
    sa.ForeignKeyConstraint(['matter_id'], ['matters.id'], ),
    sa.ForeignKeyConstraint(['resulting_draft_id'], ['drafts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attorney_instructions_draft_id'), 'attorney_instructions', ['draft_id'], unique=False)
    op.create_index(op.f('ix_attorney_instructions_matter_id'), 'attorney_instructions', ['matter_id'], unique=False)
    # Batch-Modus: SQLite unterstuetzt kein direktes ALTER TABLE ADD
    # CONSTRAINT - Alembic baut die Tabelle stattdessen in einer Batch-
    # Operation neu auf. Fuer PostgreSQL (Produktion) waere ein direktes
    # ALTER TABLE moeglich, batch_alter_table funktioniert aber
    # gleichermassen dort (kein Nachteil, siehe Alembic-Doku).
    with op.batch_alter_table('drafts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('previous_version_id', sa.String(), nullable=True))
        batch_op.create_index(op.f('ix_drafts_previous_version_id'), ['previous_version_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_drafts_previous_version_id_drafts', 'drafts', ['previous_version_id'], ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('drafts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_drafts_previous_version_id_drafts', type_='foreignkey')
        batch_op.drop_index(op.f('ix_drafts_previous_version_id'))
        batch_op.drop_column('previous_version_id')
    op.drop_index(op.f('ix_attorney_instructions_matter_id'), table_name='attorney_instructions')
    op.drop_index(op.f('ix_attorney_instructions_draft_id'), table_name='attorney_instructions')
    op.drop_table('attorney_instructions')
