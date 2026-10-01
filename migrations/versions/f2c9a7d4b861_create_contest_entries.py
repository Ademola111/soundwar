"""create contest entries for season registrations

Revision ID: f2c9a7d4b861
Revises: e18a4b9c2d71
"""
from alembic import op
import sqlalchemy as sa


revision = 'f2c9a7d4b861'
down_revision = 'e18a4b9c2d71'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'contest_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_id', sa.Integer(), nullable=False),
        sa.Column('contest_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='pending_payment', nullable=True),
        sa.Column('is_paid', sa.Boolean(), server_default=sa.false(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), server_default=sa.false(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['artist_id'], ['artists.id'], name='fk_contest_entries_artist_id_artists'),
        sa.ForeignKeyConstraint(['contest_id'], ['contests.id'], name='fk_contest_entries_contest_id_contests'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('artist_id', 'contest_id', name='uq_artist_contest_entry'),
    )


def downgrade():
    op.drop_table('contest_entries')
