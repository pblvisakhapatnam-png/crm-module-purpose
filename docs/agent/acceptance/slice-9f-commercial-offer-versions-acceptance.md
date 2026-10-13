# Slice 9F - Commercial Offer Versions Acceptance

## Test users

```text
sales1 / password      create, edit, submit, version and abandon
manager1 / password    create, edit, submit, version and abandon
finance1 / password    view version history; version commands forbidden
ops1 / password        view and pricing work where separately authorized; version commands forbidden
readonly1 / password   view only; version commands forbidden
```

## Starting URL and data

Start at `/commercial-offers/{public_id}` with an Account-linked Commercial Offer that has one active line, selected
pricing evidence, active T&C, a current credit review, submission evidence and status `SUBMITTED`. The automated
fixture creates this state through the public/service actions; the TE-1 `core-regression-bundle` creates the matching
browser target.

## Happy path

1. Sign in as `sales1`, open the submitted offer and confirm its header and content-edit actions are read-only.
2. In **Offer versions**, choose **Make a new version**, record a reason and optional note, and open the returned version.
3. Confirm the code is unchanged and the display advances from `v1` to `v2`.
4. Confirm the header, active lines, pricing evidence and selected basis, active T&C and current active credit review
   were copied with new child public IDs.
5. Confirm submission evidence, quotation documents, customer responses and legacy revision rows were not copied.
6. Edit the v2 line/rate, generate and approve a v2 quotation, then record new submission evidence.
7. Confirm the quotation reference is `offer-code v2/V1`, while v1's reference remains unchanged.
8. Mark v2 submitted. Confirm v2 becomes `SUBMITTED`, v1 becomes `REVISED`, and v1 says it was replaced by v2.
9. Record the customer outcome on v2 and confirm the same action is refused on v1.
10. Confirm open-offer reporting counts the series once while v2 is being prepared and once after v2 replaces v1.

## Abandonment and numbering

1. From a submitted latest version, make v2 and then abandon it.
2. Confirm v2 is `ABANDONED`, read-only, and the submitted predecessor is unchanged.
3. Make another version from the still-submitted predecessor; confirm it is v3, not a reused v2.
4. Confirm only one Draft/Ready later version may exist at a time.

## Negative and permission paths

- Making a version from Draft, Ready, Revised, Abandoned, Accepted, Rejected, Withdrawn or Closed is rejected.
- Making a version from an older submitted record when another later sent version exists is rejected.
- A second preparation version is rejected, including two requests made at the same time.
- Sending a later version is rejected if its predecessor is no longer Submitted; neither row is partly changed.
- Customer response, withdrawal and closure on the sent predecessor are rejected while a later version is in
  preparation; the user is told to send or abandon it first.
- Commercial edits and child writes on Submitted, Revised, Abandoned and other concluded rows are rejected.
- Starting a new legacy Slice 6K revision is rejected with **Make a new version** guidance. Existing OPEN legacy
  records remain listable and closable/resubmittable.
- `finance1`, `ops1` and `readonly1` receive backend `403` responses for version commands.
- Missing offer IDs return `404`; invalid reasons and invalid transitions return non-sensitive `422` messages.

## Regression checks

- The frozen Accepted Commercial Offer -> Work Order handoff contract is byte-identical and works from the accepted
  latest version's own offer/line identities.
- Supplementary and Change Quotation series remain separate offers; version lineage is not confused with `base_offer`.
- Submission readiness, quote generation/approval, customer response, reports and smoke-data cleanup remain usable.
- Reports do not count Draft/Ready later versions, Revised predecessors or Abandoned versions as extra open offers.
- Reads create no business event. Creating, abandoning and submitting a version create the documented events.
- Migration downgrade refuses to erase version history and succeeds when no version history exists.

## Automated gate

```powershell
docker compose --env-file .env.example -f docker-compose.yml -f .slice9f-compose.yml -p pbl-crm-9f exec -T backend pytest -q <focused files>
docker compose --env-file .env.example -f docker-compose.yml -f .slice9f-compose.yml -p pbl-crm-9f exec -T backend pytest -q tests/test_smoke_data_harness.py -k <9F targets>
docker compose --env-file .env.example -f docker-compose.yml -f .slice9f-compose.yml -p pbl-crm-9f run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run typecheck
docker compose --env-file .env.example -f docker-compose.yml -f .slice9f-compose.yml -p pbl-crm-9f run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm test
docker compose --env-file .env.example -f docker-compose.yml -f .slice9f-compose.yml -p pbl-crm-9f run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run build
python scripts/validate_contract_fixtures.py
python scripts/check_tracked_secrets.py
python -m unittest discover -s scripts/tests
git diff --check
```

The original work-package plan left full backend regression and full Playwright to the hosted required check. After
the hosted backend job exposed stale tripwires, the corrected full backend suite was also run locally; full Playwright
remains hosted. A targeted exploratory browser pass covers the new v1 -> v2 flow before review.

## Current result

- Focused backend regression: `282 passed`.
- Final post-Round-4-correction backend subset on the rebuilt image: `129 passed` (`test_commercial_offers_api`,
  CS-05c, CS-11, reports and Slice 9F).
- Slice 9F test file after version-reference, report and migration-guard additions: `10 passed`.
- Post-hosted-correction focused backend set (`test_slice_9f_commercial_offer_versions.py` plus
  `test_commercial_offers_api.py`): `58 passed` on the rebuilt image.
- Post-hosted-backend-correction Slice 9B hardening file: `93 passed`; full local backend regression:
  `3541 passed, 2 skipped` on the rebuilt image.
- Targeted TE-1 smoke-data regression: `8 passed`.
- Alembic current/head: `20260908_0054`; empty-history downgrade/upgrade cycle: pass.
- Frontend typecheck: pass.
- Frontend Vitest after Round 4 corrections: `31` files / `602` tests passed.
- Frontend production build: pass (existing large-chunk advisory only).
- Targeted Chromium happy path: `submitted-offer-lock.spec.ts`, `1 passed`; scenario and login-event cleanup passed.
- Post-hosted-correction targeted Chromium regression: `submitted-offer-lock.spec.ts` and
  `terminal-status-guard.spec.ts`, `2 passed`; scenario and login-event cleanup passed. This proves submitted/versioned
  commercial content remains locked while the current concluded row's outcome date and remarks remain editable.
- Contract-fixture validator: `7` candidate fixtures passed; tracked-secret check: passed (`2242` proposed-tree
  files); `git diff --check`: passed; frozen handoff SHA-256: matched.
- `python -m unittest discover -s scripts/tests`: `160` run, `28` skipped, `8` failed on this Windows host. The
  failures are confined to the unchanged TE-5 backup/cron tests. A traced failing case showed Git Bash resolving its
  bundled `df.exe` instead of the test's extensionless fake `df`, reading the real disk as `83%` and making the
  deliberately failing backup scenario return success. The dedicated unchanged module reproduced the same eight
  failures (`95` run, `28` skipped). The Linux hosted check remains the authoritative execution for these scripts.
- Structured self-review: complete. It found and corrected one stale Slice 6K compatibility docstring/import cluster.
- Independent review round 1: `CORRECTION_REQUIRED` against staged candidate
  `56b072ed3cbef1a7de5bce5bb63eb4ae419b9fd8` (diff SHA-256
  `a411db39058b94dddb237d7cdaa8134cc62fc8b88ceeaf2c8b226ae0ea3a5d1f`; packet SHA-256
  `b337b6f5e2624f8d8ccf5f7019d0bd65256e038a0ecfc59ea618fc25f923edb7`). The correction set closes the
  preparation-version withdrawal/closure escape, restores submitted withdrawal/closure and outcome-only UI,
  aligns lifecycle guidance, adds a predecessor-side replacement event, derives report preparation statuses from
  the module contract and fixes permission documentation. Focused backend/frontend/E2E revalidation passed.
- Independent review round 2: the no-tools re-review received the complete corrected candidate packet (packet
  SHA-256 `92a0dcc9d4e57c61a74d26bc115e8b8cfa3d439cbabf23c7a89b61370133d544`) but reached the agreed
  15-minute cap and was terminated before returning any judgement. It is recorded as a timed-out attempt, not as an
  acceptance or rejection.
- Independent review round 3: `CORRECTION_REQUIRED` against candidate diff SHA-256
  `a9c7f49e385cc0d9fbfa492b1946ca3113dd310144ba7a8d7c07171bd332da8b` (packet SHA-256
  `7da1911bf90826e81f4568da0a72418bbd0cc6c508224f2701579ba4e280d50e`). The corrected candidate now derives
  sent/replacement identity from controlled lifecycle status rather than editable `submitted_at`, refuses manual
  submission metadata on preparation versions, reports replaced/abandoned rows as inactive history even when older
  non-final responses exist, accepts a repeated unchanged status alongside an allowed outcome-note update, and
  reconciles the contract wording, event inventory and deferred downstream version-label work. The review packet's
  apparent replacement character was an encoding artefact; the visible separator was changed to ASCII as well.
  Focused backend, frontend and targeted Chromium revalidation all pass after these corrections.
- Independent review round 4: `CORRECTION_REQUIRED` against candidate diff SHA-256
  `755befabd29939a6ff5294d6e452fa0217db9b7515a9ac11478d9131919638da` (packet SHA-256
  `0e15cf493d99faaaccc5f77bdc302897a35846c887e5a4f3bd094eea02069ee8`). It verified every Round 3 correction
  and the concurrency/lock behavior, then found two material history gaps: outcome notes could still mutate
  `REVISED`/`ABANDONED` rows, and a Draft quotation from either historical status could still be approved for issue.
  The corrected candidate makes both history statuses fully read-only, blocks quotation approval for both, exposes
  the same refusal in `approval_blocked_reason`, replaces the remaining version-creation status literals, makes the
  post-transition UI fully read-only, and proves a normal header edit on a preparation version sends only changed
  fields. Slice 9F (`10`), the focused backend set (`129`), frontend (`602`) and targeted Chromium (`1`) all pass.
- Independent review round 5: `ACCEPTED` with no blocking or material findings against candidate diff SHA-256
  `47b8d045e779ab090146fca064ae154bd7398ff5bd58b3d4508f9c5dd1504974` (packet SHA-256
  `e98f56651273772a6b43fa921b8af63dc8e6aec63fdc5d812825146daa6d316a`). It confirmed all Round 4 corrections and
  the concurrency, numbering, report, migration and copy-boundary behavior. Four advisory-only observations are
  preserved as `9F-R5-A1` to `9F-R5-A4` in `DEFERRED_REQUIREMENTS.md`. Because this mandatory durable advisory record
  changed the candidate documentation after the Round 5 snapshot, Round 6 reviewed the complete
  documentation-reconciled candidate before review-to-commit binding.
- Independent review round 6: `ACCEPTED` with no blocking or material findings against candidate diff SHA-256
  `69049fa6ecf33480f64ed1c8aa500bfa37bf6fbf7d6c823ede200048cb4202e4` (packet SHA-256
  `f98b6ca0beca1102a3de51fd79760fa39a7fa3519c07112baff2701099d1705b`). It reconfirmed the complete runtime candidate
  and returned four advisory-only documentation findings. All four are corrected in this candidate: `9F-R5-A3` and
  `A4` accurately describe the observed messages, the lifecycle contract enumerates the two 9F history states, and
  stale present-tense Round 1/Round 3 status clauses are now historical. Those record-only corrections changed
  candidate identity and were reviewed in Round 7, so Round 6 is not used to bind the corrected snapshot.
- Independent review round 7: `ACCEPTED` with no blocking or material findings against candidate diff SHA-256
  `8509481f8c6c68b1b1b8c8eccbaacb8f160eb32a7e7fd9a1da26c7adc61ba313` (packet SHA-256
  `9aa7e351730978c7961ab462ecda2072c4d838766c5184d47970d01a50d7250d`). It verified every Round 6 correction and
  again found no runtime defect. Its sole advisory-only finding was stale present tense in a few earlier review
  clauses; it also suggested matching this checklist's card name to **Offer versions**. Both are corrected here. The
  record-only cleanup changes candidate identity, so Round 7 is not used to bind this corrected snapshot.
- Independent review round 8: `ACCEPTED` with no blocking or material findings against exact candidate diff SHA-256
  `04cebace133346e50ba2728103aeebb8b83454bb5c2ad615b1764510f27ff023` (packet SHA-256
  `5c83d869afd2b802ade80093cf37332563e6d5e4791ed1cc7dd5f8ae55941e64`). It verified the Round 7 cleanup and again
  found no runtime defect. Its sole advisory explicitly said not to change that accepted candidate for three cosmetic
  naming drifts; they are preserved for the next relevant touch as `9F-R8-A1` in `DEFERRED_REQUIREMENTS.md`. Adding
  the mandatory durable advisory record changes only documentation, so Round 8 is not used to bind this snapshot.
- Independent review round 9: `ACCEPTED` with no blocking or material findings against exact candidate diff SHA-256
  `764a407019bdf3c49e7acce6e816ffb111413e606b43e87d165e10c1b1ec147e` (packet SHA-256
  `2519de92bcbe46cf7097d192b8f6d82230869ea50ac2b13e5403eca4de1dd151`). The accepted candidate was committed as
  `b6e086872104f795784d5e315c83d53407509093` and opened as pull request #120. Round 9's sole advisory asked for
  post-commit parity across the slice, continuity and `NEXT_STEPS.md` records; that reconciliation is included in the
  hosted-CI correction candidate.
- The first hosted run on `b6e086872104f795784d5e315c83d53407509093` found a real UI regression in
  `terminal-status-guard.spec.ts`: the backend and existing contract allowed outcome-date/remarks-only corrections on
  the current concluded row, but the Slice 9F UI disabled the entire form. The correction keeps status and commercial
  content locked, enables only those two outcome fields for `ACCEPTED`, `REJECTED`, `WITHDRAWN` and `CLOSED`, keeps
  `REVISED`/`ABANDONED` fully immutable, and resolves `9F-R5-A1`. The affected frontend and browser gates pass; a
  fresh independent review and hosted required check on the corrected head were required.
- Hosted-CI correction independent review round 1: `ACCEPTED` with no blocking or material findings against complete
  corrected candidate diff SHA-256 `9ae48011bb051d12ca078a8696d58ed4d727370ec73419b979c289064bec7e60`
  (packet SHA-256 `908308a5d8cf354c6396f158ac76aff8373d8f273b694f7be6ef1b6e05c987bb`). Its two advisory-only future-hardening
  observations are preserved as `9F-CI-R1-A1` and `9F-CI-R1-A2` in `DEFERRED_REQUIREMENTS.md`; the reviewer explicitly
  found no current wrong outcome and recommended no runtime change. This mandatory advisory record changes only
  documentation after the reviewed snapshot, so a final documentation-reconciled review remains before binding.
- Hosted-CI correction independent review round 2: `ACCEPTED` with no blocking or material findings against exact
  candidate diff SHA-256 `e8d011a5243803bb54c26e0816af588371c001913516f43d8bc1d1648c369e9b`
  (packet SHA-256 `d9500776a054a55a0de89220f2778d2790344fe9b70567b4a0e7e93063910b55`). The committed diff matched exactly in
  `241d76a8efea0929d635ea2a71f116ac6f4cf3bb`, which was pushed to pull request #120.
- Hosted run `38132136325` on that commit passed contract fixtures, migrations, frontend, secret/dependency checks and
  Compose/health/E2E, proving the terminal-status UI regression was fixed. Backend regression then finished with
  `3541 passed` and three stale-test failures: the exact status-writer tripwire did not yet name the new, correctly
  locked `abandon_commercial_offer_version`, and a separate mutation-lock parameter still expected the pre-9F
  in-place-revision eligibility marker even though 9F now rejects new legacy revision cycles unconditionally.
- The correction adds the abandon command to the exact-set/lock-order tripwire and removes only that obsolete legacy
  revision parameter, updating the test explanation. The full Slice 9B hardening file passes (`93 passed`), followed
  by the full local backend suite (`3541 passed, 2 skipped`).
- Hosted-backend correction independent review round 3: `ACCEPTED` with no blocking or material findings against
  complete candidate diff SHA-256 `7a5084a658f1b1e08ed2665c2eccfc176f7c4d4ad270fe629a1498287ce499a3`
  (packet SHA-256 `f05a2c6fffe2ffdc4d8c6d2e3f328aad94c0ae0710e3f6e1e8ecbc44a7c0fe79`). Its advisory-only future hardening for
  the version-submission lock-order tripwire is preserved as `9F-CI-R3-A1` in `DEFERRED_REQUIREMENTS.md`; the reviewer
  found current runtime locking correct and recommended no candidate runtime change. This required record-only delta
  needs a final documentation-reconciled review before binding; the corrected hosted required check then remains.

## Deferred / known gaps

- Side-by-side value/line comparison between versions.
- Carry-forward of submission evidence or quote documents (deliberately not copied in 9F).
- Legal/deviation approval workflow and maker/checker hardening beyond the existing quotation approval gate.
- Calculated credit/exposure availability gate, server-side PDF rendering and full tender/BOQ automation.
- Work Order changes after award remain Work Order Amendment / Change Quotation work; 9F does not mutate a Work Order.
- Review advisories `9F-R5-A2` to `9F-R5-A4`, carried in `DEFERRED_REQUIREMENTS.md`; none changes the implemented 9F
  business outcome or blocks this slice. `9F-R5-A1` and `9F-R8-A1` are resolved in the hosted-CI correction candidate.
- Hosted-CI correction advisories `9F-CI-R1-A1` and `9F-CI-R1-A2`, carried in `DEFERRED_REQUIREMENTS.md`; both are
  future frontend hardening with no current wrong outcome.
- Hosted-backend correction advisory `9F-CI-R3-A1`, carried in `DEFERRED_REQUIREMENTS.md`; it is future test
  hardening for the already-correct version-submission row-lock path.

## Handoff contract check

`docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` must remain SHA-256
`0F16FF221E897F6199C352204A0ECCED6F9A67F0C6695AD97C08C9DC2CD39080` through the final candidate.
