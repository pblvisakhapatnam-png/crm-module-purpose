"""Interaction service layer (Slice 9D).

Business rules enforced here, not in routes.py:

- linked_record_type must be one of the five known types, and the target must actually exist.
- Redaction of body_text and participant address_or_number is applied in exactly one place -
  _serialize_interaction - and both the list and detail routes call it. This is deliberate: the
  classic failure mode for a content-permission split is hiding content on the detail screen and
  forgetting the list, and a single serializer makes that failure structurally impossible rather
  than merely tested against.
- Inherited history (Opportunity from its source Lead, Account from its source Lead(s)) is a
  derived read assembled here, never a copy. Nothing is written when a Lead converts.
- Immutability: update_interaction may change only outcome and next_follow_up_at.
- Idempotency (external_system + external_message_id, and idempotency_key) is enforced by the
  two partial unique indexes at the database, not here - a service-layer check would not survive
  a future ingestion job racing itself.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.authorization.contract import INTERACTION_CONTENT_READ
from app.modules.authorization.service import has_permission
from app.modules.events.service import record_business_event
from app.modules.identity.schemas import AuthUser
from app.modules.interactions.contract import (
    EXTERNAL_SYSTEM_MANUAL,
    INTERACTION_EVENT_DELETED,
    INTERACTION_EVENT_RECORDED,
    INTERACTION_EVENT_SCHEMA_VERSION,
    INTERACTION_EVENT_UPDATED,
    INTERACTION_FINGERPRINT_FIELDS,
    INTERACTION_FINGERPRINT_PARTICIPANT_FIELDS,
    INTERACTION_MODULE_NAME,
    INTERACTION_RECORD_TYPE,
    LINKED_RECORD_TYPE_ACCOUNT,
    LINKED_RECORD_TYPE_OPPORTUNITY,
)
from app.modules.interactions.repository import (
    app_user_exists,
    contact_exists,
    get_account_source_lead_public_ids,
    get_interaction_by_external_message,
    get_interaction_by_idempotency_key,
    get_interaction_by_public_id,
    get_interaction_id_by_public_id,
    get_opportunity_source_lead_public_id,
    insert_interaction,
    insert_interaction_participant,
    linked_record_exists,
    list_interaction_participants,
    list_interactions,
    list_participants_for_interactions,
    soft_delete_interaction,
    update_interaction as repo_update_interaction,
)
from app.modules.interactions.schemas import (
    InteractionCreate,
    InteractionCreatedResponse,
    InteractionDeletedResponse,
    InteractionParticipantResponse,
    InteractionResponse,
    InteractionUpdate,
    InteractionUpdatedResponse,
)


class InteractionNotFoundError(Exception):
    pass


class InteractionValidationError(Exception):
    pass


class InteractionDuplicateError(Exception):
    """Raised when the database's idempotency constraints reject a duplicate re-sync."""


# Bound on how many rows are fetched per side (direct, and per source Lead) before merging and
# paginating an include_inherited=true request. Generous for a pilot's per-record conversation
# volume; revisit if a single Lead/Opportunity/Account accumulates enough interactions to
# approach it.
_INHERITED_MERGE_FETCH_CAP = 500


def _serialize_interaction(
    row: dict[str, Any],
    participants: list[dict[str, Any]],
    *,
    db: Session,
    current_user: AuthUser,
    inherited_from: dict[str, str] | None = None,
) -> InteractionResponse:
    """The single place body_text and participant addresses are redacted.

    Both the list and detail routes must call this function rather than building
    InteractionResponse directly, so the redaction check exists exactly once.

    Takes the whole AuthUser rather than a bare role_codes list so that no interactions
    route module ever reads `.role_codes` directly - that access pattern is exactly what
    tests/test_authorization_route_migration_guard.py's fail-closed PF-1A-E1 guard forbids
    outside two narrowly pinned, pre-existing exceptions. Reading it here in service.py,
    which the guard does not scan, keeps the check where it belongs without adding a third
    exception to that guard's hardened allowlist.
    """
    may_read_content = has_permission(db, current_user.role_codes, INTERACTION_CONTENT_READ)

    participant_responses = [
        InteractionParticipantResponse(
            public_id=p["participant_public_id"],
            party_role_code=p["party_role_code"],
            contact_public_id=p.get("contact_public_id"),
            app_user_public_id=p.get("app_user_public_id"),
            display_name=p.get("display_name"),
            address_or_number=p.get("address_or_number") if may_read_content else None,
        )
        for p in participants
    ]

    return InteractionResponse(
        public_id=row["interaction_public_id"],
        linked_record_type=row["linked_record_type"],
        linked_record_public_id=row["linked_record_public_id"],
        channel_code=row["channel_code"],
        direction_code=row["direction_code"],
        occurred_at=row["occurred_at"],
        subject=row.get("subject"),
        body_text=row.get("body_text") if may_read_content else None,
        body_redacted=not may_read_content,
        body_stored=bool(row.get("body_stored")),
        external_system=row.get("external_system"),
        # Redacted with the body, not alongside the metadata. Both of these ADDRESS the content
        # rather than describe it: external_reference_url is a deep link straight to the message
        # in Outlook/WhatsApp, and external_message_id is the provider key that retrieves it
        # through that provider's API. Returning either to a caller denied body_text would defeat
        # the redaction with a pointer instead of a copy.
        external_message_id=row.get("external_message_id") if may_read_content else None,
        idempotency_key=row.get("idempotency_key"),
        external_reference_url=row.get("external_reference_url") if may_read_content else None,
        geo_latitude=row.get("geo_latitude"),
        geo_longitude=row.get("geo_longitude"),
        outcome=row.get("outcome"),
        next_follow_up_at=row.get("next_follow_up_at"),
        recorded_by=row.get("recorded_by"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        participants=participant_responses,
        inherited_from=inherited_from,
    )


def _fingerprint_value(value: Any) -> Any:
    """Normalize one command value into a JSON-serializable, comparison-stable form.

    `None` stays `None` - JSON distinguishes it from every string, so no sentinel is needed.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        # Normalize to UTC so the same instant expressed in two offsets is one command. A naive
        # datetime is read as UTC, matching how the column stores it.
        moment = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return moment.isoformat()
    if isinstance(value, Decimal):
        # Trailing zeros must not change identity: 19.076 and 19.076000 are the same coordinate.
        return format(value.normalize(), "f")
    if isinstance(value, UUID):
        return str(value)
    return value


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def compute_request_fingerprint(payload: InteractionCreate) -> str:
    """A stable SHA-256 over the normalized create command, encoded as canonical JSON.

    Two requests share a fingerprint exactly when they describe the same conversation, so a
    retry can prove it is the same command before being allowed to replay an existing record.

    **Why canonical JSON and not a delimited string.** The first implementation joined
    `name=value` pairs with a control character. That is not an injective encoding: a value
    containing the delimiter can forge a field boundary, so two genuinely different commands can
    produce identical bytes. Concretely, `subject="u"` with
    `body_text="v<US>body_text="` and `subject="u<US>body_text=v"` with `body_text=""` both
    rendered as `subject=u<US>body_text=v<US>body_text=`. JSON escapes control characters and
    quotes structurally, so the encoding is unambiguous by construction rather than by hoping
    no value contains the separator.

    Normalization is explicit: UTC for datetimes, trailing zeros stripped from decimals, the
    *effective* external_system (an omitted value and an explicit "MANUAL" are the same command,
    because the service stores MANUAL either way), and participants sorted by their own canonical
    form so ordering does not change identity.

    `idempotency_key` is the only excluded field: it is the key, not the command.
    `external_message_id` IS included - it is immutable provider identity, and excluding it let a
    retry change which provider message a record claimed to be while reusing the same key.
    """
    command = {
        name: _fingerprint_value(getattr(payload, name))
        for name in INTERACTION_FINGERPRINT_FIELDS
    }
    # The effective value the row will actually carry, not the raw request value.
    command["external_system"] = payload.external_system or EXTERNAL_SYSTEM_MANUAL

    command["participants"] = sorted(
        (
            _canonical_json(
                {
                    field: _fingerprint_value(getattr(participant, field))
                    for field in INTERACTION_FINGERPRINT_PARTICIPANT_FIELDS
                }
            )
            for participant in payload.participants
        )
    )

    return hashlib.sha256(_canonical_json(command).encode("utf-8")).hexdigest()


def _find_existing_for_replay(db: Session, *, payload: InteractionCreate) -> dict[str, Any] | None:
    """Resolve the row that made a create conflict, so the retry can replay it.

    Checks the same two keys the database's partial unique indexes enforce, in the order a
    caller would expect them to bind: an explicit idempotency_key first, then the provider's
    (external_system, external_message_id) pair. Returns None when neither key was supplied,
    because then the conflict came from something this function cannot attribute and the caller
    must see an error rather than an unrelated record.

    Resolving the row is only half the question - whether it may be REPLAYED is decided by
    `_assert_replay_is_compatible`, which this function deliberately does not do, so that
    "which row conflicted" and "may the caller have it" stay separable and separately testable.
    """
    if payload.idempotency_key:
        existing = get_interaction_by_idempotency_key(db, idempotency_key=payload.idempotency_key)
        if existing is not None:
            return existing

    if payload.external_system and payload.external_message_id:
        return get_interaction_by_external_message(
            db,
            external_system=payload.external_system,
            external_message_id=payload.external_message_id,
        )

    return None


def _assert_replay_is_compatible(existing: dict[str, Any], *, fingerprint: str) -> None:
    """Refuse to replay a record that is not the same command, or is no longer active.

    Two distinct refusals, both 409:

    - **Key reuse with a different payload.** The key identifies a command, not a licence to
      receive whatever row happens to hold it. Without this check a caller reusing a key with a
      different subject received the ORIGINAL record reported as their own successful create.
    - **The original was soft-deleted.** Replaying it would hand back deleted content as though
      it were an active record, and answering "created" for a conversation somebody deliberately
      removed is wrong in both directions. The caller is told plainly; recording it again is a
      new command with a new key.

    A stored fingerprint of None fails closed: an unattributable row is not replayable.
    """
    if existing.get("is_deleted"):
        raise InteractionDuplicateError(
            "This command was already recorded and the resulting interaction has since been "
            "deleted. It will not be restored by a retry; record it again with a new "
            "idempotency key if it is genuinely a new conversation."
        )

    stored = existing.get("request_fingerprint")
    if stored is None or stored != fingerprint:
        raise InteractionDuplicateError(
            "This idempotency key (or external message identity) has already been used for a "
            "different command. An idempotency key identifies one specific request; reusing it "
            "with a changed payload is refused rather than silently replaying the original."
        )


def create_interaction(
    db: Session,
    *,
    payload: InteractionCreate,
    current_user_public_id: str | None,
    current_user: AuthUser,
    correlation_id: str | None = None,
) -> InteractionCreatedResponse:
    if not linked_record_exists(
        db,
        linked_record_type=payload.linked_record_type,
        linked_record_public_id=str(payload.linked_record_public_id),
    ):
        raise InteractionValidationError(
            f"No {payload.linked_record_type} record exists with public id "
            f"{payload.linked_record_public_id}."
        )

    # A resolved participant link must point at something real. These are deliberately not
    # foreign keys - a participant may be an external person absent from business_party_contact,
    # and a resolved link must survive that contact being deactivated - but "not a foreign key"
    # is not the same as "unvalidated". An unresolvable link is a silent broken reference that
    # only surfaces much later, when someone asks which conversations involved a contact.
    for index, participant in enumerate(payload.participants):
        if participant.contact_public_id is not None and not contact_exists(
            db, contact_public_id=str(participant.contact_public_id)
        ):
            raise InteractionValidationError(
                f"participant {index}: no Account Contact exists with public id "
                f"{participant.contact_public_id}."
            )
        if participant.app_user_public_id is not None and not app_user_exists(
            db, app_user_public_id=str(participant.app_user_public_id)
        ):
            raise InteractionValidationError(
                f"participant {index}: no user exists with public id "
                f"{participant.app_user_public_id}."
            )

    fingerprint = compute_request_fingerprint(payload)
    body_stored = payload.body_text is not None and payload.body_text.strip() != ""
    external_system = payload.external_system or "MANUAL"

    values = {
        "linked_record_type": payload.linked_record_type,
        "linked_record_public_id": str(payload.linked_record_public_id),
        "channel_code": payload.channel_code,
        "direction_code": payload.direction_code,
        "occurred_at": payload.occurred_at,
        "subject": payload.subject,
        "body_text": payload.body_text,
        "body_stored": body_stored,
        "external_system": external_system,
        "external_message_id": payload.external_message_id,
        "idempotency_key": payload.idempotency_key,
        "external_reference_url": payload.external_reference_url,
        "geo_latitude": payload.geo_latitude,
        "geo_longitude": payload.geo_longitude,
        "outcome": payload.outcome,
        "next_follow_up_at": payload.next_follow_up_at,
        "recorded_by": current_user_public_id,
        "request_fingerprint": fingerprint,
    }

    interaction_public_id = str(uuid4())

    try:
        row = insert_interaction(db, public_id=interaction_public_id, values=values)
        if row is None:
            raise InteractionValidationError("Interaction could not be created.")

        interaction_id = row["id"]
        participant_rows: list[dict[str, Any]] = []
        for participant in payload.participants:
            participant_public_id = str(uuid4())
            participant_values = {
                "party_role_code": participant.party_role_code,
                "contact_public_id": str(participant.contact_public_id) if participant.contact_public_id else None,
                "app_user_public_id": str(participant.app_user_public_id) if participant.app_user_public_id else None,
                "display_name": participant.display_name,
                "address_or_number": participant.address_or_number,
            }
            insert_interaction_participant(
                db,
                public_id=participant_public_id,
                interaction_id=interaction_id,
                values=participant_values,
            )
            participant_rows.append(
                {
                    "participant_public_id": participant_public_id,
                    "party_role_code": participant.party_role_code,
                    "contact_public_id": participant.contact_public_id,
                    "app_user_public_id": participant.app_user_public_id,
                    "display_name": participant.display_name,
                    "address_or_number": participant.address_or_number,
                }
            )

        # Metadata only. Never the body, the subject or a participant address - see the
        # module docstring and the guard in tests/test_slice_9d_interaction_event_payloads.py.
        event = record_business_event(
            db,
            event_name=INTERACTION_EVENT_RECORDED,
            source_module=INTERACTION_MODULE_NAME,
            record_type=INTERACTION_RECORD_TYPE,
            record_public_id=interaction_public_id,
            user_public_id=current_user_public_id,
            correlation_id=correlation_id,
            reason="Interaction recorded.",
            event_payload={
                "schema_version": INTERACTION_EVENT_SCHEMA_VERSION,
                "linked_record_type": row["linked_record_type"],
                "linked_record_public_id": str(row["linked_record_public_id"]),
                "channel_code": row["channel_code"],
                "direction_code": row["direction_code"],
                "occurred_at": row["occurred_at"].isoformat() if row.get("occurred_at") else None,
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        # MCF-001: "a retry, repeated submission or double-click does not create a duplicate
        # business effect". A retryable command must therefore REPLAY, not error - an ingestion
        # job whose network call timed out after the row committed will retry, and answering
        # 409 would make a succeeded write look like a failure it must then reconcile by hand.
        # The original record is returned instead, marked so the caller can tell a replay from a
        # first write. Returning an error remains correct only when the conflict cannot be
        # resolved to a specific existing row.
        existing = _find_existing_for_replay(db, payload=payload)
        if existing is not None:
            _assert_replay_is_compatible(existing, fingerprint=fingerprint)
            existing_participants = list_interaction_participants(db, interaction_id=existing["id"])
            return InteractionCreatedResponse(
                interaction=_serialize_interaction(
                    existing, existing_participants, db=db, current_user=current_user
                ),
                event={},
                replayed=True,
            )

        raise InteractionDuplicateError(
            "An interaction with this external_message_id (for the same external_system) or "
            "this idempotency_key has already been recorded, but the existing record could not "
            "be resolved for replay."
        ) from exc
    except Exception:
        db.rollback()
        raise

    response = _serialize_interaction(row, participant_rows, db=db, current_user=current_user)
    return InteractionCreatedResponse(interaction=response, event=event.model_dump())


def get_interaction(
    db: Session, public_id: UUID, *, current_user: AuthUser
) -> InteractionResponse:
    row = get_interaction_by_public_id(db, str(public_id))
    if row is None:
        raise InteractionNotFoundError("Interaction not found.")
    participants = list_interaction_participants(db, interaction_id=row["id"])
    return _serialize_interaction(row, participants, db=db, current_user=current_user)


def list_interactions_for_record(
    db: Session,
    *,
    linked_record_type: str,
    linked_record_public_id: str,
    include_inherited: bool,
    channel_code: str | None,
    direction_code: str | None,
    occurred_from: Any,
    occurred_to: Any,
    limit: int,
    offset: int,
    current_user: AuthUser,
) -> list[InteractionResponse]:
    """The direct rows for this record, plus - only when include_inherited=true - the rows
    inherited from a source Lead. Inherited rows are read-derived, never copied; see the
    module docstring.

    When include_inherited is false this is a single paginated query, same as any other list
    route. When true, direct and inherited rows come from two different linked_record_type
    values and must be merged before pagination is meaningful - so both sides are fetched
    unpaginated (bounded by _INHERITED_MERGE_FETCH_CAP, generous for a pilot's per-record
    conversation volume) and offset/limit are applied once, after the merge and sort.
    """
    if not include_inherited:
        direct_rows = list_interactions(
            db,
            linked_record_type=linked_record_type,
            linked_record_public_id=linked_record_public_id,
            channel_code=channel_code,
            direction_code=direction_code,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            limit=limit,
            offset=offset,
        )
        combined: list[tuple[dict[str, Any], dict[str, str] | None]] = [
            (row, None) for row in direct_rows
        ]
    else:
        fetch_cap = _INHERITED_MERGE_FETCH_CAP
        direct_rows = list_interactions(
            db,
            linked_record_type=linked_record_type,
            linked_record_public_id=linked_record_public_id,
            channel_code=channel_code,
            direction_code=direction_code,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            limit=fetch_cap,
            offset=0,
        )
        combined = [(row, None) for row in direct_rows]

        source_lead_public_ids: list[str] = []
        if linked_record_type == LINKED_RECORD_TYPE_OPPORTUNITY:
            source_lead = get_opportunity_source_lead_public_id(
                db, opportunity_public_id=linked_record_public_id
            )
            if source_lead:
                source_lead_public_ids = [source_lead]
        elif linked_record_type == LINKED_RECORD_TYPE_ACCOUNT:
            source_lead_public_ids = get_account_source_lead_public_ids(
                db, account_public_id=linked_record_public_id
            )

        for lead_public_id in source_lead_public_ids:
            inherited_rows = list_interactions(
                db,
                linked_record_type="lead",
                linked_record_public_id=lead_public_id,
                channel_code=channel_code,
                direction_code=direction_code,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
                limit=fetch_cap,
                offset=0,
            )
            provenance = {
                "record_type": "lead",
                "public_id": lead_public_id,
                "display_reference": lead_public_id,
            }
            combined.extend((row, provenance) for row in inherited_rows)

        combined.sort(key=lambda pair: (pair[0]["occurred_at"], pair[0]["id"]), reverse=True)
        combined = combined[offset : offset + limit]

    interaction_ids = [row["id"] for row, _ in combined]
    participants_by_id = list_participants_for_interactions(db, interaction_ids=interaction_ids)

    return [
        _serialize_interaction(
            row,
            participants_by_id.get(row["id"], []),
            db=db,
            current_user=current_user,
            inherited_from=provenance,
        )
        for row, provenance in combined
    ]


def update_interaction(
    db: Session,
    public_id: UUID,
    *,
    payload: InteractionUpdate,
    current_user_public_id: str | None,
    current_user: AuthUser,
    correlation_id: str | None = None,
) -> InteractionUpdatedResponse:
    interaction_id = get_interaction_id_by_public_id(db, str(public_id))
    if interaction_id is None:
        raise InteractionNotFoundError("Interaction not found.")

    # Only what the caller actually set. `exclude_unset` distinguishes "field omitted" from
    # "field explicitly set to null": omitting outcome leaves it alone, sending
    # {"outcome": null} clears it deliberately. Without this, a PUT naming one field would wipe
    # the other.
    supplied = payload.model_dump(exclude_unset=True)

    try:
        row = repo_update_interaction(db, interaction_id=interaction_id, values=supplied)
        if row is None:
            raise InteractionNotFoundError("Interaction not found.")

        event = record_business_event(
            db,
            event_name=INTERACTION_EVENT_UPDATED,
            source_module=INTERACTION_MODULE_NAME,
            record_type=INTERACTION_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            correlation_id=correlation_id,
            reason="Interaction outcome/follow-up corrected.",
            event_payload={
                "schema_version": INTERACTION_EVENT_SCHEMA_VERSION,
                "linked_record_type": row["linked_record_type"],
                "linked_record_public_id": str(row["linked_record_public_id"]),
                "next_follow_up_at": row["next_follow_up_at"].isoformat() if row.get("next_follow_up_at") else None,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    participants = list_interaction_participants(db, interaction_id=interaction_id)
    response = _serialize_interaction(row, participants, db=db, current_user=current_user)
    return InteractionUpdatedResponse(interaction=response, event=event.model_dump())


def delete_interaction(
    db: Session,
    public_id: UUID,
    *,
    current_user_public_id: str | None,
    correlation_id: str | None = None,
) -> InteractionDeletedResponse:
    interaction_id = get_interaction_id_by_public_id(db, str(public_id))
    if interaction_id is None:
        raise InteractionNotFoundError("Interaction not found.")

    row = get_interaction_by_public_id(db, str(public_id))

    try:
        soft_delete_interaction(db, interaction_id=interaction_id)
        event = record_business_event(
            db,
            event_name=INTERACTION_EVENT_DELETED,
            source_module=INTERACTION_MODULE_NAME,
            record_type=INTERACTION_RECORD_TYPE,
            record_public_id=str(public_id),
            user_public_id=current_user_public_id,
            correlation_id=correlation_id,
            reason="Interaction soft-deleted.",
            event_payload={
                "schema_version": INTERACTION_EVENT_SCHEMA_VERSION,
                "linked_record_type": row["linked_record_type"] if row else None,
                "linked_record_public_id": str(row["linked_record_public_id"]) if row else None,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return InteractionDeletedResponse(public_id=public_id, event=event.model_dump())
