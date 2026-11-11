from app.models.address_model import UserAddress
from tests.test_profile import ADDRESS, PROFILE


def setup_profile(client, headers):
    client.post("/api/users/profile", json=PROFILE, headers=headers)


def add(client, headers, **overrides):
    return client.post("/api/users/addresses", json={**ADDRESS, **overrides}, headers=headers)


def defaults(client, headers):
    addresses = client.get("/api/users/addresses", headers=headers).json()
    return [a["id"] for a in addresses if a["is_default"]]


def test_addresses_without_token(client):
    assert client.get("/api/users/addresses").status_code == 401


def test_address_requires_profile(client, headers_a):
    assert add(client, headers_a).status_code == 404


def test_add_address(client, headers_a):
    setup_profile(client, headers_a)
    response = add(client, headers_a)
    assert response.status_code == 201
    body = response.json()
    assert body["address_type"] == "Home"
    assert body["city"] == "Chennai"
    assert body["user_id"] == 1


def test_first_address_becomes_default(client, headers_a):
    setup_profile(client, headers_a)
    first = add(client, headers_a).json()
    assert first["is_default"] is True
    second = add(client, headers_a, address_type="Office").json()
    assert second["is_default"] is False
    assert defaults(client, headers_a) == [first["id"]]


def test_new_default_replaces_old_default(client, headers_a):
    setup_profile(client, headers_a)
    first = add(client, headers_a).json()
    second = add(client, headers_a, address_type="Office", is_default=True).json()
    assert second["is_default"] is True
    assert defaults(client, headers_a) == [second["id"]]
    assert first["id"] not in defaults(client, headers_a)


def test_add_multiple_and_list(client, headers_a):
    setup_profile(client, headers_a)
    for kind in ("Home", "Office", "Other"):
        assert add(client, headers_a, address_type=kind).status_code == 201
    response = client.get("/api/users/addresses", headers=headers_a)
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_address_type_is_case_insensitive(client, headers_a):
    setup_profile(client, headers_a)
    assert add(client, headers_a, address_type="office").json()["address_type"] == "Office"


def test_address_validation(client, headers_a):
    setup_profile(client, headers_a)
    assert add(client, headers_a, address_type="Hotel").status_code == 422
    assert add(client, headers_a, phone_number="12").status_code == 422
    assert add(client, headers_a, postal_code="!!").status_code == 422
    assert add(client, headers_a, city="").status_code == 422
    body = {k: v for k, v in ADDRESS.items() if k != "address_line_1"}
    assert client.post("/api/users/addresses", json=body, headers=headers_a).status_code == 422


def test_address_rejects_user_id_in_body(client, headers_a):
    setup_profile(client, headers_a)
    assert add(client, headers_a, user_id=2).status_code == 422


def test_get_address(client, headers_a):
    setup_profile(client, headers_a)
    address_id = add(client, headers_a).json()["id"]
    response = client.get(f"/api/users/addresses/{address_id}", headers=headers_a)
    assert response.status_code == 200
    assert response.json()["id"] == address_id


def test_get_missing_address(client, headers_a):
    setup_profile(client, headers_a)
    response = client.get("/api/users/addresses/999", headers=headers_a)
    assert response.status_code == 404
    assert response.json()["detail"] == "Address not found"


def test_update_address(client, headers_a):
    setup_profile(client, headers_a)
    address_id = add(client, headers_a).json()["id"]
    body = {**ADDRESS, "city": "Coimbatore", "address_type": "Office"}
    response = client.put(f"/api/users/addresses/{address_id}", json=body, headers=headers_a)
    assert response.status_code == 200
    assert response.json()["city"] == "Coimbatore"
    assert response.json()["address_type"] == "Office"


def test_update_address_with_default_flag(client, headers_a):
    setup_profile(client, headers_a)
    first = add(client, headers_a).json()
    second = add(client, headers_a, address_type="Office").json()
    body = {**ADDRESS, "is_default": True}
    response = client.put(f"/api/users/addresses/{second['id']}", json=body, headers=headers_a)
    assert response.status_code == 200
    assert defaults(client, headers_a) == [second["id"]]
    assert first["id"] not in defaults(client, headers_a)


def test_set_default_address(client, headers_a):
    setup_profile(client, headers_a)
    first = add(client, headers_a).json()
    second = add(client, headers_a, address_type="Office").json()
    third = add(client, headers_a, address_type="Other").json()

    response = client.patch(f"/api/users/addresses/{third['id']}/default", headers=headers_a)
    assert response.status_code == 200
    assert response.json()["is_default"] is True
    assert defaults(client, headers_a) == [third["id"]]

    client.patch(f"/api/users/addresses/{second['id']}/default", headers=headers_a)
    assert defaults(client, headers_a) == [second["id"]]
    assert first["id"] not in defaults(client, headers_a)


def test_delete_address(client, headers_a, db_session):
    setup_profile(client, headers_a)
    add(client, headers_a)
    second = add(client, headers_a, address_type="Office").json()
    response = client.delete(f"/api/users/addresses/{second['id']}", headers=headers_a)
    assert response.status_code == 200
    assert client.get(f"/api/users/addresses/{second['id']}", headers=headers_a).status_code == 404
    assert db_session.query(UserAddress).count() == 1


def test_deleting_default_promotes_another_address(client, headers_a):
    setup_profile(client, headers_a)
    first = add(client, headers_a).json()
    second = add(client, headers_a, address_type="Office").json()
    client.delete(f"/api/users/addresses/{first['id']}", headers=headers_a)
    assert defaults(client, headers_a) == [second["id"]]


def test_user_cannot_access_another_users_address(client, headers_a, headers_b):
    setup_profile(client, headers_a)
    setup_profile(client, headers_b)
    address_id = add(client, headers_a).json()["id"]

    url = f"/api/users/addresses/{address_id}"
    assert client.get(url, headers=headers_b).status_code == 403
    assert client.put(url, json=ADDRESS, headers=headers_b).status_code == 403
    assert client.patch(f"{url}/default", headers=headers_b).status_code == 403
    assert client.delete(url, headers=headers_b).status_code == 403

    assert client.get(url, headers=headers_a).status_code == 200
    assert client.get("/api/users/addresses", headers=headers_b).json() == []


def test_deactivated_profile_cannot_manage_addresses(client, headers_a):
    setup_profile(client, headers_a)
    client.post("/api/users/profile/deactivate", headers=headers_a)
    assert add(client, headers_a).status_code == 403
