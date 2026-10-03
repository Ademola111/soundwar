from datetime import datetime, timedelta

import pytest
from flask_jwt_extended import create_access_token

from soundwarapp import create_app, db
from soundwarapp.models import Artist, Contest, ContestEntry, Payment, Song, User, Vote


@pytest.fixture

def admin_dashboard_client():
    app = create_app("testing")
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        admin = User(
            email="dashboard-admin@example.com",
            username="dashboardadmin",
            name="Dashboard Admin",
            password_hash="hashed",
            roles=["admin"],
        )
        artist_user = User(
            email="dashboard-artist@example.com",
            username="dashboardartist",
            name="Dashboard Artist",
            password_hash="hashed",
            roles=["artist"],
        )
        voter = User(
            email="dashboard-voter@example.com",
            username="dashboardvoter",
            name="Dashboard Voter",
            password_hash="hashed",
            roles=["user"],
        )
        db.session.add_all([admin, artist_user, voter])
        db.session.commit()

        artist = Artist(user_id=artist_user.id, stage_name="Live Artist", is_paid=True)
        now = datetime.now()
        contest = Contest(
            title="Live Contest",
            start_date=now - timedelta(days=5),
            submission_end_date=now + timedelta(days=2),
            voting_end_date=now + timedelta(days=32),
            is_active=True,
        )
        previous_contest = Contest(
            title="Previous Contest",
            start_date=now - timedelta(days=60),
            submission_end_date=now - timedelta(days=55),
            voting_end_date=now - timedelta(days=50),
            is_active=False,
        )
        db.session.add_all([artist, contest, previous_contest])
        db.session.commit()

        current_song = Song(
            artist_id=artist.id,
            contest_id=contest.id,
            title="Live Song",
            audio_url="http://localhost/static/songs/live.mp3",
            status="approved",
            vote_count=1,
        )
        current_pending_song = Song(
            artist_id=artist.id,
            contest_id=contest.id,
            title="Current Pending Song",
            audio_url="http://localhost/static/songs/current-pending.mp3",
            status="pending",
            vote_count=0,
        )
        previous_song = Song(
            artist_id=artist.id,
            contest_id=previous_contest.id,
            title="Previous Season Song",
            audio_url="http://localhost/static/songs/previous.mp3",
            status="pending",
            vote_count=4,
        )
        current_entry = ContestEntry(
            artist_id=artist.id,
            contest_id=contest.id,
            status="approved",
            is_paid=True,
            is_verified=True,
        )
        previous_entry = ContestEntry(
            artist_id=artist.id,
            contest_id=previous_contest.id,
            status="approved",
            is_paid=True,
            is_verified=True,
        )
        payment = Payment(
            user_id=artist_user.id,
            contest_id=contest.id,
            transaction_id="dashboard-transaction",
            tx_ref="dashboard-reference",
            amount=15000,
            currency="NGN",
            status="successful",
            verified_at=datetime.now(),
        )
        previous_payment = Payment(
            user_id=artist_user.id,
            contest_id=previous_contest.id,
            transaction_id="previous-dashboard-transaction",
            tx_ref="previous-dashboard-reference",
            amount=9000,
            currency="NGN",
            status="successful",
            verified_at=now - timedelta(days=52),
        )
        db.session.add_all([
            current_song,
            current_pending_song,
            previous_song,
            current_entry,
            previous_entry,
            payment,
            previous_payment,
        ])
        db.session.commit()
        db.session.add_all([
            Vote(user_id=voter.id, song_id=current_song.id, contest_id=contest.id),
            Vote(user_id=voter.id, song_id=previous_song.id, contest_id=previous_contest.id),
        ])
        db.session.commit()

        token = create_access_token(identity=str(admin.id))
        with app.test_client() as client:
            yield client, token
        db.session.remove()
        db.drop_all()


def test_admin_dashboard_users_and_analytics_use_database_records(admin_dashboard_client):
    client, token = admin_dashboard_client
    headers = {"Authorization": f"Bearer {token}"}

    dashboard_response = client.get("/api/admin/dashboard", headers=headers)
    users_response = client.get("/api/admin/users", headers=headers)
    analytics_response = client.get("/api/admin/analytics", headers=headers)
    pending_response = client.get("/api/admin/songs/pending", headers=headers)

    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.get_json()
    assert dashboard["stats"]["total_users"] == 3
    assert dashboard["stats"]["total_artists"] == 1
    assert dashboard["stats"]["total_songs"] == 2
    assert dashboard["stats"]["pending_songs"] == 1
    assert dashboard["stats"]["approved_songs"] == 1
    assert dashboard["stats"]["total_votes"] == 1
    assert dashboard["stats"]["total_payments"] == 1
    assert dashboard["stats"]["total_revenue"] == 15000
    assert dashboard["current_contest"]["title"] == "Live Contest"
    assert dashboard["recent_activity"]

    assert users_response.status_code == 200
    users = users_response.get_json()["users"]
    artist = next(user for user in users if user["username"] == "dashboardartist")
    assert artist["status"] == "active"
    assert artist["is_active"] is True
    assert artist["songs_count"] == 2
    assert artist["votes_received"] == 1
    voter = next(user for user in users if user["username"] == "dashboardvoter")
    assert voter["votes_cast"] == 1

    assert pending_response.status_code == 200
    pending_songs = pending_response.get_json()["songs"]
    assert [song["title"] for song in pending_songs] == ["Current Pending Song"]

    assert analytics_response.status_code == 200
    analytics = analytics_response.get_json()
    assert len(analytics["daily_votes"]) == 7
    assert sum(day["votes"] for day in analytics["daily_votes"]) == 1
    assert analytics["top_songs"][0]["title"] == "Live Song"
    assert analytics["registration_trend"]["artists_this_week"] == 1
    assert analytics["contest_revenue"] == 15000


def test_admin_can_activate_and_deactivate_user_accounts(admin_dashboard_client):
    client, token = admin_dashboard_client
    headers = {"Authorization": f"Bearer {token}"}
    users = client.get("/api/admin/users", headers=headers).get_json()["users"]
    voter = next(user for user in users if user["username"] == "dashboardvoter")
    voter_token = create_access_token(identity=str(voter["id"]))
    voter_headers = {"Authorization": f"Bearer {voter_token}"}

    deactivate_response = client.put(
        f"/api/admin/users/{voter['id']}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.get_json()["user"]["is_active"] is False
    assert client.get("/api/admin/users", headers=voter_headers).status_code == 401

    updated_users = client.get("/api/admin/users", headers=headers).get_json()["users"]
    updated_voter = next(user for user in updated_users if user["id"] == voter["id"])
    assert updated_voter["is_active"] is False

    activate_response = client.put(
        f"/api/admin/users/{voter['id']}/status",
        headers=headers,
        json={"is_active": True},
    )
    assert activate_response.status_code == 200
    assert activate_response.get_json()["user"]["is_active"] is True

    invalid_response = client.put(
        f"/api/admin/users/{voter['id']}/status",
        headers=headers,
        json={"is_active": "false"},
    )
    assert invalid_response.status_code == 400


def test_admin_can_list_and_update_payment_status(admin_dashboard_client):
    client, token = admin_dashboard_client
    headers = {"Authorization": f"Bearer {token}"}

    list_response = client.get("/api/admin/payments", headers=headers)
    assert list_response.status_code == 200
    payments = list_response.get_json()["payments"]
    payment = next(record for record in payments if record["tx_ref"] == "dashboard-reference")
    assert payment["user"]["username"] == "dashboardartist"

    update_response = client.put(
        f"/api/admin/payments/{payment['id']}/status",
        headers=headers,
        json={"status": "reversed"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["payment"]["status"] == "reversed"
    artist_user = next(
        user for user in client.get("/api/admin/users", headers=headers).get_json()["users"]
        if user["username"] == "dashboardartist"
    )
    assert artist_user["status"] == "pending_payment"

    invalid_response = client.put(
        f"/api/admin/payments/{payment['id']}/status",
        headers=headers,
        json={"status": "failed"},
    )
    assert invalid_response.status_code == 400

    restore_response = client.put(
        f"/api/admin/payments/{payment['id']}/status",
        headers=headers,
        json={"status": "successful"},
    )
    assert restore_response.status_code == 200
    assert restore_response.get_json()["payment"]["status"] == "successful"
    restored_artist = next(
        user for user in client.get("/api/admin/users", headers=headers).get_json()["users"]
        if user["username"] == "dashboardartist"
    )
    assert restored_artist["status"] == "active"


def test_admin_creates_the_next_season_and_rejects_invalid_dates(admin_dashboard_client):
    client, token = admin_dashboard_client
    headers = {"Authorization": f"Bearer {token}"}
    start = datetime.now() + timedelta(days=40)
    submission_end = start + timedelta(days=30)
    voting_end = submission_end + timedelta(days=30)

    response = client.post(
        "/api/admin/contests",
        headers=headers,
        json={
            "title": "Client supplied title is ignored",
            "start_date": start.isoformat(),
            "submission_end_date": submission_end.isoformat(),
            "voting_end_date": voting_end.isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.get_json()["contest"]["title"] == "Season 3"

    invalid_response = client.post(
        "/api/admin/contests",
        headers=headers,
        json={
            "start_date": start.isoformat(),
            "submission_end_date": voting_end.isoformat(),
            "voting_end_date": submission_end.isoformat(),
        },
    )

    assert invalid_response.status_code == 400
    assert invalid_response.get_json()["error"] == (
        "Contest dates must be ordered: start, submission close, then voting end"
    )


def test_admin_advances_contest_from_submission_to_voting_to_completed(admin_dashboard_client):
    client, token = admin_dashboard_client
    headers = {"Authorization": f"Bearer {token}"}

    voting_response = client.post(
        "/api/admin/contests/1/phase",
        headers=headers,
        json={"phase": "voting"},
    )
    assert voting_response.status_code == 200
    assert voting_response.get_json()["contest"]["phase"] == "voting"

    completed_response = client.post(
        "/api/admin/contests/1/phase",
        headers=headers,
        json={"phase": "completed"},
    )
    assert completed_response.status_code == 200
    assert completed_response.get_json()["contest"]["phase"] == "completed"

    repeated_response = client.post(
        "/api/admin/contests/1/phase",
        headers=headers,
        json={"phase": "completed"},
    )
    assert repeated_response.status_code == 409


def test_admin_updates_contest_dates_without_changing_manual_phase(admin_dashboard_client):
    client, token = admin_dashboard_client
    headers = {"Authorization": f"Bearer {token}"}
    phase_response = client.post(
        "/api/admin/contests/1/phase",
        headers=headers,
        json={"phase": "voting"},
    )
    assert phase_response.status_code == 200

    start = datetime.now() - timedelta(days=2)
    submission_end = datetime.now() + timedelta(days=5)
    voting_end = datetime.now() + timedelta(days=20)
    update_response = client.put(
        "/api/admin/contests/1/dates",
        headers=headers,
        json={
            "start_date": start.isoformat(),
            "submission_end_date": submission_end.isoformat(),
            "voting_end_date": voting_end.isoformat(),
        },
    )

    assert update_response.status_code == 200
    updated_contest = update_response.get_json()["contest"]
    assert updated_contest["phase"] == "voting"
    assert updated_contest["start_date"] == start.isoformat()
    assert updated_contest["submission_end_date"] == submission_end.isoformat()
    assert updated_contest["voting_end_date"] == voting_end.isoformat()

    invalid_response = client.put(
        "/api/admin/contests/1/dates",
        headers=headers,
        json={
            "start_date": start.isoformat(),
            "submission_end_date": voting_end.isoformat(),
            "voting_end_date": submission_end.isoformat(),
        },
    )
    assert invalid_response.status_code == 400
