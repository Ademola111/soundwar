"""add missing user profile image field

Revision ID: d91f8e2b7c40
Revises: c4b2f0e4a1d7
"""
from alembic import op
import sqlalchemy as sa


revision = 'd91f8e2b7c40'
down_revision = 'c4b2f0e4a1d7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_image', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('profile_image')
