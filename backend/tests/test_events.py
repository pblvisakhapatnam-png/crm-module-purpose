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


def test_successful_login_records_business_event() -> None:
    body = login("admin1", "password")
    token = body["access_token"]

    response = client.get(
        "/api/events/recent?limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    events = response.json()
    assert any(event["event_name"] == "UserLoginSucceeded" for event in events)
    assert "password" not in str(events).lower()


def test_failed_login_records_event_without_password() -> None:
    failed = client.post(
        "/api/auth/login",
        json={"username": "admin1", "password": "wrong-password"},
    )
    assert failed.status_code == 401

    body = login("admin1", "password")
    token = body["access_token"]

    response = client.get(
        "/api/events/recent?limit=20",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    events = response.json()
    assert any(event["event_name"] == "UserLoginFailed" for event in events)
    assert "wrong-password" not in str(events)


def test_recent_events_requires_authentication() -> None:
    response = client.get("/api/events/recent")

    assert response.status_code == 401


def test_recent_events_rejects_sales_user() -> None:
    body = login("sales1", "password")
    token = body["access_token"]

    response = client.get(
        "/api/events/recent",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_readonly_user_can_view_recent_events() -> None:
    body = login("readonly1", "password")
    token = body["access_token"]

    response = client.get(
        "/api/events/recent?limit=5",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_recent_events_can_filter_by_record_type_and_public_id() -> None:
    body = login("admin1", "password")
    token = body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    unfiltered = client.get("/api/events/recent?limit=20", headers=headers)
    assert unfiltered.status_code == 200
    sample_event = next(
        (event for event in unfiltered.json() if event.get("record_type") and event.get("record_public_id")),
        None,
    )
    assert sample_event is not None

    filtered = client.get(
        "/api/events/recent"
        f"?record_type={sample_event['record_type']}&record_public_id={sample_event['record_public_id']}",
        headers=headers,
    )
    assert filtered.status_code == 200
    filtered_events = filtered.json()
    assert len(filtered_events) >= 1
    assert all(
        event["record_type"] == sample_event["record_type"]
        and event["record_public_id"] == sample_event["record_public_id"]
        for event in filtered_events
    )


def test_recent_events_filter_by_unmatched_record_returns_empty_list() -> None:
    body = login("admin1", "password")
    token = body["access_token"]

    response = client.get(
        "/api/events/recent?record_type=work_order&record_public_id=00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []