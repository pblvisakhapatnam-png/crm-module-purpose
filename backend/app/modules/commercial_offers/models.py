
from __future__ import annotations

from datetime import datetime

from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Unicode, UnicodeText
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base
from app.modules.commercial_offers.contract import (
    COMMERCIAL_OFFER_CREDIT_REVIEW_TABLE,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_TABLE,
    COMMERCIAL_OFFER_QUOTE_DOCUMENT_TABLE,
    COMMERCIAL_OFFER_REVISION_TABLE,
    COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_TABLE,
    COMMERCIAL_OFFER_TC_CLAUSE_TABLE,
)


class CommercialOfferCustomerResponse(Base):
    __tablename__ = COMMERCIAL_OFFER_CUSTOMER_RESPONSE_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    commercial_offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    response_outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    response_reference: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    response_received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    response_channel: Mapped[str] = mapped_column(String(50), nullable=False)
    received_from: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    awarded_amount_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    awarded_currency_snapshot: Mapped[str | None] = mapped_column(String(3), nullable=True)
    awarded_version_snapshot: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    customer_po_or_wo_reference: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    customer_response_notes: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    linked_submission_evidence_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    linked_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class CommercialOfferTcClauseAttachment(Base):
    __tablename__ = COMMERCIAL_OFFER_TC_CLAUSE_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    commercial_offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tc_clause_id: Mapped[int] = mapped_column(Integer, nullable=False)
    clause_id_snapshot: Mapped[str] = mapped_column(Unicode(50), nullable=False)
    title_snapshot: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    clause_text_snapshot: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    business_line_snapshot: Mapped[str] = mapped_column(String(50), nullable=False)
    clause_category_snapshot: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    source_clause_number_snapshot: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    source_reference_snapshot: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    mandatory_default_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    risk_category_snapshot: Mapped[str | None] = mapped_column(Unicode(100), nullable=True)
    applies_to_header_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    applies_to_line_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_approval_if_omitted_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_approval_if_modified_snapshot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attached_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class CommercialOfferSubmissionEvidence(Base):
    __tablename__ = COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    commercial_offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    submission_reference: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    submission_channel: Mapped[str] = mapped_column(String(50), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    submitted_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recipient_summary: Mapped[str | None] = mapped_column(Unicode(1000), nullable=True)
    submitted_amount_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    submitted_currency_snapshot: Mapped[str | None] = mapped_column(String(3), nullable=True)
    submitted_version_snapshot: Mapped[str | None] = mapped_column(Unicode(50), nullable=True)
    document_reference_label: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    document_reference_url_or_path: Mapped[str | None] = mapped_column(Unicode(1000), nullable=True)
    evidence_notes: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class CommercialOfferCreditReview(Base):
    __tablename__ = COMMERCIAL_OFFER_CREDIT_REVIEW_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    commercial_offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    review_status: Mapped[str] = mapped_column(String(50), nullable=False)
    review_basis: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    review_reference: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_amount_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    credit_days_snapshot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exposure_note: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class CommercialOfferQuoteDocument(Base):
    """Slice 9E. The bytes live in document_metadata (Slice 9C storage abstraction); this table
    holds only what is quote-specific - version, status, the approval-gate facts and the
    source-data fingerprint used to detect staleness. See
    docs/agent/slices/slice-9e-quotation-generation.md, "Records"."""

    __tablename__ = COMMERCIAL_OFFER_QUOTE_DOCUMENT_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_document_public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    commercial_offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    quote_reference: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    document_public_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    quote_status_code: Mapped[str] = mapped_column(String(50), nullable=False)
    generated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approval_note: Mapped[str | None] = mapped_column(Unicode(1000), nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class CommercialOfferRevision(Base):
    __tablename__ = COMMERCIAL_OFFER_REVISION_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    commercial_offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_label: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    revision_reason: Mapped[str] = mapped_column(String(50), nullable=False)
    revision_notes: Mapped[str | None] = mapped_column(UnicodeText, nullable=True)
    revision_status: Mapped[str] = mapped_column(String(50), nullable=False)
    source_submission_evidence_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resubmission_evidence_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    opened_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resubmitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
