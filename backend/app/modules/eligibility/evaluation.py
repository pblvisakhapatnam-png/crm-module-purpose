"""The eligibility decision, pure: which rule applies, how long a certificate covers, and the answer (ELG-1).

docs/agent/slices/elg-1-machine-eligibility.md, sections 5.3, 6 and 7. No database and no clock: the service
reads the records and today's date in Asia/Kolkata and hands them in, as the Equipment Reference's
`plum_report.py` is handed a report. Everything here is a function of its arguments, so each rule of the
design is tested on its own.

In short:

- **A unit.** A machine is judged with its fitted parts; a piece of kit alone. Each asset of the unit is
  judged by the rules for its own class and type, and a rule is met by a certificate on that asset or on a
  part fitted to it - so a crane's road papers count when recorded on its carrier.
- **Choosing a rule.** For a kind and a day: the site's jurisdiction's rule if one is in effect, otherwise
  the baseline; within that, a rule for the asset's type before one for its class. At a central-government
  site the labour-safety rules (the examinations) come from `IN`; road papers always from the site's state.
  No rule, or `NOT_REQUIRED`, means not required.
- **Transport.** A rule for transport vehicles only applies when a registration in force on any asset of the
  unit - today or on the day the job starts - says transport; and, the cautious reading, when no registration
  is in force at all, unless the registration itself is marked "not applicable" (a machine that is not a motor
  vehicle).
- **Cover.** Each asset's certificates of a kind (and, for a permit, of a place) form their own sequence: the
  certificate in force on a day is the one not withdrawn with the latest "valid from" on or before it. It
  covers until the earlier of its "valid until" and, for an examination, its "issued on" plus the rule's
  interval. A renewal in force by the day after the cover ends continues it. A certificate counts only with
  its copy (Q5). Of the sequences on the assets that may meet a rule, the one covering longest counts: a newer
  record on the crane does not hide a valid one on its carrier.
- **"Not applicable".** A mark in force counts only where the rule chosen allows one, within the rule's
  limit on how long. Its end is held to the period as a certificate's cover is: a mark ending before the job
  starts, or during it, warns. A registration's mark exempts a machine from the transport rules only if it
  still stands on the day the job starts.
- **The answer.** Any `BLOCK` gives `BLOCKED`; else any `OVERRIDE` gives `OVERRIDE_REQUIRED`; else any warning
  gives `WARNING`; else `ELIGIBLE`. Valid until the earliest required cover or mark ends.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable

from app.modules.eligibility.contract import (
    APPLIES_ALWAYS,
    APPLIES_TRANSPORT_ONLY,
    BAND_COPY_MISSING,
    BAND_DAYS,
    BAND_MISSING,
    BAND_RUN_OUT,
    EFFECT_BLOCK,
    EFFECT_NONE,
    EFFECT_OVERRIDE,
    EFFECT_WARNING,
    JURISDICTION_CENTRAL,
    KIND_PERMIT,
    KIND_REGISTRATION,
    LAPSE_BLOCK,
    LAPSE_NOT_REQUIRED,
    LAPSE_OVERRIDE,
    NOT_APPLICABLE_ALLOWED,
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
    REGISTERED_AS_TRANSPORT,
    RUNS_OUT_SOON_DAYS,
)

@dataclass(frozen=True)
class Kind:
    kind_code: str
    kind_label: str
    end_date_optional: bool
    valid_in_required: bool
    is_examination: bool
    states_registration: bool
    display_order: int


@dataclass(frozen=True)
class Rule:
    rule_id: int
    rule_public_id: str
    kind_code: str
    class_code: str
    type_code: str | None
    applies_when_code: str
    jurisdiction_code: str | None
    effective_from: date
    effective_to: date | None
    renew_every_months: int | None
    basis_code: str
    lapse_code: str
    not_applicable_code: str
    not_applicable_max_months: int | None

    def in_effect_on(self, day: date) -> bool:
        return self.effective_from <= day and (self.effective_to is None or day <= self.effective_to)

    @property
    def allows_not_applicable(self) -> bool:
        return self.lapse_code != LAPSE_NOT_REQUIRED and self.not_applicable_code == NOT_APPLICABLE_ALLOWED


@dataclass(frozen=True)
class Certificate:
    certificate_id: int
    certificate_public_id: str
    asset_public_id: str
    kind_code: str
    issued_on: date
    valid_from: date
    valid_until: date | None
    valid_in_code: str | None
    registered_as_code: str | None
    withdrawn: bool
    has_copy: bool


@dataclass(frozen=True)
class Mark:
    mark_id: int
    mark_public_id: str
    asset_public_id: str
    kind_code: str
    until_date: date | None
    recorded_on: date
    withdrawn: bool
    # The day it was withdrawn, in Asia/Kolkata. The decision never reads it; a reminder dates a certificate needed
    # again from it (ELG-2, section 5.2).
    withdrawn_on: date | None = None


@dataclass(frozen=True)
class Asset:
    asset_public_id: str
    class_code: str
    type_code: str | None
    active: bool


@dataclass(frozen=True)
class Member:
    """One asset of a unit, with the assets whose certificates meet its rules: itself and the parts fitted
    below it."""

    asset: Asset
    subtree: tuple[str, ...]


@dataclass(frozen=True)
class Site:
    state_code: str
    central_government_site: bool


@dataclass(frozen=True)
class Period:
    starts_on: date
    # None: open-ended.
    ends_on: date | None


@dataclass(frozen=True)
class Evidence:
    kinds: dict[str, Kind]
    rules: tuple[Rule, ...]
    certificates: tuple[Certificate, ...]
    marks: tuple[Mark, ...]


@dataclass(frozen=True)
class Result:
    """What was found for one certificate required of one asset, or the asset's own check (kind None)."""

    asset_public_id: str
    kind_code: str | None
    rule: Rule | None
    certificate: Certificate | None
    mark: Mark | None
    outcome_code: str
    effect_code: str
    cover_ends_on: date | None


@dataclass(frozen=True)
class Decision:
    overall_code: str
    valid_until: date | None
    results: tuple[Result, ...]


# --- Dates ----------------------------------------------------------------------------------------------


def add_months(day: date, months: int) -> date:
    """The same day `months` later, or the month's last day where it has no such day (31 January + 1 = 28 or
    29 February)."""
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def months_after(day: date, months: int) -> date:
    """The last day of a span of `months` from `day`: the day before the same date that many months later. An
    examination of 1 October 2025 under a 12-month rule counts until 30 September 2026 - the cautious reading
    of "every 12 months"."""
    return add_months(day, months) - timedelta(days=1)


# --- Choosing the rule (section 5.3) --------------------------------------------------------------------


def rule_jurisdiction(kind: Kind, site: Site | None) -> str | None:
    """Whose rules apply to this kind at this site: the central government's at its own sites for labour safety
    (the examinations), otherwise the state's. None where no site is given: the baseline only."""
    if site is None:
        return None
    if kind.is_examination and site.central_government_site:
        return JURISDICTION_CENTRAL
    return site.state_code


def choose_rule(
    rules: Iterable[Rule], *, kind_code: str, asset: Asset, jurisdiction_code: str | None, day: date, transport: bool
) -> Rule | None:
    """The rule for one kind of one asset on a day: the jurisdiction's before the baseline, then a rule for the
    asset's type before one for its class, then one for transport vehicles before one for all. A rule for an
    unknown type never applies, so an asset whose type is not known is judged by its class's rule."""
    candidates = [
        rule
        for rule in rules
        if rule.kind_code == kind_code
        and rule.class_code == asset.class_code
        and (rule.type_code is None or rule.type_code == asset.type_code)
        and rule.in_effect_on(day)
        and (rule.applies_when_code == APPLIES_ALWAYS or transport)
        and (rule.jurisdiction_code is None or (jurisdiction_code is not None and rule.jurisdiction_code == jurisdiction_code))
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda rule: (
            rule.jurisdiction_code is None,
            rule.type_code is None,
            rule.applies_when_code != APPLIES_TRANSPORT_ONLY,
        ),
    )


def kinds_for_class(rules: Iterable[Rule], class_code: str) -> set[str]:
    return {rule.kind_code for rule in rules if rule.class_code == class_code}


# --- Certificates and marks -----------------------------------------------------------------------------


def in_force(certificates: Iterable[Certificate], day: date) -> Certificate | None:
    """The certificate in force on a day: not withdrawn, with the latest "valid from" on or before it; of two
    from the same day, the one recorded later. A renewal recorded ahead of time takes over on its start date;
    withdrawing a wrong certificate brings back the one before."""
    current = [item for item in certificates if not item.withdrawn and item.valid_from <= day]
    return max(current, key=lambda item: (item.valid_from, item.certificate_id)) if current else None


def cover_end(certificate: Certificate, rule: Rule | None) -> date | None:
    """The last day one certificate covers: the earlier of its "valid until" and, for an examination, its
    "issued on" plus the rule's interval. None: it covers without end (a one-time road tax)."""
    ends = [certificate.valid_until] if certificate.valid_until is not None else []
    if rule is not None and rule.renew_every_months:
        ends.append(months_after(certificate.issued_on, rule.renew_every_months))
    return min(ends) if ends else None


@dataclass(frozen=True)
class Cover:
    # The certificate in force today, or None.
    certificate: Certificate | None
    # MISSING, COPY_MISSING or None (a certificate with its copy is in force).
    gap_code: str | None
    ends_on: date | None


def cover(certificates: list[Certificate], rule: Rule, today: date) -> Cover:
    """How long the certificates of one kind cover from today, renewals included. Day by day the certificate that
    counts is the one in force (`in_force`), so a renewal takes over on its own start date - also one starting
    before the certificate it replaces ends (independent review, round 5, ELG1-R5-001). The cover runs through a
    takeover only when the certificate taking over has its copy and covers its start date, and ends where one
    runs out before the next takes over."""
    current = in_force(certificates, today)
    if current is None:
        return Cover(None, OUTCOME_MISSING, None)
    if not current.has_copy:
        return Cover(current, OUTCOME_COPY_MISSING, None)
    # The takeovers after today: on each later start date, of those starting then, the one recorded last.
    takeovers: dict[date, Certificate] = {}
    for item in certificates:
        if not item.withdrawn and item.valid_from > today:
            held = takeovers.get(item.valid_from)
            if held is None or item.certificate_id > held.certificate_id:
                takeovers[item.valid_from] = item
    ends_on = cover_end(current, rule)
    # Every takeover counts, however many are recorded ahead (independent review, round 6, ELG1-R6-001).
    for starts_on in sorted(takeovers):
        # Compared without adding to `ends_on`, which may be the last day a date can hold (ELG1-R7-001).
        if ends_on is not None and ends_on < starts_on - timedelta(days=1):
            break
        following = takeovers[starts_on]
        following_end = cover_end(following, rule)
        if not following.has_copy or (following_end is not None and following_end < starts_on):
            return Cover(current, None, starts_on - timedelta(days=1))
        ends_on = following_end
    return Cover(current, None, ends_on)


def current_registration(registrations: Iterable[Certificate], day: date) -> Certificate | None:
    """The registration in force on a day, if it has not run out by then. One that has run out or been withdrawn no
    longer decides whether the unit is a transport vehicle, nor stands in the way of a "not applicable" mark."""
    current = in_force(registrations, day)
    if current is None or (current.valid_until is not None and current.valid_until < day):
        return None
    return current


def registrations_in_force(
    certificates: Iterable[Certificate], assets: Iterable[str], days: Iterable[date]
) -> tuple[list[Certificate], list[Certificate]]:
    """The registration in force on each of these assets on each of the days - the latest started, not withdrawn -
    split into those still standing that day and those run out by it."""
    wanted = set(assets)
    by_asset: dict[str, list[Certificate]] = {}
    for item in certificates:
        if item.kind_code == KIND_REGISTRATION and item.asset_public_id in wanted:
            by_asset.setdefault(item.asset_public_id, []).append(item)
    standing: list[Certificate] = []
    ran_out: list[Certificate] = []
    for registrations in by_asset.values():
        for day in days:
            current = in_force(registrations, day)
            if current is not None:
                (standing if current.valid_until is None or current.valid_until >= day else ran_out).append(current)
    return standing, ran_out


def says_transport(registrations: Iterable[Certificate]) -> list[Certificate]:
    """Those of the registrations that say transport."""
    return [item for item in registrations if item.registered_as_code == REGISTERED_AS_TRANSPORT]


def registration_stands(certificates: Iterable[Certificate], days: Iterable[date]) -> bool:
    """Whether a registration of any of these assets is in force, and not run out, on any of the days."""
    by_asset: dict[str, list[Certificate]] = {}
    for item in certificates:
        if item.kind_code == KIND_REGISTRATION:
            by_asset.setdefault(item.asset_public_id, []).append(item)
    return any(current_registration(items, day) is not None for items in by_asset.values() for day in days)


def allows_mark(rule: Rule, mark: Mark) -> bool:
    """Whether the rule lets this "not applicable" mark stand: it allows marks, and the mark keeps within its limit
    on how long."""
    return rule.allows_not_applicable and (
        rule.not_applicable_max_months is None
        or (mark.until_date is not None and mark.until_date <= months_after(mark.recorded_on, rule.not_applicable_max_months))
    )


def counted_mark(marks: Iterable[Mark], rule: Rule, today: date) -> Mark | None:
    """A "not applicable" mark in force today that the rule allows, within its limit on how long; of several, the
    one that runs longest. A mark under the baseline does not count where a state's rule allows none."""
    if not rule.allows_not_applicable:
        return None
    counted = [
        mark
        for mark in marks
        if not mark.withdrawn
        and mark.recorded_on <= today
        and (mark.until_date is None or mark.until_date >= today)
        and allows_mark(rule, mark)
    ]
    if not counted:
        return None
    return max(counted, key=lambda mark: (mark.until_date is None, mark.until_date or date.min))


# --- Judging one requirement ----------------------------------------------------------------------------


def _lapse_effect(rule: Rule) -> str:
    if rule.lapse_code == LAPSE_BLOCK:
        return EFFECT_BLOCK
    if rule.lapse_code == LAPSE_OVERRIDE:
        return EFFECT_OVERRIDE
    return EFFECT_WARNING


def period_outcome(ends_on: date | None, today: date, period: Period | None) -> tuple[str, str]:
    """Where a cover - or a "not applicable" mark - ending on `ends_on` leaves the period: run out before today
    (the rule's lapse applies; the caller decides), before the job starts, during it (an open-ended job has no
    end, so any end is during it), within 15 days, or through it. None: it has no end."""
    if ends_on is not None and ends_on < today:
        return OUTCOME_RUN_OUT, EFFECT_BLOCK
    if ends_on is not None and period is not None and ends_on < period.starts_on:
        return OUTCOME_RUNS_OUT_BEFORE_START, EFFECT_WARNING
    if ends_on is not None and period is not None and (period.ends_on is None or ends_on < period.ends_on):
        return OUTCOME_RUNS_OUT_IN_PERIOD, EFFECT_WARNING
    if ends_on is not None and ends_on <= today + timedelta(days=RUNS_OUT_SOON_DAYS):
        return OUTCOME_RUNS_OUT_SOON, EFFECT_WARNING
    return OUTCOME_VALID, EFFECT_NONE


def judge(
    *,
    asset_public_id: str,
    rule: Rule,
    certificates: list[Certificate],
    marks: list[Mark],
    today: date,
    period: Period | None,
    permit_places: tuple[str, ...] | None,
) -> Result:
    """One certificate required of one asset. `certificates` and `marks` are those of the kind on the assets that
    may meet it. A permit counts only where it is valid (`permit_places`, None: anywhere); of several places,
    the one covering longest. Without a period, only the lapses and the 15-day warning apply: the renewal list
    and a machine's page."""
    mark = counted_mark(marks, rule, today)
    rule_day = max(today, period.starts_on) if period is not None else today
    if mark is not None and rule.kind_code == KIND_REGISTRATION and registration_stands(certificates, (today, rule_day)):
        # A registration in force wins over a mark saying none applies: the records disagree, and the cautious reading
        # is the registration's (owner, 28 September 2026; independent review, round 7, ELG1-R7-002).
        mark = None
    if mark is not None:
        # A counted mark has not ended today; it is held to the period as a cover is (independent review, round 3,
        # ELG1-R3-001): one ending before the job starts, or during it, warns, and the result names the mark.
        outcome, effect = period_outcome(mark.until_date, today, period)
        if outcome == OUTCOME_VALID:
            outcome, effect = OUTCOME_NOT_APPLICABLE, EFFECT_NONE
        return Result(asset_public_id, rule.kind_code, rule, None, mark, outcome, effect, mark.until_date)

    # One sequence per asset, and per place for a permit (several permits may be in force for one vehicle).
    groups: dict[tuple[str, str | None], list[Certificate]] = {}
    for item in certificates:
        if rule.kind_code == KIND_PERMIT and permit_places is not None and item.valid_in_code not in permit_places:
            continue
        groups.setdefault((item.asset_public_id, item.valid_in_code if rule.kind_code == KIND_PERMIT else None), []).append(item)
    covers = [cover(items, rule, today) for items in groups.values()]
    best = max(
        covers,
        key=lambda item: (item.gap_code is None, item.ends_on is None, item.ends_on or date.min, item.gap_code != OUTCOME_MISSING),
        default=Cover(None, OUTCOME_MISSING, None),
    )

    if best.gap_code is not None:
        return Result(asset_public_id, rule.kind_code, rule, best.certificate, None, best.gap_code, _lapse_effect(rule), None)
    ends_on = best.ends_on
    outcome, effect = period_outcome(ends_on, today, period)
    if outcome == OUTCOME_RUN_OUT:
        effect = _lapse_effect(rule)
    return Result(asset_public_id, rule.kind_code, rule, best.certificate, None, outcome, effect, ends_on)


# --- A unit ---------------------------------------------------------------------------------------------


def _of(items: Iterable, kind_code: str, assets: tuple[str, ...]) -> list:
    return [item for item in items if item.kind_code == kind_code and item.asset_public_id in assets]


def is_transport(members: tuple[Member, ...], evidence: Evidence, *, site: Site | None, today: date, rule_day: date) -> bool:
    """Whether the unit is to be judged as a transport vehicle: a registration recorded on one of its assets says so.

    The owner, 1 October 2026 (ELG-2's screen check): with no registration recorded, a machine is not a transport
    vehicle - fitness and a permit are needed once a registration saying transport is entered. The registration is
    itself required, and a missing one is reminded and blocks on its own, so nothing is allowed that should not be.
    This replaces ELG-1's cautious reading, which asked for fitness and a permit whenever no registration stood.

    - A registration standing today or on the rule day (a registration changed ahead of the job) decides: transport
      if one says so, otherwise not. A "not applicable" mark does not change that, as the registration wins (owner,
      28 September 2026).
    - With none standing, a transport registration that has run out still says what the machine is - its fitness and
      permit go on being reminded while its registration is renewed - unless the registration is now marked "not
      applicable" (taken off the road) under the registration rule this check judges it by, for this site on the
      rule day, and the mark still stands when the job starts (ELG-1's independent review, rounds 3, 4 and 7).
    - With none recorded, or the last one saying non-transport, it is not."""
    root = members[0]
    standing, ran_out = registrations_in_force(evidence.certificates, root.subtree, (today, rule_day))
    if standing:
        return bool(says_transport(standing))
    if not says_transport(ran_out):
        return False
    # The same rule requirements() chooses for the registration: a registration rule always applies, whether or not
    # the unit is a transport vehicle, so choosing it does not depend on the answer being worked out here.
    rule = choose_rule(
        evidence.rules,
        kind_code=KIND_REGISTRATION,
        asset=root.asset,
        jurisdiction_code=rule_jurisdiction(evidence.kinds[KIND_REGISTRATION], site),
        day=rule_day,
        transport=False,
    )
    if rule is None or rule.lapse_code == LAPSE_NOT_REQUIRED:
        return False
    mark = counted_mark(_of(evidence.marks, KIND_REGISTRATION, root.subtree), rule, today)
    return mark is None or (mark.until_date is not None and mark.until_date < rule_day)


def requirements(
    member: Member,
    evidence: Evidence,
    *,
    site: Site | None,
    rule_day: date,
    transport: bool,
) -> list[Rule]:
    """The rules one asset must meet: one per kind, as chosen, leaving out kinds with no rule or not required."""
    chosen: list[Rule] = []
    kinds = sorted(kinds_for_class(evidence.rules, member.asset.class_code), key=lambda code: evidence.kinds[code].display_order)
    for kind_code in kinds:
        rule = choose_rule(
            evidence.rules,
            kind_code=kind_code,
            asset=member.asset,
            jurisdiction_code=rule_jurisdiction(evidence.kinds[kind_code], site),
            day=rule_day,
            transport=transport,
        )
        if rule is not None and rule.lapse_code != LAPSE_NOT_REQUIRED:
            chosen.append(rule)
    return chosen


def judge_member(
    member: Member,
    evidence: Evidence,
    *,
    site: Site | None,
    period: Period | None,
    today: date,
    transport: bool,
) -> list[Result]:
    rule_day = max(today, period.starts_on) if period is not None else today
    permit_places = (site.state_code, JURISDICTION_CENTRAL) if site is not None else None
    return [
        judge(
            asset_public_id=member.asset.asset_public_id,
            rule=rule,
            certificates=_of(evidence.certificates, rule.kind_code, member.subtree),
            marks=_of(evidence.marks, rule.kind_code, member.subtree),
            today=today,
            period=period,
            permit_places=permit_places,
        )
        for rule in requirements(member, evidence, site=site, rule_day=rule_day, transport=transport)
    ]


def overall(results: Iterable[Result]) -> str:
    effects = {result.effect_code for result in results}
    if EFFECT_BLOCK in effects:
        return OVERALL_BLOCKED
    if EFFECT_OVERRIDE in effects:
        return OVERALL_OVERRIDE_REQUIRED
    if EFFECT_WARNING in effects:
        return OVERALL_WARNING
    return OVERALL_ELIGIBLE


def evaluate(members: tuple[Member, ...], evidence: Evidence, *, site: Site, period: Period, today: date) -> Decision:
    """May this unit work at this site over this period? `members` starts with the machine or piece asked about,
    followed by the parts fitted below it. A retired asset is blocked (RMR-001); every certificate is judged
    all the same, so the answer says everything that stands in the way."""
    root = members[0]
    results: list[Result] = []
    if not root.asset.active:
        results.append(Result(root.asset.asset_public_id, None, None, None, None, OUTCOME_RETIRED, EFFECT_BLOCK, None))
    transport = is_transport(members, evidence, site=site, today=today, rule_day=max(today, period.starts_on))
    for member in members:
        results.extend(judge_member(member, evidence, site=site, period=period, today=today, transport=transport))
    answer = overall(results)
    ends = [result.cover_ends_on for result in results if result.cover_ends_on is not None]
    valid_until = None if answer == OVERALL_BLOCKED or not ends else min(ends)
    return Decision(answer, valid_until, tuple(results))


def baseline_results(members: tuple[Member, ...], evidence: Evidence, *, today: date) -> list[Result]:
    """What every member of a unit needs today by the baseline rules, and how it stands: the renewal list and a
    machine's page. Renewal is about the machine, not a site; a state's shorter interval shows when the machine
    is checked for a site there."""
    transport = is_transport(members, evidence, site=None, today=today, rule_day=today)
    results: list[Result] = []
    for member in members:
        results.extend(judge_member(member, evidence, site=None, period=None, today=today, transport=transport))
    return results


def due_band(result: Result, today: date) -> str | None:
    """Where one result stands on Certificates due: missing, copy missing, run out, or running out - a
    certificate's cover or a mark's end - within 15, 30 or 60 days. None: nothing due within 60 days."""
    if result.outcome_code == OUTCOME_MISSING:
        return BAND_MISSING
    if result.outcome_code == OUTCOME_COPY_MISSING:
        return BAND_COPY_MISSING
    if result.outcome_code == OUTCOME_RUN_OUT:
        return BAND_RUN_OUT
    if result.cover_ends_on is None:
        return None
    for band, days in BAND_DAYS:
        if result.cover_ends_on <= today + timedelta(days=days):
            return band
    return None


# --- What may be recorded -------------------------------------------------------------------------------


def recordable_kinds(rules: Iterable[Rule], *, class_code: str, type_code: str | None, fits_class_codes: Iterable[str]) -> set[str]:
    """The kinds any rule could require of an asset: its own class's and type's, and - for a fitted part - those
    of the classes it is fitted to, since a crane's road papers are often recorded on its carrier. Rules of any
    date and jurisdiction count; a rule saying a kind is not required does not."""
    parents = set(fits_class_codes)
    return {
        rule.kind_code
        for rule in rules
        if rule.lapse_code != LAPSE_NOT_REQUIRED
        and (
            (rule.class_code == class_code and (rule.type_code is None or rule.type_code == type_code))
            or rule.class_code in parents
        )
    }


def rules_allowing_mark(rules: Iterable[Rule], *, kind_code: str, asset: Asset, today: date) -> list[Rule]:
    """Every rule in force today, as a check would choose it - all of India's, then each jurisdiction's own, by
    code - that allows marking this kind "not applicable" for this asset. Empty: nobody may mark it (the law is
    clear)."""
    rules = tuple(rules)
    allowing: list[Rule] = []
    baseline = choose_rule(rules, kind_code=kind_code, asset=asset, jurisdiction_code=None, day=today, transport=True)
    if baseline is not None and baseline.allows_not_applicable:
        allowing.append(baseline)
    for jurisdiction_code in sorted({rule.jurisdiction_code for rule in rules if rule.jurisdiction_code is not None}):
        rule = choose_rule(rules, kind_code=kind_code, asset=asset, jurisdiction_code=jurisdiction_code, day=today, transport=True)
        if rule is not None and rule.jurisdiction_code is not None and rule.allows_not_applicable:
            allowing.append(rule)
    return allowing


def rule_allowing_mark(rules: Iterable[Rule], *, kind_code: str, asset: Asset, today: date) -> Rule | None:
    """The rule a mark is recorded under, and whose limit the form offers: of those allowing one, the one letting it
    run longest - no limit, else the longest; of equals, all of India's, then by jurisdiction code. A mark any of
    them allows can so be recorded, and counts at each site whose own rule allows it (independent review, round 8,
    ELG1-R8-001). None: nobody may mark it (the law is clear)."""
    allowing = rules_allowing_mark(rules, kind_code=kind_code, asset=asset, today=today)
    if not allowing:
        return None
    # max() keeps the first of equals, and the list comes all of India's first, then by jurisdiction code.
    return max(allowing, key=lambda rule: (rule.not_applicable_max_months is None, rule.not_applicable_max_months or 0))


def mark_limit(rule: Rule, today: date) -> date | None:
    """The latest end a mark recorded today may have under the rule; None where the rule sets no limit."""
    return months_after(today, rule.not_applicable_max_months) if rule.not_applicable_max_months else None


def overlaps(rule: Rule, other: Rule) -> bool:
    """Whether two rules for the same kind, class, type, "applies when" and jurisdiction are in effect on a
    common day - which the database's exclusion constraint also refuses."""
    same_key = (
        rule.kind_code == other.kind_code
        and rule.class_code == other.class_code
        and rule.type_code == other.type_code
        and rule.applies_when_code == other.applies_when_code
        and rule.jurisdiction_code == other.jurisdiction_code
    )
    if not same_key:
        return False
    rule_end = rule.effective_to or date.max
    other_end = other.effective_to or date.max
    return rule.effective_from <= other_end and other.effective_from <= rule_end
