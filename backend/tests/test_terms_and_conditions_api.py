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


def test_tc_clause_list_requires_authentication() -> None:
    response = client.get("/api/tc-clauses")

    assert response.status_code == 401


def test_sales_user_can_list_seeded_tc_clauses() -> None:
    response = client.get("/api/tc-clauses", headers=auth_headers("sales1"))

    assert response.status_code == 200
    clauses = response.json()
    assert len(clauses) >= 15
    assert {clause["business_line"] for clause in clauses} >= {"TRANSPORTATION", "HIRING"}
    assert all("source-derived" not in clause["title"].lower() for clause in clauses)


def test_management_read_only_can_view_tc_clauses() -> None:
    response = client.get("/api/tc-clauses?limit=5", headers=auth_headers("readonly1"))

    assert response.status_code == 200
    assert len(response.json()) > 0


def test_tc_clause_filters_and_search() -> None:
    response = client.get(
        "/api/tc-clauses?business_line=HIRING&applies_to_line=true&search=overtime",
        headers=auth_headers("sales1"),
    )

    assert response.status_code == 200
    clauses = response.json()
    assert len(clauses) >= 1
    assert all(clause["business_line"] == "HIRING" for clause in clauses)
    assert all(clause["applies_to_line"] is True for clause in clauses)
    assert any("Overtime" in clause["title"] for clause in clauses)


def test_tc_clause_detail_lookup() -> None:
    list_response = client.get("/api/tc-clauses?search=quote%20validity", headers=auth_headers("sales1"))
    assert list_response.status_code == 200
    clauses = list_response.json()
    assert clauses

    public_id = clauses[0]["public_id"]
    detail_response = client.get(f"/api/tc-clauses/{public_id}", headers=auth_headers("sales1"))

    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["public_id"] == public_id
    assert body["clause_text"]
    assert body["source_reference"]


def test_missing_tc_clause_returns_404() -> None:
    response = client.get(
        "/api/tc-clauses/00000000-0000-0000-0000-000000009999",
        headers=auth_headers("sales1"),
    )

    assert response.status_code == 404


def test_invalid_tc_business_line_returns_422() -> None:
    response = client.get(
        "/api/tc-clauses?business_line=LEGAL",
        headers=auth_headers("sales1"),
    )

    assert response.status_code == 422

