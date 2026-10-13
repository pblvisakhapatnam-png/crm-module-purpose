from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login(username: str = "admin1", password: str = "password") -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def test_login_success_returns_token_and_user_without_password() -> None:
    body = login("admin1", "password")

    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "admin1"
    assert "ADMIN" in body["user"]["role_codes"]
    assert "password" not in str(body).lower()


def test_login_rejects_wrong_password() -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin1", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_me_requires_bearer_token() -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_returns_authenticated_user() -> None:
    body = login("sales1", "password")
    token = body["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "sales1"
    assert "SALES_USER" in response.json()["role_codes"]


def test_roles_endpoint_requires_admin_role() -> None:
    body = login("sales1", "password")
    token = body["access_token"]

    response = client.get(
        "/api/auth/roles",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_list_roles() -> None:
    body = login("admin1", "password")
    token = body["access_token"]

    response = client.get(
        "/api/auth/roles",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    role_codes = {role["role_code"] for role in response.json()}
    assert "ADMIN" in role_codes
    assert "SALES_USER" in role_codes