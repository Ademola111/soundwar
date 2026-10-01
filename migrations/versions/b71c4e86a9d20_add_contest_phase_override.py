"""add explicit admin phase override to contests

Revision ID: b71c4e86a9d20
Revises: c7814ae20b96
"""
from alembic import op
import sqlalchemy as sa


revision = 'b71c4e86a9d20'
down_revision = 'c7814ae20b96'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'contests',
        sa.Column('phase_override', sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade():
    op.drop_column('contests', 'phase_override')
