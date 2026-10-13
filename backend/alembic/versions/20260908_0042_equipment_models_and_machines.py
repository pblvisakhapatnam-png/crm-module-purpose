"""equipment models and machines, and the Plum report transformer (ERT-1)

Design: docs/agent/slices/ert-1-plum-machines-into-the-equipment-reference.md (agreed by the owner on
25 September 2026), section 12. Everything is the Equipment Reference module's; nothing here has a
`crm_` prefix, and no other module's table is touched.

**Structure, version 2.** `equipment_class.class_kind_code` says what a class is - `MACHINE` (every
version-1 class) or `PART` - and `equipment_part_fit` says which part classes may be fitted to which
machine classes. Version 2 adds one part class, **Crane carrier**, fitted to Crane and used by no business
line, so it is never offered where Operations asks for machines. This is the additive change WRR-001
recorded ("Part classes later").

**Models** - the Fleet Admin's list of makers' models: `equipment_model`, its rated capabilities
(`equipment_model_capability`), and the mapping from Plum's model names to it
(`equipment_model_source_key`).

**Assets** - one table for machines and the parts fitted to them, `equipment_asset`, with a kind of
`MACHINE` or `PART` that must be its class's kind (a composite foreign key). `EQ-000001` is generated
from the id, as `RR-` is. A machine's capabilities are read from its model; `equipment_asset_capability`
holds only the values the Fleet Admin sets for one machine, each with its reason. `equipment_asset_link`
fits a part to a machine by dated link, one open link per part, history kept. `equipment_asset_flag`
holds the data-quality flags the transformer raises.

**Adapter-owned** - `equipment_source_import` (one per uploaded report: its fingerprint, row count and
report date - never the file), `equipment_source_import_row` (only the used values of each row),
`equipment_source_binding` (which Plum machine number an asset came from, and the used values it was
last built from), `equipment_source_category_rule` (what Plum's capacity figure means in each category,
design section 6, held as data).

**The Fleet Admin's corrections** (design section 5B) - `equipment_source_value_rule` (how a Plum value
is read wherever it appears) and `equipment_asset_correction` (one machine's field).

`equipment_reference_state` is one row counting changes to anything a preview is computed from, so a
preview made before a change is refused at confirmation.

CHECK constraints are NULL-safe (CASE, never an OR chain a NULL can satisfy) and refuse NaN, the lessons
of Slice 7D and WRR-001. The trigger that checks a capability value against its kind is WRR-001's rule,
written once for the two new capability tables, which name their value columns alike.

Seeds two permissions, each granted to Admin only: `EQUIPMENT_REFERENCE_MANAGE` (owner, comment 1) and
`EQUIPMENT_IDENTITY_READ`, to see engine and chassis numbers (owner, 25 September 2026), and
spells out version 2 and the category rules rather than importing them, so this revision stays a frozen
historical snapshot (the 20260908_0033 to 0041 convention). No row of Plum's report is in it.

Revision ID: 20260908_0042
Revises: 20260908_0041
Create Date: 2026-09-25
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0042"
down_revision: Union[str, None] = "20260908_0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CLASS_TABLE = "equipment_class"
TYPE_TABLE = "equipment_type"
VERSION_TABLE = "equipment_taxonomy_version"
CLASS_CAPABILITY_TABLE = "equipment_class_capability"
ALIAS_TABLE = "equipment_term_alias"
PART_FIT_TABLE = "equipment_part_fit"
MODEL_TABLE = "equipment_model"
MODEL_CAPABILITY_TABLE = "equipment_model_capability"
MODEL_SOURCE_KEY_TABLE = "equipment_model_source_key"
IMPORT_TABLE = "equipment_source_import"
IMPORT_ROW_TABLE = "equipment_source_import_row"
ASSET_TABLE = "equipment_asset"
ASSET_CAPABILITY_TABLE = "equipment_asset_capability"
ASSET_LINK_TABLE = "equipment_asset_link"
ASSET_FLAG_TABLE = "equipment_asset_flag"
BINDING_TABLE = "equipment_source_binding"
CATEGORY_RULE_TABLE = "equipment_source_category_rule"
VALUE_RULE_TABLE = "equipment_source_value_rule"
CORRECTION_TABLE = "equipment_asset_correction"
STATE_TABLE = "equipment_reference_state"

UNIT_CODES = ("TONNE", "KILOGRAM", "METRE", "CUBIC_METRE", "KILOWATT", "KILOVOLT_AMPERE", "COUNT")
FLAG_CODES = (
    "CATEGORY_NOT_MAPPED",
    "MODEL_NOT_MAPPED",
    "CLASS_DISAGREES",
    "NOT_A_NUMBER",
    "OUT_OF_PATTERN",
    "DIFFERS_FROM_MODEL",
    "UNIT_UNCLEAR",
    "VALUE_MISSING",
    "NOT_IN_LATEST_REPORT",
    "POSSIBLY_RENUMBERED",
    "PART_NOT_FITTED",
    "DUPLICATE_SOURCE_KEY",
    "PLUM_CHANGED_CORRECTED_VALUE",
)
CORRECTION_FIELDS = (
    "CATEGORY",
    "MODEL",
    "ENGINE_NUMBER",
    "CHASSIS_NUMBER",
    "COMMENCED_YEAR",
    "OWNING_COMPANY",
    "STATUS",
    "CAPACITY",
)
VALUE_RULE_COLUMNS = ("CAPACITY", "COMMENCED_YEAR", "ENGINE_NUMBER", "CHASSIS_NUMBER", "OWNING_COMPANY")

ROLE_ADMIN = "ADMIN"
PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    # Admin only, until a Fleet Admin role exists (owner, comment 1 of 25 September 2026); that role is
    # given this permission by a grant, with no code change.
    "EQUIPMENT_REFERENCE_MANAGE": (
        "Import Plum's vehicle report and confirm it; record models and map Plum's model names to them; "
        "record how Plum's values are read and correct one machine's values; enter a machine's details and "
        "own capability values; fit parts to machines.",
        (ROLE_ADMIN,),
    ),
    # Engine and chassis numbers are confidential (owner, 25 September 2026): Admin only for now; Operations,
    # and Finance for audits, may be given it later by a grant.
    "EQUIPMENT_IDENTITY_READ": (
        "See machines' engine and chassis numbers, including in the corrections and value rules that carry them.",
        (ROLE_ADMIN,),
    ),
}

VERSION_2_LABEL = "Version 2"
VERSION_2_SOURCE = (
    "ERT-1 design, agreed 25 September 2026: the part class Crane carrier, fitted to Crane, so a crane Plum "
    "holds as a superstructure and a carrier becomes one machine with its fitted part."
)

# (plum category as the alias spells it, capability checked, Plum's unit, plausible low, plausible high,
# check code). Design section 6, "to be confirmed by the Fleet Admin"; held as data so a correction is not
# a code change. Low and high are in Plum's unit.
CATEGORY_RULES: tuple[tuple[str, str | None, str | None, int | None, int | None, str], ...] = (
    ("CRANES", "RATED_CAPACITY", "TONNE", 1, 1500, "CHECKED"),
    ("CRANE", "RATED_CAPACITY", "TONNE", 1, 1500, "CHECKED"),
    ("MAN LIFTS", "PLATFORM_CAPACITY", "KILOGRAM", 100, 1500, "CHECKED"),
    ("FORK LIFT", "RATED_CAPACITY", "TONNE", 1, 50, "CHECKED"),
    ("EXCAVATOR", None, None, None, None, "UNIT_UNCLEAR"),
    ("TRAILERS", "GROSS_COMBINATION_WEIGHT", "KILOGRAM", 10000, 500000, "CHECKED"),
    ("TRAILER BED", "PAYLOAD", "KILOGRAM", 1000, 200000, "CHECKED"),
    ("HYDRAULIC AXLES", "PAYLOAD", "KILOGRAM", 1000, 1000000, "CHECKED"),
    ("POWER PACKS", None, None, None, None, "NOT_CHECKED"),
    ("TRUCKS", "PAYLOAD", "KILOGRAM", 1000, 60000, "CHECKED"),
)


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    ]


def _normalized_column(name: str, source: str, length: int) -> sa.Column:
    """The stored form a uniqueness rule compares - whitespace collapsed, trimmed, upper case - generated
    by the database from the text it is taken from, so the two can never disagree. It is the same rule as
    ck_equipment_term_alias_normalized; the service matches in Python with contract.normalize_term."""
    return sa.Column(
        name,
        sa.Unicode(length=length),
        sa.Computed(f"upper(btrim(regexp_replace({source}, '\\s+', ' ', 'g')))", persisted=True),
        nullable=False,
    )


def _non_blank(column: str, max_length: int, name: str, *, nullable: bool) -> sa.CheckConstraint:
    present = f"btrim({column}) <> '' AND char_length({column}) <= {max_length}"
    if nullable:
        return sa.CheckConstraint(f"CASE WHEN {column} IS NULL THEN TRUE ELSE {present} END", name=name)
    return sa.CheckConstraint(present, name=name)


def _capability_value_check(name: str) -> sa.CheckConstraint:
    """One value or the other: a measured value above zero and a real number (numeric NaN orders above
    every number in PostgreSQL), or a choice from a fixed list."""
    return sa.CheckConstraint(
        "CASE WHEN capability_value IS NULL THEN choice_value IS NOT NULL AND btrim(choice_value) <> ''"
        " ELSE choice_value IS NULL AND capability_value > 0 AND capability_value <> 'NaN'::numeric"
        " END",
        name=name,
    )


def upgrade() -> None:
    _load_version_2()
    _create_model_tables()
    _create_import_tables()
    _create_asset_tables()
    _create_correction_tables()
    _create_capability_trigger()
    _seed_category_rules()
    _seed_permissions()


def _load_version_2() -> None:
    connection = op.get_bind()
    op.add_column(
        CLASS_TABLE,
        sa.Column("class_kind_code", sa.String(length=20), nullable=False, server_default=sa.text("'MACHINE'")),
    )
    op.create_check_constraint("ck_equipment_class_kind", CLASS_TABLE, "class_kind_code IN ('MACHINE', 'PART')")
    # The target of every (class, kind) foreign key: an asset's kind is always its class's kind.
    op.create_unique_constraint("uq_equipment_class_code_kind", CLASS_TABLE, ["class_code", "class_kind_code"])

    op.create_table(
        PART_FIT_TABLE,
        sa.Column("part_class_code", sa.String(length=50), nullable=False),
        # Constant columns, so the composite keys below can require a part class and a machine class.
        sa.Column("part_class_kind_code", sa.String(length=20), nullable=False, server_default=sa.text("'PART'")),
        sa.Column("parent_class_code", sa.String(length=50), nullable=False),
        sa.Column(
            "parent_class_kind_code", sa.String(length=20), nullable=False, server_default=sa.text("'MACHINE'")
        ),
        sa.Column("introduced_in_version", sa.Integer(), nullable=False),
        sa.Column("retired_in_version", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("part_class_code", "parent_class_code", name="pk_equipment_part_fit"),
        sa.ForeignKeyConstraint(
            ["part_class_code", "part_class_kind_code"],
            [f"{CLASS_TABLE}.class_code", f"{CLASS_TABLE}.class_kind_code"],
            name="fk_equipment_part_fit_part_class",
        ),
        sa.ForeignKeyConstraint(
            ["parent_class_code", "parent_class_kind_code"],
            [f"{CLASS_TABLE}.class_code", f"{CLASS_TABLE}.class_kind_code"],
            name="fk_equipment_part_fit_parent_class",
        ),
        sa.ForeignKeyConstraint(
            ["introduced_in_version"], [f"{VERSION_TABLE}.version_number"], name="fk_equipment_part_fit_introduced_version"
        ),
        sa.ForeignKeyConstraint(
            ["retired_in_version"], [f"{VERSION_TABLE}.version_number"], name="fk_equipment_part_fit_retired_version"
        ),
        sa.CheckConstraint("part_class_kind_code = 'PART'", name="ck_equipment_part_fit_part_kind"),
        sa.CheckConstraint("parent_class_kind_code = 'MACHINE'", name="ck_equipment_part_fit_parent_kind"),
        sa.CheckConstraint(
            "retired_in_version IS NULL OR retired_in_version > introduced_in_version",
            name="ck_equipment_part_fit_retired_after_introduced",
        ),
    )

    connection.execute(
        sa.text(f"INSERT INTO {VERSION_TABLE} (version_number, version_label, source_note) VALUES (2, :label, :source)"),
        {"label": VERSION_2_LABEL, "source": VERSION_2_SOURCE},
    )
    # After every version-1 class (the last is at 120). No business-line row: used by no business line.
    connection.execute(
        sa.text(
            f"INSERT INTO {CLASS_TABLE} (class_code, class_label, display_order, introduced_in_version, class_kind_code) "
            "VALUES ('CRANE_CARRIER', 'Crane carrier', 130, 2, 'PART')"
        )
    )
    connection.execute(
        sa.text(
            f"INSERT INTO {PART_FIT_TABLE} (part_class_code, parent_class_code, introduced_in_version) "
            "VALUES ('CRANE_CARRIER', 'CRANE', 2)"
        )
    )


def _create_model_tables() -> None:
    op.create_table(
        MODEL_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_public_id", sa.String(length=36), nullable=False),
        sa.Column("maker", sa.Unicode(length=100), nullable=False),
        sa.Column("model_name", sa.Unicode(length=100), nullable=False),
        # Maker and name as one key, in the stored form uniqueness compares.
        _normalized_column("normalized_key", "maker || ' ' || model_name", 210),
        sa.Column("class_code", sa.String(length=50), nullable=False),
        sa.Column("type_code", sa.String(length=50), nullable=True),
        sa.Column("model_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_retired", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        # A double-click or a retry records one model, not two (ADR-023).
        sa.Column("create_request_key", sa.String(length=36), nullable=False),
        *_audit_columns(),
        sa.UniqueConstraint("model_public_id", name="uq_equipment_model_public_id"),
        sa.UniqueConstraint("create_request_key", name="uq_equipment_model_create_request_key"),
        # One maker's model per class: a crane "DEMAG AC 200" and its carrier "DEMAG AC 200" are two models
        # of two classes, which is how the transformer pairs a carrier with its crane (design section 5).
        sa.UniqueConstraint("normalized_key", "class_code", name="uq_equipment_model_key_class"),
        # The target of the composite keys that keep an asset's or a capability's class the model's class.
        sa.UniqueConstraint("id", "class_code", name="uq_equipment_model_id_class"),
        sa.ForeignKeyConstraint(["class_code"], [f"{CLASS_TABLE}.class_code"], name="fk_equipment_model_class"),
        sa.ForeignKeyConstraint(
            ["class_code", "type_code"],
            [f"{TYPE_TABLE}.class_code", f"{TYPE_TABLE}.type_code"],
            name="fk_equipment_model_class_type",
        ),
        _non_blank("maker", 100, "ck_equipment_model_maker", nullable=False),
        _non_blank("model_name", 100, "ck_equipment_model_name", nullable=False),
        sa.CheckConstraint("model_version >= 1", name="ck_equipment_model_version"),
    )

    op.create_table(
        MODEL_CAPABILITY_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("equipment_model_id", sa.Integer(), nullable=False),
        sa.Column("class_code", sa.String(length=50), nullable=False),
        sa.Column("capability_code", sa.String(length=50), nullable=False),
        # The rated value, in the capability's own unit, which is never stored here.
        sa.Column("capability_value", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("choice_value", sa.String(length=50), nullable=True),
        sa.UniqueConstraint("equipment_model_id", "capability_code", name="uq_equipment_model_capability"),
        sa.ForeignKeyConstraint(
            ["equipment_model_id", "class_code"],
            [f"{MODEL_TABLE}.id", f"{MODEL_TABLE}.class_code"],
            name="fk_equipment_model_capability_model_class",
        ),
        # Only a capability that applies to the model's class.
        sa.ForeignKeyConstraint(
            ["class_code", "capability_code"],
            [f"{CLASS_CAPABILITY_TABLE}.class_code", f"{CLASS_CAPABILITY_TABLE}.capability_code"],
            name="fk_equipment_model_capability_class_capability",
        ),
        _capability_value_check("ck_equipment_model_capability_value"),
    )

    op.create_table(
        MODEL_SOURCE_KEY_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider_code", sa.String(length=20), nullable=False),
        # Plum's model name as the Fleet Admin mapped it, and the stored form it is matched in.
        sa.Column("source_name", sa.Unicode(length=200), nullable=False),
        _normalized_column("normalized_source_name", "source_name", 200),
        sa.Column("equipment_model_id", sa.Integer(), nullable=False),
        sa.Column("mapped_by", sa.String(length=36), nullable=True),
        sa.Column("mapped_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("provider_code", "normalized_source_name", name="uq_equipment_model_source_key"),
        sa.ForeignKeyConstraint(["equipment_model_id"], [f"{MODEL_TABLE}.id"], name="fk_equipment_model_source_key_model"),
        sa.CheckConstraint("provider_code = 'PLUM'", name="ck_equipment_model_source_key_provider"),
        _non_blank("source_name", 200, "ck_equipment_model_source_key_source_name", nullable=False),
    )
    op.create_index("ix_equipment_model_source_key_model", MODEL_SOURCE_KEY_TABLE, ["equipment_model_id"])


def _create_import_tables() -> None:
    op.create_table(
        IMPORT_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_public_id", sa.String(length=36), nullable=False),
        sa.Column("provider_code", sa.String(length=20), nullable=False),
        # SHA-256 of the uploaded file, in lower-case hex. The file itself is never kept (design Q8).
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        # The date the Fleet Admin gives the report: what every machine read says its facts are as of.
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("import_status_code", sa.String(length=20), nullable=False),
        # The confirmed import this preview was compared with. Deleting that import (only the test
        # harness's cleanup does) leaves this preview compared with nothing, which confirmation refuses.
        sa.Column("based_on_import_id", sa.Integer(), nullable=True),
        # The preview as last computed, and the change count it was computed at (equipment_reference_state).
        sa.Column("preview", postgresql.JSONB(), nullable=True),
        sa.Column("preview_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("preview_change_number", sa.BigInteger(), nullable=False),
        sa.Column("preview_computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_by", sa.String(length=36), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("published_by", sa.String(length=36), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discarded_by", sa.String(length=36), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discard_reason_code", sa.String(length=20), nullable=True),
        sa.UniqueConstraint("import_public_id", name="uq_equipment_source_import_public_id"),
        sa.ForeignKeyConstraint(
            ["based_on_import_id"],
            [f"{IMPORT_TABLE}.id"],
            name="fk_equipment_source_import_based_on",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint("provider_code = 'PLUM'", name="ck_equipment_source_import_provider"),
        sa.CheckConstraint("fingerprint ~ '^[0-9a-f]{64}$'", name="ck_equipment_source_import_fingerprint"),
        sa.CheckConstraint("row_count >= 0", name="ck_equipment_source_import_row_count"),
        sa.CheckConstraint("preview_version >= 1", name="ck_equipment_source_import_preview_version"),
        # Each status carries exactly its own who-and-when. CASE, so a NULL status cannot pass.
        sa.CheckConstraint(
            "CASE import_status_code"
            " WHEN 'PREVIEWED' THEN published_at IS NULL AND discarded_at IS NULL AND discard_reason_code IS NULL"
            " WHEN 'PUBLISHED' THEN published_at IS NOT NULL AND discarded_at IS NULL AND discard_reason_code IS NULL"
            " WHEN 'DISCARDED' THEN published_at IS NULL AND discarded_at IS NOT NULL"
            " AND discard_reason_code IN ('BY_FLEET_ADMIN', 'SUPERSEDED')"
            " ELSE FALSE END",
            name="ck_equipment_source_import_status",
        ),
    )
    op.create_index("ix_equipment_source_import_status", IMPORT_TABLE, ["import_status_code", "published_at"])
    op.create_index("ix_equipment_source_import_fingerprint", IMPORT_TABLE, ["fingerprint"])

    op.create_table(
        IMPORT_ROW_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("equipment_source_import_id", sa.Integer(), nullable=False),
        # The line in the file, counting the title and header lines, so the Fleet Admin can find it.
        sa.Column("row_number", sa.Integer(), nullable=False),
        # Only the values the transformer uses (design section 3); never PAN, insurance or finance columns.
        sa.Column("machine_number", sa.Unicode(length=200), nullable=True),
        sa.Column("category", sa.Unicode(length=200), nullable=True),
        sa.Column("schedule_type", sa.Unicode(length=200), nullable=True),
        sa.Column("make", sa.Unicode(length=200), nullable=True),
        sa.Column("model", sa.Unicode(length=200), nullable=True),
        sa.Column("capacity", sa.Unicode(length=200), nullable=True),
        sa.Column("load_capacity", sa.Unicode(length=200), nullable=True),
        sa.Column("engine_number", sa.Unicode(length=200), nullable=True),
        sa.Column("chassis_number", sa.Unicode(length=200), nullable=True),
        sa.Column("commenced_year", sa.Unicode(length=200), nullable=True),
        sa.Column("owning_company", sa.Unicode(length=200), nullable=True),
        sa.Column("status_text", sa.Unicode(length=200), nullable=True),
        sa.Column("bed_number", sa.Unicode(length=200), nullable=True),
        # A used value was longer than the platform stores; the row is set aside, on every refresh.
        sa.Column("value_too_long", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.UniqueConstraint("equipment_source_import_id", "row_number", name="uq_equipment_source_import_row_number"),
        sa.ForeignKeyConstraint(
            ["equipment_source_import_id"], [f"{IMPORT_TABLE}.id"], name="fk_equipment_source_import_row_import"
        ),
        sa.CheckConstraint("row_number >= 1", name="ck_equipment_source_import_row_number"),
    )

    op.create_table(
        CATEGORY_RULE_TABLE,
        # Plum's category in the alias table's stored form; the alias must exist.
        sa.Column("alias_source_code", sa.String(length=50), nullable=False, server_default=sa.text("'PLUM_CATEGORY'")),
        sa.Column("normalized_category", sa.Unicode(length=200), nullable=False),
        sa.Column("capability_code", sa.String(length=50), nullable=True),
        sa.Column("plum_unit_code", sa.String(length=50), nullable=True),
        sa.Column("plausible_low", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("plausible_high", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("check_code", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("normalized_category", name="pk_equipment_source_category_rule"),
        sa.ForeignKeyConstraint(
            ["alias_source_code", "normalized_category"],
            [f"{ALIAS_TABLE}.source_code", f"{ALIAS_TABLE}.normalized_term"],
            name="fk_equipment_source_category_rule_alias",
        ),
        sa.ForeignKeyConstraint(
            ["capability_code"], ["equipment_capability.capability_code"], name="fk_equipment_source_category_rule_capability"
        ),
        sa.CheckConstraint("alias_source_code = 'PLUM_CATEGORY'", name="ck_equipment_source_category_rule_source"),
        sa.CheckConstraint(
            "plum_unit_code IS NULL OR plum_unit_code IN (" + ", ".join(f"'{code}'" for code in UNIT_CODES) + ")",
            name="ck_equipment_source_category_rule_unit",
        ),
        # CHECKED carries what is checked, in what unit, within what range; the others carry nothing.
        sa.CheckConstraint(
            "CASE check_code"
            " WHEN 'CHECKED' THEN capability_code IS NOT NULL AND plum_unit_code IS NOT NULL"
            " AND plausible_low IS NOT NULL AND plausible_high IS NOT NULL"
            " AND plausible_low > 0 AND plausible_high >= plausible_low"
            " AND plausible_low <> 'NaN'::numeric AND plausible_high <> 'NaN'::numeric"
            " WHEN 'UNIT_UNCLEAR' THEN capability_code IS NULL AND plum_unit_code IS NULL"
            " AND plausible_low IS NULL AND plausible_high IS NULL"
            " WHEN 'NOT_CHECKED' THEN capability_code IS NULL AND plum_unit_code IS NULL"
            " AND plausible_low IS NULL AND plausible_high IS NULL"
            " ELSE FALSE END",
            name="ck_equipment_source_category_rule_check",
        ),
    )

    # One row: the count of changes to anything a preview is computed from.
    op.create_table(
        STATE_TABLE,
        sa.Column("state_key", sa.String(length=20), primary_key=True),
        sa.Column("change_number", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("state_key = 'EQUIPMENT'", name="ck_equipment_reference_state_key"),
        sa.CheckConstraint("change_number >= 0", name="ck_equipment_reference_state_change_number"),
    )
    op.execute(f"INSERT INTO {STATE_TABLE} (state_key, change_number) VALUES ('EQUIPMENT', 0)")


def _create_asset_tables() -> None:
    op.create_table(
        ASSET_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_public_id", sa.String(length=36), nullable=False),
        # EQ-000001, derived from the id as RR- is (ADR-007). Never truncated past six digits.
        sa.Column(
            "asset_reference",
            sa.String(length=30),
            sa.Computed("'EQ-' || lpad(id::text, GREATEST(6, length(id::text)), '0')", persisted=True),
            nullable=False,
        ),
        sa.Column("asset_kind_code", sa.String(length=20), nullable=False),
        sa.Column("class_code", sa.String(length=50), nullable=False),
        sa.Column("type_code", sa.String(length=50), nullable=True),
        sa.Column("equipment_model_id", sa.Integer(), nullable=True),
        # Plum's facts, as corrected by the Fleet Admin (design section 7). The machine number is the key
        # Plum and the platform share; the platform's identity is the public id.
        sa.Column("machine_number", sa.Unicode(length=200), nullable=False),
        sa.Column("engine_number", sa.Unicode(length=200), nullable=True),
        sa.Column("chassis_number", sa.Unicode(length=200), nullable=True),
        sa.Column("commenced_year", sa.Integer(), nullable=True),
        sa.Column("owning_company", sa.Unicode(length=200), nullable=True),
        sa.Column("asset_status_code", sa.String(length=20), nullable=False),
        # The platform's facts (design section 5A): never written by the transformer.
        sa.Column("serial_number", sa.Unicode(length=100), nullable=True),
        sa.Column("year_of_manufacture", sa.Integer(), nullable=True),
        sa.Column("asset_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        # The date of the report its Plum facts came from: the freshness every read carries.
        sa.Column("facts_report_date", sa.Date(), nullable=True),
        # The import that first brought it in - provenance, and what the test harness cleans up by.
        sa.Column("registered_by_import_id", sa.Integer(), nullable=True),
        *_audit_columns(),
        sa.UniqueConstraint("asset_public_id", name="uq_equipment_asset_public_id"),
        sa.UniqueConstraint("asset_reference", name="uq_equipment_asset_reference"),
        # Targets of the composite keys below.
        sa.UniqueConstraint("id", "class_code", name="uq_equipment_asset_id_class"),
        # A machine has a machine class and a part a part class.
        sa.ForeignKeyConstraint(
            ["class_code", "asset_kind_code"],
            [f"{CLASS_TABLE}.class_code", f"{CLASS_TABLE}.class_kind_code"],
            name="fk_equipment_asset_class_kind",
        ),
        sa.ForeignKeyConstraint(
            ["class_code", "type_code"],
            [f"{TYPE_TABLE}.class_code", f"{TYPE_TABLE}.type_code"],
            name="fk_equipment_asset_class_type",
        ),
        # A model of the asset's own class; MATCH SIMPLE skips the check when there is no model.
        sa.ForeignKeyConstraint(
            ["equipment_model_id", "class_code"],
            [f"{MODEL_TABLE}.id", f"{MODEL_TABLE}.class_code"],
            name="fk_equipment_asset_model_class",
        ),
        sa.ForeignKeyConstraint(
            ["registered_by_import_id"], [f"{IMPORT_TABLE}.id"], name="fk_equipment_asset_registered_by_import"
        ),
        sa.CheckConstraint("asset_kind_code IN ('MACHINE', 'PART')", name="ck_equipment_asset_kind"),
        sa.CheckConstraint("asset_status_code IN ('ACTIVE', 'RETIRED')", name="ck_equipment_asset_status"),
        sa.CheckConstraint("asset_version >= 1", name="ck_equipment_asset_version"),
        _non_blank("machine_number", 200, "ck_equipment_asset_machine_number", nullable=False),
        _non_blank("serial_number", 100, "ck_equipment_asset_serial_number", nullable=True),
        sa.CheckConstraint(
            "CASE WHEN commenced_year IS NULL THEN TRUE ELSE commenced_year BETWEEN 1900 AND 2200 END",
            name="ck_equipment_asset_commenced_year",
        ),
        sa.CheckConstraint(
            "CASE WHEN year_of_manufacture IS NULL THEN TRUE ELSE year_of_manufacture BETWEEN 1900 AND 2200 END",
            name="ck_equipment_asset_year_of_manufacture",
        ),
    )
    for index_name, columns in (
        ("ix_equipment_asset_class", ["class_code", "type_code"]),
        ("ix_equipment_asset_model", ["equipment_model_id"]),
        ("ix_equipment_asset_machine_number", ["machine_number"]),
        ("ix_equipment_asset_registered_by_import", ["registered_by_import_id"]),
    ):
        op.create_index(index_name, ASSET_TABLE, columns)

    op.create_table(
        ASSET_CAPABILITY_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("equipment_asset_id", sa.Integer(), nullable=False),
        sa.Column("class_code", sa.String(length=50), nullable=False),
        sa.Column("capability_code", sa.String(length=50), nullable=False),
        # The Fleet Admin's own value for this one machine, overriding its model's (design section 4).
        sa.Column("capability_value", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("choice_value", sa.String(length=50), nullable=True),
        sa.Column("reason", sa.UnicodeText(), nullable=False),
        sa.Column("set_by", sa.String(length=36), nullable=False),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("equipment_asset_id", "capability_code", name="uq_equipment_asset_capability"),
        # Follows the asset if its class is corrected; the service first removes any value the new class
        # does not take.
        sa.ForeignKeyConstraint(
            ["equipment_asset_id", "class_code"],
            [f"{ASSET_TABLE}.id", f"{ASSET_TABLE}.class_code"],
            name="fk_equipment_asset_capability_asset_class",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["class_code", "capability_code"],
            [f"{CLASS_CAPABILITY_TABLE}.class_code", f"{CLASS_CAPABILITY_TABLE}.capability_code"],
            name="fk_equipment_asset_capability_class_capability",
        ),
        sa.ForeignKeyConstraint(["set_by"], ["app_user.public_id"], name="fk_equipment_asset_capability_set_by"),
        _capability_value_check("ck_equipment_asset_capability_value"),
        _non_blank("reason", 1000, "ck_equipment_asset_capability_reason", nullable=False),
    )

    op.create_table(
        ASSET_LINK_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("link_public_id", sa.String(length=36), nullable=False),
        sa.Column("parent_asset_id", sa.Integer(), nullable=False),
        sa.Column("child_asset_id", sa.Integer(), nullable=False),
        sa.Column("link_kind_code", sa.String(length=20), nullable=False),
        sa.Column("fitted_on", sa.Date(), nullable=False),
        sa.Column("removed_on", sa.Date(), nullable=True),
        sa.Column("fitted_by", sa.String(length=36), nullable=False),
        sa.Column("fitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("removed_by", sa.String(length=36), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("link_public_id", name="uq_equipment_asset_link_public_id"),
        sa.ForeignKeyConstraint(["parent_asset_id"], [f"{ASSET_TABLE}.id"], name="fk_equipment_asset_link_parent"),
        sa.ForeignKeyConstraint(["child_asset_id"], [f"{ASSET_TABLE}.id"], name="fk_equipment_asset_link_child"),
        sa.ForeignKeyConstraint(["fitted_by"], ["app_user.public_id"], name="fk_equipment_asset_link_fitted_by"),
        sa.ForeignKeyConstraint(["removed_by"], ["app_user.public_id"], name="fk_equipment_asset_link_removed_by"),
        # ERT-1 fits parts only; ERT-2 adds detachable kit.
        sa.CheckConstraint("link_kind_code = 'FITTED'", name="ck_equipment_asset_link_kind"),
        sa.CheckConstraint("parent_asset_id <> child_asset_id", name="ck_equipment_asset_link_not_itself"),
        # Removed on or after it was fitted, with who and when - or still fitted, with none of them.
        sa.CheckConstraint(
            "CASE WHEN removed_on IS NULL THEN removed_by IS NULL AND removed_at IS NULL"
            " ELSE removed_on >= fitted_on AND removed_by IS NOT NULL AND removed_at IS NOT NULL END",
            name="ck_equipment_asset_link_removal",
        ),
    )
    # A part is fitted to one machine at a time; a removed link keeps its history.
    op.create_index(
        "uq_equipment_asset_link_one_open_per_child",
        ASSET_LINK_TABLE,
        ["child_asset_id"],
        unique=True,
        postgresql_where=sa.text("removed_on IS NULL"),
    )
    op.create_index("ix_equipment_asset_link_parent", ASSET_LINK_TABLE, ["parent_asset_id"])

    op.create_table(
        BINDING_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("equipment_asset_id", sa.Integer(), nullable=False),
        sa.Column("provider_code", sa.String(length=20), nullable=False),
        # Plum's machine number as the report gives it, and the form it is matched in.
        sa.Column("provider_key", sa.Unicode(length=200), nullable=False),
        _normalized_column("normalized_provider_key", "provider_key", 200),
        # The used values the asset was last built from (design section 3). Never shown to a consumer.
        sa.Column("source_values", postgresql.JSONB(), nullable=False),
        sa.Column("reconciliation_status_code", sa.String(length=20), nullable=False),
        sa.Column("first_import_id", sa.Integer(), nullable=False),
        sa.Column("last_import_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("equipment_asset_id", name="uq_equipment_source_binding_asset"),
        sa.UniqueConstraint("provider_code", "normalized_provider_key", name="uq_equipment_source_binding_key"),
        sa.ForeignKeyConstraint(["equipment_asset_id"], [f"{ASSET_TABLE}.id"], name="fk_equipment_source_binding_asset"),
        sa.ForeignKeyConstraint(["first_import_id"], [f"{IMPORT_TABLE}.id"], name="fk_equipment_source_binding_first_import"),
        sa.ForeignKeyConstraint(["last_import_id"], [f"{IMPORT_TABLE}.id"], name="fk_equipment_source_binding_last_import"),
        sa.CheckConstraint("provider_code = 'PLUM'", name="ck_equipment_source_binding_provider"),
        _non_blank("provider_key", 200, "ck_equipment_source_binding_provider_key", nullable=False),
        # CONFIRMED: in the latest confirmed report. UNMATCHED: missing from it. AMBIGUOUS: its number was on
        # two rows of it.
        sa.CheckConstraint(
            "reconciliation_status_code IN ('CONFIRMED', 'UNMATCHED', 'AMBIGUOUS')",
            name="ck_equipment_source_binding_reconciliation",
        ),
    )
    op.create_index("ix_equipment_source_binding_last_import", BINDING_TABLE, ["last_import_id"])

    op.create_table(
        ASSET_FLAG_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("equipment_asset_id", sa.Integer(), nullable=False),
        sa.Column("flag_code", sa.String(length=40), nullable=False),
        # The field or capability the flag is about; '' when it is about the whole machine.
        sa.Column("subject_code", sa.String(length=50), nullable=False, server_default=sa.text("''")),
        sa.Column("raised_by_import_id", sa.Integer(), nullable=True),
        sa.Column("raised_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("equipment_asset_id", "flag_code", "subject_code", name="uq_equipment_asset_flag"),
        sa.ForeignKeyConstraint(["equipment_asset_id"], [f"{ASSET_TABLE}.id"], name="fk_equipment_asset_flag_asset"),
        sa.ForeignKeyConstraint(
            ["raised_by_import_id"], [f"{IMPORT_TABLE}.id"], name="fk_equipment_asset_flag_raised_by_import"
        ),
        sa.CheckConstraint(
            "flag_code IN (" + ", ".join(f"'{code}'" for code in FLAG_CODES) + ")", name="ck_equipment_asset_flag_code"
        ),
    )
    op.create_index("ix_equipment_asset_flag_asset", ASSET_FLAG_TABLE, ["equipment_asset_id"])


def _create_correction_tables() -> None:
    op.create_table(
        VALUE_RULE_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_public_id", sa.String(length=36), nullable=False),
        sa.Column("column_code", sa.String(length=30), nullable=False),
        # The Plum value as the Fleet Admin saw it, and the stored form it is matched in.
        sa.Column("plum_value", sa.Unicode(length=200), nullable=False),
        _normalized_column("normalized_value", "plum_value", 200),
        sa.Column("action_code", sa.String(length=30), nullable=False),
        sa.Column("result_number", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("result_unit_code", sa.String(length=50), nullable=True),
        sa.Column("result_class_code", sa.String(length=50), nullable=True),
        sa.Column("result_type_code", sa.String(length=50), nullable=True),
        sa.Column("reason", sa.UnicodeText(), nullable=False),
        sa.Column("rule_status_code", sa.String(length=20), nullable=False),
        sa.Column("closed_reason_code", sa.String(length=20), nullable=True),
        sa.Column("closed_by", sa.String(length=36), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        # The import whose preview it was recorded on, if any - where the Fleet Admin saw the value.
        sa.Column("recorded_during_import_id", sa.Integer(), nullable=True),
        sa.Column("recorded_by", sa.String(length=36), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("rule_public_id", name="uq_equipment_source_value_rule_public_id"),
        sa.ForeignKeyConstraint(
            ["result_class_code", "result_type_code"],
            [f"{TYPE_TABLE}.class_code", f"{TYPE_TABLE}.type_code"],
            name="fk_equipment_source_value_rule_class_type",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_during_import_id"], [f"{IMPORT_TABLE}.id"], name="fk_equipment_source_value_rule_import"
        ),
        sa.ForeignKeyConstraint(["recorded_by"], ["app_user.public_id"], name="fk_equipment_source_value_rule_recorded_by"),
        sa.ForeignKeyConstraint(["closed_by"], ["app_user.public_id"], name="fk_equipment_source_value_rule_closed_by"),
        sa.CheckConstraint(
            "column_code IN (" + ", ".join(f"'{code}'" for code in VALUE_RULE_COLUMNS) + ")",
            name="ck_equipment_source_value_rule_column",
        ),
        _non_blank("plum_value", 200, "ck_equipment_source_value_rule_plum_value", nullable=False),
        # SPLIT: a number and its unit, for the capacity figure. REASSIGN: the value names a type, not a
        # figure. NOT_A_VALUE: nothing was entered. Each carries exactly its own results.
        sa.CheckConstraint(
            "CASE action_code"
            " WHEN 'SPLIT_NUMBER_AND_UNIT' THEN column_code = 'CAPACITY'"
            " AND result_number IS NOT NULL AND result_number > 0 AND result_number <> 'NaN'::numeric"
            " AND result_unit_code IN (" + ", ".join(f"'{code}'" for code in UNIT_CODES) + ")"
            " AND result_class_code IS NULL AND result_type_code IS NULL"
            " WHEN 'REASSIGN_TO_TYPE' THEN column_code = 'CAPACITY'"
            " AND result_class_code IS NOT NULL AND result_type_code IS NOT NULL"
            " AND result_number IS NULL AND result_unit_code IS NULL"
            " WHEN 'NOT_A_VALUE' THEN result_number IS NULL AND result_unit_code IS NULL"
            " AND result_class_code IS NULL AND result_type_code IS NULL"
            " ELSE FALSE END",
            name="ck_equipment_source_value_rule_action",
        ),
        _non_blank("reason", 1000, "ck_equipment_source_value_rule_reason", nullable=False),
        sa.CheckConstraint(
            "CASE rule_status_code"
            " WHEN 'OPEN' THEN closed_reason_code IS NULL AND closed_by IS NULL AND closed_at IS NULL"
            " WHEN 'CLOSED' THEN closed_reason_code IN ('BY_FLEET_ADMIN', 'SUPERSEDED')"
            " AND closed_by IS NOT NULL AND closed_at IS NOT NULL"
            " ELSE FALSE END",
            name="ck_equipment_source_value_rule_status",
        ),
    )
    # One open rule for a value in a column; closed ones are history.
    op.create_index(
        "uq_equipment_source_value_rule_one_open",
        VALUE_RULE_TABLE,
        ["column_code", "normalized_value"],
        unique=True,
        postgresql_where=sa.text("rule_status_code = 'OPEN'"),
    )

    op.create_table(
        CORRECTION_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("correction_public_id", sa.String(length=36), nullable=False),
        sa.Column("equipment_asset_id", sa.Integer(), nullable=False),
        sa.Column("field_code", sa.String(length=30), nullable=False),
        # The Plum value it replaces (blank where Plum gave none), and the correct value.
        sa.Column("plum_value", sa.Unicode(length=200), nullable=True),
        sa.Column("corrected_value", sa.Unicode(length=200), nullable=False),
        sa.Column("reason", sa.UnicodeText(), nullable=False),
        sa.Column("correction_status_code", sa.String(length=20), nullable=False),
        # PLUM_AGREES: a confirmed report carried the corrected value, so it closed itself.
        sa.Column("closed_reason_code", sa.String(length=20), nullable=True),
        sa.Column("closed_by", sa.String(length=36), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_import_id", sa.Integer(), nullable=True),
        sa.Column("recorded_by", sa.String(length=36), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("correction_public_id", name="uq_equipment_asset_correction_public_id"),
        sa.ForeignKeyConstraint(["equipment_asset_id"], [f"{ASSET_TABLE}.id"], name="fk_equipment_asset_correction_asset"),
        sa.ForeignKeyConstraint(
            ["closed_by_import_id"], [f"{IMPORT_TABLE}.id"], name="fk_equipment_asset_correction_closed_by_import"
        ),
        sa.ForeignKeyConstraint(["recorded_by"], ["app_user.public_id"], name="fk_equipment_asset_correction_recorded_by"),
        sa.ForeignKeyConstraint(["closed_by"], ["app_user.public_id"], name="fk_equipment_asset_correction_closed_by"),
        # The machine number cannot be corrected: it is the key Plum and the platform share.
        sa.CheckConstraint(
            "field_code IN (" + ", ".join(f"'{code}'" for code in CORRECTION_FIELDS) + ")",
            name="ck_equipment_asset_correction_field",
        ),
        _non_blank("corrected_value", 200, "ck_equipment_asset_correction_value", nullable=False),
        _non_blank("reason", 1000, "ck_equipment_asset_correction_reason", nullable=False),
        # Closed by the Fleet Admin (who is recorded), by a newer correction of the same field, or by a
        # confirmed report that now agrees (which import is recorded).
        sa.CheckConstraint(
            "CASE correction_status_code"
            " WHEN 'OPEN' THEN closed_reason_code IS NULL AND closed_by IS NULL AND closed_at IS NULL"
            " AND closed_by_import_id IS NULL"
            " WHEN 'CLOSED' THEN closed_at IS NOT NULL AND CASE closed_reason_code"
            " WHEN 'BY_FLEET_ADMIN' THEN closed_by IS NOT NULL AND closed_by_import_id IS NULL"
            " WHEN 'SUPERSEDED' THEN closed_by IS NOT NULL AND closed_by_import_id IS NULL"
            " WHEN 'PLUM_AGREES' THEN closed_by_import_id IS NOT NULL"
            " ELSE FALSE END"
            " ELSE FALSE END",
            name="ck_equipment_asset_correction_status",
        ),
    )
    op.create_index(
        "uq_equipment_asset_correction_one_open",
        CORRECTION_TABLE,
        ["equipment_asset_id", "field_code"],
        unique=True,
        postgresql_where=sa.text("correction_status_code = 'OPEN'"),
    )


def _create_capability_trigger() -> None:
    """WRR-001's rule - a value must fit its capability, which lives in another table - for the model's
    rated values and a machine's own values. No `%` and no colon in the body: the statement passes through
    SQLAlchemy's text() and the driver's placeholder parsing."""
    op.execute(
        """
        CREATE FUNCTION equipment_capability_value_matches_kind() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        DECLARE
            kind varchar(20);
            unit varchar(50);
            allowed varchar(50)[];
        BEGIN
            SELECT value_kind_code, unit_code, allowed_values INTO kind, unit, allowed
            FROM equipment_capability WHERE capability_code = NEW.capability_code;
            IF kind = 'CHOICE' THEN
                IF NEW.capability_value IS NOT NULL OR NEW.choice_value IS NULL
                   OR NOT COALESCE(NEW.choice_value = ANY (allowed), FALSE) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = 'check_violation',
                        CONSTRAINT = 'ck_equipment_capability_value_matches_kind',
                        MESSAGE = NEW.capability_code || ' takes one of its listed values, and nothing else.';
                END IF;
            ELSIF NEW.choice_value IS NOT NULL OR NEW.capability_value IS NULL
                  OR (unit = 'COUNT' AND NEW.capability_value <> trunc(NEW.capability_value)) THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_equipment_capability_value_matches_kind',
                    MESSAGE = NEW.capability_code || ' takes a value in its own unit, whole where it is counted.';
            END IF;
            RETURN NEW;
        END
        $body$
        """
    )
    for table in (MODEL_CAPABILITY_TABLE, ASSET_CAPABILITY_TABLE):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_matches_kind
            BEFORE INSERT OR UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION equipment_capability_value_matches_kind()
            """
        )


def _seed_category_rules() -> None:
    connection = op.get_bind()
    for category, capability_code, unit_code, low, high, check_code in CATEGORY_RULES:
        connection.execute(
            sa.text(
                f"INSERT INTO {CATEGORY_RULE_TABLE} "
                "(normalized_category, capability_code, plum_unit_code, plausible_low, plausible_high, check_code) "
                "VALUES (:category, :capability_code, :unit_code, :low, :high, :check_code)"
            ),
            {
                "category": category,
                "capability_code": capability_code,
                "unit_code": unit_code,
                "low": low,
                "high": high,
                "check_code": check_code,
            },
        )


def _seed_permissions() -> None:
    """Insert each permission row and its role grants, as 20260908_0036 to 0041 do."""
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

    for table in (MODEL_CAPABILITY_TABLE, ASSET_CAPABILITY_TABLE):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_matches_kind ON {table}")
    op.execute("DROP FUNCTION IF EXISTS equipment_capability_value_matches_kind()")
    for table in (
        CORRECTION_TABLE,
        VALUE_RULE_TABLE,
        ASSET_FLAG_TABLE,
        BINDING_TABLE,
        ASSET_LINK_TABLE,
        ASSET_CAPABILITY_TABLE,
        ASSET_TABLE,
        STATE_TABLE,
        CATEGORY_RULE_TABLE,
        IMPORT_ROW_TABLE,
        IMPORT_TABLE,
        MODEL_SOURCE_KEY_TABLE,
        MODEL_CAPABILITY_TABLE,
        MODEL_TABLE,
        PART_FIT_TABLE,
    ):
        op.drop_table(table)
    connection.execute(sa.text(f"DELETE FROM {CLASS_TABLE} WHERE class_code = 'CRANE_CARRIER'"))
    connection.execute(sa.text(f"DELETE FROM {VERSION_TABLE} WHERE version_number = 2"))
    op.drop_constraint("uq_equipment_class_code_kind", CLASS_TABLE, type_="unique")
    op.drop_constraint("ck_equipment_class_kind", CLASS_TABLE, type_="check")
    op.drop_column(CLASS_TABLE, "class_kind_code")
