import httpx

from app.core import security
from app.core.config import settings
from tests.test_profile import PROFILE


class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


def use_remote(monkeypatch, response=None, error=None):
    monkeypatch.setattr(settings, "token_verification_mode", "remote")

    def fake_post(url, json=None, timeout=None):
        assert url.endswith("/api/auth/verify-token")
        assert "token" in json
        if error:
            raise error
        return response

    monkeypatch.setattr(security.httpx, "post", fake_post)


def test_remote_verification_success(client, monkeypatch):
    use_remote(monkeypatch, FakeResponse(200, {"valid": True, "user_id": 7, "role": "customer"}))
    headers = {"Authorization": "Bearer anything"}
    response = client.post("/api/users/profile", json=PROFILE, headers=headers)
    assert response.status_code == 201
    assert response.json()["auth_user_id"] == 7


def test_remote_verification_invalid_token(client, monkeypatch):
    use_remote(monkeypatch, FakeResponse(401, {"detail": "Token has expired"}))
    response = client.get("/api/users/profile", headers={"Authorization": "Bearer anything"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_remote_verification_inactive_account(client, monkeypatch):
    use_remote(monkeypatch, FakeResponse(403, {"detail": "Account is inactive"}))
    response = client.get("/api/users/profile", headers={"Authorization": "Bearer anything"})
    assert response.status_code == 403


def test_remote_verification_auth_service_down(client, monkeypatch):
    use_remote(monkeypatch, error=httpx.ConnectError("refused"))
    response = client.get("/api/users/profile", headers={"Authorization": "Bearer anything"})
    assert response.status_code == 503


def test_remote_mode_still_requires_header(client, monkeypatch):
    use_remote(monkeypatch, FakeResponse(200, {"valid": True, "user_id": 7, "role": "customer"}))
    assert client.get("/api/users/profile").status_code == 401
