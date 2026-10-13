"""Resource Assignment request and response shapes (8A core).

Unknown request fields are refused with 422 throughout. docs/agent/contracts/resource-assignment-api-contract.md.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.resource_assignments.contract import (
    KIT_PIECES_PER_REQUEST,
    LARGEST_WHOLE_NUMBER,
    NOTES_MAX_LENGTH,
    REQUEST_KEY_MAX_LENGTH,
    TRIP_NOTE_MAX_LENGTH,
)

_WHOLE = {"le": LARGEST_WHOLE_NUMBER}


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Requests -----------------------------------------------------------------------------------------------


class AssignmentCreate(_Request):
    """Allocate a machine to one unit of a requirement. `planned_to` empty means until the requirement ends.
    `accept_warnings` says the user ticked "I have seen these warnings" (owner, Q2)."""

    create_request_key: str = Field(min_length=1, max_length=REQUEST_KEY_MAX_LENGTH)
    requirement_public_id: UUID
    unit_number: int = Field(ge=1, **_WHOLE)
    machine_public_id: UUID
    planned_from: date
    planned_to: date | None = None
    billing_cycle_code: str | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)
    accept_warnings: bool = False


class AssignmentReplace(_Request):
    """Replace the machine from a day. `planned_to` left out keeps the old allocation's end; sent empty, it is
    until the requirement ends. `billing_cycle_code` left out takes the old allocation's."""

    create_request_key: str = Field(min_length=1, max_length=REQUEST_KEY_MAX_LENGTH)
    expected_assignment_version: int = Field(ge=1, **_WHOLE)
    machine_public_id: UUID
    replace_from: date
    planned_to: date | None = None
    billing_cycle_code: str | None = Field(default=None, max_length=20)
    reason_code: str = Field(min_length=1, max_length=30)
    note: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)
    accept_warnings: bool = False


class AssignmentRelease(_Request):
    """Free the machine. `last_day` empty: it never goes to the job."""

    expected_assignment_version: int = Field(ge=1, **_WHOLE)
    last_day: date | None = None
    reason_code: str = Field(min_length=1, max_length=30)
    note: str | None = Field(default=None, max_length=NOTES_MAX_LENGTH)


class AssignmentDates(_Request):
    expected_assignment_version: int = Field(ge=1, **_WHOLE)
    planned_from: date
    planned_to: date | None = None
    accept_warnings: bool = False


class AssignmentVersion(_Request):
    expected_assignment_version: int = Field(ge=1, **_WHOLE)


class AssignmentBillingCycle(_Request):
    expected_assignment_version: int = Field(ge=1, **_WHOLE)
    # WEEKLY, MONTHLY, or empty: not stated yet.
    billing_cycle_code: str | None = Field(default=None, max_length=20)


class TripCreate(_Request):
    expected_assignment_version: int = Field(ge=1, **_WHOLE)
    goes_on: date
    note: str | None = Field(default=None, max_length=TRIP_NOTE_MAX_LENGTH)


class TripNote(_Request):
    """What a Trip (Own Load) carries - which part of the machine, in the planner's words (owner, 29 September 2026:
    a crane may go in several loads). Empty: not said."""

    expected_assignment_version: int = Field(ge=1, **_WHOLE)
    note: str | None = Field(default=None, max_length=TRIP_NOTE_MAX_LENGTH)


class KitPieceInput(_Request):
    piece_public_id: UUID
    # 1 for a piece tracked one by one; how many of a counted set go.
    quantity: int = Field(default=1, ge=1, **_WHOLE)


class KitAdd(_Request):
    create_request_key: str = Field(min_length=1, max_length=REQUEST_KEY_MAX_LENGTH)
    expected_assignment_version: int = Field(ge=1, **_WHOLE)
    trip_number: int = Field(ge=1, **_WHOLE)
    pieces: list[KitPieceInput] = Field(min_length=1, max_length=KIT_PIECES_PER_REQUEST)
    accept_warnings: bool = False


# --- Responses ----------------------------------------------------------------------------------------------


class CapabilityBrief(BaseModel):
    capability_code: str
    capability_label: str
    unit_symbol: str | None
    value: Decimal | None
    choice_value: str | None
    is_key: bool


class AssetBrief(BaseModel):
    """A machine or a piece of kit as it stands now."""

    asset_public_id: str
    asset_reference: str
    asset_kind_code: str
    # The registration of a machine; empty for a piece of kit.
    machine_number: str | None
    # A piece's own number - its mark (ERT-2, Q5).
    serial_number: str | None
    class_code: str
    class_label: str
    type_code: str | None
    type_label: str | None
    model_public_id: str | None
    model_label: str | None
    asset_status_code: str
    asset_version: int
    quantity: int
    tracking_code: str
    key_capability: CapabilityBrief | None
    capabilities: list[CapabilityBrief]
    flag_codes: list[str]


class AnswerResult(BaseModel):
    asset_public_id: str
    asset_reference: str
    kind_code: str | None
    kind_label: str | None
    outcome_code: str
    effect_code: str
    cover_ends_on: date | None


class Answer(BaseModel):
    """An eligibility answer: stored (with its decision's public id), or today's (worked out when read)."""

    decision_public_id: str | None
    overall_code: str
    valid_until: date | None
    evaluated_on: date
    site_state_code: str
    site_state_label: str
    central_government_site: bool
    period_from: date
    period_to: date | None
    results: list[AnswerResult]


class SiteFacts(BaseModel):
    """The requirement's line's site as the allocation judges it (design section 6.1)."""

    site_public_id: UUID | None
    site_label: str | None
    state_text: str | None
    state_code: str | None
    state_label: str | None
    central_government_site: bool | None
    problem_code: str | None
    problem_message: str | None


class RequirementBrief(BaseModel):
    requirement_public_id: UUID
    requirement_reference: str
    requirement_status_code: str
    requirement_version: int
    units_required: int
    units_covered: int
    units_remaining: int
    required_from: date
    required_to: date | None
    # Its own end, else the line's, else the contract's fixed end; empty when nothing bounds it.
    planned_end: date | None
    equipment_class_code: str
    equipment_class_label: str
    equipment_type_code: str | None
    equipment_type_label: str | None
    capabilities: list[dict[str, Any]]
    work_order_status_code: str


class AssignmentLink(BaseModel):
    assignment_public_id: str
    assignment_reference: str
    asset_reference: str
    machine_number: str | None
    planned_from: date
    effective_to: date | None


class Conflict(BaseModel):
    """Another allocation keeping the machine, the piece or the unit on some of the same days."""

    assignment_public_id: str
    assignment_reference: str
    work_order_code: str
    unit_number: int
    assignment_status_code: str
    busy_from: date
    busy_to: date | None


class KitLineResponse(BaseModel):
    kit_line_public_id: str
    trip_number: int
    piece: AssetBrief | None
    piece_public_id: str
    quantity: int
    line_status_code: str
    removed_by: UUID | None
    removed_by_display_name: str | None
    removed_at: datetime | None
    busy_from: date
    busy_to: date | None
    fits_machine: bool
    decision: Answer | None
    today: Answer | None


class TripResponse(BaseModel):
    trip_public_id: str
    trip_number: int
    # The day it goes: trip 1 goes with the machine, on the allocation's first day.
    goes_on: date
    note: str | None
    kit: list[KitLineResponse]


class AssignmentResponse(BaseModel):
    assignment_public_id: str
    assignment_reference: str
    assignment_status_code: str
    requirement: RequirementBrief
    unit_number: int
    work_order_public_id: UUID
    work_order_code: str
    work_order_line_public_id: UUID
    work_order_line_number: int
    source_offer_line_public_id: UUID | None
    machine: AssetBrief | None
    allocated_machine_number: str | None
    allocated_class_code: str
    allocated_type_code: str | None
    allocated_model_public_id: str | None
    allocated_asset_version: int
    planned_from: date
    planned_to: date | None
    ended_on: date | None
    # The last day it keeps the machine; empty when it runs on.
    effective_to: date | None
    billing_cycle_code: str | None
    billing_cycle_set_by: UUID | None
    billing_cycle_set_by_display_name: str | None
    billing_cycle_set_at: datetime | None
    decision: Answer | None
    today: Answer | None
    compliance_state_code: str | None
    warnings: list[str]
    site: SiteFacts
    replaces: AssignmentLink | None
    replaced_by: AssignmentLink | None
    end_reason_code: str | None
    end_note: str | None
    ended_by: UUID | None
    ended_by_display_name: str | None
    ended_at: datetime | None
    # Only on one allocation's page; empty in lists.
    trips: list[TripResponse]
    kit_pieces_listed: int
    notes: str | None
    assignment_version: int
    created_by: UUID | None
    created_by_display_name: str | None
    created_at: datetime
    updated_by: UUID | None
    updated_by_display_name: str | None
    updated_at: datetime


class AssignmentActionResponse(BaseModel):
    assignment: AssignmentResponse
    # On a replacement, the allocation it replaced, as it now stands.
    replaced: AssignmentResponse | None = None
    replayed: bool = False
    events: list[dict[str, Any]] = Field(default_factory=list)


class Candidate(BaseModel):
    machine: AssetBrief
    available: bool
    conflicts: list[Conflict]
    # Today's answer for the site and period; empty for a busy machine, or while the site cannot be judged.
    answer: Answer | None


class CandidatesResponse(BaseModel):
    requirement: RequirementBrief
    unit_number: int
    period_from: date
    period_to: date | None
    site: SiteFacts
    # Other allocations already filling this unit on some of these days: the unit cannot take another then.
    unit_conflicts: list[Conflict]
    candidates: list[Candidate]
    # Machines of the class not offered, by why: TYPE_UNKNOWN, RATING_UNKNOWN, BELOW_REQUIREMENT.
    left_out: dict[str, int]


class KitOption(BaseModel):
    piece: AssetBrief
    available: bool
    # For a counted set, how many of it are free over the trip's days; 1 or 0 for a piece tracked one by one.
    quantity_free: int
    conflicts: list[Conflict]
    answer: Answer | None


class KitOptionsResponse(BaseModel):
    assignment_public_id: str
    # The allocation's version the options were worked out for: the screen shows them only under that version
    # (independent review, 8A-FB2-003).
    assignment_version: int
    trip_number: int
    window_from: date
    window_to: date | None
    machine_has_model: bool
    pieces: list[KitOption]
