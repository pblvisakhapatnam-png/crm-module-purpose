# Slice 9F - Commercial Offer versions

## Status

**IMPLEMENTED and MERGED, 11 October 2026** (pull request #120, merge commit `cfa11d73`; reconciled 12 October 2026 -
this line read "owner integration pending"). Branch `crm/slice-9f-offer-versions`, migration `20260908_0054`. The design record below
is retained because it contains the owner's decisions and the implementation boundaries. The "check" notes were
verified during implementation; the as-built reconciliation and evidence are at the end of this document.

## The owner's decisions (10 October 2026, in chat; to be written into the records by this package)

1. "Once an offer has been submitted, it should not be editable. A new version (we can show a copy so that the entire
   offer need not be keyed in) with appropriate changes should be the way to make changes to a submitted offer."
2. Numbering: the same offer number with a version - CO-000123 v1, v2, v3.
3. The copy carries the offer's details (title, mode, type, value, currency, dates, remarks) and also: its active lines,
   its T&C clauses, its market rates with the chosen basis rate, and its current credit review. Not copied (told to the
   owner as an assumption): submission evidence and quotation documents - each version is sent afresh.
4. When the new version is sent, the old one becomes read-only history, shown "Replaced by v2". The customer's reply,
   a Work Order and everything after go on the latest version only.
5. A new version may be started any time after submission, until the customer accepts or the offer is withdrawn or
   closed; one in preparation at a time; it can be abandoned, leaving the sent version as it was.
6. Assumed and told the owner, no objection: withdrawing or closing a submitted offer stays possible; changes after the
   award stay on Work Order amendments and Change Quotations.

This replaces CS-05c's model (merged `65d47f3`), where a submitted offer's content is changed in place while a Slice 6K
revision is open. CS-05c's row locks and duplicate answers stay.

## Implemented design (Design A: each version is its own offer row)

Chosen over keeping one row with snapshots, because abandoning a version is then trivial (the sent row was never
touched) and the old version stays exactly as sent with its own lines, T&C, evidence and quotations.

**Data (migration 0054).**
- `crm_commercial_offer.version_number INTEGER NOT NULL DEFAULT 1` (check `>= 1`) and
  `previous_version_offer_id INTEGER NULL REFERENCES crm_commercial_offer(id)` (the version it was copied from).
  Optional `version_reason` (a code from `COMMERCIAL_OFFER_ALLOWED_REVISION_REASONS`) and `version_note`.
- Versions share `offer_code`: replace `ux_crm_commercial_offer_code_not_null` (unique `offer_code`) with unique
  `(offer_code, version_number) WHERE offer_code IS NOT NULL`; a copy sets its predecessor's code instead of the
  `CO-` + id code `insert_commercial_offer` writes (check that function's code update).
- A replaced version gets the seeded status `REVISED` (nothing sets it today; check `workflow_status` holds it and is
  active). An abandoned version needs a status that reports do not count as a lost or withdrawn offer - check how
  `reports/repository.py` buckets statuses before choosing between a new seeded `ABANDONED` status and an existing one.
- Recreate 0053's index so a version in preparation and a replaced one do not count:
  `WHERE offer_purpose = 'BASE' AND offer_status_code NOT IN ('WITHDRAWN','REJECTED','CLOSED','REVISED',<abandoned>)
  AND (previous_version_offer_id IS NULL OR offer_status_code NOT IN ('DRAFT','READY_FOR_REVIEW'))`. Change
  `COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` and `get_existing_actionable_commercial_offer_for_opportunity`
  to match exactly; the 0053 test that holds the migration's statuses equal to the contract's must follow.

**Commands.**
- `POST /api/commercial-offers/{public_id}/versions` (Sales through the existing `COMMERCIAL_OFFER_UPDATE` permission;
  confirmed against the authorization catalogue and added to `POST_BASELINE_NEW_ROUTES`): only on a `SUBMITTED` offer that is its
  series' latest, with no version in preparation; under the offer's row lock. Copies as in decision 3 into a new row
  (`DRAFT`, `version_number + 1`, same opportunity, Account, purpose, base offer, related Work Order and customer request
  fields); new line, attachment, evidence and review public ids; one event `CommercialOfferVersionCreated`.
- `POST /api/commercial-offers/{public_id}/abandon-version`: only on a version in preparation; event
  `CommercialOfferVersionAbandoned`.
- Sending a version (`mark-submitted` on v2) also moves its predecessor `SUBMITTED -> REVISED`, in one transaction;
  refuse if the predecessor is no longer `SUBMITTED`. Lock order always older version first (look up the predecessor,
  lock it, then lock v2) - check every path for the reverse order.
- While a version is in preparation, refuse on the sent version: a customer response, withdraw and close ("abandon or
  send version N first") - or decide to abandon it automatically; refusing is the simpler, explicit choice.
- `GET /api/commercial-offers/{public_id}/versions`: the series, oldest first. Offer responses gain `version_number`,
  `previous_version_offer_public_id`, `replaced_by_offer_public_id` and `replaced_by_version_number` (additive).

**Freeze.** `_lock_offer_for_content_change` refuses every status outside Draft and Ready for Review, open revision or
not (drop CS-05c's revision exception and its tests' "allowed while open" halves). The general update on any status
outside Draft and Ready for Review accepts only the status move (Submitted -> Withdrawn/Closed, as now) and the outcome
date and remarks; any other field is `422` "... make a new version". Update the 6M.1 section's rule 4.

**Slice 6K revisions.** With content frozen they are metadata only again. Proposed: keep the routes and records; the
page stops offering "Start revised offer" and offers "Make a new version" instead; consider refusing new 6K revisions
with a pointer to versions (an API change - record it). Lifecycle guidance texts that say "open a revision" change to
"make a new version"; add `can_make_new_version` (additive).

**Quotations.** `quote_reference` is `offer_code/V<n>` per offer row, so v2's first quotation would repeat v1's
"CO-000123/V1". Use `CO-000123 v2/V1` for versions above 1 (stored per document; v1 unchanged). Do not change the
snapshot's shape (stored fingerprints would all read stale).

**Knock-on checks.**
- Reports (`reports/repository.py`): replaced and in-preparation versions must not be counted twice in the pipeline.
- The test-data harness: `_build_revised_resubmitted_offer` and the UAT seed's `revision_requested` stage record
  submission evidence while a 6K revision is open - refused once the exception goes. Rewrite both on versions, and
  count records in `test_smoke_data_harness.py`. TE-8 (PR #117) also edits `scenarios.py`: expect a merge.
- The page: versions card (list, "Make a new version", "Abandon this version", "Replaced by v2" on old ones), header
  edit form disabled on a submitted offer, list rows labelled with the version. Playwright: extend
  `submitted-offer-lock.spec.ts` to make v2, change a line, send it, see v1 replaced.
- The frozen handoff contract is not touched: the handoff works on the accepted (latest) version's own row and lines.
- Records: offer contract (new section; reconcile CS-05c's), `DEFERRED_REQUIREMENTS.md` ("Submitted document locking"
  closes for the header; "Commercial Offer cloning and immutable version snapshots" and "Prior submitted version
  lock/tamper evidence" largely resolved), MCF row, slice/acceptance records, NEXT_STEPS, a continuity note.
- TE-8: Tester 1's steps 19-23 are written against this flow after it merges.

## As built

The design above was implemented without changing the frozen Accepted Commercial Offer -> Work Order contract.

- Migration `20260908_0054` adds the version lineage fields, `ABANDONED`, the per-code version uniqueness rule and
  the refined active-Base-Offer rule. Downgrade is refused once version history exists; an empty-history downgrade
  restores the earlier indexes and removes only the status row seeded by this migration.
- `GET /versions`, `POST /versions` and `POST /abandon-version` use the existing Commercial Offer read/update
  permissions. The two commands are backend-authorized, row-locked and event-producing. Version numbers use the
  highest number ever allocated, so an abandoned number is never reused.
- A copy receives new public identities for active lines, pricing evidence, active T&C attachments and the current
  active credit review. Submission evidence, quote documents, customer responses and legacy revision rows remain on
  the version where they occurred.
- A submitted row is immutable commercial history. Only withdrawal/closure and outcome notes remain legal on the
  submitted row. Sending the later version retires its direct predecessor to `REVISED` atomically; customer outcomes
  and Work Order handoff remain available only on the latest live version.
- New Slice 6K in-place revision cycles are refused with guidance to make a new version. Existing OPEN revision rows
  remain listable and may still be closed or marked resubmitted so pre-9F data is not stranded.
- The Commercial Offer page lists the whole series, creates and abandons preparation versions, identifies replacement
  links and removes the retired in-place-revision creation form. List and detail labels include `vN`.
- A quotation generated from version 2 or later includes the Commercial Offer version in its reference, for example
  `CO-000123 v2/V1`; version 1 references remain unchanged.
- Open-offer reports exclude later Draft/Ready preparation rows and exclude `REVISED`/`ABANDONED`, so a live series is
  counted once. The TE-1 revised/resubmitted and UAT scenarios now use immutable versions.

## Source and contract reconciliation

The governing source suggestion was the owner-approved 9F brief itself. Its immutable-copy outcome is compatible
with the frozen handoff contract because each accepted version keeps its own stable offer and line identities; no
handoff field or payload changed. The pre-9F Slice 6K/CS-05c in-place mechanism was an active implementation contract,
not a frozen cross-module contract. It remains as read/close compatibility only and is explicitly superseded for new
commercial changes. No source requirement, mandatory control, authorization boundary, module ownership or statutory
rule was weakened.

## Validation record

Completed before independent review:

- focused backend regression: `282 passed`;
- final post-Round-4-correction backend subset against the rebuilt image: `129 passed`;
- Slice 9F version tests after the final migration/test additions: `10 passed`;
- post-hosted-correction Slice 9F plus Commercial Offer API set on the rebuilt image: `58 passed`;
- post-hosted-backend-correction Slice 9B hardening file: `93 passed`; full local backend regression:
  `3541 passed, 2 skipped`;
- targeted TE-1 smoke-data regression: `8 passed`;
- frontend typecheck: pass;
- frontend Vitest: `31` files / `602` tests passed after Round 4 corrections;
- frontend production build: pass (the existing large-chunk advisory remains non-blocking);
- targeted Chromium flow `submitted-offer-lock.spec.ts`: `1 passed`, with smoke-data and login-event cleanup passing;
- post-hosted-correction targeted Chromium flows `submitted-offer-lock.spec.ts` and
  `terminal-status-guard.spec.ts`: `2 passed`, with smoke-data and login-event cleanup passing;
- Alembic current/head: `20260908_0054`; empty-history `0054 -> 0053 -> head` cycle: pass;
- downgrade refusal with real version history: covered by the Slice 9F test;
- contract fixtures (`7` candidates), tracked-secret scan (`2242` proposed-tree files), `git diff --check` and the
  frozen handoff hash: pass;
- the repository script-unit suite has eight reproducible Windows-only TE-5 backup/cron failures: Git Bash selects its
  bundled `df.exe` instead of the test's extensionless fake. The unchanged module reproduces the same result; Linux CI
  remains authoritative for it;
- full backend regression and full Playwright remain CI-owned for this package, per the work-package handoff.

Structured self-review traced the version state transitions, lock order, copy boundary, report de-duplication,
permissions, events, migration upgrade/downgrade and frozen handoff. It corrected one stale Slice 6K compatibility
docstring/import cluster.

Independent review round 1 returned `CORRECTION_REQUIRED`. The candidate now prevents a preparation version from
escaping through general withdrawal/closure, keeps submitted withdrawal/closure and outcome notes available in the
UI without unlocking commercial content, aligns lifecycle guidance with the authoritative preparation-version guard,
records predecessor replacement on the predecessor's audit history, derives preparation-report status filters from
the module contract, and corrects the route permission documentation. Those corrections were revalidated and
re-reviewed in Round 3.

Independent review round 2 received the complete corrected candidate but reached its agreed 15-minute cap without a
verdict. It is evidence of neither acceptance nor rejection; a leaner bounded packet was used for Round 3.

Independent review round 3 returned `CORRECTION_REQUIRED`. It confirmed the Round 1 corrections and found that
editable submission-header metadata could incorrectly make a preparation row look sent, and that `REVISED` /
`ABANDONED` guidance could still be overwritten by an older non-final customer response. The candidate now uses
controlled lifecycle status for sent/replacement identity, refuses manual submission metadata on preparation
versions, gives both historical statuses explicit inactive guidance, tolerates an unchanged status key with an
allowed outcome-note update, and reconciles the contract wording, event inventory and deferred downstream `vN`
labels. The focused backend, frontend and targeted Chromium gates passed after correction; Round 4 re-reviewed them.

Independent review round 4 returned `CORRECTION_REQUIRED` after confirming all Round 3 fixes and the lock/atomicity
paths. It found that general update still accepted outcome notes on `REVISED`/`ABANDONED` history and that a Draft
quotation belonging to either status could still be approved for issue. Both history statuses are now fully
read-only, quotation approval reports and enforces the same refusal, version creation uses contract status constants,
the post-transition UI disables every remaining control, and changed-fields coverage proves a normal preparation
header save omits submission metadata. The focused backend, frontend and expanded Chromium flow pass after correction;
the next bounded review was run on that corrected candidate.

Independent review round 5 returned `ACCEPTED` with no blocking or material findings against candidate diff SHA-256
`47b8d045e779ab090146fca064ae154bd7398ff5bd58b3d4508f9c5dd1504974` (packet SHA-256
`e98f56651273772a6b43fa921b8af63dc8e6aec63fdc5d812825146daa6d316a`). It independently confirmed the six Round 4
corrections, transaction/lock ordering, predecessor-first replacement, monotonically increasing version numbers,
status-derived sent/replacement identity, report de-duplication, migration downgrade guard and copy boundary. Its four
advisory-only observations are preserved under "Commercial Offer versions and legacy revisions" in
`DEFERRED_REQUIREMENTS.md` as `9F-R5-A1` to `9F-R5-A4`. Adding that mandatory durable advisory record changed only
documentation after the Round 5 snapshot; Round 6 reviewed the complete documentation-reconciled candidate, so Round
5 is not used to bind the changed snapshot.

Independent review round 6 returned `ACCEPTED` with no blocking or material findings against documentation-reconciled
candidate diff SHA-256 `69049fa6ecf33480f64ed1c8aa500bfa37bf6fbf7d6c823ede200048cb4202e4` (packet SHA-256
`f98b6ca0beca1102a3de51fd79760fa39a7fa3519c07112baff2701099d1705b`). It reconfirmed the runtime invariants and
advisory preservation. Its four advisory-only documentation findings are corrected here: `9F-R5-A3` and `A4` now
describe the observed messages precisely, the contract lists `REPLACED_HISTORY` and `ABANDONED_HISTORY`, and obsolete
present-tense review status phrases are historical. Those record-only corrections changed candidate identity and were
reviewed in Round 7; Round 6 is not used to bind the changed snapshot.

Independent review round 7 returned `ACCEPTED` with no blocking or material findings against candidate diff SHA-256
`8509481f8c6c68b1b1b8c8eccbaacb8f160eb32a7e7fd9a1da26c7adc61ba313` (packet SHA-256
`9aa7e351730978c7961ab462ecda2072c4d838766c5184d47970d01a50d7250d`). It verified every Round 6 correction and
again found no runtime defect. Its sole advisory was that a few Round 2/Round 5/Round 6 clauses still described a
later review as pending, plus the acceptance step used the old card name **Version history**. This candidate puts all
historical clauses in past tense and names the **Offer versions** card. The record-only cleanup changes candidate
identity, so Round 7 is not used for binding and the exact corrected snapshot still requires final review.

Independent review round 8 returned `ACCEPTED` with no blocking or material findings against candidate diff SHA-256
`04cebace133346e50ba2728103aeebb8b83454bb5c2ad615b1764510f27ff023` (packet SHA-256
`5c83d869afd2b802ade80093cf37332563e6d5e4791ed1cc7dd5f8ae55941e64`). Its sole advisory explicitly said not to
change that accepted candidate for three cosmetic naming drifts; they were preserved as `9F-R8-A1`. Adding that
durable advisory record changed candidate identity, so Round 9 reviewed the complete reconciled snapshot.

Independent review round 9 returned `ACCEPTED` with no blocking or material findings against candidate diff SHA-256
`764a407019bdf3c49e7acce6e816ffb111413e606b43e87d165e10c1b1ec147e` (packet SHA-256
`2519de92bcbe46cf7097d192b8f6d82230869ea50ac2b13e5403eca4de1dd151`). That exact candidate was committed as
`b6e086872104f795784d5e315c83d53407509093`, pushed and opened as pull request #120. Its one advisory asked that the
post-commit record add Round 8/Round 9 parity here, in the continuity note and in `NEXT_STEPS.md`; this correction
candidate does so.

The first hosted run on that commit exposed a real terminal-status UI regression: the backend deliberately retained
outcome-date/remarks-only corrections on the current concluded row, while the Slice 9F UI disabled the entire form.
The correction preserves the established backend behavior for `ACCEPTED`, `REJECTED`, `WITHDRAWN` and `CLOSED`,
keeps their status and commercial content locked, and keeps `REVISED`/`ABANDONED` fully immutable. The affected
frontend and targeted Chromium gates pass. It resolves `9F-R5-A1`; the same correction touch resolves `9F-R8-A1`.
Hosted-CI correction independent review round 1 returned `ACCEPTED` with no blocking or material findings against
complete corrected candidate diff SHA-256 `9ae48011bb051d12ca078a8696d58ed4d727370ec73419b979c289064bec7e60`
(packet SHA-256 `908308a5d8cf354c6396f158ac76aff8373d8f273b694f7be6ef1b6e05c987bb`). Its two advisory-only future frontend
hardening items are preserved as `9F-CI-R1-A1` and `9F-CI-R1-A2` in `DEFERRED_REQUIREMENTS.md`. Adding that mandatory
record changes documentation only, so a final documentation-reconciled review remains before binding and the hosted
`Required validation` rerun. The project owner retains merge authority.

Hosted-CI correction review round 2 then returned `ACCEPTED` with no blocking or material findings against candidate
diff SHA-256 `e8d011a5243803bb54c26e0816af588371c001913516f43d8bc1d1648c369e9b` (packet SHA-256
`d9500776a054a55a0de89220f2778d2790344fe9b70567b4a0e7e93063910b55`). The exact candidate was committed as
`241d76a8efea0929d635ea2a71f116ac6f4cf3bb`. Its hosted run passed Compose/health/E2E and every other job except the
backend regression. That job completed `3541` tests successfully and exposed three stale Slice 9B tripwires: the
new, correctly locked abandon-version status writer was missing from the expected exact set, while an obsolete
parameter still searched the now-disabled legacy revision-creation path for its pre-9F eligibility marker. The test
contract now includes the abandon writer and removes only the obsolete mutation case. The whole 9B file passes (`93`)
and the full local backend suite passes (`3541 passed, 2 skipped`). Hosted-backend correction review round 3 returned
`ACCEPTED` with no blocking or material findings against candidate diff SHA-256
`7a5084a658f1b1e08ed2665c2eccfc176f7c4d4ad270fe629a1498287ce499a3` (packet SHA-256
`f05a2c6fffe2ffdc4d8c6d2e3f328aad94c0ae0710e3f6e1e8ecbc44a7c0fe79`). Its future tripwire-hardening advisory is
preserved as `9F-CI-R3-A1`; the record-only delta needs final documentation-reconciled review before binding. A hosted
rerun then remains; owner merge authority is unchanged.
