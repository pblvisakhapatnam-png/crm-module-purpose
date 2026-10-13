"""Eligibility request and response shapes (ELG-1).

docs/agent/contracts/eligibility-api-contract.md states what each route accepts, returns and refuses. Unknown
request fields are refused with 422. A certificate's number is `null`, with `number_withheld: true`, for a
caller without EQUIPMENT_IDENTITY_READ (owner, 27 September 2026, Q6).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.eligibility.contract import (
    ISSUED_BY_MAX_LENGTH,
    MAX_BANDS,
    MAX_SEEN_AT_ONCE,
    MAX_STEPS,
    REMINDER_KEY_MAX_LENGTH,
    MAX_NOT_APPLICABLE_MONTHS,
    MAX_RENEW_EVERY_MONTHS,
    NUMBER_MAX_LENGTH,
    REASON_MAX_LENGTH,
    REQUEST_KEY_MAX_LENGTH,
    SOURCE_MAX_LENGTH,
)


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Reference lists ------------------------------------------------------------------------------------


class JurisdictionResponse(BaseModel):
    jurisdiction_code: str
    jurisdiction_label: str
    jurisdiction_kind_code: str
    gst_state_code: str | None


class CertificateKindResponse(BaseModel):
    kind_code: str
    kind_label: str
    end_date_optional: bool
    valid_in_required: bool
    is_examination: bool
    states_registration: bool


# --- Assets, as Eligibility shows them -------------------------------------------------------------------


class AssetSummary(BaseModel):
    asset_public_id: str
    asset_reference: str
    asset_kind_code: str
    origin_code: str
    class_code: str
    class_label: str
    type_code: str | None
    type_label: str | None
    machine_number: str | None
    # A piece of kit's own number - its mark, or "stencil EQ-000512 on it" where it has none (ERT-2, Q5).
    serial_number: str | None
    asset_status_code: str


# --- Certificates and marks ------------------------------------------------------------------------------


class CertificateInput(_Request):
    create_request_key: str = Field(min_length=1, max_length=REQUEST_KEY_MAX_LENGTH)
    kind_code: str = Field(min_length=1, max_length=30)
    number: str = Field(max_length=NUMBER_MAX_LENGTH)
    issued_by: str = Field(max_length=ISSUED_BY_MAX_LENGTH)
    issued_on: date
    valid_from: date
    valid_until: date | None = None
    valid_in_code: str | None = Field(default=None, max_length=10)
    registered_as_code: str | None = Field(default=None, max_length=20)


class WithdrawInput(_Request):
    reason: str = Field(max_length=REASON_MAX_LENGTH)


class NotApplicableInput(_Request):
    create_request_key: str = Field(min_length=1, max_length=REQUEST_KEY_MAX_LENGTH)
    kind_code: str = Field(min_length=1, max_length=30)
    reason: str = Field(max_length=REASON_MAX_LENGTH)
    until: date | None = None


class CertificateResponse(BaseModel):
    certificate_public_id: str
    # The asset it is recorded on - on a crane's page, its carrier's certificates carry the carrier's.
    asset_public_id: str
    asset_reference: str
    kind_code: str
    kind_label: str
    number: str | None
    number_withheld: bool
    issued_by: str
    issued_on: date
    valid_from: date
    valid_until: date | None
    valid_in_code: str | None
    valid_in_label: str | None
    registered_as_code: str | None
    certificate_status_code: str
    # Whether its copy is attached: shown to everyone; the copy itself only with EQUIPMENT_IDENTITY_READ.
    has_copy: bool
    # The certificate in force today for its asset and kind (and place, for a permit).
    in_force: bool
    recorded_by_display_name: str | None
    recorded_at: datetime
    # Withheld with the number: the Fleet Admin may well repeat the number in it.
    withdrawn_reason: str | None
    withdrawn_by_display_name: str | None
    withdrawn_at: datetime | None


class MarkResponse(BaseModel):
    mark_public_id: str
    asset_public_id: str
    asset_reference: str
    kind_code: str
    kind_label: str
    # Withheld (None) without EQUIPMENT_IDENTITY_READ, as the withdrawal reason: free text may repeat a number.
    reason: str | None
    reason_withheld: bool
    until_date: date | None
    recorded_on: date
    mark_status_code: str
    allowed_by_rule_public_id: str
    recorded_by_display_name: str | None
    recorded_at: datetime
    withdrawn_reason: str | None
    withdrawn_by_display_name: str | None
    withdrawn_at: datetime | None


class RuleSummary(BaseModel):
    rule_public_id: str
    jurisdiction_code: str | None
    basis_code: str
    lapse_code: str
    renew_every_months: int | None
    not_applicable_code: str
    not_applicable_max_months: int | None
    source: str
    note: str | None


class KindStatus(BaseModel):
    """One kind of certificate on an asset's page: required of it today by the baseline, or recorded on it."""

    kind_code: str
    kind_label: str
    required: bool
    rule: RuleSummary | None
    # VALID, RUNS_OUT_SOON, RUN_OUT, MISSING, COPY_MISSING or NOT_APPLICABLE; None where not required.
    outcome_code: str | None
    cover_ends_on: date | None
    certificate: CertificateResponse | None
    mark: MarkResponse | None


class MarkableKind(BaseModel):
    """A kind the Fleet Admin may mark "not applicable" for this asset today, under the rule that allows it."""

    kind_code: str
    kind_label: str
    rule: RuleSummary
    # The latest end a mark recorded today may have; None where the rule sets no limit.
    latest_until: date | None


class AssetCertificatesResponse(BaseModel):
    asset: AssetSummary
    # A fitted part is checked with the machine it is fitted to.
    fitted_to: AssetSummary | None
    fitted_parts: list[AssetSummary]
    numbers_withheld: bool
    statuses: list[KindStatus]
    # Every certificate on the asset and its fitted parts, in force, earlier and withdrawn; newest first.
    certificates: list[CertificateResponse]
    marks: list[MarkResponse]
    recordable_kind_codes: list[str]
    markable_kinds: list[MarkableKind]


class CertificateActionResponse(BaseModel):
    certificates: AssetCertificatesResponse
    certificate_public_id: str | None = None
    mark_public_id: str | None = None
    replayed: bool = False
    # None when nothing was recorded: a repeated request, or a withdrawal already made.
    event: dict[str, Any] | None = None


# --- The check (section 6) ------------------------------------------------------------------------------


class CheckResult(BaseModel):
    asset_public_id: str
    asset_reference: str
    # None for the asset's own check (retired).
    kind_code: str | None
    kind_label: str | None
    outcome_code: str
    effect_code: str
    lapse_code: str | None
    basis_code: str | None
    rule_public_id: str | None
    # Where the rule came from; None for the baseline.
    rule_jurisdiction_code: str | None
    certificate_public_id: str | None
    certificate_asset_reference: str | None
    mark_public_id: str | None
    cover_ends_on: date | None


class EligibilityCheckResponse(BaseModel):
    asset: AssetSummary
    site_state_code: str
    site_state_label: str
    central_government_site: bool
    period_from: date
    period_to: date | None
    evaluated_on: date
    overall_code: str
    valid_until: date | None
    outcome_counts: dict[str, int]
    results: list[CheckResult]


class StoredResult(BaseModel):
    """One result of a stored decision (8A core): which asset, which certificate kind, and what was found."""

    asset_public_id: str
    asset_reference: str
    kind_code: str | None
    kind_label: str | None
    outcome_code: str
    effect_code: str
    cover_ends_on: date | None


class StoredDecision(BaseModel):
    """A decision `record_decision` stored, read back for the allocation it was made for (8A core)."""

    decision_public_id: str
    asset_public_id: str
    site_state_code: str
    site_state_label: str
    central_government_site: bool
    period_from: date
    period_to: date | None
    evaluated_on: date
    evaluated_at: datetime
    overall_code: str
    valid_until: date | None
    results: list[StoredResult]


# --- Certificates due (section 7) ------------------------------------------------------------------------


class DueItem(BaseModel):
    asset: AssetSummary
    kind_code: str
    kind_label: str
    band_code: str
    outcome_code: str
    cover_ends_on: date | None
    certificate_public_id: str | None
    # Where the certificate is recorded, when on a part fitted to the asset.
    certificate_asset_reference: str | None
    mark_public_id: str | None


class CertificatesDueResponse(BaseModel):
    today: date
    band_counts: dict[str, int]
    total: int
    limit: int
    offset: int
    items: list[DueItem]


# --- Rules (Q7) ---------------------------------------------------------------------------------------------


class RuleInput(_Request):
    create_request_key: str = Field(min_length=1, max_length=REQUEST_KEY_MAX_LENGTH)
    kind_code: str = Field(min_length=1, max_length=30)
    class_code: str = Field(min_length=1, max_length=50)
    type_code: str | None = Field(default=None, max_length=50)
    applies_when_code: str = Field(min_length=1, max_length=20)
    # None: the baseline, for all of India.
    jurisdiction_code: str | None = Field(default=None, max_length=10)
    effective_from: date
    renew_every_months: int | None = Field(default=None, ge=1, le=MAX_RENEW_EVERY_MONTHS)
    basis_code: str = Field(min_length=1, max_length=20)
    lapse_code: str = Field(min_length=1, max_length=20)
    not_applicable_code: str = Field(min_length=1, max_length=20)
    not_applicable_max_months: int | None = Field(default=None, ge=1, le=MAX_NOT_APPLICABLE_MONTHS)
    source: str = Field(max_length=SOURCE_MAX_LENGTH)
    note: str | None = Field(default=None, max_length=SOURCE_MAX_LENGTH)


class RuleEndInput(_Request):
    # The last day it is in effect.
    effective_to: date
    reason: str = Field(max_length=REASON_MAX_LENGTH)


class RuleResponse(BaseModel):
    rule_public_id: str
    kind_code: str
    kind_label: str
    class_code: str
    class_label: str
    type_code: str | None
    type_label: str | None
    applies_when_code: str
    jurisdiction_code: str | None
    jurisdiction_label: str | None
    effective_from: date
    effective_to: date | None
    renew_every_months: int | None
    basis_code: str
    lapse_code: str
    not_applicable_code: str
    not_applicable_max_months: int | None
    source: str
    note: str | None
    # IN_EFFECT, NOT_YET or ENDED, today (Asia/Kolkata).
    state_code: str
    recorded_by_display_name: str | None
    recorded_at: datetime
    ended_by_display_name: str | None
    ended_at: datetime | None
    end_reason: str | None


class RuleActionResponse(BaseModel):
    rule: RuleResponse
    replayed: bool = False
    event: dict[str, Any] | None = None


# --- Reminders and escalation (ELG-2) ---------------------------------------------------------------------


class AlertReached(BaseModel):
    step_number: int
    role_code: str
    role_label: str
    reached_on: date


class AlertSeenBy(BaseModel):
    display_name: str
    seen_at: datetime


class AlertAllocation(BaseModel):
    """The allocation an allocation reminder is about: the machine held on it, or a piece of kit on one of its trips."""

    assignment_public_id: str
    assignment_reference: str
    work_order_public_id: str
    work_order_code: str
    work_order_line_number: int
    unit_number: int
    trip_number: int | None
    kit_line_public_id: str | None
    site_label: str | None
    site_state_code: str
    site_state_label: str
    central_government_site: bool
    period_from: date
    period_to: date | None


class AlertItem(BaseModel):
    reminder_key: str
    reminder_kind_code: str
    reminder_kind_label: str
    # The machine the reminder is about; null for PBL's holiday calendar not set up, which is about a year (HOL-1).
    asset: AssetSummary | None
    # Where a crane's paper is recorded on its fitted carrier, the carrier's reference; otherwise null.
    certificate_asset_reference: str | None
    kind_code: str
    kind_label: str
    outcome_code: str
    # The date the reminder is about, and why (design section 5.2).
    date_on: date
    reason_code: str
    mark_public_id: str | None
    allocation: AlertAllocation | None
    # The year a calendar reminder is about (HOL-1); null for every certificate reminder.
    calendar_year: int | None = None
    began_on: date
    first_reminder_on: date
    reminder_on: date
    reminders_so_far: int
    reached: list[AlertReached]
    seen_by_me: bool
    seen_by: list[AlertSeenBy]


class AlertCounts(BaseModel):
    total: int
    unseen: int
    by_kind: dict[str, int]


class AlertsResponse(BaseModel):
    today: date
    counts: AlertCounts
    total: int
    limit: int
    offset: int
    items: list[AlertItem]


class AlertCountResponse(BaseModel):
    unseen: int
    total: int


class SeenItem(_Request):
    reminder_key: str = Field(min_length=1, max_length=REMINDER_KEY_MAX_LENGTH)
    reminder_on: date


class SeenInput(_Request):
    # An empty list is refused by the service, in words; more than the page can show by the schema.
    items: list[SeenItem] = Field(max_length=MAX_SEEN_AT_ONCE)


class SeenResponse(BaseModel):
    marked: int
    already: int


class AlertBand(_Request):
    from_days_before: int
    every_days: int


class AlertStep(_Request):
    role_code: str = Field(min_length=1, max_length=50)
    starts_code: str = Field(min_length=1, max_length=20)
    from_days_before: int | None = None
    channel_codes: list[str] = Field(default_factory=lambda: ["SCREEN"], max_length=5)


class AlertStepResponse(BaseModel):
    step_number: int
    role_code: str
    role_label: str
    starts_code: str
    from_days_before: int | None
    channel_codes: list[str]


class AlertSettingVersion(BaseModel):
    setting_public_id: str
    reminder_kind_code: str
    version_number: int
    saved_by: str | None
    saved_by_display_name: str | None
    saved_at: datetime
    bands: list[AlertBand]
    steps: list[AlertStepResponse]


class AlertSettingResponse(BaseModel):
    reminder_kind_code: str
    reminder_kind_label: str
    current: AlertSettingVersion
    # Earlier versions, newest first.
    earlier: list[AlertSettingVersion]


class AlertRole(BaseModel):
    role_code: str
    role_label: str


class AlertSettingsResponse(BaseModel):
    settings: list[AlertSettingResponse]
    # The roles a step may name: the active ones.
    roles: list[AlertRole]
    channel_codes: list[str]


class AlertSettingInput(_Request):
    expected_version: int = Field(ge=1)
    # How many bands and steps a setting may have is the service's to refuse, in words (design section 5.6); the
    # schema only bounds a request far beyond it.
    bands: list[AlertBand] = Field(max_length=MAX_BANDS * 5)
    steps: list[AlertStep] = Field(max_length=MAX_STEPS * 5)


class AlertSettingActionResponse(BaseModel):
    setting: AlertSettingResponse
    unchanged: bool
    event: dict[str, Any] | None = None
