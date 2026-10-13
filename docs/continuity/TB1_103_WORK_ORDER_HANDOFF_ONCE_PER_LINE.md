# Work Order handoff: each offer line's quantity once, whole or in parts (8 October 2026)

TB-1 correction package 4: CS-04 part 1 (HOF-2), the corrective-slice register's "Recommended correction sequence" row
7. It closes the business half of TB1-103 with TB1-300 (group G-103) and TB1-301 part (c). Branch
`fix/cs-04-one-work-order-per-line`, built on `main` at `5e19123`. Alembic revision `20260908_0049`. The TB-1 records
(PBL's technical baseline review, not part of this copy) are not edited; this note, `NEXT_STEPS.md`, the contracts below and
dated reconciliation notes in the records that said otherwise carry the corrections.

Not in this package (CS-04 part 2, with CS-06): a request key that would replay a repeated request (this package
refuses it instead, by the customer's reference), the correlation id,
the line ids and amounts in the handoff's `CommercialOfferConvertedToWorkOrder` event, and the frozen contract's other
differences (TB1-103 part a).

*12 October 2026 (vendor baseline package B):* part 2's items c and d are done - the event lists each line handed
off with its quantity and amount, and the Work Order and both events carry the offer's version - by the frozen
contract's second amendment, which also records the request key and the correlation id as agreed behaviour to build
with PF-1B. The other differences are listed in `work-order-contract.md`. See `VENDOR_BASELINE_PACKAGE_B.md`.

## What was wrong

The handoff (`POST /api/work-orders/from-commercial-offer`) locked the offer and checked only that it was Accepted.

- **The same accepted lines could be handed off again** - a Create pressed after a timeout, a second tab, two people at
  once. TB-1 demonstrated two requests at once giving WO-001852 and WO-001853 for one line, and an existing test
  (`test_work_order_partial_award_allows_additional_shell_from_same_offer`) expected exactly that. Slice 6M had chosen
  no backend guard "by design" and hidden the Create button instead.
- **It handed off offers it was not meant for**: an accepted Change Quotation (which Slice 6O.2 cites on a Work Order
  amendment), and an Accepted offer whose latest customer response was on hold or pending - while the offer page said a
  Work Order could not be created.
- **An offer that already had a Work Order could be recorded as lost**, moving it to Rejected with nothing on the Work
  Order showing it (TB1-301 part c).

Credit exposure (CEX-001's selected-line allocation, transferred once), log sheets and billing will read Work Order
lines, so a line handed off twice would be counted and billed twice. Until now testers worked under the owner's
containment instruction: one Work Order per accepted offer, never a repeated request.

## The owner's decisions, 8 October 2026

Asked at the start of the package, each with a recommendation. The owner first chose all five recommendations, then
changed two after asking PBL (about 19:45 IST): a line **can** be split across Work Orders, and a Supplementary Offer
**may** make its own Work Order. The split is by the line's quantity - "4 cranes is a rough example; it just means the
quantity is, for example, 4 for a line".

1. **One accepted offer may give several Work Orders, and one offer line may be split across them by its quantity**,
   in whatever unit the line records it - quantity 4 as 3 on one Work Order and 1 on another, never more than 4 in all.
   A request for a line with nothing left, or for more than is left, is refused, naming the Work Orders that hold it.
2. **A Base Offer or a Supplementary Offer makes a Work Order; a Change Quotation never does** - it changes work
   already on a Work Order and is cited on an amendment. A Supplementary Offer may either make its own Work Order or be
   cited on an amendment of the existing one. A Work Order made from a Change Quotation before this package stays.
3. **The handoff waits for a final answer**: the offer's latest customer response must be the acceptance or award.
   **An offer with a Work Order is not recorded lost or rejected**, while no Work Order can be cancelled. Other
   responses stay allowed after a handoff; a non-final one holds back a further Work Order until an acceptance is
   recorded again.
4. **Records already on the pilots**: the migration stops and lists any offer line already on Work Orders past its
   quantity, changing nothing; the owner resolves them by hand. Before deploying, the owner runs a read-only check on
   each site (below).
5. **The frozen handoff contract** gets a dated amendment appended at its end, limited to these rules, with the change
   record its own "Change Control" section asks for, the hash before it, and the same amendment in the two planning
   documents that section names.

And the safeguards ADR-023 leaves to engineering, built without asking: the offer row lock the handoff and customer
responses already share; a database rule that holds the total when two requests arrive at once or a writer skips the
handoff (together they never pass the line's quantity); a clean `409` rather than a `500`; the offer page's reasons made to say what the server refuses.

**After review round 3 (8 October 2026), the owner added a sixth rule.** Round 1 had found that two simultaneous
requests for part of a line, both fitting, were both made; the records first stated it as a limit. The owner chose
to fix it instead: "if a WO is being entered, we will have a ref no. even if it is a LoI". So the customer's Work
Order reference is **required**, and **one offer never has two Work Orders with the same reference** (compared
without case or surrounding whitespace, tabs and line breaks included; the same reference may be on another offer's
Work Order, since one customer
order can cover a Base Offer and its Supplementary Offer). One customer order makes one Work Order: a repeat -
Create pressed again, a second tab, two people at once - is refused, naming the Work Order. The request key
(replaying instead of refusing) stays in part 2.

## What changed

**Backend.**

- `work_orders/services/handoff.py`: after the existing status and Account checks, `_check_offer_may_be_handed_off`
  refuses a Change Quotation and a latest response that is not `ACCEPTED_AWARDED` (`422`). `_work_order_parts` works
  out, under the offer lock, how much of each selected line this Work Order takes - the quantity asked
  (`selected_offer_line_quantities`) or all that is left - and refuses with `WorkOrderHandoffConflictError` (`409`) a
  line with nothing left or less than asked, naming each Work Order and its quantity. With no line chosen, a line with
  nothing left is passed over, and the request is refused only when nothing at all is left. A part's amount is the line's amount up to
  the end of the part less its amount up to its start, each the rate times the quantity so far rounded to the paisa,
  so the parts add up to the line's amount exactly and none is below zero (review of my own first version, which
  rounded each part alone, found parts a paisa off - or below zero at a rate of 0.01). If the database rule refuses an insert anyway,
  the request gets the same `409`.
- `work_orders/repository.py`: the handoff context reads the offer's purpose and its latest customer response, latest
  by the date the customer responded and then by entry - the order the offer's own lifecycle view uses -
  and `list_offer_line_work_order_parts` reads what Work Orders already hold of each line.
- `work_orders/schemas.py`: `selected_offer_line_quantities` (`[{offer_line_public_id, quantity > 0}]`), optional. The
  response is unchanged.
- `work_orders/contract.py`: the two purposes that may be handed off and the outcome required, spelled with the
  Commercial Offer module's own constants.
- `commercial_offers/service.py`: a `REJECTED_LOST` response is refused (`422`) while the offer has a Work Order,
  under the same row lock the handoff takes. The lifecycle view adds four reasons: a Change Quotation, an Accepted
  offer with no customer response, an Accepted offer whose latest response is not the acceptance (the handoff's own
  words, `latest_response_not_accepted_reason` in `commercial_offers/contract.py`, listed whatever else blocks it -
  review round 7), and every active line already on Work Orders in full; and `line_handoff` -
  each active line's quantity, what Work Orders hold of it, what is left and which Work Orders, counted in one
  statement (`list_offer_line_handoff`; review round 2), which the "in full" reason and the Create page read.
- Migration `20260908_0049`: `crm_work_order_line_within_offer_quantity` - before a Work Order line is written or its
  quantity or offer line changes, it locks its offer line and refuses a total past the line's quantity (a part of
  zero or less was already refused, by `ck_crm_work_order_line_quantity`); `crm_commercial_offer_line_keeps_its_work_orders`
  - an offer line's own quantity cannot go below what its Work Orders hold, and an offer line a Work Order holds
  cannot move to another offer (review round 4), for any writer (review round 2; the
  application already never changes an Accepted offer's lines, #97), under the same row lock, with the same rule
  name in its refusal; `crm_work_order_line_from_its_offer` - a Work Order line comes from a line of its own Work
  Order's offer, and a Work Order cannot move to another offer while its lines come from its own (review round 3);
  `crm_work_order_not_from_change_quotation` - a Work Order written or moved onto a Change Quotation is refused, and
  `crm_commercial_offer_keeps_its_work_orders_purpose` - an offer with a Work Order cannot become a Change Quotation
  (review round 3); `crm_work_order_has_customer_reference` and the unique index
  `ux_crm_work_order_customer_reference` - a Work Order written carries a customer reference, used once per offer
  (the owner's rule after round 3). Each pair takes its locks in one order - the Work Order line a share lock on its Work Order, the
  Work Order a share lock on its offer - so a move or a change of purpose waits for a write under way and counts it. The upgrade first locks the Work Order and line tables against writes (review round 2),
  then looks for any offer line already past its quantity, or Work Order line from another offer, and stops, listing
  them, then installs the rules. A Work Order made from a Change Quotation before this revision is left alone, even
  when its other columns are updated: a writer under way
  finishes first and is counted; a later one waits for the rules.

**Frontend.**

- The Create Work Order page requires the customer's Work Order reference (the owner's rule after round 3), and
  shows, for each line, what Work Orders already hold of it and what is left, as the
  server counts it (the lifecycle view's `line_handoff`; review round 1 found the page reading only the first 20
  Work Orders, round 2 that paging could race a creation), and compares what is typed with it in exact hundredths
  (`handoffQuantities.ts`: a JavaScript number loses the hundredth past about 9 x 10^15); a line on
  Work Orders in full cannot be ticked; a ticked line has a quantity box, filled with what is left. The offer's own
  reasons (the lifecycle view) and any refusal appear beside the Create button. After a Work Order is created the page
  reads the offer again, so what is left is current.
- The offer page offers "Create Work Order" whenever the lifecycle view allows it - after the first, as "Create another
  Work Order" - now that the server holds the rule, not only the screen. Its reasons heading reads "A Work Order cannot
  be created:" (it said "yet", which a Change Quotation never is), and the amber box under the Work Order list shows
  only while no Work Order exists. The note under the existing Work Orders says another takes only what is not on a
  Work Order yet, and points to "Create another Work Order" when the page shows it (`workOrderActions.ts`, which
  also names the link; review round 8 found it still saying a second Work Order was "not offered here").

**Tests and harness.**

- `backend/tests/test_cs04_handoff_once_per_line.py`, new. The quantity: parts never past it, what is left taken with
  no line chosen, quantity validation, the parts' amounts adding up to the line's, the lifecycle view counting 21 Work
  Orders. The customer reference: required; a reference already on a Work Order of the offer refused (in another case,
  with spaces), allowed on another offer; two requests at once for one customer order give one Work Order and one
  refusal, two customer orders at once for parts that fit are both made, two whole-offer requests at once give one.
  Which offers: a Change Quotation refused, a Supplementary Offer handed off, the latest response, no lost after a
  handoff. The database rules, each against a direct write and, where two writers can meet, at once: the quantity
  (two writers skipping the offer lock), an offer line shrinking under a Work Order line written at the same time, a
  Work Order line from another offer's line, a Work Order moved to another offer, an offer line moved to another offer
  while a Work Order holds it (both orders of a concurrent write and move), an offer with a Work Order made a Change
  Quotation (directly and at once), a Work Order written without a reference or with one already used, and the
  reference index under two writers skipping the offer lock. The whitespace (round 5): every character the application
  strips is blank to the database and is ignored around a reference by the index and the handoff's lookup. The
  migration's look before it adds the rules, and this note's pilot checks 1, 4 and 5 as printed, find the same on data
  the rules would refuse, a reference repeated with a tab and an ideographic space around it included (round 6).
- `frontend/src/pages/work-orders/handoffQuantities.test.ts` covers the page's choices and checks against the server's
  figures; the Playwright spec `accepted-offer-handoff.spec.ts` fills the required reference and checks the page after
  a creation. `frontend/src/pages/commercial-offers/workOrderActions.test.ts` holds the offer page's
  label and its note together, with a Work Order holding part of the offer and with none offered (round 8);
  `existing-work-order-traceability.spec.ts` checks the note on a fully handed-off offer.
- Changed to the decided rule, not weakened: `test_work_order_partial_award_allows_additional_shell_from_same_offer`
  became `..._for_what_is_left` - the same request again (the same customer order, typed in another case with spaces)
  is refused naming the first Work Order, a second customer order for the same 4 is made, a third for 4 more is refused
  with 2 left, the remainder taken whole, and the whole line again refused. Three "a line of another Work Order is not
  found" tests (7C, 7D, WRR-001) make their second Work Order from a Supplementary Offer through a new shared helper,
  `create_test_supplementary_work_order`; every test handoff that should succeed sends a customer reference of its
  own; the lifecycle test expects "every line ... in full" once the only line is handed off; the TE-6 surface pin lists
  `WorkOrderHandoffConflictError`; `existing-work-order-traceability.spec.ts` checks the new reason instead of the
  absence of "fully handed off".
- The smoke-data harness's one Work Order builder (`tooling/smoke_data/builders.py` `create_work_order`) supplies an
  invented customer reference, unique to each call; nothing else in it changed. No scenario hands off a line twice, a
  related offer, or after a non-final response (checked across every scenario).

**Records.** The frozen contract's dated amendment; `work-order-contract.md` ("CS-04 part 1"),
`commercial-offer-contract.md` (customer responses; the lifecycle view's reconciliation); the payload spec and the
parallel-agent contract under `docs/planning/`; Slice 6M's "no backend duplicate guard, by design" reconciled;
`DEFERRED_REQUIREMENTS.md` ("Partial award and multiple WO handling"); `CONTRACT_REGISTRY.md`; the frozen-contract rule
in PBL's internal working instructions and `AGENTS.md` (the hash now lives in `NEXT_STEPS.md`).

## Stated limits

- **A repeated request is refused, not replayed.** Review round 1 found that two simultaneous requests for part of a
  line both fitting were both made; the owner chose to fix it, not state it: the customer's Work Order reference is
  required and used once per offer, so the repeat carries the same reference and is refused, naming the Work Order.
  The person then opens that Work Order; CS-04 part 2's request key would answer with it directly. A person typing a
  different reference for the same customer order is not something the system can tell from a second order.
- **Splitting is by the line's quantity.** A line written as "3 Mon" splits in months; splitting it by number of
  machines would need the offer line to hold that number.
- **Splitting by period** - the same quantity on one Work Order for one period and on another for the next - is a
  future feature (the owner, 8 October 2026: rare). It loosens today's rule, so it needs no data cleanup when added;
  `DEFERRED_REQUIREMENTS.md` says what it takes. Meanwhile a line counted in machines is quoted as two lines, or the
  second order comes as a Supplementary Offer.
- **The unawarded balance of a line is not recorded** (CEX-001's worked example, step 4), and **a Work Order cannot be
  cancelled**, so its quantity never comes back.
- "Latest response" is by the date the customer responded, as the offer page counts it: an acceptance entered with an
  earlier date than a pending response already recorded leaves the pending one latest; record the acceptance again with
  the right date.
- Existing Work Orders made from a Change Quotation, and offers recorded lost after a handoff before this package, stay
  as they are.
- The database rules govern writes made outside the application too, for what they cover: an offer line's quantity
  on Work Orders (and the offer line neither shrinking under them nor moving offers), a Work Order line from its own
  offer, no Work Order from a Change Quotation and no offer with one becoming one, and a customer reference on every
  Work Order written, used once per offer. They do not re-check a Work Order made before this revision. **The
  accepted status, the latest customer response and no "lost" after a handoff are the application's rules only**,
  held under the offer's row lock, which every application path that reads or changes them takes; a writer
  bypassing the application could, for example, write a Work Order for a Draft offer (review round 5).

## Before deploying to a pilot

Run on each site's database (read-only; it changes nothing). Checks 1, 4 and 5 must be empty, or the migration stops;
checks 2 and 3 are for information.

```sql
-- 1. Offer lines on Work Orders for more than their quantity (must be empty before deploying)
SELECT co.offer_code, col.line_number, col.quantity,
       string_agg(wo.work_order_code || ' (' || wol.quantity || ')', ', ' ORDER BY wo.id) AS work_orders
FROM crm_work_order_line wol
JOIN crm_work_order wo ON wo.id = wol.work_order_id
JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
JOIN crm_commercial_offer co ON co.id = col.commercial_offer_id
GROUP BY co.offer_code, col.line_number, col.quantity, wol.commercial_offer_line_id
HAVING SUM(wol.quantity) > col.quantity;
-- 2. Work Orders made from a Change Quotation (they stay)
SELECT wo.work_order_code, co.offer_code
FROM crm_work_order wo JOIN crm_commercial_offer co ON co.id = wo.commercial_offer_id
WHERE co.offer_purpose = 'CHANGE_QUOTATION';
-- 3. Offers recorded lost that have a Work Order (they stay)
SELECT co.offer_code, string_agg(wo.work_order_code, ', ' ORDER BY wo.id) AS work_orders
FROM crm_commercial_offer co JOIN crm_work_order wo ON wo.commercial_offer_id = co.id
WHERE co.offer_status_code = 'REJECTED' GROUP BY co.offer_code;
-- 4. Work Order lines made from another offer's line (must be empty before deploying)
SELECT wo.work_order_code, wol.line_number, co.offer_code AS line_offer
FROM crm_work_order_line wol
JOIN crm_work_order wo ON wo.id = wol.work_order_id
JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
JOIN crm_commercial_offer co ON co.id = col.commercial_offer_id
WHERE col.commercial_offer_id <> wo.commercial_offer_id;
-- 5. One customer reference on two Work Orders of one offer (must be empty before deploying), compared as the
--    migration compares them: without case, and without the whitespace around them that the application strips
SELECT co.offer_code, MIN(wo.customer_wo_reference) AS reference, string_agg(wo.work_order_code, ', ' ORDER BY wo.id)
FROM crm_work_order wo JOIN crm_commercial_offer co ON co.id = wo.commercial_offer_id
WHERE COALESCE(wo.customer_wo_reference, '') !~ '^[\t\n\v\f\r\x1c-\x1f \x85\xa0  -     　]*$'
GROUP BY co.offer_code, wo.commercial_offer_id, lower(regexp_replace(wo.customer_wo_reference,
  '^[\t\n\v\f\r\x1c-\x1f \x85\xa0  -     　]+|[\t\n\v\f\r\x1c-\x1f \x85\xa0  -     　]+$', '', 'g'))
HAVING COUNT(*) > 1;
```

A test runs checks 1, 4 and 5 as printed here, and the migration's own look, on the same data - two references
differing only by a tab and an ideographic space included - and requires both to find the same
(`test_the_note_s_pilot_checks_find_what_the_migration_stops_on`, review round 6; before it, check 5 compared with
`btrim()`, which removes spaces only, and could report nothing where the migration would stop).

No route has ever written check 4's case (the handoff takes lines from the offer it hands off). Check 5 can find
something only if testers typed one reference twice on one offer (in either case, or with whitespace around it); Work
Orders with no reference, or with whitespace alone, are left alone. If
check 1, 4 or 5 lists anything, the owner decides which Work Order keeps each line; the rest is removed by hand, then the
deploy goes ahead. The practice data seeded on both sites hands no line off twice (checked across every scenario).

## Independent review

Reviewed independently, one bounded packet per round, until accepted. The rounds' findings are PBL's internal
record; every finding was corrected, and the checks below ran on the corrected code.

## Checks

On the worktree stack (PostgreSQL 17; the backend hashing at 10,000 rounds, as CI's backend job). The full backend
regression is CI's backend job, by the owner's direction; each run below names the code it ran on.

| Check | Code | Result |
| --- | --- | --- |
| Frozen handoff contract SHA-256 | `main` `5e19123`; each candidate | before `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`; after: in `NEXT_STEPS.md`. Every candidate begins with the frozen file's exact bytes |
| Every touched test file, whole (38 files) | uncommitted, before `2197dfb`'s part-amount rule | 1,683 passed, 1 skipped, 0 failed |
| The same 38 files | `2197dfb` (round 1's candidate) | 1,687 passed, 1 skipped, 0 failed |
| The same 38 files | `36572e8` (round 2's corrections) | 1,690 passed, 1 skipped, 0 failed; not rerun whole on round 3's corrections (focused rows below; CI runs the full regression) |
| Focused: the new test file, `test_work_orders_api.py`, the lifecycle test, `test_commercial_offer_related_offers_api.py` | each round's corrections, before commit | all passed; the new file 19 tests after round 3 |
| Undo proofs (each guard removed, its tests run, the file restored by checksum) | each round's corrections | all fail as they should: the handoff's quantity check, the database rules, the Change Quotation check, the latest-response check, the lost guard, the view's two new reasons, the cumulative part amount, the lock with the quantity rule, round 3's two rules; the migration's lock by the race below |
| Migration, empty database | round 3 | upgrade, downgrade, upgrade |
| Migration, a line on two Work Orders past its quantity | round 3 | stops, naming offer, line and Work Orders, changing nothing; once resolved by hand, upgrades; then one more unit, or lowering the offer line, is refused |
| Migration, a writer adding an over-allocation as the upgrade starts | round 2; again with the reference rule | the upgrade waits for it and stops; without the lock it installed the rules over the bad line |
| Migration, a Work Order line from another offer; one reference on two Work Orders of one offer | the reference rule | each stops the upgrade, naming it; corrected by hand, it upgrades, and Work Orders without a reference stay and can still be changed |
| The customer reference rule (after round 3) | uncommitted, then the PR | the new file and `test_work_orders_api.py`: 30 passed; undo proofs below; frontend clean, 578 passed; Playwright 37 passed, 9 skipped, 0 failed with the reference filled in |
| Frontend typecheck, tests, build | round 2 | clean; 29 files, 578 passed; built |
| Playwright, full suite | round 2 (`36572e8`'s tree) | 37 passed, 9 skipped, 0 failed; the handoff spec checks the page after a creation |
| Committed-credential check; contract fixtures; CRLF | round 2 | no findings; all passed; none |
| Round 5's corrections | uncommitted, then round 6's commit | the new file (now 26 tests), `test_work_orders_api.py` and the TE-6 surface test at 10,000 rounds: 40 passed; undo proofs U15-U17 fail as they should; the migration check, all five sections, passed; the 38 touched files whole at 10,000 rounds: 1,699 passed, 1 skipped, 0 failed |
| Round 6's corrections | uncommitted, then round 7's commit | the new file whole at 10,000 rounds, with the note copied into the container: 28 passed. Undo proofs: U18, the note's check 5 back to `btrim()`, fails the note test (it finds nothing on CO-A); U19, the migration's look back to `btrim()`, fails the migration test; the migration file restored in the container by SHA-256. Committed-credential check and contract fixtures: no findings, all passed |
| Round 7's corrections | uncommitted, then round 8's commit | the new file whole, the TE-6 surface test and the lifecycle test at 10,000 rounds: 36 passed; undo proof U20 (the view's new reason removed) fails the new test; the 38 touched files whole at 10,000 rounds on `2272abb`: 1,702 passed, 1 skipped, 0 failed |
| Round 8's corrections | uncommitted, then round 9's commit | frontend typecheck clean, 30 files and 581 tests passed, built; undo proof U21 (the note put back to "not offered here"): two of the new file's three tests fail, the file restored by SHA-256. The Playwright line is checked by CI (no local Playwright while other lanes run, by the owner's direction) |
| CI (`Required validation`, with the full backend regression) | `2197dfb` | all checks green; later commits: the pull request |
