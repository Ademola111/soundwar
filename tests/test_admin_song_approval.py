from datetime import datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from soundwarapp import create_app, db
from soundwarapp.models import Artist, Contest, Song, User


@pytest.fixture
def admin_song_client():
    app = create_app("testing")
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        admin = User(
            email="admin@example.com",
            username="adminuser",
            name="Admin User",
            password_hash="hashed",
            roles=["admin"],
        )
        db.session.add(admin)
        db.session.commit()
        artist = Artist(user_id=admin.id, stage_name="Test Artist", is_paid=True)
        contest = Contest(
            title="Current Contest",
            start_date=datetime.now() - timedelta(days=1),
            submission_end_date=datetime.now() + timedelta(days=1),
            voting_end_date=datetime.now() + timedelta(days=2),
        )
        db.session.add_all([artist, contest])
        db.session.commit()
        song = Song(
            artist_id=artist.id,
            contest_id=contest.id,
            title="Pending Track",
            audio_url="http://localhost/static/songs/pending.mp3",
            status="pending",
        )
        db.session.add(song)
        db.session.commit()
        token = create_access_token(identity=str(admin.id))
        with app.test_client() as client:
            yield client, token, song.id
        db.session.remove()
        db.drop_all()


def test_admin_can_approve_pending_song_without_form_csrf_token(admin_song_client):
    client, token, song_id = admin_song_client

    response = client.post(
        f"/api/admin/songs/{song_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.is_json
    assert response.get_json()["song"]["status"] == "approved"


def test_admin_can_reject_pending_song_without_form_csrf_token(admin_song_client):
    client, token, song_id = admin_song_client

    response = client.post(
        f"/api/admin/songs/{song_id}/reject",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Please provide a higher quality recording."},
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.is_json
    assert response.get_json()["song"]["status"] == "rejected"