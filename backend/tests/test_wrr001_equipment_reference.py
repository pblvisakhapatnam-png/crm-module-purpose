"""WRR-001 - the platform's Equipment Reference (ADR-037).

Version 1 of the structure is checked against section 5 of
docs/agent/slices/wrr-001-resource-requirement-foundation.md, spelled out here independently of the
migration that loads it: a test that read its expectation from the migration would pass whatever the
migration said.

Constraint tests insert a deliberately wrong row inside a transaction and roll it back, so the shared
reference data is never changed.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.main import app
from app.modules.equipment_reference.contract import normalize_term
from app.modules.equipment_reference.service import get_equipment_structure, suggest_equipment_class
from tests.test_commercial_offers_api import auth_headers, client

STRUCTURE_URL = "/api/equipment-reference/structure"
READ_ROLES = ("admin1", "sales1", "manager1", "finance1", "ops1", "readonly1")

# Section 5, class by class: label, business lines, types, capabilities with their units, key capability.
VERSION_1 = {
    "CRANE": (
        "Crane",
        ["HIRING"],
        [
            "CRAWLER",
            "ALL_TERRAIN",
            "TRUCK_MOUNTED_TELESCOPIC",
            "ROUGH_TERRAIN",
            "PICK_AND_CARRY",
            "KNUCKLE_BOOM_LOADER",
            "MOBILE_TOWER",
            "DERRICK",
        ],
        [("RATED_CAPACITY", "TONNE"), ("MAIN_BOOM_LENGTH", "METRE"), ("MAX_TIP_HEIGHT", "METRE")],
        "RATED_CAPACITY",
    ),
    "AERIAL_WORK_PLATFORM": (
        "Aerial Work Platform",
        ["HIRING"],
        ["TELESCOPIC_BOOM", "ARTICULATING_BOOM", "SCISSOR", "VERTICAL_MAST"],
        [("WORKING_HEIGHT", "METRE"), ("PLATFORM_CAPACITY", "KILOGRAM"), ("HORIZONTAL_OUTREACH", "METRE")],
        "WORKING_HEIGHT",
    ),
    "FORKLIFT": ("Forklift", ["HIRING"], [], [("RATED_CAPACITY", "TONNE"), ("LIFT_HEIGHT", "METRE")], "RATED_CAPACITY"),
    "EXCAVATOR": (
        "Excavator",
        ["HIRING"],
        [],
        [("OPERATING_WEIGHT", "TONNE"), ("BUCKET_CAPACITY", "CUBIC_METRE")],
        "OPERATING_WEIGHT",
    ),
    "PRIME_MOVER": (
        "Prime Mover",
        ["TRANSPORTATION"],
        ["TRACTOR_UNIT", "BALLAST_TRACTOR"],
        [("GROSS_COMBINATION_WEIGHT", "TONNE"), ("AXLE_CONFIGURATION", None)],
        "GROSS_COMBINATION_WEIGHT",
    ),
    "TRAILER": (
        "Trailer",
        ["TRANSPORTATION"],
        ["LOW_BED", "SEMI_LOW_BED", "FLATBED", "EXTENDABLE"],
        [("PAYLOAD", "TONNE"), ("DECK_LENGTH", "METRE"), ("AXLE_COUNT", "COUNT")],
        "PAYLOAD",
    ),
    "MODULAR_HYDRAULIC_TRAILER": (
        "Modular Hydraulic Trailer",
        ["TRANSPORTATION"],
        ["TOWED_MODULAR", "SELF_PROPELLED"],
        [("AXLE_LINES", "COUNT"), ("PAYLOAD", "TONNE")],
        "AXLE_LINES",
    ),
    "POWER_PACK": ("Power Pack", ["TRANSPORTATION"], [], [("POWER_OUTPUT", "KILOWATT")], None),
    "TRUCK": ("Truck", ["TRANSPORTATION"], [], [("PAYLOAD", "TONNE")], "PAYLOAD"),
    "GENERATOR": ("Generator", [], [], [("RATED_OUTPUT_KVA", "KILOVOLT_AMPERE")], None),
    "LIGHT_VEHICLE": ("Light Vehicle", [], ["TWO_WHEELER", "FOUR_WHEELER", "VAN"], [], None),
    "WORKSHOP_ASSET": ("Workshop Asset", [], [], [], None),
}

ANNEXURE_21_TYPES = {
    "Telescopic Cranes",
    "Mobile Tower Cranes",
    "Crawler Cranes",
    "Derrick",
    "Excavator",
    "Farana",
    "Forklift",
    "Four Wheeler",
    "Hydraulic Axles",
    "Manlifts",
    "Palfinger",
    "Puller",
    "Trailer Bed",
    "Prime Movers",
    "Two Wheelers",
}
# Every non-blank category in Plum's report of 24 September 2026, spelled as Plum spells them.
PLUM_CATEGORIES = {
    "CRANES",
    "CRANE",
    "TRAILERS",
    "TRAILER BED",
    "HYDRAULIC AXLES",
    "TWO WHEELER",
    "MAN LIFTS",
    "GARAGE ASSETS",
    "FORK LIFT",
    "VAN",
    "Power Packs",
    "GENERAL",
    "FOUR WHEELER",
    "Excavator",
    "Genertor",
    "TRUCKS",
}


def _structure(username: str = "sales1") -> dict:
    response = client.get(STRUCTURE_URL, headers=auth_headers(username))
    assert response.status_code == 200, response.text
    return response.json()


@contextmanager
def _rolled_back():
    """A session whose every change is discarded, for inserting rows a constraint must refuse."""
    with SessionLocal() as db:
        try:
            yield db
        finally:
            db.rollback()


# --- Version 1 -------------------------------------------------------------------------------------


def test_version_1_loads_exactly_as_agreed() -> None:
    """Version 1's rows are still exactly as agreed. ERT-1's version 2 and ERT-2's version 3 only add to
    them - the crane carrier, then the four kinds of kit, all part classes: tests/test_ert1_equipment_import_api.py
    and tests/test_ert2_detachable_kit.py check what they add."""
    body = _structure()
    assert body["taxonomy_version"] == 3
    assert [version["version_number"] for version in body["versions"]] == [1, 2, 3]
    version_1 = [item for item in body["classes"] if item["introduced_in_version"] == 1]
    assert [item["class_code"] for item in version_1] == list(VERSION_1)
    assert [item["class_code"] for item in body["classes"] if item["introduced_in_version"] != 1] == [
        "CRANE_CARRIER",
        "BOOM_JIB_SECTION",
        "COUNTERWEIGHT",
        "HOOK_BLOCK",
        "LIFTING_TACKLE",
    ]
    for equipment_class in version_1:
        assert equipment_class["class_kind_code"] == "MACHINE"
        label, lines, types, capabilities, key = VERSION_1[equipment_class["class_code"]]
        assert equipment_class["class_label"] == label
        assert equipment_class["business_line_codes"] == lines
        assert [item["type_code"] for item in equipment_class["types"]] == types
        assert [(item["capability_code"], item["unit_code"]) for item in equipment_class["capabilities"]] == capabilities
        keys = [item["capability_code"] for item in equipment_class["capabilities"] if item["is_key"]]
        assert keys == ([key] if key else [])
        assert equipment_class["is_active"] is True


def test_every_capability_has_exactly_one_unit_or_a_fixed_list() -> None:
    body = _structure()
    for capability in body["capabilities"]:
        if capability["value_kind_code"] == "CHOICE":
            assert capability["unit_code"] is None
            assert capability["allowed_values"]
        else:
            assert capability["value_kind_code"] == "MINIMUM"
            assert capability["unit_code"] in {unit["unit_code"] for unit in body["units"]}
            assert capability["allowed_values"] is None
    axle = next(item for item in body["capabilities"] if item["capability_code"] == "AXLE_CONFIGURATION")
    assert axle["allowed_values"] == ["4X2", "6X2", "6X4", "6X6", "8X4", "8X8"]
    units = {unit["unit_code"]: unit for unit in body["units"]}
    assert units["COUNT"]["whole_numbers_only"] is True
    assert units["TONNE"]["unit_symbol"] == "t"


def test_the_aliases_take_in_all_15_annexure_21_types_and_every_plum_category() -> None:
    aliases = _structure()["aliases"]
    assert {alias["term"] for alias in aliases if alias["source_code"] == "ANNEXURE_21"} == ANNEXURE_21_TYPES
    assert {alias["term"] for alias in aliases if alias["source_code"] == "PLUM_CATEGORY"} == PLUM_CATEGORIES
    # Plum's TRAILERS are the prime movers, and its TRAILER BED is the trailer.
    by_term = {(alias["source_code"], alias["term"]): alias for alias in aliases}
    assert by_term[("PLUM_CATEGORY", "TRAILERS")]["class_code"] == "PRIME_MOVER"
    assert by_term[("PLUM_CATEGORY", "TRAILER BED")]["class_code"] == "TRAILER"
    # Annexure-21's "Telescopic Cranes" covers several crane types, so it names the class only.
    assert by_term[("ANNEXURE_21", "Telescopic Cranes")]["type_code"] is None
    assert by_term[("TRADE_TERM", "Hydra")]["type_code"] == "PICK_AND_CARRY"


def test_every_alias_points_at_an_existing_class_and_a_type_of_that_class() -> None:
    body = _structure()
    types_by_class = {item["class_code"]: {t["type_code"] for t in item["types"]} for item in body["classes"]}
    for alias in body["aliases"]:
        assert alias["class_code"] in types_by_class
        if alias["type_code"] is not None:
            assert alias["type_code"] in types_by_class[alias["class_code"]]
        assert alias["normalized_term"] == normalize_term(alias["term"])


# --- The database keeps the structure's rules ------------------------------------------------------


def test_an_alias_naming_a_type_of_another_class_is_refused() -> None:
    with _rolled_back() as db, pytest.raises(IntegrityError, match="fk_equipment_term_alias_class_type"):
        db.execute(
            text(
                "INSERT INTO equipment_term_alias (source_code, term, normalized_term, class_code, type_code, "
                "introduced_in_version) VALUES ('TRADE_TERM', 'Cherry picker', 'CHERRY PICKER', 'CRANE', 'SCISSOR', 1)"
            )
        )


def test_an_alias_whose_normalized_form_disagrees_with_its_term_is_refused() -> None:
    with _rolled_back() as db, pytest.raises(IntegrityError, match="ck_equipment_term_alias_normalized"):
        db.execute(
            text(
                "INSERT INTO equipment_term_alias (source_code, term, normalized_term, class_code, "
                "introduced_in_version) VALUES ('TRADE_TERM', 'Cherry  picker', 'Cherry picker', 'AERIAL_WORK_PLATFORM', 1)"
            )
        )


def test_a_class_cannot_have_two_live_key_capabilities() -> None:
    with _rolled_back() as db, pytest.raises(IntegrityError, match="uq_equipment_class_capability_one_key"):
        db.execute(
            text(
                "UPDATE equipment_class_capability SET is_key = TRUE "
                "WHERE class_code = 'CRANE' AND capability_code = 'MAIN_BOOM_LENGTH'"
            )
        )


def test_a_measured_capability_needs_a_unit_and_a_fixed_list_has_none() -> None:
    with _rolled_back() as db, pytest.raises(IntegrityError, match="ck_equipment_capability_value_kind"):
        db.execute(
            text(
                "INSERT INTO equipment_capability (capability_code, capability_label, unit_code, value_kind_code, "
                "introduced_in_version) VALUES ('TEST_NO_UNIT', 'No unit', NULL, 'MINIMUM', 1)"
            )
        )
    with _rolled_back() as db, pytest.raises(IntegrityError, match="ck_equipment_capability_unit"):
        db.execute(
            text(
                "INSERT INTO equipment_capability (capability_code, capability_label, unit_code, value_kind_code, "
                "introduced_in_version) VALUES ('TEST_BAD_UNIT', 'Pounds', 'POUND', 'MINIMUM', 1)"
            )
        )


def test_a_row_cannot_be_retired_in_the_version_that_introduced_it() -> None:
    with _rolled_back() as db, pytest.raises(IntegrityError, match="ck_equipment_type_retired_after_introduced"):
        db.execute(text("UPDATE equipment_type SET retired_in_version = 1 WHERE type_code = 'CRAWLER'"))


def test_retired_rows_stay_readable_and_are_marked() -> None:
    """Nothing is deleted: a retired type is still in the structure, marked, so anything saved with it
    still reads. Checked inside a transaction that is rolled back."""
    # Version 4 is a test version: 2 is ERT-1's (migration 20260908_0042), 3 is ERT-2's (20260908_0043).
    with _rolled_back() as db:
        db.execute(
            text(
                "INSERT INTO equipment_taxonomy_version (version_number, version_label, source_note, component_depth) "
                "VALUES (4, 'Test version', 'Rolled back by the test.', 3)"
            )
        )
        db.execute(text("UPDATE equipment_type SET retired_in_version = 4 WHERE type_code = 'DERRICK'"))
        structure = get_equipment_structure(db)
        crane = next(item for item in structure.classes if item.class_code == "CRANE")
        derrick = next(item for item in crane.types if item.type_code == "DERRICK")
        assert structure.taxonomy_version == 4
        assert derrick.is_active is False
        assert derrick.retired_in_version == 4
    assert _structure()["taxonomy_version"] == 3


# --- Reading it -----------------------------------------------------------------------------------


@pytest.mark.parametrize("username", READ_ROLES)
def test_every_role_that_can_view_work_orders_can_read_the_structure(username: str) -> None:
    assert client.get(STRUCTURE_URL, headers=auth_headers(username)).status_code == 200


def test_an_unauthenticated_caller_cannot_read_the_structure() -> None:
    assert client.get(STRUCTURE_URL).status_code == 401


def test_the_structure_has_no_write_route() -> None:
    """The structure changes only by migration (design section 10). ERT-1 added writes for models,
    machines, the import and corrections, and ERT-2 for pieces of kit - none of them writes a class, type,
    capability or alias."""
    write_paths = {
        route.path
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/equipment-reference")
        and set(getattr(route, "methods", set())) - {"GET", "HEAD"}
    }
    assert write_paths
    structure_words = ("structure", "class", "type", "capabilit", "alias", "categor")
    for path in write_paths:
        first_segment = path.removeprefix("/api/equipment-reference/").split("/")[0]
        assert first_segment in {"machines", "models", "model-mappings", "value-rules", "imports", "kit"}, path
        assert not any(word in first_segment for word in structure_words), path


# --- Suggesting a class from free text -------------------------------------------------------------


@pytest.mark.parametrize(
    ("text_value", "expected"),
    [
        ("Crane", ("CRANE", None)),
        ("  crane ", ("CRANE", None)),
        ("CRANES", ("CRANE", None)),
        ("Hydra", ("CRANE", "PICK_AND_CARRY")),
        ("Farana", ("CRANE", "PICK_AND_CARRY")),
        ("Crawler Cranes", ("CRANE", "CRAWLER")),
        ("Telescopic Cranes", ("CRANE", None)),
        ("Manlifts", ("AERIAL_WORK_PLATFORM", None)),
        ("MAN LIFTS", ("AERIAL_WORK_PLATFORM", None)),
        ("Fork lift", ("FORKLIFT", None)),
        ("250MT Crane", ("CRANE", None)),
        # Transportation's classes are not offered for a Work Order requirement.
        ("Prime Movers", None),
        ("TRAILERS", None),
        ("Genertor", None),
        # Two classes named: no suggestion rather than a guess.
        ("Crane and Forklift", None),
        ("Scaffolding", None),
        ("", None),
        (None, None),
    ],
)
def test_a_class_is_suggested_only_when_the_words_name_one_hiring_class(text_value, expected) -> None:
    with SessionLocal() as db:
        structure = get_equipment_structure(db)
    suggestion = suggest_equipment_class(structure, text_value, business_line_code="HIRING")
    if expected is None:
        assert suggestion is None
    else:
        assert suggestion is not None
        assert (suggestion.class_code, suggestion.type_code) == expected


def test_a_transportation_class_is_suggested_for_transportation() -> None:
    with SessionLocal() as db:
        structure = get_equipment_structure(db)
    suggestion = suggest_equipment_class(structure, "Puller", business_line_code="TRANSPORTATION")
    assert suggestion is not None
    assert (suggestion.class_code, suggestion.type_code) == ("PRIME_MOVER", "BALLAST_TRACTOR")
