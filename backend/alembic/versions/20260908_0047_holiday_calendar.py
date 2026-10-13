"""PBL's holiday calendar, and each Work Order's changes to it (HOL-1)

Design: docs/agent/slices/hol-1-holiday-calendar.md (agreed by the owner, 2 October 2026), sections 5 and 10.

1. **The calendar** - a new module's three tables:

   - `holiday_calendar_year`: one row per year Admin has started, with its version and the "complete" mark. No row
     means the year is not started; a row without the mark means it is being entered (1.2, point 1).
   - `holiday_calendar_holiday`: one holiday of a year - its date, kind (national or festival), name, and whether
     it applies to all of India or to the states named. The kind does not decide where it applies: a state may count
     its own day among its national holidays, as Maharashtra does 1 May (1.2, point 2).
   - `holiday_calendar_holiday_state`: the states a holiday names, each a key to ELG-1's list of states and union
     territories (`eligibility_jurisdiction`), never the central government's own sites (`IN`).

   A date is never a holiday twice for one state: one all-India holiday per date (a partial unique index) and one
   holiday per state per date (a unique key) here; that an all-India holiday and a state's own are not on the same
   date, and that "these states" names at least one, are rules across rows the service owns under its lock.

2. **The Work Order's changes** (Slice 7D Part 4's two tables, reworded and extended - Q4):

   - the answer `NONE` ("names no holidays") becomes `CALENDAR_UNCHANGED` ("follows PBL's calendar unchanged") and
     `LISTED` becomes `CALENDAR_CHANGED` ("changes PBL's calendar as listed");
   - each listed date becomes a change: `HOLIDAY_ADDED` (every date already listed, with its kind) or
     `WORKING_DAY` - a calendar holiday the Work Order works, charged at the normal or the overtime rate, with no
     kind of its own.

3. **Two permissions**: reading the calendar (the six roles) and keeping it (Admin).

4. **The reminder for a year not set up** (Q2): a fifth kind of reminder in ELG-2's settings and "seen" marks. A
   "seen" mark on it is about a year, not a machine, so the asset and certificate kind are empty for it - and only
   for it - and its key still names exactly the reminder it marks. Version 1 of its setting: the standard schedule,
   counted to 1 January of the year; Admin from the first reminder, Management from 1 January.

Each CHECK is TRUE or FALSE when a column it reads is empty - `NULL IN (...)` is NULL, and a CHECK passes on NULL
(the Slice 7D Part 3 lesson) - so empty values are wrapped in COALESCE or CASE.

Spells out every value rather than importing them, so this revision stays a frozen historical snapshot (the
20260908_0033 to 0046 convention).

Downgrade removes the calendar and its permissions, the fifth reminder's settings and "seen" marks, and every
working day a Work Order listed - which did not exist before - and puts the codes and columns back.

Revision ID: 20260908_0047
Revises: 20260908_0046
Create Date: 2026-10-02
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0047"
down_revision: Union[str, None] = "20260908_0046"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


YEAR_TABLE = "holiday_calendar_year"
HOLIDAY_TABLE = "holiday_calendar_holiday"
STATE_TABLE = "holiday_calendar_holiday_state"
JURISDICTION_TABLE = "eligibility_jurisdiction"
USER_TABLE = "app_user"

WO_LIST_TABLE = "crm_work_order_holiday_list"
WO_HOLIDAY_TABLE = "crm_work_order_holiday"

SETTING_TABLE = "eligibility_alert_setting"
BAND_TABLE = "eligibility_alert_band"
STEP_TABLE = "eligibility_alert_step"
SEEN_TABLE = "eligibility_alert_acknowledgement"

FIRST_YEAR, LAST_YEAR = 2000, 2100
NAME_MAX_LENGTH = 255

CALENDAR_REMINDER = "HOLIDAY_CALENDAR_NOT_SET_UP"
CALENDAR_SUBJECT = "holiday_calendar_year"
CERTIFICATE_REMINDERS = ("CERTIFICATE_RUNNING_OUT", "NOT_YET_RECORDED", "BEFORE_JOB_STARTS", "DURING_JOB")
CERTIFICATE_SUBJECTS = ("asset", "resource_assignment", "resource_assignment_kit")
# Q2: the certificate reminders' standard schedule (60 and 30 days before, weekly from 15, daily from 7, every day from
# the date), counted to 1 January; Admin from the first reminder, Management from 1 January.
CALENDAR_SCHEDULE = ((60, 30), (15, 7), (7, 1), (0, 1))
CALENDAR_PATH = (("ADMIN", "FIRST_REMINDER", None), ("MANAGEMENT_READ_ONLY", "DAYS_BEFORE", 0))

ALL_ROLES = ("ADMIN", "SALES_USER", "SALES_MANAGER", "FINANCE_USER", "OPERATIONS_USER", "MANAGEMENT_READ_ONLY")
PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    "HOLIDAY_CALENDAR_READ": ("View PBL's holiday calendar, year by year.", ALL_ROLES),
    # Admin until a position is mapped under ORA-001 (owner, 2 October 2026); a grant, with no code change.
    "HOLIDAY_CALENDAR_MANAGE": (
        "Enter and change PBL's holiday calendar for a year, and mark a year complete.",
        ("ADMIN",),
    ),
}


def _codes(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    _create_calendar()
    _change_work_order_holidays()
    _seed_permissions()
    _add_calendar_reminder()


# --- 1. The calendar ---------------------------------------------------------------------------------------------


def _create_calendar() -> None:
    op.create_table(
        YEAR_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year_public_id", sa.String(length=36), nullable=False),
        sa.Column("calendar_year", sa.Integer(), nullable=False),
        sa.Column("year_version", sa.Integer(), nullable=False),
        # Admin's mark that the year is complete: both or neither (1.2, point 1).
        sa.Column("complete_marked_by", sa.String(length=36), nullable=True),
        sa.Column("complete_marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("year_public_id", name="uq_holiday_calendar_year_public_id"),
        sa.UniqueConstraint("calendar_year", name="uq_holiday_calendar_year"),
        # The key a holiday's year and date are checked against.
        sa.UniqueConstraint("id", "calendar_year", name="uq_holiday_calendar_year_id_year"),
        sa.ForeignKeyConstraint(["complete_marked_by"], [f"{USER_TABLE}.public_id"], name="fk_holiday_calendar_year_marked_by"),
        sa.ForeignKeyConstraint(["created_by"], [f"{USER_TABLE}.public_id"], name="fk_holiday_calendar_year_created_by"),
        sa.ForeignKeyConstraint(["updated_by"], [f"{USER_TABLE}.public_id"], name="fk_holiday_calendar_year_updated_by"),
        sa.CheckConstraint(f"calendar_year BETWEEN {FIRST_YEAR} AND {LAST_YEAR}", name="ck_holiday_calendar_year_range"),
        sa.CheckConstraint("year_version >= 1", name="ck_holiday_calendar_year_version"),
        sa.CheckConstraint(
            "(complete_marked_by IS NULL) = (complete_marked_at IS NULL)", name="ck_holiday_calendar_year_complete_mark"
        ),
    )
    op.create_table(
        HOLIDAY_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("holiday_public_id", sa.String(length=36), nullable=False),
        sa.Column("year_id", sa.Integer(), nullable=False),
        sa.Column("calendar_year", sa.Integer(), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("holiday_kind_code", sa.String(length=20), nullable=False),
        sa.Column("holiday_name", sa.Unicode(length=NAME_MAX_LENGTH), nullable=False),
        sa.Column("applies_to_code", sa.String(length=20), nullable=False),
        sa.UniqueConstraint("holiday_public_id", name="uq_holiday_calendar_holiday_public_id"),
        # The key a state row's holiday and date are checked against.
        sa.UniqueConstraint("id", "holiday_date", name="uq_holiday_calendar_holiday_id_date"),
        sa.ForeignKeyConstraint(
            ["year_id", "calendar_year"],
            [f"{YEAR_TABLE}.id", f"{YEAR_TABLE}.calendar_year"],
            name="fk_holiday_calendar_holiday_year",
        ),
        sa.CheckConstraint(
            "EXTRACT(YEAR FROM holiday_date) = calendar_year", name="ck_holiday_calendar_holiday_in_year"
        ),
        sa.CheckConstraint("holiday_kind_code IN ('NATIONAL', 'FESTIVAL')", name="ck_holiday_calendar_holiday_kind"),
        sa.CheckConstraint(
            f"btrim(holiday_name) <> '' AND char_length(holiday_name) <= {NAME_MAX_LENGTH}",
            name="ck_holiday_calendar_holiday_name",
        ),
        sa.CheckConstraint("applies_to_code IN ('ALL_INDIA', 'STATES')", name="ck_holiday_calendar_holiday_applies_to"),
    )
    op.create_index("ix_holiday_calendar_holiday_year", HOLIDAY_TABLE, ["year_id"])
    op.create_index("ix_holiday_calendar_holiday_date", HOLIDAY_TABLE, ["holiday_date"])
    # One all-India holiday on a date.
    op.create_index(
        "uq_holiday_calendar_holiday_all_india_date",
        HOLIDAY_TABLE,
        ["holiday_date"],
        unique=True,
        postgresql_where=sa.text("applies_to_code = 'ALL_INDIA'"),
    )
    op.create_table(
        STATE_TABLE,
        sa.Column("holiday_id", sa.Integer(), nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("jurisdiction_code", sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint("holiday_id", "jurisdiction_code", name="pk_holiday_calendar_holiday_state"),
        # One holiday for a state on a date.
        sa.UniqueConstraint("holiday_date", "jurisdiction_code", name="uq_holiday_calendar_holiday_state_date"),
        sa.ForeignKeyConstraint(
            ["holiday_id", "holiday_date"],
            [f"{HOLIDAY_TABLE}.id", f"{HOLIDAY_TABLE}.holiday_date"],
            name="fk_holiday_calendar_holiday_state_holiday",
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_code"],
            [f"{JURISDICTION_TABLE}.jurisdiction_code"],
            name="fk_holiday_calendar_holiday_state_jurisdiction",
        ),
        # A state or union territory: the central government's own sites are not a place with holidays of their own.
        sa.CheckConstraint("jurisdiction_code <> 'IN'", name="ck_holiday_calendar_holiday_state_not_central"),
    )


# --- 2. The Work Order's changes ---------------------------------------------------------------------------------


def _change_work_order_holidays() -> None:
    connection = op.get_bind()
    op.drop_constraint("ck_wo_holiday_list_answer", WO_LIST_TABLE, type_="check")
    connection.execute(
        sa.text(
            f"UPDATE {WO_LIST_TABLE} SET holidays_answer_code = CASE holidays_answer_code "
            "WHEN 'NONE' THEN 'CALENDAR_UNCHANGED' WHEN 'LISTED' THEN 'CALENDAR_CHANGED' ELSE holidays_answer_code END"
        )
    )
    op.create_check_constraint(
        "ck_wo_holiday_list_answer", WO_LIST_TABLE, "holidays_answer_code IN ('CALENDAR_UNCHANGED', 'CALENDAR_CHANGED')"
    )

    # Every date already listed is a holiday the Work Order added (1.2, point 11). The default fills them, then goes:
    # every later row says which change it is.
    op.add_column(
        WO_HOLIDAY_TABLE,
        sa.Column("change_code", sa.String(length=30), nullable=False, server_default=sa.text("'HOLIDAY_ADDED'")),
    )
    op.alter_column(WO_HOLIDAY_TABLE, "change_code", server_default=None)
    op.add_column(WO_HOLIDAY_TABLE, sa.Column("working_day_rate_code", sa.String(length=30), nullable=True))
    op.alter_column(WO_HOLIDAY_TABLE, "holiday_kind_code", existing_type=sa.String(length=50), nullable=True)
    op.drop_constraint("ck_wo_holiday_kind", WO_HOLIDAY_TABLE, type_="check")
    op.create_check_constraint(
        "ck_wo_holiday_change", WO_HOLIDAY_TABLE, "change_code IN ('HOLIDAY_ADDED', 'WORKING_DAY')"
    )
    # A holiday added has its kind; a working day has none of its own - it is a calendar holiday's.
    op.create_check_constraint(
        "ck_wo_holiday_kind",
        WO_HOLIDAY_TABLE,
        "CASE WHEN change_code = 'HOLIDAY_ADDED' THEN COALESCE(holiday_kind_code, '') IN ('NATIONAL', 'FESTIVAL') "
        "ELSE holiday_kind_code IS NULL END",
    )
    # A working day is charged at the normal or the overtime rate (Q4); a holiday added has no rate of its own - it is
    # charged by each line's off-day term (answer 24).
    op.create_check_constraint(
        "ck_wo_holiday_working_day_rate",
        WO_HOLIDAY_TABLE,
        "CASE WHEN change_code = 'WORKING_DAY' THEN COALESCE(working_day_rate_code, '') IN ('NORMAL_RATE', 'OVERTIME_RATE') "
        "ELSE working_day_rate_code IS NULL END",
    )


# --- 3. Permissions ------------------------------------------------------------------------------------------------


def _seed_permissions() -> None:
    """Insert each permission row and its role grants, as 20260908_0036 to 0046 do."""
    connection = op.get_bind()
    for permission_code, (description, granted_role_codes) in PERMISSION_SEED.items():
        connection.execute(
            sa.text(
                """
                INSERT INTO authz_permission (public_id, permission_code, description, is_active)
                VALUES (:public_id, :permission_code, :description, TRUE)
                """
            ),
            {"public_id": str(uuid4()), "permission_code": permission_code, "description": description},
        )
        permission_id = connection.execute(
            sa.text("SELECT id FROM authz_permission WHERE permission_code = :permission_code"),
            {"permission_code": permission_code},
        ).scalar_one()
        for role_code in granted_role_codes:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO authz_role_permission (public_id, role_code, permission_id, is_active)
                    VALUES (:public_id, :role_code, :permission_id, TRUE)
                    """
                ),
                {"public_id": str(uuid4()), "role_code": role_code, "permission_id": permission_id},
            )


# --- 4. The reminder for a year not set up -----------------------------------------------------------------------


# The whole key, exactly: its six parts joined by "|", and nothing more. Comparing part by part, as 0046 did, let a key
# with a trailing "|" - or "||" and more - through, since an empty seventh part reads the same as none (independent
# review, HOL1-R2-002); such a key could sit beside the real one under the unique index, unseen by every read. Every
# column it reads is NOT NULL but the two a year's mark leaves empty, which COALESCE reads as "".
SEEN_KEY_CHECK = (
    "reminder_key = reminder_kind_code || '|' || subject_type || '|' || subject_public_id || '|' "
    "|| COALESCE(equipment_asset_public_id, '') || '|' || COALESCE(kind_code, '') || '|' "
    "|| to_char(reminder_date_on, 'YYYY-MM-DD')"
)

# 0046's check, word for word: the downgrade puts revision 0046 back as it was.
SEEN_KEY_CHECK_0046 = (
    "split_part(reminder_key, '|', 1) = reminder_kind_code "
    "AND split_part(reminder_key, '|', 2) = subject_type "
    "AND split_part(reminder_key, '|', 3) = subject_public_id "
    "AND split_part(reminder_key, '|', 4) = equipment_asset_public_id "
    "AND split_part(reminder_key, '|', 5) = kind_code "
    "AND split_part(reminder_key, '|', 6) = to_char(reminder_date_on, 'YYYY-MM-DD') "
    "AND split_part(reminder_key, '|', 7) = ''"
)


def _add_calendar_reminder() -> None:
    kinds = (*CERTIFICATE_REMINDERS, CALENDAR_REMINDER)
    subjects = (*CERTIFICATE_SUBJECTS, CALENDAR_SUBJECT)
    op.drop_constraint("ck_eligibility_alert_setting_kind", SETTING_TABLE, type_="check")
    op.create_check_constraint("ck_eligibility_alert_setting_kind", SETTING_TABLE, f"reminder_kind_code IN ({_codes(kinds)})")

    op.drop_constraint("ck_eligibility_alert_acknowledgement_kind", SEEN_TABLE, type_="check")
    op.create_check_constraint(
        "ck_eligibility_alert_acknowledgement_kind", SEEN_TABLE, f"reminder_kind_code IN ({_codes(kinds)})"
    )
    op.drop_constraint("ck_eligibility_alert_acknowledgement_subject", SEEN_TABLE, type_="check")
    op.create_check_constraint(
        "ck_eligibility_alert_acknowledgement_subject", SEEN_TABLE, f"subject_type IN ({_codes(subjects)})"
    )
    op.alter_column(SEEN_TABLE, "equipment_asset_public_id", existing_type=sa.String(length=36), nullable=True)
    op.alter_column(SEEN_TABLE, "kind_code", existing_type=sa.String(length=30), nullable=True)
    # A year's reminder is about the year alone: no asset, no certificate kind, its date 1 January of that year and the
    # year as what it is about. Every other reminder keeps both, as before.
    op.create_check_constraint(
        "ck_eligibility_alert_acknowledgement_subject_parts",
        SEEN_TABLE,
        f"CASE WHEN subject_type = '{CALENDAR_SUBJECT}' THEN "
        f"reminder_kind_code = '{CALENDAR_REMINDER}' AND equipment_asset_public_id IS NULL AND kind_code IS NULL "
        "AND subject_public_id = to_char(reminder_date_on, 'YYYY') AND to_char(reminder_date_on, 'MM-DD') = '01-01' "
        f"ELSE reminder_kind_code <> '{CALENDAR_REMINDER}' AND equipment_asset_public_id IS NOT NULL "
        "AND kind_code IS NOT NULL END",
    )
    op.drop_constraint("ck_eligibility_alert_acknowledgement_key", SEEN_TABLE, type_="check")
    op.create_check_constraint("ck_eligibility_alert_acknowledgement_key", SEEN_TABLE, SEEN_KEY_CHECK)
    _seed_calendar_setting()


def _seed_calendar_setting() -> None:
    connection = op.get_bind()
    setting_id = connection.execute(
        sa.text(
            f"INSERT INTO {SETTING_TABLE} (setting_public_id, reminder_kind_code, version_number, saved_by, saved_at) "
            "VALUES (:public_id, :kind, 1, NULL, :saved_at) RETURNING id"
        ),
        {"public_id": str(uuid4()), "kind": CALENDAR_REMINDER, "saved_at": datetime.now(timezone.utc)},
    ).scalar_one()
    for number, (from_days_before, every_days) in enumerate(CALENDAR_SCHEDULE, 1):
        connection.execute(
            sa.text(
                f"INSERT INTO {BAND_TABLE} (setting_id, band_number, from_days_before, every_days) "
                "VALUES (:setting_id, :number, :from_days_before, :every_days)"
            ),
            {"setting_id": setting_id, "number": number, "from_days_before": from_days_before, "every_days": every_days},
        )
    for number, (role_code, starts_code, from_days_before) in enumerate(CALENDAR_PATH, 1):
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


# --- Downgrade -----------------------------------------------------------------------------------------------------


def downgrade() -> None:
    connection = op.get_bind()

    # 4. The fifth reminder: its "seen" marks and every version of its setting, then the checks as they were.
    connection.execute(sa.text(f"DELETE FROM {SEEN_TABLE} WHERE reminder_kind_code = :kind"), {"kind": CALENDAR_REMINDER})
    for table in (STEP_TABLE, BAND_TABLE):
        connection.execute(
            sa.text(
                f"DELETE FROM {table} WHERE setting_id IN (SELECT id FROM {SETTING_TABLE} WHERE reminder_kind_code = :kind)"
            ),
            {"kind": CALENDAR_REMINDER},
        )
    connection.execute(sa.text(f"DELETE FROM {SETTING_TABLE} WHERE reminder_kind_code = :kind"), {"kind": CALENDAR_REMINDER})
    op.drop_constraint("ck_eligibility_alert_acknowledgement_key", SEEN_TABLE, type_="check")
    op.drop_constraint("ck_eligibility_alert_acknowledgement_subject_parts", SEEN_TABLE, type_="check")
    op.alter_column(SEEN_TABLE, "kind_code", existing_type=sa.String(length=30), nullable=False)
    op.alter_column(SEEN_TABLE, "equipment_asset_public_id", existing_type=sa.String(length=36), nullable=False)
    op.create_check_constraint("ck_eligibility_alert_acknowledgement_key", SEEN_TABLE, SEEN_KEY_CHECK_0046)
    op.drop_constraint("ck_eligibility_alert_acknowledgement_subject", SEEN_TABLE, type_="check")
    op.create_check_constraint(
        "ck_eligibility_alert_acknowledgement_subject", SEEN_TABLE, f"subject_type IN ({_codes(CERTIFICATE_SUBJECTS)})"
    )
    op.drop_constraint("ck_eligibility_alert_acknowledgement_kind", SEEN_TABLE, type_="check")
    op.create_check_constraint(
        "ck_eligibility_alert_acknowledgement_kind", SEEN_TABLE, f"reminder_kind_code IN ({_codes(CERTIFICATE_REMINDERS)})"
    )
    op.drop_constraint("ck_eligibility_alert_setting_kind", SETTING_TABLE, type_="check")
    op.create_check_constraint(
        "ck_eligibility_alert_setting_kind", SETTING_TABLE, f"reminder_kind_code IN ({_codes(CERTIFICATE_REMINDERS)})"
    )

    # 3. Permissions.
    codes = list(PERMISSION_SEED)
    connection.execute(
        sa.text(
            "DELETE FROM authz_role_permission WHERE permission_id IN "
            "(SELECT id FROM authz_permission WHERE permission_code = ANY(:codes))"
        ),
        {"codes": codes},
    )
    connection.execute(sa.text("DELETE FROM authz_permission WHERE permission_code = ANY(:codes)"), {"codes": codes})

    # 2. The Work Order's changes: working days did not exist before, so they go.
    connection.execute(sa.text(f"DELETE FROM {WO_HOLIDAY_TABLE} WHERE change_code = 'WORKING_DAY'"))
    op.drop_constraint("ck_wo_holiday_working_day_rate", WO_HOLIDAY_TABLE, type_="check")
    op.drop_constraint("ck_wo_holiday_kind", WO_HOLIDAY_TABLE, type_="check")
    op.drop_constraint("ck_wo_holiday_change", WO_HOLIDAY_TABLE, type_="check")
    op.alter_column(WO_HOLIDAY_TABLE, "holiday_kind_code", existing_type=sa.String(length=50), nullable=False)
    op.create_check_constraint("ck_wo_holiday_kind", WO_HOLIDAY_TABLE, "holiday_kind_code IN ('NATIONAL', 'FESTIVAL')")
    op.drop_column(WO_HOLIDAY_TABLE, "working_day_rate_code")
    op.drop_column(WO_HOLIDAY_TABLE, "change_code")
    op.drop_constraint("ck_wo_holiday_list_answer", WO_LIST_TABLE, type_="check")
    connection.execute(
        sa.text(
            f"UPDATE {WO_LIST_TABLE} SET holidays_answer_code = CASE holidays_answer_code "
            "WHEN 'CALENDAR_UNCHANGED' THEN 'NONE' WHEN 'CALENDAR_CHANGED' THEN 'LISTED' ELSE holidays_answer_code END"
        )
    )
    op.create_check_constraint("ck_wo_holiday_list_answer", WO_LIST_TABLE, "holidays_answer_code IN ('NONE', 'LISTED')")

    # 1. The calendar.
    op.drop_table(STATE_TABLE)
    op.drop_index("uq_holiday_calendar_holiday_all_india_date", table_name=HOLIDAY_TABLE)
    op.drop_index("ix_holiday_calendar_holiday_date", table_name=HOLIDAY_TABLE)
    op.drop_index("ix_holiday_calendar_holiday_year", table_name=HOLIDAY_TABLE)
    op.drop_table(HOLIDAY_TABLE)
    op.drop_table(YEAR_TABLE)
