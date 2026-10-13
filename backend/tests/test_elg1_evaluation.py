"""ELG-1 - the eligibility decision, pure (backend/app/modules/eligibility/evaluation.py).

docs/agent/slices/elg-1-machine-eligibility.md, sections 5.3, 6 and 7, and section 16's first list: choosing
a rule, cover, renewals, withdrawals, "not applicable", transport vehicles, permits, an unmapped crane, a
carrier's papers, every outcome and the answer. No database: every record here is built in the test.
"""

from __future__ import annotations

from datetime import date, timedelta
from itertools import count

import pytest

from app.modules.eligibility import evaluation as ev
from app.modules.eligibility.contract import (
    BAND_COPY_MISSING,
    BAND_MISSING,
    BAND_RUN_OUT,
    BAND_WITHIN_15,
    BAND_WITHIN_30,
    BAND_WITHIN_60,
    EFFECT_BLOCK,
    EFFECT_NONE,
    EFFECT_OVERRIDE,
    EFFECT_WARNING,
    OUTCOME_COPY_MISSING,
    OUTCOME_MISSING,
    OUTCOME_NOT_APPLICABLE,
    OUTCOME_RETIRED,
    OUTCOME_RUN_OUT,
    OUTCOME_RUNS_OUT_BEFORE_START,
    OUTCOME_RUNS_OUT_IN_PERIOD,
    OUTCOME_RUNS_OUT_SOON,
    OUTCOME_VALID,
    OVERALL_BLOCKED,
    OVERALL_ELIGIBLE,
    OVERALL_OVERRIDE_REQUIRED,
    OVERALL_WARNING,
)

TODAY = date(2026, 9, 27)
FIRST_DAY = date(2025, 11, 21)
_ids = count(1)

KINDS = {
    code: ev.Kind(code, code.title(), end_optional, valid_in, exam, registration, order)
    for order, (code, end_optional, valid_in, exam, registration) in enumerate(
        (
            ("REGISTRATION", False, False, False, True),
            ("INSURANCE", False, False, False, False),
            ("POLLUTION_UNDER_CONTROL", False, False, False, False),
            ("ROAD_TAX", True, False, False, False),
            ("FITNESS", False, False, False, False),
            ("PERMIT", False, True, False, False),
            ("THOROUGH_EXAMINATION", True, False, True, False),
            ("LOAD_TEST", True, False, True, False),
        )
    )
}


def rule(
    kind: str,
    class_code: str = "CRANE",
    *,
    type_code: str | None = None,
    applies: str = "ALWAYS",
    jurisdiction: str | None = None,
    start: date = FIRST_DAY,
    end: date | None = None,
    months: int | None = None,
    basis: str = "STATUTORY",
    lapse: str = "BLOCK",
    not_applicable: str = "NOT_ALLOWED",
    max_months: int | None = None,
) -> ev.Rule:
    rule_id = next(_ids)
    return ev.Rule(rule_id, f"rule-{rule_id}", kind, class_code, type_code, applies, jurisdiction, start, end, months, basis, lapse, not_applicable, max_months)


def cert(
    kind: str,
    asset: str = "crane",
    *,
    issued: date | None = None,
    start: date = date(2026, 1, 1),
    until: date | None = date(2027, 1, 1),
    valid_in: str | None = None,
    registered_as: str | None = None,
    withdrawn: bool = False,
    copy: bool = True,
) -> ev.Certificate:
    certificate_id = next(_ids)
    return ev.Certificate(certificate_id, f"cert-{certificate_id}", asset, kind, issued or start, start, until, valid_in, registered_as, withdrawn, copy)


def mark(kind: str, asset: str = "crane", *, until: date | None = None, recorded: date = TODAY, withdrawn: bool = False) -> ev.Mark:
    mark_id = next(_ids)
    return ev.Mark(mark_id, f"mark-{mark_id}", asset, kind, until, recorded, withdrawn)


CRANE = ev.Asset("crane", "CRANE", "ALL_TERRAIN", True)
CRAWLER = ev.Asset("crane", "CRANE", "CRAWLER", True)
UNMAPPED = ev.Asset("crane", "CRANE", None, True)
CARRIER = ev.Asset("carrier", "CRANE_CARRIER", None, True)
GUJARAT = ev.Site("IN-GJ", False)
NEXT_MONTH = ev.Period(date(2026, 10, 1), date(2026, 10, 31))


def crane_unit(asset: ev.Asset = CRANE, *, carrier: bool = True) -> tuple[ev.Member, ...]:
    if not carrier:
        return (ev.Member(asset, (asset.asset_public_id,)),)
    return (ev.Member(asset, (asset.asset_public_id, "carrier")), ev.Member(CARRIER, ("carrier",)))


def evidence(rules: list[ev.Rule], certificates: list[ev.Certificate] = (), marks: list[ev.Mark] = ()) -> ev.Evidence:
    return ev.Evidence(KINDS, tuple(rules), tuple(certificates), tuple(marks))


def decide(rules, certificates=(), marks=(), *, members=None, site=GUJARAT, period=NEXT_MONTH, today=TODAY) -> ev.Decision:
    return ev.evaluate(members or crane_unit(), evidence(rules, certificates, marks), site=site, period=period, today=today)


def only(decision: ev.Decision, kind: str) -> ev.Result:
    [result] = [result for result in decision.results if result.kind_code == kind]
    return result


# --- Choosing the rule ------------------------------------------------------------------------------------


def test_a_states_rule_is_chosen_before_the_baseline_and_elsewhere_the_baseline_applies() -> None:
    baseline = rule("INSURANCE")
    gujarat = rule("INSURANCE", jurisdiction="IN-GJ", lapse="NOT_REQUIRED")
    choose = lambda where: ev.choose_rule([baseline, gujarat], kind_code="INSURANCE", asset=CRANE, jurisdiction_code=where, day=TODAY, transport=False)
    assert choose("IN-GJ") == gujarat
    assert choose("IN-MH") == baseline
    assert choose(None) == baseline
    # Not required in Gujarat: no result at all there.
    assert [result.kind_code for result in decide([baseline, gujarat]).results] == []
    assert only(decide([baseline, gujarat], site=ev.Site("IN-MH", False)), "INSURANCE").outcome_code == OUTCOME_MISSING


def test_at_a_central_government_site_the_examinations_follow_in_and_road_papers_the_state() -> None:
    examination_in = rule("THOROUGH_EXAMINATION", jurisdiction="IN", months=6, basis="PBL_RULE")
    examination_baseline = rule("THOROUGH_EXAMINATION", months=12, basis="PBL_RULE")
    insurance_in = rule("INSURANCE", jurisdiction="IN", lapse="NOT_REQUIRED")
    insurance_baseline = rule("INSURANCE")
    rules = [examination_in, examination_baseline, insurance_in, insurance_baseline]
    central = decide(rules, site=ev.Site("IN-GJ", True))
    assert only(central, "THOROUGH_EXAMINATION").rule == examination_in
    # Road papers never come from IN: insurance is still the state's (here the baseline's) and required.
    assert only(central, "INSURANCE").rule == insurance_baseline
    private = decide(rules, site=GUJARAT)
    assert only(private, "THOROUGH_EXAMINATION").rule == examination_baseline


def test_a_rule_for_the_type_comes_before_one_for_the_class_and_an_unmapped_crane_takes_the_class_rule() -> None:
    class_rule = rule("REGISTRATION")
    crawler_rule = rule("REGISTRATION", type_code="CRAWLER", not_applicable="ALLOWED")
    choose = lambda asset: ev.choose_rule([class_rule, crawler_rule], kind_code="REGISTRATION", asset=asset, jurisdiction_code=None, day=TODAY, transport=False)
    assert choose(CRAWLER) == crawler_rule
    assert choose(CRANE) == class_rule
    # Unknown never counts as exempt: an unmapped crane is judged by the class rule, which allows no mark.
    assert choose(UNMAPPED) == class_rule
    assert ev.rule_allowing_mark([class_rule, crawler_rule], kind_code="REGISTRATION", asset=UNMAPPED, today=TODAY) is None
    assert ev.rule_allowing_mark([class_rule, crawler_rule], kind_code="REGISTRATION", asset=CRAWLER, today=TODAY) == crawler_rule
    assert ev.rule_allowing_mark([class_rule, crawler_rule], kind_code="REGISTRATION", asset=CRANE, today=TODAY) is None


def test_a_state_rule_for_the_class_comes_before_a_baseline_rule_for_the_type() -> None:
    state_class = rule("REGISTRATION", jurisdiction="IN-GJ")
    baseline_type = rule("REGISTRATION", type_code="CRAWLER", not_applicable="ALLOWED")
    assert ev.choose_rule([state_class, baseline_type], kind_code="REGISTRATION", asset=CRAWLER, jurisdiction_code="IN-GJ", day=TODAY, transport=False) == state_class
    # A crawler's mark recorded under the baseline does not count in Gujarat, whose rule allows none.
    decision = decide([state_class, baseline_type], [], [mark("REGISTRATION")], members=crane_unit(CRAWLER, carrier=False))
    assert only(decision, "REGISTRATION").outcome_code == OUTCOME_MISSING
    elsewhere = decide([state_class, baseline_type], [], [mark("REGISTRATION")], members=crane_unit(CRAWLER, carrier=False), site=ev.Site("IN-MH", False))
    assert only(elsewhere, "REGISTRATION").outcome_code == OUTCOME_NOT_APPLICABLE


def test_rules_are_chosen_by_date_and_the_later_of_today_and_the_start() -> None:
    old = rule("THOROUGH_EXAMINATION", months=12, basis="PBL_RULE", end=date(2026, 10, 14))
    new = rule("THOROUGH_EXAMINATION", months=6, basis="PBL_RULE", start=date(2026, 10, 15))
    choose = lambda day: ev.choose_rule([old, new], kind_code="THOROUGH_EXAMINATION", asset=CRANE, jurisdiction_code=None, day=day, transport=False)
    assert choose(date(2026, 10, 14)) == old and choose(date(2026, 10, 15)) == new
    # Judged for a job starting after the change: the successor's interval applies.
    examination = cert("THOROUGH_EXAMINATION", start=date(2026, 3, 1), until=None)
    later = decide([old, new], [examination], period=ev.Period(date(2026, 11, 1), date(2026, 11, 30)))
    assert only(later, "THOROUGH_EXAMINATION").rule == new
    assert only(later, "THOROUGH_EXAMINATION").cover_ends_on == date(2026, 8, 31)
    assert only(later, "THOROUGH_EXAMINATION").outcome_code == OUTCOME_RUN_OUT
    earlier = decide([old, new], [examination])
    assert only(earlier, "THOROUGH_EXAMINATION").rule == old
    assert only(earlier, "THOROUGH_EXAMINATION").cover_ends_on == date(2027, 2, 28)


def test_a_rule_not_yet_in_effect_or_already_ended_is_not_chosen() -> None:
    assert ev.choose_rule([rule("INSURANCE", start=date(2026, 12, 1))], kind_code="INSURANCE", asset=CRANE, jurisdiction_code=None, day=TODAY, transport=False) is None
    assert ev.choose_rule([rule("INSURANCE", end=date(2026, 9, 26))], kind_code="INSURANCE", asset=CRANE, jurisdiction_code=None, day=TODAY, transport=False) is None


# --- Cover ----------------------------------------------------------------------------------------------


def test_cover_is_the_earlier_of_valid_until_and_the_examinations_interval() -> None:
    twelve = rule("THOROUGH_EXAMINATION", months=12, basis="PBL_RULE")
    six = rule("THOROUGH_EXAMINATION", months=6, basis="PBL_RULE")
    stated_end = cert("THOROUGH_EXAMINATION", start=date(2026, 1, 1), until=date(2026, 12, 31))
    # By the certificate's own end.
    assert ev.cover_end(stated_end, twelve) == date(2026, 12, 31)
    # By the interval: an examination made under a 12-month rule stops counting after 6 where 6 apply.
    assert ev.cover_end(stated_end, six) == date(2026, 6, 30)
    # With no stated end, the interval alone; and a one-time road tax covers without end.
    assert ev.cover_end(cert("THOROUGH_EXAMINATION", start=date(2025, 12, 1), until=None), twelve) == date(2026, 11, 30)
    assert ev.cover_end(cert("ROAD_TAX", until=None), rule("ROAD_TAX")) is None


def test_month_arithmetic_keeps_to_the_months_last_day() -> None:
    assert ev.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert ev.add_months(date(2027, 12, 15), 2) == date(2028, 2, 15)
    assert ev.months_after(date(2025, 10, 1), 12) == date(2026, 9, 30)


def test_a_renewal_continues_the_cover_when_it_starts_by_the_day_after() -> None:
    insurance = rule("INSURANCE")
    first = cert("INSURANCE", start=date(2025, 10, 5), until=date(2026, 10, 4))
    chained = cert("INSURANCE", start=date(2026, 10, 5), until=date(2027, 10, 4))
    assert ev.cover([first, chained], insurance, TODAY).ends_on == date(2027, 10, 4)
    gap = cert("INSURANCE", start=date(2026, 10, 7), until=date(2027, 10, 6))
    assert ev.cover([first, gap], insurance, TODAY).ends_on == date(2026, 10, 4)
    # A renewal without its copy does not continue it (Q5).
    unproven = cert("INSURANCE", start=date(2026, 10, 5), until=date(2027, 10, 4), copy=False)
    assert ev.cover([first, unproven], insurance, TODAY).ends_on == date(2026, 10, 4)


def test_a_renewal_recorded_ahead_takes_over_on_its_start_and_a_withdrawn_one_brings_back_the_one_before() -> None:
    insurance = rule("INSURANCE")
    current = cert("INSURANCE", start=date(2025, 12, 1), until=date(2026, 11, 30))
    ahead = cert("INSURANCE", start=date(2026, 12, 1), until=date(2027, 11, 30))
    assert ev.in_force([current, ahead], TODAY) == current
    assert ev.in_force([current, ahead], date(2026, 12, 1)) == ahead
    wrong = cert("INSURANCE", start=date(2026, 9, 1), until=date(2026, 9, 20))
    assert only(decide([insurance], [current, wrong]), "INSURANCE").outcome_code == OUTCOME_RUN_OUT
    withdrawn = cert("INSURANCE", start=date(2026, 9, 1), until=date(2026, 9, 20), withdrawn=True)
    result = only(decide([insurance], [current, withdrawn]), "INSURANCE")
    assert result.certificate == current and result.outcome_code == OUTCOME_VALID and result.cover_ends_on == date(2026, 11, 30)


# --- Outcomes ------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("certificates", "period", "outcome", "effect"),
    [
        ([], NEXT_MONTH, OUTCOME_MISSING, EFFECT_BLOCK),
        ([cert("INSURANCE", copy=False)], NEXT_MONTH, OUTCOME_COPY_MISSING, EFFECT_BLOCK),
        ([cert("INSURANCE", start=date(2025, 9, 1), until=date(2026, 9, 26))], NEXT_MONTH, OUTCOME_RUN_OUT, EFFECT_BLOCK),
        ([cert("INSURANCE", until=date(2026, 9, 30))], NEXT_MONTH, OUTCOME_RUNS_OUT_BEFORE_START, EFFECT_WARNING),
        ([cert("INSURANCE", until=date(2026, 10, 20))], NEXT_MONTH, OUTCOME_RUNS_OUT_IN_PERIOD, EFFECT_WARNING),
        ([cert("INSURANCE", until=date(2026, 10, 10))], ev.Period(TODAY, date(2026, 10, 1)), OUTCOME_RUNS_OUT_SOON, EFFECT_WARNING),
        ([cert("INSURANCE", until=date(2027, 9, 1))], NEXT_MONTH, OUTCOME_VALID, EFFECT_NONE),
        # An open-ended period: a cover with an end runs out during it.
        ([cert("INSURANCE", until=date(2027, 9, 1))], ev.Period(date(2026, 10, 1), None), OUTCOME_RUNS_OUT_IN_PERIOD, EFFECT_WARNING),
        # Covering to the period's last day is enough.
        ([cert("INSURANCE", until=date(2026, 10, 31))], NEXT_MONTH, OUTCOME_VALID, EFFECT_NONE),
    ],
    ids=["missing", "copy-missing", "run-out", "before-start", "in-period", "soon", "valid", "open-ended", "covers-last-day"],
)
def test_every_outcome_of_section_6(certificates, period, outcome, effect) -> None:
    result = only(decide([rule("INSURANCE")], certificates, period=period), "INSURANCE")
    assert (result.outcome_code, result.effect_code) == (outcome, effect)


@pytest.mark.parametrize(
    ("lapse", "answer"), [("BLOCK", OVERALL_BLOCKED), ("OVERRIDE", OVERALL_OVERRIDE_REQUIRED), ("WARN", OVERALL_WARNING)]
)
def test_what_a_lapse_does_decides_the_answer(lapse: str, answer: str) -> None:
    decision = decide([rule("INSURANCE", basis="PBL_RULE", lapse=lapse)])
    assert decision.overall_code == answer
    assert only(decision, "INSURANCE").effect_code == {"BLOCK": EFFECT_BLOCK, "OVERRIDE": EFFECT_OVERRIDE, "WARN": EFFECT_WARNING}[lapse]


def test_block_outranks_override_which_outranks_a_warning_and_valid_until_is_the_earliest_end() -> None:
    insurance, tax, examination = rule("INSURANCE"), rule("ROAD_TAX"), rule("THOROUGH_EXAMINATION", months=12, basis="PBL_RULE", lapse="OVERRIDE")
    valid = [cert("INSURANCE", until=date(2027, 3, 1)), cert("ROAD_TAX", until=None), cert("THOROUGH_EXAMINATION", start=date(2026, 6, 1), until=None)]
    eligible = decide([insurance, tax, examination], valid)
    assert eligible.overall_code == OVERALL_ELIGIBLE
    assert eligible.valid_until == date(2027, 3, 1)
    override = decide([insurance, tax, examination], valid[:2])
    assert override.overall_code == OVERALL_OVERRIDE_REQUIRED
    blocked = decide([insurance, tax, examination], valid[1:2])
    assert blocked.overall_code == OVERALL_BLOCKED and blocked.valid_until is None


def test_a_retired_asset_is_blocked_and_its_certificates_are_still_judged() -> None:
    retired = ev.Asset("crane", "CRANE", "ALL_TERRAIN", False)
    decision = decide([rule("INSURANCE")], [cert("INSURANCE", until=date(2027, 9, 1))], members=crane_unit(retired, carrier=False))
    assert decision.overall_code == OVERALL_BLOCKED
    assert decision.results[0].outcome_code == OUTCOME_RETIRED and decision.results[0].kind_code is None
    assert only(decision, "INSURANCE").outcome_code == OUTCOME_VALID


# --- "Not applicable" ----------------------------------------------------------------------------------


def test_a_mark_counts_where_the_rule_allows_it_and_its_end_is_the_covers_end() -> None:
    allowed = rule("REGISTRATION", type_code="CRAWLER", not_applicable="ALLOWED")
    ending = mark("REGISTRATION", until=date(2027, 1, 31))
    decision = decide([allowed, rule("INSURANCE", type_code="CRAWLER")], [cert("INSURANCE", until=date(2027, 9, 1))], [ending], members=crane_unit(CRAWLER, carrier=False))
    result = only(decision, "REGISTRATION")
    assert (result.outcome_code, result.effect_code, result.mark) == (OUTCOME_NOT_APPLICABLE, EFFECT_NONE, ending)
    assert decision.overall_code == OVERALL_ELIGIBLE and decision.valid_until == date(2027, 1, 31)


def test_a_mark_does_not_count_where_the_rule_allows_none_or_after_it_ends_or_once_withdrawn() -> None:
    clear = rule("REGISTRATION")
    assert only(decide([clear], [], [mark("REGISTRATION")], members=crane_unit(carrier=False)), "REGISTRATION").outcome_code == OUTCOME_MISSING
    allowed = rule("REGISTRATION", type_code="CRAWLER", not_applicable="ALLOWED")
    members = crane_unit(CRAWLER, carrier=False)
    for stale in (mark("REGISTRATION", until=date(2026, 9, 26)), mark("REGISTRATION", withdrawn=True)):
        assert only(decide([allowed], [], [stale], members=members), "REGISTRATION").outcome_code == OUTCOME_MISSING


def test_a_limited_mark_counts_only_within_the_rules_months() -> None:
    puc = rule("POLLUTION_UNDER_CONTROL", not_applicable="ALLOWED", max_months=12)
    within = mark("POLLUTION_UNDER_CONTROL", until=date(2027, 9, 26), recorded=TODAY)
    beyond = mark("POLLUTION_UNDER_CONTROL", until=date(2027, 9, 27), recorded=TODAY)
    open_ended = mark("POLLUTION_UNDER_CONTROL", until=None, recorded=TODAY)
    assert ev.mark_limit(puc, TODAY) == date(2027, 9, 26)
    assert ev.counted_mark([within], puc, TODAY) == within
    assert ev.counted_mark([beyond], puc, TODAY) is None
    assert ev.counted_mark([open_ended], puc, TODAY) is None


def test_a_mark_on_the_carrier_counts_for_the_crane_as_a_certificate_would() -> None:
    allowed = rule("INSURANCE", type_code="CRAWLER", not_applicable="ALLOWED")
    members = crane_unit(CRAWLER)
    result = only(decide([allowed], [], [mark("INSURANCE", asset="carrier")], members=members), "INSURANCE")
    assert result.outcome_code == OUTCOME_NOT_APPLICABLE


# --- Transport vehicles ------------------------------------------------------------------------------------


def _road_rules() -> list[ev.Rule]:
    return [rule("REGISTRATION"), rule("FITNESS", applies="TRANSPORT_ONLY"), rule("PERMIT", applies="TRANSPORT_ONLY")]


def test_fitness_and_a_permit_apply_on_a_transport_registration_and_not_on_a_non_transport_one() -> None:
    transport = decide(_road_rules(), [cert("REGISTRATION", asset="carrier", registered_as="TRANSPORT")])
    assert {result.kind_code for result in transport.results} == {"REGISTRATION", "FITNESS", "PERMIT"}
    assert only(transport, "FITNESS").outcome_code == OUTCOME_MISSING
    plain = decide(_road_rules(), [cert("REGISTRATION", asset="carrier", registered_as="NON_TRANSPORT")])
    assert {result.kind_code for result in plain.results} == {"REGISTRATION"}
    assert plain.overall_code == OVERALL_ELIGIBLE


def test_with_no_registration_recorded_the_transport_rules_do_not_apply() -> None:
    # The owner, 1 October 2026 (ELG-2's screen check): no registration recorded is not a transport vehicle. The
    # registration is itself required: missing, it blocks on its own.
    missing = decide(_road_rules(), [])
    assert {result.kind_code for result in missing.results} == {"REGISTRATION"}
    assert only(missing, "REGISTRATION").outcome_code == OUTCOME_MISSING
    assert missing.overall_code == OVERALL_BLOCKED
    crawler_rules = _road_rules() + [rule("REGISTRATION", type_code="CRAWLER", not_applicable="ALLOWED")]
    not_a_vehicle = decide(crawler_rules, [], [mark("REGISTRATION")], members=crane_unit(CRAWLER, carrier=False))
    assert {result.kind_code for result in not_a_vehicle.results} == {"REGISTRATION"}
    assert not_a_vehicle.overall_code == OVERALL_ELIGIBLE


def test_a_permit_counts_only_in_the_sites_state_or_all_india() -> None:
    registration = cert("REGISTRATION", registered_as="TRANSPORT")
    fitness = cert("FITNESS")
    elsewhere = decide(_road_rules(), [registration, fitness, cert("PERMIT", valid_in="IN-MH")])
    assert only(elsewhere, "PERMIT").outcome_code == OUTCOME_MISSING
    here = decide(_road_rules(), [registration, fitness, cert("PERMIT", valid_in="IN-GJ")])
    assert only(here, "PERMIT").outcome_code == OUTCOME_VALID
    national = decide(_road_rules(), [registration, fitness, cert("PERMIT", valid_in="IN")])
    assert only(national, "PERMIT").outcome_code == OUTCOME_VALID
    # Of two in force, the one covering longer.
    both = decide(_road_rules(), [registration, fitness, cert("PERMIT", valid_in="IN-GJ", until=date(2026, 9, 30)), cert("PERMIT", valid_in="IN", until=date(2027, 6, 1))])
    assert only(both, "PERMIT").cover_ends_on == date(2027, 6, 1)


# --- A unit ----------------------------------------------------------------------------------------------


def test_the_carriers_certificates_count_for_its_crane_but_a_pieces_rule_is_met_by_the_piece_alone() -> None:
    insurance = rule("INSURANCE")
    on_carrier = decide([insurance], [cert("INSURANCE", asset="carrier", until=date(2027, 9, 1))])
    result = only(on_carrier, "INSURANCE")
    assert result.asset_public_id == "crane" and result.certificate.asset_public_id == "carrier"
    assert on_carrier.overall_code == OVERALL_ELIGIBLE
    hook = ev.Asset("hook", "HOOK_BLOCK", "HOOK_BLOCK", True)
    hook_rule = rule("THOROUGH_EXAMINATION", "HOOK_BLOCK", months=12, basis="PBL_RULE")
    members = (ev.Member(hook, ("hook",)),)
    alone = ev.evaluate(members, evidence([hook_rule], [cert("THOROUGH_EXAMINATION", asset="crane", until=None)]), site=GUJARAT, period=NEXT_MONTH, today=TODAY)
    assert only(alone, "THOROUGH_EXAMINATION").outcome_code == OUTCOME_MISSING


def test_a_slings_six_months_come_before_the_tackle_classs_twelve() -> None:
    sling = ev.Asset("sling", "LIFTING_TACKLE", "SLING", True)
    tackle_rule = rule("THOROUGH_EXAMINATION", "LIFTING_TACKLE", months=12, basis="PBL_RULE")
    sling_rule = rule("THOROUGH_EXAMINATION", "LIFTING_TACKLE", type_code="SLING", months=6, basis="PBL_RULE")
    examined = cert("THOROUGH_EXAMINATION", asset="sling", start=date(2026, 3, 1), until=None)
    decision = ev.evaluate((ev.Member(sling, ("sling",)),), evidence([tackle_rule, sling_rule], [examined]), site=GUJARAT, period=NEXT_MONTH, today=TODAY)
    assert only(decision, "THOROUGH_EXAMINATION").rule == sling_rule
    assert only(decision, "THOROUGH_EXAMINATION").cover_ends_on == date(2026, 8, 31)
    assert decision.overall_code == OVERALL_BLOCKED


# --- The renewal list ----------------------------------------------------------------------------------------


def test_the_baseline_results_and_their_bands() -> None:
    rules = [rule("INSURANCE"), rule("ROAD_TAX"), rule("REGISTRATION"), rule("POLLUTION_UNDER_CONTROL", not_applicable="ALLOWED", max_months=12), rule("LOAD_TEST", months=60, basis="PBL_RULE")]
    certificates = [
        cert("INSURANCE", until=TODAY + timedelta(days=10)),
        cert("ROAD_TAX", until=TODAY + timedelta(days=25), copy=False),
        cert("REGISTRATION", registered_as="NON_TRANSPORT", until=TODAY + timedelta(days=45)),
        cert("LOAD_TEST", start=date(2021, 1, 1), until=None),
    ]
    results = ev.baseline_results(crane_unit(carrier=False), evidence(rules, certificates, [mark("POLLUTION_UNDER_CONTROL", until=TODAY + timedelta(days=20))]), today=TODAY)
    bands = {result.kind_code: ev.due_band(result, TODAY) for result in results}
    assert bands == {
        "INSURANCE": BAND_WITHIN_15,
        "ROAD_TAX": BAND_COPY_MISSING,
        "REGISTRATION": BAND_WITHIN_60,
        "POLLUTION_UNDER_CONTROL": BAND_WITHIN_30,
        "LOAD_TEST": BAND_RUN_OUT,
    }
    assert ev.due_band(ev.Result("crane", "INSURANCE", None, None, None, OUTCOME_MISSING, EFFECT_BLOCK, None), TODAY) == BAND_MISSING
    assert ev.due_band(ev.Result("crane", "INSURANCE", None, None, None, OUTCOME_VALID, EFFECT_NONE, TODAY + timedelta(days=61)), TODAY) is None
    assert ev.due_band(ev.Result("crane", "INSURANCE", None, None, None, OUTCOME_NOT_APPLICABLE, EFFECT_NONE, None), TODAY) is None


# --- What may be recorded, and rules that overlap --------------------------------------------------------------


def test_the_kinds_an_asset_may_hold_include_its_machines_for_a_fitted_part() -> None:
    rules = [rule("INSURANCE"), rule("THOROUGH_EXAMINATION", "HOOK_BLOCK", months=12, basis="PBL_RULE"), rule("FITNESS", "EXCAVATOR", applies="TRANSPORT_ONLY"), rule("ROAD_TAX", jurisdiction="IN-GJ", lapse="NOT_REQUIRED")]
    assert ev.recordable_kinds(rules, class_code="CRANE_CARRIER", type_code=None, fits_class_codes=["CRANE"]) == {"INSURANCE"}
    assert ev.recordable_kinds(rules, class_code="HOOK_BLOCK", type_code="HOOK_BLOCK", fits_class_codes=[]) == {"THOROUGH_EXAMINATION"}
    assert ev.recordable_kinds(rules, class_code="COUNTERWEIGHT", type_code=None, fits_class_codes=[]) == set()


def test_two_rules_overlap_only_with_the_same_key_on_a_common_day() -> None:
    first = rule("INSURANCE", end=date(2026, 12, 31))
    assert ev.overlaps(rule("INSURANCE", start=date(2026, 12, 31)), first)
    assert not ev.overlaps(rule("INSURANCE", start=date(2027, 1, 1)), first)
    assert not ev.overlaps(rule("INSURANCE", jurisdiction="IN-GJ"), first)
    assert not ev.overlaps(rule("INSURANCE", type_code="CRAWLER"), first)
    assert ev.overlaps(rule("INSURANCE"), rule("INSURANCE", start=date(2030, 1, 1)))


# --- Independent review, round 1 (ELG1-R1-002): each asset's certificates are their own sequence ----------------


def test_a_newer_run_out_certificate_on_the_crane_does_not_hide_the_carriers_valid_one() -> None:
    insurance = rule("INSURANCE")
    on_carrier = cert("INSURANCE", asset="carrier", start=date(2026, 1, 1), until=date(2027, 1, 1))
    on_crane = cert("INSURANCE", asset="crane", start=date(2026, 6, 1), until=date(2026, 9, 1))
    result = only(decide([insurance], [on_carrier, on_crane]), "INSURANCE")
    assert (result.outcome_code, result.certificate) == (OUTCOME_VALID, on_carrier)


def test_a_transport_registration_on_any_asset_of_the_unit_calls_for_fitness_and_a_permit() -> None:
    on_carrier = cert("REGISTRATION", asset="carrier", start=date(2026, 1, 1), registered_as="TRANSPORT")
    newer_on_crane = cert("REGISTRATION", asset="crane", start=date(2026, 6, 1), registered_as="NON_TRANSPORT")
    decision = decide(_road_rules(), [on_carrier, newer_on_crane])
    assert {result.kind_code for result in decision.results} == {"REGISTRATION", "FITNESS", "PERMIT"}


def test_a_registration_changed_to_transport_before_the_job_starts_calls_for_fitness_and_a_permit() -> None:
    now = cert("REGISTRATION", start=date(2026, 1, 1), until=date(2030, 1, 1), registered_as="NON_TRANSPORT")
    ahead = cert("REGISTRATION", start=date(2026, 10, 1), until=date(2031, 1, 1), registered_as="TRANSPORT")
    # The job starts after the change: judged as a transport vehicle.
    later = decide(_road_rules(), [now, ahead], period=ev.Period(date(2026, 10, 5), date(2026, 10, 31)))
    assert {result.kind_code for result in later.results} == {"REGISTRATION", "FITNESS", "PERMIT"}
    # A job ending before the change: judged by the registration in force.
    sooner = decide(_road_rules(), [now, ahead], period=ev.Period(date(2026, 9, 28), date(2026, 9, 30)))
    assert {result.kind_code for result in sooner.results} == {"REGISTRATION"}


# --- Independent review, round 3 (ELG1-R3-001): a mark is held to the period as a cover is ------------------------


@pytest.mark.parametrize(
    ("until", "period", "outcome"),
    [
        (date(2026, 9, 28), NEXT_MONTH, OUTCOME_RUNS_OUT_BEFORE_START),
        (date(2026, 10, 15), NEXT_MONTH, OUTCOME_RUNS_OUT_IN_PERIOD),
        (date(2027, 6, 1), ev.Period(date(2026, 10, 1), None), OUTCOME_RUNS_OUT_IN_PERIOD),
        (None, ev.Period(date(2026, 10, 1), None), OUTCOME_NOT_APPLICABLE),
        (date(2027, 6, 1), NEXT_MONTH, OUTCOME_NOT_APPLICABLE),
    ],
    ids=["ends-before-start", "ends-in-period", "open-ended-period", "no-end", "covers-the-period"],
)
def test_a_mark_ending_before_or_during_the_job_warns(until, period, outcome) -> None:
    allowed = rule("INSURANCE", type_code="CRAWLER", not_applicable="ALLOWED")
    ending = mark("INSURANCE", until=until)
    decision = decide([allowed], [], [ending], members=crane_unit(CRAWLER, carrier=False), period=period)
    result = only(decision, "INSURANCE")
    assert (result.outcome_code, result.mark) == (outcome, ending)
    assert decision.overall_code == (OVERALL_ELIGIBLE if outcome == OUTCOME_NOT_APPLICABLE else OVERALL_WARNING)


def test_a_registration_mark_ending_before_the_job_starts_no_longer_exempts_from_the_transport_rules() -> None:
    # A transport registration that has run out, its registration now marked not applicable: the mark exempts from
    # fitness and a permit only while it stands for the job.
    crawler_rules = _road_rules() + [rule("REGISTRATION", type_code="CRAWLER", not_applicable="ALLOWED")]
    members = crane_unit(CRAWLER, carrier=False)
    ran_out = cert("REGISTRATION", start=date(2011, 9, 1), until=date(2026, 8, 31), registered_as="TRANSPORT")
    ends_first = decide(crawler_rules, [ran_out], [mark("REGISTRATION", until=date(2026, 9, 30))], members=members)
    assert {result.kind_code for result in ends_first.results} == {"REGISTRATION", "FITNESS", "PERMIT"}
    assert ends_first.overall_code == OVERALL_BLOCKED
    stands = decide(crawler_rules, [ran_out], [mark("REGISTRATION", until=date(2026, 12, 31))], members=members)
    assert {result.kind_code for result in stands.results} == {"REGISTRATION"}


# --- Independent review, round 4 (ELG1-R4-001): the transport question follows the site's registration rule ------


MAHARASHTRA = ev.Site("IN-MH", False)


def test_a_states_registration_rule_allowing_the_mark_exempts_there_and_only_there() -> None:
    # A transport registration that has run out, its registration marked not applicable. The baseline allows no mark
    # on a crawler's registration; Gujarat's rule does.
    rules = _road_rules() + [rule("REGISTRATION", type_code="CRAWLER", jurisdiction="IN-GJ", not_applicable="ALLOWED")]
    members = crane_unit(CRAWLER, carrier=False)
    ran_out = cert("REGISTRATION", start=date(2011, 9, 1), until=date(2026, 8, 31), registered_as="TRANSPORT")
    in_gujarat = decide(rules, [ran_out], [mark("REGISTRATION")], members=members, site=GUJARAT)
    assert {result.kind_code for result in in_gujarat.results} == {"REGISTRATION"}
    assert only(in_gujarat, "REGISTRATION").outcome_code == OUTCOME_NOT_APPLICABLE
    assert in_gujarat.overall_code == OVERALL_ELIGIBLE
    elsewhere = decide(rules, [ran_out], [mark("REGISTRATION")], members=members, site=MAHARASHTRA)
    assert {result.kind_code for result in elsewhere.results} == {"REGISTRATION", "FITNESS", "PERMIT"}
    assert elsewhere.overall_code == OVERALL_BLOCKED


def test_a_states_registration_rule_allowing_no_mark_brings_the_transport_rules_back_there() -> None:
    # A transport registration that has run out, its registration marked not applicable. The baseline allows the mark
    # on a crawler's registration; Gujarat's rule for every crane does not.
    rules = _road_rules() + [
        rule("REGISTRATION", type_code="CRAWLER", not_applicable="ALLOWED"),
        rule("REGISTRATION", jurisdiction="IN-GJ"),
    ]
    members = crane_unit(CRAWLER, carrier=False)
    ran_out = cert("REGISTRATION", start=date(2011, 9, 1), until=date(2026, 8, 31), registered_as="TRANSPORT")
    in_gujarat = decide(rules, [ran_out], [mark("REGISTRATION")], members=members, site=GUJARAT)
    assert {result.kind_code for result in in_gujarat.results} == {"REGISTRATION", "FITNESS", "PERMIT"}
    assert only(in_gujarat, "REGISTRATION").outcome_code == OUTCOME_RUN_OUT
    elsewhere = decide(rules, [ran_out], [mark("REGISTRATION")], members=members, site=MAHARASHTRA)
    assert {result.kind_code for result in elsewhere.results} == {"REGISTRATION"}
    assert elsewhere.overall_code == OVERALL_ELIGIBLE


def test_the_registration_rule_for_the_mark_is_the_one_in_effect_when_the_job_starts() -> None:
    # A transport registration that has run out, marked not applicable. Gujarat's rule allowing the mark ends before
    # the job starts; from then the baseline allows none.
    rules = _road_rules() + [
        rule("REGISTRATION", type_code="CRAWLER", jurisdiction="IN-GJ", not_applicable="ALLOWED", end=date(2026, 9, 30))
    ]
    decision = decide(rules, [cert("REGISTRATION", start=date(2011, 9, 1), until=date(2026, 8, 31), registered_as="TRANSPORT")], [mark("REGISTRATION")], members=crane_unit(CRAWLER, carrier=False))
    assert {result.kind_code for result in decision.results} == {"REGISTRATION", "FITNESS", "PERMIT"}


def test_a_non_transport_registration_starting_by_the_job_is_not_judged_as_a_transport_vehicle() -> None:
    # Nothing in force today; a non-transport registration from before the job starts. The registration is still
    # missing today, but fitness and a permit are not asked for.
    ahead = cert("REGISTRATION", start=date(2026, 9, 30), until=date(2031, 1, 1), registered_as="NON_TRANSPORT")
    decision = decide(_road_rules(), [ahead])
    assert {result.kind_code for result in decision.results} == {"REGISTRATION"}
    assert only(decision, "REGISTRATION").outcome_code == OUTCOME_MISSING
    # A transport one starting by the job asks for them, as before.
    transport = cert("REGISTRATION", start=date(2026, 9, 30), until=date(2031, 1, 1), registered_as="TRANSPORT")
    assert {result.kind_code for result in decide(_road_rules(), [transport]).results} == {"REGISTRATION", "FITNESS", "PERMIT"}


# --- Independent review, round 5 (ELG1-R5-001): a renewal takes over on its own start date ----------------------


@pytest.mark.parametrize(
    ("until", "copy", "ends_on", "outcome", "band"),
    [
        (date(2027, 9, 30), False, date(2026, 9, 30), OUTCOME_RUNS_OUT_BEFORE_START, BAND_WITHIN_15),
        (date(2026, 10, 5), True, date(2026, 10, 5), OUTCOME_RUNS_OUT_BEFORE_START, BAND_WITHIN_15),
        (date(2027, 9, 30), True, date(2027, 9, 30), OUTCOME_VALID, None),
    ],
    ids=["without-its-copy", "ending-sooner", "ending-later"],
)
def test_a_renewal_starting_before_the_current_one_ends_takes_over_on_its_start(until, copy, ends_on, outcome, band) -> None:
    # Insured to 31 December; a renewal from 1 October is recorded ahead. From 1 October the renewal is the one in
    # force, so the cover is the renewal's - none without its copy.
    insurance = rule("INSURANCE")
    current = cert("INSURANCE", start=date(2026, 1, 1), until=date(2026, 12, 31))
    renewal = cert("INSURANCE", start=date(2026, 10, 1), until=until, copy=copy)
    assert ev.cover([current, renewal], insurance, TODAY) == ev.Cover(current, None, ends_on)
    # The check for a job from 10 October, and Certificates due.
    result = only(decide([insurance], [current, renewal], period=ev.Period(date(2026, 10, 10), date(2026, 10, 31))), "INSURANCE")
    assert (result.outcome_code, result.cover_ends_on) == (outcome, ends_on)
    [due] = ev.baseline_results(crane_unit(carrier=False), evidence([insurance], [current, renewal]), today=TODAY)
    assert ev.due_band(due, TODAY) == band


def test_of_two_renewals_starting_on_one_day_the_one_recorded_last_takes_over() -> None:
    insurance = rule("INSURANCE")
    current = cert("INSURANCE", start=date(2026, 1, 1), until=date(2026, 12, 31))
    first = cert("INSURANCE", start=date(2026, 10, 1), until=date(2027, 9, 30))
    second = cert("INSURANCE", start=date(2026, 10, 1), until=date(2027, 9, 30), copy=False)
    assert ev.cover([current, second, first], insurance, TODAY).ends_on == date(2026, 9, 30)
    withdrawn = cert("INSURANCE", start=date(2026, 10, 1), until=date(2027, 9, 30), copy=False, withdrawn=True)
    assert ev.cover([current, first, withdrawn], insurance, TODAY).ends_on == date(2027, 9, 30)


def test_a_road_tax_without_end_is_replaced_on_the_renewals_start() -> None:
    # A one-time tax has no end; a later periodic receipt taking over ends the cover at its own end.
    tax = rule("ROAD_TAX")
    one_time = cert("ROAD_TAX", start=date(2020, 1, 1), until=None)
    periodic = cert("ROAD_TAX", start=date(2026, 11, 1), until=date(2027, 10, 31))
    assert ev.cover([one_time, periodic], tax, TODAY).ends_on == date(2027, 10, 31)
    assert ev.cover([one_time], tax, TODAY).ends_on is None


# --- Independent review, round 6 (ELG1-R6-001): every takeover counts, however many ---------------------------


def test_every_takeover_counts_however_many_are_recorded_ahead() -> None:
    # 101 renewals recorded ahead, one a day from 1 October; the last has no copy, so the cover ends the day before
    # it takes over - not at the hundredth's end.
    insurance = rule("INSURANCE")
    current = cert("INSURANCE", start=date(2026, 1, 1), until=date(2026, 12, 31))
    first = date(2026, 10, 1)
    renewals = [cert("INSURANCE", start=first + timedelta(days=n), until=date(2027, 12, 31), copy=n < 100) for n in range(101)]
    last_day = first + timedelta(days=99)
    assert ev.cover([current, *renewals], insurance, TODAY).ends_on == last_day
    job = ev.Period(last_day + timedelta(days=5), last_day + timedelta(days=20))
    result = only(decide([insurance], [current, *renewals], period=job), "INSURANCE")
    assert (result.outcome_code, result.cover_ends_on) == (OUTCOME_RUNS_OUT_BEFORE_START, last_day)
    [due] = ev.baseline_results(crane_unit(carrier=False), evidence([insurance], [current, *renewals]), today=TODAY)
    assert due.cover_ends_on == last_day


# --- Independent review, round 7 (ELG1-R7-001): the last day a date can hold -------------------------------------


def test_a_certificate_valid_until_the_last_day_a_date_can_hold_is_taken_over_without_overflow() -> None:
    insurance = rule("INSURANCE")
    current = cert("INSURANCE", start=date(2026, 1, 1), until=date.max)
    renewal = cert("INSURANCE", start=date(2026, 10, 1), until=date(2027, 9, 30))
    assert ev.cover([current, renewal], insurance, TODAY).ends_on == date(2027, 9, 30)
    assert ev.cover([current], insurance, TODAY).ends_on == date.max


# --- Independent review, round 7 (ELG1-R7-002): a registration in force wins over its "not applicable" mark -------
# The owner's decision, 28 September 2026: the records disagree, and the cautious reading is the registration's.


def _crawler_rules() -> list[ev.Rule]:
    return _road_rules() + [rule("REGISTRATION", type_code="CRAWLER", not_applicable="ALLOWED")]


def test_a_transport_registration_in_force_wins_over_the_registrations_mark() -> None:
    registration = cert("REGISTRATION", registered_as="TRANSPORT")
    marked = mark("REGISTRATION")
    members = crane_unit(CRAWLER, carrier=False)
    decision = decide(_crawler_rules(), [registration], [marked], members=members)
    assert {result.kind_code for result in decision.results} == {"REGISTRATION", "FITNESS", "PERMIT"}
    row = only(decision, "REGISTRATION")
    assert (row.outcome_code, row.certificate, row.mark) == (OUTCOME_VALID, registration, None)
    assert only(decision, "FITNESS").outcome_code == OUTCOME_MISSING and decision.overall_code == OVERALL_BLOCKED
    # The machine's page and Certificates due read the same.
    baseline = {result.kind_code: result for result in ev.baseline_results(members, evidence(_crawler_rules(), [registration], [marked]), today=TODAY)}
    assert baseline["REGISTRATION"].certificate == registration and baseline["REGISTRATION"].mark is None
    assert ev.due_band(baseline["FITNESS"], TODAY) == BAND_MISSING


def test_a_non_transport_registration_in_force_is_shown_rather_than_the_mark() -> None:
    registration = cert("REGISTRATION", registered_as="NON_TRANSPORT")
    decision = decide(_crawler_rules(), [registration], [mark("REGISTRATION")], members=crane_unit(CRAWLER, carrier=False))
    assert {result.kind_code for result in decision.results} == {"REGISTRATION"}
    assert (only(decision, "REGISTRATION").certificate, only(decision, "REGISTRATION").mark) == (registration, None)


def test_once_the_registration_has_run_out_the_mark_counts() -> None:
    ran_out = cert("REGISTRATION", start=date(2011, 9, 1), until=date(2026, 8, 31), registered_as="TRANSPORT")
    marked = mark("REGISTRATION")
    decision = decide(_crawler_rules(), [ran_out], [marked], members=crane_unit(CRAWLER, carrier=False))
    assert {result.kind_code for result in decision.results} == {"REGISTRATION"}
    assert (only(decision, "REGISTRATION").outcome_code, only(decision, "REGISTRATION").mark) == (OUTCOME_NOT_APPLICABLE, marked)
    assert decision.overall_code == OVERALL_ELIGIBLE


def test_a_registration_that_has_run_out_still_says_what_the_machine_is() -> None:
    # Run out, a non-transport registration calls for no fitness or permit; a transport one still does - the
    # registration recorded says what the machine is (the owner's rule, 1 October 2026) - so their reminders carry on
    # while the registration is renewed. Either is itself run out.
    non_transport = cert("REGISTRATION", start=date(2011, 9, 1), until=date(2026, 8, 31), registered_as="NON_TRANSPORT")
    plain = decide(_road_rules(), [non_transport])
    assert {result.kind_code for result in plain.results} == {"REGISTRATION"}
    assert only(plain, "REGISTRATION").outcome_code == OUTCOME_RUN_OUT
    transport = decide(_road_rules(), [cert("REGISTRATION", start=date(2011, 9, 1), until=date(2026, 8, 31), registered_as="TRANSPORT")])
    assert {result.kind_code for result in transport.results} == {"REGISTRATION", "FITNESS", "PERMIT"}
    assert only(transport, "REGISTRATION").outcome_code == OUTCOME_RUN_OUT


# --- Independent review, round 8 (ELG1-R8-001): a mark may run as long as any rule allows ---------------------------


def test_a_mark_is_recorded_under_the_rule_letting_it_run_longest() -> None:
    baseline = rule("POLLUTION_UNDER_CONTROL", not_applicable="ALLOWED", max_months=12)
    gujarat_open = rule("POLLUTION_UNDER_CONTROL", jurisdiction="IN-GJ", not_applicable="ALLOWED")
    choose = lambda rules: ev.rule_allowing_mark(rules, kind_code="POLLUTION_UNDER_CONTROL", asset=CRANE, today=TODAY)
    # A state's rule with no limit lets it run open-ended, though all of India's allows 12 months.
    assert choose([baseline, gujarat_open]) == gujarat_open and ev.mark_limit(gujarat_open, TODAY) is None
    # Of limits, the longest - whatever the order of the states' codes.
    andhra_24 = rule("POLLUTION_UNDER_CONTROL", jurisdiction="IN-AP", not_applicable="ALLOWED", max_months=24)
    gujarat_18 = rule("POLLUTION_UNDER_CONTROL", jurisdiction="IN-GJ", not_applicable="ALLOWED", max_months=18)
    assert choose([baseline, gujarat_18, andhra_24]) == andhra_24
    andhra_18 = rule("POLLUTION_UNDER_CONTROL", jurisdiction="IN-AP", not_applicable="ALLOWED", max_months=18)
    gujarat_24 = rule("POLLUTION_UNDER_CONTROL", jurisdiction="IN-GJ", not_applicable="ALLOWED", max_months=24)
    assert choose([baseline, andhra_18, gujarat_24]) == gujarat_24
    # Of equals, all of India's; a state allowing none adds nothing.
    gujarat_12 = rule("POLLUTION_UNDER_CONTROL", jurisdiction="IN-GJ", not_applicable="ALLOWED", max_months=12)
    assert choose([gujarat_12, baseline]) == baseline
    assert choose([baseline, rule("POLLUTION_UNDER_CONTROL", jurisdiction="IN-GJ")]) == baseline
    # Where all of India allows none, a state's rule allowing one still lets it be recorded.
    assert choose([rule("POLLUTION_UNDER_CONTROL"), gujarat_18]) == gujarat_18
