from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_CREDIT_REVIEW_TABLE,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_TABLE,
    COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE,
    COMMERCIAL_OFFER_LINE_BASIS_CHOICE_TABLE,
    COMMERCIAL_OFFER_LINE_TABLE,
    COMMERCIAL_OFFER_PURPOSE_BASE,
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_TABLE,
    COMMERCIAL_OFFER_REVISION_TABLE,
    COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_TABLE,
    COMMERCIAL_OFFER_TC_CLAUSE_TABLE,
    COMMERCIAL_OFFER_TABLE,
    COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES,
    COMMERCIAL_OFFER_VERSION_UNSENT_STATUSES,
    COMMERCIAL_OFFER_WORKFLOW_MODULE,
)
from app.modules.commercial_offers.schemas import (
    CommercialOfferCreditReviewResponse,
    CommercialOfferCustomerResponseResponse,
    CommercialOfferLineResponse,
    CommercialOfferPricingEvidenceResponse,
    CommercialOfferResponse,
    CommercialOfferRevisionResponse,
    CommercialOfferSubmissionEvidenceResponse,
    CommercialOfferTcClauseResponse,
)
from app.modules.terms_and_conditions.contract import TC_CLAUSE_LIBRARY_TABLE


COMMERCIAL_OFFER_SELECT_COLUMNS = """
    co.offer_public_id AS public_id,
    co.offer_code,
    o.opportunity_public_id AS opportunity_public_id,
    COALESCE(offer_bp.business_party_public_id, opportunity_bp.business_party_public_id) AS account_public_id,
    co.offer_title,
    co.offer_mode,
    co.offer_type,
    co.offer_status_code,
    co.offer_value,
    co.currency_code,
    co.offer_date,
    co.valid_until,
    co.submitted_at,
    co.submission_reference,
    co.submission_proof_note,
    co.outcome_date,
    co.outcome_remarks,
    co.remarks,
    co.offer_purpose,
    base_offer.offer_public_id AS base_offer_public_id,
    base_offer.offer_code AS base_offer_code,
    related_wo.work_order_public_id AS related_work_order_public_id,
    related_wo.work_order_code AS related_work_order_code,
    co.customer_request_reference,
    co.customer_request_received_date,
    co.customer_request_summary,
    co.version_number,
    previous_version.offer_public_id AS previous_version_offer_public_id,
    co.version_reason,
    co.version_note,
    replaced_by.offer_public_id AS replaced_by_offer_public_id,
    replaced_by.version_number AS replaced_by_version_number,
    co.created_by,
    offer_creator.display_name AS created_by_display_name,
    co.created_at,
    co.updated_at,
    co.row_version
"""

# Every query that selects COMMERCIAL_OFFER_SELECT_COLUMNS appends these joins. Status constants
# are trusted module-owned values; rendering them once keeps this reusable join parameter-free.
_COMMERCIAL_OFFER_VERSION_UNSENT_STATUS_SQL = ", ".join(
    f"'{status}'" for status in COMMERCIAL_OFFER_VERSION_UNSENT_STATUSES
)

# The app_user join
# resolves the creator's display name read-only, as a LEFT JOIN like QUOTE_DOCUMENT_ACTOR_JOINS
# below: an offer whose creator id matches no user still lists, with a NULL name.
COMMERCIAL_OFFER_SELECT_JOINS = f"""
    LEFT JOIN crm_commercial_offer base_offer ON base_offer.id = co.base_offer_id
    LEFT JOIN crm_commercial_offer previous_version ON previous_version.id = co.previous_version_offer_id
    LEFT JOIN LATERAL (
        SELECT child.offer_public_id, child.version_number
        FROM crm_commercial_offer child
        WHERE child.previous_version_offer_id = co.id
          AND child.offer_status_code NOT IN ({_COMMERCIAL_OFFER_VERSION_UNSENT_STATUS_SQL})
        ORDER BY child.version_number DESC, child.id DESC
        LIMIT 1
    ) replaced_by ON TRUE
    LEFT JOIN crm_work_order related_wo ON related_wo.id = co.related_work_order_id
    LEFT JOIN app_user offer_creator ON offer_creator.public_id = co.created_by
"""

COMMERCIAL_OFFER_UPDATE_COLUMNS = (
    "offer_title",
    "offer_mode",
    "offer_type",
    "offer_status_code",
    "offer_value",
    "currency_code",
    "offer_date",
    "valid_until",
    "submitted_at",
    "submission_reference",
    "submission_proof_note",
    "outcome_date",
    "outcome_remarks",
    "remarks",
)


def _status_placeholders(prefix: str, values: tuple[str, ...]) -> tuple[str, dict[str, str]]:
    keys = [f"{prefix}{index}" for index in range(len(values))]
    return ", ".join(f":{key}" for key in keys), dict(zip(keys, values, strict=True))


def _row_mapping(row: Any) -> Any:
    return row._mapping if hasattr(row, "_mapping") else row


def _row_to_commercial_offer(row: Any) -> CommercialOfferResponse:
    data = _row_mapping(row)
    return CommercialOfferResponse(
        public_id=data["public_id"],
        offer_code=data["offer_code"],
        opportunity_public_id=data["opportunity_public_id"],
        account_public_id=data.get("account_public_id"),
        offer_title=data.get("offer_title"),
        offer_mode=data["offer_mode"],
        offer_type=data["offer_type"],
        offer_status_code=data["offer_status_code"],
        offer_value=data.get("offer_value"),
        currency_code=data["currency_code"],
        offer_date=data.get("offer_date"),
        valid_until=data.get("valid_until"),
        submitted_at=data.get("submitted_at"),
        submission_reference=data.get("submission_reference"),
        submission_proof_note=data.get("submission_proof_note"),
        outcome_date=data.get("outcome_date"),
        outcome_remarks=data.get("outcome_remarks"),
        remarks=data.get("remarks"),
        offer_purpose=data["offer_purpose"],
        base_offer_public_id=data.get("base_offer_public_id"),
        base_offer_code=data.get("base_offer_code"),
        related_work_order_public_id=data.get("related_work_order_public_id"),
        related_work_order_code=data.get("related_work_order_code"),
        customer_request_reference=data.get("customer_request_reference"),
        customer_request_received_date=data.get("customer_request_received_date"),
        customer_request_summary=data.get("customer_request_summary"),
        version_number=data["version_number"],
        previous_version_offer_public_id=data.get("previous_version_offer_public_id"),
        version_reason=data.get("version_reason"),
        version_note=data.get("version_note"),
        replaced_by_offer_public_id=data.get("replaced_by_offer_public_id"),
        replaced_by_version_number=data.get("replaced_by_version_number"),
        created_by=data.get("created_by"),
        created_by_display_name=data.get("created_by_display_name"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        row_version=data["row_version"],
    )


def active_commercial_offer_status_exists(db: Session, status_code: str) -> bool:
    exists = db.execute(
        text(
            """
            SELECT 1
            FROM workflow_status
            WHERE module = :module
              AND status_code = :status_code
              AND is_active IS TRUE
            """
        ),
        {"module": COMMERCIAL_OFFER_WORKFLOW_MODULE, "status_code": status_code},
    ).scalar()
    return exists == 1


def get_opportunity_context_by_public_id(db: Session, opportunity_public_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT
                o.id AS opportunity_id,
                o.opportunity_public_id,
                o.opportunity_name,
                o.opportunity_status_code,
                o.business_party_id,
                bp.business_party_public_id AS account_public_id
            FROM crm_opportunity o
            LEFT JOIN business_party bp ON bp.id = o.business_party_id
            WHERE o.opportunity_public_id = :opportunity_public_id
            LIMIT 1
            """
        ),
        {"opportunity_public_id": opportunity_public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def get_base_offer_creation_context(db: Session, base_offer_public_id: str) -> dict[str, Any] | None:
    """Read-only lookup used only to derive Account/Opportunity context and eligibility
    for a new Supplementary Offer / Change Quotation. Never used to mutate the Base Offer."""
    row = db.execute(
        text(
            f"""
            SELECT
                co.id AS commercial_offer_id,
                co.offer_public_id,
                co.offer_code,
                co.offer_status_code,
                co.version_number,
                co.offer_purpose,
                co.opportunity_id,
                co.business_party_id,
                o.opportunity_public_id,
                o.business_party_id AS opportunity_business_party_id,
                COALESCE(offer_bp.business_party_public_id, opportunity_bp.business_party_public_id) AS account_public_id
            FROM {COMMERCIAL_OFFER_TABLE} co
            INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
            LEFT JOIN business_party offer_bp ON offer_bp.id = co.business_party_id
            LEFT JOIN business_party opportunity_bp ON opportunity_bp.id = o.business_party_id
            WHERE co.offer_public_id = :base_offer_public_id
            LIMIT 1
            """
        ),
        {"base_offer_public_id": base_offer_public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def get_work_order_lineage_context(db: Session, work_order_public_id: str) -> dict[str, Any] | None:
    """Read-only cross-module lookup (raw SQL, no import of the work_orders module -
    matches the existing list_linked_work_order_contexts_for_offer pattern) used only to
    validate that a Work Order named on a related-offer creation request genuinely belongs
    to the same Account/Opportunity lineage as the Base Offer."""
    row = db.execute(
        text(
            """
            SELECT
                wo.id AS work_order_id,
                wo.work_order_public_id,
                wo.work_order_code,
                wo.work_order_status_code,
                wo.opportunity_id,
                wo.business_party_id,
                wo.commercial_offer_id AS source_commercial_offer_id
            FROM crm_work_order wo
            WHERE wo.work_order_public_id = :work_order_public_id
            LIMIT 1
            """
        ),
        {"work_order_public_id": work_order_public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def list_related_commercial_offers_for_base_offer(
    db: Session,
    *,
    base_offer_id: int,
) -> list[CommercialOfferResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_TABLE} co
            INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
            LEFT JOIN business_party offer_bp ON offer_bp.id = co.business_party_id
            LEFT JOIN business_party opportunity_bp ON opportunity_bp.id = o.business_party_id
            {COMMERCIAL_OFFER_SELECT_JOINS}
            WHERE co.base_offer_id = :base_offer_id
            ORDER BY co.created_at DESC, co.id DESC
            """
        ),
        {"base_offer_id": base_offer_id},
    ).fetchall()
    return [_row_to_commercial_offer(row) for row in rows]


def list_related_commercial_offers_for_work_order(
    db: Session,
    *,
    work_order_id: int,
) -> list[CommercialOfferResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_TABLE} co
            INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
            LEFT JOIN business_party offer_bp ON offer_bp.id = co.business_party_id
            LEFT JOIN business_party opportunity_bp ON opportunity_bp.id = o.business_party_id
            {COMMERCIAL_OFFER_SELECT_JOINS}
            WHERE co.related_work_order_id = :work_order_id
            ORDER BY co.created_at DESC, co.id DESC
            """
        ),
        {"work_order_id": work_order_id},
    ).fetchall()
    return [_row_to_commercial_offer(row) for row in rows]


def insert_commercial_offer(
    db: Session,
    *,
    public_id: str,
    values: dict[str, Any],
) -> CommercialOfferResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {COMMERCIAL_OFFER_TABLE} (
                offer_public_id,
                offer_code,
                opportunity_id,
                business_party_id,
                offer_title,
                offer_mode,
                offer_type,
                offer_status_code,
                offer_value,
                currency_code,
                offer_date,
                valid_until,
                remarks,
                offer_purpose,
                base_offer_id,
                related_work_order_id,
                customer_request_reference,
                customer_request_received_date,
                customer_request_summary,
                version_number,
                previous_version_offer_id,
                version_reason,
                version_note,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :offer_public_id,
                :offer_code,
                :opportunity_id,
                :business_party_id,
                :offer_title,
                :offer_mode,
                :offer_type,
                :offer_status_code,
                :offer_value,
                :currency_code,
                :offer_date,
                :valid_until,
                :remarks,
                :offer_purpose,
                :base_offer_id,
                :related_work_order_id,
                :customer_request_reference,
                :customer_request_received_date,
                :customer_request_summary,
                :version_number,
                :previous_version_offer_id,
                :version_reason,
                :version_note,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "offer_public_id": public_id,
            "offer_code": values.get("offer_code"),
            "offer_purpose": values.get("offer_purpose", COMMERCIAL_OFFER_PURPOSE_BASE),
            "base_offer_id": values.get("base_offer_id"),
            "related_work_order_id": values.get("related_work_order_id"),
            "customer_request_reference": values.get("customer_request_reference"),
            "customer_request_received_date": values.get("customer_request_received_date"),
            "customer_request_summary": values.get("customer_request_summary"),
            "version_number": values.get("version_number", 1),
            "previous_version_offer_id": values.get("previous_version_offer_id"),
            "version_reason": values.get("version_reason"),
            "version_note": values.get("version_note"),
            **{
                key: value
                for key, value in values.items()
                if key
                not in {
                    "offer_purpose",
                    "base_offer_id",
                    "related_work_order_id",
                    "customer_request_reference",
                    "customer_request_received_date",
                    "customer_request_summary",
                    "offer_code",
                    "version_number",
                    "previous_version_offer_id",
                    "version_reason",
                    "version_note",
                }
            },
        },
    )
    db.execute(
        text(
            f"""
            UPDATE {COMMERCIAL_OFFER_TABLE}
            SET offer_code = 'CO-' || RIGHT('000000' || CAST(id AS VARCHAR(20)), 6)
            WHERE offer_public_id = :offer_public_id
              AND offer_code IS NULL
            """
        ),
        {"offer_public_id": public_id},
    )
    commercial_offer = get_commercial_offer_by_public_id(db, public_id)
    if commercial_offer is None:
        raise RuntimeError("Inserted Commercial Offer could not be reloaded.")
    return commercial_offer




def update_commercial_offer_by_public_id(
    db: Session,
    *,
    public_id: str,
    values: dict[str, Any],
    expected_row_version: int | None = None,
) -> CommercialOfferResponse | None:
    """Write the offer's row. Every write raises row_version by one (CS-05a), whichever action makes it.

    With expected_row_version the row is written only while it still has that version - the backstop to the
    caller's own check under the offer's row lock - and None is returned when it has moved on. Without it the
    write always lands, as for marking an offer submitted or a customer response setting its status.
    """
    assignments = [f"{column} = :{column}" for column in COMMERCIAL_OFFER_UPDATE_COLUMNS if column in values]
    if not assignments:
        commercial_offer = get_commercial_offer_by_public_id(db, public_id)
        if commercial_offer is None:
            raise RuntimeError("Commercial Offer could not be reloaded.")
        return commercial_offer

    assignments.append("updated_at = CURRENT_TIMESTAMP")
    assignments.append("row_version = row_version + 1")
    params: dict[str, Any] = {"public_id": public_id, **values}
    version_guard = ""
    if expected_row_version is not None:
        version_guard = "AND row_version = :expected_row_version"
        params["expected_row_version"] = expected_row_version
    result = db.execute(
        text(
            f"""
            UPDATE {COMMERCIAL_OFFER_TABLE}
            SET {', '.join(assignments)}
            WHERE offer_public_id = :public_id
              {version_guard}
            """
        ),
        params,
    )
    if expected_row_version is not None and result.rowcount != 1:
        return None
    commercial_offer = get_commercial_offer_by_public_id(db, public_id)
    if commercial_offer is None:
        raise RuntimeError("Updated Commercial Offer could not be reloaded.")
    return commercial_offer


def get_commercial_offer_by_public_id(db: Session, public_id: str) -> CommercialOfferResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_TABLE} co
            INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
            LEFT JOIN business_party offer_bp ON offer_bp.id = co.business_party_id
            LEFT JOIN business_party opportunity_bp ON opportunity_bp.id = o.business_party_id
            {COMMERCIAL_OFFER_SELECT_JOINS}
            WHERE co.offer_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_commercial_offer(row) if row else None


def list_recent_commercial_offers(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    status_code: str | None = None,
    offer_mode: str | None = None,
    opportunity_public_id: str | None = None,
) -> list[CommercialOfferResponse]:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    filters: list[str] = []
    params: dict[str, Any] = {}

    if status_code:
        filters.append("co.offer_status_code = :status_code")
        params["status_code"] = status_code

    if offer_mode:
        filters.append("co.offer_mode = :offer_mode")
        params["offer_mode"] = offer_mode

    if opportunity_public_id:
        filters.append("o.opportunity_public_id = :opportunity_public_id")
        params["opportunity_public_id"] = opportunity_public_id

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_TABLE} co
            INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
            LEFT JOIN business_party offer_bp ON offer_bp.id = co.business_party_id
            LEFT JOIN business_party opportunity_bp ON opportunity_bp.id = o.business_party_id
            {COMMERCIAL_OFFER_SELECT_JOINS}
            {where_clause}
            ORDER BY co.created_at DESC, co.id DESC
            LIMIT {safe_limit} OFFSET {safe_offset}
            """
        ),
        params,
    ).fetchall()
    return [_row_to_commercial_offer(row) for row in rows]


def get_existing_actionable_commercial_offer_for_opportunity(
    db: Session,
    *,
    opportunity_id: int,
    inactive_statuses: tuple[str, ...],
) -> CommercialOfferResponse | None:
    rows = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_TABLE} co
            INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
            LEFT JOIN business_party offer_bp ON offer_bp.id = co.business_party_id
            LEFT JOIN business_party opportunity_bp ON opportunity_bp.id = o.business_party_id
            {COMMERCIAL_OFFER_SELECT_JOINS}
            WHERE co.opportunity_id = :opportunity_id
              AND co.offer_purpose = :base_purpose
            ORDER BY co.created_at DESC, co.id DESC
            """
        ),
        {"opportunity_id": opportunity_id, "base_purpose": COMMERCIAL_OFFER_PURPOSE_BASE},
    ).fetchall()
    for row in rows:
        commercial_offer = _row_to_commercial_offer(row)
        if (
            commercial_offer.previous_version_offer_public_id is not None
            and commercial_offer.offer_status_code in COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES
        ):
            continue
        if commercial_offer.offer_status_code not in inactive_statuses:
            return commercial_offer
    return None


def get_commercial_offer_version_context(db: Session, *, public_id: str) -> dict[str, Any] | None:
    preparation_placeholders, preparation_params = _status_placeholders(
        "preparation_status_", COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES
    )
    unsent_placeholders, unsent_params = _status_placeholders(
        "unsent_status_", COMMERCIAL_OFFER_VERSION_UNSENT_STATUSES
    )
    row = db.execute(
        text(
            f"""
            SELECT co.id AS commercial_offer_id, co.offer_public_id, co.offer_code,
                   co.offer_status_code, co.version_number, co.previous_version_offer_id,
                   previous.offer_public_id AS previous_version_offer_public_id,
                   previous.offer_status_code AS previous_version_status_code,
                   co.opportunity_id, co.business_party_id, co.offer_title, co.offer_mode,
                   co.offer_type, co.offer_value, co.currency_code, co.offer_date, co.valid_until,
                   co.remarks, co.offer_purpose, co.base_offer_id, co.related_work_order_id,
                   co.customer_request_reference, co.customer_request_received_date,
                   co.customer_request_summary,
                   (SELECT MAX(series.version_number)
                    FROM {COMMERCIAL_OFFER_TABLE} series
                    WHERE series.offer_code = co.offer_code) AS maximum_version_number,
                   (SELECT prep.offer_public_id
                    FROM {COMMERCIAL_OFFER_TABLE} prep
                    WHERE prep.offer_code = co.offer_code
                      AND prep.previous_version_offer_id IS NOT NULL
                      AND prep.offer_status_code IN ({preparation_placeholders})
                    ORDER BY prep.version_number DESC, prep.id DESC
                    LIMIT 1) AS preparation_offer_public_id,
                   (SELECT sent.offer_public_id
                    FROM {COMMERCIAL_OFFER_TABLE} sent
                    WHERE sent.offer_code = co.offer_code
                      AND sent.offer_status_code NOT IN ({unsent_placeholders})
                    ORDER BY sent.version_number DESC, sent.id DESC
                    LIMIT 1) AS latest_sent_offer_public_id
            FROM {COMMERCIAL_OFFER_TABLE} co
            LEFT JOIN {COMMERCIAL_OFFER_TABLE} previous ON previous.id = co.previous_version_offer_id
            WHERE co.offer_public_id = :public_id
            LIMIT 1
            """
        ),
        {"public_id": public_id, **preparation_params, **unsent_params},
    ).first()
    return dict(_row_mapping(row)) if row else None


def list_commercial_offer_versions_for_code(db: Session, *, offer_code: str) -> list[CommercialOfferResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT {COMMERCIAL_OFFER_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_TABLE} co
            INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
            LEFT JOIN business_party offer_bp ON offer_bp.id = co.business_party_id
            LEFT JOIN business_party opportunity_bp ON opportunity_bp.id = o.business_party_id
            {COMMERCIAL_OFFER_SELECT_JOINS}
            WHERE co.offer_code = :offer_code
            ORDER BY co.version_number, co.id
            """
        ),
        {"offer_code": offer_code},
    ).fetchall()
    return [_row_to_commercial_offer(row) for row in rows]


def lock_commercial_offer_version_submission_rows(
    db: Session, *, current_offer_id: int, previous_offer_id: int
) -> None:
    db.execute(
        text(
            f"""
            SELECT id
            FROM {COMMERCIAL_OFFER_TABLE}
            WHERE id IN (:current_offer_id, :previous_offer_id)
            ORDER BY id
            FOR UPDATE
            """
        ),
        {"current_offer_id": current_offer_id, "previous_offer_id": previous_offer_id},
    ).fetchall()


def copy_commercial_offer_version_children(
    db: Session,
    *,
    source_offer_id: int,
    target_offer_id: int,
    current_user_public_id: str | None,
) -> dict[str, int]:
    copied = {"lines": 0, "pricing_evidence": 0, "tc_clauses": 0, "credit_reviews": 0}

    lines = db.execute(
        text(
            """
            SELECT id AS source_line_id, line_number, line_status_code, scope_description, equipment_service_category,
                   quantity, uom, rate_amount, currency_code, line_amount, remarks
            FROM crm_commercial_offer_line
            WHERE commercial_offer_id = :source_offer_id AND line_status_code = 'ACTIVE'
            ORDER BY line_number, id
            """
        ),
        {"source_offer_id": source_offer_id},
    ).mappings().all()
    copied_line_ids: dict[int, int] = {}
    for row in lines:
        values = dict(row)
        source_line_id = int(values.pop("source_line_id"))
        copied_line_ids[source_line_id] = int(
            db.execute(
                text(
                    """
                    INSERT INTO crm_commercial_offer_line (
                        line_public_id, commercial_offer_id, line_number, line_status_code,
                        scope_description, equipment_service_category, quantity, uom, rate_amount,
                        currency_code, line_amount, remarks, created_by, created_at, updated_at
                    ) VALUES (
                        :public_id, :target_offer_id, :line_number, :line_status_code,
                        :scope_description, :equipment_service_category, :quantity, :uom, :rate_amount,
                        :currency_code, :line_amount, :remarks, :actor, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    RETURNING id
                    """
                ),
                {"public_id": str(uuid4()), "target_offer_id": target_offer_id, "actor": current_user_public_id, **values},
            ).scalar_one()
        )
        copied["lines"] += 1

    # Each active line's rates go to its copy, and rates recorded for the whole offer before Slice 4G go as they are.
    # A rate on a line left behind (cancelled) stays with that line. Each copy is linked to the rate it was copied from,
    # on the offer this version was made from - held so by the database (review 4G-R4-005) - and its quote copy is
    # found through that link: the attached document stays where it was filed. A copy carries no user reference of
    # its own (reviews 4G-R2-001, 4G-R4-005).
    evidence_rows = db.execute(
        text(
            """
            SELECT id AS source_evidence_id, commercial_offer_line_id, recorded_for_whole_offer,
                   evidence_type, source_name, vendor_contact, equipment_service_description,
                   rate_amount, currency_code, rate_basis, collected_by_name, collected_at,
                   source_reference, is_selected_basis, selection_reason, comparison_notes
            FROM crm_commercial_offer_pricing_evidence
            WHERE commercial_offer_id = :source_offer_id
            ORDER BY id
            """
        ),
        {"source_offer_id": source_offer_id},
    ).mappings().all()
    copied_evidence_ids: dict[int, int] = {}
    for row in evidence_rows:
        values = dict(row)
        source_evidence_id = int(values.pop("source_evidence_id"))
        source_line_id = values.pop("commercial_offer_line_id")
        if not values["recorded_for_whole_offer"] and int(source_line_id) not in copied_line_ids:
            continue
        values["commercial_offer_line_id"] = None if source_line_id is None else copied_line_ids[int(source_line_id)]
        values["is_selected_basis"] = bool(values["is_selected_basis"]) and bool(values["recorded_for_whole_offer"])
        copied_evidence_ids[source_evidence_id] = int(
            db.execute(
                text(
                    """
                    INSERT INTO crm_commercial_offer_pricing_evidence (
                        evidence_public_id, commercial_offer_id, commercial_offer_line_id, recorded_for_whole_offer,
                        copied_from_evidence_id, copied_from_offer_id, evidence_type, source_name, vendor_contact,
                        equipment_service_description, rate_amount, currency_code, rate_basis,
                        collected_by_name, collected_at, source_reference, is_selected_basis,
                        selection_reason, comparison_notes, created_by, created_at, updated_at
                    ) VALUES (
                        :public_id, :target_offer_id, :commercial_offer_line_id, :recorded_for_whole_offer,
                        :copied_from_evidence_id, :source_offer_id, :evidence_type, :source_name, :vendor_contact,
                        :equipment_service_description, :rate_amount, :currency_code, :rate_basis,
                        :collected_by_name, :collected_at, :source_reference, :is_selected_basis,
                        :selection_reason, :comparison_notes, :actor, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    RETURNING id
                    """
                ),
                {
                    "public_id": str(uuid4()),
                    "target_offer_id": target_offer_id,
                    "copied_from_evidence_id": source_evidence_id,
                    "source_offer_id": source_offer_id,
                    "actor": current_user_public_id,
                    **values,
                },
            ).scalar_one()
        )
        copied["pricing_evidence"] += 1

    # Each copied line's current basis choice is carried over, naming the choice it came from; the earlier history
    # stays on the earlier version.
    open_choices = db.execute(
        text(
            """
            SELECT id, commercial_offer_line_id, pricing_evidence_id, selection_reason, chosen_by, chosen_at
            FROM crm_commercial_offer_line_basis_choice
            WHERE ended_at IS NULL AND commercial_offer_line_id IN (
                SELECT id FROM crm_commercial_offer_line WHERE commercial_offer_id = :source_offer_id
            )
            ORDER BY id
            """
        ),
        {"source_offer_id": source_offer_id},
    ).mappings().all()
    for choice in open_choices:
        line_id = copied_line_ids.get(int(choice["commercial_offer_line_id"]))
        evidence_id = copied_evidence_ids.get(int(choice["pricing_evidence_id"]))
        if line_id is None or evidence_id is None:
            continue
        db.execute(
            text(
                """
                INSERT INTO crm_commercial_offer_line_basis_choice (
                    choice_public_id, commercial_offer_line_id, pricing_evidence_id, selection_reason,
                    chosen_by, chosen_at, carried_from_choice_id, created_at
                ) VALUES (
                    :public_id, :line_id, :evidence_id, :selection_reason,
                    :chosen_by, :chosen_at, :carried_from_choice_id, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "public_id": str(uuid4()),
                "line_id": line_id,
                "evidence_id": evidence_id,
                "selection_reason": choice["selection_reason"],
                "chosen_by": choice["chosen_by"],
                "chosen_at": choice["chosen_at"],
                "carried_from_choice_id": int(choice["id"]),
            },
        )

    clause_rows = db.execute(
        text(
            """
            SELECT tc_clause_id, clause_id_snapshot, title_snapshot, clause_text_snapshot,
                   business_line_snapshot, clause_category_snapshot, source_clause_number_snapshot,
                   source_reference_snapshot, mandatory_default_snapshot, risk_category_snapshot,
                   applies_to_header_snapshot, applies_to_line_snapshot,
                   requires_approval_if_omitted_snapshot, requires_approval_if_modified_snapshot,
                   sort_order, active
            FROM commercial_offer_tc_clause
            WHERE commercial_offer_id = :source_offer_id AND active IS TRUE
            ORDER BY sort_order, id
            """
        ),
        {"source_offer_id": source_offer_id},
    ).mappings()
    for row in clause_rows:
        db.execute(
            text(
                """
                INSERT INTO commercial_offer_tc_clause (
                    public_id, commercial_offer_id, tc_clause_id, clause_id_snapshot, title_snapshot,
                    clause_text_snapshot, business_line_snapshot, clause_category_snapshot,
                    source_clause_number_snapshot, source_reference_snapshot, mandatory_default_snapshot,
                    risk_category_snapshot, applies_to_header_snapshot, applies_to_line_snapshot,
                    requires_approval_if_omitted_snapshot, requires_approval_if_modified_snapshot,
                    sort_order, active, attached_by, created_at, updated_at
                ) VALUES (
                    :public_id, :target_offer_id, :tc_clause_id, :clause_id_snapshot, :title_snapshot,
                    :clause_text_snapshot, :business_line_snapshot, :clause_category_snapshot,
                    :source_clause_number_snapshot, :source_reference_snapshot, :mandatory_default_snapshot,
                    :risk_category_snapshot, :applies_to_header_snapshot, :applies_to_line_snapshot,
                    :requires_approval_if_omitted_snapshot, :requires_approval_if_modified_snapshot,
                    :sort_order, :active, :actor, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {"public_id": str(uuid4()), "target_offer_id": target_offer_id, "actor": current_user_public_id, **row},
        )
        copied["tc_clauses"] += 1

    review = db.execute(
        text(
            """
            SELECT review_status, review_basis, review_reference, reviewed_at, reviewed_by,
                   approved_amount_snapshot, credit_days_snapshot, exposure_note, active
            FROM commercial_offer_credit_review
            WHERE commercial_offer_id = :source_offer_id AND active IS TRUE
            ORDER BY reviewed_at DESC, id DESC
            LIMIT 1
            """
        ),
        {"source_offer_id": source_offer_id},
    ).mappings().first()
    if review is not None:
        db.execute(
            text(
                """
                INSERT INTO commercial_offer_credit_review (
                    public_id, commercial_offer_id, review_status, review_basis, review_reference,
                    reviewed_at, reviewed_by, approved_amount_snapshot, credit_days_snapshot,
                    exposure_note, active, created_by, created_at, updated_at
                ) VALUES (
                    :public_id, :target_offer_id, :review_status, :review_basis, :review_reference,
                    :reviewed_at, :reviewed_by, :approved_amount_snapshot, :credit_days_snapshot,
                    :exposure_note, :active, :actor, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {"public_id": str(uuid4()), "target_offer_id": target_offer_id, "actor": current_user_public_id, **review},
        )
        copied["credit_reviews"] = 1
    return copied


COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_SELECT_COLUMNS = """
    evidence.public_id,
    co.offer_public_id AS commercial_offer_public_id,
    evidence.submission_reference,
    evidence.submission_channel,
    evidence.submitted_at,
    evidence.submitted_by,
    evidence.recipient_summary,
    evidence.submitted_amount_snapshot,
    evidence.submitted_currency_snapshot,
    evidence.submitted_version_snapshot,
    evidence.document_reference_label,
    evidence.document_reference_url_or_path,
    evidence.evidence_notes,
    evidence.active,
    evidence.created_by,
    evidence.created_at,
    evidence.updated_at
"""


def _row_to_submission_evidence(row: Any) -> CommercialOfferSubmissionEvidenceResponse:
    data = _row_mapping(row)
    return CommercialOfferSubmissionEvidenceResponse(
        public_id=data["public_id"],
        commercial_offer_public_id=data["commercial_offer_public_id"],
        submission_reference=data.get("submission_reference"),
        submission_channel=data["submission_channel"],
        submitted_at=data["submitted_at"],
        submitted_by=data.get("submitted_by"),
        recipient_summary=data.get("recipient_summary"),
        submitted_amount_snapshot=data.get("submitted_amount_snapshot"),
        submitted_currency_snapshot=data.get("submitted_currency_snapshot"),
        submitted_version_snapshot=data.get("submitted_version_snapshot"),
        document_reference_label=data.get("document_reference_label"),
        document_reference_url_or_path=data.get("document_reference_url_or_path"),
        evidence_notes=data.get("evidence_notes"),
        active=bool(data["active"]),
        created_by=data.get("created_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def insert_commercial_offer_submission_evidence(
    db: Session,
    *,
    public_id: str,
    commercial_offer_id: int,
    values: dict[str, Any],
) -> CommercialOfferSubmissionEvidenceResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_TABLE} (
                public_id,
                commercial_offer_id,
                submission_reference,
                submission_channel,
                submitted_at,
                submitted_by,
                recipient_summary,
                submitted_amount_snapshot,
                submitted_currency_snapshot,
                submitted_version_snapshot,
                document_reference_label,
                document_reference_url_or_path,
                evidence_notes,
                active,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :public_id,
                :commercial_offer_id,
                :submission_reference,
                :submission_channel,
                :submitted_at,
                :submitted_by,
                :recipient_summary,
                :submitted_amount_snapshot,
                :submitted_currency_snapshot,
                :submitted_version_snapshot,
                :document_reference_label,
                :document_reference_url_or_path,
                :evidence_notes,
                TRUE,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"public_id": public_id, "commercial_offer_id": commercial_offer_id, **values},
    )
    evidence = get_commercial_offer_submission_evidence_by_public_id(db, public_id=public_id)
    if evidence is None:
        raise RuntimeError("Inserted Commercial Offer submission evidence could not be reloaded.")
    return evidence


def get_commercial_offer_submission_evidence_by_public_id(
    db: Session,
    *,
    public_id: str,
) -> CommercialOfferSubmissionEvidenceResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_TABLE} evidence
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = evidence.commercial_offer_id
            WHERE evidence.public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_submission_evidence(row) if row else None


def list_commercial_offer_submission_evidence_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
) -> list[CommercialOfferSubmissionEvidenceResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_TABLE} evidence
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = evidence.commercial_offer_id
            WHERE evidence.commercial_offer_id = :commercial_offer_id
              AND evidence.active IS TRUE
            ORDER BY evidence.submitted_at DESC, evidence.created_at DESC, evidence.id DESC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [_row_to_submission_evidence(row) for row in rows]


def get_submission_evidence_context_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
    public_id: str,
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            f"""
            SELECT id, public_id
            FROM {COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_TABLE}
            WHERE commercial_offer_id = :commercial_offer_id
              AND public_id = :public_id
              AND active IS TRUE
            """
        ),
        {"commercial_offer_id": commercial_offer_id, "public_id": public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def get_revision_context_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
    public_id: str,
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            f"""
            SELECT id, public_id, revision_status
            FROM {COMMERCIAL_OFFER_REVISION_TABLE}
            WHERE commercial_offer_id = :commercial_offer_id
              AND public_id = :public_id
            """
        ),
        {"commercial_offer_id": commercial_offer_id, "public_id": public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def list_linked_work_order_contexts_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
) -> list[dict[str, Any]]:
    """Read-only lookup of Work Order shells handed off from this Commercial Offer.

    Mirrors the existing cross-module raw-SQL pattern already used elsewhere in this
    repository (e.g. crm_opportunity, business_party, tc_clause_library) rather than
    importing the work_orders module, keeping module boundaries intact.
    """
    rows = db.execute(
        text(
            """
            SELECT
                wo.work_order_public_id AS public_id,
                wo.work_order_code,
                wo.work_order_status_code
            FROM crm_work_order wo
            WHERE wo.commercial_offer_id = :commercial_offer_id
            ORDER BY wo.created_at DESC, wo.id DESC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def list_offer_line_handoff(db: Session, *, commercial_offer_id: int) -> list[dict[str, Any]]:
    """Each active line of this offer: its quantity, how much of it Work Orders hold, what is left, and the Work Orders
    holding it - in one statement, so every line is counted against the same moment (CS-04 part 1: an offer line's
    quantity goes onto Work Orders once, whole or in parts; review round 2 moved this off the page). Read-only, by the
    same cross-module SQL as the lookup above. Quantities in the list stay text, so no float ever carries them."""
    rows = db.execute(
        text(
            """
            SELECT
                col.line_public_id AS offer_line_public_id,
                col.line_number,
                col.quantity,
                COALESCE(SUM(wol.quantity), 0) AS quantity_on_work_orders,
                col.quantity - COALESCE(SUM(wol.quantity), 0) AS quantity_left,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'work_order_public_id', wo.work_order_public_id,
                            'work_order_code', wo.work_order_code,
                            'quantity', CAST(wol.quantity AS VARCHAR)
                        )
                        ORDER BY wo.id, wol.id
                    ) FILTER (WHERE wol.id IS NOT NULL),
                    '[]'
                ) AS work_orders
            FROM crm_commercial_offer_line col
            LEFT JOIN crm_work_order_line wol ON wol.commercial_offer_line_id = col.id
            LEFT JOIN crm_work_order wo ON wo.id = wol.work_order_id
            WHERE col.commercial_offer_id = :commercial_offer_id
              AND col.line_status_code = 'ACTIVE'
            GROUP BY col.id, col.line_public_id, col.line_number, col.quantity
            ORDER BY col.line_number ASC, col.id ASC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


COMMERCIAL_OFFER_CUSTOMER_RESPONSE_SELECT_COLUMNS = """
    response.public_id,
    co.offer_public_id AS commercial_offer_public_id,
    response.response_outcome,
    response.response_reference,
    response.response_received_at,
    response.response_channel,
    response.received_from,
    response.awarded_amount_snapshot,
    response.awarded_currency_snapshot,
    response.awarded_version_snapshot,
    response.customer_po_or_wo_reference,
    response.customer_response_notes,
    evidence.public_id AS linked_submission_evidence_public_id,
    revision.public_id AS linked_revision_public_id,
    response.created_by,
    response.created_at,
    response.updated_at
"""


def _row_to_customer_response(row: Any) -> CommercialOfferCustomerResponseResponse:
    data = _row_mapping(row)
    return CommercialOfferCustomerResponseResponse(
        public_id=data["public_id"],
        commercial_offer_public_id=data["commercial_offer_public_id"],
        response_outcome=data["response_outcome"],
        response_reference=data.get("response_reference"),
        response_received_at=data["response_received_at"],
        response_channel=data["response_channel"],
        received_from=data.get("received_from"),
        awarded_amount_snapshot=data.get("awarded_amount_snapshot"),
        awarded_currency_snapshot=data.get("awarded_currency_snapshot"),
        awarded_version_snapshot=data.get("awarded_version_snapshot"),
        customer_po_or_wo_reference=data.get("customer_po_or_wo_reference"),
        customer_response_notes=data.get("customer_response_notes"),
        linked_submission_evidence_public_id=data.get("linked_submission_evidence_public_id"),
        linked_revision_public_id=data.get("linked_revision_public_id"),
        created_by=data.get("created_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _customer_response_select_from() -> str:
    return f"""
        FROM {COMMERCIAL_OFFER_CUSTOMER_RESPONSE_TABLE} response
        INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = response.commercial_offer_id
        LEFT JOIN {COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_TABLE} evidence
            ON evidence.id = response.linked_submission_evidence_id
        LEFT JOIN {COMMERCIAL_OFFER_REVISION_TABLE} revision
            ON revision.id = response.linked_revision_id
    """


def insert_commercial_offer_customer_response(
    db: Session,
    *,
    public_id: str,
    commercial_offer_id: int,
    values: dict[str, Any],
) -> CommercialOfferCustomerResponseResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {COMMERCIAL_OFFER_CUSTOMER_RESPONSE_TABLE} (
                public_id, commercial_offer_id, response_outcome, response_reference,
                response_received_at, response_channel, received_from,
                awarded_amount_snapshot, awarded_currency_snapshot, awarded_version_snapshot,
                customer_po_or_wo_reference, customer_response_notes,
                linked_submission_evidence_id, linked_revision_id, created_by,
                created_at, updated_at
            ) VALUES (
                :public_id, :commercial_offer_id, :response_outcome, :response_reference,
                :response_received_at, :response_channel, :received_from,
                :awarded_amount_snapshot, :awarded_currency_snapshot, :awarded_version_snapshot,
                :customer_po_or_wo_reference, :customer_response_notes,
                :linked_submission_evidence_id, :linked_revision_id, :created_by,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        ),
        {"public_id": public_id, "commercial_offer_id": commercial_offer_id, **values},
    )
    row = db.execute(
        text(
            f"""
            SELECT {COMMERCIAL_OFFER_CUSTOMER_RESPONSE_SELECT_COLUMNS}
            {_customer_response_select_from()}
            WHERE response.public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    if row is None:
        raise RuntimeError("Inserted Commercial Offer customer response could not be reloaded.")
    return _row_to_customer_response(row)


def list_commercial_offer_customer_responses_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
) -> list[CommercialOfferCustomerResponseResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT {COMMERCIAL_OFFER_CUSTOMER_RESPONSE_SELECT_COLUMNS}
            {_customer_response_select_from()}
            WHERE response.commercial_offer_id = :commercial_offer_id
            ORDER BY response.response_received_at DESC, response.created_at DESC, response.id DESC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [_row_to_customer_response(row) for row in rows]


COMMERCIAL_OFFER_REVISION_SELECT_COLUMNS = """
    revision.public_id,
    co.offer_public_id AS commercial_offer_public_id,
    revision.revision_label,
    revision.revision_reason,
    revision.revision_notes,
    revision.revision_status,
    source_evidence.public_id AS source_submission_evidence_public_id,
    resubmission_evidence.public_id AS resubmission_evidence_public_id,
    revision.opened_at,
    revision.opened_by,
    revision.resubmitted_at,
    revision.cancelled_at,
    revision.created_by,
    revision.created_at,
    revision.updated_at
"""


def _row_to_revision(row: Any) -> CommercialOfferRevisionResponse:
    data = _row_mapping(row)
    return CommercialOfferRevisionResponse(
        public_id=data["public_id"],
        commercial_offer_public_id=data["commercial_offer_public_id"],
        revision_label=data["revision_label"],
        revision_reason=data["revision_reason"],
        revision_notes=data.get("revision_notes"),
        revision_status=data["revision_status"],
        source_submission_evidence_public_id=data.get("source_submission_evidence_public_id"),
        resubmission_evidence_public_id=data.get("resubmission_evidence_public_id"),
        opened_at=data["opened_at"],
        opened_by=data.get("opened_by"),
        resubmitted_at=data.get("resubmitted_at"),
        cancelled_at=data.get("cancelled_at"),
        created_by=data.get("created_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _revision_select_from() -> str:
    return f"""
        FROM {COMMERCIAL_OFFER_REVISION_TABLE} revision
        INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = revision.commercial_offer_id
        LEFT JOIN {COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_TABLE} source_evidence
            ON source_evidence.id = revision.source_submission_evidence_id
        LEFT JOIN {COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_TABLE} resubmission_evidence
            ON resubmission_evidence.id = revision.resubmission_evidence_id
    """


def insert_commercial_offer_revision(
    db: Session,
    *,
    public_id: str,
    commercial_offer_id: int,
    values: dict[str, Any],
) -> CommercialOfferRevisionResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {COMMERCIAL_OFFER_REVISION_TABLE} (
                public_id,
                commercial_offer_id,
                revision_label,
                revision_reason,
                revision_notes,
                revision_status,
                source_submission_evidence_id,
                resubmission_evidence_id,
                opened_at,
                opened_by,
                resubmitted_at,
                cancelled_at,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :public_id,
                :commercial_offer_id,
                :revision_label,
                :revision_reason,
                :revision_notes,
                :revision_status,
                :source_submission_evidence_id,
                NULL,
                :opened_at,
                :opened_by,
                NULL,
                NULL,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"public_id": public_id, "commercial_offer_id": commercial_offer_id, **values},
    )
    revision = get_commercial_offer_revision_for_offer(
        db,
        commercial_offer_id=commercial_offer_id,
        public_id=public_id,
    )
    if revision is None:
        raise RuntimeError("Inserted Commercial Offer revision could not be reloaded.")
    return revision


def get_commercial_offer_revision_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
    public_id: str,
) -> CommercialOfferRevisionResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT {COMMERCIAL_OFFER_REVISION_SELECT_COLUMNS}
            {_revision_select_from()}
            WHERE revision.commercial_offer_id = :commercial_offer_id
              AND revision.public_id = :public_id
            """
        ),
        {"commercial_offer_id": commercial_offer_id, "public_id": public_id},
    ).first()
    return _row_to_revision(row) if row else None


def list_commercial_offer_revisions_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
) -> list[CommercialOfferRevisionResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT {COMMERCIAL_OFFER_REVISION_SELECT_COLUMNS}
            {_revision_select_from()}
            WHERE revision.commercial_offer_id = :commercial_offer_id
            ORDER BY revision.opened_at DESC, revision.created_at DESC, revision.id DESC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [_row_to_revision(row) for row in rows]


def get_open_commercial_offer_revision_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
) -> CommercialOfferRevisionResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT {COMMERCIAL_OFFER_REVISION_SELECT_COLUMNS}
            {_revision_select_from()}
            WHERE revision.commercial_offer_id = :commercial_offer_id
              AND revision.revision_status = 'OPEN'
            ORDER BY revision.opened_at DESC, revision.created_at DESC, revision.id DESC
            LIMIT 1
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).first()
    return _row_to_revision(row) if row else None


def count_commercial_offer_revisions_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
) -> int:
    value = db.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM {COMMERCIAL_OFFER_REVISION_TABLE}
            WHERE commercial_offer_id = :commercial_offer_id
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).scalar_one()
    return int(value)


def update_commercial_offer_revision_status(
    db: Session,
    *,
    commercial_offer_id: int,
    public_id: str,
    expected_status: str,
    new_status: str,
    resubmission_evidence_id: int | None = None,
) -> CommercialOfferRevisionResponse | None:
    result = db.execute(
        text(
            f"""
            UPDATE {COMMERCIAL_OFFER_REVISION_TABLE}
            SET revision_status = :new_status,
                -- Explicit casts below are required by PostgreSQL, not cosmetic. A bare
                -- parameter under IS NULL carries no type information at all, and a
                -- parameter used both as a bare assignment and in a comparison is deduced
                -- as `text` in one place and `character varying` in the other. Either case
                -- is rejected as AmbiguousParameter. The values and behaviour are unchanged.
                resubmission_evidence_id = CASE
                    WHEN CAST(:resubmission_evidence_id AS INTEGER) IS NULL THEN resubmission_evidence_id
                    ELSE CAST(:resubmission_evidence_id AS INTEGER)
                END,
                resubmitted_at = CASE WHEN CAST(:new_status AS VARCHAR) = 'RESUBMITTED' THEN CURRENT_TIMESTAMP ELSE resubmitted_at END,
                cancelled_at = CASE WHEN CAST(:new_status AS VARCHAR) = 'CANCELLED' THEN CURRENT_TIMESTAMP ELSE cancelled_at END,
                updated_at = CURRENT_TIMESTAMP
            WHERE commercial_offer_id = :commercial_offer_id
              AND public_id = :public_id
              AND revision_status = :expected_status
            """
        ),
        {
            "commercial_offer_id": commercial_offer_id,
            "public_id": public_id,
            "expected_status": expected_status,
            "new_status": new_status,
            "resubmission_evidence_id": resubmission_evidence_id,
        },
    )
    if result.rowcount != 1:
        return None
    return get_commercial_offer_revision_for_offer(
        db,
        commercial_offer_id=commercial_offer_id,
        public_id=public_id,
    )


COMMERCIAL_OFFER_CREDIT_REVIEW_SELECT_COLUMNS = """
    review.public_id,
    co.offer_public_id AS commercial_offer_public_id,
    review.review_status,
    review.review_basis,
    review.review_reference,
    review.reviewed_at,
    review.reviewed_by,
    review.approved_amount_snapshot,
    review.credit_days_snapshot,
    review.exposure_note,
    review.active,
    review.created_by,
    review.created_at,
    review.updated_at
"""


def _row_to_credit_review(row: Any) -> CommercialOfferCreditReviewResponse:
    data = _row_mapping(row)
    return CommercialOfferCreditReviewResponse(
        public_id=data["public_id"],
        commercial_offer_public_id=data["commercial_offer_public_id"],
        review_status=data["review_status"],
        review_basis=data.get("review_basis"),
        review_reference=data.get("review_reference"),
        reviewed_at=data["reviewed_at"],
        reviewed_by=data.get("reviewed_by"),
        approved_amount_snapshot=data.get("approved_amount_snapshot"),
        credit_days_snapshot=data.get("credit_days_snapshot"),
        exposure_note=data.get("exposure_note"),
        active=bool(data["active"]),
        created_by=data.get("created_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def insert_commercial_offer_credit_review(
    db: Session,
    *,
    public_id: str,
    commercial_offer_id: int,
    values: dict[str, Any],
) -> CommercialOfferCreditReviewResponse:
    db.execute(
        text(
            f"""
            UPDATE {COMMERCIAL_OFFER_CREDIT_REVIEW_TABLE}
            SET active = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE commercial_offer_id = :commercial_offer_id
              AND active IS TRUE
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    )
    db.execute(
        text(
            f"""
            INSERT INTO {COMMERCIAL_OFFER_CREDIT_REVIEW_TABLE} (
                public_id,
                commercial_offer_id,
                review_status,
                review_basis,
                review_reference,
                reviewed_at,
                reviewed_by,
                approved_amount_snapshot,
                credit_days_snapshot,
                exposure_note,
                active,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :public_id,
                :commercial_offer_id,
                :review_status,
                :review_basis,
                :review_reference,
                :reviewed_at,
                :reviewed_by,
                :approved_amount_snapshot,
                :credit_days_snapshot,
                :exposure_note,
                TRUE,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"public_id": public_id, "commercial_offer_id": commercial_offer_id, **values},
    )
    review = get_commercial_offer_credit_review_by_public_id(db, public_id=public_id)
    if review is None:
        raise RuntimeError("Inserted Commercial Offer credit review could not be reloaded.")
    return review


def get_commercial_offer_credit_review_by_public_id(
    db: Session,
    *,
    public_id: str,
) -> CommercialOfferCreditReviewResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_CREDIT_REVIEW_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_CREDIT_REVIEW_TABLE} review
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = review.commercial_offer_id
            WHERE review.public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_credit_review(row) if row else None


def list_commercial_offer_credit_reviews_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
) -> list[CommercialOfferCreditReviewResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_CREDIT_REVIEW_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_CREDIT_REVIEW_TABLE} review
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = review.commercial_offer_id
            WHERE review.commercial_offer_id = :commercial_offer_id
            ORDER BY review.active DESC, review.reviewed_at DESC, review.created_at DESC, review.id DESC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [_row_to_credit_review(row) for row in rows]


def get_current_commercial_offer_credit_review(
    db: Session,
    *,
    commercial_offer_id: int,
) -> CommercialOfferCreditReviewResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_CREDIT_REVIEW_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_CREDIT_REVIEW_TABLE} review
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = review.commercial_offer_id
            WHERE review.commercial_offer_id = :commercial_offer_id
              AND review.active IS TRUE
            ORDER BY review.reviewed_at DESC, review.created_at DESC, review.id DESC
            LIMIT 1
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).first()
    return _row_to_credit_review(row) if row else None




COMMERCIAL_OFFER_PRICING_EVIDENCE_SELECT_COLUMNS = """
    pe.id AS pricing_evidence_id,
    pe.evidence_public_id AS public_id,
    co.offer_public_id AS commercial_offer_public_id,
    rate_line.line_public_id,
    rate_line.line_number,
    rate_line.line_status_code,
    pe.recorded_for_whole_offer,
    quote_copy.evidence_public_id AS quote_copy_rate_public_id,
    pe.evidence_type,
    pe.source_name,
    pe.vendor_contact,
    pe.equipment_service_description,
    pe.rate_amount,
    pe.currency_code,
    pe.rate_basis,
    pe.collected_by_name,
    pe.collected_at,
    pe.source_reference,
    CASE WHEN pe.recorded_for_whole_offer THEN pe.is_selected_basis ELSE open_choice.id IS NOT NULL END
        AS is_selected_basis,
    CASE WHEN pe.recorded_for_whole_offer THEN pe.selection_reason ELSE open_choice.selection_reason END
        AS selection_reason,
    pe.comparison_notes,
    pe.created_by,
    pe.created_at,
    pe.updated_at
"""

# A line's rate is its line's basis while it holds the line's open choice, and gives that choice's reason (Slice 4G);
# a rate recorded for the whole offer before then keeps the marker and reason stored on it.
COMMERCIAL_OFFER_PRICING_EVIDENCE_FROM = f"""
    {COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE} pe
    INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = pe.commercial_offer_id
    LEFT JOIN {COMMERCIAL_OFFER_LINE_TABLE} rate_line ON rate_line.id = pe.commercial_offer_line_id
    LEFT JOIN {COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE} quote_copy ON quote_copy.id = pe.quote_copy_evidence_id
    LEFT JOIN {COMMERCIAL_OFFER_LINE_BASIS_CHOICE_TABLE} open_choice
        ON open_choice.pricing_evidence_id = pe.id AND open_choice.ended_at IS NULL
"""


def _row_to_pricing_evidence(row: Any) -> CommercialOfferPricingEvidenceResponse:
    data = _row_mapping(row)
    return CommercialOfferPricingEvidenceResponse(
        public_id=data["public_id"],
        commercial_offer_public_id=data["commercial_offer_public_id"],
        line_public_id=data.get("line_public_id"),
        line_number=data.get("line_number"),
        line_status_code=data.get("line_status_code"),
        recorded_for_whole_offer=bool(data["recorded_for_whole_offer"]),
        quote_copy_rate_public_id=data.get("quote_copy_rate_public_id"),
        evidence_type=data["evidence_type"],
        source_name=data.get("source_name"),
        vendor_contact=data.get("vendor_contact"),
        equipment_service_description=data["equipment_service_description"],
        rate_amount=data["rate_amount"],
        currency_code=data["currency_code"],
        rate_basis=data["rate_basis"],
        collected_by_name=data.get("collected_by_name"),
        collected_at=data.get("collected_at"),
        source_reference=data.get("source_reference"),
        is_selected_basis=bool(data["is_selected_basis"]),
        selection_reason=data.get("selection_reason"),
        comparison_notes=data.get("comparison_notes"),
        created_by=data.get("created_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def get_commercial_offer_context_by_public_id(db: Session, public_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            f"""
            SELECT
                co.id AS commercial_offer_id,
                co.offer_public_id,
                co.offer_code,
                co.offer_status_code,
                co.version_number,
                o.opportunity_public_id,
                COALESCE(offer_bp.business_party_public_id, opportunity_bp.business_party_public_id) AS account_public_id
            FROM {COMMERCIAL_OFFER_TABLE} co
            INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
            LEFT JOIN business_party offer_bp ON offer_bp.id = co.business_party_id
            LEFT JOIN business_party opportunity_bp ON opportunity_bp.id = o.business_party_id
            WHERE co.offer_public_id = :public_id
            LIMIT 1
            """
        ),
        {"public_id": public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def insert_pricing_evidence(
    db: Session,
    *,
    public_id: str,
    commercial_offer_id: int,
    commercial_offer_line_id: int,
    quote_copy_evidence_id: int | None,
    values: dict[str, Any],
) -> CommercialOfferPricingEvidenceResponse:
    """A new rate for one line of the offer, never the basis yet: choosing it is choose_line_basis_rate (Slice 4G)."""
    db.execute(
        text(
            f"""
            INSERT INTO {COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE} (
                evidence_public_id,
                commercial_offer_id,
                commercial_offer_line_id,
                recorded_for_whole_offer,
                quote_copy_evidence_id,
                evidence_type,
                source_name,
                vendor_contact,
                equipment_service_description,
                rate_amount,
                currency_code,
                rate_basis,
                collected_by_name,
                collected_at,
                source_reference,
                is_selected_basis,
                comparison_notes,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :evidence_public_id,
                :commercial_offer_id,
                :commercial_offer_line_id,
                FALSE,
                :quote_copy_evidence_id,
                :evidence_type,
                :source_name,
                :vendor_contact,
                :equipment_service_description,
                :rate_amount,
                :currency_code,
                :rate_basis,
                :collected_by_name,
                :collected_at,
                :source_reference,
                FALSE,
                :comparison_notes,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "evidence_public_id": public_id,
            "commercial_offer_id": commercial_offer_id,
            "commercial_offer_line_id": commercial_offer_line_id,
            "quote_copy_evidence_id": quote_copy_evidence_id,
            "evidence_type": values["evidence_type"],
            "source_name": values["source_name"],
            "vendor_contact": values["vendor_contact"],
            "equipment_service_description": values["equipment_service_description"],
            "rate_amount": values["rate_amount"],
            "currency_code": values["currency_code"],
            "rate_basis": values["rate_basis"],
            "collected_by_name": values["collected_by_name"],
            "collected_at": values["collected_at"],
            "source_reference": values["source_reference"],
            "comparison_notes": values["comparison_notes"],
            "created_by": values["created_by"],
        },
    )
    evidence = get_pricing_evidence_by_public_id(db, public_id)
    if evidence is None:
        raise RuntimeError("Inserted Commercial Offer pricing evidence could not be reloaded.")
    return evidence


def get_pricing_evidence_by_public_id(db: Session, public_id: str) -> CommercialOfferPricingEvidenceResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_PRICING_EVIDENCE_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_PRICING_EVIDENCE_FROM}
            WHERE pe.evidence_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_pricing_evidence(row) if row else None


def get_pricing_evidence_context(
    db: Session,
    *,
    evidence_public_id: str,
    commercial_offer_id: int | None = None,
) -> dict[str, Any] | None:
    """One rate with its line and offer; within one offer when commercial_offer_id is given."""
    row = db.execute(
        text(
            f"""
            SELECT
                pe.id AS pricing_evidence_id,
                pe.evidence_public_id,
                pe.commercial_offer_id,
                co.offer_public_id,
                pe.evidence_type,
                CASE WHEN pe.recorded_for_whole_offer THEN pe.is_selected_basis
                     ELSE EXISTS (
                         SELECT 1 FROM {COMMERCIAL_OFFER_LINE_BASIS_CHOICE_TABLE} open_choice
                         WHERE open_choice.pricing_evidence_id = pe.id AND open_choice.ended_at IS NULL
                     )
                END AS is_selected_basis,
                pe.recorded_for_whole_offer,
                pe.commercial_offer_line_id,
                rate_line.line_public_id,
                rate_line.line_number,
                rate_line.line_status_code
            FROM {COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE} pe
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = pe.commercial_offer_id
            LEFT JOIN {COMMERCIAL_OFFER_LINE_TABLE} rate_line ON rate_line.id = pe.commercial_offer_line_id
            WHERE pe.evidence_public_id = :evidence_public_id
              AND (CAST(:commercial_offer_id AS integer) IS NULL OR pe.commercial_offer_id = :commercial_offer_id)
            LIMIT 1
            """
        ),
        {"commercial_offer_id": commercial_offer_id, "evidence_public_id": evidence_public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def list_pricing_evidence_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
) -> list[CommercialOfferPricingEvidenceResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_PRICING_EVIDENCE_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_PRICING_EVIDENCE_FROM}
            WHERE pe.commercial_offer_id = :commercial_offer_id
            ORDER BY rate_line.line_number NULLS LAST, (open_choice.id IS NOT NULL OR pe.is_selected_basis) DESC,
                     pe.collected_at DESC NULLS LAST,
                     pe.created_at DESC, pe.id DESC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [_row_to_pricing_evidence(row) for row in rows]


def list_basis_choices_for_rates(db: Session, *, evidence_public_ids: list[str]) -> list[dict[str, Any]]:
    """Every basis choice of these rates, oldest first: who chose each, when and why, and when and by whom it ended
    (Slice 4G). A choice carried into a new version names the version it was carried from."""
    if not evidence_public_ids:
        return []
    statement = text(
        f"""
        SELECT
            choice.choice_public_id AS public_id,
            pe.evidence_public_id AS pricing_evidence_public_id,
            choice.selection_reason,
            choice.chosen_by,
            chooser.display_name AS chosen_by_display_name,
            choice.chosen_at,
            choice.ended_by,
            ender.display_name AS ended_by_display_name,
            choice.ended_at,
            carried_offer.version_number AS carried_over_from_version_number
        FROM {COMMERCIAL_OFFER_LINE_BASIS_CHOICE_TABLE} choice
        INNER JOIN {COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE} pe ON pe.id = choice.pricing_evidence_id
        LEFT JOIN app_user chooser ON chooser.public_id = choice.chosen_by
        LEFT JOIN app_user ender ON ender.public_id = choice.ended_by
        LEFT JOIN {COMMERCIAL_OFFER_LINE_BASIS_CHOICE_TABLE} carried ON carried.id = choice.carried_from_choice_id
        LEFT JOIN {COMMERCIAL_OFFER_LINE_TABLE} carried_line ON carried_line.id = carried.commercial_offer_line_id
        LEFT JOIN {COMMERCIAL_OFFER_TABLE} carried_offer ON carried_offer.id = carried_line.commercial_offer_id
        WHERE pe.evidence_public_id IN :ids
        ORDER BY choice.chosen_at, choice.id
        """
    ).bindparams(bindparam("ids", expanding=True))
    return [dict(_row_mapping(row)) for row in db.execute(statement, {"ids": evidence_public_ids}).fetchall()]


def list_quote_copy_holders_for_rates(db: Session, *, evidence_public_ids: list[str]) -> list[dict[str, Any]]:
    """For each rate, every rate whose attached documents serve as its quote copy: itself, the rate it refers to - or,
    for a new version's rate, the rate it was copied from - that rate's own link, and so on (Slice 4G). The database lets a rate refer only to a rate entered before it
    (a smaller id), so each step goes to a smaller id and the chain ends however long it is (review 4G-R3-001)."""
    if not evidence_public_ids:
        return []
    statement = text(
        f"""
        WITH RECURSIVE holder(rate_id, holder_id, depth) AS (
            SELECT pe.id, pe.id, 0
            FROM {COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE} pe
            WHERE pe.evidence_public_id IN :ids
            UNION ALL
            SELECT holder.rate_id, COALESCE(referred.quote_copy_evidence_id, referred.copied_from_evidence_id),
                   holder.depth + 1
            FROM holder
            INNER JOIN {COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE} referred ON referred.id = holder.holder_id
            WHERE COALESCE(referred.quote_copy_evidence_id, referred.copied_from_evidence_id) IS NOT NULL
        )
        SELECT
            rate.evidence_public_id AS rate_public_id,
            held.evidence_public_id AS holder_public_id,
            holder_line.line_number AS holder_line_number,
            holder_offer.version_number AS holder_offer_version_number,
            holder.depth
        FROM holder
        INNER JOIN {COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE} rate ON rate.id = holder.rate_id
        INNER JOIN {COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE} held ON held.id = holder.holder_id
        INNER JOIN {COMMERCIAL_OFFER_TABLE} holder_offer ON holder_offer.id = held.commercial_offer_id
        LEFT JOIN {COMMERCIAL_OFFER_LINE_TABLE} holder_line ON holder_line.id = held.commercial_offer_line_id
        ORDER BY rate.evidence_public_id, holder.depth
        """
    ).bindparams(bindparam("ids", expanding=True))
    return [dict(_row_mapping(row)) for row in db.execute(statement, {"ids": evidence_public_ids}).fetchall()]


def choose_line_basis_rate(
    db: Session,
    *,
    commercial_offer_line_id: int,
    pricing_evidence_id: int,
    selection_reason: str,
    current_user_public_id: str | None,
) -> str | None:
    """Make this rate its line's basis (Slice 4G). The line's open choice, if any, is ended - never rewritten or
    deleted - and a new choice is recorded with its reason. Returns the public id of the rate that was the basis
    before, if there was one. The open choice is the line's basis: the database holds one per line."""
    previous = db.execute(
        text(
            f"""
            UPDATE {COMMERCIAL_OFFER_LINE_BASIS_CHOICE_TABLE} choice
            SET ended_at = CURRENT_TIMESTAMP,
                ended_by = :actor
            FROM {COMMERCIAL_OFFER_PRICING_EVIDENCE_TABLE} pe
            WHERE choice.commercial_offer_line_id = :line_id
              AND choice.ended_at IS NULL
              AND pe.id = choice.pricing_evidence_id
            RETURNING pe.evidence_public_id
            """
        ),
        {"line_id": commercial_offer_line_id, "actor": current_user_public_id},
    ).scalar()
    db.execute(
        text(
            f"""
            INSERT INTO {COMMERCIAL_OFFER_LINE_BASIS_CHOICE_TABLE} (
                choice_public_id, commercial_offer_line_id, pricing_evidence_id, selection_reason,
                chosen_by, chosen_at, created_at
            ) VALUES (
                :public_id, :line_id, :evidence_id, :selection_reason, :actor, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "public_id": str(uuid4()),
            "line_id": commercial_offer_line_id,
            "evidence_id": pricing_evidence_id,
            "selection_reason": selection_reason,
            "actor": current_user_public_id,
        },
    )
    return str(previous) if previous else None


COMMERCIAL_OFFER_LINE_SELECT_COLUMNS = """
    line.line_public_id AS public_id,
    co.offer_public_id AS commercial_offer_public_id,
    line.line_number,
    line.line_status_code,
    line.scope_description,
    line.equipment_service_category,
    line.quantity,
    line.uom,
    line.rate_amount,
    line.currency_code,
    line.line_amount,
    line.remarks,
    line.created_by,
    line.created_at,
    line.updated_at,
    line.row_version
"""

COMMERCIAL_OFFER_LINE_UPDATE_COLUMNS = (
    "line_number",
    "line_status_code",
    "scope_description",
    "equipment_service_category",
    "quantity",
    "uom",
    "rate_amount",
    "currency_code",
    "line_amount",
    "remarks",
)


def _row_to_commercial_offer_line(row: Any) -> CommercialOfferLineResponse:
    data = _row_mapping(row)
    return CommercialOfferLineResponse(
        public_id=data["public_id"],
        commercial_offer_public_id=data["commercial_offer_public_id"],
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
        created_by=data.get("created_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        row_version=data["row_version"],
    )


def get_next_commercial_offer_line_number(db: Session, *, commercial_offer_id: int) -> int:
    value = db.execute(
        text(
            f"""
            SELECT COALESCE(MAX(line_number), 0) + 1
            FROM {COMMERCIAL_OFFER_LINE_TABLE}
            WHERE commercial_offer_id = :commercial_offer_id
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).scalar()
    return int(value or 1)


def insert_commercial_offer_line(
    db: Session,
    *,
    public_id: str,
    commercial_offer_id: int,
    values: dict[str, Any],
) -> CommercialOfferLineResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {COMMERCIAL_OFFER_LINE_TABLE} (
                line_public_id,
                commercial_offer_id,
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
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :line_public_id,
                :commercial_offer_id,
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
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"line_public_id": public_id, "commercial_offer_id": commercial_offer_id, **values},
    )
    offer_line = get_commercial_offer_line_by_public_id(
        db,
        commercial_offer_id=commercial_offer_id,
        line_public_id=public_id,
    )
    if offer_line is None:
        raise RuntimeError("Inserted Commercial Offer line could not be reloaded.")
    return offer_line


def get_commercial_offer_line_by_public_id(
    db: Session,
    *,
    commercial_offer_id: int,
    line_public_id: str,
) -> CommercialOfferLineResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_LINE_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_LINE_TABLE} line
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = line.commercial_offer_id
            WHERE line.commercial_offer_id = :commercial_offer_id
              AND line.line_public_id = :line_public_id
            """
        ),
        {"commercial_offer_id": commercial_offer_id, "line_public_id": line_public_id},
    ).first()
    return _row_to_commercial_offer_line(row) if row else None


def get_commercial_offer_line_context(
    db: Session,
    *,
    commercial_offer_id: int,
    line_public_id: str,
    for_update: bool = False,
) -> dict[str, Any] | None:
    """One line as it stands. With for_update the line's row stays locked to the end of the caller's transaction
    (FOR NO KEY UPDATE, the lock its own UPDATE takes), so what the caller computes from it - a line's amount from
    its quantity and rate (CS-05a) - is computed from the row it then writes, whatever else writes lines."""
    lock = "FOR NO KEY UPDATE" if for_update else ""
    row = db.execute(
        text(
            f"""
            SELECT
                line.id AS line_id,
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
                line.remarks,
                line.row_version
            FROM {COMMERCIAL_OFFER_LINE_TABLE} line
            WHERE line.commercial_offer_id = :commercial_offer_id
              AND line.line_public_id = :line_public_id
            LIMIT 1
            {lock}
            """
        ),
        {"commercial_offer_id": commercial_offer_id, "line_public_id": line_public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def list_commercial_offer_lines_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
) -> list[CommercialOfferLineResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_LINE_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_LINE_TABLE} line
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = line.commercial_offer_id
            WHERE line.commercial_offer_id = :commercial_offer_id
            ORDER BY line.line_number ASC, line.id ASC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [_row_to_commercial_offer_line(row) for row in rows]


def update_commercial_offer_line_by_public_id(
    db: Session,
    *,
    commercial_offer_id: int,
    line_public_id: str,
    values: dict[str, Any],
    expected_row_version: int,
) -> CommercialOfferLineResponse | None:
    """Write the line's row while it still has expected_row_version, raising it by one (CS-05a). Returns None when
    no row was written: the line has moved on, or is not on this offer."""
    assignments = [f"{column} = :{column}" for column in COMMERCIAL_OFFER_LINE_UPDATE_COLUMNS if column in values]
    if assignments:
        assignments.append("updated_at = CURRENT_TIMESTAMP")
        assignments.append("row_version = row_version + 1")
        result = db.execute(
            text(
                f"""
                UPDATE {COMMERCIAL_OFFER_LINE_TABLE}
                SET {', '.join(assignments)}
                WHERE commercial_offer_id = :commercial_offer_id
                  AND line_public_id = :line_public_id
                  AND row_version = :expected_row_version
                """
            ),
            {
                "commercial_offer_id": commercial_offer_id,
                "line_public_id": line_public_id,
                "expected_row_version": expected_row_version,
                **values,
            },
        )
        if result.rowcount != 1:
            return None

    return get_commercial_offer_line_by_public_id(
        db,
        commercial_offer_id=commercial_offer_id,
        line_public_id=line_public_id,
    )


COMMERCIAL_OFFER_TC_CLAUSE_SELECT_COLUMNS = """
    attachment.public_id,
    co.offer_public_id AS commercial_offer_public_id,
    clause.public_id AS tc_clause_public_id,
    attachment.clause_id_snapshot,
    attachment.title_snapshot,
    attachment.clause_text_snapshot,
    attachment.business_line_snapshot,
    attachment.clause_category_snapshot,
    attachment.source_clause_number_snapshot,
    attachment.source_reference_snapshot,
    attachment.mandatory_default_snapshot,
    attachment.risk_category_snapshot,
    attachment.applies_to_header_snapshot,
    attachment.applies_to_line_snapshot,
    attachment.requires_approval_if_omitted_snapshot,
    attachment.requires_approval_if_modified_snapshot,
    attachment.sort_order,
    attachment.active,
    attachment.attached_by,
    attachment.created_at,
    attachment.updated_at
"""


def _row_to_commercial_offer_tc_clause(row: Any) -> CommercialOfferTcClauseResponse:
    data = _row_mapping(row)
    return CommercialOfferTcClauseResponse(
        public_id=data["public_id"],
        commercial_offer_public_id=data["commercial_offer_public_id"],
        tc_clause_public_id=data["tc_clause_public_id"],
        clause_id_snapshot=data["clause_id_snapshot"],
        title_snapshot=data["title_snapshot"],
        clause_text_snapshot=data["clause_text_snapshot"],
        business_line_snapshot=data["business_line_snapshot"],
        clause_category_snapshot=data["clause_category_snapshot"],
        source_clause_number_snapshot=data.get("source_clause_number_snapshot"),
        source_reference_snapshot=data.get("source_reference_snapshot"),
        mandatory_default_snapshot=bool(data["mandatory_default_snapshot"]),
        risk_category_snapshot=data.get("risk_category_snapshot"),
        applies_to_header_snapshot=bool(data["applies_to_header_snapshot"]),
        applies_to_line_snapshot=bool(data["applies_to_line_snapshot"]),
        requires_approval_if_omitted_snapshot=bool(data["requires_approval_if_omitted_snapshot"]),
        requires_approval_if_modified_snapshot=bool(data["requires_approval_if_modified_snapshot"]),
        sort_order=data["sort_order"],
        active=bool(data["active"]),
        attached_by=data.get("attached_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def list_commercial_offer_tc_clauses_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
) -> list[CommercialOfferTcClauseResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_TC_CLAUSE_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_TC_CLAUSE_TABLE} attachment
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = attachment.commercial_offer_id
            INNER JOIN {TC_CLAUSE_LIBRARY_TABLE} clause ON clause.id = attachment.tc_clause_id
            WHERE attachment.commercial_offer_id = :commercial_offer_id
              AND attachment.active IS TRUE
            ORDER BY attachment.sort_order ASC, attachment.created_at ASC, attachment.id ASC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [_row_to_commercial_offer_tc_clause(row) for row in rows]


def list_recommended_tc_clause_contexts(
    db: Session,
    *,
    recommendation_basis: str,
) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            f"""
            SELECT
                id AS tc_clause_id,
                public_id,
                clause_id,
                business_line,
                clause_category,
                source_clause_number,
                title,
                clause_text,
                mandatory_default,
                risk_category,
                applies_to_header,
                applies_to_line,
                requires_approval_if_omitted,
                requires_approval_if_modified,
                active,
                source_reference
            FROM {TC_CLAUSE_LIBRARY_TABLE}
            WHERE business_line = :recommendation_basis
              AND active IS TRUE
              AND applies_to_header IS TRUE
            ORDER BY mandatory_default DESC, clause_id ASC, id ASC
            """
        ),
        {"recommendation_basis": recommendation_basis},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def list_active_commercial_offer_tc_clause_attachment_contexts(
    db: Session,
    *,
    commercial_offer_id: int,
) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            f"""
            SELECT
                attachment.id AS attachment_id,
                attachment.public_id,
                attachment.tc_clause_id,
                attachment.clause_id_snapshot,
                attachment.title_snapshot,
                attachment.mandatory_default_snapshot,
                attachment.active
            FROM {COMMERCIAL_OFFER_TC_CLAUSE_TABLE} attachment
            WHERE attachment.commercial_offer_id = :commercial_offer_id
              AND attachment.active IS TRUE
            ORDER BY attachment.sort_order ASC, attachment.created_at ASC, attachment.id ASC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [dict(_row_mapping(row)) for row in rows]


def get_tc_clause_context_by_public_id(db: Session, public_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            f"""
            SELECT
                id AS tc_clause_id,
                public_id,
                clause_id,
                business_line,
                clause_category,
                source_clause_number,
                title,
                clause_text,
                mandatory_default,
                risk_category,
                applies_to_header,
                applies_to_line,
                requires_approval_if_omitted,
                requires_approval_if_modified,
                active,
                source_reference
            FROM {TC_CLAUSE_LIBRARY_TABLE}
            WHERE public_id = :public_id
            LIMIT 1
            """
        ),
        {"public_id": public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def active_commercial_offer_tc_clause_attachment_exists(
    db: Session,
    *,
    commercial_offer_id: int,
    tc_clause_id: int,
) -> bool:
    exists = db.execute(
        text(
            f"""
            SELECT 1
            FROM {COMMERCIAL_OFFER_TC_CLAUSE_TABLE}
            WHERE commercial_offer_id = :commercial_offer_id
              AND tc_clause_id = :tc_clause_id
              AND active IS TRUE
            """
        ),
        {"commercial_offer_id": commercial_offer_id, "tc_clause_id": tc_clause_id},
    ).scalar()
    return exists == 1


def get_next_commercial_offer_tc_clause_sort_order(db: Session, *, commercial_offer_id: int) -> int:
    value = db.execute(
        text(
            f"""
            SELECT COALESCE(MAX(sort_order), 0) + 1
            FROM {COMMERCIAL_OFFER_TC_CLAUSE_TABLE}
            WHERE commercial_offer_id = :commercial_offer_id
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).scalar()
    return int(value or 1)


def insert_commercial_offer_tc_clause_attachment(
    db: Session,
    *,
    public_id: str,
    commercial_offer_id: int,
    tc_clause_id: int,
    values: dict[str, Any],
) -> CommercialOfferTcClauseResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {COMMERCIAL_OFFER_TC_CLAUSE_TABLE} (
                public_id,
                commercial_offer_id,
                tc_clause_id,
                clause_id_snapshot,
                title_snapshot,
                clause_text_snapshot,
                business_line_snapshot,
                clause_category_snapshot,
                source_clause_number_snapshot,
                source_reference_snapshot,
                mandatory_default_snapshot,
                risk_category_snapshot,
                applies_to_header_snapshot,
                applies_to_line_snapshot,
                requires_approval_if_omitted_snapshot,
                requires_approval_if_modified_snapshot,
                sort_order,
                active,
                attached_by,
                created_at,
                updated_at
            ) VALUES (
                :public_id,
                :commercial_offer_id,
                :tc_clause_id,
                :clause_id_snapshot,
                :title_snapshot,
                :clause_text_snapshot,
                :business_line_snapshot,
                :clause_category_snapshot,
                :source_clause_number_snapshot,
                :source_reference_snapshot,
                :mandatory_default_snapshot,
                :risk_category_snapshot,
                :applies_to_header_snapshot,
                :applies_to_line_snapshot,
                :requires_approval_if_omitted_snapshot,
                :requires_approval_if_modified_snapshot,
                :sort_order,
                TRUE,
                :attached_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"public_id": public_id, "commercial_offer_id": commercial_offer_id, "tc_clause_id": tc_clause_id, **values},
    )
    attachment = get_commercial_offer_tc_clause_attachment_by_public_id(db, public_id=public_id)
    if attachment is None:
        raise RuntimeError("Inserted Commercial Offer T&C clause attachment could not be reloaded.")
    return attachment


def get_commercial_offer_tc_clause_attachment_by_public_id(
    db: Session,
    *,
    public_id: str,
) -> CommercialOfferTcClauseResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {COMMERCIAL_OFFER_TC_CLAUSE_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_TC_CLAUSE_TABLE} attachment
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = attachment.commercial_offer_id
            INNER JOIN {TC_CLAUSE_LIBRARY_TABLE} clause ON clause.id = attachment.tc_clause_id
            WHERE attachment.public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_commercial_offer_tc_clause(row) if row else None


def get_commercial_offer_tc_clause_attachment_context(
    db: Session,
    *,
    commercial_offer_id: int,
    attachment_public_id: str,
) -> dict[str, Any] | None:
    row = db.execute(
        text(
            f"""
            SELECT
                attachment.id AS attachment_id,
                attachment.public_id,
                attachment.tc_clause_id,
                attachment.clause_id_snapshot,
                attachment.title_snapshot,
                attachment.active
            FROM {COMMERCIAL_OFFER_TC_CLAUSE_TABLE} attachment
            WHERE attachment.commercial_offer_id = :commercial_offer_id
              AND attachment.public_id = :attachment_public_id
            LIMIT 1
            """
        ),
        {"commercial_offer_id": commercial_offer_id, "attachment_public_id": attachment_public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def deactivate_commercial_offer_tc_clause_attachment(
    db: Session,
    *,
    commercial_offer_id: int,
    attachment_public_id: str,
) -> CommercialOfferTcClauseResponse | None:
    db.execute(
        text(
            f"""
            UPDATE {COMMERCIAL_OFFER_TC_CLAUSE_TABLE}
            SET active = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE commercial_offer_id = :commercial_offer_id
              AND public_id = :attachment_public_id
              AND active IS TRUE
            """
        ),
        {"commercial_offer_id": commercial_offer_id, "attachment_public_id": attachment_public_id},
    )
    return get_commercial_offer_tc_clause_attachment_by_public_id(db, public_id=attachment_public_id)


def lock_commercial_offer_row(db: Session, *, public_id: str) -> int | None:
    """Take a row-level exclusive lock on one Commercial Offer for the current transaction.

    Any caller that reads `offer_status_code` and then conditionally writes it must lock first.
    Without the lock two concurrent requests can both observe an allowed status and both commit:
    a REJECTED_LOST response could land, and a concurrent ACCEPTED_AWARDED could then overwrite
    it, leaving a rejected offer reactivated to ACCEPTED with both response rows recorded. The
    lock is released when the surrounding transaction commits or rolls back.

    Returns the internal id, or None when no such offer exists.
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
        {"public_id": public_id},
    ).first()
    return int(row[0]) if row is not None else None


def lock_opportunity_row(db: Session, *, opportunity_public_id: str) -> int | None:
    """Row-lock the parent Opportunity for the current transaction.

    Commercial Offer creation reads the Opportunity's status (rejecting WON/LOST/CLOSED) and
    checks the Slice 6B.1 one-active-Base-Offer rule, then inserts. A row lock is used rather
    than an advisory lock because it does two things an advisory lock cannot:

    - it serializes offer creation against *any* concurrent writer of that Opportunity row,
      including `update_opportunity` moving it to WON/LOST/CLOSED, because an UPDATE must take
      the same row lock. An advisory lock only excludes other advisory-lock takers, so the
      Opportunity could still close between the status read and the insert;
    - it serializes two concurrent Base Offer creations for the same Opportunity, which is what
      the advisory lock was added for. That advisory lock is therefore removed as redundant.

    This locks a row owned by the Opportunity module. That is a deliberate, narrow exception: it
    takes no data and changes nothing, and the alternative - a database-level partial unique
    index - needs a migration, which this slice does not take because the Hiring lane owns the
    Alembic head. The index remains the stronger long-term control.

    Since CS-05c (migration 20260908_0053) the index exists too: the lock still serializes creations, so the second
    gets the check's refusal, and the index holds the rule against any writer that does not take the lock.
    """
    row = db.execute(
        text(
            """
            SELECT id
            FROM crm_opportunity
            WHERE opportunity_public_id = :public_id
            FOR UPDATE
            """
        ),
        {"public_id": opportunity_public_id},
    ).first()
    return int(row[0]) if row is not None else None


# ---------------------------------------------------------------------------------------------
# Slice 9E - Quotation Generation foundation.
# ---------------------------------------------------------------------------------------

QUOTE_DOCUMENT_SELECT_COLUMNS = """
    qd.quote_document_public_id AS public_id,
    co.offer_public_id AS commercial_offer_public_id,
    qd.version_no,
    qd.quote_reference,
    qd.document_public_id,
    qd.source_fingerprint,
    qd.quote_status_code,
    qd.generated_by,
    generator.display_name AS generated_by_display_name,
    qd.generated_at,
    qd.approved_by,
    approver.display_name AS approved_by_display_name,
    qd.approved_at,
    qd.approval_note,
    qd.superseded_at,
    qd.created_at,
    qd.updated_at
"""

# Resolved in the same query rather than per row, so listing N versions stays one round trip.
# LEFT JOINs, because a version generated by a user who was later removed must still list -
# the display name simply comes back NULL rather than dropping the row.
QUOTE_DOCUMENT_ACTOR_JOINS = """
    LEFT JOIN app_user generator ON generator.public_id = qd.generated_by
    LEFT JOIN app_user approver ON approver.public_id = qd.approved_by
"""


def get_user_display_name(db: Session, *, public_id: str | None) -> str | None:
    """Read-only display-name lookup for the quotation's prepared-by line.

    A read-only join/lookup against another module's table, consistent with what this repository
    already does for business_party, crm_opportunity, crm_work_order and interaction, rather than
    importing the identity module's repository across a module boundary.
    """
    if not public_id:
        return None
    row = db.execute(
        text("SELECT display_name FROM app_user WHERE public_id = :public_id"),
        {"public_id": public_id},
    ).first()
    return str(row[0]) if row is not None and row[0] else None


def _row_to_quote_document_dict(row: Any) -> dict[str, Any]:
    """Returns a plain dict, not a Pydantic response object.

    Unlike every other subordinate-record row-mapper in this file, a quote document's response
    needs one field (`is_stale`) that cannot be computed from this row alone - it requires
    recomputing the CURRENT source fingerprint and comparing it, which is a service-layer
    concern (it needs to call build_quote_snapshot again). Returning a plain dict here, rather
    than a schema object a caller would have to reconstruct around, keeps that boundary honest.
    """
    data = _row_mapping(row)
    return dict(data)


def get_quote_snapshot_source_context(db: Session, *, commercial_offer_id: int) -> dict[str, Any] | None:
    """Read-only lookup of everything build_quote_snapshot() needs about the offer header,
    Account identity and Opportunity reference. Lines and T&C clauses are fetched separately
    through the existing list_commercial_offer_lines_for_offer /
    list_commercial_offer_tc_clauses_for_offer functions, which this module already has."""
    row = db.execute(
        text(
            f"""
            SELECT
                co.id AS commercial_offer_id,
                co.offer_public_id,
                co.offer_code,
                co.offer_status_code,
                co.offer_date,
                co.valid_until,
                co.currency_code,
                co.customer_request_reference,
                o.opportunity_public_id,
                COALESCE(offer_bp.business_party_public_id, opportunity_bp.business_party_public_id) AS account_public_id,
                COALESCE(offer_bp.account_name, opportunity_bp.account_name) AS account_name,
                COALESCE(offer_bp.legal_name, opportunity_bp.legal_name) AS account_legal_name
            FROM {COMMERCIAL_OFFER_TABLE} co
            INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
            LEFT JOIN business_party offer_bp ON offer_bp.id = co.business_party_id
            LEFT JOIN business_party opportunity_bp ON opportunity_bp.id = o.business_party_id
            WHERE co.id = :commercial_offer_id
            LIMIT 1
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


@contextmanager
def single_instant_read_session(db: Session) -> Iterator[Session]:
    """A separate, read-only session in which every statement sees the database at one instant.

    Under PostgreSQL's default READ COMMITTED each statement takes its own snapshot, so a read made
    of several statements can combine data from different moments. REPEATABLE READ fixes the
    snapshot at the transaction's first statement instead. Isolation can only be chosen before a
    transaction's first statement, so this opens its own connection from the caller's engine rather
    than altering the caller's transaction, which has usually already taken row locks.

    It sees committed data only, never anything the caller has written but not committed. It takes
    no locks and writes nothing, so it can neither block on the caller's row locks nor fail with a
    serialization error, and it is always rolled back.

    Cost: the caller's session already holds a pooled connection, so for the length of this read a
    caller uses two at once. The pool has to allow for that when many such reads run concurrently.
    """
    with db.get_bind().engine.connect() as connection:
        connection.execution_options(isolation_level="REPEATABLE READ")
        with Session(bind=connection) as read_db:
            read_db.execute(text("SET TRANSACTION READ ONLY"))
            yield read_db


def lock_commercial_offer_quote_document_row(db: Session, *, public_id: str) -> int | None:
    """Row-lock one quote document for the current transaction, exactly as
    lock_commercial_offer_row does for the parent offer.

    Approval reads quote_status_code (must be DRAFT) and superseded_at (must be NULL), then
    conditionally writes. Without this lock, two concurrent approve calls against the SAME
    version could both read DRAFT and both proceed - the second write would silently overwrite
    the first approver's identity/timestamp rather than being rejected, which is exactly the
    "asserted, not enforced" gate shape this slice's own decision 3 explicitly disclaims wanting
    to build. This is a distinct row from crm_commercial_offer, so lock_commercial_offer_row does
    not cover it; a separate lock is required, not a reuse.
    """
    row = db.execute(
        text(
            f"""
            SELECT id
            FROM {COMMERCIAL_OFFER_QUOTE_DOCUMENT_TABLE}
            WHERE quote_document_public_id = :public_id
            FOR UPDATE
            """
        ),
        {"public_id": public_id},
    ).first()
    return int(row[0]) if row is not None else None


def get_next_quote_document_version_no(db: Session, *, commercial_offer_id: int) -> int:
    value = db.execute(
        text(
            f"""
            SELECT COALESCE(MAX(version_no), 0) + 1
            FROM {COMMERCIAL_OFFER_QUOTE_DOCUMENT_TABLE}
            WHERE commercial_offer_id = :commercial_offer_id
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).scalar()
    return int(value or 1)


def supersede_earlier_quote_documents(db: Session, *, commercial_offer_id: int) -> None:
    """Marks every not-yet-superseded quote document for this offer as superseded, in the same
    transaction as the new version's insert.

    Deliberately does NOT touch quote_status_code, approved_by or approved_at: a superseded
    version that was approved for issue remains a true historical record of what was approved
    and, potentially, already sent to the customer. superseded_at is a separate fact from
    approval status, stored as a separate column for exactly that reason - see
    docs/agent/slices/slice-9e-quotation-generation.md, "Records"."""
    db.execute(
        text(
            f"""
            UPDATE {COMMERCIAL_OFFER_QUOTE_DOCUMENT_TABLE}
            SET superseded_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE commercial_offer_id = :commercial_offer_id
              AND superseded_at IS NULL
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    )


def insert_commercial_offer_quote_document(
    db: Session,
    *,
    public_id: str,
    commercial_offer_id: int,
    values: dict[str, Any],
) -> dict[str, Any]:
    db.execute(
        text(
            f"""
            INSERT INTO {COMMERCIAL_OFFER_QUOTE_DOCUMENT_TABLE} (
                quote_document_public_id,
                commercial_offer_id,
                version_no,
                quote_reference,
                document_public_id,
                source_fingerprint,
                quote_status_code,
                generated_by,
                generated_at,
                created_at,
                updated_at
            ) VALUES (
                :quote_document_public_id,
                :commercial_offer_id,
                :version_no,
                :quote_reference,
                :document_public_id,
                :source_fingerprint,
                :quote_status_code,
                :generated_by,
                :generated_at,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "quote_document_public_id": public_id,
            "commercial_offer_id": commercial_offer_id,
            **values,
        },
    )
    return get_quote_document_row_by_public_id(db, commercial_offer_id=commercial_offer_id, public_id=public_id)  # type: ignore[return-value]


def list_commercial_offer_quote_documents_for_offer(
    db: Session,
    *,
    commercial_offer_id: int,
) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {QUOTE_DOCUMENT_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_QUOTE_DOCUMENT_TABLE} qd
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = qd.commercial_offer_id
            {QUOTE_DOCUMENT_ACTOR_JOINS}
            WHERE qd.commercial_offer_id = :commercial_offer_id
            ORDER BY qd.version_no DESC
            """
        ),
        {"commercial_offer_id": commercial_offer_id},
    ).fetchall()
    return [_row_to_quote_document_dict(row) for row in rows]


def get_quote_document_row_by_public_id(
    db: Session,
    *,
    commercial_offer_id: int,
    public_id: str,
) -> dict[str, Any] | None:
    """Scoped to a specific commercial_offer_id, not merely a global lookup by public_id - a
    quote document from a different offer must never be approvable through this offer's route,
    even if the public_id were somehow guessed or supplied by mistake."""
    row = db.execute(
        text(
            f"""
            SELECT
                {QUOTE_DOCUMENT_SELECT_COLUMNS}
            FROM {COMMERCIAL_OFFER_QUOTE_DOCUMENT_TABLE} qd
            INNER JOIN {COMMERCIAL_OFFER_TABLE} co ON co.id = qd.commercial_offer_id
            {QUOTE_DOCUMENT_ACTOR_JOINS}
            WHERE qd.commercial_offer_id = :commercial_offer_id
              AND qd.quote_document_public_id = :public_id
            LIMIT 1
            """
        ),
        {"commercial_offer_id": commercial_offer_id, "public_id": public_id},
    ).first()
    return dict(_row_mapping(row)) if row else None


def mark_quote_document_approved_for_issue(
    db: Session,
    *,
    quote_document_public_id: str,
    approved_by: str | None,
    approval_note: str | None,
) -> None:
    """Writes quote_status_code/approved_by/approved_at together in one UPDATE, so the database
    CHECK constraint (ck_quote_document_approval_is_complete) is satisfied at every point a
    concurrent reader could observe the row - never a moment where status says APPROVED_FOR_ISSUE
    but approved_by/approved_at have not landed yet."""
    db.execute(
        text(
            f"""
            UPDATE {COMMERCIAL_OFFER_QUOTE_DOCUMENT_TABLE}
            SET quote_status_code = 'APPROVED_FOR_ISSUE',
                approved_by = :approved_by,
                approved_at = CURRENT_TIMESTAMP,
                approval_note = :approval_note,
                updated_at = CURRENT_TIMESTAMP
            WHERE quote_document_public_id = :quote_document_public_id
            """
        ),
        {
            "quote_document_public_id": quote_document_public_id,
            "approved_by": approved_by,
            "approval_note": approval_note,
        },
    )


def count_interactions_in_commercial_offer_chain(
    db: Session,
    *,
    commercial_offer_public_id: str,
    opportunity_public_id: str | None,
    account_public_id: str | None,
) -> int:
    """Read-only cross-module lookup (raw SQL against `interaction`, no import of the
    interactions module - the same pattern get_work_order_lineage_context already uses for
    crm_work_order) used only for the advisory INTERACTION_LOG submission-readiness row: has any
    conversation been logged against this offer, or its Opportunity, or its Account?

    linked_record_type values ('commercial_offer', 'opportunity', 'business_party') match
    Slice 9D's own contract (backend/app/modules/interactions/contract.py) exactly - 'business_party'
    is Slice 9D's canonical Account link type, not the legacy 'account' value some pre-9D
    document_metadata rows use.
    """
    linked_ids: list[tuple[str, str]] = [("commercial_offer", commercial_offer_public_id)]
    if opportunity_public_id:
        linked_ids.append(("opportunity", opportunity_public_id))
    if account_public_id:
        linked_ids.append(("business_party", account_public_id))

    conditions = " OR ".join(
        f"(linked_record_type = :type_{i} AND linked_record_public_id = :id_{i})"
        for i in range(len(linked_ids))
    )
    params: dict[str, Any] = {}
    for i, (record_type, record_public_id) in enumerate(linked_ids):
        params[f"type_{i}"] = record_type
        params[f"id_{i}"] = record_public_id

    value = db.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM interaction
            WHERE is_deleted IS FALSE
              AND ({conditions})
            """
        ),
        params,
    ).scalar()
    return int(value or 0)
