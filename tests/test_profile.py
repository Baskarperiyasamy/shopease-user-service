from datetime import date, timedelta

from app.models.user_model import UserProfile
from tests.conftest import make_token

PROFILE = {
    "full_name": "Baskar P",
    "phone_number": "9876543210",
    "date_of_birth": "2000-05-14",
    "gender": "male",
    "profile_image": "https://example.com/baskar.png",
}


def create(client, headers, **overrides):
    return client.post("/api/users/profile", json={**PROFILE, **overrides}, headers=headers)


def test_profile_without_token(client):
    assert client.get("/api/users/profile").status_code == 401
    assert client.post("/api/users/profile", json=PROFILE).status_code == 401


def test_profile_with_invalid_token(client):
    response = client.get("/api/users/profile", headers={"Authorization": "Bearer not.a.token"})
    assert response.status_code == 401


def test_profile_with_expired_token(client):
    headers = {"Authorization": f"Bearer {make_token(1, minutes=-5)}"}
    response = client.get("/api/users/profile", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_profile_with_wrong_secret(client):
    headers = {"Authorization": f"Bearer {make_token(1, secret='y' * 40)}"}
    assert client.get("/api/users/profile", headers=headers).status_code == 401


def test_create_profile(client, headers_a, db_session):
    response = create(client, headers_a)
    assert response.status_code == 201
    body = response.json()
    assert body["auth_user_id"] == 1
    assert body["full_name"] == "Baskar P"
    assert body["is_active"] is True
    assert db_session.query(UserProfile).count() == 1


def test_create_profile_takes_user_id_from_token(client, headers_b):
    response = create(client, headers_b)
    assert response.json()["auth_user_id"] == 2


def test_create_profile_rejects_user_id_in_body(client, headers_a):
    response = create(client, headers_a, auth_user_id=99)
    assert response.status_code == 422


def test_create_duplicate_profile(client, headers_a):
    create(client, headers_a)
    response = create(client, headers_a)
    assert response.status_code == 409


def test_create_profile_validation(client, headers_a):
    assert create(client, headers_a, phone_number="abc").status_code == 422
    assert create(client, headers_a, phone_number="123").status_code == 422
    assert create(client, headers_a, full_name="").status_code == 422
    assert create(client, headers_a, gender="robot").status_code == 422
    future = (date.today() + timedelta(days=5)).isoformat()
    assert create(client, headers_a, date_of_birth=future).status_code == 422
    assert client.post("/api/users/profile", json={}, headers=headers_a).status_code == 422


def test_phone_number_is_cleaned(client, headers_a):
    response = create(client, headers_a, phone_number="+91 98765-43210")
    assert response.json()["phone_number"] == "+919876543210"


def test_get_profile(client, headers_a):
    create(client, headers_a)
    response = client.get("/api/users/profile", headers=headers_a)
    assert response.status_code == 200
    assert response.json()["phone_number"] == "9876543210"


def test_get_profile_before_creation(client, headers_a):
    assert client.get("/api/users/profile", headers=headers_a).status_code == 404


def test_user_cannot_see_another_users_profile(client, headers_a, headers_b):
    create(client, headers_a)
    assert client.get("/api/users/profile", headers=headers_b).status_code == 404
    create(client, headers_b, full_name="Other Person")
    assert client.get("/api/users/profile", headers=headers_a).json()["full_name"] == "Baskar P"
    assert client.get("/api/users/profile", headers=headers_b).json()["full_name"] == "Other Person"


def test_put_profile(client, headers_a):
    create(client, headers_a)
    body = {"full_name": "Baskar Periyasamy", "phone_number": "9123456780"}
    response = client.put("/api/users/profile", json=body, headers=headers_a)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Baskar Periyasamy"
    assert data["date_of_birth"] is None
    assert data["gender"] is None


def test_put_profile_requires_required_fields(client, headers_a):
    create(client, headers_a)
    assert client.put("/api/users/profile", json={"full_name": "Only Name"}, headers=headers_a).status_code == 422


def test_patch_profile(client, headers_a):
    create(client, headers_a)
    response = client.patch("/api/users/profile", json={"gender": "Female"}, headers=headers_a)
    assert response.status_code == 200
    data = response.json()
    assert data["gender"] == "female"
    assert data["full_name"] == "Baskar P"


def test_patch_profile_empty_and_null_required(client, headers_a):
    create(client, headers_a)
    assert client.patch("/api/users/profile", json={}, headers=headers_a).status_code == 400
    assert client.patch("/api/users/profile", json={"full_name": None}, headers=headers_a).status_code == 422
    assert client.patch("/api/users/profile", json={"phone_number": "bad"}, headers=headers_a).status_code == 422


def test_patch_cannot_change_auth_user_id(client, headers_a):
    create(client, headers_a)
    assert client.patch("/api/users/profile", json={"auth_user_id": 5}, headers=headers_a).status_code == 422


def test_update_contact(client, headers_a):
    create(client, headers_a)
    response = client.patch("/api/users/profile/contact", json={"phone_number": "9000000001"}, headers=headers_a)
    assert response.status_code == 200
    assert response.json()["phone_number"] == "9000000001"


def test_delete_profile_removes_addresses(client, headers_a, db_session):
    create(client, headers_a)
    client.post("/api/users/addresses", json=ADDRESS, headers=headers_a)
    response = client.delete("/api/users/profile", headers=headers_a)
    assert response.status_code == 200
    assert client.get("/api/users/profile", headers=headers_a).status_code == 404
    from app.models.address_model import UserAddress

    assert db_session.query(UserAddress).count() == 0


def test_deactivate_and_reactivate(client, headers_a):
    create(client, headers_a)
    response = client.post("/api/users/profile/deactivate", headers=headers_a)
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    assert client.get("/api/users/profile", headers=headers_a).status_code == 200
    assert client.patch("/api/users/profile", json={"gender": "male"}, headers=headers_a).status_code == 403
    assert client.get("/api/users/addresses", headers=headers_a).status_code == 403
    assert client.post("/api/users/profile/deactivate", headers=headers_a).status_code == 400

    response = client.post("/api/users/profile/reactivate", headers=headers_a)
    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert client.get("/api/users/addresses", headers=headers_a).status_code == 200
    assert client.post("/api/users/profile/reactivate", headers=headers_a).status_code == 400


def test_account_overview(client, headers_a):
    create(client, headers_a)
    client.post("/api/users/addresses", json=ADDRESS, headers=headers_a)
    client.post("/api/users/addresses", json={**ADDRESS, "address_type": "Office"}, headers=headers_a)
    response = client.get("/api/users/account", headers=headers_a)
    assert response.status_code == 200
    body = response.json()
    assert body["auth_user_id"] == 1
    assert body["role"] == "customer"
    assert body["address_count"] == 2
    assert body["default_address"]["address_type"] == "Home"


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


ADDRESS = {
    "address_type": "Home",
    "full_name": "Baskar P",
    "phone_number": "9876543210",
    "address_line_1": "12 Gandhi Road",
    "address_line_2": "Near Park",
    "city": "Chennai",
    "state": "Tamil Nadu",
    "country": "India",
    "postal_code": "600001",
}
