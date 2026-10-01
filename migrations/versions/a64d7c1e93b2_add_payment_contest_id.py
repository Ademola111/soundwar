"""add contest association to payments

Revision ID: a64d7c1e93b2
Revises: f2c9a7d4b861
"""
from alembic import op
import sqlalchemy as sa


revision = 'a64d7c1e93b2'
down_revision = 'f2c9a7d4b861'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('payments', sa.Column('contest_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_payments_contest_id_contests',
        'payments',
        'contests',
        ['contest_id'],
        ['id'],
    )

    bind = op.get_bind()
    payments = sa.table(
        'payments',
        sa.column('contest_id', sa.Integer()),
        sa.column('verified_at', sa.DateTime()),
        sa.column('created_at', sa.DateTime()),
    )
    contests = sa.table(
        'contests',
        sa.column('id', sa.Integer()),
        sa.column('start_date', sa.DateTime()),
        sa.column('voting_end_date', sa.DateTime()),
    )
    seasons = bind.execute(
        sa.select(
            contests.c.id,
            contests.c.start_date,
            contests.c.voting_end_date,
        ).order_by(contests.c.start_date.desc())
    ).fetchall()
    payment_timestamp = sa.func.coalesce(payments.c.verified_at, payments.c.created_at)

    for contest_id, start_date, voting_end_date in seasons:
        if start_date and voting_end_date and start_date < voting_end_date:
            bind.execute(
                payments.update()
                .where(
                    payments.c.contest_id.is_(None),
                    payment_timestamp >= start_date,
                    payment_timestamp <= voting_end_date,
                )
                .values(contest_id=contest_id)
            )


def downgrade():
    op.drop_constraint('fk_payments_contest_id_contests', 'payments', type_='foreignkey')
    op.drop_column('payments', 'contest_id')
