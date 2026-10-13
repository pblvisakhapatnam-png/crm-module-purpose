# TE-3 Acceptance — UAT Synthetic Data Pack

Technical-enablement package. No CRM business behaviour, API contract, schema, migration,
permission rule, business event or frontend screen changed. Both frozen contracts unchanged.

## Automated checks

| Check | Command | Result |
| --- | --- | --- |
| Harness suite | `docker compose exec backend pytest tests/test_smoke_data_harness.py` | 61 passed (38 pre-existing + 23 new) |
| Full backend regression | `docker compose exec backend pytest` | **1304 passed, 0 failed**, 7m 42s |
| Alembic head | `alembic current` / `heads` | `20260908_0035` — unchanged, no migration added |

1281 was the baseline at Slice 9E; 1281 + 23 new = 1304, so nothing was displaced.

### One failure that did not reproduce, recorded rather than dismissed

An earlier full run reported `1293 passed, 1 failed` -
`test_commercial_offer_related_offers_api.py::test_change_quotation_requires_linked_work_order`,
a test unrelated to this package. It did not reproduce in five subsequent runs: alone, as a whole
file, alongside the harness file in one session, and in two clean full-suite runs.

Two facts point away from this package: it changes **no application code**, only test tooling
under `backend/tooling/smoke_data/`; and Slice 9E already recorded "pre-existing full-suite
ordering flakiness against the shared development database", which affected three unrelated tests
then. This is a new instance of that known class, on a different test.

One fact is not explained. **That run took 7h 55m against 7m 56s for the identical run before it**
- a factor of sixty, overnight, so the machine was presumably asleep or heavily loaded for most of
it. Nothing about behaviour during that window should be reasoned about confidently.

**The traceback was lost**, because the run used `-q` with only the last few lines captured. That
was an avoidable process error, not an environment problem, and it is the reason this can only be
recorded as *not reproduced* rather than *diagnosed*. Later runs used `-rf --tb=long`.

Frontend was not touched, so its gate was not run.

## The three cleanup regression tests failed first

Each was written before the fix and observed failing, in two distinct modes:

| Test | Failure observed before the fix |
| --- | --- |
| `test_cleanup_discovers_a_quote_document_generated_after_seeding` | quotation survived its deleted offer (`assert 1 == 0`) |
| `test_cleanup_removes_account_identity_records_attached_after_seeding` | `ForeignKeyViolation` on `business_party` |
| `test_cleanup_discovers_an_interaction_logged_after_seeding` | interaction survived its deleted offer |

Independently confirmed against the database before fixing: **2 orphaned quote documents and 2
orphaned `document_metadata` rows**, with cleanup having reported success.

## Dataset verified for substance, not row counts

| Shape it exists to test | Verified |
| --- | --- |
| Very long legal name | 217 characters, rendered into the generated quotation |
| Multi-line site address | line 2 populated, district (`Kalahandi`) differs from city (`Lanjigarh`) |
| Several GSTINs for one customer | 4 registrations across states 37/36/21/24, all sharing one PAN |
| Unpriced active line | quotation total row reads **"Not fully priced"**, while the priced line's own amount (952,000.00) is still shown |
| Superseded version | v1 `DRAFT` + superseded, v2 `DRAFT` current, each keeping its own status |
| Lifecycle spread | offers in `DRAFT`, `SUBMITTED`, `ACCEPTED`, `REJECTED`; 7 approved-for-issue quotations; 3 Work Orders; 1 amendment; 2 related offers |
| Deliberate gaps | one offer with no quotation, one with no interaction, so the advisory checklist is not all-green |

## Second-review corrections verified

Each test reproduces a failure the second independent review demonstrated by fault injection.

| Test | The failure it reproduces |
| --- | --- |
| `test_cleanup_removes_an_ordinary_offer_created_on_a_seeded_opportunity` | FK rollback aborting the whole cleanup |
| `test_cleanup_removes_an_account_repaired_onto_a_seeded_opportunity` | Account surviving silently with its audit row |
| `test_cleanup_removes_the_audit_event_of_a_lead_activity_created_after_seeding` | exactly one `business_event` left behind |
| `test_status_detects_an_orphaned_quote_document` | status certifying a failed reset as clean |
| `test_cleanup_raises_rather_than_reporting_success_when_bytes_cannot_be_deleted` | leaked bytes reported as "1 deleted", exit 0 |
| `test_ownership_closure_settles_and_does_not_reach_unrelated_records` | guards the wider closure against over-deletion |

The closure was also demonstrated incidentally: cleaning a leftover account from a bare account id
reached its Opportunity, offer, lines, submission evidence, credit review and customer response -
a path the previous one-directional discovery did not follow at all.

## Sales journey verified

| Step | Verified |
| --- | --- |
| Lead worked then converted | `CONVERTED` in the database, produced its own Account, Opportunity and quotation |
| Lead closed as not worth pursuing | `UNQUALIFIED`, and correctly produced **no** Account |
| Lead left open | `NEW`, for a tester to work live |
| Lead activity trails | 4, 3 and 2 entries respectively, not a single entry each |
| Market rates | 3 per offer, from 3 named Operations Executives |
| Basis choice | Both cases present: lowest for some, second-lowest for others with a recorded reason. Verified the dearer choice is genuinely not the lowest rate |
| Negotiation | 4-message trail on one offer |
| Revision | Real `Rev 1 / RESUBMITTED` record plus a second approved quotation version, v1 retained and superseded |
| Document upload | 3 files uploaded through the real Slice 9C path (`storage_mode=local_upload`, real storage key), removed on cleanup, `documents_storage_deleted` matching the row count |

## Cleanup verified end to end

Full dataset removed: 11 accounts, 11 opportunities, 13 offers, 29 offer lines, 3 leads, 9 lead
activities, 11 quote documents, 14 documents, 16 interactions, 33 pricing evidence rows, 1
revision, 18 GSTINs, 11 addresses, 10 tax profiles, 3 Work Orders, 1 amendment, 306 business
events. **Zero files remained in the document store** (`find /app/document-store -type f` → 0),
confirming stored bytes go with their rows.

The account and opportunity counts exceed the ten seeded customers because the converted lead
produces its own Account and Opportunity, which the closure reaches through the lead.

## Manual checks performed

| Check | Result |
| --- | --- |
| `seed --scenario uat-pilot-seeded` | Pass — 13 records (3 leads + 10 customers), ~4s |
| `list-runs` | Pass — run listed with scenario name |
| `status --run-id` while seeded | Pass — anchors present, attached records listed |
| `cleanup --run-id` | Pass — per-table counts reported |
| `status --run-id` after cleanup | Pass — "no anchor records and nothing left attached", exit 0 |
| `cleanup --run-id` twice | Pass — idempotent, zero deletions, exit 0 |

Every command printed in `docs/uat/PBL_CRM_UAT_RUNBOOK.md` was executed as written.

## Deferred / not covered

- **No Playwright coverage of the UAT dataset.** The pilot is a human exercise; the existing E2E
  suite already covers the underlying flows.
- **No browser walkthrough of the seeded data yet.** The dataset was verified through the service
  layer and the database. Looking at it on screen is the first step of the UI cleanup decision
  (restructure vs reskin) and belongs there, not here.
- **No `uat-data.ps1` wrapper.** `scripts/smoke-data.ps1` already exposes seed/status/cleanup for
  any scenario.
- Blank-canvas records typed in by hand are not covered by any manifest and must be removed
  through the application or by resetting the database. Stated in the runbook.

## Human acceptance checklist

Test user: `sales1` / `password` (and `manager1` for approvals). Starting URL:
`http://localhost:3000`.

1. Seed the dataset; confirm ten `UAT-` customers appear in the Accounts list.
2. Open `UAT-Kakinada Steel & Ferro Alloys`; confirm the long legal name displays without
   breaking the layout, and that four GSTINs are listed.
3. Open its Commercial Offer; confirm five lines including the paired overtime lines.
4. Open `UAT-Saint-Guilbert...`; generate a quotation; confirm the total reads "Not fully priced".
5. As `sales1`, attempt to approve it for issue — expect refusal.
6. As `manager1`, approve it — expect success with name and timestamp.
7. Open `UAT-MacDiarmid...`; confirm two quotation versions with v1 marked superseded.
8. Reset with `cleanup --run-id`; confirm `status` reports nothing left attached.
