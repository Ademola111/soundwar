from io import BytesIO

from flask_jwt_extended import create_access_token
import pytest

from soundwarapp import create_app, db
from soundwarapp.models import Artist, User


@pytest.fixture
def artist_profile_client(tmp_path):
    app = create_app("testing")
    app.config.update(TESTING=True, ARTIST_PROFILE_UPLOAD_FOLDER=str(tmp_path))
    with app.app_context():
        db.create_all()
        user = User(
            email="artist@example.com",
            username="artistuser",
            name="Artist User",
            password_hash="hashed",
            roles=["artist"],
        )
        db.session.add(user)
        db.session.commit()
        artist = Artist(
            user_id=user.id,
            stage_name="Old Stage Name",
            genre="Pop",
            bio="Original bio",
        )
        db.session.add(artist)
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        with app.test_client() as client:
            yield client, token, artist.id, tmp_path
        db.session.remove()
        db.drop_all()


def test_artist_can_update_profile_details(artist_profile_client):
    client, token, artist_id, _ = artist_profile_client

    response = client.put(
        "/api/artists/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "stage_name": "New Stage Name",
            "genre": "Afrobeats",
            "bio": "A refreshed artist biography.",
            "profile_image": "https://example.com/artist.jpg",
        },
    )

    assert response.status_code == 200
    artist = response.get_json()["artist"]
    assert artist["stage_name"] == "New Stage Name"
    assert artist["genre"] == "Afrobeats"
    assert artist["bio"] == "A refreshed artist biography."
    assert artist["profile_image"] == "https://example.com/artist.jpg"


def test_artist_profile_rejects_invalid_image_url(artist_profile_client):
    client, token, _, _ = artist_profile_client

    response = client.put(
        "/api/artists/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"profile_image": "javascript:alert(1)"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Profile image must be a valid HTTP or HTTPS URL"


def test_artist_can_upload_display_picture(artist_profile_client):
    client, token, _, upload_folder = artist_profile_client

    response = client.post(
        "/api/artists/profile/image",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "profile_image": (
                BytesIO(b"\xff\xd8\xfftest image data"),
                "portrait.jpg",
                "image/jpeg",
            )
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    image_url = response.get_json()["artist"]["profile_image"]
    assert image_url.endswith(".jpg")
    saved_images = list(upload_folder.glob("*.jpg"))
    assert len(saved_images) == 1
    assert saved_images[0].read_bytes() == b"\xff\xd8\xfftest image data"