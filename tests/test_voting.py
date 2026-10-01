from datetime import datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from soundwarapp import create_app, db
from soundwarapp.models import Artist, Contest, Song, User, Vote


@pytest.fixture
def voting_client():
    app = create_app("testing")
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        user = User(
            email="contestant@example.com",
            username="contestant",
            name="Contestant",
            password_hash="hashed",
            roles=["artist"],
        )
        db.session.add(user)
        db.session.commit()
        artist = Artist(user_id=user.id, stage_name="Contestant Artist", is_paid=True)
        now = datetime.now()
        contest = Contest(
            title="Voting Contest",
            start_date=now - timedelta(days=3),
            submission_end_date=now - timedelta(days=1),
            voting_end_date=now + timedelta(days=1),
        )
        db.session.add_all([artist, contest])
        db.session.commit()
        song = Song(
            artist_id=artist.id,
            contest_id=contest.id,
            title="Artist's Own Song",
            audio_url="http://localhost/static/songs/own.mp3",
            status="approved",
        )
        db.session.add(song)
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        with app.test_client() as client:
            yield client, token, song.id, user.id, contest.id
        db.session.remove()
        db.drop_all()


def test_artist_can_vote_for_own_song_once(voting_client):
    client, token, song_id, user_id, contest_id = voting_client
    headers = {"Authorization": f"Bearer {token}"}

    first_vote = client.post(
        "/api/votes/cast",
        headers=headers,
        json={"song_id": song_id},
    )
    assert first_vote.status_code == 201, first_vote.get_data(as_text=True)

    second_vote = client.post(
        "/api/votes/cast",
        headers=headers,
        json={"song_id": song_id},
    )
    assert second_vote.status_code == 409

    with client.application.app_context():
        assert Vote.query.filter_by(user_id=user_id, contest_id=contest_id).count() == 1
        assert Song.query.get(song_id).vote_count == 1

    vote_status = client.get("/api/votes/my-vote", headers=headers)
    assert vote_status.status_code == 200
    assert vote_status.get_json()["vote"]["song_id"] == song_id


def test_artist_can_vote_once_again_in_next_contest_season(voting_client):
    client, token, first_song_id, user_id, first_contest_id = voting_client
    headers = {"Authorization": f"Bearer {token}"}

    first_vote = client.post(
        "/api/votes/cast",
        headers=headers,
        json={"song_id": first_song_id},
    )
    assert first_vote.status_code == 201

    with client.application.app_context():
        first_contest = Contest.query.get(first_contest_id)
        first_contest.is_active = False
        now = datetime.now()
        first_song = Song.query.get(first_song_id)
        next_contest = Contest(
            title="Next Season",
            start_date=now - timedelta(days=60),
            submission_end_date=now - timedelta(days=30),
            voting_end_date=now + timedelta(days=30),
        )
        next_song = Song(
            artist_id=first_song.artist_id,
            contest=next_contest,
            title="Next Season Song",
            audio_url="http://localhost/static/songs/next.mp3",
            status="approved",
        )
        db.session.add_all([next_contest, next_song])
        db.session.commit()
        next_song_id = next_song.id

    old_season_vote = client.post(
        "/api/votes/cast",
        headers=headers,
        json={"song_id": first_song_id},
    )
    assert old_season_vote.status_code == 400

    vote_status = client.get("/api/votes/my-vote", headers=headers)
    assert vote_status.status_code == 200
    assert vote_status.get_json()["vote"] is None

    next_vote = client.post(
        "/api/votes/cast",
        headers=headers,
        json={"song_id": next_song_id},
    )
    assert next_vote.status_code == 201, next_vote.get_data(as_text=True)

    with client.application.app_context():
        assert Vote.query.filter_by(user_id=user_id).count() == 2