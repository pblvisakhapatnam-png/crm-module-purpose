"""Interaction request/response schemas (Slice 9D)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.interactions.contract import (
    INTERACTION_CHANNELS,
    INTERACTION_CONTRACT_VERSION,
    INTERACTION_DIRECTIONS,
    INTERACTION_EXTERNAL_SYSTEMS,
    INTERACTION_LINKED_RECORD_TYPES,
    INTERACTION_PARTICIPANT_ROLES,
)
from app.shared.zoned_datetime import ZonedDateTime


class InteractionParticipantCreate(BaseModel):
    # Same reasoning as InteractionUpdate: an unrecognised field is a caller mistake and must be
    # reported, not silently dropped. A participant whose address lands in a misspelled key would
    # otherwise be recorded as naming nobody.
    model_config = ConfigDict(extra="forbid")

    party_role_code: str = Field(max_length=20)
    contact_public_id: UUID | None = None
    app_user_public_id: UUID | None = None
    display_name: str | None = Field(default=None, max_length=255)
    address_or_number: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _must_identify_exactly_one_party(self) -> "InteractionParticipantCreate":
        """A participant must name somebody, and must not claim to be two people.

        **Must name someone.** At least one of the four identifying fields is required. Without
        this a caller can insert unlimited rows carrying only a role code, which pollutes the
        "every conversation involving this contact" query the child table exists to serve.

        **Must not be both.** `contact_public_id` and `app_user_public_id` may not both be
        supplied. They address different populations: `business_party_contact` is a person at
        the customer's Account, `app_user` is a PBL staff login. A participant is either the
        external party to the conversation or the internal one, never simultaneously both. If a
        row ever needs both, that is an identity-resolution ambiguity to be decided deliberately
        - two people on one conversation are two participant rows, which is exactly what the
        child table is for - not a dual identity to be silently stored.
        """
        if self.contact_public_id is not None and self.app_user_public_id is not None:
            raise ValueError(
                "a participant may carry contact_public_id or app_user_public_id, not both: an "
                "Account Contact and a PBL user are different people. Record two participants "
                "if the conversation involved both."
            )

        if not any(
            (
                self.contact_public_id,
                self.app_user_public_id,
                (self.display_name or "").strip(),
                (self.address_or_number or "").strip(),
            )
        ):
            raise ValueError(
                "a participant must carry at least one of contact_public_id, app_user_public_id, "
                "display_name or address_or_number."
            )
        return self


class InteractionParticipantResponse(BaseModel):
    public_id: UUID
    party_role_code: str
    contact_public_id: UUID | None = None
    app_user_public_id: UUID | None = None
    display_name: str | None = None
    # Redacted (set to None) alongside body_text when the caller lacks
    # INTERACTION_CONTENT_READ. See InteractionResponse.body_redacted.
    address_or_number: str | None = None


class InteractionCreate(BaseModel):
    # A create carrying an unrecognised field is refused rather than partially honoured. Silently
    # dropping it would mean a caller believes content was stored when it was not - and
    # body_stored would truthfully report false while nobody was looking.
    model_config = ConfigDict(extra="forbid")

    linked_record_type: str = Field(max_length=100)
    linked_record_public_id: UUID
    channel_code: str = Field(max_length=50)
    direction_code: str = Field(max_length=20)
    occurred_at: ZonedDateTime
    subject: str | None = Field(default=None, max_length=500)
    body_text: str | None = None
    external_system: str | None = Field(default=None, max_length=50)
    external_message_id: str | None = Field(default=None, max_length=255)
    idempotency_key: str | None = Field(default=None, max_length=255)
    external_reference_url: str | None = Field(default=None, max_length=1000)
    geo_latitude: Decimal | None = None
    geo_longitude: Decimal | None = None
    outcome: str | None = Field(default=None, max_length=255)
    next_follow_up_at: ZonedDateTime | None = None
    participants: list[InteractionParticipantCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> "InteractionCreate":
        if self.linked_record_type not in INTERACTION_LINKED_RECORD_TYPES:
            raise ValueError(
                f"linked_record_type must be one of {INTERACTION_LINKED_RECORD_TYPES}."
            )
        if self.channel_code not in INTERACTION_CHANNELS:
            raise ValueError(f"channel_code must be one of {INTERACTION_CHANNELS}.")
        if self.direction_code not in INTERACTION_DIRECTIONS:
            raise ValueError(f"direction_code must be one of {INTERACTION_DIRECTIONS}.")
        if self.external_system is not None and self.external_system not in INTERACTION_EXTERNAL_SYSTEMS:
            raise ValueError(f"external_system must be one of {INTERACTION_EXTERNAL_SYSTEMS}.")
        for participant in self.participants:
            if participant.party_role_code not in INTERACTION_PARTICIPANT_ROLES:
                raise ValueError(
                    f"participant party_role_code must be one of {INTERACTION_PARTICIPANT_ROLES}."
                )

        # Coordinates are stored as numeric(9,6). Out-of-range values would be silently
        # truncated or rejected by the database with an opaque error, and a lone latitude is not
        # a location - FRD line 177 asks for the coordinates of a visit, which needs both.
        if (self.geo_latitude is None) != (self.geo_longitude is None):
            raise ValueError(
                "geo_latitude and geo_longitude must be supplied together, or both omitted."
            )
        if self.geo_latitude is not None and not (Decimal("-90") <= self.geo_latitude <= Decimal("90")):
            raise ValueError("geo_latitude must be between -90 and 90.")
        if self.geo_longitude is not None and not (
            Decimal("-180") <= self.geo_longitude <= Decimal("180")
        ):
            raise ValueError("geo_longitude must be between -180 and 180.")

        return self


class InteractionUpdate(BaseModel):
    """Only the two fields Slice 9D allows to change after recording.

    See INTERACTION_MUTABLE_UPDATE_FIELDS in contract.py - body, subject, channel, direction,
    occurred_at, external_message_id and the participant set are immutable once recorded. A
    mistake is corrected by soft-deleting and re-recording, which leaves both rows and both
    events as evidence.

    `extra="forbid"` is what makes that immutability real rather than asserted. Pydantic's
    default is `extra="ignore"`, under which a PUT carrying `body_text` returned 200, silently
    discarded the attempted replacement, applied any other supplied field, and still emitted an
    InteractionUpdated event - a false audit record of a change that never happened. A caller
    attempting to edit an immutable field must be told no, not quietly ignored.
    """

    model_config = ConfigDict(extra="forbid")

    outcome: str | None = Field(default=None, max_length=255)
    next_follow_up_at: ZonedDateTime | None = None


class InteractionResponse(BaseModel):
    public_id: UUID
    linked_record_type: str
    linked_record_public_id: UUID
    channel_code: str
    direction_code: str
    occurred_at: datetime
    subject: str | None = None
    # Both fields below are redacted (forced to None, with body_redacted=True) when the
    # requesting caller lacks INTERACTION_CONTENT_READ. This happens in one shared serializer
    # function used by both the list and detail routes - see service._serialize_interaction -
    # so the redaction cannot be applied on one route and forgotten on the other.
    body_text: str | None = None
    body_redacted: bool = False
    body_stored: bool = False
    external_system: str | None = None
    external_message_id: str | None = None
    idempotency_key: str | None = None
    external_reference_url: str | None = None
    geo_latitude: Decimal | None = None
    geo_longitude: Decimal | None = None
    outcome: str | None = None
    next_follow_up_at: datetime | None = None
    recorded_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    participants: list[InteractionParticipantResponse] = Field(default_factory=list)
    # Present only when this row was returned through include_inherited=true and belongs to a
    # different record than the one queried (e.g. shown on an Opportunity but recorded against
    # its originating Lead). Never implies the message was addressed to the queried record.
    inherited_from: dict[str, str] | None = None


class InteractionCreatedResponse(BaseModel):
    interaction: InteractionResponse
    event: dict[str, Any]
    contract_version: str = INTERACTION_CONTRACT_VERSION
    correlation_id: str | None = None
    # True when this response replayed an existing record instead of creating one, because the
    # caller retried a command that had already succeeded. MCF-001 retry safety: the caller gets
    # the original record and can tell that it did.
    replayed: bool = False


class InteractionUpdatedResponse(BaseModel):
    interaction: InteractionResponse
    event: dict[str, Any]
    contract_version: str = INTERACTION_CONTRACT_VERSION
    correlation_id: str | None = None


class InteractionDeletedResponse(BaseModel):
    public_id: UUID
    event: dict[str, Any]
    contract_version: str = INTERACTION_CONTRACT_VERSION
    correlation_id: str | None = None
