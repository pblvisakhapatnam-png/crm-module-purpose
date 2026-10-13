"""PF-1A-E3: closed vocabularies, and the purity of the policy layer."""

from __future__ import annotations

import ast
import dataclasses
import inspect
from datetime import datetime, timedelta, timezone

import pytest

from app.modules.authorization.business_authority import (
    configuration_contract as e3,
    configuration_domain,
    configuration_models,
    configuration_policy,
    configuration_repository,
    configuration_service,
    lineage,
    material,
)
from app.modules.authorization.business_authority import contract as e2


def test_the_vocabularies_are_closed_and_disjoint() -> None:
    assert e3.CHANGE_TYPES == ("CREATE", "UPDATE", "DEACTIVATE")
    assert e3.LIFECYCLE_STATUSES == ("PENDING", "ACTIVE", "REJECTED")
    assert e3.TERMINAL_LIFECYCLE_STATUSES == ("ACTIVE", "REJECTED")
    assert e3.EVALUATION_STAGES == ("PROPOSAL", "AUTHORIZATION", "REJECTION", "ACTIVATION")
    assert e3.EVALUATION_OUTCOMES == ("RECORDED", "PERMITTED", "REFUSED")
    assert len(set(e3.REFUSAL_REASONS)) == len(e3.REFUSAL_REASONS)
    assert not set(e3.REFUSAL_REASONS) & set(e3.EVALUATION_OUTCOMES)

    # A successful outcome is enumerated, not inferred by negating REFUSED, so a later added
    # outcome has to be classified deliberately instead of defaulting to "successful".
    assert e3.SUCCESSFUL_EVALUATION_OUTCOMES == ("RECORDED", "PERMITTED")
    assert set(e3.SUCCESSFUL_EVALUATION_OUTCOMES) < set(e3.EVALUATION_OUTCOMES)
    assert e3.OUTCOME_REFUSED not in e3.SUCCESSFUL_EVALUATION_OUTCOMES

    # "Nobody authorized this" and "the recorded authorization cannot be verified" stay
    # separate governance answers.
    assert e3.AUTHORIZATION_MISSING in e3.REFUSAL_REASONS
    assert e3.AUTHORIZATION_EVIDENCE_UNVERIFIABLE in e3.REFUSAL_REASONS
    assert e3.AUTHORIZATION_EVIDENCE_UNVERIFIABLE != e3.AUTHORIZATION_MISSING

    # "You named the wrong predecessor" and "the recorded clock cannot be published behind" are
    # different structural failures and keep different reasons: the second can occur while the
    # expected predecessor is perfectly correct.
    assert e3.PUBLICATION_TIMESTAMP_NOT_MONOTONIC in e3.REFUSAL_REASONS
    assert e3.PUBLICATION_TIMESTAMP_NOT_MONOTONIC != e3.LINEAGE_PRECONDITION_FAILED

    # "The resulting lineage would be defective" is a third, distinct structural answer. It can
    # occur while the expected predecessor is correct AND the recorded clock is fine, so collapsing
    # it into either of the two above would misattribute the cause.
    assert e3.PUBLICATION_LINEAGE_INVALID in e3.REFUSAL_REASONS
    assert e3.PUBLICATION_LINEAGE_INVALID not in (
        e3.LINEAGE_PRECONDITION_FAILED,
        e3.PUBLICATION_TIMESTAMP_NOT_MONOTONIC,
    )


def test_the_governed_writer_publishes_under_the_e2_configuration_change_provenance() -> None:
    """E2 defined the value and never created such a record; E3 is what populates it."""

    assert e3.PUBLICATION_REFERENCE_TYPE == e2.CONFIGURATION_CHANGE
    assert e3.PUBLICATION_REFERENCE_TYPE in e2.PUBLICATION_REFERENCE_TYPES


def test_the_e2_vocabularies_are_imported_not_restated_and_are_unchanged() -> None:
    assert e3.OBJECT_FAMILIES is e2.OBJECT_FAMILIES
    assert len(e2.OBJECT_FAMILIES) == 4
    assert e2.PUBLICATION_REFERENCE_TYPES == ("BOOTSTRAP_PROVENANCE", "CONFIGURATION_CHANGE")
    assert set(e3.CHANGE_PAYLOAD_FIELDS) == set(e2.OBJECT_FAMILIES)
    assert set(e3.STABLE_REFERENCE_FIELDS) == set(e2.OBJECT_FAMILIES)
    # `active_flag` is a governed lifecycle decision, never an editable payload field.
    for fields in e3.CHANGE_PAYLOAD_FIELDS.values():
        assert "active_flag" not in fields


def test_an_allocated_object_version_is_unique_and_strictly_greater_than_any_predecessor() -> (
    None
):
    """THE ALLOCATION INVARIANT, over ARBITRARY opaque predecessors.

    PF-1A-E2 requires a publisher to use a lexicographically ordered version identity, because
    the kernel reads `published_at` as non-decreasing in `object_version` order. A merely unique
    identifier is not enough: one that sorted before its own predecessor would be read as
    contradictory provenance.

    The rule is `new = maximum + non-empty suffix`, so the maximum is a PROPER PREFIX of the
    result and lexicographic comparison places a proper prefix strictly before its extension -
    for any predecessor whatsoever, without inspecting one character of it.
    """

    change = "cc-11111111-2222-3333-4444-555555555555"
    suffix = e3.object_version_suffix(change)
    assert suffix
    assert suffix == e3.object_version_suffix(change)
    assert suffix != e3.object_version_suffix("cc-11111111-2222-3333-4444-555555555556")
    assert suffix.isalnum(), "punctuation would make the ordering collation-dependent"
    with pytest.raises(ValueError):
        e3.object_version_suffix("")

    # Every one of these is a legitimate opaque predecessor some other authorized publisher
    # could have written, including ones chosen to defeat a fixed-width or numeric scheme.
    predecessors = [
        None,
        "",
        "0001",
        "9999",
        "v1",
        "V1",
        "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
        "~~~~~~~~",
        "0f8c1ec2-3f0b-4d64-9d21-1f6b5b2f9a11",
        "e3" + "f" * 16,
        "  leading space",
        "版本一",
    ]
    for predecessor in predecessors:
        allocated = e3.allocate_object_version(predecessor, change)
        existing = predecessor or ""
        assert allocated > existing, (predecessor, allocated)
        assert allocated.startswith(existing)
        assert allocated != existing
        # The predecessor is carried through byte for byte: nothing about it was interpreted.
        assert allocated[: len(existing)] == existing

    # Successive allocations for one object are strictly increasing, which is the property the
    # unchanged kernel actually depends on.
    chain = [None]
    for index in range(6):
        chain.append(e3.allocate_object_version(chain[-1], f"cc-chain-{index}"))
    published = [value for value in chain if value is not None]
    assert published == sorted(published)
    assert all(later > earlier for earlier, later in zip(published, published[1:]))
    assert len(set(published)) == len(published)

    # An allocated identity carries no sequence and is never readable as a number.
    assert not e3.allocate_object_version(None, change).isdigit()

    distinct = {e3.allocate_object_version(None, f"cc-{index}") for index in range(500)}
    assert len(distinct) == 500


def test_no_e3_module_parses_a_version_identifier_as_a_number() -> None:
    """PF-1A-E2 defines `object_version` as OPAQUE, and PF-1A-E3 must honour that.

    A pre-PF-1A-E3 publication legitimately reads "v1" or a UUID. Any numeric reading of a
    version identifier would make every one of those unmanageable - the exact defect this scan
    exists to keep out - so the helpers that once did it are gone rather than merely unused.
    """

    for removed in ("format_object_version", "parse_object_version", "OBJECT_VERSION_WIDTH"):
        assert not hasattr(e3, removed), removed

    for module in (configuration_policy, configuration_repository, configuration_service):
        source = inspect.getsource(module)
        for forbidden in ("parse_object_version", "format_object_version", ".isdigit()"):
            assert forbidden not in source, f"{module.__name__} names {forbidden}"

    # Ordering is by whole-string comparison, which is not parsing. The repository must not
    # delegate "the greatest version" to a SQL ORDER BY over the text column either: that would
    # apply the DATABASE COLLATION, while the kernel compares in Python, so the store could
    # believe a different version was current from the one the kernel does.
    repository_source = inspect.getsource(configuration_repository)
    assert "ORDER BY v.object_version" not in repository_source
    assert "max(published)" in repository_source


_UNIT_OBJECT = (e2.BUSINESS_AUTHORITY_ROLE, "e3-unit-object")
_NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)


def _row(
    object_version: str,
    *,
    effective_from: datetime,
    active_flag: bool = True,
    declared_effective_to: datetime | None = None,
    published_at: datetime | None = None,
    retracted: bool = False,
) -> configuration_domain.PublishedRow:
    """One well-formed published row of the unit-test object, with conforming provenance."""

    return configuration_domain.PublishedRow(
        object_family=_UNIT_OBJECT[0],
        object_id=_UNIT_OBJECT[1],
        object_version=object_version,
        active_flag=active_flag,
        retracted=retracted,
        effective_from=effective_from,
        declared_effective_to=declared_effective_to,
        payload={"role_code": "E3_UNIT", "role_name": "Unit", "description": ""},
        publication_reference_type=e2.BOOTSTRAP_PROVENANCE,
        publication_reference_id="e3-unit-test",
        published_at=published_at if published_at is not None else effective_from,
    )


def _context(rows, retractions=()) -> configuration_domain.AuthorityContext:
    """A minimal context carrying exactly what a prospective publication evaluation reads."""

    return configuration_domain.AuthorityContext(
        as_of=_NOW,
        rows=tuple(rows),
        incumbent_person_by_position={},
        protected_candidate_codes=(),
        unresolved=(),
        fingerprint="e3-unit-fingerprint",
        context_reference={},
        retractions=tuple(retractions),
    )


def _proposed(
    object_version: str = "0001e3unit",
    *,
    effective_from: datetime,
    declared_effective_to: datetime | None = None,
    active_flag: bool | None = True,
    published_at: datetime | None = None,
) -> configuration_domain.PublishedRow:
    """The exact immutable version a governed activation would append, in E3's own row shape."""

    return configuration_domain.PublishedRow(
        object_family=_UNIT_OBJECT[0],
        object_id=_UNIT_OBJECT[1],
        object_version=object_version,
        active_flag=active_flag,
        retracted=False,
        effective_from=effective_from,
        declared_effective_to=declared_effective_to,
        payload={"role_code": "E3_UNIT", "role_name": "Unit", "description": ""},
        corrects_object_version=None,
        publication_reference_type=e2.CONFIGURATION_CHANGE,
        publication_reference_id="cc-e3-unit",
        published_at=published_at if published_at is not None else _NOW,
    )


def test_a_publishable_append_reports_no_prospective_defect() -> None:
    """The control. The check must not refuse ordinary supersession, or it refuses everything.

    Two shapes are publishable and both are ordinary: a successor to a predecessor with NO declared
    end (the predecessor's asserted interval simply closes at the successor's start, 11.4), and an
    ADJACENT successor whose start equals the predecessor's declared end (11.4's explicit adjacency
    branch, which is valid).
    """

    open_ended = _row("0001", effective_from=_NOW - timedelta(days=30))
    assert (
        configuration_policy.prospective_publication_defects(
            _context([open_ended]),
            _proposed(effective_from=_NOW - timedelta(days=1)),
        )
        == ()
    )

    declared_end = _NOW - timedelta(hours=6)
    adjacent = _row(
        "0001",
        effective_from=_NOW - timedelta(hours=48),
        declared_effective_to=declared_end,
        published_at=_NOW - timedelta(hours=48),
    )
    assert (
        configuration_policy.prospective_publication_defects(
            _context([adjacent]), _proposed(effective_from=declared_end)
        )
        == ()
    )


def test_an_append_starting_before_a_still_declared_predecessor_end_is_refused() -> None:
    """THE R20 REGRESSION, in its pure form.

    PF-1A-E3's UPDATE APPENDS; it does not retract and republish. So a predecessor carrying a
    finite `declared_effective_to` stays asserted beside the new version, and a new version that
    starts BEFORE that declared end leaves 11.4's EXPLICIT OVERLAP - which fails the whole object's
    resolution closed under the unchanged kernel.

    The interval below is STRICTLY NARROWER in entitlement terms, which `classify_risk` correctly
    reads as not a privilege increase. That classification is right and is not changed here. It is
    simply not an answer to whether the append may be published, and treating it as one is exactly
    the defect this check removes.
    """

    predecessor = _row(
        "0001",
        effective_from=_NOW - timedelta(hours=48),
        declared_effective_to=_NOW - timedelta(hours=2),
        published_at=_NOW - timedelta(hours=48),
    )
    defects = configuration_policy.prospective_publication_defects(
        _context([predecessor]),
        _proposed(
            effective_from=_NOW - timedelta(hours=36),
            declared_effective_to=_NOW - timedelta(hours=6),
        ),
    )

    assert defects
    assert any(e2.AUTHORITY_LINEAGE_CONTRADICTORY in defect for defect in defects)
    assert any("explicit overlap" in defect for defect in defects)


def test_prospective_validation_catches_defect_classes_other_than_the_overlap_shape() -> None:
    """The check is the KERNEL's verdict on the whole prospective lineage, not one hard-coded rule.

    Three structurally unrelated defects, each reached through a different part of PF-1A-E2-A and
    none of them an interval overlap: a duplicate start (11.6's pre-check, a lineage-level defect
    with no attributed version), recorded provenance that decreases across the version order
    (11.8.3), and material that is not a published-version record at all (the 9.3.3 DTO/port
    boundary, which is not a semantic classification and is reported as its own kind).

    A local "do these two intervals overlap?" rule would pass all three.
    """

    start = _NOW - timedelta(days=30)
    duplicate_start = configuration_policy.prospective_publication_defects(
        _context([_row("0001", effective_from=start)]),
        _proposed(effective_from=start),
    )
    assert any("share one effective_from" in defect for defect in duplicate_start)

    recorded_backwards = configuration_policy.prospective_publication_defects(
        _context([_row("0001", effective_from=start, published_at=_NOW)]),
        _proposed(
            effective_from=_NOW - timedelta(days=1),
            published_at=_NOW - timedelta(days=2),
        ),
    )
    assert any(e2.PUBLICATION_PROVENANCE_INVALID in defect for defect in recorded_backwards)
    assert any("published_at decreases" in defect for defect in recorded_backwards)

    ill_formed = configuration_policy.prospective_publication_defects(
        _context([_row("0001", effective_from=start)]),
        _proposed(effective_from=_NOW - timedelta(days=1), active_flag=None),
    )
    assert any(material.MATERIAL_ILL_FORMED in defect for defect in ill_formed)


def test_prospective_validation_delegates_rather_than_re_deriving_the_rules() -> None:
    """It must ask the unchanged kernel, not grow a second copy of closure semantics.

    A partial local rule would pass every defect class it did not anticipate, and would also be the
    duplicated-semantics defect this package has already been corrected for once.
    """

    tree = ast.parse(inspect.getsource(configuration_policy.prospective_publication_defects))
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    # Asserted over the CALL GRAPH rather than over raw text, because this function's own docstring
    # names both kernel entry points and a substring scan would therefore pass on prose alone.
    assert {"check_material_well_formed", "evaluate_lineage"} <= called
    assert "_intervals_overlap" not in called


def test_the_authority_graph_is_derived_by_the_unchanged_e2_kernel_not_reimplemented() -> None:
    """The semantics are IMPORTED, and the shortcut that replaced them is GONE.

    An earlier revision ranked published rows by the store's physical append order and treated
    "the latest non-retracted row" as current. That is a second notion of currency which
    disagrees with the kernel's, so the functions that expressed it are removed rather than left
    unused, and `PublishedRow` no longer carries the append-order field they ranked by.
    """

    assert configuration_policy.evaluate_lineage is lineage.evaluate_lineage
    assert configuration_policy.check_material_well_formed is material.check_material_well_formed

    for removed in ("latest_rows_by_object", "active_latest_rows", "current_payload"):
        assert not hasattr(configuration_policy, removed), removed
    assert not any(
        field.name == "publication_sequence"
        for field in dataclasses.fields(configuration_domain.PublishedRow)
    )

    # And no local copy of the closure / effectiveness rules crept back in beside the import.
    source = inspect.getsource(configuration_policy)
    for forbidden in (
        "def is_effective",
        "def _derive_asserted_intervals",
        "def _select_effective",
        "def _validate_structure",
    ):
        assert forbidden not in source, forbidden


def test_derive_effective_state_separates_the_effective_version_from_the_predecessor() -> None:
    """THE PURE FORM OF THE EFFECTIVENESS REGRESSION.

    A live version plus a later-published, future-effective INACTIVE successor. The effective
    version is still the live one - which is what every linkage and grant question needs - while
    the authoritative predecessor is the successor, because that is what a further UPDATE would
    supersede. Answering both questions with one value is wrong whichever value is chosen.
    """

    live = _row("0001", effective_from=_NOW - timedelta(days=30))
    future = _row(
        "0002",
        effective_from=_NOW + timedelta(days=30),
        active_flag=False,
        published_at=_NOW - timedelta(days=1),
    )

    state = configuration_policy.derive_effective_state((live, future), (), _NOW)

    assert state.unresolved == ()
    assert state.effective_rows[_UNIT_OBJECT] is live
    assert state.predecessor_rows[_UNIT_OBJECT] is future


def test_derive_effective_state_keeps_a_predecessor_whose_interval_has_lapsed() -> None:
    """A lapsed interval has no effective version but still has something to supersede.

    Conflating the two would make an identical republication of a lapsed version unprovable as
    non-increasing, and would therefore demand a second person for a change that grants nothing.
    """

    lapsed = _row(
        "0001",
        effective_from=_NOW - timedelta(days=30),
        declared_effective_to=_NOW - timedelta(days=1),
    )

    state = configuration_policy.derive_effective_state((lapsed,), (), _NOW)

    assert state.unresolved == ()
    assert _UNIT_OBJECT not in state.effective_rows
    assert state.predecessor_rows[_UNIT_OBJECT] is lapsed


def test_derive_effective_state_fails_closed_on_a_lineage_it_cannot_establish() -> None:
    """Two current-asserted versions sharing one start have no single current answer, so the
    object is reported UNRESOLVED rather than resolved to whichever was written last."""

    start = _NOW - timedelta(days=30)
    state = configuration_policy.derive_effective_state(
        (_row("0001", effective_from=start), _row("0002", effective_from=start)), (), _NOW
    )

    assert state.effective_rows == {}
    assert state.predecessor_rows == {}
    assert state.unresolved == (
        f"{configuration_policy.LINEAGE_UNRESOLVED_PREFIX}:"
        f"{_UNIT_OBJECT[0]}/{_UNIT_OBJECT[1]}",
    )


def test_a_retracted_version_is_never_the_authoritative_predecessor() -> None:
    """Even as the lexicographic maximum. A valid retraction removes its target from the current
    asserted lineage, and that is the only lineage a predecessor can come from."""

    survivor = _row("aaa", effective_from=_NOW - timedelta(days=30))
    withdrawn = _row("zzz", effective_from=_NOW - timedelta(days=20), retracted=True)
    assertion = configuration_domain.RetractionRow(
        object_family=_UNIT_OBJECT[0],
        object_id=_UNIT_OBJECT[1],
        object_version="zzz",
        retraction_id="e3-unit-retraction",
        retracted_at=_NOW - timedelta(days=10),
        publication_reference_type=e2.BOOTSTRAP_PROVENANCE,
        publication_reference_id="e3-unit-test",
    )

    state = configuration_policy.derive_effective_state(
        (survivor, withdrawn), (assertion,), _NOW
    )

    assert state.unresolved == ()
    assert state.predecessor_rows[_UNIT_OBJECT] is survivor
    assert state.effective_rows[_UNIT_OBJECT] is survivor


def test_publication_time_monotonicity_permits_equality_and_fails_closed_otherwise() -> None:
    """PF-1A-E2-A 11.8.3 requires NON-DECREASING, not strictly increasing, so equality passes.
    Everything that cannot be compared refuses; nothing is rewritten to make it comparable."""

    check = configuration_policy.publication_time_is_non_decreasing
    anchor = configuration_domain.AllocationAnchor

    # No published version at all: there is nothing to be earlier than.
    assert check(anchor(), _NOW) is True
    assert check(anchor(object_version="v1", published_at=_NOW), _NOW) is True
    assert check(anchor(object_version="v1", published_at=_NOW - timedelta(days=1)), _NOW) is True
    # A clock rollback: the anchor was recorded AHEAD of the activation instant.
    assert (
        check(anchor(object_version="v1", published_at=_NOW + timedelta(seconds=1)), _NOW)
        is False
    )
    # An anchor exists but its recorded time is absent or unusable: refuse, never assume.
    assert check(anchor(object_version="v1", published_at=None), _NOW) is False
    assert check(anchor(object_version="v1", published_at=datetime(2020, 1, 1)), _NOW) is False
    # Aware but NOT UTC-normalized. Comparable, and still refused: PF-1A-E2-A 11.8.3 requires a
    # UTC-normalized recorded time, and rewriting one into UTC here would manufacture conformance.
    offset = timezone(timedelta(hours=5, minutes=30))
    non_utc = datetime(2020, 1, 1, tzinfo=offset)
    assert check(anchor(object_version="v1", published_at=non_utc), _NOW) is False


def test_the_table_names_match_the_models_that_implement_them() -> None:
    assert (
        configuration_models.AuthorityConfigurationChange.__tablename__
        == e3.CONFIGURATION_CHANGE_TABLE
    )
    assert (
        configuration_models.AuthorityConfigurationEvaluation.__tablename__
        == e3.CONFIGURATION_EVALUATION_TABLE
    )
    assert e3.CONFIGURATION_TABLES_CHILD_FIRST == (
        e3.CONFIGURATION_EVALUATION_TABLE,
        e3.CONFIGURATION_CHANGE_TABLE,
    )


def test_the_policy_layer_is_pure_no_clock_no_session_no_provider() -> None:
    """Purity is what makes every governance rule directly testable and stops the service
    acquiring a second, quieter copy of one."""

    source = inspect.getsource(configuration_policy)
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "sqlalchemy" not in imported
    assert "fastapi" not in imported
    for forbidden in ("datetime.now", "utcnow", "time.time", "os.environ", "getenv"):
        assert forbidden not in source, forbidden


def test_every_domain_object_is_frozen_and_validates_nothing_at_construction() -> None:
    for name in (
        "ConfigurationChangeProposal",
        "PublishedRow",
        "RetractionRow",
        "AllocationAnchor",
        "EffectiveConfigurationState",
        "AuthorityContext",
        "RiskClassification",
        "GovernanceEvaluation",
        "ConfigurationChangeOutcome",
    ):
        cls = getattr(configuration_domain, name)
        assert dataclasses.is_dataclass(cls)
        assert cls.__dataclass_params__.frozen is True

    # A structurally impossible proposal is CONSTRUCTIBLE: rejecting it here would move the rule
    # out of the layer the tests inspect.
    built = configuration_domain.ConfigurationChangeProposal(
        configuration_object_family="NOT_A_FAMILY",
        configuration_object_id="",
        change_type="NOT_A_CHANGE",
        change_payload={},
        effective_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert built.change_type == "NOT_A_CHANGE"
