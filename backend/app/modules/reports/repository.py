from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.reports.contract import (
    COMMERCIAL_OFFER_ACCEPTED_STATUS,
    COMMERCIAL_OFFER_OPEN_EXCLUDED_STATUSES,
    OFFER_AGEING_BUCKETS,
)
from app.modules.commercial_offers.contract import COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES

# Amounts are never converted. Every SUM of an offer amount is grouped by the
# offer's currency, and the service reports each currency's total separately
# (owner's decision, 4 October 2026, TB1-600; the list is app/shared/currency.py).
# Opportunities carry no currency: their estimated value is in INR (Q-08, ADR-023).

COMMERCIAL_OFFER_AWAITING_RESPONSE_STATUS = "SUBMITTED"


def _rows(result: Any) -> list[Any]:
    return [row._mapping if hasattr(row, "_mapping") else row for row in result]


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def _status_placeholders(prefix: str, values: tuple[str, ...]) -> tuple[str, dict[str, str]]:
    """Build a bound IN-list.

    Values come from module contracts, never from user input, but are still
    bound rather than interpolated.
    """
    keys = [f"{prefix}{index}" for index in range(len(values))]
    placeholders = ", ".join(f":{key}" for key in keys)
    return placeholders, dict(zip(keys, values, strict=True))


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def fetch_leads_by_status(db: Session) -> list[dict[str, Any]]:
    result = db.execute(
        text(
            """
            SELECT lead_status_code AS status_code, COUNT(*) AS record_count
            FROM crm_lead
            GROUP BY lead_status_code
            ORDER BY lead_status_code
            """
        )
    )
    return [
        {"status_code": row["status_code"], "record_count": int(row["record_count"])}
        for row in _rows(result)
    ]


def fetch_opportunities_by_status(db: Session) -> list[dict[str, Any]]:
    result = db.execute(
        text(
            """
            SELECT
                opportunity_status_code AS status_code,
                COUNT(*) AS record_count,
                COALESCE(SUM(estimated_value), 0) AS total_value
            FROM crm_opportunity
            GROUP BY opportunity_status_code
            ORDER BY opportunity_status_code
            """
        )
    )
    return [
        {
            "status_code": row["status_code"],
            "record_count": int(row["record_count"]),
            "total_value": _decimal(row["total_value"]),
        }
        for row in _rows(result)
    ]


# ---------------------------------------------------------------------------
# Open offers
# ---------------------------------------------------------------------------
def fetch_open_offers_by_status(db: Session) -> list[dict[str, Any]]:
    placeholders, params = _status_placeholders("excl", COMMERCIAL_OFFER_OPEN_EXCLUDED_STATUSES)
    preparation_placeholders, preparation_params = _status_placeholders(
        "prep", COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES
    )
    result = db.execute(
        text(
            f"""
            SELECT
                offer_status_code AS status_code,
                currency_code,
                COUNT(*) AS record_count,
                COALESCE(SUM(offer_value), 0) AS total_value
            FROM crm_commercial_offer
            WHERE offer_status_code NOT IN ({placeholders})
              AND NOT (
                  previous_version_offer_id IS NOT NULL
                  AND offer_status_code IN ({preparation_placeholders})
              )
            GROUP BY offer_status_code, currency_code
            ORDER BY offer_status_code, currency_code
            """
        ),
        {**params, **preparation_params},
    )
    return [
        {
            "status_code": row["status_code"],
            "currency_code": row["currency_code"],
            "record_count": int(row["record_count"]),
            "total_value": _decimal(row["total_value"]),
        }
        for row in _rows(result)
    ]


def _ageing_select() -> tuple[str, dict[str, int]]:
    """Build the ageing FILTER fragments from the contract's bucket definition."""
    fragments: list[str] = []
    params: dict[str, int] = {}
    for index, (_label, low, high) in enumerate(OFFER_AGEING_BUCKETS):
        conditions: list[str] = []
        if low is not None:
            conditions.append(f"age_days >= :age_low_{index}")
            params[f"age_low_{index}"] = low
        if high is not None:
            conditions.append(f"age_days <= :age_high_{index}")
            params[f"age_high_{index}"] = high
        condition = " AND ".join(conditions) if conditions else "TRUE"
        fragments.append(f"COUNT(*) FILTER (WHERE {condition}) AS bucket_count_{index}")
        fragments.append(
            f"COALESCE(SUM(offer_value) FILTER (WHERE {condition}), 0) AS bucket_value_{index}"
        )
    return ",\n                ".join(fragments), params


def fetch_open_offer_ageing(db: Session) -> list[dict[str, Any]]:
    select_fragment, age_params = _ageing_select()
    placeholders, status_params = _status_placeholders(
        "excl", COMMERCIAL_OFFER_OPEN_EXCLUDED_STATUSES
    )
    preparation_placeholders, preparation_params = _status_placeholders(
        "prep", COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES
    )
    result = db.execute(
        text(
            f"""
            SELECT
                currency_code,
                {select_fragment}
            FROM (
                SELECT
                    currency_code,
                    offer_value,
                    (CURRENT_DATE - COALESCE(offer_date, created_at::date)) AS age_days
                FROM crm_commercial_offer
                WHERE offer_status_code NOT IN ({placeholders})
                  AND NOT (
                      previous_version_offer_id IS NOT NULL
                      AND offer_status_code IN ({preparation_placeholders})
                  )
            ) AS aged
            GROUP BY currency_code
            ORDER BY currency_code
            """
        ),
        {**age_params, **status_params, **preparation_params},
    )
    rows = _rows(result)
    return [
        {
            "label": label,
            "by_currency": [
                {
                    "currency_code": row["currency_code"],
                    "record_count": int(row[f"bucket_count_{index}"]),
                    "total_value": _decimal(row[f"bucket_value_{index}"]),
                }
                for row in rows
            ],
        }
        for index, (label, _low, _high) in enumerate(OFFER_AGEING_BUCKETS)
    ]


def fetch_open_offer_expiry(db: Session, horizon_days: int) -> dict[str, int]:
    placeholders, status_params = _status_placeholders(
        "excl", COMMERCIAL_OFFER_OPEN_EXCLUDED_STATUSES
    )
    preparation_placeholders, preparation_params = _status_placeholders(
        "prep", COMMERCIAL_OFFER_VERSION_PREPARATION_STATUSES
    )
    result = db.execute(
        text(
            f"""
            SELECT
                COUNT(*) FILTER (WHERE valid_until IS NULL) AS no_expiry_recorded,
                COUNT(*) FILTER (
                    WHERE valid_until IS NOT NULL AND valid_until < CURRENT_DATE
                ) AS already_expired,
                COUNT(*) FILTER (
                    WHERE valid_until IS NOT NULL
                      AND valid_until >= CURRENT_DATE
                      AND valid_until <= CURRENT_DATE + make_interval(days => :horizon_days)
                ) AS expiring_within_horizon,
                COUNT(*) FILTER (
                    WHERE offer_status_code = :awaiting_status
                ) AS awaiting_customer_response
            FROM crm_commercial_offer
            WHERE offer_status_code NOT IN ({placeholders})
              AND NOT (
                  previous_version_offer_id IS NOT NULL
                  AND offer_status_code IN ({preparation_placeholders})
              )
            """
        ),
        {
            **status_params,
            **preparation_params,
            "horizon_days": horizon_days,
            "awaiting_status": COMMERCIAL_OFFER_AWAITING_RESPONSE_STATUS,
        },
    )
    row = _rows(result)[0]
    return {key: int(row[key]) for key in row.keys()}


# ---------------------------------------------------------------------------
# Accepted offers
# ---------------------------------------------------------------------------
def fetch_accepted_offers_by_purpose(db: Session) -> list[dict[str, Any]]:
    result = db.execute(
        text(
            """
            SELECT
                o.offer_purpose,
                o.currency_code,
                COUNT(*) AS record_count,
                COALESCE(SUM(o.offer_value), 0) AS total_value,
                COUNT(*) FILTER (WHERE shells.shell_count > 0) AS with_work_order_shell,
                COUNT(*) FILTER (WHERE shells.shell_count = 0) AS awaiting_handoff,
                COALESCE(
                    SUM(o.offer_value) FILTER (WHERE shells.shell_count = 0), 0
                ) AS awaiting_handoff_value
            FROM crm_commercial_offer o
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS shell_count
                FROM crm_work_order w
                WHERE w.commercial_offer_id = o.id
            ) AS shells ON TRUE
            WHERE o.offer_status_code = :accepted_status
            GROUP BY o.offer_purpose, o.currency_code
            ORDER BY o.offer_purpose, o.currency_code
            """
        ),
        {"accepted_status": COMMERCIAL_OFFER_ACCEPTED_STATUS},
    )
    return [
        {
            "offer_purpose": row["offer_purpose"],
            "currency_code": row["currency_code"],
            "record_count": int(row["record_count"]),
            "total_value": _decimal(row["total_value"]),
            "with_work_order_shell": int(row["with_work_order_shell"]),
            "awaiting_handoff": int(row["awaiting_handoff"]),
            "awaiting_handoff_value": _decimal(row["awaiting_handoff_value"]),
        }
        for row in _rows(result)
    ]


# ---------------------------------------------------------------------------
# Work Order handoff
# ---------------------------------------------------------------------------
def fetch_work_orders_by_status(db: Session) -> list[dict[str, Any]]:
    result = db.execute(
        text(
            """
            SELECT work_order_status_code AS status_code, COUNT(*) AS record_count
            FROM crm_work_order
            GROUP BY work_order_status_code
            ORDER BY work_order_status_code
            """
        )
    )
    return [
        {"status_code": row["status_code"], "record_count": int(row["record_count"])}
        for row in _rows(result)
    ]


def fetch_handoff_source_values(db: Session) -> list[dict[str, Any]]:
    result = db.execute(
        text(
            """
            SELECT o.currency_code, COALESCE(SUM(o.offer_value), 0) AS total_value
            FROM crm_work_order w
            JOIN crm_commercial_offer o ON o.id = w.commercial_offer_id
            GROUP BY o.currency_code
            ORDER BY o.currency_code
            """
        )
    )
    return [
        {"currency_code": row["currency_code"], "total_value": _decimal(row["total_value"])}
        for row in _rows(result)
    ]


def fetch_recent_handoffs(db: Session, limit: int) -> list[dict[str, Any]]:
    result = db.execute(
        text(
            """
            SELECT
                w.work_order_public_id,
                w.work_order_code,
                w.work_order_status_code,
                w.customer_wo_reference,
                w.received_date,
                w.created_at,
                o.offer_public_id AS source_offer_public_id,
                o.offer_code AS source_offer_code,
                o.offer_value AS source_offer_value,
                o.currency_code AS source_offer_currency_code,
                bp.business_party_public_id AS account_public_id
            FROM crm_work_order w
            JOIN crm_commercial_offer o ON o.id = w.commercial_offer_id
            LEFT JOIN business_party bp ON bp.id = w.business_party_id
            ORDER BY w.created_at DESC, w.id DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [
        {
            "work_order_public_id": str(row["work_order_public_id"]),
            "work_order_code": row["work_order_code"],
            "work_order_status_code": row["work_order_status_code"],
            "customer_wo_reference": row["customer_wo_reference"],
            "received_date": row["received_date"],
            "created_at": row["created_at"],
            "source_offer_public_id": str(row["source_offer_public_id"]),
            "source_offer_code": row["source_offer_code"],
            "source_offer_value": (
                _decimal(row["source_offer_value"])
                if row["source_offer_value"] is not None
                else None
            ),
            "source_offer_currency_code": row["source_offer_currency_code"],
            "account_public_id": (
                str(row["account_public_id"]) if row["account_public_id"] is not None else None
            ),
        }
        for row in _rows(result)
    ]
