"""Plum's vehicle report, read and transformed into the Equipment Reference (ERT-1). Adapter-owned.

Design: docs/agent/slices/ert-1-plum-machines-into-the-equipment-reference.md, sections 3 to 8.

Pure: no database and no clock. `read_report` turns the uploaded file into rows holding only the values
the transformer uses (section 3) - never PAN, insurance or finance columns. `compute_preview` turns those
rows, and everything the platform holds that they are read against (`TransformContext`), into what a
confirmation would do: which machines are new, changed, retired or reactivated, what is set aside and
why, the flags, the corrections applied, the model names still to map and the crane halves to pair.
`derive_row` is the part of it that reads one row, and is also what re-reads one machine after the Fleet
Admin corrects it.

The order within a row is the design's: the Fleet Admin's value rules and machine corrections first
(section 5B), so every later step reads values as the Fleet Admin has said they are to be read; then the
class from the category, the model from the model name, and the capacity check against the model.
Nothing is ever taken from Plum's capacity figure: it is only checked (Q5).
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from app.modules.equipment_reference.contract import (
    ASSET_KIND_MACHINE,
    ASSET_KIND_PART,
    ASSET_STATUS_ACTIVE,
    ASSET_STATUS_RETIRED,
    CATEGORY_CHECKED,
    CATEGORY_UNIT_UNCLEAR,
    CORRECTION_FIELD_CAPACITY,
    CORRECTION_FIELD_CATEGORY,
    CORRECTION_FIELD_CHASSIS_NUMBER,
    CORRECTION_FIELD_COMMENCED_YEAR,
    CORRECTION_FIELD_ENGINE_NUMBER,
    CORRECTION_FIELD_MODEL,
    CORRECTION_FIELD_OWNING_COMPANY,
    CORRECTION_FIELD_STATUS,
    DATA_QUALITY_CATEGORY_NOT_MAPPED,
    DATA_QUALITY_CLASS_DISAGREES,
    DATA_QUALITY_DIFFERS_FROM_MODEL,
    DATA_QUALITY_DUPLICATE_SOURCE_KEY,
    DATA_QUALITY_MODEL_NOT_MAPPED,
    DATA_QUALITY_NOT_A_NUMBER,
    DATA_QUALITY_NOT_IN_LATEST_REPORT,
    DATA_QUALITY_OUT_OF_PATTERN,
    DATA_QUALITY_PART_NOT_FITTED,
    DATA_QUALITY_PLUM_CHANGED_CORRECTED_VALUE,
    DATA_QUALITY_POSSIBLY_RENUMBERED,
    DATA_QUALITY_UNIT_UNCLEAR,
    DATA_QUALITY_VALUE_MISSING,
    EARLIEST_YEAR,
    MAX_REPORT_ROWS,
    TEXT_VALUE_MAX_LENGTH,
    VALUE_RULE_NOT_A_VALUE,
    VALUE_RULE_REASSIGN_TO_TYPE,
    VALUE_RULE_SPLIT_NUMBER_AND_UNIT,
    normalize_term,
)

# --- Reading the file ------------------------------------------------------------------------------

# The row field each used Plum column fills (design section 3). Every other column - PAN, insurance,
# purchase, finance posting accounts, GPS, tyres, weights - is never read into anything.
PLUM_COLUMNS: dict[str, str] = {
    "machine_number": "VehicleNo",
    "schedule_type": "ScheduleMaintanceType",
    "make": "Make",
    "model": "Model",
    "category": "VehCategory",
    "status_text": "Status",
    "capacity": "Capacity",
    "load_capacity": "LoadCapacity",
    "engine_number": "EngineNo",
    "chassis_number": "ChassisNo",
    "commenced_year": "CommencedYear",
    "owning_company": "Owner",
    "bed_number": "BedNo",
}
ROW_FIELDS: tuple[str, ...] = tuple(PLUM_COLUMNS)
# The header may sit below a title line; it is looked for in the first few lines.
HEADER_SEARCH_LINES = 5


class ReportReadError(ValueError):
    """The file is not a report the transformer can read. The message says why, for the Fleet Admin."""


@dataclass(frozen=True)
class ReportRow:
    """One row of the report: its line in the file and the used values only, trimmed, blank as None."""

    row_number: int
    machine_number: str | None = None
    schedule_type: str | None = None
    make: str | None = None
    model: str | None = None
    category: str | None = None
    status_text: str | None = None
    capacity: str | None = None
    load_capacity: str | None = None
    engine_number: str | None = None
    chassis_number: str | None = None
    commenced_year: str | None = None
    owning_company: str | None = None
    bed_number: str | None = None
    # Set when any used value is longer than the platform stores; the row is then set aside.
    too_long: bool = False

    def values(self) -> dict[str, str | None]:
        return {name: getattr(self, name) for name in ROW_FIELDS}


def row_from_values(row_number: int, values: dict[str, Any], *, too_long: bool = False) -> ReportRow:
    """A row rebuilt from stored used values (an import row, or a binding's last values)."""
    return ReportRow(row_number=row_number, too_long=too_long, **{name: _cell(values.get(name)) for name in ROW_FIELDS})


def _cell(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _decode(content: bytes) -> str:
    # Plum's export may be UTF-8 (with or without a byte-order mark) or a Windows code page.
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ReportReadError("This file could not be read as text. Export Plum's report as CSV and upload that file.")


def _header_key(name: str) -> str:
    return "".join(name.split()).upper()


def read_report(content: bytes, *, max_rows: int = MAX_REPORT_ROWS) -> list[ReportRow]:
    """The report's rows, holding only the used values. Refuses a file without every used column."""
    if not content:
        raise ReportReadError("The file is empty.")
    text = _decode(content)
    # Each record with the line of the file it starts on, which a quoted value spanning lines moves on.
    lines: list[list[str]] = []
    line_numbers: list[int] = []
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        previous_end = 0
        for cells in reader:
            lines.append(cells)
            line_numbers.append(previous_end + 1)
            previous_end = reader.line_num
    except csv.Error as exc:
        raise ReportReadError("This file is not a readable CSV file.") from exc

    wanted = {_header_key(column): field_name for field_name, column in PLUM_COLUMNS.items()}
    header_index: int | None = None
    best_missing: list[str] | None = None
    for index, cells in enumerate(lines[:HEADER_SEARCH_LINES]):
        present = {_header_key(cell) for cell in cells}
        missing = [column for column in PLUM_COLUMNS.values() if _header_key(column) not in present]
        if not missing:
            header_index = index
            break
        if len(missing) < len(PLUM_COLUMNS) and (best_missing is None or len(missing) < len(best_missing)):
            best_missing = missing
    if header_index is None:
        if best_missing:
            raise ReportReadError(
                "This report's header is missing the column"
                f"{'s' if len(best_missing) > 1 else ''} {', '.join(best_missing)}. Export the full vehicle report "
                "from Plum."
            )
        raise ReportReadError(
            "This file is not Plum's vehicle report: none of its first "
            f"{HEADER_SEARCH_LINES} lines is a header naming the columns {', '.join(PLUM_COLUMNS.values())}."
        )

    positions: dict[str, int] = {}
    for position, cell in enumerate(lines[header_index]):
        field_name = wanted.get(_header_key(cell))
        if field_name is not None and field_name not in positions:
            positions[field_name] = position

    rows: list[ReportRow] = []
    for index in range(header_index + 1, len(lines)):
        cells = lines[index]
        if not any(cell.strip() for cell in cells):
            continue
        if len(rows) >= max_rows:
            raise ReportReadError(f"This report has more than {max_rows:,} rows, more than one upload may hold.")
        values: dict[str, str | None] = {}
        too_long = False
        for field_name, position in positions.items():
            value = _cell(cells[position]) if position < len(cells) else None
            if value is not None and len(value) > TEXT_VALUE_MAX_LENGTH:
                too_long = True
                value = value[:TEXT_VALUE_MAX_LENGTH]
            values[field_name] = value
        # The line of the file the row starts on, counted from one, title and header included, so the Fleet
        # Admin can find it.
        rows.append(ReportRow(row_number=line_numbers[index], too_long=too_long, **values))
    return rows


# --- What the rows are read against ----------------------------------------------------------------


@dataclass(frozen=True)
class ClassInfo:
    class_code: str
    class_label: str
    kind_code: str
    business_line_codes: tuple[str, ...]
    type_codes: frozenset[str]
    capability_codes: frozenset[str]


@dataclass(frozen=True)
class CapabilityInfo:
    capability_code: str
    unit_code: str | None


@dataclass(frozen=True)
class ModelInfo:
    model_public_id: str
    maker: str
    model_name: str
    class_code: str
    type_code: str | None
    is_retired: bool
    # Rated values in the capability's own unit; a choice capability holds its choice.
    capabilities: dict[str, Decimal | str]

    @property
    def normalized_key(self) -> str:
        return normalize_term(f"{self.maker} {self.model_name}")

    @property
    def label(self) -> str:
        return f"{self.maker} {self.model_name}"


@dataclass(frozen=True)
class CategoryRule:
    normalized_category: str
    class_code: str
    capability_code: str | None
    plum_unit_code: str | None
    plausible_low: Decimal | None
    plausible_high: Decimal | None
    check_code: str


@dataclass(frozen=True)
class ValueRule:
    rule_public_id: str
    column_code: str
    plum_value: str
    action_code: str
    result_number: Decimal | None = None
    result_unit_code: str | None = None
    result_class_code: str | None = None
    result_type_code: str | None = None

    @property
    def normalized_value(self) -> str:
        return normalize_term(self.plum_value)


@dataclass(frozen=True)
class Correction:
    correction_public_id: str
    field_code: str
    plum_value: str | None
    corrected_value: str


@dataclass(frozen=True)
class KnownAsset:
    """An asset the platform holds, as a report is compared with it."""

    asset_public_id: str
    asset_reference: str
    machine_number: str
    kind_code: str
    class_code: str
    type_code: str | None
    model_public_id: str | None
    engine_number: str | None
    chassis_number: str | None
    commenced_year: int | None
    owning_company: str | None
    status_code: str
    # The Fleet Admin's own values for this machine, which the capacity check compares with first.
    own_capabilities: dict[str, Decimal | str] = field(default_factory=dict)
    corrections: tuple[Correction, ...] = ()
    # The machine this part is fitted to, if it is a part with an open link.
    fitted_to_public_id: str | None = None
    # The classes of the parts fitted to this machine now.
    fitted_part_class_codes: frozenset[str] = frozenset()

    @property
    def normalized_key(self) -> str:
        return normalize_term(self.machine_number)


@dataclass(frozen=True)
class TransformContext:
    classes: dict[str, ClassInfo]
    capabilities: dict[str, CapabilityInfo]
    # Plum's categories, normalized, to (class, type or None) - the PLUM_CATEGORY aliases.
    category_aliases: dict[str, tuple[str, str | None]]
    # (part class, machine class) pairs a part may be fitted as.
    part_fits: frozenset[tuple[str, str]]
    models: dict[str, ModelInfo]
    # Plum's model names, normalized, to a model public id.
    model_mappings: dict[str, str]
    category_rules: dict[str, CategoryRule]
    value_rules: tuple[ValueRule, ...]
    known_assets: tuple[KnownAsset, ...]
    # The report's year: a commenced year after the next one is not a year Plum could mean.
    report_year: int

    def value_rule(self, column_code: str, value: str | None) -> ValueRule | None:
        if value is None:
            return None
        normalized = normalize_term(value)
        return next(
            (rule for rule in self.value_rules if rule.column_code == column_code and rule.normalized_value == normalized),
            None,
        )

    def rule_for_class(self, class_code: str) -> CategoryRule | None:
        """The capacity rule for a class reached by a corrected category rather than Plum's own word."""
        return next((rule for rule in self.category_rules.values() if rule.class_code == class_code), None)


# --- One row -----------------------------------------------------------------------------------------

SET_ASIDE_NO_MACHINE_NUMBER = "NO_MACHINE_NUMBER"
SET_ASIDE_VALUE_TOO_LONG = "VALUE_TOO_LONG"
SET_ASIDE_DUPLICATE_SOURCE_KEY = "DUPLICATE_SOURCE_KEY"
SET_ASIDE_CATEGORY_NOT_MAPPED = "CATEGORY_NOT_MAPPED"
SET_ASIDE_STATUS_NOT_RECOGNISED = "STATUS_NOT_RECOGNISED"

NOT_BROUGHT_IN_INACTIVE = "INACTIVE_NOT_KNOWN"
NOT_BROUGHT_IN_CLASS_NOT_USED = "CLASS_NOT_USED"

OUTCOME_NEW = "NEW"
OUTCOME_CHANGED = "CHANGED"
OUTCOME_UNCHANGED = "UNCHANGED"
OUTCOME_RETIRED = "RETIRED"
OUTCOME_REACTIVATED = "REACTIVATED"
OUTCOME_NOT_BROUGHT_IN = "NOT_BROUGHT_IN"
OUTCOME_SET_ASIDE = "SET_ASIDE"
OUTCOMES = (
    OUTCOME_NEW,
    OUTCOME_CHANGED,
    OUTCOME_UNCHANGED,
    OUTCOME_RETIRED,
    OUTCOME_REACTIVATED,
    OUTCOME_NOT_BROUGHT_IN,
    OUTCOME_SET_ASIDE,
)

# What a correction does on this row.
CORRECTION_APPLIED = "APPLIED"
CORRECTION_PLUM_AGREES = "PLUM_AGREES"
CORRECTION_PLUM_CHANGED = "PLUM_CHANGED"

# The facts a report can change, in the order changed-fact lists name them.
COMPARED_FACTS: tuple[str, ...] = (
    "kind_code",
    "class_code",
    "type_code",
    "model_public_id",
    "engine_number",
    "chassis_number",
    "commenced_year",
    "owning_company",
    "status_code",
)

_NUMBER = re.compile(r"^\d+(\.\d+)?$")
_YEAR = re.compile(r"^\d{4}$")
_MASS_IN_KILOGRAMS = {"KILOGRAM": Decimal(1), "TONNE": Decimal(1000)}


@dataclass(frozen=True)
class Flag:
    flag_code: str
    subject_code: str = ""


@dataclass(frozen=True)
class DerivedFacts:
    kind_code: str
    class_code: str
    type_code: str | None
    model_public_id: str | None
    engine_number: str | None
    chassis_number: str | None
    commenced_year: int | None
    owning_company: str | None
    status_code: str


@dataclass(frozen=True)
class CorrectionEffect:
    correction_public_id: str
    field_code: str
    effect_code: str


@dataclass(frozen=True)
class DerivedRow:
    """One row as the platform reads it. `set_aside_reason` set means nothing about it is taken in."""

    row: ReportRow
    set_aside_reason: str | None = None
    facts: DerivedFacts | None = None
    # The class Plum's category (or the Fleet Admin's correction of it) names - what "used by a business
    # line" is judged on, since a carrier's category is its crane's.
    category_class_code: str | None = None
    model_key: str | None = None
    flags: tuple[Flag, ...] = ()
    rules_applied: tuple[str, ...] = ()
    corrections: tuple[CorrectionEffect, ...] = ()


def _plum_value(row: ReportRow, field_code: str) -> str | None:
    """The Plum value a correction of this field replaces."""
    if field_code == CORRECTION_FIELD_CATEGORY:
        return row.category
    if field_code == CORRECTION_FIELD_MODEL:
        return model_key_of(row)
    if field_code == CORRECTION_FIELD_CAPACITY:
        return row.capacity or row.load_capacity
    if field_code == CORRECTION_FIELD_STATUS:
        return row.status_text
    return {
        CORRECTION_FIELD_ENGINE_NUMBER: row.engine_number,
        CORRECTION_FIELD_CHASSIS_NUMBER: row.chassis_number,
        CORRECTION_FIELD_COMMENCED_YEAR: row.commenced_year,
        CORRECTION_FIELD_OWNING_COMPANY: row.owning_company,
    }[field_code]


def plum_value_for_correction(row: ReportRow, field_code: str) -> str | None:
    return _plum_value(row, field_code)


def model_key_of(row: ReportRow) -> str | None:
    """Plum's model name: the maintenance-schedule type, or, where that is blank, make and model."""
    if row.schedule_type:
        return row.schedule_type
    joined = " ".join(part for part in (row.make, row.model) if part)
    return joined or None


def _same(left: str | None, right: str | None) -> bool:
    return normalize_term(left) == normalize_term(right)


def parse_number(value: str | None) -> Decimal | None:
    """A plain figure - digits, an optional decimal part, thousands separators allowed - or None."""
    if value is None:
        return None
    cleaned = value.replace(",", "").strip()
    if not _NUMBER.match(cleaned):
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:  # pragma: no cover - the pattern admits only valid decimals
        return None


def parse_year(value: str | None, *, report_year: int) -> int | None:
    if value is None or not _YEAR.match(value.strip()):
        return None
    year = int(value.strip())
    return year if EARLIEST_YEAR <= year <= report_year + 1 else None


def parse_status(value: str | None) -> bool | None:
    """Plum's Active or Inactive: True, False, or None when it is neither."""
    normalized = normalize_term(value)
    if normalized == "ACTIVE":
        return True
    if normalized == "INACTIVE":
        return False
    return None


def convert(value: Decimal, from_unit: str | None, to_unit: str | None) -> Decimal | None:
    """A figure in another unit, or None where the two units do not convert (only mass does, here)."""
    if from_unit is None or to_unit is None:
        return None
    if from_unit == to_unit:
        return value
    if from_unit in _MASS_IN_KILOGRAMS and to_unit in _MASS_IN_KILOGRAMS:
        return value * _MASS_IN_KILOGRAMS[from_unit] / _MASS_IN_KILOGRAMS[to_unit]
    return None


def _correction_effect(correction: Correction, row: ReportRow, ctx: TransformContext) -> str:
    """Unchanged Plum value: apply. Plum now holds the corrected value: it closes itself. Anything else:
    apply, and flag that Plum changed a value the Fleet Admin had corrected (design section 5B)."""
    plum = _plum_value(row, correction.field_code)
    if _same(plum, correction.plum_value):
        return CORRECTION_APPLIED
    if _plum_now_agrees(correction, plum, ctx):
        return CORRECTION_PLUM_AGREES
    return CORRECTION_PLUM_CHANGED


def _plum_now_agrees(correction: Correction, plum: str | None, ctx: TransformContext) -> bool:
    if plum is None:
        return False
    corrected = correction.corrected_value
    if correction.field_code == CORRECTION_FIELD_CATEGORY:
        alias = ctx.category_aliases.get(normalize_term(plum))
        return alias is not None and alias[0] == corrected
    if correction.field_code == CORRECTION_FIELD_MODEL:
        return ctx.model_mappings.get(normalize_term(plum)) == corrected
    if correction.field_code == CORRECTION_FIELD_CAPACITY:
        figure, wanted = parse_number(plum), parse_number(corrected)
        return figure is not None and wanted is not None and figure == wanted
    if correction.field_code == CORRECTION_FIELD_COMMENCED_YEAR:
        return parse_year(plum, report_year=ctx.report_year) == parse_year(corrected, report_year=ctx.report_year)
    if correction.field_code == CORRECTION_FIELD_STATUS:
        return parse_status(plum) == parse_status(corrected) and parse_status(plum) is not None
    return _same(plum, corrected)


def derive_row(row: ReportRow, ctx: TransformContext, *, known: KnownAsset | None = None) -> DerivedRow:
    """Read one row the way the Fleet Admin has said it is to be read, and check what it says."""
    flags: list[Flag] = []
    rules_applied: list[str] = []
    effects: list[CorrectionEffect] = []
    applied: dict[str, str] = {}
    for correction in known.corrections if known else ():
        effect = _correction_effect(correction, row, ctx)
        effects.append(CorrectionEffect(correction.correction_public_id, correction.field_code, effect))
        if effect == CORRECTION_PLUM_AGREES:
            continue
        applied[correction.field_code] = correction.corrected_value
        if effect == CORRECTION_PLUM_CHANGED:
            flags.append(Flag(DATA_QUALITY_PLUM_CHANGED_CORRECTED_VALUE, correction.field_code))
    base = DerivedRow(row=row, rules_applied=(), corrections=tuple(effects))
    # A row set aside takes nothing in - not even what it says of a correction: an agreeing value does not
    # close it, nor a third value flag it, until a row that is taken in says so (independent review,
    # round 4, ERT1-R4-003).
    set_aside = replace(base, corrections=())

    # Status first: a row whose status is neither Active nor Inactive cannot be taken in.
    status_text = applied.get(CORRECTION_FIELD_STATUS, row.status_text)
    is_active = parse_status(status_text)
    if is_active is None:
        return replace(set_aside, set_aside_reason=SET_ASIDE_STATUS_NOT_RECOGNISED, flags=(Flag(DATA_QUALITY_OUT_OF_PATTERN, CORRECTION_FIELD_STATUS),))

    # The class the category names.
    if CORRECTION_FIELD_CATEGORY in applied:
        category_class, category_type = applied[CORRECTION_FIELD_CATEGORY], None
        category_rule = ctx.rule_for_class(category_class)
    else:
        alias = ctx.category_aliases.get(normalize_term(row.category))
        if alias is None:
            return replace(
                set_aside, set_aside_reason=SET_ASIDE_CATEGORY_NOT_MAPPED, flags=(Flag(DATA_QUALITY_CATEGORY_NOT_MAPPED),)
            )
        category_class, category_type = alias
        category_rule = ctx.category_rules.get(normalize_term(row.category))

    # The model the model name maps to, and the class and type it gives.
    model_key = model_key_of(row)
    if CORRECTION_FIELD_MODEL in applied:
        model_public_id: str | None = applied[CORRECTION_FIELD_MODEL]
    else:
        model_public_id = ctx.model_mappings.get(normalize_term(model_key)) if model_key else None
    model = ctx.models.get(model_public_id) if model_public_id else None
    # A record's kind is its class's kind (fk_equipment_asset_class_kind): today every class a category
    # names is a machine class, but that is the structure's to say, not this code's.
    category_class_info = ctx.classes.get(category_class)
    category_kind = category_class_info.kind_code if category_class_info else ASSET_KIND_MACHINE
    class_code, kind_code, type_code = category_class, category_kind, category_type
    if model is None:
        flags.append(Flag(DATA_QUALITY_MODEL_NOT_MAPPED))
        model_public_id = None
    else:
        model_class = ctx.classes.get(model.class_code)
        if model.class_code == category_class:
            type_code = model.type_code or category_type
        elif model_class is not None and model_class.kind_code == ASSET_KIND_PART and (
            model.class_code,
            category_class,
        ) in ctx.part_fits:
            class_code, kind_code, type_code = model.class_code, ASSET_KIND_PART, model.type_code
        else:
            flags.append(Flag(DATA_QUALITY_CLASS_DISAGREES))
            model, model_public_id = None, None

    engine = _text_fact(row.engine_number, CORRECTION_FIELD_ENGINE_NUMBER, applied, ctx, rules_applied)
    chassis = _text_fact(row.chassis_number, CORRECTION_FIELD_CHASSIS_NUMBER, applied, ctx, rules_applied)
    owner = _text_fact(row.owning_company, CORRECTION_FIELD_OWNING_COMPANY, applied, ctx, rules_applied)
    year_text = _text_fact(row.commenced_year, CORRECTION_FIELD_COMMENCED_YEAR, applied, ctx, rules_applied)
    commenced_year = parse_year(year_text, report_year=ctx.report_year)
    if year_text is not None and commenced_year is None:
        flags.append(Flag(DATA_QUALITY_OUT_OF_PATTERN, CORRECTION_FIELD_COMMENCED_YEAR))

    if kind_code == ASSET_KIND_MACHINE:
        reassigned_type = _check_capacity(
            row,
            ctx,
            class_code=class_code,
            rule=category_rule,
            model=model,
            known=known,
            applied=applied,
            flags=flags,
            rules_applied=rules_applied,
        )
        if reassigned_type is not None and type_code is None:
            type_code = reassigned_type

    facts = DerivedFacts(
        kind_code=kind_code,
        class_code=class_code,
        type_code=type_code,
        model_public_id=model_public_id,
        engine_number=engine,
        chassis_number=chassis,
        commenced_year=commenced_year,
        owning_company=owner,
        status_code=ASSET_STATUS_ACTIVE if is_active else ASSET_STATUS_RETIRED,
    )
    return replace(
        base,
        facts=facts,
        category_class_code=category_class,
        model_key=model_key,
        flags=tuple(dict.fromkeys(flags)),
        rules_applied=tuple(dict.fromkeys(rules_applied)),
    )


def _text_fact(
    value: str | None, field_code: str, applied: dict[str, str], ctx: TransformContext, rules_applied: list[str]
) -> str | None:
    """A text fact: the machine's correction if one applies, else Plum's value unless a rule says it is not
    a value."""
    if field_code in applied:
        return applied[field_code]
    rule = ctx.value_rule(field_code, value)
    if rule is not None and rule.action_code == VALUE_RULE_NOT_A_VALUE:
        rules_applied.append(rule.rule_public_id)
        return None
    return value


def _check_capacity(
    row: ReportRow,
    ctx: TransformContext,
    *,
    class_code: str,
    rule: CategoryRule | None,
    model: ModelInfo | None,
    known: KnownAsset | None,
    applied: dict[str, str],
    flags: list[Flag],
    rules_applied: list[str],
) -> str | None:
    """Check Plum's capacity figure against the model (design section 6). Nothing is taken from it.
    Returns a type where a value rule says the figure names one ("PULLER")."""
    if rule is None or rule.class_code != class_code:
        return None
    raw = row.capacity or row.load_capacity
    if rule.check_code == CATEGORY_UNIT_UNCLEAR:
        if raw is not None or CORRECTION_FIELD_CAPACITY in applied:
            flags.append(Flag(DATA_QUALITY_UNIT_UNCLEAR))
        return None
    if rule.check_code != CATEGORY_CHECKED or rule.capability_code is None:
        return None
    capability = rule.capability_code
    class_info = ctx.classes.get(class_code)
    if class_info is None or capability not in class_info.capability_codes:
        return None

    figure: Decimal | None
    unit = rule.plum_unit_code
    if CORRECTION_FIELD_CAPACITY in applied:
        figure = parse_number(applied[CORRECTION_FIELD_CAPACITY])
    else:
        value_rule = ctx.value_rule(CORRECTION_FIELD_CAPACITY, raw)
        if value_rule is not None and value_rule.action_code == VALUE_RULE_REASSIGN_TO_TYPE:
            if value_rule.result_class_code == class_code:
                rules_applied.append(value_rule.rule_public_id)
                # The value names a type, not a figure: there is no figure to check.
                return value_rule.result_type_code
            value_rule = None
        if value_rule is not None and value_rule.action_code == VALUE_RULE_NOT_A_VALUE:
            rules_applied.append(value_rule.rule_public_id)
            raw = None
        if raw is None:
            flags.append(Flag(DATA_QUALITY_VALUE_MISSING, capability))
            return None
        if value_rule is not None and value_rule.action_code == VALUE_RULE_SPLIT_NUMBER_AND_UNIT:
            rules_applied.append(value_rule.rule_public_id)
            figure = convert(value_rule.result_number, value_rule.result_unit_code, unit) if value_rule.result_number else None
            if figure is None:
                flags.append(Flag(DATA_QUALITY_UNIT_UNCLEAR, capability))
                return None
        else:
            figure = parse_number(raw)
            if figure is None:
                flags.append(Flag(DATA_QUALITY_NOT_A_NUMBER, capability))
                return None
    if figure is None:
        # A corrected figure is checked to be a number when it is recorded; this is the backstop.
        flags.append(Flag(DATA_QUALITY_NOT_A_NUMBER, capability))
        return None

    if (rule.plausible_low is not None and figure < rule.plausible_low) or (
        rule.plausible_high is not None and figure > rule.plausible_high
    ):
        flags.append(Flag(DATA_QUALITY_OUT_OF_PATTERN, capability))
        return None

    expected = (known.own_capabilities.get(capability) if known else None) or (
        model.capabilities.get(capability) if model else None
    )
    if isinstance(expected, Decimal):
        in_capability_unit = convert(figure, unit, ctx.capabilities[capability].unit_code)
        if in_capability_unit is not None and in_capability_unit.quantize(Decimal("0.001")) != expected.quantize(
            Decimal("0.001")
        ):
            flags.append(Flag(DATA_QUALITY_DIFFERS_FROM_MODEL, capability))
    return None


# --- The whole report --------------------------------------------------------------------------------


@dataclass(frozen=True)
class ClosingLink:
    """A fitted-part link confirmation will close: once the report's facts are taken, its two ends no
    longer fit together - the machine end not a machine, the part end not a part, or the part's class not
    one that fits the machine's (independent review, round 3, ERT1-R3-001)."""

    machine_public_id: str
    part_public_id: str
    machine_number: str
    part_number: str
    because: str  # KIND_CHANGED or CLASS_CHANGED


@dataclass(frozen=True)
class PreviewRow:
    derived: DerivedRow
    outcome_code: str
    reason_code: str | None
    known: KnownAsset | None
    changed_facts: tuple[str, ...]
    flags: tuple[Flag, ...]
    # The links this row's asset is in that confirmation will close.
    closing_links: tuple[ClosingLink, ...] = ()


@dataclass(frozen=True)
class PairProposal:
    part_key: str
    proposed_machine_key: str | None
    candidate_machine_keys: tuple[str, ...]


@dataclass(frozen=True)
class Preview:
    rows: tuple[PreviewRow, ...]
    missing: tuple[KnownAsset, ...]
    # Known assets whose row was set aside, and the flag that says why.
    set_aside_known: tuple[tuple[KnownAsset, Flag], ...]
    unmapped_model_names: tuple[dict[str, Any], ...]
    pair_proposals: tuple[PairProposal, ...]
    # Every fitted-part link confirmation will close; confirmation closes exactly these.
    closing_links: tuple[ClosingLink, ...] = ()

    def counts(self) -> dict[str, int]:
        counts = {outcome: 0 for outcome in OUTCOMES}
        for row in self.rows:
            counts[row.outcome_code] += 1
        counts["MISSING"] = len(self.missing)
        return counts

    def rows_to_take_in(self) -> list[PreviewRow]:
        return [row for row in self.rows if row.outcome_code not in (OUTCOME_NOT_BROUGHT_IN, OUTCOME_SET_ASIDE)]


def compute_preview(rows: Iterable[ReportRow], ctx: TransformContext) -> Preview:
    rows = list(rows)
    known_by_key = {asset.normalized_key: asset for asset in ctx.known_assets}
    keys = [normalize_term(row.machine_number) if row.machine_number else None for row in rows]
    duplicate_keys = {key for key in keys if key is not None and keys.count(key) > 1}

    preview_rows: list[PreviewRow] = []
    set_aside_known: list[tuple[KnownAsset, Flag]] = []
    seen_known: set[str] = set()
    for row, key in zip(rows, keys):
        known = known_by_key.get(key) if key else None
        if known is not None:
            seen_known.add(known.asset_public_id)
        if key is None:
            preview_rows.append(_set_aside(row, SET_ASIDE_NO_MACHINE_NUMBER, None))
            continue
        if row.too_long:
            preview_rows.append(_set_aside(row, SET_ASIDE_VALUE_TOO_LONG, known, Flag(DATA_QUALITY_OUT_OF_PATTERN)))
            if known is not None:
                set_aside_known.append((known, Flag(DATA_QUALITY_OUT_OF_PATTERN)))
            continue
        if key in duplicate_keys:
            preview_rows.append(_set_aside(row, SET_ASIDE_DUPLICATE_SOURCE_KEY, known, Flag(DATA_QUALITY_DUPLICATE_SOURCE_KEY)))
            if known is not None:
                set_aside_known.append((known, Flag(DATA_QUALITY_DUPLICATE_SOURCE_KEY)))
            continue
        derived = derive_row(row, ctx, known=known)
        if derived.set_aside_reason is not None:
            preview_rows.append(
                PreviewRow(derived, OUTCOME_SET_ASIDE, derived.set_aside_reason, known, (), derived.flags)
            )
            if known is not None:
                set_aside_known.append((known, derived.flags[0]))
            continue
        preview_rows.append(_classify(derived, known, ctx))

    # The same known asset twice through two spellings of one key cannot happen: keys are normalized.
    missing = tuple(asset for asset in ctx.known_assets if asset.asset_public_id not in seen_known)
    preview_rows = _flag_possible_renumbering(preview_rows, missing)
    taken = [row for row in preview_rows if row.outcome_code not in (OUTCOME_NOT_BROUGHT_IN, OUTCOME_SET_ASIDE)]
    closing = _closing_links(taken, ctx)
    preview_rows = _mark_closing_links(preview_rows, closing)
    taken = [row for row in preview_rows if row.outcome_code not in (OUTCOME_NOT_BROUGHT_IN, OUTCOME_SET_ASIDE)]
    return Preview(
        rows=tuple(preview_rows),
        missing=missing,
        set_aside_known=tuple(set_aside_known),
        unmapped_model_names=_unmapped_model_names(taken, ctx),
        pair_proposals=_pair_proposals(taken, ctx, closing),
        closing_links=closing,
    )


def _closing_links(taken: list[PreviewRow], ctx: TransformContext) -> tuple[ClosingLink, ...]:
    """The open links whose ends, with the report's facts taken, no longer fit together. Only a change of
    kind or class of either end is looked at - what `write_derived_facts` looks at on a machine's page - and
    each end is judged as it will stand: from its row if the report takes one, else as it is now."""
    after = {row.known.asset_public_id: row.derived.facts for row in taken if row.known is not None and row.derived.facts is not None}
    by_id = {asset.asset_public_id: asset for asset in ctx.known_assets}
    closing: list[ClosingLink] = []
    for part in ctx.known_assets:
        machine = by_id.get(part.fitted_to_public_id) if part.fitted_to_public_id else None
        if machine is None:
            continue
        machine_facts, part_facts = after.get(machine.asset_public_id), after.get(part.asset_public_id)
        machine_kind, machine_class = (machine_facts.kind_code, machine_facts.class_code) if machine_facts else (machine.kind_code, machine.class_code)
        part_kind, part_class = (part_facts.kind_code, part_facts.class_code) if part_facts else (part.kind_code, part.class_code)
        kind_changed = machine_kind != machine.kind_code or part_kind != part.kind_code
        class_changed = machine_class != machine.class_code or part_class != part.class_code
        if not (kind_changed or class_changed):
            continue
        # The rules `_still_fits` judges a link by on a machine's page: the part end a part, of a class the
        # structure fits to the other end's class (a machine's, or a part's within the depth setting).
        if part_kind == ASSET_KIND_PART and (part_class, machine_class) in ctx.part_fits:
            continue
        closing.append(
            ClosingLink(
                machine_public_id=machine.asset_public_id,
                part_public_id=part.asset_public_id,
                machine_number=machine.machine_number,
                part_number=part.machine_number,
                because="KIND_CHANGED" if kind_changed else "CLASS_CHANGED",
            )
        )
    return tuple(closing)


def _mark_closing_links(rows: list[PreviewRow], closing: tuple[ClosingLink, ...]) -> list[PreviewRow]:
    """Each row names the links of its asset that will close; a part row whose link closes is flagged as
    not fitted, as it will be unless it is paired again in the same confirmation."""
    if not closing:
        return rows
    marked: list[PreviewRow] = []
    for row in rows:
        mine = tuple(link for link in closing if row.known is not None and row.known.asset_public_id in (link.machine_public_id, link.part_public_id))
        if mine:
            unfitted = any(link.part_public_id == row.known.asset_public_id for link in mine)
            facts = row.derived.facts
            flags = row.flags
            if unfitted and facts is not None and facts.kind_code == ASSET_KIND_PART and Flag(DATA_QUALITY_PART_NOT_FITTED) not in flags:
                flags = flags + (Flag(DATA_QUALITY_PART_NOT_FITTED),)
            row = replace(row, closing_links=mine, flags=flags)
        marked.append(row)
    return marked


def _set_aside(row: ReportRow, reason: str, known: KnownAsset | None, flag: Flag | None = None) -> PreviewRow:
    flags = (flag,) if flag else ()
    return PreviewRow(DerivedRow(row=row, set_aside_reason=reason, flags=flags), OUTCOME_SET_ASIDE, reason, known, (), flags)


def _classify(derived: DerivedRow, known: KnownAsset | None, ctx: TransformContext) -> PreviewRow:
    facts = derived.facts
    assert facts is not None
    if known is None:
        if facts.status_code != ASSET_STATUS_ACTIVE:
            return PreviewRow(derived, OUTCOME_NOT_BROUGHT_IN, NOT_BROUGHT_IN_INACTIVE, None, (), derived.flags)
        category_class = ctx.classes.get(derived.category_class_code or "")
        if category_class is None or not category_class.business_line_codes:
            return PreviewRow(derived, OUTCOME_NOT_BROUGHT_IN, NOT_BROUGHT_IN_CLASS_NOT_USED, None, (), derived.flags)
        return PreviewRow(derived, OUTCOME_NEW, None, None, tuple(COMPARED_FACTS), derived.flags)

    current = {name: getattr(known, name) for name in COMPARED_FACTS}
    changed = tuple(name for name in COMPARED_FACTS if current[name] != getattr(facts, name))
    if known.status_code == ASSET_STATUS_ACTIVE and facts.status_code == ASSET_STATUS_RETIRED:
        outcome = OUTCOME_RETIRED
    elif known.status_code == ASSET_STATUS_RETIRED and facts.status_code == ASSET_STATUS_ACTIVE:
        outcome = OUTCOME_REACTIVATED
    else:
        outcome = OUTCOME_CHANGED if changed else OUTCOME_UNCHANGED
    return PreviewRow(derived, outcome, None, known, changed, derived.flags)


def _flag_possible_renumbering(rows: list[PreviewRow], missing: tuple[KnownAsset, ...]) -> list[PreviewRow]:
    """A new machine whose chassis number is a missing machine's may be that machine under a new number."""
    missing_chassis = {normalize_term(asset.chassis_number) for asset in missing if asset.chassis_number}
    if not missing_chassis:
        return rows
    result: list[PreviewRow] = []
    for row in rows:
        facts = row.derived.facts
        if row.outcome_code == OUTCOME_NEW and facts and facts.chassis_number and normalize_term(facts.chassis_number) in missing_chassis:
            row = replace(row, flags=row.flags + (Flag(DATA_QUALITY_POSSIBLY_RENUMBERED),))
        result.append(row)
    return result


def _unmapped_model_names(rows: list[PreviewRow], ctx: TransformContext) -> tuple[dict[str, Any], ...]:
    """Each model name still to map, with its category and how many machines carry it (design Q4)."""
    names: dict[str, dict[str, Any]] = {}
    for row in rows:
        if Flag(DATA_QUALITY_MODEL_NOT_MAPPED) not in row.flags or not row.derived.model_key:
            continue
        normalized = normalize_term(row.derived.model_key)
        entry = names.setdefault(
            normalized,
            {
                "source_name": row.derived.model_key,
                "normalized_source_name": normalized,
                "category": row.derived.row.category,
                "class_code": row.derived.category_class_code,
                "make": row.derived.row.make,
                "model": row.derived.row.model,
                "machine_count": 0,
            },
        )
        entry["machine_count"] += 1
    return tuple(sorted(names.values(), key=lambda item: (-item["machine_count"], item["normalized_source_name"])))


@dataclass(frozen=True)
class _PairSide:
    key: str
    class_code: str
    model_key: str | None
    is_active: bool
    fitted_part_classes: frozenset[str]


def _pair_proposals(rows: list[PreviewRow], ctx: TransformContext, closing: tuple[ClosingLink, ...] = ()) -> tuple[PairProposal, ...]:
    """For each part not fitted to a machine, the machines it could be fitted to, and the one proposed:
    the machine of the same model name, where exactly one such machine has no part of that class (design
    section 5, step 8). The Fleet Admin confirms or chooses; nothing is paired here. Links confirmation will
    close are taken as closed: their parts need pairing again, and their machines are free for one."""
    in_report: dict[str, PreviewRow] = {normalize_term(row.derived.row.machine_number): row for row in rows}
    by_id = {asset.asset_public_id: asset for asset in ctx.known_assets}
    unfitting = {link.part_public_id for link in closing}
    freed: dict[str, set[str]] = {}
    for link in closing:
        part = by_id.get(link.part_public_id)
        if part is not None:
            freed.setdefault(link.machine_public_id, set()).add(part.class_code)

    def fitted_classes(asset: KnownAsset | None) -> frozenset[str]:
        return frozenset(asset.fitted_part_class_codes - freed.get(asset.asset_public_id, set())) if asset else frozenset()

    machines: dict[str, _PairSide] = {}
    parts: list[tuple[str, str, str | None]] = []
    for key, row in in_report.items():
        facts = row.derived.facts
        assert facts is not None
        model = ctx.models.get(facts.model_public_id) if facts.model_public_id else None
        if facts.kind_code == ASSET_KIND_MACHINE:
            machines[key] = _PairSide(key, facts.class_code, model.normalized_key if model else None, facts.status_code == ASSET_STATUS_ACTIVE, fitted_classes(row.known))
        elif facts.status_code == ASSET_STATUS_ACTIVE and (
            row.known is None or row.known.fitted_to_public_id is None or row.known.asset_public_id in unfitting
        ):
            parts.append((key, facts.class_code, model.normalized_key if model else None))
    for asset in ctx.known_assets:
        if asset.normalized_key in in_report or asset.kind_code != ASSET_KIND_MACHINE:
            continue
        model = ctx.models.get(asset.model_public_id) if asset.model_public_id else None
        machines[asset.normalized_key] = _PairSide(
            asset.normalized_key,
            asset.class_code,
            model.normalized_key if model else None,
            asset.status_code == ASSET_STATUS_ACTIVE,
            fitted_classes(asset),
        )

    proposals: list[PairProposal] = []
    for part_key, part_class, part_model_key in sorted(parts):
        candidates = sorted(
            machine.key
            for machine in machines.values()
            if machine.is_active and (part_class, machine.class_code) in ctx.part_fits and part_class not in machine.fitted_part_classes
        )
        same_model = [key for key in candidates if part_model_key and machines[key].model_key == part_model_key]
        proposals.append(
            PairProposal(part_key=part_key, proposed_machine_key=same_model[0] if len(same_model) == 1 else None, candidate_machine_keys=tuple(candidates))
        )
    return tuple(proposals)


# --- One machine, re-read after a correction ------------------------------------------------------


def rederive_known(values: dict[str, Any], known: KnownAsset, ctx: TransformContext) -> DerivedRow:
    """Re-read one machine from the used values it was last built from, with its corrections as they now
    stand. Used when the Fleet Admin records or closes a correction on the machine itself."""
    return derive_row(row_from_values(0, values), ctx, known=known)
