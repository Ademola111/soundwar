"""add user account status

Revision ID: 9d8b3a2c1f64
Revises: b71c4e86a9d20
"""
from alembic import op
import sqlalchemy as sa


revision = '9d8b3a2c1f64'
down_revision = 'b71c4e86a9d20'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true())
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_active')
