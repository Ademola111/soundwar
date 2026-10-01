from datetime import datetime, timedelta

from soundwarapp import create_app, db
from soundwarapp.models import User


def test_registration_requires_activation_and_activation_enables_login():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        client = app.test_client()

        response = client.post(
            "/api/auth/register",
            json={
                "name": "New Voter",
                "username": "newvoter",
                "email": "newvoter@example.com",
                "password": "Str0ng!Pass",
                "role": "voter",
            },
        )

        assert response.status_code == 201
        user = User.query.filter_by(email="newvoter@example.com").first()
        assert user.email_verified is False
        assert response.get_json()["requires_activation"] is True

        blocked = client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "Str0ng!Pass"},
        )
        assert blocked.status_code == 403

        activated = client.post(
            "/api/auth/activate",
            json={"token": user.activation_token},
        )
        assert activated.status_code == 200
        assert user.email_verified is True

        logged_in = client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "Str0ng!Pass"},
        )
        assert logged_in.status_code == 200

        db.drop_all()


def test_password_reset_token_is_one_time_and_expires():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        user = User(
            email="reset@example.com",
            username="resetuser",
            name="Reset User",
            password_hash="unused",
        )
        db.session.add(user)
        db.session.commit()
        client = app.test_client()

        requested = client.post(
            "/api/auth/forgot-password",
            json={"email": user.email},
        )
        assert requested.status_code == 200
        token = user.reset_token

        reset = client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "NewStr0ng!Pass"},
        )
        assert reset.status_code == 200
        assert user.reset_token is None

        reused = client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "AnotherStr0ng!Pass"},
        )
        assert reused.status_code == 400

        user.reset_token = "expired-token"
        user.reset_token_expires = datetime.utcnow() - timedelta(minutes=1)
        db.session.commit()
        expired = client.post(
            "/api/auth/verify-reset-token",
            json={"token": "expired-token"},
        )
        assert expired.status_code == 400

        db.drop_all()
