"""add account activation fields

Revision ID: c4b2f0e4a1d7
Revises: 7fc284ac41da
"""
from alembic import op
import sqlalchemy as sa


revision = 'c4b2f0e4a1d7'
down_revision = '7fc284ac41da'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('activation_token', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('activation_token_expires', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('activation_token_expires')
        batch_op.drop_column('activation_token')
        batch_op.drop_column('email_verified')