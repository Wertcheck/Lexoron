"""add draft_quality_ratings table

Revision ID: prompt43_001
Revises: 5ce0d7e04699
Create Date: 2026-08-17 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'prompt43_001'
# War zuvor None ("wird vom User gesetzt nach bisherigem Stand") - erzeugte
# einen zweiten, unverbundenen Migrations-Head statt an die bestehende Kette
# anzuknuepfen ("Multiple head revisions"). Gefunden+behoben im Zuge von
# Prompt 46 (auf ausdruecklichen Wunsch, siehe ARCHITECTURE.md): 5ce0d7e04699
# war zu diesem Zeitpunkt der einzige andere Kettenkopf (Prompt 35, letzte
# committete Migration).
down_revision: Union[str, Sequence[str], None] = '5ce0d7e04699'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('draft_quality_ratings',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('draft_id', sa.String(), nullable=False),
    sa.Column('rated_by_user_id', sa.String(), nullable=False),
    sa.Column('content_quality', sa.Integer(), nullable=True),
    sa.Column('usefulness', sa.Integer(), nullable=True),
    sa.Column('completeness', sa.Integer(), nullable=True),
    sa.Column('language_quality', sa.Integer(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['draft_id'], ['drafts.id'], ),
    sa.ForeignKeyConstraint(['rated_by_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_draft_quality_ratings_draft_id'), 'draft_quality_ratings', ['draft_id'], unique=False)
    op.create_index(op.f('ix_draft_quality_ratings_rated_by_user_id'), 'draft_quality_ratings', ['rated_by_user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_draft_quality_ratings_rated_by_user_id'), table_name='draft_quality_ratings')
    op.drop_index(op.f('ix_draft_quality_ratings_draft_id'), table_name='draft_quality_ratings')
    op.drop_table('draft_quality_ratings')
