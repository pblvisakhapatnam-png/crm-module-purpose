"""UI cleanup package (September 2026): display names beside user public ids.

Several responses exposed people only as user public ids, so the screen showed a UUID for
"Owner" and "Created by". These tests pin the additive, read-only display-name fields that
resolve those ids from app_user.display_name - on the create response, the list and the detail
of every module that carries them - and pin that an id which is null, or which matches no user,
yields a null name while the record itself still lists. The second half is what proves the join
is a LEFT JOIN: an INNER JOIN would silently drop the record from the list instead.

The existing *_public_id / created_by fields are asserted alongside, because the package is
additive only and must not change them.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text

from app.core.database import SessionLocal
from tests.test_commercial_offers_api import (
    auth_headers,
    client,
    cleanup_test_records,
    create_account_linked_test_opportunity,
    create_test_commercial_offer,
)
from tests.test_work_order_amendments_api import _build_accepted_work_order_chain, _teardown


def _seeded_user(username: str = "sales1") -> dict[str, str]:
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT public_id, display_name FROM app_user WHERE lower(username) = :username"),
            {"username": username},
        ).first()
    assert row is not None, f"seed user {username!r} is missing from app_user"
    assert row.display_name, f"seed user {username!r} has no display_name to resolve"
    return {"public_id": str(row.public_id), "display_name": str(row.display_name)}


def _assert_display_name(record: dict[str, object], field: str, expected: str | None) -> None:
    assert field in record, f"response has no {field!r} field; it has {sorted(record)}"
    assert record[field] == expected, f"{field!r} was {record[field]!r}, expected {expected!r}"


def _find(records: list[dict[str, object]], public_id: str) -> dict[str, object]:
    matches = [record for record in records if record["public_id"] == public_id]
    assert len(matches) == 1, f"record {public_id} is not in the list response"
    return matches[0]


def _get_ok(url: str, headers: dict[str, str]) -> object:
    response = client.get(url, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _point_actors_at_unknown_user(
    *,
    table: str,
    public_id_column: str,
    public_id: str,
    actor_columns: tuple[str, ...],
) -> str:
    """Rewrite actor ids to a UUID that matches no app_user row. These columns carry no foreign
    key to app_user, so an id with no matching user is a reachable state, not a contrived one.
    Written directly because no route is meant to produce it."""
    unknown_user_public_id = str(uuid4())
    assignments = ", ".join(f"{column} = :unknown" for column in actor_columns)
    with SessionLocal() as db:
        result = db.execute(
            text(f"UPDATE {table} SET {assignments} WHERE {public_id_column} = :public_id"),
            {"unknown": unknown_user_public_id, "public_id": public_id},
        )
        assert result.rowcount == 1
        db.commit()
    return unknown_user_public_id


# --- Account ------------------------------------------------------------------------------------


def test_account_names_resolve_on_create_list_detail_and_classification() -> None:
    user = _seeded_user()
    headers = auth_headers("sales1")
    account_public_ids: list[str] = []
    try:
        response = client.post(
            "/api/accounts",
            headers=headers,
            json={"account_name": f"UI cleanup display-name Account {uuid4()}"},
        )
        assert response.status_code == 201, response.text
        created = response.json()["account"]
        account_public_id = str(created["public_id"])
        account_public_ids.append(account_public_id)

        # The owner defaults to the creating user; the ids themselves are unchanged.
        assert created["account_owner_user_public_id"] == user["public_id"]
        assert created["created_by"] == user["public_id"]

        listed = _find(_get_ok("/api/accounts?limit=100", headers), account_public_id)
        detail = _get_ok(f"/api/accounts/{account_public_id}", headers)
        for record in (created, listed, detail):
            _assert_display_name(record, "account_owner_display_name", user["display_name"])
            _assert_display_name(record, "created_by_display_name", user["display_name"])

        classification = _get_ok(f"/api/accounts/{account_public_id}/classification", headers)
        assert classification["account_owner_user_public_id"] == user["public_id"]
        _assert_display_name(classification, "account_owner_display_name", user["display_name"])
    finally:
        cleanup_test_records(opportunity_public_ids=[], offer_public_ids=[], account_public_ids=account_public_ids)


def test_account_names_are_null_when_ids_are_null_or_do_not_resolve() -> None:
    user = _seeded_user()
    headers = auth_headers("sales1")
    account_public_ids: list[str] = []
    try:
        response = client.post(
            "/api/accounts",
            headers=headers,
            json={"account_name": f"UI cleanup unresolved-name Account {uuid4()}"},
        )
        assert response.status_code == 201, response.text
        account_public_id = str(response.json()["account"]["public_id"])
        account_public_ids.append(account_public_id)

        # A null owner, set through the real classification route: null owner name, while the
        # creator still resolves.
        cleared = client.put(
            f"/api/accounts/{account_public_id}/classification",
            headers=headers,
            json={"account_owner_user_public_id": None},
        )
        assert cleared.status_code == 200, cleared.text
        cleared_classification = cleared.json()["classification"]
        assert cleared_classification["account_owner_user_public_id"] is None
        _assert_display_name(cleared_classification, "account_owner_display_name", None)
        detail = _get_ok(f"/api/accounts/{account_public_id}", headers)
        assert detail["account_owner_user_public_id"] is None
        _assert_display_name(detail, "account_owner_display_name", None)
        _assert_display_name(detail, "created_by_display_name", user["display_name"])

        # Ids that match no user: the record still lists, keeps its ids, and carries null names.
        unknown = _point_actors_at_unknown_user(
            table="business_party",
            public_id_column="business_party_public_id",
            public_id=account_public_id,
            actor_columns=("account_owner_user_public_id", "created_by"),
        )
        listed = _find(_get_ok("/api/accounts?limit=100", headers), account_public_id)
        detail = _get_ok(f"/api/accounts/{account_public_id}", headers)
        for record in (listed, detail):
            assert record["account_owner_user_public_id"] == unknown
            assert record["created_by"] == unknown
            _assert_display_name(record, "account_owner_display_name", None)
            _assert_display_name(record, "created_by_display_name", None)
        classification = _get_ok(f"/api/accounts/{account_public_id}/classification", headers)
        assert classification["account_owner_user_public_id"] == unknown
        _assert_display_name(classification, "account_owner_display_name", None)
    finally:
        cleanup_test_records(opportunity_public_ids=[], offer_public_ids=[], account_public_ids=account_public_ids)


def test_account_classification_save_returns_the_new_owners_name() -> None:
    """Independent review, round 1. The Account page shows the owner from the classification save
    response, so that response must carry the NEW owner's name, not only their id. This covers
    existing behaviour - the save re-reads through the same joined query as the GET - rather than
    proving a fix."""
    creator = _seeded_user("sales1")
    new_owner = _seeded_user("manager1")
    assert new_owner["display_name"] != creator["display_name"], "the test needs two distinct names"
    headers = auth_headers("sales1")
    account_public_ids: list[str] = []
    try:
        response = client.post(
            "/api/accounts",
            headers=headers,
            json={"account_name": f"UI cleanup reassigned-owner Account {uuid4()}"},
        )
        assert response.status_code == 201, response.text
        account_public_id = str(response.json()["account"]["public_id"])
        account_public_ids.append(account_public_id)

        saved = client.put(
            f"/api/accounts/{account_public_id}/classification",
            headers=headers,
            json={"account_owner_user_public_id": new_owner["public_id"]},
        )
        assert saved.status_code == 200, saved.text
        classification = saved.json()["classification"]
        assert classification["account_owner_user_public_id"] == new_owner["public_id"]
        _assert_display_name(classification, "account_owner_display_name", new_owner["display_name"])

        detail = _get_ok(f"/api/accounts/{account_public_id}", headers)
        _assert_display_name(detail, "account_owner_display_name", new_owner["display_name"])
    finally:
        cleanup_test_records(opportunity_public_ids=[], offer_public_ids=[], account_public_ids=account_public_ids)


# --- Opportunity --------------------------------------------------------------------------------


def test_opportunity_names_resolve_on_create_update_list_and_detail() -> None:
    user = _seeded_user()
    headers = auth_headers("sales1")
    opportunity_public_ids: list[str] = []
    try:
        response = client.post(
            "/api/opportunities",
            headers=headers,
            json={
                "opportunity_name": f"UI cleanup display-name Opportunity {uuid4()}",
                "opportunity_source": "manual",
            },
        )
        assert response.status_code == 201, response.text
        created = response.json()["opportunity"]
        opportunity_public_id = str(created["public_id"])
        opportunity_public_ids.append(opportunity_public_id)
        assert created["owner_user_public_id"] == user["public_id"]
        assert created["created_by"] == user["public_id"]

        listed = _find(_get_ok("/api/opportunities?limit=100", headers), opportunity_public_id)
        detail = _get_ok(f"/api/opportunities/{opportunity_public_id}", headers)
        for record in (created, listed, detail):
            _assert_display_name(record, "owner_display_name", user["display_name"])
            _assert_display_name(record, "created_by_display_name", user["display_name"])

        # Clearing the owner through the real update route gives a null owner name.
        updated = client.put(
            f"/api/opportunities/{opportunity_public_id}",
            headers=headers,
            json={"owner_user_public_id": None},
        )
        assert updated.status_code == 200, updated.text
        updated_record = updated.json()["opportunity"]
        assert updated_record["owner_user_public_id"] is None
        _assert_display_name(updated_record, "owner_display_name", None)
        _assert_display_name(updated_record, "created_by_display_name", user["display_name"])

        unknown = _point_actors_at_unknown_user(
            table="crm_opportunity",
            public_id_column="opportunity_public_id",
            public_id=opportunity_public_id,
            actor_columns=("owner_user_public_id", "created_by"),
        )
        listed = _find(_get_ok("/api/opportunities?limit=100", headers), opportunity_public_id)
        assert listed["owner_user_public_id"] == unknown
        assert listed["created_by"] == unknown
        _assert_display_name(listed, "owner_display_name", None)
        _assert_display_name(listed, "created_by_display_name", None)
    finally:
        cleanup_test_records(opportunity_public_ids=opportunity_public_ids, offer_public_ids=[])


# --- Lead ---------------------------------------------------------------------------------------


def test_lead_names_resolve_on_create_list_and_detail() -> None:
    user = _seeded_user()
    headers = auth_headers("sales1")
    lead_public_ids: list[str] = []
    try:
        response = client.post(
            "/api/leads",
            headers=headers,
            json={
                "lead_source": "manual",
                "company_name": f"UI cleanup display-name Lead {uuid4()}",
                "assigned_to_user_public_id": user["public_id"],
            },
        )
        assert response.status_code == 201, response.text
        created = response.json()["lead"]
        lead_public_id = str(created["public_id"])
        lead_public_ids.append(lead_public_id)
        assert created["assigned_to_user_public_id"] == user["public_id"]
        assert created["created_by"] == user["public_id"]

        listed = _find(_get_ok("/api/leads?limit=100", headers), lead_public_id)
        detail = _get_ok(f"/api/leads/{lead_public_id}", headers)
        for record in (created, listed, detail):
            _assert_display_name(record, "assigned_to_display_name", user["display_name"])
            _assert_display_name(record, "created_by_display_name", user["display_name"])

        # An unassigned Lead has a null assignee name; its creator still resolves.
        unassigned = client.post(
            "/api/leads",
            headers=headers,
            json={"lead_source": "manual", "company_name": f"UI cleanup unassigned Lead {uuid4()}"},
        )
        assert unassigned.status_code == 201, unassigned.text
        unassigned_record = unassigned.json()["lead"]
        lead_public_ids.append(str(unassigned_record["public_id"]))
        assert unassigned_record["assigned_to_user_public_id"] is None
        _assert_display_name(unassigned_record, "assigned_to_display_name", None)
        _assert_display_name(unassigned_record, "created_by_display_name", user["display_name"])

        unknown = _point_actors_at_unknown_user(
            table="crm_lead",
            public_id_column="lead_public_id",
            public_id=lead_public_id,
            actor_columns=("assigned_to_user_public_id", "created_by"),
        )
        listed = _find(_get_ok("/api/leads?limit=100", headers), lead_public_id)
        assert listed["assigned_to_user_public_id"] == unknown
        assert listed["created_by"] == unknown
        _assert_display_name(listed, "assigned_to_display_name", None)
        _assert_display_name(listed, "created_by_display_name", None)
    finally:
        cleanup_test_records(opportunity_public_ids=[], offer_public_ids=[], lead_public_ids=lead_public_ids)


# --- Commercial Offer, and the records Lead conversion embeds ----------------------------------


def test_commercial_offer_creator_name_resolves_and_conversion_embeds_resolved_names() -> None:
    user = _seeded_user()
    headers = auth_headers("sales1")
    lead_public_ids: list[str] = []
    account_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    try:
        linked = create_account_linked_test_opportunity()
        lead_public_ids.append(str(linked["lead"]["public_id"]))
        account_public_ids.append(str(linked["account"]["public_id"]))
        opportunity_public_id = str(linked["opportunity"]["public_id"])
        opportunity_public_ids.append(opportunity_public_id)

        # Lead conversion returns the Lead, Account and Opportunity together; each embedded
        # record carries its names as well.
        _assert_display_name(linked["lead"], "created_by_display_name", user["display_name"])
        _assert_display_name(linked["account"], "account_owner_display_name", user["display_name"])
        _assert_display_name(linked["account"], "created_by_display_name", user["display_name"])
        _assert_display_name(linked["opportunity"], "owner_display_name", user["display_name"])
        _assert_display_name(linked["opportunity"], "created_by_display_name", user["display_name"])

        created = create_test_commercial_offer(opportunity_public_id)
        offer_public_id = str(created["public_id"])
        offer_public_ids.append(offer_public_id)
        assert created["created_by"] == user["public_id"]

        list_url = f"/api/commercial-offers?opportunity_public_id={opportunity_public_id}"
        listed = _find(_get_ok(list_url, headers), offer_public_id)
        detail = _get_ok(f"/api/commercial-offers/{offer_public_id}", headers)
        for record in (created, listed, detail):
            _assert_display_name(record, "created_by_display_name", user["display_name"])

        unknown = _point_actors_at_unknown_user(
            table="crm_commercial_offer",
            public_id_column="offer_public_id",
            public_id=offer_public_id,
            actor_columns=("created_by",),
        )
        listed = _find(_get_ok(list_url, headers), offer_public_id)
        assert listed["created_by"] == unknown
        _assert_display_name(listed, "created_by_display_name", None)
    finally:
        cleanup_test_records(
            opportunity_public_ids=opportunity_public_ids,
            offer_public_ids=offer_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )


# --- Work Order and Work Order Amendment --------------------------------------------------------


def test_work_order_and_amendment_creator_names_resolve_on_reads_but_not_on_the_frozen_handoff() -> None:
    user = _seeded_user()
    headers = auth_headers("sales1")
    work_order_public_ids: list[str] = []
    offer_public_ids: list[str] = []
    opportunity_public_ids: list[str] = []
    account_public_ids: list[str] = []
    lead_public_ids: list[str] = []
    try:
        chain = _build_accepted_work_order_chain()
        opportunity_public_ids.append(str(chain["opportunity"]["public_id"]))
        account_public_ids.append(str(chain["account"]["public_id"]))
        lead_public_ids.append(str(chain["lead"]["public_id"]))
        base_offer_public_id = str(chain["base_offer_public_id"])
        offer_public_ids.append(base_offer_public_id)
        # The Work Order record as returned by the handoff POST itself. That output belongs to the
        # frozen Accepted Offer -> Work Order handoff contract and must keep its exact shape, so the
        # display name appears on the read routes only - never on the handoff response.
        work_order = chain["work_order"]
        work_order_public_id = str(work_order["public_id"])
        work_order_public_ids.append(work_order_public_id)
        assert work_order["created_by"] == user["public_id"]
        assert "created_by_display_name" not in work_order, (
            "the frozen handoff output gained a field; display names belong on the read routes only"
        )

        work_order_list_url = f"/api/work-orders?commercial_offer_public_id={base_offer_public_id}"
        listed = _find(_get_ok(work_order_list_url, headers), work_order_public_id)
        detail = _get_ok(f"/api/work-orders/{work_order_public_id}", headers)
        for record in (listed, detail):
            _assert_display_name(record, "created_by_display_name", user["display_name"])

        response = client.post(
            f"/api/work-orders/{work_order_public_id}/amendments",
            headers=headers,
            json={
                "amendment_type_code": "ADMINISTRATIVE",
                "received_date": "2026-09-10",
                "amendment_reason": "Customer requested a site contact change.",
                "administrative_change_summary": "Site contact updated.",
                "customer_amendment_reference": f"UI-CLEANUP-AMD-{uuid4()}",
            },
        )
        assert response.status_code == 201, response.text
        amendment = response.json()["amendment"]
        amendment_public_id = str(amendment["public_id"])
        assert amendment["created_by"] == user["public_id"]

        amendment_list_url = f"/api/work-orders/{work_order_public_id}/amendments"
        amendment_listed = _find(_get_ok(amendment_list_url, headers), amendment_public_id)
        amendment_detail = _get_ok(f"{amendment_list_url}/{amendment_public_id}", headers)
        for record in (amendment, amendment_listed, amendment_detail):
            _assert_display_name(record, "created_by_display_name", user["display_name"])

        unknown_work_order_creator = _point_actors_at_unknown_user(
            table="crm_work_order",
            public_id_column="work_order_public_id",
            public_id=work_order_public_id,
            actor_columns=("created_by",),
        )
        unknown_amendment_creator = _point_actors_at_unknown_user(
            table="crm_work_order_amendment",
            public_id_column="amendment_public_id",
            public_id=amendment_public_id,
            actor_columns=("created_by",),
        )
        listed = _find(_get_ok(work_order_list_url, headers), work_order_public_id)
        assert listed["created_by"] == unknown_work_order_creator
        _assert_display_name(listed, "created_by_display_name", None)
        amendment_listed = _find(_get_ok(amendment_list_url, headers), amendment_public_id)
        assert amendment_listed["created_by"] == unknown_amendment_creator
        _assert_display_name(amendment_listed, "created_by_display_name", None)
    finally:
        _teardown(
            work_order_public_ids=work_order_public_ids,
            offer_public_ids=offer_public_ids,
            opportunity_public_ids=opportunity_public_ids,
            account_public_ids=account_public_ids,
            lead_public_ids=lead_public_ids,
        )
