# CS-05c - A submitted offer changes only through a revision; one active Base Offer held by the database; duplicates answered

## Status

**BUILT 10 October 2026**, on branch `fix/cs-05c-submitted-offer-lock`, built on `main` at `0666423` (Alembic head
`20260908_0052`, Slice 7D Part 5). Migration `20260908_0053`. Independent review (bounded packet) and
CI's `Required validation` decide the merge; the outcome is recorded in `docs/continuity/CS_05C_SUBMITTED_OFFER_LOCK.md`
and `docs/continuity/NEXT_STEPS.md`.

TB-1 corrective package CS-05, its third part: the rest of the Commercial Offer part, built before CS-05b (Accounts,
Leads, Opportunities, Work Order amendments, interactions). It closes TB1-301 parts (b2) and (d), TB1-304 for the
offer constraints (the selected basis rate, a T&C clause, the current credit review) and the deferred "Database-level
uniqueness for the one-active-Base-Offer rule". The TB-1 records under `docs/agent/tb-1/` are pinned by SHA-256 inside
themselves and are not edited; this record, the continuity note and `NEXT_STEPS.md` carry the findings' status from
here on, as every package since TB-1 has.

## Work package

```text
Title / package ID      CS-05c - submitted-offer lock, one-active-Base-Offer index, duplicate messages
Objective               A submitted offer's lines, prices, T&C, credit reviews and submission evidence change only while
                        a revision is open; the database holds one active Base Offer per Opportunity; a duplicate two
                        requests make at once is answered with the module's own 422/409, never a 500
Why this is next        The owner's decisions of 9 October 2026 (below), planned in CS-05a's records as the next package
Owning module           Commercial Offers (backend/app/modules/commercial_offers, the offer page)
Branch/worktree         fix/cs-05c-submitted-offer-lock, <a separate worktree>
Migration               20260908_0053 (down_revision 20260908_0052), assigned by the owner's brief
```

### Authority and required reading

Read in full: PBL's internal working instructions, `AGENTS.md`, PBL's local working notes; `docs/agent/tb-1/TB_1_CORRECTIVE_SLICE_REGISTER.md` (CS-05
and the sequence); `docs/agent/tb-1/TB_1_FINDINGS_REGISTER.md` (TB1-301, TB1-303, TB1-304);
`docs/agent/contracts/commercial-offer-contract.md`; CS-05a's records (`docs/agent/slices/cs-05a-offer-stale-save-protection.md`,
`docs/continuity/CS_05A_OFFER_STALE_SAVE_PROTECTION.md`, its acceptance record); `DEFERRED_REQUIREMENTS.md`
("Submitted document locking", "Database-level uniqueness for the one-active-Base-Offer rule", "Commercial Offer
revisions"); PR #97's record (`docs/continuity/TB1_301B_FINAL_OFFER_CONTENT_STAYS.md`). Searched and read the matching
sections: `MCF_ADOPTION_RECORD.md` (the Commercial Offers row), `BOUNDARY_EXCEPTION_REGISTER.md` (R3, the Opportunity
lock - unchanged), `CODING_STANDARDS.md` (section 9, logging a database error; "When a service outgrows one file"),
`TESTING_STRATEGY.md` section 11 (the harness's record sets), CS-04's migration `20260908_0049` (the pattern for a
migration that looks at the data first and stops naming what breaks the rule), `app/core/errors.py` (TB1-503). The
frozen `accepted-offer-to-work-order-handoff-contract.md` is unchanged; SHA-256
`0f16ff221e897f6199c352204a0ecced6f9a67f0c6695ad97c08c9dc2cd39080` before and after.

### The owner's decisions (9 October 2026)

1. "Do not allow submitted offer to be changed except by means of a revision."
2. The database must enforce the one-active-Base-Offer rule, for consistency.
3. A double click is quite possible, so a clear message is the right answer.

The brief scoped (1) to the five kinds of content #97 locked for final offers - lines (add, edit, cancel), pricing
evidence and the basis-rate choice, T&C clauses, credit reviews and submission evidence - and named TB1-304's other
modules (GSTIN, Lead conversion, PAN, amendment reference) and the deferred "prior submitted version" tamper evidence
out of scope.

## What was wrong

- **TB1-301 (b2).** #97 locked a final offer's content; a Submitted offer's lines, prices, T&C, credit reviews and
  evidence stayed editable, though the customer held the offer, so what was submitted and what the record showed could
  silently part.
- **TB1-301 (d).** Mark-submitted checks at least one active line and no Rejected / On Hold credit review. #97's lock
  already serialised it against those writers, but nothing stopped them right after it - (b2) made "submitted with no
  active line" reachable without a race.
- **TB1-304 (offer parts).** Where a unique index, not a lock, stops a concurrent duplicate, the losing request got an
  unhandled `500`. For the offer's three constraints #97's lock already made the check see the first request, so the
  rule is reached only by a writer that skips the lock - but nothing answered it if it was.
- **Deferred since Slice 9B.** The one-active-Base-Offer rule was the application's alone (a check under the
  Opportunity's row lock).

## What changed

**Verified first: how a revision works.** A revision opens only on a `SUBMITTED` offer, one at a time, under the
offer's row lock; it closes when marked resubmitted (citing existing submission evidence of the same offer) or
cancelled. So an open revision is the window in which a submitted offer is revised; the rule needs no new state. One
change made "only through a revision" true under concurrency: resubmitting and cancelling a revision took no lock on the
offer. They now take it before reading the revision (`_get_open_revision_context`), as opening one already did.

**Backend.**

- `services/common.py`: `_lock_offer_for_content_change`, which all eight content writers (nine routes) already called,
  now also refuses (`422`) an offer past Draft and Ready for Review that has no open revision, after the final-status
  refusal and under the same lock. `_refuse_duplicate` answers a unique violation on a named rule with the module's
  refusal and logs it by `database_error_fields`; any other error is raised as it came.
- `services/revisions.py`: resubmitting and cancelling a revision take the offer's row lock first.
- `services/offers.py`: creation answers the new index with the check's own refusal, naming the active offer
  (`_active_base_offer_refusal`, now shared by the check and the answer).
- `services/pricing_evidence.py`, `services/credit_reviews.py`: the selected-basis and current-review rules answered
  `409` (`CommercialOfferConflictError`); `services/tc_clauses.py`: the active-clause rule answered as the check answers
  (`422`, naming the clause).
- `routes.py`: `409` on the pricing-evidence create, select-basis and credit-review routes.
- `contract.py`: the four rules' names. `repository.py`: `lock_opportunity_row`'s docstring notes the index.
- `app/core/errors.py`: `database_error_fields`, the value-free part of TB1-503's log line, now shared; the request log
  line is unchanged.
- Migration `20260908_0053`: the partial unique index; the upgrade locks the offer table, looks for any Opportunity with
  two active Base Offers and, finding one, stops naming them, changing nothing.

**Frontend.** `offerStatus.ts`: `offerContentLocked(status, hasOpenRevision)` and `contentLockedNote(status)` (Vitest
tests). The offer page passes whether a revised offer is in progress; on a submitted offer without one, the line,
pricing, T&C, credit-review and submission-evidence forms give way to the note "change only through a revised offer.
Start a revised offer on the Submission tab, ..." (a line's edit form already open closes too); the revision panel says that a revised offer in progress lets them
change and that cancelling it does not undo a change.

**Tests and tooling.** `backend/tests/test_cs05c_submitted_offer_lock.py` (new; below). Two existing tests changed
because they relied on what is now refused: `test_a_final_offers_lines_prices_terms_and_evidence_can_no_longer_change`
(#97) added its line to the submitted offer directly and now does so through a revision it opens and cancels; and
`test_a_concurrent_rejection_defeats_an_in_flight_related_offer_creation` (Slice 9B) set a rejected offer back to
Accepted by a direct statement beside its replacement - two active Base Offers, which the index refuses - and now
closes the replacement first, which the race does not involve. No assertion changed. The core bundle gains its twelfth
record set, `submitted_lock_target` (a submitted offer with one line), `test_smoke_data_harness.py` counts its Account
(`11`, was `10`), and `e2e/tests/submitted-offer-lock.spec.ts` (new) finds its lines locked, starts a revised offer and
finds them open.

## Design choices

- **One helper, not eight checks.** Every content writer already called `_lock_offer_for_content_change` (#97), so the
  rule lives there and no writer can miss it. The lock comes first; the final-status refusal before the revision rule,
  so an offer accepted while a revision was left open is still final.
- **Fail closed past submission.** The rule refuses any status that is neither before submission nor final unless a
  revision is open - in practice `SUBMITTED`; `REVISED`, which nothing sets, is held the same, as the finding
  recommended ("outside DRAFT/READY_FOR_REVIEW").
- **The revision closes under the same lock.** Without it a change could read the revision open while a cancel was
  committing and land after it closed.
- **Answer the rule, keep the lock.** The lock still makes a double click get the check's answer; the rule's answer is
  the backstop for a writer that skips the lock. Each answer is the check's own where the check refuses (a clause, a
  Base Offer: `422`), and a `409` "at the same time ... reload" where one after another the second would have replaced
  the first (a basis rate, a credit review). Only the four named rules are answered.
- **Log the rule, never the row.** The database's DETAIL repeats the duplicated key; the log line carries the class,
  SQLSTATE, table, constraint and code path, reusing TB1-503's fields (`database_error_fields`).
- **The index states the service's rule exactly.** The migration holds its own copy of the inactive statuses (a
  migration must not change when the code does) and a test holds it equal to the contract's tuple and reads the
  index's definition. Both columns are NOT NULL, so the index and the check see the same rows.
- **Stop, don't choose.** An Opportunity with two active Base Offers is the business's to settle; the migration names
  them and changes nothing, as CS-04's did.

## MCF-001 and cross-module access

G4/G5: a duplicate refused by the database is answered with the check's `422` or a `409`, not a `500` - refused, not
replayed (the module's commands take no request key; PF-1B); the body keeps `{"detail": ...}`, the recorded exception
retired by CS-06. The Commercial Offers row of `MCF_ADOPTION_RECORD.md` is updated. No cross-module access added or
removed: the Opportunity row lock is R3's, unchanged; `BOUNDARY_EXCEPTION_REGISTER.md` is unchanged.

## Out of scope and stated limits

- TB1-304 in other modules - GSTIN, Lead conversion, a first PAN profile, an amendment's customer reference (CS-05b,
  PF-1B). The deferred "Prior submitted version lock/tamper evidence".
- **For the owner:** the offer's own fields the general update saves with the status unchanged (title, value,
  currency, dates, remarks, submission and outcome fields) stay editable on a submitted offer, as #97 left them on a
  final one. Whether they too should wait for a revised offer is a decision the brief did not take; recorded in
  `DEFERRED_REQUIREMENTS.md` ("Submitted document locking").
- Cancelling a revision does not undo what was changed while it was open; the events record each change and the
  cancellation.
- Marking a revision resubmitted does not repeat mark-submitted's checks (an active line, no credit hold).
- A write that bypasses the application can still change a submitted offer; the index holds only the Base Offer rule.

## Tests

`backend/tests/test_cs05c_submitted_offer_lock.py`:

| Test | Proves |
| --- | --- |
| `test_a_submitted_offer_refuses_every_content_writer_without_an_open_revision` | All ten requests (nine routes; a line's edit and cancel) `422` with the message; nothing written, no event |
| `test_an_open_revision_lets_every_writer_change_a_submitted_offer_until_it_is_resubmitted` | Each allowed while open; refused again after the revision is marked resubmitted |
| `test_a_cancelled_revision_closes_a_submitted_offer_to_changes_again` | Refused after a cancel; the change made while open stays |
| `test_a_final_offer_stays_refused_even_with_a_revision_left_open` | Accepted while a revision is open: every writer gets the final offer's refusal |
| `test_an_offer_before_submission_still_takes_changes` | Draft and Ready for Review unchanged |
| `test_mark_submitted_first_then_a_line_cancellation_is_refused` and the reverse | TB1-301 (d): both wait on the offer's lock; whichever is second is refused; never submitted with no active line |
| `test_mark_submitted_first_then_a_credit_hold_is_refused` and the reverse | The same for a Rejected / On Hold credit review |
| `test_a_change_waiting_behind_a_revision_s_cancel_is_refused`, `..._ahead_of_...` | Closing a revision takes the offer's lock: a change queued behind it is refused, one ahead of it is made |
| `test_two_attaches_of_one_clause_at_once_make_one_attachment` | A double click on Attach: one attachment, the second told it is attached |
| `test_a_basis_rate_selected_at_the_same_time_is_answered_409`, `test_a_selected_market_rate_added_...` | A writer that skips the lock holds a selected rate uncommitted; the request reaches the rule, waits, and is answered `409`; logged without the key |
| `test_a_credit_review_recorded_at_the_same_time_is_answered_409` | The same for the current credit review |
| `test_a_clause_attached_at_the_same_time_is_answered_as_already_attached` | The same for a clause: the check's `422` |
| `test_a_base_offer_made_active_at_the_same_time_is_answered_with_the_check_s_refusal` | The same for the new index: `422` naming the offer that became active |
| `test_a_database_error_on_another_rule_is_not_answered_as_a_duplicate` | Only the named rules are answered |
| `test_the_index_holds_exactly_the_service_s_rule` | The migration's name and statuses equal the contract's; the index's definition |
| `test_the_database_refuses_a_second_active_base_offer_and_nothing_else` | Each active status refused, each inactive one and each related offer allowed |
| `test_the_migration_stops_on_an_opportunity_with_two_active_base_offers_and_names_them` | The upgrade's look finds exactly the Opportunities the index would refuse and names each offer and status |

The commands and counts of each run are in the continuity note and the acceptance record.
