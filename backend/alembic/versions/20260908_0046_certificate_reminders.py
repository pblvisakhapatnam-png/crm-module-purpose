"""certificate reminders and escalation: settings and "seen" marks (ELG-2)

Design: docs/agent/slices/elg-2-certificate-reminders.md (agreed by the owner, 1 October 2026), sections 5 and 10.
The reminders themselves are worked out when read; what is stored is:

- **`eligibility_alert_setting`** - one version of one kind of reminder's setting, never edited: a change is a new
  version, with who saved it and when (Q18).
- **`eligibility_alert_band`** - the setting's schedule: from N days before the date, every M days.
- **`eligibility_alert_step`** - the setting's path: a role, from when it is reached, and its channels - the screen
  only, until the notification service exists (NTF-001).
- **`eligibility_alert_acknowledgement`** - one person's "seen" of one reminder on one reminder day (Q17). It
  changes nothing else, and records no business event.
- **The standard settings** - version 1 of each of the four kinds: the schedule of Q15 and the paths of Q16, and
  for "A certificate not yet recorded" those of Q19a.

The order across rows - bands in order with the last on or after the date, the first step from the first reminder -
is the service's, under the module's write lock, as rules are. Spells out every value rather than importing them, so
this revision stays a frozen historical snapshot (the 20260908_0033 to 0045 convention).

Revision ID: 20260908_0046
Revises: 20260908_0045
Create Date: 2026-10-01
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from alembic import op

revision: str = "20260908_0046"
down_revision: Union[str, None] = "20260908_0045"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SETTING_TABLE = "eligibility_alert_setting"
BAND_TABLE = "eligibility_alert_band"
STEP_TABLE = "eligibility_alert_step"
SEEN_TABLE = "eligibility_alert_acknowledgement"
USER_TABLE = "app_user"
ROLE_TABLE = "role"
ASSET_TABLE = "equipment_asset"
KIND_TABLE = "eligibility_certificate_kind"

REMINDER_KINDS = ("CERTIFICATE_RUNNING_OUT", "NOT_YET_RECORDED", "BEFORE_JOB_STARTS", "DURING_JOB")
SUBJECT_TYPES = ("asset", "resource_assignment", "resource_assignment_kit")
STEP_STARTS = ("FIRST_REMINDER", "DAYS_BEFORE")
MAX_DAYS = 365

# Q15: 60 and 30 days before, weekly from 15, daily from 7, and every day from the day it runs out.
STANDARD_SCHEDULE = ((60, 30), (15, 7), (7, 1), (0, 1))
# Q19a: every day from the day it became needed.
NOT_YET_RECORDED_SCHEDULE = ((0, 1),)
# (role, start, days before - negative: after). Q16 and Q19a.
STANDARD_SETTINGS: dict[str, tuple[tuple[tuple[int, int], ...], tuple[tuple[str, str, int | None], ...]]] = {
    "CERTIFICATE_RUNNING_OUT": (
        STANDARD_SCHEDULE,
        (("ADMIN", "FIRST_REMINDER", None), ("OPERATIONS_USER", "DAYS_BEFORE", 15), ("MANAGEMENT_READ_ONLY", "DAYS_BEFORE", 7)),
    ),
    "NOT_YET_RECORDED": (
        NOT_YET_RECORDED_SCHEDULE,
        (("ADMIN", "FIRST_REMINDER", None), ("OPERATIONS_USER", "DAYS_BEFORE", -7), ("MANAGEMENT_READ_ONLY", "DAYS_BEFORE", -14)),
    ),
    "BEFORE_JOB_STARTS": (
        STANDARD_SCHEDULE,
        (("ADMIN", "FIRST_REMINDER", None), ("OPERATIONS_USER", "FIRST_REMINDER", None), ("MANAGEMENT_READ_ONLY", "DAYS_BEFORE", 7)),
    ),
    "DURING_JOB": (
        STANDARD_SCHEDULE,
        (("ADMIN", "FIRST_REMINDER", None), ("OPERATIONS_USER", "FIRST_REMINDER", None), ("MANAGEMENT_READ_ONLY", "DAYS_BEFORE", 7)),
    ),
}


def _codes(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        SETTING_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("setting_public_id", sa.String(length=36), nullable=False),
        sa.Column("reminder_kind_code", sa.String(length=30), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        # Empty for the versions loaded by this migration: "loaded with the package".
        sa.Column("saved_by", sa.String(length=36), nullable=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("setting_public_id", name="uq_eligibility_alert_setting_public_id"),
        sa.UniqueConstraint("reminder_kind_code", "version_number", name="uq_eligibility_alert_setting_version"),
        sa.ForeignKeyConstraint(["saved_by"], [f"{USER_TABLE}.public_id"], name="fk_eligibility_alert_setting_saved_by"),
        sa.CheckConstraint(f"reminder_kind_code IN ({_codes(REMINDER_KINDS)})", name="ck_eligibility_alert_setting_kind"),
        sa.CheckConstraint("version_number >= 1", name="ck_eligibility_alert_setting_version"),
    )
    op.create_table(
        BAND_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("setting_id", sa.Integer(), nullable=False),
        sa.Column("band_number", sa.Integer(), nullable=False),
        # Days before the date the band starts; negative: after it.
        sa.Column("from_days_before", sa.Integer(), nullable=False),
        sa.Column("every_days", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["setting_id"], [f"{SETTING_TABLE}.id"], name="fk_eligibility_alert_band_setting"),
        sa.UniqueConstraint("setting_id", "band_number", name="uq_eligibility_alert_band_number"),
        sa.UniqueConstraint("setting_id", "from_days_before", name="uq_eligibility_alert_band_start"),
        sa.CheckConstraint("band_number >= 1", name="ck_eligibility_alert_band_number"),
        sa.CheckConstraint(f"from_days_before BETWEEN -{MAX_DAYS} AND {MAX_DAYS}", name="ck_eligibility_alert_band_start"),
        sa.CheckConstraint(f"every_days BETWEEN 1 AND {MAX_DAYS}", name="ck_eligibility_alert_band_every"),
    )
    op.create_table(
        STEP_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("setting_id", sa.Integer(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("role_code", sa.String(length=50), nullable=False),
        sa.Column("starts_code", sa.String(length=20), nullable=False),
        sa.Column("from_days_before", sa.Integer(), nullable=True),
        sa.Column("channel_codes", ARRAY(sa.String(length=20)), nullable=False),
        sa.ForeignKeyConstraint(["setting_id"], [f"{SETTING_TABLE}.id"], name="fk_eligibility_alert_step_setting"),
        sa.ForeignKeyConstraint(["role_code"], [f"{ROLE_TABLE}.role_code"], name="fk_eligibility_alert_step_role"),
        sa.UniqueConstraint("setting_id", "step_number", name="uq_eligibility_alert_step_number"),
        sa.UniqueConstraint("setting_id", "role_code", name="uq_eligibility_alert_step_role"),
        sa.CheckConstraint("step_number >= 1", name="ck_eligibility_alert_step_number"),
        sa.CheckConstraint(f"starts_code IN ({_codes(STEP_STARTS)})", name="ck_eligibility_alert_step_starts"),
        sa.CheckConstraint(
            "(starts_code = 'DAYS_BEFORE') = (from_days_before IS NOT NULL)", name="ck_eligibility_alert_step_days_given"
        ),
        sa.CheckConstraint(
            f"from_days_before IS NULL OR from_days_before BETWEEN -{MAX_DAYS} AND {MAX_DAYS}",
            name="ck_eligibility_alert_step_days",
        ),
        # The screen only, until another channel is integrated (NTF-001): a later revision widens this.
        sa.CheckConstraint(
            "cardinality(channel_codes) >= 1 AND channel_codes <@ ARRAY['SCREEN']::varchar[]",
            name="ck_eligibility_alert_step_channels",
        ),
    )
    op.create_table(
        SEEN_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reminder_key", sa.String(length=400), nullable=False),
        sa.Column("reminder_kind_code", sa.String(length=30), nullable=False),
        sa.Column("equipment_asset_public_id", sa.String(length=36), nullable=False),
        # What the reminder is about. No key for an allocation or kit line, as a stored decision's "requested for"
        # has none: Eligibility's tables never point into Resource Assignments'.
        sa.Column("subject_type", sa.String(length=30), nullable=False),
        sa.Column("subject_public_id", sa.String(length=36), nullable=False),
        sa.Column("kind_code", sa.String(length=30), nullable=False),
        # The date the reminder is about, which its key ends with.
        sa.Column("reminder_date_on", sa.Date(), nullable=False),
        sa.Column("reminder_on", sa.Date(), nullable=False),
        sa.Column("seen_by", sa.String(length=36), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("reminder_key", "reminder_on", "seen_by", name="uq_eligibility_alert_acknowledgement"),
        sa.ForeignKeyConstraint(
            ["equipment_asset_public_id"], [f"{ASSET_TABLE}.asset_public_id"], name="fk_eligibility_alert_acknowledgement_asset"
        ),
        sa.ForeignKeyConstraint(["kind_code"], [f"{KIND_TABLE}.kind_code"], name="fk_eligibility_alert_acknowledgement_kind"),
        sa.ForeignKeyConstraint(["seen_by"], [f"{USER_TABLE}.public_id"], name="fk_eligibility_alert_acknowledgement_seen_by"),
        sa.CheckConstraint(
            f"reminder_kind_code IN ({_codes(REMINDER_KINDS)})", name="ck_eligibility_alert_acknowledgement_kind"
        ),
        sa.CheckConstraint(
            f"subject_type IN ({_codes(SUBJECT_TYPES)})", name="ck_eligibility_alert_acknowledgement_subject"
        ),
        # The key names exactly the reminder it marks, part by part: its kind, what it is about, the asset, the
        # certificate kind and its date - the stored date written as YYYY-MM-DD, so an impossible date can never match -
        # and nothing more (independent review, ELG2-R1-004 and ELG2-R2-006).
        sa.CheckConstraint(
            "split_part(reminder_key, '|', 1) = reminder_kind_code "
            "AND split_part(reminder_key, '|', 2) = subject_type "
            "AND split_part(reminder_key, '|', 3) = subject_public_id "
            "AND split_part(reminder_key, '|', 4) = equipment_asset_public_id "
            "AND split_part(reminder_key, '|', 5) = kind_code "
            "AND split_part(reminder_key, '|', 6) = to_char(reminder_date_on, 'YYYY-MM-DD') "
            "AND split_part(reminder_key, '|', 7) = ''",
            name="ck_eligibility_alert_acknowledgement_key",
        ),
    )
    op.create_index("ix_eligibility_alert_acknowledgement_asset", SEEN_TABLE, ["equipment_asset_public_id"])
    op.create_index("ix_eligibility_alert_acknowledgement_subject", SEEN_TABLE, ["subject_public_id"])
    _seed_standard_settings()


def _seed_standard_settings() -> None:
    connection = op.get_bind()
    saved_at = datetime.now(timezone.utc)
    for kind, (bands, steps) in STANDARD_SETTINGS.items():
        setting_id = connection.execute(
            sa.text(
                f"INSERT INTO {SETTING_TABLE} (setting_public_id, reminder_kind_code, version_number, saved_by, saved_at) "
                "VALUES (:public_id, :kind, 1, NULL, :saved_at) RETURNING id"
            ),
            {"public_id": str(uuid4()), "kind": kind, "saved_at": saved_at},
        ).scalar_one()
        for number, (from_days_before, every_days) in enumerate(bands, 1):
            connection.execute(
                sa.text(
                    f"INSERT INTO {BAND_TABLE} (setting_id, band_number, from_days_before, every_days) "
                    "VALUES (:setting_id, :number, :from_days_before, :every_days)"
                ),
                {"setting_id": setting_id, "number": number, "from_days_before": from_days_before, "every_days": every_days},
            )
        for number, (role_code, starts_code, from_days_before) in enumerate(steps, 1):
            connection.execute(
                sa.text(
                    f"INSERT INTO {STEP_TABLE} (setting_id, step_number, role_code, starts_code, from_days_before, channel_codes) "
                    "VALUES (:setting_id, :number, :role_code, :starts_code, :from_days_before, ARRAY['SCREEN']::varchar[])"
                ),
                {
                    "setting_id": setting_id,
                    "number": number,
                    "role_code": role_code,
                    "starts_code": starts_code,
                    "from_days_before": from_days_before,
                },
            )


def downgrade() -> None:
    """Remove the four tables. Nothing else changed."""
    op.drop_index("ix_eligibility_alert_acknowledgement_subject", table_name=SEEN_TABLE)
    op.drop_index("ix_eligibility_alert_acknowledgement_asset", table_name=SEEN_TABLE)
    for table in (SEEN_TABLE, STEP_TABLE, BAND_TABLE, SETTING_TABLE):
        op.drop_table(table)
