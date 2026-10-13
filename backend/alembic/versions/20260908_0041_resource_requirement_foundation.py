"""resource requirement foundation and the platform's Equipment Reference (WRR-001)

Two new modules, one migration (owner, answer Q17 of 24 September 2026); see
docs/agent/slices/wrr-001-resource-requirement-foundation.md.

**Equipment Reference** - the platform's own equipment structure (ADR-037): classes, the types within
each, and the capabilities that describe them, each capability in exactly one unit. Seven tables:

- `equipment_taxonomy_version` - each version of the structure and where it came from. Version 1 is
  loaded here.
- `equipment_class`, `equipment_type`, `equipment_capability` - codes are the primary keys and never
  change. Nothing is deleted: a row records the version that introduced it and, once retired, the
  version that retired it.
- `equipment_class_business_line` - which business lines deploy a class to customers (HIRING,
  TRANSPORTATION, or neither when a class has no row), so one structure serves both modules (Q14).
- `equipment_class_capability` - which capabilities apply to a class, and which one is its key
  capability, the one planners compare first. At most one live key per class.
- `equipment_term_alias` - what other systems and people call things (Plum's categories,
  Annexure-21's equipment types, trade words), each mapped to a class and optionally a type. Its
  normalized form is fixed by a CHECK, so a lookup can never miss because of spacing or case.

The part classes of the machine component hierarchy (boom section, hook block, counterweight, tool) come
with the machine records as an additive change: more rows in `equipment_class`, and a column with a
default or a table referring to it by code to say what a class is and what it may be fitted to. Nothing
here assumes every class is a machine: a class with no business-line row is offered to no business line.

**Resource Requirements** - Operations' record of what one Work Order line needs on site. Three
tables, none with a `crm_` prefix because none is CRM's:

- `resource_requirement` - one per requirement; several per line (Q7). A foreign key to
  `crm_work_order_line(id)` guarantees the line exists; the line's immutable identity is copied once
  (ADR-017's approved immutable reference). The reference `RR-000001` is derived from the id, as `CO-`
  and `WO-` are (ADR-007), by a generated column rather than a second statement, so it can never be
  missing or disagree with the id.
- `resource_requirement_item` - what one unit is made of. The shape holds several items so
  Transportation's combinations fit later; this slice allows exactly one (Q15), enforced by
  `ck_rr_item_single_item_this_slice`, which a later migration drops when combinations arrive.
- `resource_requirement_item_capability` - the least value a capability must reach (or, for a fixed
  list such as axle configuration, the value). Composite foreign keys make the database refuse a type
  of another class and a capability that does not apply to the item's class. A trigger,
  `trg_rr_item_capability_matches_kind`, refuses a value that does not fit its capability: a least
  value for a fixed-list capability or a choice for a measured one, a choice not on the list, and a
  fraction for a capability counted in whole numbers. A CHECK cannot see the capability's row, so a
  trigger is the database's own way to hold that rule; it raises a check violation under that name.

Nothing here writes a Work Order table, and the frozen handoff's tables are untouched.

CHECK constraints are written NULL-safe (CASE, never an OR chain a NULL can satisfy) and refuse
NaN, which PostgreSQL's numeric orders above every number - both lessons of Slice 7D.

Seeds three permissions, spelled out rather than imported so this revision stays a frozen
historical snapshot (the 20260908_0033 to 0040 convention). The version-1 structure is spelled out
here for the same reason: the migration is what loads it, and a later change to application
constants must not rewrite what version 1 was.

Revision ID: 20260908_0041
Revises: 20260908_0040
Create Date: 2026-09-24
"""

from __future__ import annotations

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0041"
down_revision: Union[str, None] = "20260908_0040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VERSION_TABLE = "equipment_taxonomy_version"
CLASS_TABLE = "equipment_class"
CLASS_LINE_TABLE = "equipment_class_business_line"
TYPE_TABLE = "equipment_type"
CAPABILITY_TABLE = "equipment_capability"
CLASS_CAPABILITY_TABLE = "equipment_class_capability"
ALIAS_TABLE = "equipment_term_alias"
REQUIREMENT_TABLE = "resource_requirement"
ITEM_TABLE = "resource_requirement_item"
ITEM_CAPABILITY_TABLE = "resource_requirement_item_capability"

CODE_PATTERN = "^[A-Z][A-Z0-9_]*$"
UNIT_CODES = ("TONNE", "KILOGRAM", "METRE", "CUBIC_METRE", "KILOWATT", "KILOVOLT_AMPERE", "COUNT")

ROLE_ADMIN = "ADMIN"
ROLE_SALES_USER = "SALES_USER"
ROLE_SALES_MANAGER = "SALES_MANAGER"
ROLE_FINANCE_USER = "FINANCE_USER"
ROLE_OPERATIONS_USER = "OPERATIONS_USER"
ROLE_MANAGEMENT_READ_ONLY = "MANAGEMENT_READ_ONLY"

# The roles that can view Work Orders (WORK_ORDER_READ), all six.
WORK_ORDER_READ_ROLES = (
    ROLE_ADMIN,
    ROLE_SALES_USER,
    ROLE_SALES_MANAGER,
    ROLE_FINANCE_USER,
    ROLE_OPERATIONS_USER,
    ROLE_MANAGEMENT_READ_ONLY,
)

PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    "RESOURCE_REQUIREMENT_READ": (
        "View the resources Work Order lines need, and the planning list.",
        WORK_ORDER_READ_ROLES,
    ),
    # Operations and Admin only (owner, answer Q6 of 24 September 2026).
    "RESOURCE_REQUIREMENT_WRITE": (
        "Record, change or cancel what a Work Order line needs on site.",
        (ROLE_ADMIN, ROLE_OPERATIONS_USER),
    ),
    "EQUIPMENT_REFERENCE_READ": (
        "View the platform's equipment structure: classes, types, capabilities and the words that map to them.",
        WORK_ORDER_READ_ROLES,
    ),
}


# --- Version 1 of the structure (docs/agent/slices/wrr-001-resource-requirement-foundation.md,
#     section 5, agreed by the owner on 24 September 2026) -------------------------------------------

VERSION_1_LABEL = "Version 1"
VERSION_1_SOURCE = (
    "WRR-001 design, agreed 24 September 2026: the FRS Annexure-21 equipment types, the categories in "
    "Plum's Own Vehicle Complete Information Report of 24 September 2026, and the machines named in the "
    "FRS workbooks. Owned on the business side by Fleet's Equipment Master owner (Q14)."
)

# capability_code: (label, unit_code or None, value_kind_code, allowed values for a CHOICE)
CAPABILITIES: dict[str, tuple[str, str | None, str, tuple[str, ...] | None]] = {
    "RATED_CAPACITY": ("Rated capacity", "TONNE", "MINIMUM", None),
    "MAIN_BOOM_LENGTH": ("Main boom length", "METRE", "MINIMUM", None),
    "MAX_TIP_HEIGHT": ("Maximum tip height", "METRE", "MINIMUM", None),
    "WORKING_HEIGHT": ("Working height", "METRE", "MINIMUM", None),
    "PLATFORM_CAPACITY": ("Platform capacity", "KILOGRAM", "MINIMUM", None),
    "HORIZONTAL_OUTREACH": ("Horizontal outreach", "METRE", "MINIMUM", None),
    "LIFT_HEIGHT": ("Lift height", "METRE", "MINIMUM", None),
    "OPERATING_WEIGHT": ("Operating weight", "TONNE", "MINIMUM", None),
    "BUCKET_CAPACITY": ("Bucket capacity", "CUBIC_METRE", "MINIMUM", None),
    "GROSS_COMBINATION_WEIGHT": ("Gross combination weight", "TONNE", "MINIMUM", None),
    "AXLE_CONFIGURATION": ("Axle configuration", None, "CHOICE", ("4X2", "6X2", "6X4", "6X6", "8X4", "8X8")),
    "PAYLOAD": ("Payload", "TONNE", "MINIMUM", None),
    "DECK_LENGTH": ("Deck length", "METRE", "MINIMUM", None),
    "AXLE_COUNT": ("Axles", "COUNT", "MINIMUM", None),
    "AXLE_LINES": ("Axle lines", "COUNT", "MINIMUM", None),
    "POWER_OUTPUT": ("Power", "KILOWATT", "MINIMUM", None),
    "RATED_OUTPUT_KVA": ("Rated output", "KILOVOLT_AMPERE", "MINIMUM", None),
}

# class_code: (label, business lines, [(type_code, type_label)], [capability_code], key capability)
CLASSES: dict[str, tuple[str, tuple[str, ...], tuple[tuple[str, str], ...], tuple[str, ...], str | None]] = {
    "CRANE": (
        "Crane",
        ("HIRING",),
        (
            ("CRAWLER", "Crawler"),
            ("ALL_TERRAIN", "All-terrain"),
            ("TRUCK_MOUNTED_TELESCOPIC", "Truck-mounted telescopic"),
            ("ROUGH_TERRAIN", "Rough-terrain"),
            ("PICK_AND_CARRY", "Pick-and-carry"),
            ("KNUCKLE_BOOM_LOADER", "Knuckle-boom loader"),
            ("MOBILE_TOWER", "Mobile tower"),
            ("DERRICK", "Derrick"),
        ),
        ("RATED_CAPACITY", "MAIN_BOOM_LENGTH", "MAX_TIP_HEIGHT"),
        "RATED_CAPACITY",
    ),
    "AERIAL_WORK_PLATFORM": (
        "Aerial Work Platform",
        ("HIRING",),
        (
            ("TELESCOPIC_BOOM", "Telescopic boom"),
            ("ARTICULATING_BOOM", "Articulating boom"),
            ("SCISSOR", "Scissor"),
            ("VERTICAL_MAST", "Vertical mast"),
        ),
        ("WORKING_HEIGHT", "PLATFORM_CAPACITY", "HORIZONTAL_OUTREACH"),
        "WORKING_HEIGHT",
    ),
    "FORKLIFT": ("Forklift", ("HIRING",), (), ("RATED_CAPACITY", "LIFT_HEIGHT"), "RATED_CAPACITY"),
    "EXCAVATOR": ("Excavator", ("HIRING",), (), ("OPERATING_WEIGHT", "BUCKET_CAPACITY"), "OPERATING_WEIGHT"),
    "PRIME_MOVER": (
        "Prime Mover",
        ("TRANSPORTATION",),
        (("TRACTOR_UNIT", "Tractor unit"), ("BALLAST_TRACTOR", "Ballast tractor (puller)")),
        ("GROSS_COMBINATION_WEIGHT", "AXLE_CONFIGURATION"),
        "GROSS_COMBINATION_WEIGHT",
    ),
    "TRAILER": (
        "Trailer",
        ("TRANSPORTATION",),
        (
            ("LOW_BED", "Low-bed"),
            ("SEMI_LOW_BED", "Semi-low-bed"),
            ("FLATBED", "Flatbed"),
            ("EXTENDABLE", "Extendable"),
        ),
        ("PAYLOAD", "DECK_LENGTH", "AXLE_COUNT"),
        "PAYLOAD",
    ),
    "MODULAR_HYDRAULIC_TRAILER": (
        "Modular Hydraulic Trailer",
        ("TRANSPORTATION",),
        (("TOWED_MODULAR", "Towed modular"), ("SELF_PROPELLED", "Self-propelled (SPMT)")),
        ("AXLE_LINES", "PAYLOAD"),
        "AXLE_LINES",
    ),
    "POWER_PACK": ("Power Pack", ("TRANSPORTATION",), (), ("POWER_OUTPUT",), None),
    "TRUCK": ("Truck", ("TRANSPORTATION",), (), ("PAYLOAD",), "PAYLOAD"),
    "GENERATOR": ("Generator", (), (), ("RATED_OUTPUT_KVA",), None),
    "LIGHT_VEHICLE": (
        "Light Vehicle",
        (),
        (("TWO_WHEELER", "Two-wheeler"), ("FOUR_WHEELER", "Four-wheeler"), ("VAN", "Van")),
        (),
        None,
    ),
    "WORKSHOP_ASSET": ("Workshop Asset", (), (), (), None),
}

# (term, source_code, class_code, type_code or None). Plum's categories are spelled exactly as its
# report spells them, typing errors included ("Genertor"): the alias exists to recognise them.
ALIASES: tuple[tuple[str, str, str, str | None], ...] = (
    # Plum's VehCategory values.
    ("CRANES", "PLUM_CATEGORY", "CRANE", None),
    ("CRANE", "PLUM_CATEGORY", "CRANE", None),
    ("MAN LIFTS", "PLUM_CATEGORY", "AERIAL_WORK_PLATFORM", None),
    ("FORK LIFT", "PLUM_CATEGORY", "FORKLIFT", None),
    ("Excavator", "PLUM_CATEGORY", "EXCAVATOR", None),
    # Plum's "TRAILERS" are the prime movers; its "TRAILER BED" is the trailer.
    ("TRAILERS", "PLUM_CATEGORY", "PRIME_MOVER", None),
    ("TRAILER BED", "PLUM_CATEGORY", "TRAILER", None),
    ("HYDRAULIC AXLES", "PLUM_CATEGORY", "MODULAR_HYDRAULIC_TRAILER", None),
    ("Power Packs", "PLUM_CATEGORY", "POWER_PACK", None),
    ("TRUCKS", "PLUM_CATEGORY", "TRUCK", None),
    ("Genertor", "PLUM_CATEGORY", "GENERATOR", None),
    ("TWO WHEELER", "PLUM_CATEGORY", "LIGHT_VEHICLE", "TWO_WHEELER"),
    ("FOUR WHEELER", "PLUM_CATEGORY", "LIGHT_VEHICLE", "FOUR_WHEELER"),
    ("VAN", "PLUM_CATEGORY", "LIGHT_VEHICLE", "VAN"),
    ("GARAGE ASSETS", "PLUM_CATEGORY", "WORKSHOP_ASSET", None),
    ("GENERAL", "PLUM_CATEGORY", "WORKSHOP_ASSET", None),
    # The fifteen FRS Annexure-21 equipment types. "Telescopic Cranes" covers all-terrain,
    # truck-mounted, rough-terrain and pick-and-carry cranes, so it maps to the class only: the type
    # has to come from the model (section 5).
    ("Telescopic Cranes", "ANNEXURE_21", "CRANE", None),
    ("Mobile Tower Cranes", "ANNEXURE_21", "CRANE", "MOBILE_TOWER"),
    ("Crawler Cranes", "ANNEXURE_21", "CRANE", "CRAWLER"),
    ("Derrick", "ANNEXURE_21", "CRANE", "DERRICK"),
    ("Excavator", "ANNEXURE_21", "EXCAVATOR", None),
    ("Farana", "ANNEXURE_21", "CRANE", "PICK_AND_CARRY"),
    ("Forklift", "ANNEXURE_21", "FORKLIFT", None),
    ("Four Wheeler", "ANNEXURE_21", "LIGHT_VEHICLE", "FOUR_WHEELER"),
    ("Hydraulic Axles", "ANNEXURE_21", "MODULAR_HYDRAULIC_TRAILER", None),
    ("Manlifts", "ANNEXURE_21", "AERIAL_WORK_PLATFORM", None),
    ("Palfinger", "ANNEXURE_21", "CRANE", "KNUCKLE_BOOM_LOADER"),
    ("Puller", "ANNEXURE_21", "PRIME_MOVER", "BALLAST_TRACTOR"),
    ("Trailer Bed", "ANNEXURE_21", "TRAILER", None),
    ("Prime Movers", "ANNEXURE_21", "PRIME_MOVER", None),
    ("Two Wheelers", "ANNEXURE_21", "LIGHT_VEHICLE", "TWO_WHEELER"),
    # Trade words.
    ("Hydra", "TRADE_TERM", "CRANE", "PICK_AND_CARRY"),
)


def _versioned_columns() -> list[sa.Column]:
    """The two version columns every structure row carries: introduced in, and (once) retired in."""
    return [
        sa.Column("introduced_in_version", sa.Integer(), nullable=False),
        sa.Column("retired_in_version", sa.Integer(), nullable=True),
    ]


def _versioned_constraints(prefix: str) -> list[sa.schema.SchemaItem]:
    return [
        sa.ForeignKeyConstraint(
            ["introduced_in_version"], [f"{VERSION_TABLE}.version_number"], name=f"fk_{prefix}_introduced_version"
        ),
        sa.ForeignKeyConstraint(
            ["retired_in_version"], [f"{VERSION_TABLE}.version_number"], name=f"fk_{prefix}_retired_version"
        ),
        # A row cannot be retired in the version that introduced it, or before.
        sa.CheckConstraint(
            "retired_in_version IS NULL OR retired_in_version > introduced_in_version",
            name=f"ck_{prefix}_retired_after_introduced",
        ),
    ]


def _normalized(term: str) -> str:
    """What the CHECK on equipment_term_alias requires the normalized column to hold."""
    return " ".join(term.split()).upper()


def upgrade() -> None:
    _create_equipment_reference_tables()
    _load_version_1()
    _create_resource_requirement_tables()
    _seed_permissions()


def _create_equipment_reference_tables() -> None:
    op.create_table(
        VERSION_TABLE,
        sa.Column("version_number", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("version_label", sa.Unicode(length=100), nullable=False),
        sa.Column("source_note", sa.UnicodeText(), nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("version_number >= 1", name="ck_equipment_taxonomy_version_number"),
    )

    op.create_table(
        CLASS_TABLE,
        sa.Column("class_code", sa.String(length=50), primary_key=True),
        sa.Column("class_label", sa.Unicode(length=100), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        *_versioned_columns(),
        *_versioned_constraints("equipment_class"),
        sa.CheckConstraint(f"class_code ~ '{CODE_PATTERN}'", name="ck_equipment_class_code"),
    )

    op.create_table(
        CLASS_LINE_TABLE,
        sa.Column("class_code", sa.String(length=50), nullable=False),
        sa.Column("business_line_code", sa.String(length=50), nullable=False),
        *_versioned_columns(),
        sa.PrimaryKeyConstraint("class_code", "business_line_code", name="pk_equipment_class_business_line"),
        sa.ForeignKeyConstraint(["class_code"], [f"{CLASS_TABLE}.class_code"], name="fk_equipment_class_line_class"),
        *_versioned_constraints("equipment_class_line"),
        sa.CheckConstraint(
            "business_line_code IN ('HIRING', 'TRANSPORTATION')", name="ck_equipment_class_line_business_line"
        ),
    )

    op.create_table(
        TYPE_TABLE,
        sa.Column("type_code", sa.String(length=50), primary_key=True),
        sa.Column("class_code", sa.String(length=50), nullable=False),
        sa.Column("type_label", sa.Unicode(length=100), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        *_versioned_columns(),
        sa.ForeignKeyConstraint(["class_code"], [f"{CLASS_TABLE}.class_code"], name="fk_equipment_type_class"),
        # The target of every composite (class, type) foreign key: a type is only ever named together
        # with the class it belongs to.
        sa.UniqueConstraint("class_code", "type_code", name="uq_equipment_type_class_type"),
        *_versioned_constraints("equipment_type"),
        sa.CheckConstraint(f"type_code ~ '{CODE_PATTERN}'", name="ck_equipment_type_code"),
    )

    op.create_table(
        CAPABILITY_TABLE,
        sa.Column("capability_code", sa.String(length=50), primary_key=True),
        sa.Column("capability_label", sa.Unicode(length=100), nullable=False),
        # The one unit a value of this capability is always in. None only for a fixed list of values.
        sa.Column("unit_code", sa.String(length=50), nullable=True),
        sa.Column("value_kind_code", sa.String(length=20), nullable=False),
        sa.Column("allowed_values", postgresql.ARRAY(sa.String(length=50)), nullable=True),
        *_versioned_columns(),
        *_versioned_constraints("equipment_capability"),
        sa.CheckConstraint(f"capability_code ~ '{CODE_PATTERN}'", name="ck_equipment_capability_code"),
        sa.CheckConstraint(
            "unit_code IS NULL OR unit_code IN (" + ", ".join(f"'{code}'" for code in UNIT_CODES) + ")",
            name="ck_equipment_capability_unit",
        ),
        # MINIMUM: a least value, in the capability's unit, with no fixed list. CHOICE: one of a fixed
        # list, with no unit. Written as a CASE so a NULL kind cannot slip through an OR.
        sa.CheckConstraint(
            "CASE value_kind_code"
            " WHEN 'MINIMUM' THEN unit_code IS NOT NULL AND allowed_values IS NULL"
            " WHEN 'CHOICE' THEN unit_code IS NULL AND allowed_values IS NOT NULL"
            " AND cardinality(allowed_values) >= 1"
            " ELSE FALSE"
            " END",
            name="ck_equipment_capability_value_kind",
        ),
    )

    op.create_table(
        CLASS_CAPABILITY_TABLE,
        sa.Column("class_code", sa.String(length=50), nullable=False),
        sa.Column("capability_code", sa.String(length=50), nullable=False),
        sa.Column("is_key", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("display_order", sa.Integer(), nullable=False),
        *_versioned_columns(),
        sa.PrimaryKeyConstraint("class_code", "capability_code", name="pk_equipment_class_capability"),
        sa.ForeignKeyConstraint(["class_code"], [f"{CLASS_TABLE}.class_code"], name="fk_equipment_class_capability_class"),
        sa.ForeignKeyConstraint(
            ["capability_code"],
            [f"{CAPABILITY_TABLE}.capability_code"],
            name="fk_equipment_class_capability_capability",
        ),
        *_versioned_constraints("equipment_class_capability"),
    )
    # At most one live key capability per class. A retired key does not block its successor.
    op.create_index(
        "uq_equipment_class_capability_one_key",
        CLASS_CAPABILITY_TABLE,
        ["class_code"],
        unique=True,
        postgresql_where=sa.text("is_key AND retired_in_version IS NULL"),
    )

    op.create_table(
        ALIAS_TABLE,
        sa.Column("source_code", sa.String(length=50), nullable=False),
        sa.Column("term", sa.Unicode(length=200), nullable=False),
        sa.Column("normalized_term", sa.Unicode(length=200), nullable=False),
        sa.Column("class_code", sa.String(length=50), nullable=False),
        sa.Column("type_code", sa.String(length=50), nullable=True),
        *_versioned_columns(),
        sa.PrimaryKeyConstraint("source_code", "normalized_term", name="pk_equipment_term_alias"),
        sa.ForeignKeyConstraint(["class_code"], [f"{CLASS_TABLE}.class_code"], name="fk_equipment_term_alias_class"),
        # A type named by an alias must belong to the alias's class. MATCH SIMPLE skips the check
        # when the type is empty, which is what "the class only" means.
        sa.ForeignKeyConstraint(
            ["class_code", "type_code"],
            [f"{TYPE_TABLE}.class_code", f"{TYPE_TABLE}.type_code"],
            name="fk_equipment_term_alias_class_type",
        ),
        *_versioned_constraints("equipment_term_alias"),
        sa.CheckConstraint(
            "source_code IN ('PLUM_CATEGORY', 'ANNEXURE_21', 'TRADE_TERM')", name="ck_equipment_term_alias_source"
        ),
        sa.CheckConstraint(
            "normalized_term = upper(btrim(regexp_replace(term, '\\s+', ' ', 'g'))) AND normalized_term <> ''",
            name="ck_equipment_term_alias_normalized",
        ),
    )
    op.create_index("ix_equipment_term_alias_normalized_term", ALIAS_TABLE, ["normalized_term"])


def _load_version_1() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            f"INSERT INTO {VERSION_TABLE} (version_number, version_label, source_note) "
            "VALUES (1, :label, :source)"
        ),
        {"label": VERSION_1_LABEL, "source": VERSION_1_SOURCE},
    )

    for capability_code, (label, unit_code, value_kind_code, allowed_values) in CAPABILITIES.items():
        connection.execute(
            sa.text(
                f"INSERT INTO {CAPABILITY_TABLE} "
                "(capability_code, capability_label, unit_code, value_kind_code, allowed_values, introduced_in_version) "
                "VALUES (:code, :label, :unit_code, :kind, :allowed_values, 1)"
            ),
            {
                "code": capability_code,
                "label": label,
                "unit_code": unit_code,
                "kind": value_kind_code,
                "allowed_values": list(allowed_values) if allowed_values else None,
            },
        )

    for class_order, (class_code, (label, business_lines, types, capabilities, key)) in enumerate(CLASSES.items(), 1):
        connection.execute(
            sa.text(
                f"INSERT INTO {CLASS_TABLE} (class_code, class_label, display_order, introduced_in_version) "
                "VALUES (:code, :label, :display_order, 1)"
            ),
            {"code": class_code, "label": label, "display_order": class_order * 10},
        )
        for business_line_code in business_lines:
            connection.execute(
                sa.text(
                    f"INSERT INTO {CLASS_LINE_TABLE} (class_code, business_line_code, introduced_in_version) "
                    "VALUES (:class_code, :line, 1)"
                ),
                {"class_code": class_code, "line": business_line_code},
            )
        for type_order, (type_code, type_label) in enumerate(types, 1):
            connection.execute(
                sa.text(
                    f"INSERT INTO {TYPE_TABLE} (type_code, class_code, type_label, display_order, introduced_in_version) "
                    "VALUES (:type_code, :class_code, :label, :display_order, 1)"
                ),
                {"type_code": type_code, "class_code": class_code, "label": type_label, "display_order": type_order * 10},
            )
        for capability_order, capability_code in enumerate(capabilities, 1):
            connection.execute(
                sa.text(
                    f"INSERT INTO {CLASS_CAPABILITY_TABLE} "
                    "(class_code, capability_code, is_key, display_order, introduced_in_version) "
                    "VALUES (:class_code, :capability_code, :is_key, :display_order, 1)"
                ),
                {
                    "class_code": class_code,
                    "capability_code": capability_code,
                    "is_key": capability_code == key,
                    "display_order": capability_order * 10,
                },
            )

    for term, source_code, class_code, type_code in ALIASES:
        connection.execute(
            sa.text(
                f"INSERT INTO {ALIAS_TABLE} "
                "(source_code, term, normalized_term, class_code, type_code, introduced_in_version) "
                "VALUES (:source_code, :term, :normalized_term, :class_code, :type_code, 1)"
            ),
            {
                "source_code": source_code,
                "term": term,
                "normalized_term": _normalized(term),
                "class_code": class_code,
                "type_code": type_code,
            },
        )


def _create_resource_requirement_tables() -> None:
    op.create_table(
        REQUIREMENT_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requirement_public_id", sa.String(length=36), nullable=False),
        # RR-000001, derived from the id as CO- and WO- are (ADR-007). Never truncated past six digits.
        sa.Column(
            "requirement_reference",
            sa.String(length=30),
            sa.Computed("'RR-' || lpad(id::text, GREATEST(6, length(id::text)), '0')", persisted=True),
            nullable=False,
        ),
        sa.Column("work_order_line_id", sa.Integer(), nullable=False),
        # The line's immutable identity, copied once at creation (ADR-017's approved immutable reference).
        sa.Column("work_order_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_code", sa.Unicode(length=50), nullable=False),
        sa.Column("work_order_line_public_id", sa.String(length=36), nullable=False),
        sa.Column("work_order_line_number", sa.Integer(), nullable=False),
        sa.Column("source_offer_line_public_id", sa.String(length=36), nullable=True),
        sa.Column("account_public_id", sa.String(length=36), nullable=True),
        sa.Column("units_required", sa.Integer(), nullable=False),
        sa.Column("required_from", sa.Date(), nullable=False),
        # Blank: until the line ends.
        sa.Column("required_to", sa.Date(), nullable=True),
        sa.Column("crew_operators_required", sa.Integer(), nullable=False),
        sa.Column("crew_helpers_required", sa.Integer(), nullable=False),
        sa.Column("crew_notes", sa.UnicodeText(), nullable=True),
        sa.Column("priority_code", sa.String(length=20), nullable=False),
        sa.Column("planning_notes", sa.UnicodeText(), nullable=True),
        sa.Column("requirement_status_code", sa.String(length=20), nullable=False),
        sa.Column("requirement_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        # The structure version the requirement was last saved against.
        sa.Column("taxonomy_version", sa.Integer(), nullable=False),
        sa.Column("cancellation_reason", sa.UnicodeText(), nullable=True),
        sa.Column("cancelled_by", sa.String(length=36), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        # A double-click or a retry creates one requirement, not two (ADR-023).
        sa.Column("create_request_key", sa.String(length=36), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("requirement_public_id", name="uq_resource_requirement_public_id"),
        sa.UniqueConstraint("requirement_reference", name="uq_resource_requirement_reference"),
        sa.UniqueConstraint("create_request_key", name="uq_resource_requirement_create_request_key"),
        sa.ForeignKeyConstraint(
            ["work_order_line_id"], ["crm_work_order_line.id"], name="fk_resource_requirement_work_order_line"
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_version"], [f"{VERSION_TABLE}.version_number"], name="fk_resource_requirement_taxonomy_version"
        ),
        # Who cancelled must be a real user, not merely a non-empty string: a blank or unknown id would
        # leave the cancellation unattributed. Users are disabled, never deleted, so this cannot strand a
        # cancelled requirement.
        sa.ForeignKeyConstraint(
            ["cancelled_by"], ["app_user.public_id"], name="fk_resource_requirement_cancelled_by"
        ),
        sa.CheckConstraint("units_required >= 1", name="ck_resource_requirement_units"),
        sa.CheckConstraint(
            "required_to IS NULL OR required_to >= required_from", name="ck_resource_requirement_dates_ordered"
        ),
        sa.CheckConstraint(
            "crew_operators_required >= 0 AND crew_helpers_required >= 0", name="ck_resource_requirement_crew"
        ),
        sa.CheckConstraint(
            "crew_notes IS NULL OR char_length(crew_notes) <= 2000", name="ck_resource_requirement_crew_notes"
        ),
        sa.CheckConstraint(
            "planning_notes IS NULL OR char_length(planning_notes) <= 4000",
            name="ck_resource_requirement_planning_notes",
        ),
        sa.CheckConstraint("priority_code IN ('NORMAL', 'URGENT')", name="ck_resource_requirement_priority"),
        # PARTLY_FULFILLED, FULFILLED and COMPLETED are reserved for Assignment (8A); this slice's
        # constraint does not accept them.
        sa.CheckConstraint(
            "requirement_status_code IN ('OPEN', 'CANCELLED')", name="ck_resource_requirement_status"
        ),
        sa.CheckConstraint("requirement_version >= 1", name="ck_resource_requirement_version"),
        # The cancellation fields are present exactly when the requirement is cancelled. CASE, not
        # OR: a CHECK rejects only on FALSE, and `NULL = 'CANCELLED'` is NULL.
        sa.CheckConstraint(
            "CASE WHEN requirement_status_code = 'CANCELLED'"
            " THEN cancellation_reason IS NOT NULL AND btrim(cancellation_reason) <> ''"
            " AND char_length(cancellation_reason) <= 2000 AND cancelled_at IS NOT NULL"
            " AND cancelled_by IS NOT NULL"
            " ELSE cancellation_reason IS NULL AND cancelled_by IS NULL AND cancelled_at IS NULL"
            " END",
            name="ck_resource_requirement_cancellation",
        ),
    )
    for index_name, columns in (
        ("ix_resource_requirement_work_order_line", ["work_order_line_id"]),
        ("ix_resource_requirement_work_order", ["work_order_public_id"]),
        ("ix_resource_requirement_planning", ["requirement_status_code", "priority_code", "required_from"]),
    ):
        op.create_index(index_name, REQUIREMENT_TABLE, columns)

    op.create_table(
        ITEM_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_requirement_id", sa.Integer(), nullable=False),
        sa.Column("item_number", sa.Integer(), nullable=False),
        sa.Column("equipment_class_code", sa.String(length=50), nullable=False),
        # Blank: any type in the class.
        sa.Column("equipment_type_code", sa.String(length=50), nullable=True),
        sa.Column("equipment_specification", sa.UnicodeText(), nullable=True),
        sa.UniqueConstraint("resource_requirement_id", "item_number", name="uq_resource_requirement_item_number"),
        # The target of the capability rows' composite key, which keeps each capability on its item's class.
        sa.UniqueConstraint("id", "equipment_class_code", name="uq_resource_requirement_item_class"),
        sa.ForeignKeyConstraint(
            ["resource_requirement_id"], [f"{REQUIREMENT_TABLE}.id"], name="fk_resource_requirement_item_requirement"
        ),
        sa.ForeignKeyConstraint(
            ["equipment_class_code"], [f"{CLASS_TABLE}.class_code"], name="fk_resource_requirement_item_class"
        ),
        sa.ForeignKeyConstraint(
            ["equipment_class_code", "equipment_type_code"],
            [f"{TYPE_TABLE}.class_code", f"{TYPE_TABLE}.type_code"],
            name="fk_resource_requirement_item_class_type",
        ),
        # Exactly one item per requirement in this slice (owner, Q15). The shape holds several so a
        # later migration can drop this when Transportation's combinations arrive; at least one is the
        # service's rule, since a CHECK cannot count rows.
        sa.CheckConstraint("item_number = 1", name="ck_rr_item_single_item_this_slice"),
        sa.CheckConstraint(
            "equipment_specification IS NULL OR char_length(equipment_specification) <= 1000",
            name="ck_resource_requirement_item_specification",
        ),
    )
    op.create_index("ix_resource_requirement_item_requirement", ITEM_TABLE, ["resource_requirement_id"])

    op.create_table(
        ITEM_CAPABILITY_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resource_requirement_item_id", sa.Integer(), nullable=False),
        sa.Column("equipment_class_code", sa.String(length=50), nullable=False),
        sa.Column("capability_code", sa.String(length=50), nullable=False),
        # The least value, in the capability's unit (which is never stored here and cannot be sent).
        sa.Column("minimum_value", sa.Numeric(precision=12, scale=3), nullable=True),
        # For a capability with a fixed list of values, the value required.
        sa.Column("choice_value", sa.String(length=50), nullable=True),
        sa.UniqueConstraint(
            "resource_requirement_item_id", "capability_code", name="uq_resource_requirement_item_capability"
        ),
        sa.ForeignKeyConstraint(
            ["resource_requirement_item_id", "equipment_class_code"],
            [f"{ITEM_TABLE}.id", f"{ITEM_TABLE}.equipment_class_code"],
            name="fk_rr_item_capability_item_class",
        ),
        # Only a capability that applies to the item's class.
        sa.ForeignKeyConstraint(
            ["equipment_class_code", "capability_code"],
            [f"{CLASS_CAPABILITY_TABLE}.class_code", f"{CLASS_CAPABILITY_TABLE}.capability_code"],
            name="fk_rr_item_capability_class_capability",
        ),
        # One value or the other. A least value is above zero and a real number: numeric NaN orders
        # above every number in PostgreSQL, so `> 0` alone would admit it.
        sa.CheckConstraint(
            "CASE WHEN minimum_value IS NULL THEN choice_value IS NOT NULL AND btrim(choice_value) <> ''"
            " ELSE choice_value IS NULL AND minimum_value > 0 AND minimum_value <> 'NaN'::numeric"
            " END",
            name="ck_rr_item_capability_value",
        ),
    )
    op.create_index(
        "ix_rr_item_capability_item", ITEM_CAPABILITY_TABLE, ["resource_requirement_item_id"]
    )
    # The value must fit its capability, which lives in another table. No `%` and no colon in the body:
    # the statement passes through SQLAlchemy's text() and the driver's placeholder parsing.
    op.execute(
        """
        CREATE FUNCTION rr_item_capability_matches_kind() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        DECLARE
            kind varchar(20);
            unit varchar(50);
            allowed varchar(50)[];
        BEGIN
            SELECT value_kind_code, unit_code, allowed_values INTO kind, unit, allowed
            FROM equipment_capability WHERE capability_code = NEW.capability_code;
            IF kind = 'CHOICE' THEN
                IF NEW.minimum_value IS NOT NULL OR NEW.choice_value IS NULL
                   OR NOT COALESCE(NEW.choice_value = ANY (allowed), FALSE) THEN
                    RAISE EXCEPTION USING
                        ERRCODE = 'check_violation',
                        CONSTRAINT = 'ck_rr_item_capability_matches_kind',
                        MESSAGE = NEW.capability_code || ' takes one of its listed values, and nothing else.';
                END IF;
            ELSIF NEW.choice_value IS NOT NULL OR NEW.minimum_value IS NULL
                  OR (unit = 'COUNT' AND NEW.minimum_value <> trunc(NEW.minimum_value)) THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_rr_item_capability_matches_kind',
                    MESSAGE = NEW.capability_code || ' takes a least value in its own unit, whole where it is counted.';
            END IF;
            RETURN NEW;
        END
        $body$
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER trg_rr_item_capability_matches_kind
        BEFORE INSERT OR UPDATE ON {ITEM_CAPABILITY_TABLE}
        FOR EACH ROW EXECUTE FUNCTION rr_item_capability_matches_kind()
        """
    )


def _seed_permissions() -> None:
    """Insert each permission row and its role grants, as 20260908_0036 to 0040 do."""
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
    connection.execute(
        sa.text("DELETE FROM authz_permission WHERE permission_code = ANY(:codes)"),
        {"codes": codes},
    )

    op.execute(f"DROP TRIGGER IF EXISTS trg_rr_item_capability_matches_kind ON {ITEM_CAPABILITY_TABLE}")
    op.execute("DROP FUNCTION IF EXISTS rr_item_capability_matches_kind()")
    op.drop_table(ITEM_CAPABILITY_TABLE)
    op.drop_table(ITEM_TABLE)
    op.drop_table(REQUIREMENT_TABLE)
    op.drop_table(ALIAS_TABLE)
    op.drop_table(CLASS_CAPABILITY_TABLE)
    op.drop_table(CAPABILITY_TABLE)
    op.drop_table(TYPE_TABLE)
    op.drop_table(CLASS_LINE_TABLE)
    op.drop_table(CLASS_TABLE)
    op.drop_table(VERSION_TABLE)
