"""Eligibility codes: certificate kinds, rules, outcomes, the due list's bands and events (ELG-1).

docs/agent/slices/elg-1-machine-eligibility.md, sections 5, 6, 7 and 11. The jurisdictions, the certificate
kinds and the rules themselves are data, loaded by migration 20260908_0044 and read from the database; what
lives here is the fixed vocabulary around them.
"""

from __future__ import annotations

from typing import Final

ELIGIBILITY_MODULE_NAME: Final = "eligibility"

# --- Jurisdictions ---------------------------------------------------------------------------------------
# `IN` is the central government's own sites (Q8): its rules apply there to labour safety. Every other
# jurisdiction is a state or union territory, by its ISO 3166-2:IN code.
JURISDICTION_CENTRAL: Final = "IN"
JURISDICTION_KIND_CENTRAL: Final = "CENTRAL"

# --- Certificate kinds (section 5.4) --------------------------------------------------------------------
KIND_REGISTRATION: Final = "REGISTRATION"
KIND_INSURANCE: Final = "INSURANCE"
KIND_POLLUTION_UNDER_CONTROL: Final = "POLLUTION_UNDER_CONTROL"
KIND_ROAD_TAX: Final = "ROAD_TAX"
KIND_FITNESS: Final = "FITNESS"
KIND_PERMIT: Final = "PERMIT"
KIND_THOROUGH_EXAMINATION: Final = "THOROUGH_EXAMINATION"
KIND_LOAD_TEST: Final = "LOAD_TEST"

# How a registration says the vehicle is registered. Transport vehicles also need fitness and permits.
REGISTERED_AS_TRANSPORT: Final = "TRANSPORT"
REGISTERED_AS_NON_TRANSPORT: Final = "NON_TRANSPORT"
REGISTERED_AS_CODES: Final = (REGISTERED_AS_TRANSPORT, REGISTERED_AS_NON_TRANSPORT)

CERTIFICATE_STATUS_RECORDED: Final = "RECORDED"
CERTIFICATE_STATUS_WITHDRAWN: Final = "WITHDRAWN"
MARK_STATUS_IN_FORCE: Final = "IN_FORCE"
MARK_STATUS_WITHDRAWN: Final = "WITHDRAWN"

# --- Rules (section 5.3) -------------------------------------------------------------------------------
APPLIES_ALWAYS: Final = "ALWAYS"
APPLIES_TRANSPORT_ONLY: Final = "TRANSPORT_ONLY"
APPLIES_WHEN_CODES: Final = (APPLIES_ALWAYS, APPLIES_TRANSPORT_ONLY)

BASIS_STATUTORY: Final = "STATUTORY"
BASIS_PBL_RULE: Final = "PBL_RULE"
BASIS_CODES: Final = (BASIS_STATUTORY, BASIS_PBL_RULE)

# What a lapse does. The law always blocks (ELA-001), or is not required where a jurisdiction says so.
LAPSE_BLOCK: Final = "BLOCK"
LAPSE_OVERRIDE: Final = "OVERRIDE"
LAPSE_WARN: Final = "WARN"
LAPSE_NOT_REQUIRED: Final = "NOT_REQUIRED"
LAPSE_CODES: Final = (LAPSE_BLOCK, LAPSE_OVERRIDE, LAPSE_WARN, LAPSE_NOT_REQUIRED)
STATUTORY_LAPSE_CODES: Final = (LAPSE_BLOCK, LAPSE_NOT_REQUIRED)

# Whether "not applicable" may be claimed for one asset: only where the law is unclear (owner, 27 September
# 2026: "Option of N/A ... accepted in such cases - not if the law is clear").
NOT_APPLICABLE_NOT_ALLOWED: Final = "NOT_ALLOWED"
NOT_APPLICABLE_ALLOWED: Final = "ALLOWED"
NOT_APPLICABLE_CODES: Final = (NOT_APPLICABLE_NOT_ALLOWED, NOT_APPLICABLE_ALLOWED)
MAX_NOT_APPLICABLE_MONTHS: Final = 120
MAX_RENEW_EVERY_MONTHS: Final = 240

# --- The decision (section 6; ELA-001) ------------------------------------------------------------------
OVERALL_ELIGIBLE: Final = "ELIGIBLE"
OVERALL_WARNING: Final = "WARNING"
OVERALL_BLOCKED: Final = "BLOCKED"
OVERALL_OVERRIDE_REQUIRED: Final = "OVERRIDE_REQUIRED"

OUTCOME_VALID: Final = "VALID"
OUTCOME_RUNS_OUT_SOON: Final = "RUNS_OUT_SOON"
OUTCOME_RUNS_OUT_IN_PERIOD: Final = "RUNS_OUT_IN_PERIOD"
OUTCOME_RUNS_OUT_BEFORE_START: Final = "RUNS_OUT_BEFORE_START"
OUTCOME_RUN_OUT: Final = "RUN_OUT"
OUTCOME_MISSING: Final = "MISSING"
OUTCOME_COPY_MISSING: Final = "COPY_MISSING"
OUTCOME_NOT_APPLICABLE: Final = "NOT_APPLICABLE"
# The asset's own check: a retired asset cannot be allocated (RMR-001).
OUTCOME_RETIRED: Final = "RETIRED"

EFFECT_NONE: Final = "NONE"
EFFECT_WARNING: Final = "WARNING"
EFFECT_OVERRIDE: Final = "OVERRIDE"
EFFECT_BLOCK: Final = "BLOCK"

# FRS Controls, "Asset Documentation Warning": a certificate within this many days of running out warns.
RUNS_OUT_SOON_DAYS: Final = 15

# --- Certificates due (section 7) ------------------------------------------------------------------------
BAND_MISSING: Final = "MISSING"
BAND_COPY_MISSING: Final = "COPY_MISSING"
BAND_RUN_OUT: Final = "RUN_OUT"
BAND_WITHIN_15: Final = "WITHIN_15"
BAND_WITHIN_30: Final = "WITHIN_30"
BAND_WITHIN_60: Final = "WITHIN_60"
BAND_CODES: Final = (BAND_MISSING, BAND_COPY_MISSING, BAND_RUN_OUT, BAND_WITHIN_15, BAND_WITHIN_30, BAND_WITHIN_60)
# ELA-001's 60, 30 and 15 days: PBL's policy, not the law (section 2, C).
BAND_DAYS: Final = ((BAND_WITHIN_15, 15), (BAND_WITHIN_30, 30), (BAND_WITHIN_60, 60))

# --- Events (section 11) ----------------------------------------------------------------------------------
EVENT_CERTIFICATE_RECORDED: Final = "ELIGIBILITY_CERTIFICATE_RECORDED"
EVENT_CERTIFICATE_WITHDRAWN: Final = "ELIGIBILITY_CERTIFICATE_WITHDRAWN"
EVENT_NOT_APPLICABLE_RECORDED: Final = "ELIGIBILITY_NOT_APPLICABLE_RECORDED"
EVENT_NOT_APPLICABLE_WITHDRAWN: Final = "ELIGIBILITY_NOT_APPLICABLE_WITHDRAWN"
EVENT_RULE_RECORDED: Final = "ELIGIBILITY_RULE_RECORDED"
EVENT_RULE_ENDED: Final = "ELIGIBILITY_RULE_ENDED"
EVENT_EVALUATED: Final = "ELIGIBILITY_EVALUATED"

# A certificate's copy: a Slice 9C document of this type, uploaded to the platform (Q5). No other document
# linked to a certificate counts, and none other may be attached to one.
COPY_DOCUMENT_TYPE: Final = "CERTIFICATE"

# The record types events are written under, and a certificate's copies are linked to (Slice 9C).
RECORD_TYPE_CERTIFICATE: Final = "eligibility_certificate"
RECORD_TYPE_NOT_APPLICABLE: Final = "eligibility_not_applicable"
RECORD_TYPE_RULE: Final = "eligibility_rule"
RECORD_TYPE_DECISION: Final = "eligibility_decision"

# --- Reminders and escalation (ELG-2) ---------------------------------------------------------------------
# docs/agent/slices/elg-2-certificate-reminders.md. The reminders are worked out when read; only the settings and
# the "seen" marks are stored.
REMINDER_RUNNING_OUT: Final = "CERTIFICATE_RUNNING_OUT"
REMINDER_NOT_YET_RECORDED: Final = "NOT_YET_RECORDED"
REMINDER_BEFORE_JOB: Final = "BEFORE_JOB_STARTS"
REMINDER_DURING_JOB: Final = "DURING_JOB"
# HOL-1 (Q2): PBL's holiday calendar for a year is not set up - about a year, not a machine. Read through the port the
# calendar registers (ports.py); its date is 1 January of the year.
REMINDER_CALENDAR_NOT_SET_UP: Final = "HOLIDAY_CALENDAR_NOT_SET_UP"
REMINDER_KIND_CODES: Final = (
    REMINDER_RUNNING_OUT,
    REMINDER_NOT_YET_RECORDED,
    REMINDER_BEFORE_JOB,
    REMINDER_DURING_JOB,
    REMINDER_CALENDAR_NOT_SET_UP,
)
REMINDER_KIND_LABELS: Final = {
    REMINDER_RUNNING_OUT: "A certificate running out",
    REMINDER_NOT_YET_RECORDED: "A certificate not yet recorded",
    REMINDER_BEFORE_JOB: "Runs out before the job starts",
    REMINDER_DURING_JOB: "Runs out during the job",
    REMINDER_CALENDAR_NOT_SET_UP: "PBL's holiday calendar not set up",
}
ALLOCATION_REMINDER_KIND_CODES: Final = (REMINDER_BEFORE_JOB, REMINDER_DURING_JOB)

# Why a certificate is short, which gives a reminder its date (section 5.2). The last three are papers never entered
# since they became needed: "A certificate not yet recorded" (Q19a).
REASON_RUNS_OUT: Final = "RUNS_OUT"
REASON_MARK_ENDS: Final = "MARK_ENDS"
REASON_MARK_WITHDRAWN: Final = "MARK_WITHDRAWN"
REASON_COPY_MISSING: Final = "COPY_MISSING"
REASON_ADDED: Final = "MACHINE_ADDED"
REASON_RULE: Final = "RULE_IN_EFFECT"
REASON_TRANSPORT: Final = "REGISTERED_TRANSPORT"
NOT_YET_RECORDED_REASONS: Final = (REASON_ADDED, REASON_RULE, REASON_TRANSPORT)
# A year's calendar not marked complete (HOL-1).
REASON_CALENDAR_NOT_COMPLETE: Final = "CALENDAR_NOT_COMPLETE"

# What a reminder is about: an asset (the renewal list), or a machine or piece of kit on an allocation (8A).
SUBJECT_ASSET: Final = "asset"
SUBJECT_ALLOCATION: Final = "resource_assignment"
SUBJECT_KIT_LINE: Final = "resource_assignment_kit"
# A year of PBL's holiday calendar (HOL-1): its "seen" marks carry the year, and no asset or certificate kind.
SUBJECT_CALENDAR_YEAR: Final = "holiday_calendar_year"
SUBJECT_TYPES: Final = (SUBJECT_ASSET, SUBJECT_ALLOCATION, SUBJECT_KIT_LINE, SUBJECT_CALENDAR_YEAR)

# A step of a path reaches its audience from the first reminder, or from N days before the date (negative: after).
STEP_FROM_FIRST_REMINDER: Final = "FIRST_REMINDER"
STEP_FROM_DAYS_BEFORE: Final = "DAYS_BEFORE"
STEP_START_CODES: Final = (STEP_FROM_FIRST_REMINDER, STEP_FROM_DAYS_BEFORE)

# Channels: the screen only, until the notification service (NTF-001) is built with a provider.
CHANNEL_SCREEN: Final = "SCREEN"
CHANNEL_CODES: Final = (CHANNEL_SCREEN,)

MAX_BANDS: Final = 10
MAX_STEPS: Final = 10
MAX_REMINDER_DAYS: Final = 365
MAX_SEEN_AT_ONCE: Final = 200
MAX_ALERT_LIMIT: Final = 500
REMINDER_KEY_MAX_LENGTH: Final = 400

EVENT_ALERT_SETTING_CHANGED: Final = "ELIGIBILITY_ALERT_SETTING_CHANGED"
RECORD_TYPE_ALERT_SETTING: Final = "eligibility_alert_setting"

# --- Limits ------------------------------------------------------------------------------------------------
NUMBER_MAX_LENGTH: Final = 200
ISSUED_BY_MAX_LENGTH: Final = 200
REASON_MAX_LENGTH: Final = 1000
SOURCE_MAX_LENGTH: Final = 1000
REQUEST_KEY_MAX_LENGTH: Final = 100
