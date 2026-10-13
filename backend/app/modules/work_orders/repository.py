from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.work_orders.contract import (
    WORK_ORDER_AMENDMENT_LINE_TABLE,
    WORK_ORDER_AMENDMENT_TABLE,
    WORK_ORDER_CONTRACT_EXTENSION_TABLE,
    WORK_ORDER_CONTRACT_PERIOD_TABLE,
    WORK_ORDER_HOLIDAY_LIST_TABLE,
    WORK_ORDER_HOLIDAY_TABLE,
    WORK_ORDER_LINE_BILLING_TERM_TABLE,
    WORK_ORDER_LINE_DETAIL_TABLE,
    WORK_ORDER_LINE_TABLE,
    WORK_ORDER_LINE_UPKEEP_COLUMNS,
    WORK_ORDER_REFERENCE_SPACE,
    WORK_ORDER_TABLE,
)
from app.modules.work_orders.schemas import (
    WorkOrderAmendmentLineResponse,
    WorkOrderAmendmentResponse,
    WorkOrderLineResponse,
    WorkOrderReadResponse,
    WorkOrderResponse,
)


WORK_ORDER_SELECT_COLUMNS = """
    wo.work_order_public_id AS public_id,
    wo.work_order_code,
    wo.work_order_title,
    wo.work_order_status_code,
    co.offer_public_id AS commercial_offer_public_id,
    co.offer_code AS commercial_offer_code,
    co.version_number AS commercial_offer_version_number,
    o.opportunity_public_id,
    bp.business_party_public_id AS account_public_id,
    wo.customer_wo_reference,
    wo.received_date,
    wo.source_offer_status_code,
    wo.remarks,
    wo.created_by,
    work_order_creator.display_name AS created_by_display_name,
    wo.created_at,
    wo.updated_at
"""

# Read-only display name for the creator id, resolved in the same query so a list stays one round
# trip. A LEFT JOIN, following QUOTE_DOCUMENT_ACTOR_JOINS in the commercial_offers repository: a
# Work Order whose creator id matches no app_user row still lists, with a NULL name.
WORK_ORDER_ACTOR_JOINS = """
    LEFT JOIN app_user work_order_creator ON work_order_creator.public_id = wo.created_by
"""

WORK_ORDER_LINE_SELECT_COLUMNS = """
    wol.work_order_line_public_id AS public_id,
    wo.work_order_public_id,
    col.line_public_id AS source_offer_line_public_id,
    col.line_number AS source_offer_line_number,
    wol.line_number,
    wol.line_status_code,
    wol.scope_description,
    wol.equipment_service_category,
    wol.quantity,
    wol.uom,
    wol.rate_amount,
    wol.currency_code,
    wol.line_amount,
    wol.remarks,
    wol.created_at,
    wol.updated_at
"""


def _row_mapping(row: Any) -> Any:
    return row._mapping if hasattr(row, "_mapping") else row


def _row_to_work_order(row: Any) -> WorkOrderReadResponse:
    # Always the read model: the handoff POST places it in a WorkOrderResponse field, whose declared
    # type governs serialization, so the frozen handoff output never carries the display name.
    data = _row_mapping(row)
    return WorkOrderReadResponse(
        public_id=data["public_id"],
        work_order_code=data["work_order_code"],
        work_order_title=data.get("work_order_title"),
        work_order_status_code=data["work_order_status_code"],
        commercial_offer_public_id=data["commercial_offer_public_id"],
        commercial_offer_code=data.get("commercial_offer_code"),
        commercial_offer_version_number=data.get("commercial_offer_version_number"),
        opportunity_public_id=data["opportunity_public_id"],
        account_public_id=data.get("account_public_id"),
        customer_wo_reference=data.get("customer_wo_reference"),
        received_date=data.get("received_date"),
        source_offer_status_code=data["source_offer_status_code"],
        remarks=data.get("remarks"),
        created_by=data.get("created_by"),
        created_by_display_name=data.get("created_by_display_name"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _row_to_work_order_line(row: Any) -> WorkOrderLineResponse:
    data = _row_mapping(row)
    return WorkOrderLineResponse(
        public_id=data["public_id"],
        work_order_public_id=data["work_order_public_id"],
        source_offer_line_public_id=data.get("source_offer_line_public_id"),
        source_offer_line_number=data.get("source_offer_line_number"),
        line_number=data["line_number"],
        line_status_code=data["line_status_code"],
        scope_description=data["scope_description"],
        equipment_service_category=data.get("equipment_service_category"),
        quantity=data["quantity"],
        uom=data["uom"],
        rate_amount=data.get("rate_amount"),
        currency_code=data["currency_code"],
        line_amount=data.get("line_amount"),
        remarks=data.get("remarks"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def get_commercial_offer_handoff_context(db: Session, commercial_offer_public_id: str) -> dict[str, Any] | None:
    """The offer as the handoff reads it, under the offer's row lock (CS-04 part 1).

    The latest customer response is the one the offer's own lifecycle view treats as latest: by the date the customer
    responded, then by entry (`list_commercial_offer_customer_responses_for_offer`), so the endpoint and the offer page
    agree on whether a Work Order may be created."""
    row = db.execute(
        text(
            """
            SELECT
                co.id AS commercial_offer_id,
                co.offer_public_id,
                co.offer_code,
                co.version_number,
                co.offer_title,
                co.offer_status_code,
                co.offer_purpose,
                (
                    SELECT response.response_outcome
                    FROM commercial_offer_customer_response response
                    WHERE response.commercial_offer_id = co.id
                    ORDER BY response.response_received_at DESC, response.created_at DESC, response.id DESC
                    LIMIT 1
                ) AS latest_customer_response_outcome,
                COALESCE(co.business_party_id, o.business_party_id) AS business_party_id,
                bp.business_party_public_id AS account_public_id,
                o.id AS opportunity_id,
                o.opportunity_public_id,
                o.opportunity_name
            FROM crm_commercial_offer co
            INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
            LEFT JOIN business_party bp ON bp.id = COALESCE(co.business_party_id, o.business_party_id)
            WHERE co.offer_public_id = :commercial_offer_public_id
            LIMIT 1
            """
        ),
        {"commercial_offer_public_id": commercial_offer_public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def list_active_offer_line_contexts(db: Session, commercial_offer_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
                line.id AS commercial_offer_line_id,
                line.line_public_id,
                line.line_number,
                line.line_status_code,
                line.scope_description,
                line.equipment_service_category,
                line.quantity,
                line.uom,
                line.rate_amount,
                line.currency_code,
                line.line_amount,
                line.remarks
            FROM crm_commercial_offer_line line
            WHERE line.commercial_offer_id = :commercial_offer_id
              AND line.line_status_code = 'ACTIVE'
            ORDER BY line.line_number ASC, line.id ASC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def list_offer_line_work_order_parts(db: Session, *, commercial_offer_line_ids: list[int]) -> list[dict[str, Any]]:
    """The Work Order lines already made from these offer lines: which Work Order, and how much of the line's quantity
    each holds (CS-04 part 1: an offer line's quantity goes onto Work Orders once, whole or in parts)."""
    if not commercial_offer_line_ids:
        return []
    rows = db.execute(
        text(
            f"""
            SELECT
                wol.commercial_offer_line_id,
                wol.quantity,
                COALESCE(wo.work_order_code, CAST(wo.work_order_public_id AS VARCHAR)) AS work_order_code
            FROM {WORK_ORDER_LINE_TABLE} wol
            INNER JOIN {WORK_ORDER_TABLE} wo ON wo.id = wol.work_order_id
            WHERE wol.commercial_offer_line_id = ANY(:commercial_offer_line_ids)
            ORDER BY wo.id ASC, wol.id ASC
            """
        ),
        {"commercial_offer_line_ids": commercial_offer_line_ids},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def find_work_order_with_customer_reference(db: Session, *, commercial_offer_id: int, reference: str) -> str | None:
    """The Work Order of this offer that already carries this customer reference, compared as migration
    20260908_0049's unique index compares it: without case or surrounding whitespace."""
    trim = f"'^[{WORK_ORDER_REFERENCE_SPACE}]+|[{WORK_ORDER_REFERENCE_SPACE}]+$', '', 'g'"
    value = db.execute(
        text(
            f"""
            SELECT COALESCE(work_order_code, CAST(work_order_public_id AS VARCHAR))
            FROM {WORK_ORDER_TABLE}
            WHERE commercial_offer_id = :commercial_offer_id
              AND lower(regexp_replace(customer_wo_reference, {trim})) = lower(regexp_replace(:reference, {trim}))
            ORDER BY id ASC
            LIMIT 1
            """
        ),
        {"commercial_offer_id": commercial_offer_id, "reference": reference},
    ).scalar()
    return str(value) if value is not None else None


def insert_work_order(
    db: Session,
    *,
    public_id: str,
    values: dict[str, Any],
) -> WorkOrderResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {WORK_ORDER_TABLE} (
                work_order_public_id,
                commercial_offer_id,
                opportunity_id,
                business_party_id,
                work_order_title,
                work_order_status_code,
                customer_wo_reference,
                received_date,
                source_offer_status_code,
                remarks,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :work_order_public_id,
                :commercial_offer_id,
                :opportunity_id,
                :business_party_id,
                :work_order_title,
                :work_order_status_code,
                :customer_wo_reference,
                :received_date,
                :source_offer_status_code,
                :remarks,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"work_order_public_id": public_id, **values},
    )
    db.execute(
        text(
            f"""
            UPDATE {WORK_ORDER_TABLE}
            SET work_order_code = 'WO-' || RIGHT('000000' || CAST(id AS VARCHAR(20)), 6)
            WHERE work_order_public_id = :work_order_public_id
              AND work_order_code IS NULL
            """
        ),
        {"work_order_public_id": public_id},
    )
    work_order = get_work_order_by_public_id(db, public_id)
    if work_order is None:
        raise RuntimeError("Inserted Work Order could not be reloaded.")
    return work_order


def insert_work_order_line(
    db: Session,
    *,
    public_id: str,
    work_order_id: int,
    values: dict[str, Any],
) -> None:
    db.execute(
        text(
            f"""
            INSERT INTO {WORK_ORDER_LINE_TABLE} (
                work_order_line_public_id,
                work_order_id,
                commercial_offer_line_id,
                line_number,
                line_status_code,
                scope_description,
                equipment_service_category,
                quantity,
                uom,
                rate_amount,
                currency_code,
                line_amount,
                remarks,
                created_at,
                updated_at
            ) VALUES (
                :work_order_line_public_id,
                :work_order_id,
                :commercial_offer_line_id,
                :line_number,
                :line_status_code,
                :scope_description,
                :equipment_service_category,
                :quantity,
                :uom,
                :rate_amount,
                :currency_code,
                :line_amount,
                :remarks,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"work_order_line_public_id": public_id, "work_order_id": work_order_id, **values},
    )


def list_related_commercial_offer_contexts(db: Session, work_order_id: int) -> list[dict[str, Any]]:
    """Read-only cross-module lookup (raw SQL, mirrors get_commercial_offer_handoff_context
    above) of Slice 6O.1 Supplementary Offers / Change Quotations linked to this Work Order
    via crm_commercial_offer.related_work_order_id. Never writes to crm_commercial_offer."""
    rows = db.execute(
        text(
            """
            SELECT
                co.offer_public_id AS public_id,
                co.offer_code,
                co.offer_purpose,
                co.offer_status_code,
                base_offer.offer_public_id AS base_offer_public_id,
                base_offer.offer_code AS base_offer_code,
                co.customer_request_summary,
                co.created_at
            FROM crm_commercial_offer co
            LEFT JOIN crm_commercial_offer base_offer ON base_offer.id = co.base_offer_id
            WHERE co.related_work_order_id = :work_order_id
            ORDER BY co.created_at DESC, co.id DESC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def get_work_order_internal_id(db: Session, work_order_public_id: str) -> int | None:
    value = db.execute(
        text(f"SELECT id FROM {WORK_ORDER_TABLE} WHERE work_order_public_id = :work_order_public_id"),
        {"work_order_public_id": work_order_public_id},
    ).scalar()
    return int(value) if value is not None else None


def get_work_order_by_public_id(db: Session, public_id: str) -> WorkOrderResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT {WORK_ORDER_SELECT_COLUMNS}
            FROM {WORK_ORDER_TABLE} wo
            INNER JOIN crm_commercial_offer co ON co.id = wo.commercial_offer_id
            INNER JOIN crm_opportunity o ON o.id = wo.opportunity_id
            LEFT JOIN business_party bp ON bp.id = wo.business_party_id
            {WORK_ORDER_ACTOR_JOINS}
            WHERE wo.work_order_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_work_order(row) if row else None


def list_recent_work_orders(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    commercial_offer_public_id: str | None = None,
) -> list[WorkOrderResponse]:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    filters: list[str] = []
    params: dict[str, Any] = {}

    if commercial_offer_public_id:
        filters.append("co.offer_public_id = :commercial_offer_public_id")
        params["commercial_offer_public_id"] = commercial_offer_public_id

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        text(
            f"""
            SELECT {WORK_ORDER_SELECT_COLUMNS}
            FROM {WORK_ORDER_TABLE} wo
            INNER JOIN crm_commercial_offer co ON co.id = wo.commercial_offer_id
            INNER JOIN crm_opportunity o ON o.id = wo.opportunity_id
            LEFT JOIN business_party bp ON bp.id = wo.business_party_id
            {WORK_ORDER_ACTOR_JOINS}
            {where_clause}
            ORDER BY wo.created_at DESC, wo.id DESC
            LIMIT {safe_limit} OFFSET {safe_offset}
            """
        ),
        params,
    ).fetchall()
    return [_row_to_work_order(row) for row in rows]


def list_work_order_lines_by_public_id(db: Session, public_id: str) -> list[WorkOrderLineResponse] | None:
    work_order = get_work_order_by_public_id(db, public_id)
    if work_order is None:
        return None

    rows = db.execute(
        text(
            f"""
            SELECT {WORK_ORDER_LINE_SELECT_COLUMNS}
            FROM {WORK_ORDER_LINE_TABLE} wol
            INNER JOIN {WORK_ORDER_TABLE} wo ON wo.id = wol.work_order_id
            LEFT JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
            WHERE wo.work_order_public_id = :public_id
            ORDER BY wol.line_number ASC, wol.id ASC
            """
        ),
        {"public_id": public_id},
    ).fetchall()
    return [_row_to_work_order_line(row) for row in rows]


# --- Slice 6O.2 Work Order Amendment intake foundation -----------------------------------

WORK_ORDER_AMENDMENT_SELECT_COLUMNS = """
    wa.amendment_public_id AS public_id,
    wo.work_order_public_id,
    wo.work_order_code,
    wa.amendment_sequence_no,
    wa.amendment_type_code,
    wa.amendment_status_code,
    wa.customer_amendment_reference,
    wa.customer_amendment_date,
    wa.received_date,
    wa.effective_date,
    wa.amendment_reason,
    wa.administrative_change_summary,
    wa.commercial_change_summary,
    rel.offer_public_id AS related_commercial_offer_public_id,
    rel.offer_code AS related_commercial_offer_code,
    rel.offer_purpose AS related_commercial_offer_purpose,
    rel.offer_status_code AS related_commercial_offer_status_code,
    wa.customer_document_reference,
    wa.decision_notes,
    wa.reviewed_at,
    wa.validated_at,
    wa.rejected_at,
    wa.cancelled_at,
    wa.decided_by,
    wa.remarks,
    wa.created_by,
    amendment_creator.display_name AS created_by_display_name,
    wa.created_at,
    wa.updated_at
"""

WORK_ORDER_AMENDMENT_LINE_SELECT_COLUMNS = """
    wal.amendment_line_public_id AS public_id,
    wa.amendment_public_id,
    wal.line_number,
    wal.action_code,
    swol.work_order_line_public_id AS source_work_order_line_public_id,
    wal.change_summary,
    wal.proposed_scope_description,
    wal.proposed_equipment_service_category,
    wal.proposed_quantity,
    wal.proposed_uom,
    wal.proposed_rate_amount,
    wal.proposed_currency_code,
    wal.proposed_amount,
    wal.original_scope_description,
    wal.original_equipment_service_category,
    wal.original_quantity,
    wal.original_uom,
    wal.original_rate_amount,
    wal.original_currency_code,
    wal.original_amount,
    wal.original_source_offer_line_public_id,
    wal.created_by,
    wal.created_at,
    wal.updated_at
"""


def _amendment_select_from() -> str:
    # The app_user LEFT JOIN resolves created_by_display_name read-only, like
    # WORK_ORDER_ACTOR_JOINS: an amendment whose creator id matches no user still lists.
    return f"""
        FROM {WORK_ORDER_AMENDMENT_TABLE} wa
        INNER JOIN {WORK_ORDER_TABLE} wo ON wo.id = wa.work_order_id
        LEFT JOIN crm_commercial_offer rel ON rel.id = wa.related_commercial_offer_id
        LEFT JOIN app_user amendment_creator ON amendment_creator.public_id = wa.created_by
    """


def _amendment_line_select_from() -> str:
    return f"""
        FROM {WORK_ORDER_AMENDMENT_LINE_TABLE} wal
        INNER JOIN {WORK_ORDER_AMENDMENT_TABLE} wa ON wa.id = wal.amendment_id
        LEFT JOIN {WORK_ORDER_LINE_TABLE} swol ON swol.id = wal.source_work_order_line_id
    """


def _row_to_amendment(row: Any) -> WorkOrderAmendmentResponse:
    data = _row_mapping(row)
    return WorkOrderAmendmentResponse(
        public_id=data["public_id"],
        work_order_public_id=data["work_order_public_id"],
        work_order_code=data["work_order_code"],
        amendment_sequence_no=data["amendment_sequence_no"],
        amendment_type_code=data["amendment_type_code"],
        amendment_status_code=data["amendment_status_code"],
        customer_amendment_reference=data.get("customer_amendment_reference"),
        customer_amendment_date=data.get("customer_amendment_date"),
        received_date=data["received_date"],
        effective_date=data.get("effective_date"),
        amendment_reason=data["amendment_reason"],
        administrative_change_summary=data.get("administrative_change_summary"),
        commercial_change_summary=data.get("commercial_change_summary"),
        related_commercial_offer_public_id=data.get("related_commercial_offer_public_id"),
        related_commercial_offer_code=data.get("related_commercial_offer_code"),
        related_commercial_offer_purpose=data.get("related_commercial_offer_purpose"),
        related_commercial_offer_status_code=data.get("related_commercial_offer_status_code"),
        customer_document_reference=data.get("customer_document_reference"),
        decision_notes=data.get("decision_notes"),
        reviewed_at=data.get("reviewed_at"),
        validated_at=data.get("validated_at"),
        rejected_at=data.get("rejected_at"),
        cancelled_at=data.get("cancelled_at"),
        decided_by=data.get("decided_by"),
        remarks=data.get("remarks"),
        created_by=data.get("created_by"),
        created_by_display_name=data.get("created_by_display_name"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _row_to_amendment_line(row: Any) -> WorkOrderAmendmentLineResponse:
    data = _row_mapping(row)
    return WorkOrderAmendmentLineResponse(
        public_id=data["public_id"],
        amendment_public_id=data["amendment_public_id"],
        line_number=data["line_number"],
        action_code=data["action_code"],
        source_work_order_line_public_id=data.get("source_work_order_line_public_id"),
        change_summary=data.get("change_summary"),
        proposed_scope_description=data.get("proposed_scope_description"),
        proposed_equipment_service_category=data.get("proposed_equipment_service_category"),
        proposed_quantity=data.get("proposed_quantity"),
        proposed_uom=data.get("proposed_uom"),
        proposed_rate_amount=data.get("proposed_rate_amount"),
        proposed_currency_code=data.get("proposed_currency_code"),
        proposed_amount=data.get("proposed_amount"),
        original_scope_description=data.get("original_scope_description"),
        original_equipment_service_category=data.get("original_equipment_service_category"),
        original_quantity=data.get("original_quantity"),
        original_uom=data.get("original_uom"),
        original_rate_amount=data.get("original_rate_amount"),
        original_currency_code=data.get("original_currency_code"),
        original_amount=data.get("original_amount"),
        original_source_offer_line_public_id=data.get("original_source_offer_line_public_id"),
        created_by=data.get("created_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def get_related_offer_context_for_amendment(db: Session, offer_public_id: str) -> dict[str, Any] | None:
    """Read-only cross-module lookup (raw SQL, no import of the commercial_offers module -
    matches the existing get_work_order_lineage_context / list_related_commercial_offer_contexts
    pattern) used only to validate that a Commercial Offer named as an amendment's commercial
    basis is a genuine Slice 6O.1 related offer already linked to a Work Order, and to read its
    live status/lineage at validation time."""
    row = db.execute(
        text(
            """
            SELECT
                co.id AS commercial_offer_id,
                co.offer_public_id,
                co.offer_code,
                co.offer_purpose,
                co.offer_status_code,
                co.opportunity_id,
                co.business_party_id,
                co.related_work_order_id
            FROM crm_commercial_offer co
            WHERE co.offer_public_id = :offer_public_id
            LIMIT 1
            """
        ),
        {"offer_public_id": offer_public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def get_work_order_lineage_ids(db: Session, *, work_order_id: int) -> dict[str, Any] | None:
    """Internal opportunity/account ids for the given Work Order, used only as a
    defense-in-depth cross-check (mirrors the existing opportunity/business_party
    comparison in commercial_offers.service._validate_related_work_order) alongside the
    primary related_work_order_id equality check."""
    row = db.execute(
        text("SELECT opportunity_id, business_party_id FROM crm_work_order WHERE id = :work_order_id"),
        {"work_order_id": work_order_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def get_work_order_line_reference_row(db: Session, *, line_public_id: str) -> dict[str, Any] | None:
    """One line and the Work Order it belongs to, found by the line's public id alone (WRR-001).

    Read-only. A Resource Requirement is created for a line, and this is how it learns which Work Order
    that is without reading a Work Order table itself."""
    row = db.execute(
        text(
            """
            SELECT
                wol.id AS work_order_line_id,
                wol.work_order_line_public_id,
                wol.line_number,
                wol.equipment_service_category,
                col.line_public_id AS source_offer_line_public_id,
                wo.work_order_public_id,
                wo.work_order_code,
                wo.work_order_status_code,
                bp.business_party_public_id AS account_public_id
            FROM crm_work_order_line wol
            INNER JOIN crm_work_order wo ON wo.id = wol.work_order_id
            LEFT JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
            LEFT JOIN business_party bp ON bp.id = wo.business_party_id
            WHERE wol.work_order_line_public_id = :line_public_id
            LIMIT 1
            """
        ),
        {"line_public_id": line_public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def get_work_order_line_context(db: Session, *, work_order_id: int, line_public_id: str) -> dict[str, Any] | None:
    """Read-only lookup used to validate that a source line referenced by CHANGE_LINE /
    CANCEL_LINE belongs to the amendment's own Work Order, and to capture an original-value
    snapshot at intake time. Never used to write to crm_work_order_line."""
    row = db.execute(
        text(
            """
            SELECT
                wol.id AS work_order_line_id,
                wol.work_order_line_public_id,
                wol.scope_description,
                wol.equipment_service_category,
                wol.quantity,
                wol.uom,
                wol.rate_amount,
                wol.currency_code,
                wol.line_amount,
                col.line_public_id AS source_offer_line_public_id
            FROM crm_work_order_line wol
            LEFT JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
            WHERE wol.work_order_id = :work_order_id
              AND wol.work_order_line_public_id = :line_public_id
            LIMIT 1
            """
        ),
        {"work_order_id": work_order_id, "line_public_id": line_public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def get_next_amendment_sequence_no(db: Session, *, work_order_id: int) -> int:
    value = db.execute(
        text(f"SELECT COALESCE(MAX(amendment_sequence_no), 0) FROM {WORK_ORDER_AMENDMENT_TABLE} WHERE work_order_id = :work_order_id"),
        {"work_order_id": work_order_id},
    ).scalar_one()
    return int(value) + 1


def get_work_order_amendment_by_reference(
    db: Session,
    *,
    work_order_id: int,
    customer_amendment_reference: str,
) -> WorkOrderAmendmentResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT {WORK_ORDER_AMENDMENT_SELECT_COLUMNS}
            {_amendment_select_from()}
            WHERE wa.work_order_id = :work_order_id
              AND wa.customer_amendment_reference = :customer_amendment_reference
            LIMIT 1
            """
        ),
        {"work_order_id": work_order_id, "customer_amendment_reference": customer_amendment_reference},
    ).first()
    return _row_to_amendment(row) if row else None


def get_amendment_internal_id(db: Session, *, work_order_id: int, public_id: str) -> int | None:
    value = db.execute(
        text(
            f"""
            SELECT id FROM {WORK_ORDER_AMENDMENT_TABLE}
            WHERE work_order_id = :work_order_id AND amendment_public_id = :public_id
            """
        ),
        {"work_order_id": work_order_id, "public_id": public_id},
    ).scalar()
    return int(value) if value is not None else None


def insert_work_order_amendment(
    db: Session,
    *,
    public_id: str,
    work_order_id: int,
    values: dict[str, Any],
) -> WorkOrderAmendmentResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {WORK_ORDER_AMENDMENT_TABLE} (
                amendment_public_id,
                work_order_id,
                amendment_sequence_no,
                amendment_type_code,
                amendment_status_code,
                customer_amendment_reference,
                customer_amendment_date,
                received_date,
                effective_date,
                amendment_reason,
                administrative_change_summary,
                commercial_change_summary,
                related_commercial_offer_id,
                customer_document_reference,
                remarks,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :amendment_public_id,
                :work_order_id,
                :amendment_sequence_no,
                :amendment_type_code,
                :amendment_status_code,
                :customer_amendment_reference,
                :customer_amendment_date,
                :received_date,
                :effective_date,
                :amendment_reason,
                :administrative_change_summary,
                :commercial_change_summary,
                :related_commercial_offer_id,
                :customer_document_reference,
                :remarks,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"amendment_public_id": public_id, "work_order_id": work_order_id, **values},
    )
    amendment = get_work_order_amendment_for_work_order(db, work_order_id=work_order_id, public_id=public_id)
    if amendment is None:
        raise RuntimeError("Inserted Work Order Amendment could not be reloaded.")
    return amendment


def get_work_order_amendment_for_work_order(
    db: Session,
    *,
    work_order_id: int,
    public_id: str,
) -> WorkOrderAmendmentResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT {WORK_ORDER_AMENDMENT_SELECT_COLUMNS}
            {_amendment_select_from()}
            WHERE wa.work_order_id = :work_order_id
              AND wa.amendment_public_id = :public_id
            """
        ),
        {"work_order_id": work_order_id, "public_id": public_id},
    ).first()
    return _row_to_amendment(row) if row else None


def list_work_order_amendments_for_work_order(db: Session, *, work_order_id: int) -> list[WorkOrderAmendmentResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT {WORK_ORDER_AMENDMENT_SELECT_COLUMNS}
            {_amendment_select_from()}
            WHERE wa.work_order_id = :work_order_id
            ORDER BY wa.amendment_sequence_no DESC, wa.id DESC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    return [_row_to_amendment(row) for row in rows]


def update_work_order_amendment_header(
    db: Session,
    *,
    work_order_id: int,
    public_id: str,
    values: dict[str, Any],
) -> WorkOrderAmendmentResponse | None:
    if not values:
        return get_work_order_amendment_for_work_order(db, work_order_id=work_order_id, public_id=public_id)

    assignments = ", ".join(f"{column} = :{column}" for column in values)
    db.execute(
        text(
            f"""
            UPDATE {WORK_ORDER_AMENDMENT_TABLE}
            SET {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE work_order_id = :work_order_id
              AND amendment_public_id = :public_id
            """
        ),
        {"work_order_id": work_order_id, "public_id": public_id, **values},
    )
    return get_work_order_amendment_for_work_order(db, work_order_id=work_order_id, public_id=public_id)


def apply_work_order_amendment_decision(
    db: Session,
    *,
    work_order_id: int,
    public_id: str,
    expected_status: str,
    new_status: str,
    decided_by: str | None,
    decision_notes: str | None,
    timestamp_column: str | None,
) -> WorkOrderAmendmentResponse | None:
    timestamp_assignment = f"{timestamp_column} = CURRENT_TIMESTAMP," if timestamp_column else ""
    result = db.execute(
        text(
            f"""
            UPDATE {WORK_ORDER_AMENDMENT_TABLE}
            SET amendment_status_code = :new_status,
                decision_notes = :decision_notes,
                decided_by = :decided_by,
                {timestamp_assignment}
                updated_at = CURRENT_TIMESTAMP
            WHERE work_order_id = :work_order_id
              AND amendment_public_id = :public_id
              AND amendment_status_code = :expected_status
            """
        ),
        {
            "work_order_id": work_order_id,
            "public_id": public_id,
            "expected_status": expected_status,
            "new_status": new_status,
            "decided_by": decided_by,
            "decision_notes": decision_notes,
        },
    )
    if result.rowcount == 0:
        return None
    return get_work_order_amendment_for_work_order(db, work_order_id=work_order_id, public_id=public_id)


def get_next_amendment_line_number(db: Session, *, amendment_id: int) -> int:
    value = db.execute(
        text(
            f"SELECT COALESCE(MAX(line_number), 0) FROM {WORK_ORDER_AMENDMENT_LINE_TABLE} WHERE amendment_id = :amendment_id"
        ),
        {"amendment_id": amendment_id},
    ).scalar_one()
    return int(value) + 1


def insert_work_order_amendment_line(
    db: Session,
    *,
    public_id: str,
    amendment_id: int,
    values: dict[str, Any],
) -> WorkOrderAmendmentLineResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {WORK_ORDER_AMENDMENT_LINE_TABLE} (
                amendment_line_public_id,
                amendment_id,
                line_number,
                action_code,
                source_work_order_line_id,
                change_summary,
                proposed_scope_description,
                proposed_equipment_service_category,
                proposed_quantity,
                proposed_uom,
                proposed_rate_amount,
                proposed_currency_code,
                proposed_amount,
                original_scope_description,
                original_equipment_service_category,
                original_quantity,
                original_uom,
                original_rate_amount,
                original_currency_code,
                original_amount,
                original_source_offer_line_public_id,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :amendment_line_public_id,
                :amendment_id,
                :line_number,
                :action_code,
                :source_work_order_line_id,
                :change_summary,
                :proposed_scope_description,
                :proposed_equipment_service_category,
                :proposed_quantity,
                :proposed_uom,
                :proposed_rate_amount,
                :proposed_currency_code,
                :proposed_amount,
                :original_scope_description,
                :original_equipment_service_category,
                :original_quantity,
                :original_uom,
                :original_rate_amount,
                :original_currency_code,
                :original_amount,
                :original_source_offer_line_public_id,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"amendment_line_public_id": public_id, "amendment_id": amendment_id, **values},
    )
    line = get_amendment_line_for_amendment(db, amendment_id=amendment_id, public_id=public_id)
    if line is None:
        raise RuntimeError("Inserted Work Order Amendment line could not be reloaded.")
    return line


def get_amendment_line_for_amendment(
    db: Session,
    *,
    amendment_id: int,
    public_id: str,
) -> WorkOrderAmendmentLineResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT {WORK_ORDER_AMENDMENT_LINE_SELECT_COLUMNS}
            {_amendment_line_select_from()}
            WHERE wal.amendment_id = :amendment_id
              AND wal.amendment_line_public_id = :public_id
            """
        ),
        {"amendment_id": amendment_id, "public_id": public_id},
    ).first()
    return _row_to_amendment_line(row) if row else None


def list_amendment_lines_for_amendment(db: Session, *, amendment_id: int) -> list[WorkOrderAmendmentLineResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT {WORK_ORDER_AMENDMENT_LINE_SELECT_COLUMNS}
            {_amendment_line_select_from()}
            WHERE wal.amendment_id = :amendment_id
            ORDER BY wal.line_number ASC, wal.id ASC
            """
        ),
        {"amendment_id": amendment_id},
    ).fetchall()
    return [_row_to_amendment_line(row) for row in rows]


def update_amendment_line(
    db: Session,
    *,
    amendment_id: int,
    public_id: str,
    values: dict[str, Any],
) -> WorkOrderAmendmentLineResponse | None:
    if not values:
        return get_amendment_line_for_amendment(db, amendment_id=amendment_id, public_id=public_id)

    assignments = ", ".join(f"{column} = :{column}" for column in values)
    db.execute(
        text(
            f"""
            UPDATE {WORK_ORDER_AMENDMENT_LINE_TABLE}
            SET {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE amendment_id = :amendment_id
              AND amendment_line_public_id = :public_id
            """
        ),
        {"amendment_id": amendment_id, "public_id": public_id, **values},
    )
    return get_amendment_line_for_amendment(db, amendment_id=amendment_id, public_id=public_id)


def delete_amendment_line(db: Session, *, amendment_id: int, public_id: str) -> bool:
    result = db.execute(
        text(
            f"""
            DELETE FROM {WORK_ORDER_AMENDMENT_LINE_TABLE}
            WHERE amendment_id = :amendment_id
              AND amendment_line_public_id = :public_id
            """
        ),
        {"amendment_id": amendment_id, "public_id": public_id},
    )
    return result.rowcount > 0


def lock_commercial_offer_row(db: Session, *, commercial_offer_public_id: str) -> int | None:
    """Row-lock the source Commercial Offer for the current transaction.

    Work Order handoff reads the offer's status, requires ACCEPTED, and then inserts a Work Order
    shell. Without the lock a concurrent customer response can commit REJECTED between that read
    and the insert, producing a shell against an offer that is no longer accepted.

    This module already reads `crm_commercial_offer` directly for the handoff context, so the
    lock is taken here rather than by importing the Commercial Offer module's repository.
    """
    row = db.execute(
        text(
            """
            SELECT id
            FROM crm_commercial_offer
            WHERE offer_public_id = :public_id
            FOR UPDATE
            """
        ),
        {"public_id": commercial_offer_public_id},
    ).first()
    return int(row[0]) if row is not None else None


def lock_work_order_amendment_row(db: Session, *, work_order_id: int, public_id: str) -> int | None:
    """Row-lock one Work Order Amendment for the current transaction.

    The amendment is the aggregate root for its own header, its related-offer link and its lines.
    Every path that reads amendment status or readiness inputs and then writes - the header
    update, the decision, and the three line mutations - takes this lock first, so header and
    line changes cannot interleave with readiness evaluation.

    Locking the header row is sufficient for the lines too: a line mutation must acquire this
    same lock before it reads, so it serializes behind any in-flight decision.
    """
    row = db.execute(
        text(
            """
            SELECT id
            FROM crm_work_order_amendment
            WHERE work_order_id = :work_order_id
              AND amendment_public_id = :public_id
            FOR UPDATE
            """
        ),
        {"work_order_id": work_order_id, "public_id": public_id},
    ).first()
    return int(row[0]) if row is not None else None

def lock_work_order_row(db: Session, *, public_id: str) -> int | None:
    """Row-lock one Work Order for the current transaction.

    Amendment *creation* cannot lock the amendment row it is about to insert, so it locks the
    parent Work Order instead. Two invariants are computed by reading that Work Order's existing
    amendments and then inserting:

    - `amendment_sequence_no` is `MAX(...) + 1` for the Work Order, protected by the
      `uq_crm_work_order_amendment_wo_sequence` unique constraint;
    - `customer_amendment_reference` must be unique per Work Order, protected by the
      `ux_crm_work_order_amendment_customer_reference` partial unique index.

    Without this lock two concurrent valid intakes read the same maximum and the same "no
    duplicate reference" answer, and the second insert fails on a constraint the user never
    violated - surfacing as an unhandled database error rather than a business message.
    Serializing creation per Work Order makes the second request compute the next sequence,
    or report the duplicate reference properly.
    """
    row = db.execute(
        text(f"SELECT id FROM {WORK_ORDER_TABLE} WHERE work_order_public_id = :public_id FOR UPDATE"),
        {"public_id": public_id},
    ).first()
    return int(row[0]) if row is not None else None


def share_lock_work_order_status(db: Session, *, public_id: str) -> str | None:
    """A Work Order's status under a shared row lock held for the current transaction (8A core): writes of other
    modules' records that belong to a Work Order take it, so a change to the Work Order - which takes the row's
    update lock - waits for them, and they see it once it is committed."""
    row = db.execute(
        text(f"SELECT work_order_status_code FROM {WORK_ORDER_TABLE} WHERE work_order_public_id = :public_id FOR SHARE"),
        {"public_id": public_id},
    ).first()
    return str(row[0]) if row is not None else None


# --- Slice 7C Work Order line operational detail -------------------------------------------
# Reads and writes crm_work_order_line_detail only. crm_work_order_line is read, never written.
# No join reaches into Account tables: the Account references are stored as public ids and the
# service resolves them through the accounts service.

WORK_ORDER_LINE_DETAIL_COLUMNS = (
    "site_address_public_id",
    "billing_gstin_public_id",
    "billing_address_public_id",
    "customer_line_reference",
    "operational_notes",
    # Slice 7D Part 3: the line's own dates inside the contract period. Blank means the line follows
    # the Work Order (owner decision 13).
    "line_start_date",
    "line_end_date",
    # 8A core: whether the site is a central-government site (ELG-1 Q8); null is not answered.
    "site_central_government",
)


def list_work_order_line_detail_rows(db: Session, *, work_order_id: int) -> list[dict[str, Any]]:
    """One row per Work Order line, in line order, with detail columns null where none recorded."""
    rows = db.execute(
        text(
            f"""
            SELECT
                wol.id AS work_order_line_id,
                wol.work_order_line_public_id,
                wol.line_number,
                col.line_public_id AS source_offer_line_public_id,
                d.work_order_line_detail_public_id AS detail_public_id,
                d.detail_version,
                {", ".join(f"d.{column}" for column in WORK_ORDER_LINE_DETAIL_COLUMNS)},
                d.updated_by,
                detail_updater.display_name AS updated_by_display_name,
                d.updated_at
            FROM {WORK_ORDER_LINE_TABLE} wol
            LEFT JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
            LEFT JOIN {WORK_ORDER_LINE_DETAIL_TABLE} d ON d.work_order_line_id = wol.id
            LEFT JOIN app_user detail_updater ON detail_updater.public_id = d.updated_by
            WHERE wol.work_order_id = :work_order_id
            ORDER BY wol.line_number ASC, wol.id ASC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def get_work_order_line_detail_row(db: Session, *, work_order_line_id: int) -> dict[str, Any] | None:
    row = db.execute(
        text(
            f"""
            SELECT work_order_line_detail_public_id, detail_version, {", ".join(WORK_ORDER_LINE_DETAIL_COLUMNS)}
            FROM {WORK_ORDER_LINE_DETAIL_TABLE}
            WHERE work_order_line_id = :work_order_line_id
            """
        ),
        {"work_order_line_id": work_order_line_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def insert_work_order_line_detail(
    db: Session,
    *,
    public_id: str,
    work_order_line_id: int,
    values: dict[str, Any],
    current_user_public_id: str | None,
) -> None:
    columns = ", ".join(WORK_ORDER_LINE_DETAIL_COLUMNS)
    binds = ", ".join(f":{column}" for column in WORK_ORDER_LINE_DETAIL_COLUMNS)
    db.execute(
        text(
            f"""
            INSERT INTO {WORK_ORDER_LINE_DETAIL_TABLE} (
                work_order_line_detail_public_id, work_order_line_id, {columns},
                detail_version, created_by, created_at, updated_by, updated_at
            ) VALUES (
                :public_id, :work_order_line_id, {binds},
                1, :user_public_id, CURRENT_TIMESTAMP, :user_public_id, CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "public_id": public_id,
            "work_order_line_id": work_order_line_id,
            "user_public_id": current_user_public_id,
            **{column: values.get(column) for column in WORK_ORDER_LINE_DETAIL_COLUMNS},
        },
    )


def update_work_order_line_detail(
    db: Session,
    *,
    work_order_line_id: int,
    expected_detail_version: int,
    values: dict[str, Any],
    current_user_public_id: str | None,
) -> int:
    """Replace the detail and move to the next version. Guarded on the expected version as well as
    by the caller's Work Order lock, so a write can never land on a version it did not read.
    Returns the number of rows updated (0 means the version moved underneath the caller)."""
    assignments = ", ".join(f"{column} = :{column}" for column in WORK_ORDER_LINE_DETAIL_COLUMNS)
    result = db.execute(
        text(
            f"""
            UPDATE {WORK_ORDER_LINE_DETAIL_TABLE}
            SET {assignments},
                detail_version = detail_version + 1,
                updated_by = :user_public_id,
                updated_at = CURRENT_TIMESTAMP
            WHERE work_order_line_id = :work_order_line_id
              AND detail_version = :expected_detail_version
            """
        ),
        {
            "work_order_line_id": work_order_line_id,
            "expected_detail_version": expected_detail_version,
            "user_public_id": current_user_public_id,
            **{column: values.get(column) for column in WORK_ORDER_LINE_DETAIL_COLUMNS},
        },
    )
    return int(result.rowcount or 0)


# --- Slice 7D Work Order line billing terms ----------------------------------------------------
# Reads and writes crm_work_order_line_billing_term only. crm_work_order_line is read, never written.

WORK_ORDER_LINE_BILLING_TERM_COLUMNS = (
    "effective_from",
    "billing_uom_code",
    "contracted_hours_per_billing_unit",
    "contracted_working_days_per_month",
    "normal_rate_amount",
    "weekly_off_day_codes",
    "off_day_work_treatment_code",
    "holiday_rate_method_code",
    "holiday_rate_amount",
    "holiday_rate_percent",
    "overtime_rate_method_code",
    "overtime_rate_amount",
    "overtime_rate_percent",
    "month_overtime_hours_basis_code",
    "month_overtime_counting_code",
    "breakdown_treatment_code",
    "breakdown_rate_method_code",
    "breakdown_rate_amount",
    "breakdown_rate_percent",
    "breakdown_offset_by_same_day_overtime",
    "customer_idle_treatment_code",
    "standby_rate_method_code",
    "standby_rate_amount",
    "standby_rate_percent",
    "minimum_guarantee_code",
    "minimum_billing_units_per_month",
    "part_month_basis_code",
    # Slice 7D Part 5. The shift pattern belongs to each period; it took the place of Part 2's night shift.
    "shift_pattern_code",
    "shift_1_hours",
    "shift_2_hours",
    "shift_3_hours",
    "shift_rate_code",
    "shift_2_rate_method_code",
    "shift_2_rate_amount",
    "shift_2_rate_percent",
    "shift_2_working_days_per_month",
    "shift_3_rate_method_code",
    "shift_3_rate_amount",
    "shift_3_rate_percent",
    "shift_3_working_days_per_month",
    "overtime_counted_per_code",
    # Slice 7D Part 2. Fuel belongs to each period; mobilisation and demobilisation are recorded on
    # period 1 only, because they describe the whole line (owner decision 8).
    "mobilisation_charge_code",
    "mobilisation_charge_amount",
    "mobilisation_credit_after_months",
    "demobilisation_charge_code",
    "demobilisation_charge_amount",
    "demobilisation_waived_after_months",
    "fuel_treatment_code",
    "fuel_charge_method_code",
    "fuel_rate_per_litre_amount",
    "fuel_litres_per_working_hour",
    "fuel_travel_allowance_code",
    "fuel_litres_per_travel_hour",
    # Slice 7D Part 4. Extra kilometres and crew belong to each period.
    "extra_km_allowance_code",
    "extra_km_included_km",
    "extra_km_rate_amount",
    "crew_code",
    "crew_operators_per_unit",
    "crew_helpers_per_unit",
    "extra_crew_charge_code",
    "extra_crew_operator_rate_amount",
    "extra_crew_helper_rate_amount",
    # Slice 7D Part 5. The crew's food, accommodation and travel, for operators and helpers.
    *WORK_ORDER_LINE_UPKEEP_COLUMNS,
    "term_notes",
)

_BILLING_TERM_SELECT = f"""
    t.id AS term_id,
    t.work_order_line_id,
    t.work_order_line_billing_term_public_id AS term_public_id,
    t.period_number,
    t.term_revision,
    t.currency_code,
    {", ".join(f"t.{column}" for column in WORK_ORDER_LINE_BILLING_TERM_COLUMNS)},
    -- Slice 7D Part 5: a Part 2 night shift "not in the Work Order", kept by the migration; read, never written.
    t.legacy_night_shift_not_in_work_order,
    t.updated_by,
    term_updater.display_name AS updated_by_display_name,
    t.updated_at
"""


def list_work_order_billing_term_lines(db: Session, *, work_order_id: int) -> list[dict[str, Any]]:
    """Every line of the Work Order in line order, with the quoted unit and rate the handoff copied."""
    rows = db.execute(
        text(
            f"""
            SELECT
                wol.id AS work_order_line_id,
                wol.work_order_line_public_id,
                wol.line_number,
                col.line_public_id AS source_offer_line_public_id,
                wol.uom AS quoted_uom,
                wol.rate_amount AS quoted_rate_amount
            FROM {WORK_ORDER_LINE_TABLE} wol
            LEFT JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
            WHERE wol.work_order_id = :work_order_id
            ORDER BY wol.line_number ASC, wol.id ASC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def list_work_order_billing_term_rows(db: Session, *, work_order_id: int) -> list[dict[str, Any]]:
    """Every billing-term period of every line of the Work Order, ordered by line then period."""
    rows = db.execute(
        text(
            f"""
            SELECT {_BILLING_TERM_SELECT}
            FROM {WORK_ORDER_LINE_BILLING_TERM_TABLE} t
            INNER JOIN {WORK_ORDER_LINE_TABLE} wol ON wol.id = t.work_order_line_id
            LEFT JOIN app_user term_updater ON term_updater.public_id = t.updated_by
            WHERE wol.work_order_id = :work_order_id
            ORDER BY t.work_order_line_id ASC, t.period_number ASC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def list_billing_term_rows_for_line(db: Session, *, work_order_line_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            f"""
            SELECT {_BILLING_TERM_SELECT}
            FROM {WORK_ORDER_LINE_BILLING_TERM_TABLE} t
            LEFT JOIN app_user term_updater ON term_updater.public_id = t.updated_by
            WHERE t.work_order_line_id = :work_order_line_id
            ORDER BY t.period_number ASC
            """
        ),
        {"work_order_line_id": work_order_line_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def insert_billing_term(
    db: Session,
    *,
    public_id: str,
    work_order_line_id: int,
    period_number: int,
    values: dict[str, Any],
    current_user_public_id: str | None,
) -> None:
    columns = ", ".join(WORK_ORDER_LINE_BILLING_TERM_COLUMNS)
    binds = ", ".join(f":{column}" for column in WORK_ORDER_LINE_BILLING_TERM_COLUMNS)
    db.execute(
        text(
            f"""
            INSERT INTO {WORK_ORDER_LINE_BILLING_TERM_TABLE} (
                work_order_line_billing_term_public_id, work_order_line_id, period_number, {columns},
                term_revision, currency_code, created_by, created_at, updated_by, updated_at
            ) VALUES (
                :public_id, :work_order_line_id, :period_number, {binds},
                1, 'INR', :user_public_id, CURRENT_TIMESTAMP, :user_public_id, CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "public_id": public_id,
            "work_order_line_id": work_order_line_id,
            "period_number": period_number,
            "user_public_id": current_user_public_id,
            **{column: values.get(column) for column in WORK_ORDER_LINE_BILLING_TERM_COLUMNS},
        },
    )


def update_billing_term(
    db: Session,
    *,
    term_id: int,
    expected_term_revision: int,
    values: dict[str, Any],
    current_user_public_id: str | None,
) -> int:
    """Replace one period and move to its next revision. Guarded on the expected revision as well as
    by the caller's Work Order lock. Returns the number of rows updated (0: the revision moved)."""
    assignments = ", ".join(f"{column} = :{column}" for column in WORK_ORDER_LINE_BILLING_TERM_COLUMNS)
    result = db.execute(
        text(
            f"""
            UPDATE {WORK_ORDER_LINE_BILLING_TERM_TABLE}
            SET {assignments},
                term_revision = term_revision + 1,
                updated_by = :user_public_id,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :term_id
              AND term_revision = :expected_term_revision
            """
        ),
        {
            "term_id": term_id,
            "expected_term_revision": expected_term_revision,
            "user_public_id": current_user_public_id,
            **{column: values.get(column) for column in WORK_ORDER_LINE_BILLING_TERM_COLUMNS},
        },
    )
    return int(result.rowcount or 0)


def delete_billing_term(db: Session, *, term_id: int, expected_term_revision: int) -> int:
    result = db.execute(
        text(
            f"""
            DELETE FROM {WORK_ORDER_LINE_BILLING_TERM_TABLE}
            WHERE id = :term_id
              AND term_revision = :expected_term_revision
            """
        ),
        {"term_id": term_id, "expected_term_revision": expected_term_revision},
    )
    return int(result.rowcount or 0)


# --- Slice 7D Part 3: contract period and extensions ---------------------------------------------
# Reads and writes crm_work_order_contract_period and crm_work_order_contract_extension only.
# crm_work_order is read, never written: the handoff owns that table and its output is frozen.

WORK_ORDER_CONTRACT_PERIOD_COLUMNS = (
    "contract_start_date",
    "contract_end_basis_code",
    "contract_end_date",
    "contract_notes",
)


def get_work_order_contract_period_row(db: Session, *, work_order_id: int) -> dict[str, Any] | None:
    row = db.execute(
        text(
            f"""
            SELECT
                p.work_order_contract_period_public_id AS period_public_id,
                p.period_version,
                {", ".join(f"p.{column}" for column in WORK_ORDER_CONTRACT_PERIOD_COLUMNS)},
                p.updated_by,
                period_updater.display_name AS updated_by_display_name,
                p.updated_at
            FROM {WORK_ORDER_CONTRACT_PERIOD_TABLE} p
            LEFT JOIN app_user period_updater ON period_updater.public_id = p.updated_by
            WHERE p.work_order_id = :work_order_id
            """
        ),
        {"work_order_id": work_order_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def insert_work_order_contract_period(
    db: Session,
    *,
    public_id: str,
    work_order_id: int,
    values: dict[str, Any],
    current_user_public_id: str | None,
) -> None:
    columns = ", ".join(WORK_ORDER_CONTRACT_PERIOD_COLUMNS)
    binds = ", ".join(f":{column}" for column in WORK_ORDER_CONTRACT_PERIOD_COLUMNS)
    db.execute(
        text(
            f"""
            INSERT INTO {WORK_ORDER_CONTRACT_PERIOD_TABLE} (
                work_order_contract_period_public_id, work_order_id, {columns},
                period_version, created_by, created_at, updated_by, updated_at
            ) VALUES (
                :public_id, :work_order_id, {binds},
                1, :user_public_id, CURRENT_TIMESTAMP, :user_public_id, CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "public_id": public_id,
            "work_order_id": work_order_id,
            "user_public_id": current_user_public_id,
            **{column: values.get(column) for column in WORK_ORDER_CONTRACT_PERIOD_COLUMNS},
        },
    )


def update_work_order_contract_period(
    db: Session,
    *,
    work_order_id: int,
    expected_period_version: int,
    values: dict[str, Any],
    current_user_public_id: str | None,
) -> int:
    """Replace the contract period and move to the next version. Guarded on the expected version as
    well as by the caller's Work Order lock. Returns rows updated (0: the version moved)."""
    assignments = ", ".join(f"{column} = :{column}" for column in WORK_ORDER_CONTRACT_PERIOD_COLUMNS)
    result = db.execute(
        text(
            f"""
            UPDATE {WORK_ORDER_CONTRACT_PERIOD_TABLE}
            SET {assignments},
                period_version = period_version + 1,
                updated_by = :user_public_id,
                updated_at = CURRENT_TIMESTAMP
            WHERE work_order_id = :work_order_id
              AND period_version = :expected_period_version
            """
        ),
        {
            "work_order_id": work_order_id,
            "expected_period_version": expected_period_version,
            "user_public_id": current_user_public_id,
            **{column: values.get(column) for column in WORK_ORDER_CONTRACT_PERIOD_COLUMNS},
        },
    )
    return int(result.rowcount or 0)


def list_work_order_contract_extension_rows(db: Session, *, work_order_id: int) -> list[dict[str, Any]]:
    """Every extension of this Work Order, oldest first, so the history reads in the order it happened."""
    rows = db.execute(
        text(
            f"""
            SELECT
                e.work_order_contract_extension_public_id AS extension_public_id,
                e.extension_sequence_no,
                e.previous_end_basis_code,
                e.previous_end_date,
                e.new_end_date,
                e.extension_start_date,
                e.customer_reference,
                e.received_date,
                e.extension_notes,
                e.created_by,
                extension_creator.display_name AS created_by_display_name,
                e.created_at
            FROM {WORK_ORDER_CONTRACT_EXTENSION_TABLE} e
            LEFT JOIN app_user extension_creator ON extension_creator.public_id = e.created_by
            WHERE e.work_order_id = :work_order_id
            ORDER BY e.extension_sequence_no ASC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def insert_work_order_contract_extension(
    db: Session,
    *,
    public_id: str,
    work_order_id: int,
    extension_sequence_no: int,
    previous_end_basis_code: str | None,
    previous_end_date: Any,
    new_end_date: Any,
    extension_start_date: Any,
    customer_reference: str | None,
    received_date: Any,
    extension_notes: str | None,
    current_user_public_id: str | None,
) -> None:
    db.execute(
        text(
            f"""
            INSERT INTO {WORK_ORDER_CONTRACT_EXTENSION_TABLE} (
                work_order_contract_extension_public_id, work_order_id, extension_sequence_no,
                previous_end_basis_code, previous_end_date, new_end_date, extension_start_date,
                customer_reference, received_date, extension_notes,
                created_by, created_at
            ) VALUES (
                :public_id, :work_order_id, :extension_sequence_no,
                :previous_end_basis_code, :previous_end_date, :new_end_date, :extension_start_date,
                :customer_reference, :received_date, :extension_notes,
                :user_public_id, CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "public_id": public_id,
            "work_order_id": work_order_id,
            "extension_sequence_no": extension_sequence_no,
            "previous_end_basis_code": previous_end_basis_code,
            "previous_end_date": previous_end_date,
            "new_end_date": new_end_date,
            "extension_start_date": extension_start_date,
            "customer_reference": customer_reference,
            "received_date": received_date,
            "extension_notes": extension_notes,
            "user_public_id": current_user_public_id,
        },
    )


def delete_work_order_contract_extension(db: Session, *, work_order_id: int, public_id: str) -> int:
    """Remove one extension row. The caller has already established, under the Work Order lock, that
    it is the most recent one. Returns rows deleted."""
    result = db.execute(
        text(
            f"""
            DELETE FROM {WORK_ORDER_CONTRACT_EXTENSION_TABLE}
            WHERE work_order_id = :work_order_id
              AND work_order_contract_extension_public_id = :public_id
            """
        ),
        {"work_order_id": work_order_id, "public_id": public_id},
    )
    return int(result.rowcount or 0)


def list_work_order_line_date_rows(db: Session, *, work_order_id: int) -> list[dict[str, Any]]:
    """Each line's own recorded dates, for checking a contract change against what lines already hold.

    Only lines whose detail row holds at least one date appear; a line following the Work Order has
    nothing to check.
    """
    rows = db.execute(
        text(
            f"""
            SELECT
                wol.work_order_line_public_id,
                wol.line_number,
                d.line_start_date,
                d.line_end_date
            FROM {WORK_ORDER_LINE_DETAIL_TABLE} d
            INNER JOIN {WORK_ORDER_LINE_TABLE} wol ON wol.id = d.work_order_line_id
            WHERE wol.work_order_id = :work_order_id
              AND (d.line_start_date IS NOT NULL OR d.line_end_date IS NOT NULL)
            ORDER BY wol.line_number ASC, wol.id ASC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def list_work_order_billing_period_start_rows(db: Session, *, work_order_id: int) -> list[dict[str, Any]]:
    """Every dated billing-terms period start on this Work Order, for the same check.

    Period 1 has no date - it starts with the contract - so it can never conflict and is left out.
    """
    rows = db.execute(
        text(
            f"""
            SELECT
                wol.work_order_line_public_id,
                wol.line_number,
                t.period_number,
                t.effective_from
            FROM {WORK_ORDER_LINE_BILLING_TERM_TABLE} t
            INNER JOIN {WORK_ORDER_LINE_TABLE} wol ON wol.id = t.work_order_line_id
            WHERE wol.work_order_id = :work_order_id
              AND t.effective_from IS NOT NULL
            ORDER BY wol.line_number ASC, t.period_number ASC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def delete_billing_terms_for_line(db: Session, *, work_order_line_id: int) -> int:
    """Remove every billing-terms period of one line, so the source line's periods can replace them
    wholesale (owner decision 20b: a ticked line that already has terms is replaced, on confirmation).
    """
    result = db.execute(
        text(
            f"""
            DELETE FROM {WORK_ORDER_LINE_BILLING_TERM_TABLE}
            WHERE work_order_line_id = :work_order_line_id
            """
        ),
        {"work_order_line_id": work_order_line_id},
    )
    return int(result.rowcount or 0)


def list_work_order_line_ids(db: Session, *, work_order_id: int) -> list[dict[str, Any]]:
    """Every line of the Work Order in line order, with its internal id and public id."""
    rows = db.execute(
        text(
            f"""
            SELECT id AS work_order_line_id, work_order_line_public_id, line_number
            FROM {WORK_ORDER_LINE_TABLE}
            WHERE work_order_id = :work_order_id
            ORDER BY line_number ASC, id ASC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


# --- Slice 7D Part 4: the holidays a Work Order names; since HOL-1 its changes to PBL's calendar ------
# Reads and writes crm_work_order_holiday_list and crm_work_order_holiday only. crm_work_order is read,
# never written: the handoff owns that table and its output is frozen. Each row of crm_work_order_holiday is
# one change: a holiday added, or a calendar holiday made a working day (HOL-1, Q4).


def get_work_order_holiday_list_row(db: Session, *, work_order_id: int) -> dict[str, Any] | None:
    """The Work Order's answer to "which holidays does it name", or None when not answered yet."""
    row = db.execute(
        text(
            f"""
            SELECT
                l.id AS holiday_list_id,
                l.work_order_holiday_list_public_id AS holiday_list_public_id,
                l.holidays_answer_code,
                l.list_version,
                l.updated_by,
                list_updater.display_name AS updated_by_display_name,
                l.updated_at
            FROM {WORK_ORDER_HOLIDAY_LIST_TABLE} l
            LEFT JOIN app_user list_updater ON list_updater.public_id = l.updated_by
            WHERE l.work_order_id = :work_order_id
            """
        ),
        {"work_order_id": work_order_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def get_work_order_holiday_list_snapshot(
    db: Session, *, work_order_id: int
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """The answer and its dates, read in ONE statement, so they come from one snapshot.

    Read as two statements, a save committing between them could return an answer with another
    version's dates - "names no holidays" beside a list - which never existed (Part 4 review round 2,
    finding F-05). Under PostgreSQL's READ COMMITTED each statement sees one snapshot, so one statement is
    enough. Returns (None, []) when no answer is recorded.
    """
    rows = db.execute(
        text(
            f"""
            SELECT
                l.id AS holiday_list_id,
                l.work_order_holiday_list_public_id AS holiday_list_public_id,
                l.holidays_answer_code,
                l.list_version,
                l.updated_by,
                list_updater.display_name AS updated_by_display_name,
                l.updated_at,
                h.work_order_holiday_public_id AS change_public_id,
                h.change_code,
                h.holiday_date,
                h.holiday_kind_code,
                h.working_day_rate_code,
                h.description
            FROM {WORK_ORDER_HOLIDAY_LIST_TABLE} l
            LEFT JOIN app_user list_updater ON list_updater.public_id = l.updated_by
            LEFT JOIN {WORK_ORDER_HOLIDAY_TABLE} h ON h.work_order_holiday_list_id = l.id
            WHERE l.work_order_id = :work_order_id
            ORDER BY h.holiday_date ASC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    if not rows:
        return None, []
    mapped = [dict(_row_mapping(row)) for row in rows]
    header_columns = (
        "holiday_list_id",
        "holiday_list_public_id",
        "holidays_answer_code",
        "list_version",
        "updated_by",
        "updated_by_display_name",
        "updated_at",
    )
    header = {column: mapped[0][column] for column in header_columns}
    changes = [
        {key: row[key] for key in _HOLIDAY_CHANGE_KEYS}
        for row in mapped
        if row["change_public_id"] is not None
    ]
    return header, changes


_HOLIDAY_CHANGE_KEYS = (
    "change_public_id",
    "change_code",
    "holiday_date",
    "holiday_kind_code",
    "working_day_rate_code",
    "description",
)


def list_work_order_holiday_rows(db: Session, *, holiday_list_id: int) -> list[dict[str, Any]]:
    """The changes on one list, earliest first."""
    rows = db.execute(
        text(
            f"""
            SELECT
                h.work_order_holiday_public_id AS change_public_id,
                h.change_code,
                h.holiday_date,
                h.holiday_kind_code,
                h.working_day_rate_code,
                h.description
            FROM {WORK_ORDER_HOLIDAY_TABLE} h
            WHERE h.work_order_holiday_list_id = :holiday_list_id
            ORDER BY h.holiday_date ASC
            """
        ),
        {"holiday_list_id": holiday_list_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def list_work_order_holiday_dates(db: Session, *, work_order_id: int) -> list[tuple[Any, str]]:
    """Every date a Work Order lists, with what it is - a holiday added or a working day (HOL-1) - earliest first,
    for checking a contract change against."""
    rows = db.execute(
        text(
            f"""
            SELECT h.holiday_date, h.change_code
            FROM {WORK_ORDER_HOLIDAY_TABLE} h
            INNER JOIN {WORK_ORDER_HOLIDAY_LIST_TABLE} l ON l.id = h.work_order_holiday_list_id
            WHERE l.work_order_id = :work_order_id
            ORDER BY h.holiday_date ASC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    return [(row[0], row[1]) for row in rows]


def insert_work_order_holiday_list(
    db: Session,
    *,
    public_id: str,
    work_order_id: int,
    holidays_answer_code: str,
    current_user_public_id: str | None,
) -> int:
    """Record the Work Order's first answer. Returns the new list's internal id."""
    return int(
        db.execute(
            text(
                f"""
                INSERT INTO {WORK_ORDER_HOLIDAY_LIST_TABLE} (
                    work_order_holiday_list_public_id, work_order_id, holidays_answer_code,
                    list_version, created_by, created_at, updated_by, updated_at
                ) VALUES (
                    :public_id, :work_order_id, :holidays_answer_code,
                    1, :user_public_id, CURRENT_TIMESTAMP, :user_public_id, CURRENT_TIMESTAMP
                )
                RETURNING id
                """
            ),
            {
                "public_id": public_id,
                "work_order_id": work_order_id,
                "holidays_answer_code": holidays_answer_code,
                "user_public_id": current_user_public_id,
            },
        ).scalar_one()
    )


def update_work_order_holiday_list(
    db: Session,
    *,
    holiday_list_id: int,
    expected_list_version: int,
    holidays_answer_code: str,
    current_user_public_id: str | None,
) -> int:
    """Record a changed answer or list and move to the next version. Guarded on the expected version as
    well as by the caller's Work Order lock. Returns rows updated (0: the version moved)."""
    result = db.execute(
        text(
            f"""
            UPDATE {WORK_ORDER_HOLIDAY_LIST_TABLE}
            SET holidays_answer_code = :holidays_answer_code,
                list_version = list_version + 1,
                updated_by = :user_public_id,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :holiday_list_id
              AND list_version = :expected_list_version
            """
        ),
        {
            "holiday_list_id": holiday_list_id,
            "expected_list_version": expected_list_version,
            "holidays_answer_code": holidays_answer_code,
            "user_public_id": current_user_public_id,
        },
    )
    return int(result.rowcount or 0)


def delete_work_order_holidays(db: Session, *, holiday_list_id: int) -> int:
    """Remove every date on one list, so the saved list can replace them wholesale."""
    result = db.execute(
        text(f"DELETE FROM {WORK_ORDER_HOLIDAY_TABLE} WHERE work_order_holiday_list_id = :holiday_list_id"),
        {"holiday_list_id": holiday_list_id},
    )
    return int(result.rowcount or 0)


def insert_work_order_holiday(
    db: Session,
    *,
    public_id: str,
    holiday_list_id: int,
    change_code: str,
    holiday_date: Any,
    holiday_kind_code: str | None,
    working_day_rate_code: str | None,
    description: str | None,
) -> None:
    db.execute(
        text(
            f"""
            INSERT INTO {WORK_ORDER_HOLIDAY_TABLE} (
                work_order_holiday_public_id, work_order_holiday_list_id, change_code, holiday_date,
                holiday_kind_code, working_day_rate_code, description
            ) VALUES (
                :public_id, :holiday_list_id, :change_code, :holiday_date, :holiday_kind_code,
                :working_day_rate_code, :description
            )
            """
        ),
        {
            "public_id": public_id,
            "holiday_list_id": holiday_list_id,
            "change_code": change_code,
            "holiday_date": holiday_date,
            "holiday_kind_code": holiday_kind_code,
            "working_day_rate_code": working_day_rate_code,
            "description": description,
        },
    )
