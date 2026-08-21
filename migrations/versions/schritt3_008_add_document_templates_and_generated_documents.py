"""add document_templates and generated_documents tables

Revision ID: schritt3_008
Revises: schritt3_007
Create Date: 2026-08-20 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'schritt3_008'
down_revision: Union[str, Sequence[str], None] = 'schritt3_007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'document_templates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_by_actor', sa.String(length=128), nullable=True),
        sa.Column('updated_by_actor', sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'generated_documents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('template_id', sa.String(), nullable=True),
        sa.Column('matter_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('unresolved_placeholders_json', sa.Text(), nullable=True),
        sa.Column('created_by_actor', sa.String(length=128), nullable=True),
        sa.Column('updated_by_actor', sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['document_templates.id']),
        sa.ForeignKeyConstraint(['matter_id'], ['matters.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_generated_documents_template_id'), 'generated_documents', ['template_id'], unique=False
    )
    op.create_index(
        op.f('ix_generated_documents_matter_id'), 'generated_documents', ['matter_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_generated_documents_matter_id'), table_name='generated_documents')
    op.drop_index(op.f('ix_generated_documents_template_id'), table_name='generated_documents')
    op.drop_table('generated_documents')
    op.drop_table('document_templates')
