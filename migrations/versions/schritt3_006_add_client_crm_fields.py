"""add crm fields (practice_area, status, responsible_user_id) to clients

Revision ID: schritt3_006
Revises: schritt3_005
Create Date: 2026-08-20 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'schritt3_006'
down_revision: Union[str, Sequence[str], None] = 'schritt3_005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite unterstuetzt kein direktes ALTER von Constraints - Batch-Modus
    # noetig (kopiert Tabelle intern um), siehe b6a73935d3bb fuer dasselbe
    # Muster (created_by_user_id auf knowledge_items).
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('practice_area', sa.String(length=128), nullable=True))
        batch_op.add_column(
            sa.Column('status', sa.String(length=32), nullable=False, server_default='active')
        )
        batch_op.add_column(sa.Column('responsible_user_id', sa.String(), nullable=True))
        batch_op.create_index(
            op.f('ix_clients_responsible_user_id'), ['responsible_user_id'], unique=False
        )
        batch_op.create_foreign_key(
            'fk_clients_responsible_user_id_users', 'users', ['responsible_user_id'], ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.drop_constraint('fk_clients_responsible_user_id_users', type_='foreignkey')
        batch_op.drop_index(op.f('ix_clients_responsible_user_id'))
        batch_op.drop_column('responsible_user_id')
        batch_op.drop_column('status')
        batch_op.drop_column('practice_area')
