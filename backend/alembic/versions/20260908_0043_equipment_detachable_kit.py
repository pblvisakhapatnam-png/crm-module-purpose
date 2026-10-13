"""equipment detachable kit, held for the crane models it fits (ERT-2)

Design: docs/agent/slices/ert-2-detachable-kit.md (every question answered by the owner, 26 September
2026), sections 5 and 11. Everything is the Equipment Reference module's; no other module's table is
touched.

**Structure, version 3.** Four kinds of kit, as part classes offered to no business line: Boom and jib
section, Counterweight, Hook block and Lifting tackle (owner, Q1). Each is kit for Crane, not fitted to it:
`equipment_part_fit.fit_kind_code` says which, and the carrier's row stays `FITTED`. A kind is tracked one
by one or counted (`equipment_class.tracking_code`; counterweight counted, Q3). Two capabilities, Length and
Weight, are added; weight measures every kind of kit (Q13). `equipment_taxonomy_version.component_depth`
is the depth setting (Q9): 1 for version 1, 2 for version 2, 3 for version 3; the current version's is in
force. A part class may now be the parent of a fitted part fit, so fitted parts can nest to that depth.

**Kit models** name the crane models they fit, one or more (Q12): `equipment_model_fit`. Composite keys
hold that the kit model's class is kit for the crane model's class, and that neither model changes class
while the row exists. A model may carry the maker's part number (Q13).

**Pieces of kit** are `equipment_asset` rows of origin `PLATFORM`: no Plum machine number, a model always,
a quantity above one only for a counted kind, a request key so "add several alike" has one effect. They are
never linked to a crane (Q6): kit is held for the models it fits. A retired piece records the date, the
reason (scrapped, lost, sold, recorded by mistake, or other with a note; Q8, Q14) and a note. Every
existing asset becomes origin `PLUM`, unchanged.

Spells out version 3 rather than importing it, so this revision stays a frozen historical snapshot (the
20260908_0033 to 0042 convention). The trigger bodies hold no `%` and no colon: they pass through
SQLAlchemy's text() and the driver's placeholder parsing.

Revision ID: 20260908_0043
Revises: 20260908_0042
Create Date: 2026-09-26
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0043"
down_revision: Union[str, None] = "20260908_0042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


VERSION_TABLE = "equipment_taxonomy_version"
CLASS_TABLE = "equipment_class"
TYPE_TABLE = "equipment_type"
CAPABILITY_TABLE = "equipment_capability"
CLASS_CAPABILITY_TABLE = "equipment_class_capability"
PART_FIT_TABLE = "equipment_part_fit"
MODEL_TABLE = "equipment_model"
MODEL_CAPABILITY_TABLE = "equipment_model_capability"
MODEL_FIT_TABLE = "equipment_model_fit"
MODEL_SOURCE_KEY_TABLE = "equipment_model_source_key"
ASSET_TABLE = "equipment_asset"
ASSET_CAPABILITY_TABLE = "equipment_asset_capability"
ASSET_FLAG_TABLE = "equipment_asset_flag"
ASSET_LINK_TABLE = "equipment_asset_link"

VERSION_3_LABEL = "Version 3"
VERSION_3_SOURCE = (
    "ERT-2 design, every question answered by the owner on 26 September 2026: the detachable kit cranes are "
    "configured from - boom and jib sections, counterweight, hook blocks and lifting tackle - as kinds of kit "
    "held for the crane models they fit, and the depth setting of 3."
)
# The depth each version allowed: version 1 had no parts; version 2 fitted one part level; version 3 is the
# owner's setting (Q9).
COMPONENT_DEPTHS = {1: 1, 2: 2, 3: 3}

# capability_code: (label, unit_code) - both measured, MINIMUM, as every measured capability is.
CAPABILITIES: dict[str, tuple[str, str]] = {
    "LENGTH": ("Length", "METRE"),
    "WEIGHT": ("Weight", "TONNE"),
}

# class_code: (label, display order, tracking, [(type_code, type_label)], [capability_code], key capability)
# After Crane carrier (130). No business-line row: offered to no business line. Each is kit for Crane.
KIT_CLASSES: dict[str, tuple[str, int, str, tuple[tuple[str, str], ...], tuple[str, ...], str]] = {
    "BOOM_JIB_SECTION": (
        "Boom and jib section",
        140,
        "SINGLE",
        (
            ("MAIN_BOOM_FOOT", "Main boom foot (butt)"),
            ("MAIN_BOOM_INSERT", "Main boom insert"),
            ("MAIN_BOOM_HEAD", "Main boom head (top)"),
            ("LUFFING_JIB_SECTION", "Luffing jib section"),
            ("FIXED_JIB_SECTION", "Fixed jib section"),
            ("FOLDING_JIB", "Folding (swing-away) jib"),
            ("STRUT_OR_MAST", "Strut or mast"),
        ),
        ("LENGTH", "WEIGHT"),
        "LENGTH",
    ),
    "COUNTERWEIGHT": (
        "Counterweight",
        150,
        "COUNTED",
        (
            ("UPPER_COUNTERWEIGHT", "Upper counterweight (plate or box)"),
            ("COUNTERWEIGHT_TRAY", "Counterweight tray"),
            ("CARBODY_BALLAST", "Carbody (central) ballast"),
            ("SUPERLIFT_BALLAST", "Superlift or derrick ballast"),
        ),
        ("WEIGHT",),
        "WEIGHT",
    ),
    "HOOK_BLOCK": (
        "Hook block",
        160,
        "SINGLE",
        (("HOOK_BLOCK", "Hook block"), ("SINGLE_LINE_HOOK", "Single-line hook or weight ball")),
        ("RATED_CAPACITY", "WEIGHT"),
        "RATED_CAPACITY",
    ),
    "LIFTING_TACKLE": (
        "Lifting tackle",
        170,
        "SINGLE",
        (
            ("HANDLING_PENDANT", "Counterweight-handling pendant or link"),
            ("SPREADER_BEAM", "Spreader or lifting beam"),
            ("SLING", "Sling"),
            ("SHACKLE", "Shackle"),
        ),
        ("RATED_CAPACITY", "WEIGHT"),
        "RATED_CAPACITY",
    ),
}
KIT_PARENT_CLASS = "CRANE"

RETIREMENT_REASONS = ("SCRAPPED", "LOST", "SOLD", "RECORDED_BY_MISTAKE", "OTHER")


def _in(values: Sequence[str]) -> str:
    return "(" + ", ".join(f"'{value}'" for value in values) + ")"


def upgrade() -> None:
    _load_version_3()
    _extend_models()
    _extend_assets()
    _create_asset_trigger()
    _check_the_structure()


def _load_version_3() -> None:
    connection = op.get_bind()
    op.add_column(VERSION_TABLE, sa.Column("component_depth", sa.Integer(), nullable=True))
    for version_number, depth in COMPONENT_DEPTHS.items():
        if version_number < 3:
            connection.execute(
                sa.text(f"UPDATE {VERSION_TABLE} SET component_depth = :depth WHERE version_number = :version"),
                {"depth": depth, "version": version_number},
            )
    connection.execute(
        sa.text(
            f"INSERT INTO {VERSION_TABLE} (version_number, version_label, source_note, component_depth) "
            "VALUES (3, :label, :source, :depth)"
        ),
        {"label": VERSION_3_LABEL, "source": VERSION_3_SOURCE, "depth": COMPONENT_DEPTHS[3]},
    )
    op.alter_column(VERSION_TABLE, "component_depth", nullable=False)
    op.create_check_constraint(
        "ck_equipment_taxonomy_version_component_depth", VERSION_TABLE, "component_depth BETWEEN 1 AND 10"
    )

    # One by one, or counted. A machine is always one record for one machine.
    op.add_column(
        CLASS_TABLE,
        sa.Column("tracking_code", sa.String(length=20), nullable=False, server_default=sa.text("'SINGLE'")),
    )
    op.create_check_constraint(
        "ck_equipment_class_tracking",
        CLASS_TABLE,
        "tracking_code IN ('SINGLE', 'COUNTED') AND (class_kind_code = 'PART' OR tracking_code = 'SINGLE')",
    )

    # Fitted (always part of the machine, a dated link) or kit (held for the models it fits, never linked).
    op.add_column(
        PART_FIT_TABLE,
        sa.Column("fit_kind_code", sa.String(length=20), nullable=False, server_default=sa.text("'FITTED'")),
    )
    op.create_check_constraint("ck_equipment_part_fit_kind", PART_FIT_TABLE, "fit_kind_code IN ('FITTED', 'KIT')")
    # A part class may now carry fitted parts of its own (the depth setting); kit hangs off machine classes.
    op.drop_constraint("ck_equipment_part_fit_parent_kind", PART_FIT_TABLE, type_="check")
    op.create_check_constraint(
        "ck_equipment_part_fit_parent_kind",
        PART_FIT_TABLE,
        "parent_class_kind_code IN ('MACHINE', 'PART') AND (fit_kind_code = 'FITTED' OR parent_class_kind_code = 'MACHINE')",
    )
    # The target of the model fit's composite key: a kit model fits a crane model only where its class is kit
    # for the crane model's class.
    op.create_unique_constraint(
        "uq_equipment_part_fit_kind", PART_FIT_TABLE, ["part_class_code", "parent_class_code", "fit_kind_code"]
    )

    for capability_code, (label, unit_code) in CAPABILITIES.items():
        connection.execute(
            sa.text(
                f"INSERT INTO {CAPABILITY_TABLE} "
                "(capability_code, capability_label, unit_code, value_kind_code, introduced_in_version) "
                "VALUES (:code, :label, :unit_code, 'MINIMUM', 3)"
            ),
            {"code": capability_code, "label": label, "unit_code": unit_code},
        )

    for class_code, (label, display_order, tracking, types, capabilities, key) in KIT_CLASSES.items():
        connection.execute(
            sa.text(
                f"INSERT INTO {CLASS_TABLE} "
                "(class_code, class_label, display_order, introduced_in_version, class_kind_code, tracking_code) "
                "VALUES (:code, :label, :display_order, 3, 'PART', :tracking)"
            ),
            {"code": class_code, "label": label, "display_order": display_order, "tracking": tracking},
        )
        for type_order, (type_code, type_label) in enumerate(types, 1):
            connection.execute(
                sa.text(
                    f"INSERT INTO {TYPE_TABLE} (type_code, class_code, type_label, display_order, introduced_in_version) "
                    "VALUES (:type_code, :class_code, :label, :display_order, 3)"
                ),
                {"type_code": type_code, "class_code": class_code, "label": type_label, "display_order": type_order * 10},
            )
        for capability_order, capability_code in enumerate(capabilities, 1):
            connection.execute(
                sa.text(
                    f"INSERT INTO {CLASS_CAPABILITY_TABLE} "
                    "(class_code, capability_code, is_key, display_order, introduced_in_version) "
                    "VALUES (:class_code, :capability_code, :is_key, :display_order, 3)"
                ),
                {
                    "class_code": class_code,
                    "capability_code": capability_code,
                    "is_key": capability_code == key,
                    "display_order": capability_order * 10,
                },
            )
        connection.execute(
            sa.text(
                f"INSERT INTO {PART_FIT_TABLE} (part_class_code, parent_class_code, introduced_in_version, fit_kind_code) "
                "VALUES (:part_class, :parent_class, 3, 'KIT')"
            ),
            {"part_class": class_code, "parent_class": KIT_PARENT_CLASS},
        )


def _extend_models() -> None:
    op.add_column(MODEL_TABLE, sa.Column("maker_part_number", sa.Unicode(length=100), nullable=True))
    op.create_check_constraint(
        "ck_equipment_model_maker_part_number",
        MODEL_TABLE,
        "CASE WHEN maker_part_number IS NULL THEN TRUE "
        "ELSE btrim(maker_part_number) <> '' AND char_length(maker_part_number) <= 100 END",
    )

    op.create_table(
        MODEL_FIT_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kit_model_id", sa.Integer(), nullable=False),
        sa.Column("kit_class_code", sa.String(length=50), nullable=False),
        sa.Column("crane_model_id", sa.Integer(), nullable=False),
        sa.Column("crane_class_code", sa.String(length=50), nullable=False),
        # A constant, so the composite key below can require the part fit to be kit, not fitted.
        sa.Column("fit_kind_code", sa.String(length=20), nullable=False, server_default=sa.text("'KIT'")),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("kit_model_id", "crane_model_id", name="uq_equipment_model_fit"),
        # Each end is the model with that class: neither model's class can change while the row exists.
        sa.ForeignKeyConstraint(
            ["kit_model_id", "kit_class_code"],
            [f"{MODEL_TABLE}.id", f"{MODEL_TABLE}.class_code"],
            name="fk_equipment_model_fit_kit_model",
        ),
        sa.ForeignKeyConstraint(
            ["crane_model_id", "crane_class_code"],
            [f"{MODEL_TABLE}.id", f"{MODEL_TABLE}.class_code"],
            name="fk_equipment_model_fit_crane_model",
        ),
        # The kit model's class is kit for the crane model's class (and so the crane model's class is a
        # machine class: a kit fit's parent always is, ck_equipment_part_fit_parent_kind).
        sa.ForeignKeyConstraint(
            ["kit_class_code", "crane_class_code", "fit_kind_code"],
            [f"{PART_FIT_TABLE}.part_class_code", f"{PART_FIT_TABLE}.parent_class_code", f"{PART_FIT_TABLE}.fit_kind_code"],
            name="fk_equipment_model_fit_part_fit",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.public_id"], name="fk_equipment_model_fit_created_by"),
        sa.CheckConstraint("fit_kind_code = 'KIT'", name="ck_equipment_model_fit_kind"),
        sa.CheckConstraint("kit_model_id <> crane_model_id", name="ck_equipment_model_fit_not_itself"),
    )
    op.create_index("ix_equipment_model_fit_crane_model", MODEL_FIT_TABLE, ["crane_model_id"])


def _extend_assets() -> None:
    op.add_column(
        ASSET_TABLE,
        sa.Column("origin_code", sa.String(length=20), nullable=False, server_default=sa.text("'PLUM'")),
    )
    op.add_column(ASSET_TABLE, sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")))
    # "Add several alike" is one request with one effect (ADR-023): each record it made holds its position.
    op.add_column(ASSET_TABLE, sa.Column("create_request_key", sa.String(length=36), nullable=True))
    op.add_column(ASSET_TABLE, sa.Column("create_request_position", sa.Integer(), nullable=True))
    # The kit model the request added - fixed, though a piece's own model may change later: a repeated request
    # is judged by what it first asked for (independent review, round 2, ERT2-R2-001).
    op.add_column(ASSET_TABLE, sa.Column("create_request_model_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_equipment_asset_create_request_model", ASSET_TABLE, MODEL_TABLE, ["create_request_model_id"], ["id"]
    )
    op.add_column(ASSET_TABLE, sa.Column("retired_on", sa.Date(), nullable=True))
    op.add_column(ASSET_TABLE, sa.Column("retirement_reason_code", sa.String(length=30), nullable=True))
    op.add_column(ASSET_TABLE, sa.Column("retirement_note", sa.UnicodeText(), nullable=True))

    # Kit has no Plum machine number: the machine number is Plum's key, and kit has no Plum row.
    op.drop_constraint("ck_equipment_asset_machine_number", ASSET_TABLE, type_="check")
    op.alter_column(ASSET_TABLE, "machine_number", nullable=True)
    op.create_check_constraint(
        "ck_equipment_asset_origin",
        ASSET_TABLE,
        "CASE origin_code"
        " WHEN 'PLUM' THEN machine_number IS NOT NULL AND btrim(machine_number) <> ''"
        " AND char_length(machine_number) <= 200 AND quantity = 1"
        " AND create_request_key IS NULL AND create_request_position IS NULL AND create_request_model_id IS NULL"
        " WHEN 'PLATFORM' THEN machine_number IS NULL AND asset_kind_code = 'PART'"
        " AND registered_by_import_id IS NULL AND equipment_model_id IS NOT NULL"
        " AND create_request_key IS NOT NULL AND create_request_position IS NOT NULL"
        " AND create_request_model_id IS NOT NULL"
        " AND create_request_position >= 1"
        " ELSE FALSE END",
    )
    op.create_check_constraint("ck_equipment_asset_quantity", ASSET_TABLE, "quantity >= 1")
    op.create_unique_constraint(
        "uq_equipment_asset_create_request", ASSET_TABLE, ["create_request_key", "create_request_position"]
    )
    # A retired piece of kit carries its date and reason, "other" with a note; nothing else carries them.
    op.create_check_constraint(
        "ck_equipment_asset_retirement",
        ASSET_TABLE,
        "CASE WHEN origin_code = 'PLATFORM' AND asset_status_code = 'RETIRED'"
        # The reason is tested NOT NULL first: an IN on NULL is NULL, which a CHECK lets pass (ERT2-R4-001).
        " THEN retired_on IS NOT NULL AND retirement_reason_code IS NOT NULL"
        f" AND retirement_reason_code IN {_in(RETIREMENT_REASONS)}"
        " AND CASE WHEN retirement_note IS NULL THEN retirement_reason_code <> 'OTHER'"
        " ELSE btrim(retirement_note) <> '' AND char_length(retirement_note) <= 1000 END"
        " ELSE retired_on IS NULL AND retirement_reason_code IS NULL AND retirement_note IS NULL END",
    )
    op.create_index("ix_equipment_asset_origin", ASSET_TABLE, ["origin_code", "equipment_model_id"])


def _create_asset_trigger() -> None:
    """What a CHECK cannot see, because it lives in the class and part-fit tables or in the row before the
    change: a quantity above one only on a counted kind, a piece's own number only on a kind tracked one by
    one, a platform-made asset only of a kind of kit and a kind of kit only platform-made, and the request that
    made a record never changed."""
    op.execute(
        """
        CREATE FUNCTION equipment_asset_matches_tracking() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        DECLARE
            tracking varchar(20);
            is_kit boolean;
        BEGIN
            SELECT tracking_code INTO tracking FROM equipment_class WHERE class_code = NEW.class_code;
            is_kit := EXISTS (
                SELECT 1 FROM equipment_part_fit WHERE part_class_code = NEW.class_code AND fit_kind_code = 'KIT'
            );
            IF NEW.quantity > 1 AND tracking IS DISTINCT FROM 'COUNTED' THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_equipment_asset_matches_tracking',
                    MESSAGE = NEW.class_code || ' is tracked one by one, so a record holds one piece.';
            END IF;
            IF NEW.serial_number IS NOT NULL AND tracking = 'COUNTED' THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_equipment_asset_matches_tracking',
                    MESSAGE = NEW.class_code || ' is counted, so a record carries no number of its own.';
            END IF;
            IF NEW.origin_code = 'PLATFORM' AND NOT is_kit THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_equipment_asset_matches_tracking',
                    MESSAGE = 'Only kit is recorded on the platform, and ' || NEW.class_code || ' is not a kind of kit.';
            END IF;
            -- And kit is only recorded on the platform, never read from Plum (ERT2-R4-002).
            IF NEW.origin_code = 'PLUM' AND is_kit THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_equipment_asset_matches_tracking',
                    MESSAGE = NEW.class_code || ' is a kind of kit: kit is recorded on the platform, never read from Plum.';
            END IF;
            -- The request that made a record - its key, its place in the lot, the model asked for - never
            -- changes: a repeated request is judged by it (ERT2-R2-001).
            IF TG_OP = 'UPDATE' AND (
                NEW.create_request_key IS DISTINCT FROM OLD.create_request_key
                OR NEW.create_request_position IS DISTINCT FROM OLD.create_request_position
                OR NEW.create_request_model_id IS DISTINCT FROM OLD.create_request_model_id
            ) THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_equipment_asset_matches_tracking',
                    MESSAGE = 'The request that made a record never changes.';
            END IF;
            RETURN NEW;
        END
        $body$
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER trg_{ASSET_TABLE}_matches_tracking
        BEFORE INSERT OR UPDATE ON {ASSET_TABLE}
        FOR EACH ROW EXECUTE FUNCTION equipment_asset_matches_tracking()
        """
    )
    # The same two rules from the class's side: a later structure version cannot change a kind's tracking
    # under records it no longer fits (design section 13 - tracking moving to the model is a new decision).
    op.execute(
        f"""
        CREATE FUNCTION equipment_class_tracking_matches_assets() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM {ASSET_TABLE}
                WHERE class_code = NEW.class_code
                  AND ((NEW.tracking_code <> 'COUNTED' AND quantity > 1)
                    OR (NEW.tracking_code = 'COUNTED' AND serial_number IS NOT NULL))
            ) THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_equipment_asset_matches_tracking',
                    MESSAGE = 'Records of ' || NEW.class_code || ' do not fit tracking ' || NEW.tracking_code || '.';
            END IF;
            RETURN NEW;
        END
        $body$
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER trg_{CLASS_TABLE}_tracking_matches_assets
        BEFORE UPDATE OF tracking_code ON {CLASS_TABLE}
        FOR EACH ROW EXECUTE FUNCTION equipment_class_tracking_matches_assets()
        """
    )


def _check_the_structure() -> None:
    """The part fits hold no loop, and no chain of parts is deeper than the current depth setting (design
    section 5, "The rules"). A migration that breaks either stops here, rolled back whole."""
    connection = op.get_bind()
    depth = connection.execute(
        sa.text(f"SELECT component_depth FROM {VERSION_TABLE} ORDER BY version_number DESC LIMIT 1")
    ).scalar_one()
    parents: dict[str, set[str]] = {}
    for part_class, parent_class in connection.execute(
        sa.text(f"SELECT part_class_code, parent_class_code FROM {PART_FIT_TABLE} WHERE retired_in_version IS NULL")
    ).fetchall():
        parents.setdefault(str(part_class), set()).add(str(parent_class))

    def levels(class_code: str, seen: tuple[str, ...]) -> int:
        if class_code in seen:
            raise RuntimeError(f"The part fits loop through {class_code}.")
        above = parents.get(class_code, set())
        return 1 + max((levels(parent, seen + (class_code,)) for parent in above), default=0)

    for class_code in parents:
        if levels(class_code, ()) > depth:
            raise RuntimeError(f"{class_code} would sit deeper than the depth setting of {depth}.")
    # Open links too: a fit retired in a later version may leave links below it, and the setting may not
    # fall below the deepest chain of them. The walk starts from every asset - a loop has no top to start
    # from - carries its path to see a loop, and stops past the setting (independent review, ERT2-R1-005).
    deepest, looped = connection.execute(
        sa.text(
            f"""
            WITH RECURSIVE chain(asset_id, level, path, looped) AS (
                SELECT a.id, 1, ARRAY[a.id], FALSE FROM {ASSET_TABLE} a
                UNION ALL
                SELECT l.child_asset_id, chain.level + 1, chain.path || l.child_asset_id,
                       l.child_asset_id = ANY(chain.path)
                FROM {ASSET_LINK_TABLE} l INNER JOIN chain ON l.parent_asset_id = chain.asset_id
                WHERE l.removed_on IS NULL AND NOT chain.looped AND chain.level <= :depth
            )
            SELECT COALESCE(MAX(level), 1), COALESCE(BOOL_OR(looped), FALSE) FROM chain
            """
        ),
        {"depth": depth},
    ).one()
    if looped:
        raise RuntimeError("Open fitted links loop: a part is fitted, through others, below itself.")
    if deepest > depth:
        raise RuntimeError(f"Open fitted links reach {deepest} levels, deeper than the depth setting of {depth}.")
    # Records as the structure now says: kit only on the platform, and the platform only kit. The trigger holds
    # it row by row; a later version that makes a kind kit, or stops it being kit, is checked here (ERT2-R4-002).
    misplaced = connection.execute(
        sa.text(
            f"""
            SELECT COUNT(*) FROM {ASSET_TABLE} a
            WHERE (a.origin_code = 'PLATFORM') <> EXISTS (
                SELECT 1 FROM {PART_FIT_TABLE} f WHERE f.part_class_code = a.class_code AND f.fit_kind_code = 'KIT'
            )
            """
        )
    ).scalar_one()
    if misplaced:
        raise RuntimeError(f"{misplaced} record(s) disagree with the structure: kit is recorded only on the platform, and only kit.")


def downgrade() -> None:
    """Remove version 3 and everything made with it. Kit models and pieces are removed with it: their classes
    are version 3's."""
    connection = op.get_bind()
    kit_classes = list(KIT_CLASSES)
    op.execute(f"DROP TRIGGER IF EXISTS trg_{ASSET_TABLE}_matches_tracking ON {ASSET_TABLE}")
    op.execute("DROP FUNCTION IF EXISTS equipment_asset_matches_tracking()")
    op.execute(f"DROP TRIGGER IF EXISTS trg_{CLASS_TABLE}_tracking_matches_assets ON {CLASS_TABLE}")
    op.execute("DROP FUNCTION IF EXISTS equipment_class_tracking_matches_assets()")
    for table in (ASSET_FLAG_TABLE, ASSET_CAPABILITY_TABLE):
        connection.execute(
            sa.text(
                f"DELETE FROM {table} WHERE equipment_asset_id IN (SELECT id FROM {ASSET_TABLE} WHERE origin_code = 'PLATFORM')"
            )
        )
    connection.execute(sa.text(f"DELETE FROM {ASSET_TABLE} WHERE origin_code = 'PLATFORM'"))
    op.drop_table(MODEL_FIT_TABLE)
    # No Plum name is mapped to a kit model (the service refuses it); should one be, it goes with the model
    # rather than stopping the downgrade (independent review, round 3, ERT2-R3-001).
    for table in (MODEL_SOURCE_KEY_TABLE, MODEL_CAPABILITY_TABLE):
        connection.execute(
            sa.text(
                f"DELETE FROM {table} WHERE equipment_model_id IN (SELECT id FROM {MODEL_TABLE} WHERE class_code = ANY(:classes))"
            ),
            {"classes": kit_classes},
        )
    connection.execute(sa.text(f"DELETE FROM {MODEL_TABLE} WHERE class_code = ANY(:classes)"), {"classes": kit_classes})

    op.drop_index("ix_equipment_asset_origin", ASSET_TABLE)
    for name in ("ck_equipment_asset_retirement", "uq_equipment_asset_create_request", "ck_equipment_asset_quantity", "ck_equipment_asset_origin"):
        op.drop_constraint(name, ASSET_TABLE, type_="unique" if name.startswith("uq_") else "check")
    op.alter_column(ASSET_TABLE, "machine_number", nullable=False)
    op.create_check_constraint(
        "ck_equipment_asset_machine_number",
        ASSET_TABLE,
        "btrim(machine_number) <> '' AND char_length(machine_number) <= 200",
    )
    op.drop_constraint("fk_equipment_asset_create_request_model", ASSET_TABLE, type_="foreignkey")
    for column in (
        "retirement_note",
        "retirement_reason_code",
        "retired_on",
        "create_request_model_id",
        "create_request_position",
        "create_request_key",
        "quantity",
        "origin_code",
    ):
        op.drop_column(ASSET_TABLE, column)

    op.drop_constraint("ck_equipment_model_maker_part_number", MODEL_TABLE, type_="check")
    op.drop_column(MODEL_TABLE, "maker_part_number")

    connection.execute(sa.text(f"DELETE FROM {PART_FIT_TABLE} WHERE part_class_code = ANY(:classes)"), {"classes": kit_classes})
    connection.execute(sa.text(f"DELETE FROM {CLASS_CAPABILITY_TABLE} WHERE class_code = ANY(:classes)"), {"classes": kit_classes})
    connection.execute(sa.text(f"DELETE FROM {TYPE_TABLE} WHERE class_code = ANY(:classes)"), {"classes": kit_classes})
    connection.execute(sa.text(f"DELETE FROM {CLASS_TABLE} WHERE class_code = ANY(:classes)"), {"classes": kit_classes})
    connection.execute(
        sa.text(f"DELETE FROM {CAPABILITY_TABLE} WHERE capability_code = ANY(:codes)"), {"codes": list(CAPABILITIES)}
    )
    op.drop_constraint("uq_equipment_part_fit_kind", PART_FIT_TABLE, type_="unique")
    op.drop_constraint("ck_equipment_part_fit_parent_kind", PART_FIT_TABLE, type_="check")
    op.create_check_constraint(
        "ck_equipment_part_fit_parent_kind", PART_FIT_TABLE, "parent_class_kind_code = 'MACHINE'"
    )
    op.drop_constraint("ck_equipment_part_fit_kind", PART_FIT_TABLE, type_="check")
    op.drop_column(PART_FIT_TABLE, "fit_kind_code")
    op.drop_constraint("ck_equipment_class_tracking", CLASS_TABLE, type_="check")
    op.drop_column(CLASS_TABLE, "tracking_code")
    connection.execute(sa.text(f"DELETE FROM {VERSION_TABLE} WHERE version_number = 3"))
    op.drop_constraint("ck_equipment_taxonomy_version_component_depth", VERSION_TABLE, type_="check")
    op.drop_column(VERSION_TABLE, "component_depth")
