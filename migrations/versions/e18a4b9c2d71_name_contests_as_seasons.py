"""rename contest titles to sequential season names

Revision ID: e18a4b9c2d71
Revises: d91f8e2b7c40
"""
from alembic import op
import sqlalchemy as sa


revision = 'e18a4b9c2d71'
down_revision = 'd91f8e2b7c40'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    contests = sa.table(
        'contests',
        sa.column('id', sa.Integer),
        sa.column('title', sa.String(length=200)),
        sa.column('start_date', sa.DateTime()),
    )
    rows = bind.execute(
        sa.select(contests.c.id).order_by(contests.c.start_date, contests.c.id)
    ).fetchall()

    for season_number, (contest_id,) in enumerate(rows, start=1):
        bind.execute(
            contests.update()
            .where(contests.c.id == contest_id)
            .values(title=f'Season {season_number}')
        )


def downgrade():
    pass
