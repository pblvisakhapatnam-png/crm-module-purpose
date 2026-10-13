from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CurrencyTotal(BaseModel):
    """One currency's own total. Amounts in different currencies are never converted or added together."""

    currency_code: str
    amount: Decimal


# Every list of totals below starts with INR, which is always present, even at zero. Another currency appears only
# when a record in that group is in it (owner's decision, 4 October 2026, TB1-600).


class StatusCount(BaseModel):
    """One status bucket. `totals` is omitted where the record type carries no amount."""

    status_code: str
    record_count: int
    totals: list[CurrencyTotal] | None = None


class LabelledCount(BaseModel):
    label: str
    record_count: int
    totals: list[CurrencyTotal] | None = None


class PipelineReport(BaseModel):
    generated_at: datetime
    lead_total: int
    leads_by_status: list[StatusCount]
    opportunity_total: int
    # Opportunities carry no currency: their estimated value is in INR.
    opportunity_totals: list[CurrencyTotal]
    opportunities_by_status: list[StatusCount]


class OpenOffersReport(BaseModel):
    generated_at: datetime
    open_offer_total: int
    open_offer_totals: list[CurrencyTotal]
    offers_by_status: list[StatusCount]
    ageing: list[LabelledCount]
    awaiting_customer_response: int
    expiry_horizon_days: int
    expiring_within_horizon: int
    already_expired: int
    # ADR-027: a controlled submitted offer with no expiry needs a review date.
    # Surfacing the count is reporting, not enforcement.
    no_expiry_recorded: int


class AcceptedOfferPurposeRow(BaseModel):
    offer_purpose: str
    record_count: int
    totals: list[CurrencyTotal]
    with_work_order_shell: int
    awaiting_handoff: int


class AcceptedOffersReport(BaseModel):
    generated_at: datetime
    accepted_total: int
    accepted_totals: list[CurrencyTotal]
    with_work_order_shell: int
    awaiting_handoff: int
    awaiting_handoff_totals: list[CurrencyTotal]
    by_purpose: list[AcceptedOfferPurposeRow]


class HandoffRow(BaseModel):
    work_order_public_id: str
    work_order_code: str
    work_order_status_code: str
    customer_wo_reference: str | None = None
    received_date: date | None = None
    created_at: datetime
    source_offer_public_id: str
    source_offer_code: str
    source_offer_value: Decimal | None = None
    source_offer_currency_code: str
    account_public_id: str | None = None


class WorkOrderHandoffReport(BaseModel):
    generated_at: datetime
    work_order_total: int
    work_orders_by_status: list[StatusCount]
    source_offer_totals: list[CurrencyTotal]
    recent_limit: int = Field(..., ge=1)
    recent: list[HandoffRow]
