# Slice 9B - CRM Pilot Hardening

## Status

Implemented, 7 September 2026. Foundation Slice Mode. No migration.

Track 1 of the post-E3 plan in
`docs/continuity/PF_1A_E3_INTEGRATION_CLOSURE_AND_WAY_FORWARD_2026-09-07.md`: the minimum needed
before real users enter real customer data in an internal pilot.

## Two independent changes

### 1. A Rejected Commercial Offer is final

**Business decision, PBL, 7 September 2026.** Once a Commercial Offer is Rejected, no further
customer response may be recorded against it. If the customer later awards the enquiry, Sales
records that against the replacement offer.

`REJECTED` is removed from `COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES`, which closes
the `REJECTED -> ACCEPTED` path through the Slice 6L Customer Response action. The service
returns `422` with a message naming the replacement offer as the correct place to record the
outcome.

This closes the gap recorded in `docs/agent/DEFERRED_REQUIREMENTS.md`: because a rejected offer
counts as inactive for the Slice 6B.1 one-active-Base-Offer guard, a replacement offer can
legitimately exist for the same Opportunity; a late `ACCEPTED_AWARDED` response then produced two
live offers for one enquiry.

Deliberately unchanged:

- `COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` still contains `REJECTED`. Preparing a
  replacement offer stays permitted - that was never the defect.
- `ACCEPTED` remains an allowed customer-response status. This narrows one status, not the action.
- The Slice 6M lifecycle-guidance read model needed no change: `can_record_customer_response`
  already derives from the same contract tuple.

Frontend: the Record-customer-response form is gated on the backend's
`can_record_customer_response` rather than shown-and-then-refused, with a **status-appropriate**
panel in its place - the finality/replacement wording appears only for `REJECTED`, since that flag
is also false for Draft, Ready for Review, Withdrawn and Closed. This removed the hardcoded
`["SUBMITTED", "ACCEPTED", "REJECTED"]` list from `CommercialOfferDetailPage.tsx`, which
duplicated the backend contract and had drifted from it. The capability is four-state - `loading`,
`failed`, `allowed`, `blocked` - because guidance being absent means two different things: still
loading (render "checking...") or a completed failure (render the error with a Retry). Both block
the form, but they must say different things. Backend authorization remains authoritative
regardless.

### 2. Insecure placeholder secrets refuse to start outside development

`app/core/config.py` gained a `model_validator` that refuses to construct `Settings` when a known
public placeholder value from `.env.example` is still configured and `app_env` is not a
development environment.

```text
jwt_secret        blank/whitespace refused; placeholder "change-this-in-real-use" refused
database password refused when the EFFECTIVE password is "ChangeThisStrongPassword123!".
                  DATABASE_URL is authoritative when configured - including when it carries no
                  password at all - and postgres_password is consulted only when no URL is set
```

`jwt_secret` is the serious one: it signs authentication tokens, so the shipped placeholder would
let anyone with the repository forge a session for any user and any role. It was confirmed live in
the development environment on 7 September 2026, which is what prompted this.

Design points:

- **Fails closed.** Only `development`, `dev`, `local`, `test` and `ci` are exempt; an
  unrecognised `app_env` (including a typo) is treated as production.
- **Checks the effective value, not just a field.** `.env.example` ships the placeholder password
  inside `DATABASE_URL`, so checking the discrete field alone would have missed the configuration
  that actually ships. The guard parses and URL-decodes the password out of the URL.
- **Branches on whether a URL is configured, not on whether one was parsed out of it.** A
  configured `DATABASE_URL` carrying no password is a legitimate production setup - libpq can
  supply credentials from a service file, `.pgpass`, or an external/IAM mechanism - and must not
  fall back to the discrete field that the URL's presence has already made irrelevant. Doing so
  wrongly refused startup for a passwordless URL whenever `postgres_password` still held its
  default.
- **No value disclosure.** The error names the offending setting, never its configured value.
- Development is unaffected, so the documented local setup keeps working unchanged.

## Out of scope

- Real user provisioning (operational, not code).
- Document upload - `storage_mode: external_link` already supports governed external links, which
  is the agreed pilot approach; no code needed.
- TLS, SSO/MFA and secret-store integration. These belong to the production gate, not the internal
  pilot, and would have delayed it substantially for no pilot benefit.
- `AIV-001` (SurePass), `ACP-001` and `CEX-001` remain deferred; the pilot stays shadow-mode on
  the commitment boundary.

## Verification

```text
docker compose exec backend pytest tests/test_slice_9b_pilot_hardening.py -q    87 passed
docker compose exec backend pytest -q                                         1112 passed (1025 + 87)
alembic current == heads == 20260906_0032                                     unchanged
frontend npm run typecheck / test / build                                     clean / 54 passed / clean
```

Guard verified end to end against the running container, not only in unit tests: development
startup unaffected; `APP_ENV=production` with the placeholder secret refuses with a clear message;
`APP_ENV=production` with a real secret starts normally.

Recorded manual acceptance results, including the one check that could not be completed, are in
`docs/agent/acceptance/slice-9b-crm-pilot-hardening-acceptance.md`.

## Test-quality note

The first version of the refusal tests passed for the wrong reason. The payload used
`received_at` and `response_summary`, but the real schema fields are `response_received_at` and
`customer_response_notes`, so the `422` came from schema validation rather than the business
guard. A positive control was added -
`test_the_payload_shape_itself_is_valid_so_the_refusals_are_genuine` - which sends the identical
payload to a Draft offer and asserts it is refused with "only after submission" and *not* with a
missing-field error. Every refusal test now also asserts the business message, so a malformed
payload cannot make them pass again.


## Correction pass, 7 September 2026

Independent review of candidate `33d1010` returned ten findings, three P1. All were corrected.

**P1-1 - the placeholder database password bypassed the guard through `DATABASE_URL`.**
`.env.example` ships the placeholder password *inside* `DATABASE_URL`, and the guard skipped
`postgres_password` whenever `database_url` was set - which is exactly the shipped configuration.
A production deployment using the unchanged example URL started happily with a publicly known
password. The guard now derives an `effective_database_password`, parsing and URL-decoding the
password out of `DATABASE_URL` when present, and checks that.

**P1-2 - production accepted an empty JWT signing key.** Only exact placeholder matches were
rejected, so `jwt_secret=""` passed. A blank HMAC key is not a weak secret, it is no secret. Blank
and whitespace-only secrets are now refused with a distinct message. This is not an entropy
policy, which remains out of scope.

**P1-3 - concurrent responses could still reactivate a rejected offer.** The status was read
without a row lock and later written by an unconditional `UPDATE`, so two concurrent requests
against a `SUBMITTED` offer could both pass the guard; if `REJECTED_LOST` committed first and
`ACCEPTED_AWARDED` second, the offer ended `ACCEPTED` with both records. `lock_commercial_offer_row`
takes `SELECT ... FOR UPDATE` before the status is read, serializing writers on the offer for the
transaction. Covered by a static ordering guard and a behavioural two-connection `NOWAIT` test.

**P2-4 - Draft offers were described as final.** `can_record_customer_response` is false for
Draft, Ready for Review, Withdrawn, Closed *and* Rejected; collapsing them into one boolean told
Draft users their offer was final and needed a replacement. The panel is now status-appropriate,
reserving the finality wording for `REJECTED`.

**P2-5 - the drifted hardcoded status list still existed.** The previous commit message claimed
it was removed; it survived in the submit button's `disabled` expression and still contained
`REJECTED`. Removed. The capability was made three-state at this point, so that while lifecycle
guidance was loading or had failed a safe "checking..." state rendered instead of a permissively
enabled form. The second correction pass below split that into four states, because collapsing
loading and failure together was itself a defect.

**P2-6 - rejection removed its own success feedback.** Recording `REJECTED_LOST` makes the offer
final, which unmounts the form - and the confirmation message lived inside it, so the user never
saw that the response saved. Feedback now renders outside the conditional.

**P2-7 - the contract contradicted itself.** The original normative sentence still said creation
was allowed for `SUBMITTED`, `ACCEPTED` or `REJECTED`. Appending a correction does not make a
contract unambiguous. The sentence is corrected in place with the former behaviour preserved as a
dated historical note.

**P2-8 - the secret-disclosure test asserted the wrong value.** It configured the placeholder but
asserted an unrelated string was absent, so it would have stayed green had the guard echoed the
real value. It now asserts the configured value is absent, with an equivalent database-password
case.

**P2-9 and P2-10 - missing continuity record and unrecorded manual acceptance.** Both addressed;
see `docs/continuity/SLICE_9B_CRM_PILOT_HARDENING.md` and the recorded-results section of the
acceptance file, which also names the one manual check that could not be completed.


## Second correction pass, 7 September 2026

A follow-up independent review found one remaining P1 path and two P2s. All three are corrected.

**P1 - the general-update route could still reactivate a concurrently rejected offer.** The first
correction pass locked the customer-response path but not `update_commercial_offer`, which reads
`offer_status_code`, validates it against the cannot-leave/cannot-enter sets, and then writes an
unconditional `UPDATE`. A general update could read `SUBMITTED`, a concurrent customer response
could commit `REJECTED`, and the update would overwrite the rejection with `DRAFT`. The same row
lock is now taken before that read. Covered by a static ordering guard and a cross-route
concurrency test that forces the exact interleaving: session A holds the lock, thread B's general
update blocks on it, A commits `REJECTED`, and B is then refused on re-read with the rejection
intact. The earlier `NOWAIT` test could not have caught this - it only exercised two
customer-response writers.

**P2 - a passwordless authoritative `DATABASE_URL` wrongly consulted `postgres_password`.**
`database_url_password()` returns `None` both when no URL is set and when a configured URL has no
password, so `effective_database_password` fell back to the explicitly ignored discrete field in
both cases, refusing startup for a legitimate passwordless production URL. It now branches on
whether a URL is configured and returns `None` for a configured passwordless one.

**P2 - a failed guidance request displayed "Checking..." indefinitely.** A failure also leaves
`lifecycleGuidance` null, so the three-state capability reported a completed failure as still in
progress and offered no recovery. The capability is now four-state - `loading`, `failed`,
`allowed`, `blocked` - and the failed state shows the actual error beside the unavailable action
with a Retry button that re-runs `loadLifecycleGuidance`. Behaviour stays fail-closed.


## Third correction pass, 7 September 2026

A third independent review found one remaining P1 and two documentation defects.

**P1 - `mark_commercial_offer_submitted` was the third unlocked read-then-write path.** It read
`offer_status_code`, checked it against the mark-submitted allowed set, and wrote an unconditional
`UPDATE`. A concurrent general update could commit `WITHDRAWN` or `CLOSED` in between, and the
resuming submission would reopen that terminal offer as `SUBMITTED`. The row lock is now taken
before the read, covered by a static ordering guard and an inverse cross-route concurrency test.

**Why this happened three times, and what now prevents a fourth.** Each of the first two
corrections fixed the route the reviewer named instead of the property. The durable fix is a pair
of tests over `commercial_offers.service`, which detect every function writing
`offer_status_code` through `update_commercial_offer_by_public_id`:

- `test_the_set_of_status_writing_paths_is_exactly_the_known_set` asserts the detected set equals
  an explicit three-name set. A newly detected path fails until a human adds the lock and updates
  the set; a *disappearance* fails too, which is what catches a broken detector.
- `test_every_status_writing_path_locks_before_reading_the_status` asserts the lock call precedes
  the first use of `offer_status_code`, parsed with `ast` so comments and docstrings mentioning
  either name cannot affect the result.

The guard's own mechanism is covered by five further tests that feed it synthetic sources -
lock-before-read, lock-after-read, missing lock, comment-decoy, and a non-zero detection count.
That matters because the first version of this guard collected only offenders, so zero detections
passed vacuously, and it checked only that the lock *appeared* somewhere rather than that it came
first.

**P2/P3 - documentation and a code comment still described the superseded three-state UI**, and
the continuity note said there were two status-writing paths when there are three. Both corrected
in place; the historical correction-pass sections keep their original wording but are now written
in past tense so they cannot be read as current state.


## Fifth correction pass, 7 September 2026

Test-file hygiene only. No runtime, contract or guard-logic change.

**P2 - two tests were defined twice, so the earlier copies never ran.** Python keeps only the last
definition of a duplicated name, and pytest reports the module green either way. The cause was my
own editing method in the fourth pass: a string splice using `s.index(start)` and `s.index(end)`
without checking that `start < end`. The end anchor's first occurrence was *earlier* in the file,
so `s[:start] + replacement + s[end:]` duplicated a region instead of replacing it. Both copies
were verified byte-identical before the shadowed ones were removed, so nothing was lost.

The danger this created is specific and worth naming: someone editing the first copy of a test
would have received a passing suite that ignored the edit entirely - in a package whose whole
subject was test validity.

**P3 - the obsolete presence-only guard was still present** alongside the exact-set and
AST-ordering pair meant to replace it. The fourth pass's broken splice had failed to remove it.
Deleted, so there is one authoritative guard.

**Added: `test_no_test_module_defines_the_same_test_twice`**, which parses every `test_*.py` under
`backend/tests` and fails on any duplicated test name. All 52 modules are currently clean. This
follows the rule established earlier in this slice: where a mistake has recurred, encode it as a
test rather than as advice.


## Sixth correction pass, 7 September 2026

Test-guard hardening only. No runtime, contract or service-lock change.

**P2 - the duplicate-test guard reproduced the exact flaw it was written to prevent.** Added in the
fifth pass to stop shadowed tests recurring, it could itself pass vacuously (an empty `rglob`, or
every parse skipped, reaches `assert not offenders` and passes) and inspected only top-level
synchronous `ast.FunctionDef` nodes while its docstring claimed to catch "any duplicated test
name" - so a duplicated `async def` test, or a duplicated method inside a test class, would have
been missed.

Detection is now a helper, `_duplicate_test_names`, covering `def` and `async def` at module level
and inside classes. Shadowing is scoped per namespace: the same name in two different classes, or
once at module level and once as a method, are separate objects that both run, so neither is
reported. `_scan_test_modules` returns module and test counts alongside offenders, and the guard
asserts both are non-zero before asserting no offenders.

Seven tests exercise the helper directly - unique names, repeated module-level test, repeated
async test, repeated class method, repeated async class method, the two cross-namespace
false-positive cases, and a non-zero repository scan. Current scan at that point: 50 modules, 1004 test definitions - which the seventh pass showed
was two modules short.

The pattern worth recording: this is the second guard in this slice whose first version could pass
vacuously. Writing a guard is not the same as knowing it can fail. A guard that cannot demonstrate
its own failure mode is an assertion of intent, not a control.


## Seventh correction pass, 7 September 2026

Test-guard correctness only. No runtime, contract or service-lock change.

**P2 - two test modules were silently excluded from the duplicate scan.**
`test_opportunities_api.py` and `test_work_orders_api.py` begin with a UTF-8 BOM. Python's import
machinery accepts them and pytest runs them normally, but reading with `encoding="utf-8"` leaves
U+FEFF in the string and `ast.parse` rejects it as an invalid non-printable character. The
scanner caught that `SyntaxError` and `continue`d, so both modules - and the 20 tests in them -
were invisible to the guard while it reported success.

Three fixes, of which the second is the important one:

1. Read with `tokenize.open`, which honours both a BOM and a PEP 263 coding declaration.
   `_duplicate_test_names` also strips a leading BOM defensively, so either entry point copes.
2. **Never skip silently.** Read and parse failures are collected and returned, and the guard
   fails on them by path. Separately it asserts `parsed == candidates`, so a module that is found
   but not scanned can no longer hide behind a passing assertion.
3. Regression cases: a synthetic BOM-prefixed source that `ast.parse` rejects but the helper
   handles, and a check that the repository's real BOM-prefixed modules are reachable.

Scan before: 50 of 52 modules, 1004 tests. After: **52 of 52, 1026 tests, 0 offenders.**

This was the third silent-pass defect in this slice, and the pattern is now clear enough to state
plainly: `except ...: continue` inside a checker is almost always a bug. A checker that cannot
examine something must say so, because the alternative is a green result that means nothing.


## Eighth correction pass, 7 September 2026

Three P1 findings, two P2s and two P3s. **This pass changes runtime behaviour**, unlike the four
before it, and it widens the concurrency audit beyond where the earlier passes stopped.

**P1 - the password guard was bypassable through a query-parameter password.** SQLAlchemy accepts
a password in user info *or* as a query parameter, and the query parameter takes precedence for
the driver. `urlsplit(...).password` reads only user info, so a URL carrying the placeholder as a
query parameter passed the guard - including one whose user-info password looked genuine. The
guard now parses with SQLAlchemy's own `make_url`, the same parser the connection builder uses,
and applies the same precedence. All three shapes are covered by tests.

**P1 - the locking audit stopped at status writers; status-dependent mutations were still
raceable.** Related Offer creation requires `ACCEPTED`, revision creation requires `SUBMITTED`,
and Work Order handoff requires `ACCEPTED` - each then inserts a downstream record. A concurrent
customer response committing `REJECTED` between the read and the insert let all three complete
against an offer that was no longer eligible. All three now take the row lock before reading. A
row lock only protects an invariant when every participant takes it, which the previous three
passes missed by treating "which functions write the status" as the whole question.

**P1 - the one-active-Base-Offer rule was itself concurrency-unsafe.** Two simultaneous creations
could both observe no actionable offer and both insert, producing the same two-live-offers state
the rule exists to prevent. This predates Slice 9B but is the same invariant the slice is about.
Creation now serializes per Opportunity using a transaction-scoped advisory lock, chosen over a
row lock on `crm_opportunity` because that table belongs to another module, and over a partial
unique index because that would need a migration this slice deliberately does not add. The index
remains the stronger long-term control and is recorded as follow-up work.

**Also corrected:** the related-offer contract wrongly described `ACCEPTED` as a stable
cannot-leave status. The Slice 6M.1 guard only stops generic update leaving it; the dedicated
customer-response route writes the status directly and can move it to `REJECTED`. That inaccuracy
is precisely what made the missing lock there look unnecessary.

**P2 - the frontend could still hang on "Checking...".** Two paths left the capability
unrenderable: a retry after session loss cleared the error and returned without setting another,
and JSON decoding sat outside the `try`, so a malformed body threw before the loading flag was
cleared. Now `try/catch/finally` with an explicit no-token error.

**P2 - the status-writer detector was weaker than its documentation.** It silently continued on
`inspect.getsource` failure, and it detects only direct textual calls to one repository function,
so it cannot see a wrapper or raw SQL. Source failures are now assertion failures, and the
docstring states the limitation plainly: it is a tripwire for the shape that caused three
defects, not a proof that no other status write exists.

**P3 - the BOM regression depended on accidental repository files.** Normalising them would have
failed a test whose subject is the scanner, so it now creates a temporary BOM fixture.

**P3 - two evidence claims tightened.** The outcome-refusal test omitted `PENDING_CUSTOMER_DECISION`
and `REJECTED_LOST`; it is now parameterised over the full contract list, with a further test that
fails if the contract grows an outcome. The documented starts command inherited the container's
`DATABASE_URL` and would fail on a machine using the shipped placeholder, so it now overrides
every effective secret.


## Ninth correction pass, 7 September 2026

Two further P1 concurrency gaps, plus test and backlog corrections. The concurrency inventory is
now complete for the offer-status invariant.

**P1 - Work Order Amendment validation was the fourth status-dependent mutation.**
`decide_work_order_amendment` requires the cited related Commercial Offer to be currently
`ACCEPTED` and then commits `VALIDATED`, without locking that offer. A concurrent customer
response could reject it in between, validating an amendment against a rejected commercial basis.
The offer is now locked before the readiness read.

This one was found by tracing *consumers of the readiness function* rather than searching for
obvious creation functions - a better enumeration method than the three earlier passes used, and
the reason the earlier audits kept stopping short.

**P1 - the advisory lock closed duplicate creation but left Opportunity eligibility raceable.**
`_normalize_create_payload` read `opportunity_status_code` *before* taking the advisory lock, and
Opportunity updates never took that lock at all, so the Opportunity could become WON/LOST/CLOSED
between the read and the insert. Replaced with a row lock on `crm_opportunity`, taken before the
status read. A row lock is strictly stronger here: an `UPDATE` on that row must acquire the same
lock, so it also blocks a concurrent Opportunity status change, which an advisory lock cannot.
It serializes two concurrent Base Offer creations as well, so the advisory lock was removed as
redundant.

**P2 - the concurrency tests asserted source order, not behaviour.** Two real races are now
exercised: two concurrent `create_commercial_offer` calls for one Opportunity, asserting exactly
one offer survives and the other is refused by the one-active rule; and a concurrent rejection
landing while related-offer creation is blocked on the Base Offer lock, asserting creation is
then refused.

**P3 - the BOM fixture bypassed the scanner.** It called `tokenize.open` and the duplicate helper
by hand, so it would have stayed green if the scanner regressed. `_scan_test_modules` now takes an
injectable `root`, and the test drives the scanner itself against a temporary BOM fixture.

**P3 - the deferred index was not in the canonical backlog.** Recorded in
`docs/agent/DEFERRED_REQUIREMENTS.md` and `docs/continuity/NEXT_STEPS.md`, not only in this
slice's own notes.

## Tenth correction pass, 7 September 2026

One P1, three P2s and two P3s. The offer-status inventory was complete after the ninth pass; this
pass closes a second invariant the ninth pass exposed but did not cover, and replaces the remaining
scheduling-dependent test.

**P1 - Work Order Amendment mutations were not serialized against their own decision.**
The ninth pass locked the *related Commercial Offer* before `decide_work_order_amendment` read its
status, but nothing locked the amendment itself. Its own status is a second invariant with the same
shape: five functions read `amendment_status_code`, check it is non-terminal, and then write - the
header decision plus `update_work_order_amendment`, `create_work_order_amendment_line`,
`update_work_order_amendment_line` and `delete_work_order_amendment_line`. A line could therefore
be added, changed or deleted while a concurrent decision was committing `VALIDATED`, so the
validated amendment would not be the amendment that was reviewed.

`lock_work_order_amendment_row` is added to the Work Order repository and `_get_amendment_and_id`
gains `for_update: bool = False`, which takes the lock *before* the status read. All five mutators
pass `for_update=True`. The three read-only paths - `get_work_order_amendment`,
`get_work_order_amendment_readiness` and `list_work_order_amendment_lines` - deliberately do not,
so ordinary reads are not serialized behind a review.

The lock is on the amendment **header**, not on each line. Locking line rows individually would
leave add and delete raceable, because a row that does not exist yet cannot be locked. Locking the
aggregate root serializes every one of its mutators through the record that owns the invariant.

**P2 - the amendment lock needed a behavioural test.** A source-order assertion proves the lock is
written in the right place, not that it works.
`test_a_concurrent_rejection_defeats_an_in_flight_amendment_validation` now forces the real
interleaving: an external session holds the commercial-basis offer's row lock, validation blocks on
it, the offer is rejected and committed, and validation must then be refused.

**P2 - the duplicate-test detector saw only functions.** `_duplicate_test_names` walked
`FunctionDef`/`AsyncFunctionDef` but not `ClassDef`, so two `class TestX` blocks in one module -
where the second silently shadows the first, exactly the failure the detector exists to catch -
passed. It now reports duplicate class names as `class <name>`, with three tests: a repeated class,
two distinct classes, and the whole scan end-to-end through `_scan_test_modules`.

**P2 - the contract comment described `ACCEPTED` as a cannot-leave terminal status.** It is not:
the customer-response route writes `offer_status_code` through the repository and is unaffected by
the generic-update guard. That wrong description is the reason the missing lock on related-offer
creation looked unnecessary for three review rounds, so it is corrected rather than left as
harmless prose.

**P3 - the concurrent-create test depended on thread scheduling.** The ninth pass's
"two concurrent creations, exactly one survives" test could pass for the wrong reason if the second
thread started after the first committed. It is replaced by `_blocked_then_released`, a helper that
forces the interleaving deterministically: start the operation in a thread while an external
session holds the lock, assert it is genuinely still blocked, release, then assert the outcome.
`test_a_concurrent_opportunity_closure_defeats_an_in_flight_offer_creation` uses it to prove the
Opportunity row lock does the job the advisory lock could not.

**P3 - the completion note still described the ninth pass's superseded design.** It recorded three
status-dependent mutations and an advisory lock. Reconciled in
`docs/continuity/SLICE_9B_CRM_PILOT_HARDENING.md`: four dependants, the Opportunity **row** lock,
an explicit statement that no advisory lock remains, and the amendment aggregate-root lock.

**Self-review finding in the same pass - test teardown was not fail-safe.**
`test_a_concurrent_opportunity_closure_defeats_an_in_flight_offer_creation` deleted its
Opportunity *after* its assertions, so a failing run would have left a row behind - the same
residue defect this slice's own notes record from Slice 9A. Teardown moved into a `finally`, and
it now also removes any offer that a lock regression would have created, since such an offer
would otherwise block the parent delete. Both deterministic concurrency tests additionally assert
the post-state, not only the refusal: the amendment must still be `UNDER_REVIEW`, and no offer may
exist for the closed Opportunity. A refusal that raised *after* writing would pass a
message-only assertion.


## Eleventh correction pass, 8 September 2026

Three P2s and one P3. No P1. The verdict recorded that the six production fixes from the tenth
pass were correct; what this pass corrects is that two of them were not actually protected by a
test, plus a second concurrency gap the tenth pass created the conditions to notice.

**P2 - the aggregate-root lock had no effective regression test.** The tenth pass's
`test_a_concurrent_rejection_defeats_an_in_flight_amendment_validation` exercised the *related
offer's* row lock, which the ninth pass had added. It passed with `lock_work_order_amendment_row`
removed, so it protected the wrong invariant and would have let a regression through.

Two things were done about it. First, the shared helper `_blocked_then_released` now takes a
mandatory `expected_exception`; anything else the worker raises is classified `"crashed"` rather
than reported as the business refusal, so a mis-built fixture can no longer look like a pass -
the same catch-all-`except` defect this slice already recorded twice, this time in a test helper
rather than a checker.

Second, `test_a_concurrent_cancellation_defeats_an_in_flight_amendment_line_add` exercises the
amendment lock directly: an external session holds the amendment row lock, adding a line blocks,
the amendment is cancelled and committed, and the line add must then be refused with the line not
inserted. **Verified by deleting the lock and re-running:** the test fails, as does
`test_every_amendment_mutator_takes_the_row_lock`.

That deletion also showed the failure mode is subtler than "the add would not block". Inserting a
line takes a `FOR KEY SHARE` lock on the parent amendment row for the foreign key, which conflicts
with the external `FOR UPDATE`, so the insert waits *anyway*. What the aggregate-root lock changes
is **when the status is read**: without it the status is read before the wait, so the decision is
made on stale data and the line lands on a cancelled amendment. A test asserting only "it took a
while" would have proved nothing.

Three introspection tests now hold the inventory the tenth pass's acceptance file merely claimed:
the set of functions that resolve an amendment is discovered by introspection and must equal five
named mutators plus three named read-only paths; every mutator must pass `for_update=True`; no
read-only path may. A new amendment accessor is therefore classified deliberately or the suite
fails.

**P2 - amendment intake was still concurrency-unsafe.** `create_work_order_amendment` computes
`amendment_sequence_no` as `MAX(...) + 1` for the Work Order and checks that
`customer_amendment_reference` is not already used, then inserts - a read-then-insert with no
lock. It cannot lock the amendment row it is about to create, so it now locks the parent Work
Order: `lock_work_order_row` in the repository, reached through
`_get_work_order_and_id(..., for_update=True)` so the lock is part of the read rather than
something a caller must remember afterwards.

Two concurrent valid intakes previously collided on
`uq_crm_work_order_amendment_wo_sequence` - a constraint neither user violated - surfacing as an
unhandled database error rather than a business message.
`test_a_concurrent_intake_would_collide_on_the_sequence_number_without_the_lock` forces exactly
that interleaving. **Verified by deleting the lock:** the run fails with a detected deadlock, and
leaves no residue, because that test clears every amendment on its Work Order before the manifest
cleanup rather than assuming the run created nothing unexpected.

**P2 - the audit-event anomaly had a real mechanism, not just an unlucky run.** The tenth pass
recorded the three unreproducible failures honestly but treated reruns as the response. The
reviewer identified the cause, and it is worse than a flaky count:
`backend/tests/test_smoke_data_audit_events.py` passed `("sales1",)` as the deletion allowlist and
asserted exact counts such as `deleted == 2`. `delete_login_events_after` is global above its
boundary, so any concurrent `sales1` login - another test, an E2E run, a person using the app -
both broke the count **and was itself deleted**. A test was capable of destroying a real user's
audit trail.

The allowlist is the isolation boundary, so each test now generates its own actor username and
can neither see nor delete anything else. `residual == []` becomes "no *allowlisted* actor appears
in the residual", which is the actual property and is immune to concurrent noise. The real
`DEFAULT_E2E_ACTORS` tuple is still exercised by the argument-validation tests, which write no
rows. **Verified**: with a stray `sales1` login event deliberately present, all 20 tests pass and
the stray survives untouched. No change was made to `tooling/smoke_data/audit_events.py` itself.

**P3 - documentation reconciliation.** The tenth pass's acceptance file titled a five-row table
"the four new tests", and claimed the amendment lock inventory "was verified by introspection"
when that had been a manual shell check, not a test. Both corrected; the introspection tests it
described now exist. The completion note's mutator arithmetic is corrected to three line-level
plus two header-level mutators, and it now records that creation locks the Work Order instead.


## Twelfth correction pass, 8 September 2026

Three P2s and one P3, no P1. The runtime locks and audit isolation from the eleventh pass were
confirmed sound; two of the three P2s are again guards that did not guard.

**P2 - a successful customer response could still lose its confirmation.** The POST handler set
the success message only after three sequentially awaited refreshes, and parsed the response body
outside any `try`. Once the POST has succeeded the response is recorded on the server, so every
line after it is display work - but a malformed body, or a throw inside `loadCustomerResponses` or
`loadSubmissionReadiness`, left a genuinely recorded rejection showing no confirmation at all.
This is the same defect as review finding 6 in the first pass, one layer further out: that pass
moved the message outside the *form*, so unmounting could not remove it, but left it downstream of
work that can fail.

The handler now parses inside a `try` (reporting "recorded, but the confirmation could not be
read" on failure), sets the message and clears the saving state **immediately** after the POST
response is processed, and only then refreshes - through `Promise.allSettled`, so one failing
refresh neither prevents the others nor propagates out of an action that has already succeeded.

**P2 - the amendment-validation test accepted the wrong refusal.** It asserted the exception class
and the unchanged status, but not the reason, so replacing the intended post-block refusal with an
unrelated `WorkOrderValidationError` kept it green. It now asserts the message states that the
linked Supplementary Offer / Change Quotation must be Accepted. **Verified by replacing that
message with a generic one: the test fails.**

**P2 - the new lock-inventory guards were comment-decoyable.** They searched source text for
`for_update=True` and compared string indexes. Removing the real argument while leaving the words
in a comment kept the authoritative inventory test green - precisely the failure mode this slice
has now hit three times. All of them are AST-based now: `_calls_with_keyword` parses the source and
counts only a genuine keyword argument whose value is the constant `True`, on a genuine call to the
named callee; the mutator assertion requires *every* such call to pass it, so a second unlocked
lookup beside a locked one fails; and the creation-order assertion compares AST line numbers rather
than string indexes. The helper carries four tests of its own mechanism, including the exact
comment decoy and a string-literal decoy. **Verified by reproducing the reviewer's decoy: both the
inventory guard and the behavioural test fail.**

**P3 - the intake test's docstring described a failure that does not occur.** It predicted an
`IntegrityError` classified as `"crashed"`. The actual mutation deadlocks on the main thread inside
the holder's release, before the helper returns any outcome. The docstring now records the observed
behaviour rather than the predicted one, and states plainly that what matters is that the test fails
without the lock and passes with it.

**Parked, with the reason recorded.** The reviewer's requested frontend regression test - a
successful `REJECTED_LOST` whose secondary refresh fails, asserting the finality panel and success
message both still appear - is **not** added here. The frontend has no component-test capability at
all: `frontend/package.json` carries Vitest but neither `@testing-library/react` nor `jsdom`, and
`frontend/src/routes.test.ts` is pure route-table matching. Adding one behavioural test means adding
two dev dependencies and a jsdom test environment, which is a frontend-tooling package rather than a
correction to this slice. It is recorded in `docs/agent/DEFERRED_REQUIREMENTS.md` together with the
outstanding manual UI check, which the same capability would close.
