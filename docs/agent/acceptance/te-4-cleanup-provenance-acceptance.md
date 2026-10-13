# TE-4 Acceptance — Cleanup Correctness for the TE-1 Harness

Technical-enablement package. No CRM business behaviour, API contract, schema, migration,
permission rule, business event or frontend screen changed. Both frozen contracts unchanged.

Changed: `backend/tooling/smoke_data/{cleanup,status,cli,manifest}.py`,
`backend/tests/{conftest,test_smoke_data_harness}.py`, `scripts/vendor-demo.ps1`, documentation.
`store.py` is byte-identical to `main`.

## Automated checks

| Check | Command | Result |
| --- | --- | --- |
| Harness suite (baseline) | `pytest tests/test_smoke_data_harness.py` | 61 passed |
| Harness suite (final) | same | **74 passed** (61 + 13 new cases) |
| Full backend regression | `pytest -q -rf --tb=long` | **1317 passed, 0 failed**, 7m 18s |
| PowerShell parse | `[Parser]::ParseFile('scripts/vendor-demo.ps1', …)` | parses cleanly, 0 errors |
| Alembic head | `alembic current` | `20260908_0035 (head)` — unchanged, no migration |

1304 was the TE-3 baseline; 1304 + 13 = 1317, so nothing was displaced.

## Every finding reproduced before it was fixed

Six correction rounds against this package, each writing the failing test first. Findings closed:

| Round | Findings | Note |
| --- | --- | --- |
| 1 | 5 | repair-created Account escaping deletion; `status` unable to certify; manifest collections skipped; provider conformance assumed; a bad manifest reported as a database error |
| 2 | 6 | the recorded scope covering six of ten id groups; any truthy object counting as one; scope files accumulating; a non-atomic write; `status` exiting 0 for two opposite states; documentation overstating the code |
| 3 | 4 | an empty or wrong-run scope treated as authoritative; a corrupt one silently replaced; a rerun not retrying stored files; a failing `exists()` probe skipping the delete |
| 4 | 7 | **stored keys and completion stamp deleted rather than repaired** — two findings closed with no code written |
| 5 | 3 | a narrow inline scope hiding the sidecar; `status` not applying the audit type boundary; records describing removed behaviour |
| 6 | 4 | **the recorded scope removed entirely** (owner decision), plus the sub-record type cross-product |
| 7 | 3 | activity-only manifests deleting the audit row but not the record; scope-era prose surviving the removal, including a false `residue_clear` claim; a collision test still leaking on setup failure |

## Non-vacuity

A test that passes before its fix proves nothing until the behaviour it guards is removed. Each was
broken deliberately, watched fail, restored.

| Test | Behaviour removed | Observed failure |
| --- | --- | --- |
| provider conformance | local `delete` made a no-op | `exists()` still reports an object after `delete()` |
| repair-created Account | the provenance edge | the created Account survived cleanup |
| manifest collections | entries skipped instead of refused | `DID NOT RAISE CleanupValidationError` |
| audit type boundary | matching on id alone | the unrelated `equipment` event was deleted |
| sub-record types | address ids paired with all four types | `an address id was matched against the GSTIN record type` |
| `exists()` probe | probe moved back inside the delete's `try` | the object leaked |
| `--require-present` | the flag | `unrecognized arguments` |
| empty-manifest guard | the guard | `DID NOT RAISE` |

## Three tests were written wrong, and the failures said so

- **An interaction-document probe** injected a *fresh* id, which no record could know. Rewritten to
  reinstate the id cleanup had actually deleted.
- **A merge guard** compared records from a scenario whose closure discovers nothing beyond the
  manifest, so a deliberately non-merging save still passed.
- **The orphan-quote-document test** reused the deleted quotation's own id, making the orphan
  attributable — the opposite of its subject. Now uses a fresh id.

The first two tested a mechanism since removed; the third remains.

## Scope-file accumulation

```text
before          manifests: 31   scopes: 620   orphan scopes: 593
after (first)   fixture in the harness test module — still 6 orphans per full-suite run
after (final)   fixture in conftest.py — a full regression added none
```

Re-measuring is what caught the intermediate state: `test_slice_9b_pilot_hardening.py` also uses the
harness, so a fixture in the module *about* the harness missed it. The scope files themselves are
gone with the mechanism; the isolation remains and still matters for manifests.

## Residue

Zero document-store files, zero harness rows, zero quote documents, zero interactions, and the same
three pre-existing `document_metadata` rows from 14 August and 9 September 2026 — not created by
this package and deliberately not deleted.

Files were leaked twice during the work, both by me, both removed by exact path: by the deliberate
no-op-`delete` experiment, and by killing a full-suite run mid-flight.

**Worth keeping:** the Slice 9C tests measure `before = _stored_file_count()` and assert a return to
it, so a file leaked by an interrupted run is invisible to every subsequent green run. **A green
full run is not evidence the storage root is clean** — check the absolute count separately.

**Also worth keeping:** a regression run and a source edit cannot overlap, because
`backend/{app,tests,tooling}` are bind-mounted live into the container. One run was discarded for
exactly that. Once a regression starts, the tree is frozen until it reports.

## Deferred

`status` cannot certify a targeted cleanup — TE-3's limitation, unchanged, and the mechanism built
to close it was removed for the reasons in the package document. The READ COMMITTED race; a seed
that fails partway; no index on `business_event.record_public_id`.

## Human acceptance checklist

| # | Check | Expected |
| --- | --- | --- |
| 1 | `smoke-data.ps1 seed -Scenario uat-pilot-seeded`, open `/accounts` | Ten `UAT-` customers plus the converted lead's Account |
| 2 | `smoke-data.ps1 status -RunId <id>` | Anchors present, attached records listed, exit 0 |
| 3 | `smoke-data.ps1 status -RunId <id> --require-present` | exit 0 while the data is there |
| 4 | `smoke-data.ps1 cleanup -RunId <id>` | Per-table counts, exit 0 |
| 5 | `smoke-data.ps1 status -RunId <id>` | anchors gone, nothing attached to identifiable records, exit 0 |
| 6 | same, with `--require-present` | exit 1 |
| 7 | `find /app/document-store -type f \| wc -l` | `0` |
| 8 | Repeat step 4 | All counts 0, "that is not an error", exit 0 |
| 9 | Seed a second scenario, clean up only the first | The second run's records still present |
