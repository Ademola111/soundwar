import pytest

from soundwarapp import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def test_register_preflight_allows_vite_origin(client):
    response = client.options(
        "/api/auth/register",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
