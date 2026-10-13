"""equipment allocation: own machines held for resource requirements, their trips and kit (8A core)

Design: docs/agent/slices/8a-core-equipment-allocation.md (agreed by the owner, 28 September 2026), sections
5, 8 and 11. The new Resource Assignments module's tables - three designed, and the request-key registry added in
review (8A-R2-002) - and two small changes the design names:

- **`resource_assignment`** - one machine on one unit of one requirement, for a period. Before the Work Order
  is released it is HELD (Q1); REPLACED and RELEASED ("freed") end it, keeping it as history. ALLOCATED (7B)
  and COMPLETED (8E) are reserved and not accepted yet. Its busy days are a generated range, and two
  exclusion constraints refuse a machine on two allocations, or a unit filled twice, on any common day
  (`RPA-001`: the first valid commitment wins). `btree_gist` is 0044's.
- **`resource_assignment_trip`** - deliveries to site within an allocation; trip 1 goes with the machine.
- **`resource_assignment_kit`** - one piece of kit, or a count from a counted set, on a trip, with its own
  eligibility decision. A piece tracked one by one is never on two listed lines on a common day.
- **`resource_requirement`** - its status accepts PARTLY_FULFILLED and FULFILLED (WRR-001 reserved them).
- **`crm_work_order_line_detail.site_central_government`** - whether the line's site is a central-government
  site (ELG-1 Q8), nullable: empty is not answered.
- **`RESOURCE_ASSIGNMENT_READ`** and **`RESOURCE_ASSIGNMENT_WRITE`**, and their grants.

Records key on other modules' records by public id, with foreign keys, as ELG-1's do (its refinement 1).
Spells out every value rather than importing them, so this revision stays a frozen historical snapshot (the
20260908_0033 to 0044 convention).

Revision ID: 20260908_0045
Revises: 20260908_0044
Create Date: 2026-09-28
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import DATERANGE
from alembic import op

revision: str = "20260908_0045"
down_revision: Union[str, None] = "20260908_0044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ASSIGNMENT_TABLE = "resource_assignment"
TRIP_TABLE = "resource_assignment_trip"
KIT_TABLE = "resource_assignment_kit"
REQUEST_TABLE = "resource_assignment_request"
REQUIREMENT_TABLE = "resource_requirement"
LINE_DETAIL_TABLE = "crm_work_order_line_detail"
ASSET_TABLE = "equipment_asset"
DECISION_TABLE = "eligibility_decision"
USER_TABLE = "app_user"
# The transaction advisory lock every Resource Assignments write takes (resource_assignments/repository.py,
# WRITE_LOCK_KEY). Statements that write an allocation's dates, a trip or a kit line take it too, before any row
# (8A-R6-001, 8A-R7-001): two transactions writing an allocation and its trips or kit are serialized even when one
# bypasses the service, in the order the service keeps - this lock, then the rows.
WRITE_LOCK_KEY = 80_450_001

REPLACEMENT_REASONS = ("BREAKDOWN", "COMPLIANCE", "CUSTOMER_REQUEST", "PLANNING", "OTHER")
RELEASE_REASONS = ("NOT_NEEDED", "RECORDED_BY_MISTAKE", "MACHINE_UNAVAILABLE", "OTHER", "REQUIREMENT_CANCELLED")

ALL_ROLES = ("ADMIN", "SALES_USER", "SALES_MANAGER", "FINANCE_USER", "OPERATIONS_USER", "MANAGEMENT_READ_ONLY")
PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    # Reading follows who can view Work Orders; allocating is Operations and Admin, as requirements are.
    "RESOURCE_ASSIGNMENT_READ": (
        "View the machines allocated to Work Orders, and find machines for a requirement.",
        ALL_ROLES,
    ),
    "RESOURCE_ASSIGNMENT_WRITE": (
        "Allocate machines to a Work Order's requirements; replace or free them, change their dates, check them "
        "again, and list the kit going to site.",
        ("ADMIN", "OPERATIONS_USER"),
    ),
}


def _codes(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _note_check(column: str, max_length: int, name: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(
        f"{column} IS NULL OR (btrim({column}) <> '' AND char_length({column}) <= {max_length})", name=name
    )


def upgrade() -> None:
    _create_assignments()
    _create_trips()
    _create_kit()
    _kit_tracking_trigger()
    _service_writes_only()
    _serialize_statements()
    _requirement_never_changes_trigger()
    _trip_within_allocation_triggers()
    _kit_days_triggers()
    _create_requests()
    _requirement_statuses(("OPEN", "PARTLY_FULFILLED", "FULFILLED", "CANCELLED"))
    op.add_column(LINE_DETAIL_TABLE, sa.Column("site_central_government", sa.Boolean(), nullable=True))
    _seed_permissions()


def _create_assignments() -> None:
    op.create_table(
        ASSIGNMENT_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_public_id", sa.String(length=36), nullable=False),
        # AL-000001, derived from the id as RR- is. Never truncated past six digits.
        sa.Column(
            "assignment_reference",
            sa.String(length=30),
            sa.Computed("'AL-' || lpad(id::text, GREATEST(6, length(id::text)), '0')", persisted=True),
            nullable=False,
        ),
        sa.Column("resource_requirement_public_id", sa.String(length=36), nullable=False),
        # Which place of the requirement it fills: 1 .. units required.
        sa.Column("unit_number", sa.Integer(), nullable=False),
        # Copied once from the requirement: they never change.
        sa.Column("work_order_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_code", sa.Unicode(length=50), nullable=False),
        sa.Column("work_order_line_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_line_number", sa.Integer(), nullable=False),
        sa.Column("source_offer_line_public_id", sa.String(length=36), nullable=True),
        sa.Column("equipment_asset_public_id", sa.String(length=36), nullable=False),
        # The machine as allocated (RMR-001): history shows what was allocated even if it is later renumbered
        # or re-rated.
        sa.Column("allocated_machine_number", sa.Unicode(length=200), nullable=True),
        sa.Column("allocated_class_code", sa.String(length=50), nullable=False),
        sa.Column("allocated_type_code", sa.String(length=50), nullable=True),
        sa.Column("allocated_model_public_id", sa.String(length=36), nullable=True),
        sa.Column("allocated_asset_version", sa.Integer(), nullable=False),
        # A unit is one machine in Hiring; a column so Transportation's combinations fit later.
        sa.Column("units_fulfilled", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("planned_from", sa.Date(), nullable=False),
        # Empty only where nothing bounds the requirement.
        sa.Column("planned_to", sa.Date(), nullable=True),
        # The last day on the job when replaced or freed; the day before its start when it never started.
        sa.Column("ended_on", sa.Date(), nullable=True),
        # The days it keeps the machine: from its start to the earlier of its planned end and the day it ended,
        # both included; none when it ended before it started.
        sa.Column(
            "busy_range",
            DATERANGE(),
            sa.Computed(
                "CASE WHEN ended_on IS NOT NULL AND ended_on < planned_from THEN 'empty'::daterange "
                "ELSE daterange(planned_from, LEAST(planned_to, ended_on), '[]') END",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("assignment_status_code", sa.String(length=20), nullable=False),
        sa.Column("replaces_assignment_id", sa.Integer(), nullable=True),
        sa.Column("end_reason_code", sa.String(length=30), nullable=True),
        sa.Column("end_note", sa.UnicodeText(), nullable=True),
        sa.Column("ended_by", sa.String(length=36), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("billing_cycle_code", sa.String(length=20), nullable=True),
        sa.Column("billing_cycle_set_by", sa.String(length=36), nullable=True),
        sa.Column("billing_cycle_set_at", sa.DateTime(timezone=True), nullable=True),
        # The latest eligibility decision stored for it (ELA-001); every earlier one stays in Eligibility.
        sa.Column("decision_public_id", sa.String(length=36), nullable=False),
        sa.Column("notes", sa.UnicodeText(), nullable=True),
        sa.Column("assignment_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("create_request_key", sa.String(length=100), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_by", sa.String(length=36), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("assignment_public_id", name="uq_resource_assignment_public_id"),
        sa.UniqueConstraint("assignment_reference", name="uq_resource_assignment_reference"),
        sa.UniqueConstraint("create_request_key", name="uq_resource_assignment_create_request_key"),
        # At most one allocation replaces another.
        sa.UniqueConstraint("replaces_assignment_id", name="uq_resource_assignment_replaces"),
        sa.ForeignKeyConstraint(
            ["resource_requirement_public_id"],
            [f"{REQUIREMENT_TABLE}.requirement_public_id"],
            name="fk_resource_assignment_requirement",
        ),
        sa.ForeignKeyConstraint(
            ["equipment_asset_public_id"], [f"{ASSET_TABLE}.asset_public_id"], name="fk_resource_assignment_asset"
        ),
        sa.ForeignKeyConstraint(
            ["decision_public_id"], [f"{DECISION_TABLE}.decision_public_id"], name="fk_resource_assignment_decision"
        ),
        sa.ForeignKeyConstraint(["replaces_assignment_id"], [f"{ASSIGNMENT_TABLE}.id"], name="fk_resource_assignment_replaces"),
        sa.ForeignKeyConstraint(["ended_by"], [f"{USER_TABLE}.public_id"], name="fk_resource_assignment_ended_by"),
        sa.ForeignKeyConstraint(
            ["billing_cycle_set_by"], [f"{USER_TABLE}.public_id"], name="fk_resource_assignment_billing_cycle_set_by"
        ),
        sa.ForeignKeyConstraint(["created_by"], [f"{USER_TABLE}.public_id"], name="fk_resource_assignment_created_by"),
        sa.ForeignKeyConstraint(["updated_by"], [f"{USER_TABLE}.public_id"], name="fk_resource_assignment_updated_by"),
        sa.CheckConstraint("unit_number >= 1", name="ck_resource_assignment_unit"),
        sa.CheckConstraint("units_fulfilled = 1", name="ck_resource_assignment_units_fulfilled"),
        sa.CheckConstraint("allocated_asset_version >= 1", name="ck_resource_assignment_asset_version"),
        sa.CheckConstraint("assignment_version >= 1", name="ck_resource_assignment_version"),
        sa.CheckConstraint("planned_to IS NULL OR planned_to >= planned_from", name="ck_resource_assignment_dates"),
        sa.CheckConstraint(
            "assignment_status_code IN ('HELD', 'REPLACED', 'RELEASED')", name="ck_resource_assignment_status"
        ),
        # The end fields are present exactly when it has ended. CASE, not OR: a CHECK rejects only on FALSE.
        sa.CheckConstraint(
            "CASE WHEN assignment_status_code IN ('REPLACED', 'RELEASED') THEN ended_on IS NOT NULL "
            "AND end_reason_code IS NOT NULL AND ended_by IS NOT NULL AND ended_at IS NOT NULL "
            "ELSE ended_on IS NULL AND end_reason_code IS NULL AND end_note IS NULL AND ended_by IS NULL "
            "AND ended_at IS NULL END",
            name="ck_resource_assignment_end",
        ),
        sa.CheckConstraint(
            "CASE assignment_status_code "
            f"WHEN 'REPLACED' THEN end_reason_code IN ({_codes(REPLACEMENT_REASONS)}) "
            f"WHEN 'RELEASED' THEN end_reason_code IN ({_codes(RELEASE_REASONS)}) "
            "ELSE TRUE END",
            name="ck_resource_assignment_end_reason",
        ),
        sa.CheckConstraint(
            "end_reason_code IS DISTINCT FROM 'OTHER' OR end_note IS NOT NULL", name="ck_resource_assignment_other_note"
        ),
        # It ends within its days, or the day before its start when it never started.
        sa.CheckConstraint(
            "ended_on IS NULL OR (ended_on >= planned_from - 1 AND (planned_to IS NULL OR ended_on <= planned_to))",
            name="ck_resource_assignment_ended_on",
        ),
        # Only a replacement replaces.
        sa.CheckConstraint(
            "replaces_assignment_id IS NULL OR replaces_assignment_id <> id", name="ck_resource_assignment_replaces_self"
        ),
        sa.CheckConstraint(
            "billing_cycle_code IS NULL OR billing_cycle_code IN ('WEEKLY', 'MONTHLY')",
            name="ck_resource_assignment_billing_cycle",
        ),
        _note_check("end_note", 2000, "ck_resource_assignment_end_note"),
        _note_check("notes", 2000, "ck_resource_assignment_notes"),
        sa.CheckConstraint(
            "btrim(create_request_key) <> ''", name="ck_resource_assignment_create_request_key"
        ),
    )
    # A machine is never on two allocations on a common day, and a unit is never filled twice on one: the first
    # valid commitment wins (RPA-001). Days an allocation actually held stay in the history; an empty range
    # overlaps nothing.
    op.execute(
        f"""
        ALTER TABLE {ASSIGNMENT_TABLE} ADD CONSTRAINT ex_resource_assignment_machine_overlap EXCLUDE USING gist (
            equipment_asset_public_id WITH =,
            busy_range WITH &&
        )
        """
    )
    op.execute(
        f"""
        ALTER TABLE {ASSIGNMENT_TABLE} ADD CONSTRAINT ex_resource_assignment_unit_overlap EXCLUDE USING gist (
            resource_requirement_public_id WITH =,
            unit_number WITH =,
            busy_range WITH &&
        )
        """
    )
    for index_name, columns in (
        ("ix_resource_assignment_requirement", ["resource_requirement_public_id"]),
        ("ix_resource_assignment_work_order", ["work_order_public_id"]),
        ("ix_resource_assignment_asset", ["equipment_asset_public_id"]),
        ("ix_resource_assignment_status_start", ["assignment_status_code", "planned_from"]),
    ):
        op.create_index(index_name, ASSIGNMENT_TABLE, columns)


def _create_trips() -> None:
    op.create_table(
        TRIP_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trip_public_id", sa.String(length=36), nullable=False),
        sa.Column("resource_assignment_id", sa.Integer(), nullable=False),
        sa.Column("trip_number", sa.Integer(), nullable=False),
        # Empty for trip 1, which goes with the machine on the allocation's first day.
        sa.Column("goes_on", sa.Date(), nullable=True),
        sa.Column("note", sa.Unicode(length=500), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("trip_public_id", name="uq_resource_assignment_trip_public_id"),
        sa.UniqueConstraint("resource_assignment_id", "trip_number", name="uq_resource_assignment_trip_number"),
        # What a kit line's composite foreign key names, so its trip is a trip of its own allocation.
        sa.UniqueConstraint("id", "resource_assignment_id", name="uq_resource_assignment_trip_assignment"),
        sa.ForeignKeyConstraint(
            ["resource_assignment_id"], [f"{ASSIGNMENT_TABLE}.id"], name="fk_resource_assignment_trip_assignment"
        ),
        sa.ForeignKeyConstraint(["created_by"], [f"{USER_TABLE}.public_id"], name="fk_resource_assignment_trip_created_by"),
        sa.CheckConstraint("trip_number >= 1", name="ck_resource_assignment_trip_number"),
        sa.CheckConstraint("(trip_number = 1) = (goes_on IS NULL)", name="ck_resource_assignment_trip_goes_on"),
        _note_check("note", 500, "ck_resource_assignment_trip_note"),
    )


def _create_kit() -> None:
    op.create_table(
        KIT_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kit_line_public_id", sa.String(length=36), nullable=False),
        sa.Column("resource_assignment_id", sa.Integer(), nullable=False),
        sa.Column("resource_assignment_trip_id", sa.Integer(), nullable=False),
        sa.Column("equipment_asset_public_id", sa.String(length=36), nullable=False),
        # As listed: the piece's kit model, and how its kind is tracked (ERT-2).
        sa.Column("listed_kit_model_public_id", sa.String(length=36), nullable=True),
        sa.Column("tracking_code", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_status_code", sa.String(length=20), nullable=False, server_default=sa.text("'LISTED'")),
        sa.Column("removed_by", sa.String(length=36), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_public_id", sa.String(length=36), nullable=False),
        # The trip's day to the allocation's end, kept in step with the allocation.
        sa.Column("busy_from", sa.Date(), nullable=False),
        sa.Column("busy_to", sa.Date(), nullable=True),
        sa.Column(
            "busy_range",
            DATERANGE(),
            sa.Computed(
                "CASE WHEN busy_to IS NOT NULL AND busy_to < busy_from THEN 'empty'::daterange "
                "ELSE daterange(busy_from, busy_to, '[]') END",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("create_request_key", sa.String(length=100), nullable=False),
        sa.Column("create_request_position", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("kit_line_public_id", name="uq_resource_assignment_kit_public_id"),
        sa.UniqueConstraint(
            "create_request_key", "create_request_position", name="uq_resource_assignment_kit_create_request"
        ),
        sa.ForeignKeyConstraint(
            ["resource_assignment_id"], [f"{ASSIGNMENT_TABLE}.id"], name="fk_resource_assignment_kit_assignment"
        ),
        sa.ForeignKeyConstraint(
            ["resource_assignment_trip_id", "resource_assignment_id"],
            [f"{TRIP_TABLE}.id", f"{TRIP_TABLE}.resource_assignment_id"],
            name="fk_resource_assignment_kit_trip",
        ),
        sa.ForeignKeyConstraint(
            ["equipment_asset_public_id"], [f"{ASSET_TABLE}.asset_public_id"], name="fk_resource_assignment_kit_asset"
        ),
        sa.ForeignKeyConstraint(
            ["decision_public_id"], [f"{DECISION_TABLE}.decision_public_id"], name="fk_resource_assignment_kit_decision"
        ),
        sa.ForeignKeyConstraint(["removed_by"], [f"{USER_TABLE}.public_id"], name="fk_resource_assignment_kit_removed_by"),
        sa.ForeignKeyConstraint(["created_by"], [f"{USER_TABLE}.public_id"], name="fk_resource_assignment_kit_created_by"),
        sa.CheckConstraint("tracking_code IN ('SINGLE', 'COUNTED')", name="ck_resource_assignment_kit_tracking"),
        # A piece tracked one by one is one piece; a counted set gives how many of it go.
        sa.CheckConstraint(
            "quantity >= 1 AND (tracking_code = 'COUNTED' OR quantity = 1)", name="ck_resource_assignment_kit_quantity"
        ),
        sa.CheckConstraint("line_status_code IN ('LISTED', 'REMOVED')", name="ck_resource_assignment_kit_status"),
        sa.CheckConstraint(
            "CASE WHEN line_status_code = 'REMOVED' THEN removed_by IS NOT NULL AND removed_at IS NOT NULL "
            "ELSE removed_by IS NULL AND removed_at IS NULL END",
            name="ck_resource_assignment_kit_removed",
        ),
        sa.CheckConstraint("create_request_position >= 1", name="ck_resource_assignment_kit_position"),
        sa.CheckConstraint("btrim(create_request_key) <> ''", name="ck_resource_assignment_kit_create_request_key"),
    )
    # A piece tracked one by one is never on two listed lines on a common day. A counted set's lines may
    # overlap; the service keeps their total within the set's quantity.
    op.execute(
        f"""
        ALTER TABLE {KIT_TABLE} ADD CONSTRAINT ex_resource_assignment_kit_piece_overlap EXCLUDE USING gist (
            equipment_asset_public_id WITH =,
            busy_range WITH &&
        ) WHERE (line_status_code = 'LISTED' AND tracking_code = 'SINGLE')
        """
    )
    op.create_index("ix_resource_assignment_kit_assignment", KIT_TABLE, ["resource_assignment_id"])
    op.create_index("ix_resource_assignment_kit_asset", KIT_TABLE, ["equipment_asset_public_id"])


def _kit_tracking_trigger() -> None:
    """A kit line's tracking is its piece's class's (8A-R3-005): the exclusion constraint on pieces tracked one by one
    reads the line's own column, so the database holds that column true. ERT-2's triggers keep a class's tracking
    from changing under its pieces, so a line stays true after it is written."""
    op.execute(
        """
        CREATE FUNCTION resource_assignment_kit_matches_tracking() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        DECLARE
            tracking varchar(20);
        BEGIN
            SELECT c.tracking_code INTO tracking
            FROM equipment_asset a INNER JOIN equipment_class c ON c.class_code = a.class_code
            WHERE a.asset_public_id = NEW.equipment_asset_public_id;
            IF tracking IS DISTINCT FROM NEW.tracking_code THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_resource_assignment_kit_matches_tracking',
                    MESSAGE = 'A kit line carries its piece''s tracking: ' || COALESCE(tracking, 'none') || '.';
            END IF;
            RETURN NEW;
        END
        $body$
        """
    )
    op.execute(
        """
        CREATE TRIGGER resource_assignment_kit_matches_tracking
        BEFORE INSERT OR UPDATE OF equipment_asset_public_id, tracking_code ON resource_assignment_kit
        FOR EACH ROW EXECUTE FUNCTION resource_assignment_kit_matches_tracking()
        """
    )


# The transaction-local setting the Resource Assignments service sets before it writes an allocation
# (resource_assignments/repository.py, SERVICE_WRITE_SETTING).
SERVICE_WRITE_SETTING = "pbl.resource_assignment_writer"


def _service_writes_only() -> None:
    """An allocation is added, changed or removed only in a transaction the Resource Assignments service marks
    (independent review, 8A-FA2-001): the service keeps the requirement's stored status in step in the same
    transaction, which a statement written around it would not - leaving a requirement "allocated" with a day
    uncovered. A statement-level BEFORE trigger, named to run before the lock trigger, so a statement refused here
    waits for nothing and locks no row. The mark is a transaction-local setting (`set_config(..., true)`), gone at
    commit or rollback."""
    op.execute(
        f"""
        CREATE FUNCTION resource_assignment_guard() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        BEGIN
            IF COALESCE(current_setting('{SERVICE_WRITE_SETTING}', true), '') <> 'service' THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_resource_assignment_written_by_the_service',
                    MESSAGE = 'An allocation is written only by the Resource Assignments service, which keeps its '
                        || 'requirement''s status in step.';
            END IF;
            RETURN NULL;
        END
        $body$
        """
    )
    op.execute(
        f"CREATE TRIGGER resource_assignment_guard BEFORE INSERT OR UPDATE OR DELETE ON {ASSIGNMENT_TABLE} "
        "FOR EACH STATEMENT EXECUTE FUNCTION resource_assignment_guard()"
    )


def _serialize_statements() -> None:
    """Take the module's lock at the start of every statement that changes or removes an allocation, or adds, changes
    or removes a trip or a kit line - every column (8A-R7-001, R8-001, R9-002). A statement-level BEFORE trigger runs
    before PostgreSQL locks any target row, so a direct statement waits for a service write holding the lock without
    having taken a row the service is about to lock: the service's own order, the lock then the rows. Adding an
    allocation takes no part (8A-R9-001): it reads no other table's dates - the exclusion constraints decide overlaps,
    safely under concurrency - and its foreign keys lock the requirement's row, which the service takes before this
    lock; taking the lock first would invert that. An allocation's requirement never changes (below), so no update
    reaches for the requirement's row after the lock either."""
    op.execute(
        f"""
        CREATE FUNCTION resource_assignment_serialize() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        BEGIN
            PERFORM pg_advisory_xact_lock({WRITE_LOCK_KEY});
            RETURN NULL;
        END
        $body$
        """
    )
    for name, events, table in (
        ("resource_assignment_serialize_allocation", "UPDATE OR DELETE", ASSIGNMENT_TABLE),
        ("resource_assignment_serialize_trip", "INSERT OR UPDATE OR DELETE", TRIP_TABLE),
        ("resource_assignment_serialize_kit", "INSERT OR UPDATE OR DELETE", KIT_TABLE),
    ):
        op.execute(
            f"CREATE TRIGGER {name} BEFORE {events} ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION resource_assignment_serialize()"
        )


def _requirement_never_changes_trigger() -> None:
    """The requirement an allocation fills never changes (design section 5.3): refused before the foreign key would
    lock the other requirement's row after the module's lock (8A-R9-001)."""
    op.execute(
        """
        CREATE FUNCTION resource_assignment_keeps_its_requirement() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        BEGIN
            IF NEW.resource_requirement_public_id IS DISTINCT FROM OLD.resource_requirement_public_id THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_resource_assignment_keeps_its_requirement',
                    MESSAGE = 'The requirement an allocation fills never changes.';
            END IF;
            RETURN NEW;
        END
        $body$
        """
    )
    op.execute(
        """
        CREATE TRIGGER resource_assignment_keeps_its_requirement
        BEFORE UPDATE OF resource_requirement_public_id ON resource_assignment
        FOR EACH ROW EXECUTE FUNCTION resource_assignment_keeps_its_requirement()
        """
    )


def _trip_within_allocation_triggers() -> None:
    """A later trip goes on a day of its allocation's planned period (8A-R5-001), so the kit days derived from it are
    never longer than the allocation's: a trip written, or moved, outside the period is refused, and so is a change
    to the period that would leave one outside. The day an allocation ended is not its planned period: replacing or
    freeing it early cuts a later trip's kit to no days, which is the history, not an error."""
    op.execute(
        f"""
        CREATE FUNCTION resource_assignment_trip_within_allocation() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        DECLARE
            first_day date;
            last_day date;
        BEGIN
            IF TG_TABLE_NAME = 'resource_assignment_trip' THEN
                IF NEW.goes_on IS NULL THEN
                    RETURN NEW;
                END IF;
                SELECT planned_from, planned_to INTO first_day, last_day
                FROM resource_assignment WHERE id = NEW.resource_assignment_id;
                IF NEW.goes_on < first_day OR (last_day IS NOT NULL AND NEW.goes_on > last_day) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = 'check_violation',
                        CONSTRAINT = 'ck_resource_assignment_trip_within_allocation',
                        MESSAGE = 'A later trip goes on a day of its allocation''s planned period.';
                END IF;
            ELSIF EXISTS (
                SELECT 1 FROM resource_assignment_trip t
                WHERE t.resource_assignment_id = NEW.id AND t.goes_on IS NOT NULL
                  AND (t.goes_on < NEW.planned_from OR (NEW.planned_to IS NOT NULL AND t.goes_on > NEW.planned_to))
            ) THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_resource_assignment_trip_within_allocation',
                    MESSAGE = 'An allocation''s planned period keeps every later trip within it.';
            END IF;
            RETURN NEW;
        END
        $body$
        """
    )
    op.execute(
        """
        CREATE TRIGGER resource_assignment_trip_within_allocation
        BEFORE INSERT OR UPDATE OF goes_on, resource_assignment_id ON resource_assignment_trip
        FOR EACH ROW EXECUTE FUNCTION resource_assignment_trip_within_allocation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER resource_assignment_period_keeps_trips
        BEFORE UPDATE OF planned_from, planned_to ON resource_assignment
        FOR EACH ROW EXECUTE FUNCTION resource_assignment_trip_within_allocation()
        """
    )


def _kit_days_triggers() -> None:
    """A kit line's days are its trip's day (trip 1: the allocation's first) to its allocation's end, derived here
    whatever a write sends (8A-R4-003): the exclusion constraint on pieces tracked one by one reads them, so they
    cannot be written untrue. A change to an allocation's dates or end, or to a trip's day, moves its lines with it
    in the same statement."""
    op.execute(
        f"""
        CREATE FUNCTION resource_assignment_kit_days() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        DECLARE
            trip_day date;
            first_day date;
            last_day date;
            ended date;
        BEGIN
            SELECT t.goes_on, a.planned_from, a.planned_to, a.ended_on INTO trip_day, first_day, last_day, ended
            FROM resource_assignment_trip t INNER JOIN resource_assignment a ON a.id = t.resource_assignment_id
            WHERE t.id = NEW.resource_assignment_trip_id;
            NEW.busy_from := COALESCE(trip_day, first_day);
            -- LEAST ignores an empty end: the earlier of the planned end and the day it ended, or neither.
            NEW.busy_to := LEAST(last_day, ended);
            RETURN NEW;
        END
        $body$
        """
    )
    op.execute(
        """
        CREATE TRIGGER resource_assignment_kit_days
        BEFORE INSERT OR UPDATE ON resource_assignment_kit
        FOR EACH ROW EXECUTE FUNCTION resource_assignment_kit_days()
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION resource_assignment_kit_follows() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        BEGIN
            IF TG_TABLE_NAME = 'resource_assignment' THEN
                UPDATE resource_assignment_kit SET busy_from = busy_from WHERE resource_assignment_id = NEW.id;
            ELSE
                UPDATE resource_assignment_kit SET busy_from = busy_from WHERE resource_assignment_trip_id = NEW.id;
            END IF;
            RETURN NULL;
        END
        $body$
        """
    )
    op.execute(
        """
        CREATE TRIGGER resource_assignment_kit_follows_allocation
        AFTER UPDATE OF planned_from, planned_to, ended_on ON resource_assignment
        FOR EACH ROW EXECUTE FUNCTION resource_assignment_kit_follows()
        """
    )
    op.execute(
        """
        CREATE TRIGGER resource_assignment_kit_follows_trip
        AFTER UPDATE OF goes_on ON resource_assignment_trip
        FOR EACH ROW EXECUTE FUNCTION resource_assignment_kit_follows()
        """
    )


def _create_requests() -> None:
    """Every request key used to allocate, replace or list kit, once across the three (8A-R2-002): a key is either
    the same request again - the same kind, allocation and fields sent, hashed - or refused."""
    op.create_table(
        REQUEST_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("create_request_key", sa.String(length=100), nullable=False),
        sa.Column("request_kind_code", sa.String(length=20), nullable=False),
        # The requirement the request belongs to: what the harness's cleanup finds it by, and what keeps it from
        # outliving the requirement (8A-R3-002).
        sa.Column("resource_requirement_public_id", sa.String(length=36), nullable=False),
        # The SHA-256 of the fields sent, and only those, with the allocation acted on.
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("create_request_key", name="uq_resource_assignment_request_key"),
        sa.ForeignKeyConstraint(["created_by"], [f"{USER_TABLE}.public_id"], name="fk_resource_assignment_request_created_by"),
        sa.ForeignKeyConstraint(
            ["resource_requirement_public_id"],
            [f"{REQUIREMENT_TABLE}.requirement_public_id"],
            name="fk_resource_assignment_request_requirement",
        ),
        sa.CheckConstraint("btrim(create_request_key) <> ''", name="ck_resource_assignment_request_key"),
        sa.CheckConstraint(
            f"request_kind_code IN ({_codes(('ALLOCATE', 'REPLACE', 'KIT'))})", name="ck_resource_assignment_request_kind"
        ),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_resource_assignment_request_fingerprint"
        ),
    )


def _requirement_statuses(codes: tuple[str, ...]) -> None:
    op.drop_constraint("ck_resource_requirement_status", REQUIREMENT_TABLE, type_="check")
    op.create_check_constraint(
        "ck_resource_requirement_status", REQUIREMENT_TABLE, f"requirement_status_code IN ({_codes(codes)})"
    )


def _seed_permissions() -> None:
    """Insert each permission row and its role grants, as 20260908_0036 to 0044 do."""
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


def downgrade() -> None:
    """Remove the module's tables, the column and the permissions. Requirements partly or fully allocated go back
    to OPEN, the only live status the revision below accepts. `btree_gist` stays: it is 0044's. The decisions
    stored for allocations stay in Eligibility, naming allocations that no longer exist."""
    connection = op.get_bind()
    codes = list(PERMISSION_SEED)
    connection.execute(
        sa.text(
            "DELETE FROM authz_role_permission WHERE permission_id IN "
            "(SELECT id FROM authz_permission WHERE permission_code = ANY(:codes))"
        ),
        {"codes": codes},
    )
    connection.execute(sa.text("DELETE FROM authz_permission WHERE permission_code = ANY(:codes)"), {"codes": codes})
    op.drop_column(LINE_DETAIL_TABLE, "site_central_government")
    connection.execute(
        sa.text(
            f"UPDATE {REQUIREMENT_TABLE} SET requirement_status_code = 'OPEN' "
            "WHERE requirement_status_code IN ('PARTLY_FULFILLED', 'FULFILLED')"
        )
    )
    _requirement_statuses(("OPEN", "CANCELLED"))
    for table in (REQUEST_TABLE, KIT_TABLE, TRIP_TABLE, ASSIGNMENT_TABLE):
        op.drop_table(table)
    op.execute("DROP FUNCTION resource_assignment_kit_matches_tracking()")
    op.execute("DROP FUNCTION resource_assignment_kit_days()")
    op.execute("DROP FUNCTION resource_assignment_trip_within_allocation()")
    op.execute("DROP FUNCTION resource_assignment_serialize()")
    op.execute("DROP FUNCTION resource_assignment_guard()")
    op.execute("DROP FUNCTION resource_assignment_keeps_its_requirement()")
    op.execute("DROP FUNCTION resource_assignment_kit_follows()")
