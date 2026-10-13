"""Interaction contract constants (Slice 9D).

A shared, channel-agnostic conversation log - calls, emails, WhatsApp messages, meetings and
site visits - attached polymorphically to Lead, Account, Opportunity, Commercial Offer or Work
Order.

Interactions are a different record from Slice 2D Lead activities (`crm_lead_activity`), which
remain unchanged. See docs/agent/slices/slice-9d-interaction-foundation.md for the reconciliation
note on why the two are kept separate.
"""

INTERACTION_MODULE_NAME = "interactions"
INTERACTION_TABLE = "interaction"
INTERACTION_PARTICIPANT_TABLE = "interaction_participant"
INTERACTION_RECORD_TYPE = "interaction"

# MCF-001 "stable public identity and explicit contract/schema version". Consumers read this
# rather than inferring compatibility from field presence. Bump the minor part for a backward-
# compatible addition, the major part for a breaking change, and record the change in
# docs/agent/contracts/interaction-contract.md before doing either.
INTERACTION_CONTRACT_VERSION = "2.0"  # 2.0 (11 October 2026): a date and time with no zone is refused

# The schema version of the event payloads this module emits. Deliberately separate from the API
# contract version above: an event consumer and an API caller are different audiences and can
# legitimately move at different speeds.
INTERACTION_EVENT_SCHEMA_VERSION = "1.0"

# MCF-001 correlation. Callers may supply this header to tie a command, its business events and
# any downstream activity into one traceable chain; when absent the service generates one so a
# correlation reference always exists.
INTERACTION_CORRELATION_HEADER = "X-Correlation-Id"

# --- linked_record_type: the five record types an interaction may be recorded against --------
LINKED_RECORD_TYPE_LEAD = "lead"
LINKED_RECORD_TYPE_ACCOUNT = "business_party"
LINKED_RECORD_TYPE_OPPORTUNITY = "opportunity"
LINKED_RECORD_TYPE_COMMERCIAL_OFFER = "commercial_offer"
LINKED_RECORD_TYPE_WORK_ORDER = "work_order"

INTERACTION_LINKED_RECORD_TYPES = (
    LINKED_RECORD_TYPE_LEAD,
    LINKED_RECORD_TYPE_ACCOUNT,
    LINKED_RECORD_TYPE_OPPORTUNITY,
    LINKED_RECORD_TYPE_COMMERCIAL_OFFER,
    LINKED_RECORD_TYPE_WORK_ORDER,
)

# Maps each linked_record_type to the table and public-id column used to prove the target
# actually exists. Deliberately a direct, minimal, read-only lookup rather than importing each
# owning module's repository/service layer - a public_id existence check is the smallest
# possible cross-module read, consistent with PRODUCTION_ARCHITECTURE_DIRECTION.md's allowance
# for "an explicitly approved immutable identifier/reference", and it avoids adding a fifth
# instance of the cross-module repository-import pattern PF-1B is already scoped to clean up
# (see ADR-030's PLATFORM_PRINCIPLES_IMPLEMENTATION_REVIEW.md finding on leads/service.py and
# opportunities/service.py).
LINKED_RECORD_EXISTENCE_LOOKUP: dict[str, tuple[str, str]] = {
    LINKED_RECORD_TYPE_LEAD: ("crm_lead", "lead_public_id"),
    LINKED_RECORD_TYPE_ACCOUNT: ("business_party", "business_party_public_id"),
    LINKED_RECORD_TYPE_OPPORTUNITY: ("crm_opportunity", "opportunity_public_id"),
    LINKED_RECORD_TYPE_COMMERCIAL_OFFER: ("crm_commercial_offer", "offer_public_id"),
    LINKED_RECORD_TYPE_WORK_ORDER: ("crm_work_order", "work_order_public_id"),
}

# --- channel_code -------------------------------------------------------------------------
CHANNEL_CALL = "CALL"
CHANNEL_EMAIL = "EMAIL"
CHANNEL_WHATSAPP = "WHATSAPP"
CHANNEL_MEETING = "MEETING"
CHANNEL_SITE_VISIT = "SITE_VISIT"
CHANNEL_SMS = "SMS"
CHANNEL_PORTAL = "PORTAL"
CHANNEL_LETTER = "LETTER"
CHANNEL_NOTE = "NOTE"
CHANNEL_OTHER = "OTHER"

INTERACTION_CHANNELS = (
    CHANNEL_CALL,
    CHANNEL_EMAIL,
    CHANNEL_WHATSAPP,
    CHANNEL_MEETING,
    CHANNEL_SITE_VISIT,
    CHANNEL_SMS,
    CHANNEL_PORTAL,
    CHANNEL_LETTER,
    CHANNEL_NOTE,
    CHANNEL_OTHER,
)

# --- direction_code ------------------------------------------------------------------------
DIRECTION_INBOUND = "INBOUND"
DIRECTION_OUTBOUND = "OUTBOUND"
DIRECTION_INTERNAL = "INTERNAL"

INTERACTION_DIRECTIONS = (DIRECTION_INBOUND, DIRECTION_OUTBOUND, DIRECTION_INTERNAL)

# --- external_system: who originated the record, for future ingestion idempotency -----------
EXTERNAL_SYSTEM_MANUAL = "MANUAL"
EXTERNAL_SYSTEM_OUTLOOK = "OUTLOOK"
EXTERNAL_SYSTEM_WHATSAPP = "WHATSAPP"
EXTERNAL_SYSTEM_FREJUN = "FREJUN"
EXTERNAL_SYSTEM_RUNO = "RUNO"

INTERACTION_EXTERNAL_SYSTEMS = (
    EXTERNAL_SYSTEM_MANUAL,
    EXTERNAL_SYSTEM_OUTLOOK,
    EXTERNAL_SYSTEM_WHATSAPP,
    EXTERNAL_SYSTEM_FREJUN,
    EXTERNAL_SYSTEM_RUNO,
)

# --- participant party_role_code ------------------------------------------------------------
PARTICIPANT_ROLE_FROM = "FROM"
PARTICIPANT_ROLE_TO = "TO"
PARTICIPANT_ROLE_CC = "CC"
PARTICIPANT_ROLE_BCC = "BCC"
PARTICIPANT_ROLE_ATTENDEE = "ATTENDEE"

INTERACTION_PARTICIPANT_ROLES = (
    PARTICIPANT_ROLE_FROM,
    PARTICIPANT_ROLE_TO,
    PARTICIPANT_ROLE_CC,
    PARTICIPANT_ROLE_BCC,
    PARTICIPANT_ROLE_ATTENDEE,
)

# --- immutable fields, enforced by the update route --------------------------------------
# Once recorded, these fields may never change through PUT. The original communication is
# evidence; an editable body is evidence of what someone last typed, not what the customer said.
# PUT may change only outcome and next_follow_up_at.
INTERACTION_MUTABLE_UPDATE_FIELDS = ("outcome", "next_follow_up_at")

# --- idempotency ------------------------------------------------------------------------------
# The fields that define "the same command" for replay purposes. A retry may replay an existing
# record only when its normalized fingerprint over exactly these fields matches the stored one.
#
# Deliberately excludes exactly one field: idempotency_key, which is the KEY rather than the
# command. Also excluded is recorded_by, which is not part of the command at all - the same
# command retried by a different authenticated user is still the same command, and the original
# actor stays recorded.
#
# external_message_id IS included. An earlier version excluded it on the reasoning that it was
# "part of the key"; that was wrong. It is immutable provider identity, and excluding it let a
# retry reusing one idempotency key change which provider message the record claimed to be while
# still matching the stored fingerprint.
#
# external_system is fingerprinted at its EFFECTIVE value: the service stores "MANUAL" when the
# caller omits it, so an omitted value and an explicit "MANUAL" are the same command.
INTERACTION_FINGERPRINT_FIELDS = (
    "linked_record_type",
    "linked_record_public_id",
    "channel_code",
    "direction_code",
    "occurred_at",
    "subject",
    "body_text",
    "external_system",
    "external_message_id",
    "external_reference_url",
    "geo_latitude",
    "geo_longitude",
    "outcome",
    "next_follow_up_at",
)

INTERACTION_FINGERPRINT_PARTICIPANT_FIELDS = (
    "party_role_code",
    "contact_public_id",
    "app_user_public_id",
    "display_name",
    "address_or_number",
)

# --- business events -----------------------------------------------------------------------
INTERACTION_EVENT_RECORDED = "InteractionRecorded"
INTERACTION_EVENT_UPDATED = "InteractionUpdated"
INTERACTION_EVENT_DELETED = "InteractionDeleted"
