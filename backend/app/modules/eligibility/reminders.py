"""Certificate reminders and escalation, pure (ELG-2).

docs/agent/slices/elg-2-certificate-reminders.md, section 5. No database and no clock, as `evaluation.py`: the
service hands in the results ELG-1's evaluation gave, the evidence, today and the settings, and gets back each
reminder's date, its reminder days and the steps of its path that have reached their audience.

In short:

- **A date and a reason.** A cover that runs out - also one a renewal without its copy cuts short - or a "not
  applicable" mark that ends, is dated by its last day. A certificate never recorded, or in force without its copy,
  is dated by the day it became needed: the machine added, the rule requiring it in effect, the registration saying
  transport, a mark that stood for it ending or withdrawn, the cover before it ending. The latest wins; on a tie,
  the one that is not "not yet recorded".
- **Reminder days.** A schedule is bands of "from N days before the date, every M days" (negative N: after). The
  reminder days are those, from the day the reminder began - the asset added, the allocation or kit line
  recorded - and that day too when it falls inside the schedule's reach: flagged at once.
- **The path.** Each step reaches its audience from the first reminder day, or from N days before the date if
  later. Nobody drops off.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Iterator

from app.modules.eligibility import evaluation
from app.modules.eligibility.contract import (
    APPLIES_TRANSPORT_ONLY,
    CHANNEL_CODES,
    LAPSE_NOT_REQUIRED,
    MAX_BANDS,
    MAX_REMINDER_DAYS,
    MAX_STEPS,
    NOT_YET_RECORDED_REASONS,
    OUTCOME_COPY_MISSING,
    OUTCOME_MISSING,
    OUTCOME_RUN_OUT,
    OUTCOME_RUNS_OUT_BEFORE_START,
    OUTCOME_RUNS_OUT_IN_PERIOD,
    REASON_ADDED,
    REASON_COPY_MISSING,
    REASON_MARK_ENDS,
    REASON_MARK_WITHDRAWN,
    REASON_RULE,
    REASON_RUNS_OUT,
    REASON_TRANSPORT,
    REMINDER_BEFORE_JOB,
    REMINDER_DURING_JOB,
    REMINDER_NOT_YET_RECORDED,
    REMINDER_RUNNING_OUT,
    STEP_FROM_DAYS_BEFORE,
    STEP_FROM_FIRST_REMINDER,
)

# Lower than any days-before a reminder can reach: the search for the first reminder day has no "today" bound.
_FAR_AFTER = -10**7


def _shift(day: date, days: int) -> date:
    """`day` moved by `days`, held at the first or last day a date can be: a certificate may be dated 1 January of
    year 1 or 31 December 9999, and the API stores both (independent review, ELG2-R1-005)."""
    try:
        return day + timedelta(days=days)
    except OverflowError:
        return date.max if days > 0 else date.min


@dataclass(frozen=True)
class Band:
    from_days_before: int
    every_days: int


@dataclass(frozen=True)
class Step:
    role_code: str
    starts_code: str
    from_days_before: int | None
    channel_codes: tuple[str, ...]


@dataclass(frozen=True)
class Setting:
    reminder_kind_code: str
    version_number: int
    # Ordered from the band starting furthest ahead of the date to the last, which runs on.
    bands: tuple[Band, ...]
    steps: tuple[Step, ...]


@dataclass(frozen=True)
class Dated:
    on: date
    reason_code: str

    @property
    def not_yet_recorded(self) -> bool:
        return self.reason_code in NOT_YET_RECORDED_REASONS


@dataclass(frozen=True)
class Days:
    first_on: date
    current_on: date
    so_far: int


@dataclass(frozen=True)
class Reached:
    step_number: int
    step: Step
    reached_on: date


# --- A reminder's date (section 5.2) ---------------------------------------------------------------------------


def _requirement(rule: evaluation.Rule, rules: Iterable[evaluation.Rule]) -> Iterator[evaluation.Rule]:
    """The rule, then, back in time, each rule of the same scope it took over from the day after that one ended."""
    candidates = [
        item
        for item in rules
        if item.kind_code == rule.kind_code
        and item.class_code == rule.class_code
        and item.type_code == rule.type_code
        and item.applies_when_code == rule.applies_when_code
        and item.jurisdiction_code == rule.jurisdiction_code
        and item.lapse_code != LAPSE_NOT_REQUIRED
        and item.effective_to is not None
    ]
    current = rule
    yield current
    while current.effective_from > date.min:
        previous = next((item for item in candidates if item.effective_to == current.effective_from - timedelta(days=1)), None)
        if previous is None or previous.effective_from >= current.effective_from:
            return
        current = previous
        yield current


def requirement_began(rule: evaluation.Rule, rules: Iterable[evaluation.Rule]) -> date:
    """The day this requirement began: the rule's own start, or, where it took over from a rule of the same scope
    ending the day before, that rule's - and so on back. A rule replaced by a successor does not make the
    certificate newly needed."""
    *_, first = _requirement(rule, rules)
    return first.effective_from


def _rule_on(rule: evaluation.Rule, rules: Iterable[evaluation.Rule], day: date) -> evaluation.Rule | None:
    """The rule of this requirement in force on `day` - the rule itself or one it took over from - or None before the
    requirement began."""
    return next((item for item in _requirement(rule, rules) if item.effective_from <= day), None)


def transport_since(evidence: evaluation.Evidence, assets: tuple[str, ...], days: tuple[date, ...]) -> date | None:
    """The day the registration saying transport took effect, of those in force on any of these assets on any of
    `days` - today, and for a job the day its rules are chosen for - read as the check reads the transport question
    (`evaluation.is_transport`; independent review, ELG2-R2-003): one standing, or, with none standing, one run out."""
    standing, ran_out = evaluation.registrations_in_force(evidence.certificates, assets, days)
    transport = evaluation.says_transport(standing if standing else ran_out)
    return max(item.valid_from for item in transport) if transport else None


def mark_stopped(
    marks: Iterable[evaluation.Mark], today: date, rule: evaluation.Rule, rules: Iterable[evaluation.Rule]
) -> Dated | None:
    """The latest day a "not applicable" mark stopped standing for this requirement: its last day where it ended, or
    the day it was withdrawn (its last day, if that came first). Only a mark the requirement's rule in force that day
    let stand - allowing marks, within its limit on how long, as the check counts one - ever stood for it: a mark
    under the baseline never covered a state's rule allowing none (independent review, ELG2-R3-002). Where a later
    rule stopped a mark standing before it ended, the date falls back to the requirement's start or the machine
    added: earlier, the cautious side."""
    rules = tuple(rules)
    stopped: list[Dated] = []
    for mark in marks:
        if mark.withdrawn and mark.withdrawn_on is not None:
            if mark.until_date is not None and mark.until_date < mark.withdrawn_on:
                dated = Dated(mark.until_date, REASON_MARK_ENDS)
            else:
                dated = Dated(mark.withdrawn_on, REASON_MARK_WITHDRAWN)
        elif not mark.withdrawn and mark.until_date is not None and mark.until_date < today:
            dated = Dated(mark.until_date, REASON_MARK_ENDS)
        else:
            continue
        in_force = _rule_on(rule, rules, dated.on)
        if in_force is not None and evaluation.allows_mark(in_force, mark):
            stopped.append(dated)
    return max(stopped, key=lambda item: item.on) if stopped else None


def _sequence(evidence: evaluation.Evidence, certificate: evaluation.Certificate) -> list[evaluation.Certificate]:
    """The certificates of one sequence, as `evaluation.cover` groups them: one asset's of one kind - and, for a permit,
    one place's."""
    return [
        item
        for item in evidence.certificates
        if item.kind_code == certificate.kind_code
        and item.asset_public_id == certificate.asset_public_id
        and item.valid_in_code == certificate.valid_in_code
    ]


def covered_until_before(
    certificate: evaluation.Certificate, rule: evaluation.Rule, evidence: evaluation.Evidence
) -> date:
    """For a certificate in force without its copy: the last day its sequence covered before it took over - the cover
    in force the day before its start, which a renewal without its copy cuts short at that day - or, with none, the
    day before its start. The day the cover ends, as a certificate running out is dated (independent review,
    ELG2-R2-002). Where the one before it was also without its copy, and the one before that, the walk goes back
    through them all: the cover ended once, where the last certificate with its copy stopped covering, and each
    further one without its copy leaves that date - and so the reminder - as it was (ELG2-R4-001)."""
    sequence = _sequence(evidence, certificate)
    starts_on = certificate.valid_from
    while True:
        day_before = _shift(starts_on, -1)
        before = evaluation.cover(sequence, rule, day_before)
        if before.gap_code is None and before.ends_on is not None:
            return min(before.ends_on, day_before)
        uncopied = before.certificate if before.gap_code == OUTCOME_COPY_MISSING else None
        if uncopied is None or uncopied.valid_from >= starts_on:
            return day_before
        starts_on = uncopied.valid_from


def uncopied_takeover(result: evaluation.Result, evidence: evaluation.Evidence) -> evaluation.Certificate | None:
    """The renewal, recorded ahead, whose missing copy ends the cover: it takes over the day after the cover ends - of
    those starting that day in the same sequence (the same asset and, for a permit, place), the one recorded last, as
    `evaluation.cover` takes it - and has no copy. The reminder is then about the copy, still dated by the day the cover
    ends: the renewal changes its reason, not its date (independent review, ELG2-R1-001 and ELG2-R2-002)."""
    current = result.certificate
    if current is None or result.cover_ends_on is None or result.cover_ends_on == date.max:
        return None
    starts_on = result.cover_ends_on + timedelta(days=1)
    takeovers = [item for item in _sequence(evidence, current) if not item.withdrawn and item.valid_from == starts_on]
    if not takeovers:
        return None
    takeover = max(takeovers, key=lambda item: item.certificate_id)
    return None if takeover.has_copy else takeover


def _latest(candidates: list[Dated]) -> Dated:
    # The reason it is needed now; on a tie the cautious one - "running out" reaches more people sooner.
    return max(candidates, key=lambda item: (item.on, not item.not_yet_recorded))


def reminder_date(
    result: evaluation.Result,
    evidence: evaluation.Evidence,
    *,
    assets: tuple[str, ...],
    added_on: date,
    today: date,
    rule_day: date | None = None,
) -> Dated | None:
    """The date one result is reminded about, with its reason, or None when it has none: a certificate with no end,
    a mark with no end, or no certificate required. `assets` are those whose certificates meet the result's rule -
    the asset and the parts fitted below it - `added_on` the day the asset was added to the Equipment Master, and
    `rule_day` (for a job) the day its rules were chosen for.

    A certificate short because of a missing copy is dated, as one running out is, by the day the cover ends: a
    renewal recorded without its copy changes the reason, not the date - so not the reminder either, and nobody it has
    reached drops off (independent review, ELG2-R2-002)."""
    if result.kind_code is None or result.rule is None:
        return None
    if result.outcome_code not in (OUTCOME_MISSING, OUTCOME_COPY_MISSING):
        if result.cover_ends_on is None:
            return None
        if result.mark is not None:
            return Dated(result.cover_ends_on, REASON_MARK_ENDS)
        if uncopied_takeover(result, evidence) is not None:
            return Dated(result.cover_ends_on, REASON_COPY_MISSING)
        return Dated(result.cover_ends_on, REASON_RUNS_OUT)
    candidates = [Dated(added_on, REASON_ADDED), Dated(requirement_began(result.rule, evidence.rules), REASON_RULE)]
    if result.rule.applies_when_code == APPLIES_TRANSPORT_ONLY:
        since = transport_since(evidence, assets, (today, rule_day or today))
        if since is not None:
            candidates.append(Dated(since, REASON_TRANSPORT))
    if result.outcome_code == OUTCOME_COPY_MISSING and result.certificate is not None:
        candidates.append(Dated(covered_until_before(result.certificate, result.rule, evidence), REASON_COPY_MISSING))
    stopped = mark_stopped(
        (mark for mark in evidence.marks if mark.kind_code == result.kind_code and mark.asset_public_id in assets),
        today,
        result.rule,
        evidence.rules,
    )
    if stopped is not None:
        candidates.append(stopped)
    return _latest(candidates)


# --- Which reminder (section 5.1) ------------------------------------------------------------------------------


def asset_reminder_kind(dated: Dated) -> str:
    return REMINDER_NOT_YET_RECORDED if dated.not_yet_recorded else REMINDER_RUNNING_OUT


def allocation_reminder_kind(outcome_code: str, *, first_day: date, today: date) -> str | None:
    """The allocation reminder one result of an allocation's check raises, if any. A cover ending after the job,
    or none ending, raises none: the renewal list's reminder covers the machine."""
    if outcome_code == OUTCOME_RUNS_OUT_BEFORE_START:
        return REMINDER_BEFORE_JOB
    if outcome_code == OUTCOME_RUNS_OUT_IN_PERIOD:
        return REMINDER_DURING_JOB
    if outcome_code in (OUTCOME_RUN_OUT, OUTCOME_MISSING, OUTCOME_COPY_MISSING):
        return REMINDER_BEFORE_JOB if first_day > today else REMINDER_DURING_JOB
    return None


def reminder_key(
    reminder_kind_code: str, subject_type: str, subject_public_id: str, asset_public_id: str, kind_code: str, on: date
) -> str:
    """A reminder's identity: what it is, what it is about, and its date. A new date - a renewal recorded - is a new
    reminder, and its "seen" marks start afresh."""
    return "|".join((reminder_kind_code, subject_type, subject_public_id, asset_public_id, kind_code, on.isoformat()))


# --- Reminder days (section 5.3) -------------------------------------------------------------------------------


def _band_offsets(bands: tuple[Band, ...], index: int, low: int, high: int) -> tuple[int, int, int]:
    """How many of band `index`'s days-before fall in [low, high], and the smallest and largest of them."""
    band = bands[index]
    floor = bands[index + 1].from_days_before + 1 if index + 1 < len(bands) else low
    top, bottom = min(band.from_days_before, high), max(floor, low)
    if top < bottom:
        return 0, 0, 0
    every = band.every_days
    k_first = (band.from_days_before - top + every - 1) // every
    k_last = (band.from_days_before - bottom) // every
    if k_last < k_first:
        return 0, 0, 0
    return k_last - k_first + 1, band.from_days_before - k_last * every, band.from_days_before - k_first * every


def _offsets(bands: tuple[Band, ...], low: int, high: int) -> tuple[int, int | None, int | None]:
    count, smallest, largest = 0, None, None
    for index in range(len(bands)):
        found, band_smallest, band_largest = _band_offsets(bands, index, low, high)
        if found:
            count += found
            smallest = band_smallest if smallest is None else min(smallest, band_smallest)
            largest = band_largest if largest is None else max(largest, band_largest)
    return count, smallest, largest


def reminder_days(bands: tuple[Band, ...], *, date_on: date, began_on: date, today: date) -> Days | None:
    """The reminder days of a reminder dated `date_on` that began on `began_on`, up to today; None when none has come
    yet. The day it began is a reminder day too when it falls inside the schedule's reach."""
    if not bands or today < began_on:
        return None
    began_before = (date_on - began_on).days
    count, smallest, _largest = _offsets(bands, (date_on - today).days, began_before)
    flagged = began_before <= bands[0].from_days_before
    extra = flagged and _offsets(bands, began_before, began_before)[0] == 0
    so_far = count + (1 if extra else 0)
    if so_far == 0:
        return None
    current_on = _shift(date_on, -smallest) if smallest is not None else began_on
    if extra:
        current_on = max(current_on, began_on)
    if flagged:
        first_on = began_on
    else:
        _count, _smallest, first = _offsets(bands, _FAR_AFTER, began_before)
        first_on = _shift(date_on, -(first if first is not None else 0))
    return Days(first_on, current_on, so_far)


def reached_steps(steps: tuple[Step, ...], *, first_on: date, date_on: date, today: date) -> list[Reached]:
    """The steps that have reached their audience by today, each from when."""
    reached: list[Reached] = []
    for number, step in enumerate(steps, 1):
        if step.starts_code == STEP_FROM_FIRST_REMINDER or step.from_days_before is None:
            on = first_on
        else:
            on = max(first_on, _shift(date_on, -step.from_days_before))
        if on <= today:
            reached.append(Reached(number, step, on))
    return reached


# --- Settings (section 5.6) ------------------------------------------------------------------------------------


def ordered_bands(bands: Iterable[Band]) -> tuple[Band, ...]:
    return tuple(sorted(bands, key=lambda band: -band.from_days_before))


def setting_problem(bands: tuple[Band, ...], steps: tuple[Step, ...], *, active_roles: set[str]) -> str | None:
    """Why a schedule and path cannot be saved, in words, or None. `bands` as given; their order does not matter."""
    if not 1 <= len(bands) <= MAX_BANDS:
        return f"Give at least one band of reminders, and no more than {MAX_BANDS}."
    for band in bands:
        if not -MAX_REMINDER_DAYS <= band.from_days_before <= MAX_REMINDER_DAYS:
            return f"A band must start between {MAX_REMINDER_DAYS} days before and {MAX_REMINDER_DAYS} days after the date."
        if not 1 <= band.every_days <= MAX_REMINDER_DAYS:
            return f"A band must repeat every 1 to {MAX_REMINDER_DAYS} days."
    starts = [band.from_days_before for band in bands]
    if len(set(starts)) != len(starts):
        return "Two bands start on the same day. Give each band its own start."
    if min(starts) > 0:
        return (
            "The last band must start on the reminder's date - the day a certificate runs out, or 1 January for a "
            "holiday calendar year - or after it, so that what is past its date is never left without reminders."
        )
    if not 1 <= len(steps) <= MAX_STEPS:
        return f"Give at least one step on the path, and no more than {MAX_STEPS}."
    roles = [step.role_code for step in steps]
    if any(role not in active_roles for role in roles):
        return "Choose each step's role from the list."
    if len(set(roles)) != len(roles):
        return "A role may be on one step only."
    if steps[0].starts_code != STEP_FROM_FIRST_REMINDER:
        return "The first step must start at the first reminder, so that the first reminder reaches someone."
    first_band = max(starts)
    for step in steps:
        if step.starts_code not in (STEP_FROM_FIRST_REMINDER, STEP_FROM_DAYS_BEFORE):
            return "Each step starts at the first reminder, or a number of days before or after the date."
        if (step.starts_code == STEP_FROM_DAYS_BEFORE) != (step.from_days_before is not None):
            return "Give the days for a step that starts some days before or after the date, and only for such a step."
        if step.from_days_before is not None:
            if step.from_days_before < -MAX_REMINDER_DAYS:
                return f"A step must start no more than {MAX_REMINDER_DAYS} days after the date."
            if step.from_days_before > first_band:
                return "A step cannot start before the first reminder."
        if not step.channel_codes or any(code not in CHANNEL_CODES for code in step.channel_codes):
            return "Only the screen is available as a channel for now."
        if len(set(step.channel_codes)) != len(step.channel_codes):
            return "Give each channel once."
    return None
