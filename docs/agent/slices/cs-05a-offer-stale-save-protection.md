# CS-05a - A stale form cannot overwrite a Commercial Offer or an offer line

## Status

**BUILT 9 October 2026**, on branch `fix/cs-05a-offer-stale-save`, built on `main` at `f0eb393` (Alembic head
`20260908_0050`). Migration `20260908_0051`. Independent review (bounded packet) and CI's
`Required validation` decide the merge; the outcome is recorded in `docs/continuity/CS_05A_OFFER_STALE_SAVE_PROTECTION.md`
and `docs/continuity/NEXT_STEPS.md`.

TB-1 corrective package CS-05, its first part (CS-05a: offer header and lines), row 10 of the corrective register's
"Recommended correction sequence" - before vendor handover. It closes finding TB1-303's offer part. The TB-1 records
under `docs/agent/tb-1/` are pinned by SHA-256 inside themselves and are not edited; this record, the continuity note
and `NEXT_STEPS.md` carry the finding's status from here on, as every package since TB-1 has.

## Work package

```text
Title / package ID      CS-05a - stale-save protection for Commercial Offer headers and lines
Objective               A form opened before someone else's save can no longer overwrite it: the offer's edit and a
                        line's edit carry the version the screen loaded and are refused (409) when the record has moved
                        on; the screens send only what changed; a line's amount comes from the line as locked
Why this is next        Row 10 of the TB-1 register's sequence, after CS-11 split the service (row 9). The owner scoped
                        it on 9 October 2026 (below)
Owning module           Commercial Offers (backend/app/modules/commercial_offers, the offer page)
Branch/worktree         fix/cs-05a-offer-stale-save, <a separate worktree>
Migration               20260908_0051 (down_revision 20260908_0050), assigned by the owner
```

### Authority and required reading

Read in full: PBL's internal working instructions, `AGENTS.md`, PBL's local working notes; `docs/agent/tb-1/TB_1_CORRECTIVE_SLICE_REGISTER.md` (CS-05
and the sequence); `docs/agent/tb-1/TB_1_FINDINGS_REGISTER.md` (TB1-303, with TB1-301 for context);
`docs/agent/contracts/commercial-offer-contract.md`; `docs/agent/technical-enablement/CS_11_COMMERCIAL_OFFERS_SERVICE_SPLIT.md`
(the service lives in `services/offers.py` and `services/lines.py`; a new public name is pinned in
`NAMES_ADDED_AFTER_THE_SPLIT`). Read for the pattern reused: `docs/agent/contracts/work-order-contract.md` (7C's
`expected_detail_version`, 7D's `expected_term_revision`, the contract period's `expected_period_version`) and
`backend/app/modules/work_orders/services/billing_terms.py` and `line_detail.py`. Searched and read the matching
sections: `DEFERRED_REQUIREMENTS.md` ("Submitted document locking", "Database-level uniqueness for the
one-active-Base-Offer rule"), `MCF_ADOPTION_RECORD.md` (the Commercial Offers row), `TESTING_STRATEGY.md` section 11
(the harness's record sets), `CODING_STANDARDS.md` ("When a service outgrows one file", section 7's styling rule),
the frozen `accepted-offer-to-work-order-handoff-contract.md` (unchanged; SHA-256
`0f16ff221e897f6199c352204a0ecced6f9a67f0c6695ad97c08c9dc2cd39080` before and after).

### The owner's decisions (9 October 2026)

- CS-05a is stale-save protection only: a version column and migration (slot `0051`), the `409` refusal, forms that
  send the version and only the fields that changed, and the line amount computed from the locked row.
- For the next package, recorded in `NEXT_STEPS.md` and not built here: (1) a submitted offer may not be changed except
  through a revision; (2) the database enforces the one-active-Base-Offer rule; (3) a duplicate caused by a double
  click gets a clear message, not a server error.
- The "do not edit in two tabs" tester instruction is lifted for offers only; it stands for the other modules.

## What was wrong

TB1-303 (TB-1 Pass 3): 32 of 95 writing routes compared a version - every Hiring and Work Order line-level edit - but
none of the CRM edits. The offer's edit took the offer's row lock and compared nothing; the screen sent the whole form,
status included. A line's edit sent with only the quantity by one user and only the rate by another could store an
amount that was neither user's quantity times rate. Two tabs reproduced it.

## What changed

**Database.** `row_version INTEGER NOT NULL DEFAULT 1` with a check `row_version >= 1` on `crm_commercial_offer`
(`ck_crm_commercial_offer_row_version`) and `crm_commercial_offer_line` (`ck_crm_commercial_offer_line_row_version`).
Existing rows start at `1`. Downgrade drops both.

**Backend.**

- `repository.py`: both selects return `row_version`. `update_commercial_offer_by_public_id` raises it on every write
  and, given `expected_row_version`, writes only while the row still has it (returning `None` otherwise);
  `update_commercial_offer_line_by_public_id` always does. `get_commercial_offer_line_context(for_update=True)` reads
  the line `FOR NO KEY UPDATE`.
- `services/offers.py`: under the offer's row lock, `expected_row_version` against the row's, before the rules about
  the request's values (status moves, dates, currency); `409` on any difference. The version is not counted as a field
  of the offer. What the request schema itself refuses (types, the bounds it declares) is FastAPI's `422` before any of
  this, whatever the version - the contract section lists the order of the checks.
- `services/lines.py`: the same under the offer lock, with the line read locked; its amount is computed from that row.
- `services/common.py`: `CommercialOfferConflictError` (the module's error vocabulary), re-exported by `service.py` and
  pinned in `test_cs11_commercial_offers_service_surface.py`'s `NAMES_ADDED_AFTER_THE_SPLIT`; `routes.py` maps it to
  `409` on the two `PUT` routes.
- `schemas.py`: `expected_row_version` (required, `>= 1`) on both update requests; `row_version` on both responses.
- Marking an offer submitted and a customer response that sets its status raise the version through the same
  repository function, so a form opened before either is refused.
- Events: `CommercialOfferUpdated` and `CommercialOfferLineUpdated` carry `row_version`. No new event, route or
  permission.

**Frontend.** `pages/commercial-offers/offerEditState.ts` (with Vitest tests): `changedFields` and `updateRequest`. The
offer page keeps the offer (and the line) each edit form was opened from; a save sends that record's `row_version` and
only the fields the user changed, says "Nothing has been changed, so there is nothing to save." when nothing did, and
shows any refusal - the `409` included - beside the Save button pressed: the offer's form already had its message
there; the line's edit form gains its own (`offerLineEditError`, classes `action-feedback text-danger`), where its
errors were shown above the list before.

**Tests and tooling.** `backend/tests/test_cs05a_offer_stale_save.py` (new; below). Every existing test that edits an
offer or a line sends the version as it is now, read by `tests/offer_version_test_support.py`: 28 calls in
`test_commercial_offers_api.py`, 3 in `test_operating_currency.py`, 2 in `test_reports_api.py`, 1 each in
`test_slice_9b_pilot_hardening.py` (the version read after the submission and before the race) and
`test_slice_9e_quotation_generation.py`. No assertion changed. No smoke-data builder edits an offer or a line through
the edit routes. The core bundle gains its eleventh record set, `stale_save_target` (a draft offer with one line, built
as `document_upload_target` is, through the same new `_build_draft_offer_with_line`), and
`test_smoke_data_harness.py` counts its Account (`10`, was `9`). `e2e/tests/offer-stale-save.spec.ts` (new) opens it in
two tabs. No existing Playwright spec saves an offer or a line.

## Design choices

- **The Hiring modules' pattern, not a new one.** An expected version in the request, compared under the row lock,
  `409` with the module's own plain message, the `UPDATE` guarded on the version as a backstop - as 7C's line detail,
  7D's billing terms, the contract period and HOL-1's calendar do. Named `row_version` (`CODING_STANDARDS.md` section 4)
  rather than `offer_version`, which would read as the offer's commercial version or revision.
- **Every write of the row raises it, not only the edit.** A tab opened while the offer was a draft offers "Withdrawn";
  after someone marks it submitted, that tab's save would otherwise withdraw a submitted offer its user never saw.
- **Required, not optional.** An omitted version would skip the check, so it is refused (`422`). A page loaded before
  the upgrade must be reloaded once.
- **The request schema first.** FastAPI validates the typed request body before the route runs, so what the schema
  declares (types, bounds, lengths) is refused `422` before the version is read. Comparing the version first would mean
  replacing the typed body, and the API schema it documents, with raw JSON parsed by hand, for an outcome that writes
  nothing either way and that the page never meets (it checks the same bounds before sending). Review round 1 found the
  first records said "before the request's values are judged"; they now state the order exactly.
- **Every save changing something is a write.** The offer's and line's edits keep their existing behaviour of recording
  a save that repeats the stored values; the page no longer sends one (it says nothing changed). The Hiring modules'
  "an identical save is not an edit" rule was not carried over: the owner scoped this package to the version.
- **The line locked as well as the offer.** Every application writer of lines takes the offer's lock already; the
  line's own lock makes the amount right even against a writer that does not.
- **Application-level, with a static guard.** No database trigger: the Hiring modules raise their versions in the
  `UPDATE` itself. A test fails if a function in the application writes either table without raising the version -
  found by the table's name or any constant bound to it, in any letter case - and no ORM model maps either table.

## MCF-001 and cross-module access

G4 (idempotency): the two edits now check an expected version, so a retry after the save is a `409`, not a replay -
as Work Orders' edits; the module's commands still take no request key (PF-1B). G5: the `409` keeps
`{"detail": "..."}`, the recorded exception retired by CS-06. The Commercial Offers row of `MCF_ADOPTION_RECORD.md` is
updated. No cross-module access added or removed; `BOUNDARY_EXCEPTION_REGISTER.md` is unchanged.

## Out of scope

The submitted-offer lock, the one-Base-Offer database rule and double-click messages (the next package, with the
owner's decisions above). Accounts, Leads, Opportunities, Work Order amendments and interactions (CS-05b). Versions on
pricing evidence, T&C attachments, credit reviews, submission evidence, revisions and customer responses: they are
appended or soft-removed, never edited in place.

## Tests

`backend/tests/test_cs05a_offer_stale_save.py`:

| Test | Proves |
| --- | --- |
| `test_every_offer_and_line_starts_at_version_one_and_never_below_it` | New rows are `1` on create, get and list; the database refuses `0` |
| `test_a_save_raises_the_version_and_returns_it` | `1 -> 2 -> 3`, in the response and the event |
| `test_a_save_from_a_form_opened_before_someone_elses_is_refused_and_changes_nothing` | Two tabs: `409` with the message, nothing written, no event, the first save stands |
| `test_a_stale_save_is_refused_before_its_content_is_judged` | A stale form whose values pass the schema is told to reload, not that they break a rule |
| `test_a_request_the_schema_refuses_is_refused_whatever_its_version` (offer and line) | The order the contract states: the schema's `422` first, nothing written |
| `test_a_stale_line_save_on_a_final_offer_is_told_the_offer_is_final` | For a line, the final offer's refusal comes before the version, as the contract states |
| `test_a_version_ahead_of_the_offer_is_refused_too` | Any other version, not only an older one |
| `test_a_save_without_a_version_is_refused` (3 cases) | Missing, `0` and `null` are `422`, nothing written |
| `test_a_version_alone_is_not_a_change` | The version is not a field of the offer |
| `test_marking_submitted_raises_the_version_so_a_form_opened_before_is_refused` | A tab opened on the draft cannot withdraw the submitted offer |
| `test_a_customer_response_that_sets_the_status_raises_the_version_and_one_that_does_not_leaves_it` | Only a write raises it |
| `test_two_saves_from_the_same_version_at_once_make_one_change` | Both wait on the offer lock; one saved, one refused |
| `test_a_line_save_raises_its_version_and_returns_it` | A line's `1 -> 2`, its amount, the event; the offer's version untouched |
| `test_a_line_save_from_a_form_opened_before_someone_elses_is_refused` | TB1-303's own quantity/rate case: refused, nothing written |
| `test_a_line_save_without_a_version_is_refused` | `422` |
| `test_a_line_amount_is_computed_from_the_line_it_writes` | Against a writer holding the line, the amount is the stored quantity times rate |
| `test_every_application_write_of_an_offer_or_a_line_raises_its_version` | The three writers found - by the table's name or any constant bound to it, in any letter case; each raises it but the new offer's code |
| `test_the_writer_scan_finds_a_writer_however_it_names_the_table` | The scan finds a planted writer in lower case, through another constant, or with `ONLY` |
| `test_no_orm_model_maps_an_offer_or_a_line` | No ORM model maps either table, so the SQL the scan reads is every writer |

The commands and counts of each run are in the continuity note and the acceptance record.
