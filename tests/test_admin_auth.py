import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from soundwarapp import create_app, db
from soundwarapp.models import User


@pytest.fixture
def admin_auth_client():
    app = create_app("testing")
    app.config.update(TESTING=True, ADMIN_SETUP_KEY="test-setup-secret")
    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()


def test_admin_bootstrap_hashes_password_and_admin_login_uses_admin_route(admin_auth_client):
    registration = admin_auth_client.post(
        "/api/auth/admin/register",
        json={
            "setup_key": "test-setup-secret",
            "name": "Site Admin",
            "username": "siteadmin",
            "email": "admin@example.com",
            "password": "StrongPass1!",
        },
    )

    assert registration.status_code == 201
    with admin_auth_client.application.app_context():
        admin = User.query.filter_by(email="admin@example.com").one()
        assert admin.roles == ["admin"]
        assert admin.password_hash != "StrongPass1!"
        assert check_password_hash(admin.password_hash, "StrongPass1!")

    login = admin_auth_client.post(
        "/api/auth/admin/login",
        json={"email": "admin@example.com", "password": "StrongPass1!"},
    )
    assert login.status_code == 200
    assert login.get_json()["user"]["roles"] == ["admin"]

    second_registration = admin_auth_client.post(
        "/api/auth/admin/register",
        json={
            "setup_key": "test-setup-secret",
            "name": "Second Admin",
            "username": "secondadmin",
            "email": "second@example.com",
            "password": "StrongPass1!",
        },
    )
    assert second_registration.status_code == 409


def test_public_registration_cannot_create_admin(admin_auth_client):
    response = admin_auth_client.post(
        "/api/auth/register",
        json={
            "name": "Injected Admin",
            "username": "injectedadmin",
            "email": "injected@example.com",
            "password": "StrongPass1!",
            "role": "admin",
        },
    )

    assert response.status_code == 400
    with admin_auth_client.application.app_context():
        assert User.query.filter_by(email="injected@example.com").first() is None


def test_admin_bootstrap_requires_configured_setup_key(admin_auth_client):
    admin_auth_client.application.config["ADMIN_SETUP_KEY"] = None
    response = admin_auth_client.post(
        "/api/auth/admin/register",
        json={"setup_key": "test-setup-secret"},
    )

    assert response.status_code == 503


def test_admin_login_rejects_regular_user(admin_auth_client):
    with admin_auth_client.application.app_context():
        user = User(
            email="voter@example.com",
            username="voteruser",
            name="Voter User",
            password_hash=generate_password_hash("StrongPass1!"),
            roles=["user"],
        )
        db.session.add(user)
        db.session.commit()

    response = admin_auth_client.post(
        "/api/auth/admin/login",
        json={"email": "voter@example.com", "password": "StrongPass1!"},
    )

    assert response.status_code == 401