"""add pilot_feedback table

Revision ID: schritt3_001
Revises: prompt43_001
Create Date: 2026-08-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'schritt3_001'
down_revision: Union[str, Sequence[str], None] = 'prompt43_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'pilot_feedback',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_by_actor', sa.String(length=128), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('system_context_json', sa.Text(), nullable=True),
        sa.Column('ai_suggested_category', sa.String(length=32), nullable=True),
        sa.Column('ai_confidence', sa.Float(), nullable=True),
        sa.Column('requires_admin_review', sa.Boolean(), nullable=False),
        sa.Column('review_status', sa.String(length=32), nullable=False),
        sa.Column('reviewed_by_actor', sa.String(length=128), nullable=True),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('pilot_feedback')
