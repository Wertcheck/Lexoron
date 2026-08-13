"""extend knowledge_items with source and validity range

Revision ID: b6a73935d3bb
Revises: af613a5a969a
Create Date: 2026-08-13 21:20:25.234108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6a73935d3bb'
down_revision: Union[str, Sequence[str], None] = 'af613a5a969a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite unterstuetzt kein direktes ALTER von Constraints - Batch-Modus
    # noetig (kopiert Tabelle intern um), siehe SQLAlchemy-Dokumentation.
    with op.batch_alter_table('knowledge_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('valid_from', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('valid_until', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('created_by_user_id', sa.String(), nullable=True))
        batch_op.create_foreign_key(
            'fk_knowledge_items_created_by_user_id', 'users', ['created_by_user_id'], ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('knowledge_items', schema=None) as batch_op:
        batch_op.drop_constraint('fk_knowledge_items_created_by_user_id', type_='foreignkey')
        batch_op.drop_column('created_by_user_id')
        batch_op.drop_column('valid_until')
        batch_op.drop_column('valid_from')
        batch_op.drop_column('source')
