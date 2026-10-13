from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.modules.reports import repository
from app.modules.reports.contract import OFFER_EXPIRY_HORIZON_DAYS
from app.modules.reports.schemas import (
    AcceptedOfferPurposeRow,
    AcceptedOffersReport,
    CurrencyTotal,
    HandoffRow,
    LabelledCount,
    OpenOffersReport,
    PipelineReport,
    StatusCount,
    WorkOrderHandoffReport,
)
from app.shared.currency import DEFAULT_CURRENCY, OPERATING_CURRENCIES


def _now() -> datetime:
    """Reports are generated in UTC. The UI converts to Asia/Kolkata for display."""
    return datetime.now(timezone.utc)


def _currency_order(currency_code: str) -> tuple[int, str]:
    """INR first, then the rest of the list in its order; a code not on the list (an older record) last."""
    if currency_code in OPERATING_CURRENCIES:
        return OPERATING_CURRENCIES.index(currency_code), currency_code
    return len(OPERATING_CURRENCIES), currency_code


def _currency_totals(amounts: Iterable[tuple[str, Decimal]]) -> list[CurrencyTotal]:
    """Each currency's own total; nothing is converted or added across currencies.

    INR is always present. Another currency appears only when the caller passes an amount in it, which callers do
    only for a group holding at least one record in that currency.
    """
    totals: dict[str, Decimal] = {DEFAULT_CURRENCY: Decimal("0")}
    for currency_code, amount in amounts:
        totals[currency_code] = totals.get(currency_code, Decimal("0")) + amount
    return [
        CurrencyTotal(currency_code=code, amount=totals[code])
        for code in sorted(totals, key=_currency_order)
    ]


def _group_by(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    """Rows sharing one value of `key` (one row per currency), in the order the query returned them."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row[key], []).append(row)
    return groups


def build_pipeline_report(db: Session) -> PipelineReport:
    leads = repository.fetch_leads_by_status(db)
    opportunities = repository.fetch_opportunities_by_status(db)

    return PipelineReport(
        generated_at=_now(),
        lead_total=sum(row["record_count"] for row in leads),
        leads_by_status=[
            StatusCount(status_code=row["status_code"], record_count=row["record_count"])
            for row in leads
        ],
        opportunity_total=sum(row["record_count"] for row in opportunities),
        opportunity_totals=_currency_totals(
            (DEFAULT_CURRENCY, row["total_value"]) for row in opportunities
        ),
        opportunities_by_status=[
            StatusCount(
                status_code=row["status_code"],
                record_count=row["record_count"],
                totals=_currency_totals([(DEFAULT_CURRENCY, row["total_value"])]),
            )
            for row in opportunities
        ],
    )


def build_open_offers_report(db: Session) -> OpenOffersReport:
    by_status = repository.fetch_open_offers_by_status(db)
    ageing = repository.fetch_open_offer_ageing(db)
    expiry = repository.fetch_open_offer_expiry(db, OFFER_EXPIRY_HORIZON_DAYS)

    return OpenOffersReport(
        generated_at=_now(),
        open_offer_total=sum(row["record_count"] for row in by_status),
        open_offer_totals=_currency_totals(
            (row["currency_code"], row["total_value"]) for row in by_status
        ),
        offers_by_status=[
            StatusCount(
                status_code=status_code,
                record_count=sum(row["record_count"] for row in rows),
                totals=_currency_totals((row["currency_code"], row["total_value"]) for row in rows),
            )
            for status_code, rows in _group_by(by_status, "status_code").items()
        ],
        ageing=[
            LabelledCount(
                label=bucket["label"],
                record_count=sum(row["record_count"] for row in bucket["by_currency"]),
                totals=_currency_totals(
                    (row["currency_code"], row["total_value"])
                    for row in bucket["by_currency"]
                    if row["record_count"] > 0
                ),
            )
            for bucket in ageing
        ],
        awaiting_customer_response=expiry["awaiting_customer_response"],
        expiry_horizon_days=OFFER_EXPIRY_HORIZON_DAYS,
        expiring_within_horizon=expiry["expiring_within_horizon"],
        already_expired=expiry["already_expired"],
        no_expiry_recorded=expiry["no_expiry_recorded"],
    )


def build_accepted_offers_report(db: Session) -> AcceptedOffersReport:
    by_purpose = repository.fetch_accepted_offers_by_purpose(db)

    return AcceptedOffersReport(
        generated_at=_now(),
        accepted_total=sum(row["record_count"] for row in by_purpose),
        accepted_totals=_currency_totals(
            (row["currency_code"], row["total_value"]) for row in by_purpose
        ),
        with_work_order_shell=sum(row["with_work_order_shell"] for row in by_purpose),
        awaiting_handoff=sum(row["awaiting_handoff"] for row in by_purpose),
        awaiting_handoff_totals=_currency_totals(
            (row["currency_code"], row["awaiting_handoff_value"])
            for row in by_purpose
            if row["awaiting_handoff"] > 0
        ),
        by_purpose=[
            AcceptedOfferPurposeRow(
                offer_purpose=offer_purpose,
                record_count=sum(row["record_count"] for row in rows),
                totals=_currency_totals((row["currency_code"], row["total_value"]) for row in rows),
                with_work_order_shell=sum(row["with_work_order_shell"] for row in rows),
                awaiting_handoff=sum(row["awaiting_handoff"] for row in rows),
            )
            for offer_purpose, rows in _group_by(by_purpose, "offer_purpose").items()
        ],
    )


def build_work_order_handoff_report(db: Session, limit: int) -> WorkOrderHandoffReport:
    by_status = repository.fetch_work_orders_by_status(db)
    recent = repository.fetch_recent_handoffs(db, limit)

    return WorkOrderHandoffReport(
        generated_at=_now(),
        work_order_total=sum(row["record_count"] for row in by_status),
        work_orders_by_status=[
            StatusCount(status_code=row["status_code"], record_count=row["record_count"])
            for row in by_status
        ],
        source_offer_totals=_currency_totals(
            (row["currency_code"], row["total_value"])
            for row in repository.fetch_handoff_source_values(db)
        ),
        recent_limit=limit,
        recent=[HandoffRow(**row) for row in recent],
    )
