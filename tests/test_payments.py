import pytest
from flask_jwt_extended import create_access_token

from soundwarapp import create_app, db
from soundwarapp.models import Artist, User
import soundwarapp.myroutes.payments as payments_module


@pytest.fixture()
def app_instance():
    app = create_app("testing")
    app.config.update(TESTING=True)

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app_instance):
    return app_instance.test_client()


def test_initialize_payment_returns_link_for_valid_token(client, app_instance, monkeypatch):
    with app_instance.app_context():
        user = User(
            email="payuser@example.com",
            username="payuser",
            name="Pay User",
            password_hash="hashed",
            roles=["artist"],
        )
        db.session.add(user)
        db.session.commit()
        db.session.add(Artist(user_id=user.id, stage_name="Pay Artist"))
        db.session.commit()
        token = create_access_token(identity=str(user.id))

    class FakeResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        def json(self):
            return self._payload

    def fake_post(*args, **kwargs):
        assert args[0] == "https://api.flutterwave.com/v3/payments"
        assert kwargs["json"]["amount"] == app_instance.config["ARTIST_REGISTRATION_FEE"]
        assert kwargs["json"]["customer"] == {
            "email": "payuser@example.com",
            "name": "Pay User",
        }
        return FakeResponse({
            "status": "success",
            "message": "OK",
            "data": {"link": "https://checkout.flutterwave.com/test"},
        })

    monkeypatch.setattr(payments_module.requests, "post", fake_post)

    for tx_ref in ("SW-test-ref-12345", "SW-test-ref-67890"):
        response = client.post(
            "/api/payments/initialize",
            headers={"Authorization": f"Bearer {token}"},
            json={"tx_ref": tx_ref, "amount": 1},
        )

        assert response.status_code == 201
        body = response.get_json()
        assert body["payment_link"] == "https://checkout.flutterwave.com/test"
