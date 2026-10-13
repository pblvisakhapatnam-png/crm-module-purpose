from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_database_settings_summary

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "pbl-crm-hiring-backend"


def test_platform_config_summary_does_not_expose_password() -> None:
    response = client.get("/api/platform/config-summary")

    assert response.status_code == 200
    body = response.json()
    assert "database" in body
    assert "password" not in str(body).lower()


def test_database_summary_does_not_include_password() -> None:
    summary = get_database_settings_summary()

    assert "password" not in summary