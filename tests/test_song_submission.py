from datetime import datetime, timedelta
from io import BytesIO

import pytest
from flask_jwt_extended import create_access_token

from soundwarapp import create_app, db
from soundwarapp.models import Artist, Contest, ContestEntry, Payment, Song, User, Vote


@pytest.fixture
def submission_client(tmp_path):
    app = create_app("testing")
    app.config.update(
        TESTING=True,
        SONG_UPLOAD_FOLDER=str(tmp_path),
        SONG_COVER_FOLDER=str(tmp_path / "covers"),
    )
    with app.app_context():
        db.create_all()
        user = User(
            email="artist@example.com",
            username="artist",
            name="Test Artist",
            password_hash="hashed",
            roles=["artist"],
        )
        db.session.add(user)
        db.session.commit()
        artist = Artist(user_id=user.id, stage_name="Test Artist", genre="Electronic", is_paid=True)
        contest = Contest(
            title="Current Contest",
            start_date=datetime.now() - timedelta(days=1),
            submission_end_date=datetime.now() + timedelta(days=1),
            voting_end_date=datetime.now() + timedelta(days=2),
        )
        db.session.add_all([artist, contest])
        db.session.commit()
        entry = ContestEntry(
            artist_id=artist.id,
            contest_id=contest.id,
            is_paid=True,
            is_verified=True,
            status='approved',
        )
        payment = Payment(
            user_id=user.id,
            contest_id=contest.id,
            transaction_id='tx-valid-1',
            tx_ref='valid-ref-1',
            amount=15000,
            currency='NGN',
            status='successful',
            payment_purpose='contest_registration',
        )
        db.session.add_all([entry, payment])
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        with app.test_client() as client:
            yield client, token, tmp_path
        db.session.remove()
        db.drop_all()


def test_submit_song_saves_mp3_and_returns_its_url(submission_client):
    client, token, upload_folder = submission_client

    response = client.post(
        "/api/songs/submit",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "My Track",
            "duration": "185",
            "audio_file": (BytesIO(b"mp3 data"), "track.mp3", "audio/mpeg"),
            "cover_file": (BytesIO(b"cover image"), "cover.jpg", "image/jpeg"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201, response.get_data(as_text=True)
    body = response.get_json()
    assert body["song"]["title"] == "My Track"
    assert body["song"]["duration"] == 185
    assert body["song"]["artist"]["genre"] == "Electronic"
    assert body["song"]["audio_url"].endswith(".mp3")
    assert body["song"]["cover_image"].endswith(".jpg")
    saved_files = [path for path in upload_folder.iterdir() if path.is_file()]
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == b"mp3 data"
    saved_covers = list((upload_folder / "covers").iterdir())
    assert len(saved_covers) == 1
    assert saved_covers[0].read_bytes() == b"cover image"


def test_submit_song_rejects_non_mp3_files(submission_client):
    client, token, upload_folder = submission_client

    response = client.post(
        "/api/songs/submit",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "My Track",
            "duration": "185",
            "audio_file": (BytesIO(b"not mp3"), "track.wav"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Only MP3 files are allowed"
    assert list(upload_folder.iterdir()) == []


def test_submit_song_requires_duration(submission_client):
    client, token, upload_folder = submission_client

    response = client.post(
        "/api/songs/submit",
        headers={"Authorization": f"Bearer {token}"},
        data={"title": "My Track", "audio_file": (BytesIO(b"mp3 data"), "track.mp3")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Song duration is required"
    assert list(upload_folder.iterdir()) == []


def test_submit_song_rejects_unsupported_cover_art(submission_client):
    client, token, upload_folder = submission_client

    response = client.post(
        "/api/songs/submit",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "My Track",
            "duration": "185",
            "audio_file": (BytesIO(b"mp3 data"), "track.mp3"),
            "cover_file": (BytesIO(b"not an image"), "cover.gif", "image/gif"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Cover art must be a JPG, PNG, or WebP image"
    assert list(upload_folder.iterdir()) == []


def test_submit_song_uses_dates_instead_of_stale_contest_phase(submission_client):
    client, token, upload_folder = submission_client
    with client.application.app_context():
        contest = Contest.query.first()
        contest.phase = "submission"
        contest.submission_end_date = datetime.now() - timedelta(days=1)
        contest.voting_end_date = datetime.now() + timedelta(days=1)
        db.session.commit()

    response = client.post(
        "/api/songs/submit",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "Late Track",
            "duration": "185",
            "audio_file": (BytesIO(b"mp3 data"), "track.mp3"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Contest is not accepting submissions"
    assert list(upload_folder.iterdir()) == []


def test_artist_requires_new_contest_entry_before_submitting_again():
    app = create_app("testing")
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        user = User(
            email="season@example.com",
            username="seasonartist",
            name="Season Artist",
            password_hash="hashed",
            roles=["artist"],
        )
        db.session.add(user)
        db.session.commit()
        artist = Artist(user_id=user.id, stage_name="Season Artist")
        first_contest = Contest(
            title="Season One",
            start_date=datetime.now() - timedelta(days=20),
            submission_end_date=datetime.now() + timedelta(days=5),
            voting_end_date=datetime.now() + timedelta(days=10),
            is_active=True,
        )
        second_contest = Contest(
            title="Season Two",
            start_date=datetime.now() - timedelta(days=5),
            submission_end_date=datetime.now() + timedelta(days=20),
            voting_end_date=datetime.now() + timedelta(days=30),
            is_active=False,
        )
        db.session.add_all([artist, first_contest, second_contest])
        db.session.commit()
        db.session.add(ContestEntry(
            artist_id=artist.id,
            contest_id=first_contest.id,
            is_paid=True,
            is_verified=True,
            status="approved",
        ))
        db.session.add(Payment(
            user_id=user.id,
            contest_id=first_contest.id,
            transaction_id='tx-season-1',
            tx_ref='season-ref-1',
            amount=15000,
            currency='NGN',
            status='successful',
            payment_purpose='contest_registration',
        ))
        db.session.commit()

        assert artist.has_paid_for_contest(first_contest) is True
        assert artist.has_paid_for_contest(second_contest) is False

        first_contest.is_active = False
        second_contest.is_active = True
        db.session.commit()

        with app.test_client() as client:
            token = create_access_token(identity=str(user.id))
            response = client.post(
                "/api/songs/submit",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "title": "Season Two Track",
                    "duration": "185",
                    "audio_file": (BytesIO(b"mp3 data"), "track.mp3"),
                },
                content_type="multipart/form-data",
            )

            assert response.status_code == 403
            assert response.get_json()["error"] == "Payment required for this contest season"

            second_entry = ContestEntry(
                artist_id=artist.id,
                contest_id=second_contest.id,
                is_paid=True,
                is_verified=True,
                status="approved",
            )
            db.session.add_all([
                second_entry,
                Payment(
                    user_id=user.id,
                    contest_id=second_contest.id,
                    transaction_id='tx-season-2',
                    tx_ref='season-ref-2',
                    amount=15000,
                    currency='NGN',
                    status='successful',
                    payment_purpose='contest_registration',
                ),
            ])
            db.session.commit()

            assert artist.has_paid_for_contest(second_contest) is True

            response = client.post(
                "/api/songs/submit",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "title": "Season Two Track",
                    "duration": "185",
                    "audio_file": (BytesIO(b"mp3 data"), "track.mp3"),
                },
                content_type="multipart/form-data",
            )

            assert response.status_code == 201
            assert response.get_json()["song"]["title"] == "Season Two Track"

        db.drop_all()


def test_user_can_update_profile_picture_and_details():
    app = create_app("testing")
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        user = User(
            email="profile@example.com",
            username="profileuser",
            name="Old Name",
            password_hash="hashed",
            roles=['user'],
        )
        db.session.add(user)
        db.session.commit()

        with app.test_client() as client:
            token = create_access_token(identity=str(user.id))
            response = client.put(
                "/api/auth/profile",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "name": "Updated Name",
                    "username": "profileuser2",
                    "profile_image": "https://example.com/avatar.png",
                },
            )

            assert response.status_code == 200
            body = response.get_json()
            assert body["user"]["name"] == "Updated Name"
            assert body["user"]["username"] == "profileuser2"
            assert body["user"]["profile_image"] == "https://example.com/avatar.png"

        db.drop_all()


def test_user_profile_includes_vote_history_and_count():
    app = create_app("testing")
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        user = User(
            email="voter@example.com",
            username="voter123",
            name="Voter User",
            password_hash="hashed",
            roles=['user'],
        )
        artist = Artist(user_id=1, stage_name="Vote Artist")
        contest = Contest(
            title="Season Profile Vote",
            start_date=datetime.now() - timedelta(days=10),
            submission_end_date=datetime.now() - timedelta(days=1),
            voting_end_date=datetime.now() + timedelta(days=5),
            is_active=True,
            phase='voting',
        )
        db.session.add_all([user, artist, contest])
        db.session.commit()

        artist.user_id = user.id
        song = Song(
            artist_id=artist.id,
            contest_id=contest.id,
            title='Profile Song',
            audio_url='https://example.com/song.mp3',
            duration=180,
            status='approved',
            vote_count=1,
        )
        db.session.add(song)
        db.session.commit()

        vote = Vote(user_id=user.id, song_id=song.id, contest_id=contest.id)
        db.session.add(vote)
        db.session.commit()

        with app.test_client() as client:
            token = create_access_token(identity=str(user.id))
            profile_response = client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert profile_response.status_code == 200
            assert profile_response.get_json()['user']['votes_cast'] == 1
            assert profile_response.get_json()['user']['vote_history'][0]['artist_name'] == 'Vote Artist'

            history_response = client.get(
                "/api/votes/my-history",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert history_response.status_code == 200
            assert history_response.get_json()['votes'][0]['song_title'] == 'Profile Song'
            assert history_response.get_json()['votes'][0]['contest_title'] == 'Season Profile Vote'

        db.drop_all()