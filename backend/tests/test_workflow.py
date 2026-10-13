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


def auth_headers(username: str = "admin1") -> dict[str, str]:
    body = login(username, "password")
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_workflow_statuses_require_authentication() -> None:
    response = client.get("/api/workflow/statuses?module=business_party")

    assert response.status_code == 401


def test_admin_can_list_business_party_statuses() -> None:
    response = client.get(
        "/api/workflow/statuses?module=business_party",
        headers=auth_headers("admin1"),
    )

    assert response.status_code == 200
    statuses = response.json()
    codes = [status["status_code"] for status in statuses]
    assert "DRAFT" in codes
    assert "QUALIFIED_PROSPECT" in codes
    assert "CUSTOMER_ACTIVATION_PENDING" in codes
    assert "CUSTOMER_ACTIVE" in codes
    assert "BLACKLISTED" in codes
    assert all(status["module"] == "business_party" for status in statuses)


def test_sales_user_can_read_status_reference_data() -> None:
    response = client.get(
        "/api/workflow/statuses?module=business_party",
        headers=auth_headers("sales1"),
    )

    assert response.status_code == 200
    assert len(response.json()) >= 10


def test_workflow_modules_include_business_party() -> None:
    response = client.get(
        "/api/workflow/modules",
        headers=auth_headers("admin1"),
    )

    assert response.status_code == 200
    assert "business_party" in response.json()


def test_unknown_module_returns_empty_list() -> None:
    response = client.get(
        "/api/workflow/statuses?module=unknown_module",
        headers=auth_headers("admin1"),
    )

    assert response.status_code == 200
    assert response.json() == []