"""link legacy artist payments to their unambiguous season

Revision ID: c7814ae20b96
Revises: a64d7c1e93b2
"""
from alembic import op
import sqlalchemy as sa


revision = 'c7814ae20b96'
down_revision = 'a64d7c1e93b2'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    artists = sa.table(
        'artists',
        sa.column('id', sa.Integer()),
        sa.column('user_id', sa.Integer()),
        sa.column('payment_id', sa.Integer()),
        sa.column('is_paid', sa.Boolean()),
        sa.column('is_verified', sa.Boolean()),
    )
    songs = sa.table(
        'songs',
        sa.column('artist_id', sa.Integer()),
        sa.column('contest_id', sa.Integer()),
        sa.column('created_at', sa.DateTime()),
    )
    payments = sa.table(
        'payments',
        sa.column('id', sa.Integer()),
        sa.column('user_id', sa.Integer()),
        sa.column('contest_id', sa.Integer()),
        sa.column('status', sa.String(length=20)),
    )
    entries = sa.table(
        'contest_entries',
        sa.column('artist_id', sa.Integer()),
        sa.column('contest_id', sa.Integer()),
        sa.column('status', sa.String(length=30)),
        sa.column('is_paid', sa.Boolean()),
        sa.column('is_verified', sa.Boolean()),
        sa.column('created_at', sa.DateTime()),
        sa.column('updated_at', sa.DateTime()),
    )

    participation_rows = bind.execute(
        sa.select(
            artists.c.id,
            artists.c.user_id,
            artists.c.payment_id,
            artists.c.is_paid,
            artists.c.is_verified,
            songs.c.contest_id,
            songs.c.created_at,
        )
        .select_from(artists.join(songs, songs.c.artist_id == artists.c.id))
        .where(artists.c.payment_id.is_not(None))
    ).fetchall()

    participation = {}
    for artist_id, user_id, payment_id, is_paid, is_verified, contest_id, song_created_at in participation_rows:
        if payment_id is None or contest_id is None:
            continue
        key = (artist_id, user_id, payment_id)
        season = participation.setdefault(key, {})
        current = season.setdefault(contest_id, song_created_at)
        if song_created_at and (current is None or song_created_at < current):
            season[contest_id] = song_created_at

    for (artist_id, user_id, payment_id), seasons in participation.items():
        if len(seasons) != 1:
            continue
        contest_id, submitted_at = next(iter(seasons.items()))
        payment = bind.execute(
            sa.select(payments.c.user_id, payments.c.contest_id, payments.c.status)
            .where(payments.c.id == payment_id)
        ).first()
        if not payment or payment.user_id != user_id or payment.status != 'successful':
            continue
        if payment.contest_id not in (None, contest_id):
            continue

        if payment.contest_id is None:
            bind.execute(
                payments.update()
                .where(payments.c.id == payment_id)
                .values(contest_id=contest_id)
            )

        existing_entry = bind.execute(
            sa.select(entries.c.artist_id)
            .where(entries.c.artist_id == artist_id, entries.c.contest_id == contest_id)
        ).first()
        if not existing_entry:
            verified = bool(is_verified)
            bind.execute(entries.insert().values(
                artist_id=artist_id,
                contest_id=contest_id,
                status='approved' if verified else 'pending_approval',
                is_paid=bool(is_paid),
                is_verified=verified,
                created_at=submitted_at,
                updated_at=submitted_at,
            ))


def downgrade():
    pass
