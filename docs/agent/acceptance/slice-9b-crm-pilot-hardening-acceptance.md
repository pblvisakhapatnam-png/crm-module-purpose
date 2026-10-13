# Slice 9B Acceptance - CRM Pilot Hardening

Written so a later tester can perform regression/UAT without this session's chat history.

## Preconditions

Stack running, Alembic at `20260906_0032 (head)` - this slice adds no migration. If
`alembic current` reports an older revision than `alembic heads`, rebuild the backend image:
`alembic/` is baked into the image, so a merged migration is invisible until
`docker compose up -d --build --force-recreate backend` runs.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| Focused suite | `docker compose exec backend pytest tests/test_slice_9b_pilot_hardening.py -q` | 87 passed |
| Full backend regression | `docker compose exec backend pytest -q` | 1112 passed, 0 failed |
| Alembic unchanged | `docker compose exec backend alembic current` | `20260906_0032 (head)` |
| Frontend typecheck / tests / build | see `AGENTS.md` frontend sequence | clean / 54 passed / clean |

## Part 1 - A Rejected Commercial Offer is final

### Test data

Seed a rejected offer:

```powershell
docker compose exec backend python -m tooling.smoke_data seed --scenario rejected-offer
```

Record the `run_id` and clean up afterwards with `cleanup --run-id <run_id>`.

### Manual positive path

Test user `sales1` / `password` (SALES_USER).

1. Open the seeded Commercial Offer, go to the **Submission** tab.
2. Confirm the offer status is **Rejected**.
3. In the Customer Response section, confirm the "Record new customer response" form is **not**
   shown, and an amber panel explains that the offer is final and that a later award should be
   recorded against the replacement Commercial Offer.
4. In the Lifecycle Guidance panel, confirm "Another customer response allowed" reads **No**.

### Manual negative path (API, since the UI no longer offers it)

```
POST /api/commercial-offers/{rejected_offer_public_id}/customer-responses
{
  "response_outcome": "ACCEPTED_AWARDED",
  "response_channel": "EMAIL",
  "response_received_at": "2026-09-07T10:00:00",
  "customer_response_notes": "Late award attempt."
}
```

Expect `422`, with a message stating the offer was rejected and is final and directing the user
to the replacement offer. Then confirm:

- the offer's `offer_status_code` is still `REJECTED`;
- no new row appears in `GET .../customer-responses`;
- no `CommercialOfferCustomerResponseRecorded` event was created.

Repeat with `REVISION_REQUESTED`, `ON_HOLD` and `OTHER` - all must be refused. The rule is about
the offer's finality, not one particular outcome.

### Regression path - what must still work

1. A **Submitted** offer still accepts every customer response outcome, including
   `ACCEPTED_AWARDED` and `REJECTED_LOST`.
2. An **Accepted** offer still accepts a further customer response.
3. A replacement Commercial Offer can still be created for an Opportunity whose earlier offer is
   Rejected. This is the Slice 6B.1 rule and is deliberately unchanged.
4. The replacement offer's own lifecycle is unaffected.

## Part 2 - Insecure placeholder secrets

### Manual check

Override **every** effective secret. The "starts" case must not inherit the container's
`DATABASE_URL`: on a machine still using the shipped `.env.example`, that URL carries the
placeholder password and the guard would correctly refuse, making a valid JWT override look like
a failure.

```powershell
# refuses - placeholder JWT secret
docker compose exec -e APP_ENV=production -e JWT_SECRET=change-this-in-real-use `
  -e DATABASE_URL=postgresql+psycopg://u:<YOUR-REAL-PASSWORD>@db:5432/x backend `
  python -c "from app.core.config import Settings; Settings()"

# refuses - placeholder password in the URL query string, which overrides user info
docker compose exec -e APP_ENV=production -e JWT_SECRET=a-real-secret `
  -e "DATABASE_URL=postgresql+psycopg://u:<ANYTHING>@db:5432/x?password=<THE-PLACEHOLDER-FROM-ENV-EXAMPLE>" backend `
  python -c "from app.core.config import Settings; Settings()"

# starts - every effective secret overridden
docker compose exec -e APP_ENV=production -e JWT_SECRET=a-real-secret `
  -e DATABASE_URL=postgresql+psycopg://u:<YOUR-REAL-PASSWORD>@db:5432/x backend `
  python -c "from app.core.config import Settings; print(Settings().app_env)"
```

The first must raise `InsecureDefaultConfigurationError` naming `jwt_secret` and **must not print
any configured secret value**. The second must succeed.

Also confirm an unrecognised environment fails closed: `APP_ENV=producton` (deliberate typo) with
the placeholder secret must also refuse.

### Regression path

Ordinary development startup must be unaffected: `docker compose up -d` then
`GET /api/health` returns `{"status":"ok", ..., "environment":"development"}`.

## Deferred / not covered

- Real user provisioning is operational work, not covered here.
- TLS, SSO/MFA and secret-store integration belong to the production gate.
- Playwright coverage for the blocked customer-response UI. The TE-1 suite has a
  `rejected-offer` scenario that could carry an assertion; adding it should follow the existing
  manifest-driven pattern rather than a new seeding mechanism.
- The guard checks only two known placeholder values. It is not a general secret-strength or
  entropy check, and does not detect a weak-but-different secret.

---

## Recorded acceptance result - correction pass, 7 September 2026

Independent review of the first candidate (`33d1010`) returned ten findings, three of them P1.
All ten were corrected; this section records what was actually executed afterwards, rather than
only what should be executed.

### Automated results

| Check | Result |
| --- | --- |
| `pytest tests/test_slice_9b_pilot_hardening.py -q` | **76 passed** (21 original + 55 across ten correction passes) |
| `pytest -q` | **1101 passed, 0 failed** |
| `alembic current` / `heads` | `20260906_0032` - unchanged |
| Frontend typecheck / tests / build | clean / 54 passed / clean |
| `check_tracked_secrets.py` | no findings |
| `validate_contract_fixtures.py` | passed |

### Manual checks performed

Test user `sales1` (SALES_USER), against seeded scenarios, frontend image rebuilt first.

| # | Check | Result |
| --- | --- | --- |
| 1 | Rejected offer (`rejected-offer` scenario), Submission tab | **Pass.** Form absent. Panel reads "This Commercial Offer was rejected and is final... record the outcome against the replacement Commercial Offer for this Opportunity." |
| 2 | Draft offer (`supplementary-offer-draft`), Submission tab | **Pass.** Panel reads "A customer response can be recorded only after the Commercial Offer has been submitted. Current status: Draft." The finality/replacement wording is correctly **not** shown - this was review finding 4. |
| 3 | Submitted offer (`blocked-handoff`), Submission tab | **Pass.** Form is shown with an enabled "Record customer response" button. |
| 4 | Hardcoded status list removed | **Pass.** `grep` for `"SUBMITTED", "ACCEPTED", "REJECTED"` in `CommercialOfferDetailPage.tsx` returns nothing - this was review finding 5. |
| 5 | Config guard against the running container | **Pass.** Development startup unaffected (`/api/health` ok); `APP_ENV=production` with the placeholder secret refuses with a message naming `jwt_secret` and disclosing no value; with a real secret it starts. |

All seeded scenarios were cleaned up afterwards; `business_party` rows matching `TE1-SMOKE%`
returned to zero.

### Check NOT completed, and why

**Live end-to-end confirmation of the success-feedback fix (review finding 6) was not
performed.** The intended check was: record a `REJECTED_LOST` response through the UI on a
submitted offer, and confirm the green confirmation message still renders after the form
unmounts. The in-app browser repeatedly rendered a blank viewport when scrolling this
particularly long page, and the form could not be driven to submission.

What *was* verified is structural: `customerResponseMessage` and `customerResponseError` are now
siblings of the entire conditional block inside `SectionCard`, not children of the form, so no
branch of that conditional can unmount them. That is the substance of the fix, but it is static
verification, not behavioural.

**A reviewer should perform this one check manually before final acceptance.** Steps: seed
`blocked-handoff`, open the offer's Submission tab, record a customer response with outcome
"Rejected / lost", and confirm that after saving (a) the form is replaced by the finality panel
and (b) the green "recorded" confirmation is still visible.

### Acceptance status

**Not self-accepted.** Under `AGENTS.md` an implementation agent does not record acceptance of
its own package. The corrections above are complete and evidenced; the outstanding manual check
is named explicitly rather than implied to have passed.

---

## Recorded acceptance result - tenth correction pass, 7 September 2026

The tenth review round returned one P1, three P2s and two P3s. All six were corrected. This
section records what was executed for that pass.

### Automated results

| Check | Result |
| --- | --- |
| `pytest tests/test_slice_9b_pilot_hardening.py -q` | **76 passed** |
| `pytest -q` | **1101 passed, 0 failed** |
| `alembic current` / `heads` | `20260906_0032 (head)` - unchanged, no migration |
| Frontend typecheck / tests / build | clean / 54 passed / clean (677 kB chunk warning is pre-existing) |
| `check_tracked_secrets.py` | 837 files in the proposed tree, no findings |
| `validate_contract_fixtures.py` | 7 fixtures, all rules passed |
| `python -m unittest discover -s scripts/tests` | 58 tests, OK |

### What the five new tests assert

| Test | Property |
| --- | --- |
| `test_the_duplicate_detector_finds_a_repeated_test_class` | the detector reports a shadowed `class TestX` |
| `test_distinct_test_classes_are_not_reported` | and does not report two differently-named classes |
| `test_the_scanner_sees_a_duplicated_class_in_a_module` | the same, end to end through `_scan_test_modules` |
| `test_a_concurrent_opportunity_closure_defeats_an_in_flight_offer_creation` | Base Offer creation blocks on the Opportunity row lock, then refuses once the Opportunity is closed |
| `test_a_concurrent_rejection_defeats_an_in_flight_amendment_validation` | amendment validation blocks on the basis offer's row lock, then refuses once that offer is rejected |

The last two use `_blocked_then_released`, which forces the interleaving instead of relying on
thread scheduling: it asserts the operation is *still blocked* before releasing the lock, so a
test that passed only because the two operations happened to serialize would now fail.

**Correction, recorded in the eleventh pass.** An earlier version of this section said the
amendment lock inventory "was verified by introspection". No such test existed; the sentence
described a manual shell check. The introspection tests it described now exist
(`test_the_set_of_amendment_accessors_is_exactly_the_known_set`,
`test_every_amendment_mutator_takes_the_row_lock`,
`test_read_only_amendment_paths_deliberately_do_not_lock`), and the claim is true because they
run, not because it was written down.

### Resolved: the anomalous full-suite run had a real mechanism

**Superseded by the eleventh pass.** The tenth pass recorded three unreproducible `F` markers in
the progress band containing `backend/tests/test_smoke_data_audit_events.py`, and proposed reruns
as the response. Independent review identified the cause instead, and it was worse than a flaky
count.

Those tests passed `("sales1",)` as the deletion allowlist and asserted exact counts such as
`deleted == 2`. `delete_login_events_after` deletes every matching login event above its boundary
globally, so any concurrent `sales1` login - another test, an E2E run, a person using the
application - **both** broke the count **and was itself deleted**. The failing assertion was the
visible symptom; the deletion of a real user's audit row was the actual defect.

The fix is isolation, not reruns. Each test now generates its own actor username, so its allowlist
scopes both the count and the deletion to rows it created. `residual == []` became "no
*allowlisted* actor appears in the residual", which is the property actually being asserted and is
immune to concurrent noise. The real `DEFAULT_E2E_ACTORS` tuple is still exercised by the
argument-validation tests, which write no rows, and
`backend/tooling/smoke_data/audit_events.py` itself is unchanged.

Verified: with a stray `sales1` login event deliberately inserted, all 20 tests pass and the stray
survives untouched. Under the previous version that stray would have been counted and destroyed.

### Acceptance status

**Not self-accepted.** One item remains open for the independent reviewer: the manual UI check
named earlier in this file (live confirmation that the success message survives the form
unmounting). The audit-event anomaly recorded by the tenth pass is closed - its mechanism is
identified and fixed above, not merely un-reproduced.


---

## Recorded acceptance result - eleventh correction pass, 8 September 2026

Three P2s and one P3; no P1. The tenth pass's six production fixes were confirmed correct by the
review; what this pass corrects is that two of them were not actually protected by a test, plus a
second concurrency gap in amendment creation.

| Check | Result |
| --- | --- |
| `pytest tests/test_slice_9b_pilot_hardening.py -q` | **83 passed** |
| `pytest tests/test_smoke_data_audit_events.py -q` | **20 passed** |
| `pytest -q` | **1108 passed, 0 failed** |
| `alembic current` / `heads` | `20260906_0032 (head)` - unchanged, no migration |
| Frontend typecheck / tests | clean / 54 passed (no frontend change this pass) |
| `check_tracked_secrets.py` | no findings |
| `validate_contract_fixtures.py` | 7 fixtures, all rules passed |

### Locks proven by deletion, not by reading

Every lock added in the last two passes was re-checked by removing it and confirming a named test
goes red. This is the check that would have caught the tenth pass's ineffective test immediately.

| Lock removed | Test that fails |
| --- | --- |
| `for_update=True` in `create_work_order_amendment_line` | `test_a_concurrent_cancellation_defeats_an_in_flight_amendment_line_add`, `test_every_amendment_mutator_takes_the_row_lock` |
| `for_update=True` in `create_work_order_amendment` | `test_a_concurrent_intake_would_collide_on_the_sequence_number_without_the_lock` (deadlock), `test_amendment_creation_locks_the_work_order_before_reading_its_amendments` |

Each mutated run was also checked for residue afterwards: zero seeded accounts, zero probe
amendments, zero probe audit rows. The intake test clears every amendment on its Work Order before
the manifest cleanup, because an earlier version let a regressed build leak a whole record set
when cleanup hit the Work Order foreign key.

### What the seven new tests assert

| Test | Property |
| --- | --- |
| `test_the_amendment_accessor_detection_finds_a_nonzero_number_of_paths` | the inventory below cannot pass vacuously |
| `test_the_set_of_amendment_accessors_is_exactly_the_known_set` | a new amendment path must be classified, not inherited |
| `test_every_amendment_mutator_takes_the_row_lock` | five of five mutators pass `for_update=True` |
| `test_read_only_amendment_paths_deliberately_do_not_lock` | the three read paths are not serialized behind a review |
| `test_amendment_creation_locks_the_work_order_before_reading_its_amendments` | the lock precedes both the duplicate check and the sequence read |
| `test_a_concurrent_cancellation_defeats_an_in_flight_amendment_line_add` | the aggregate-root lock, exercised |
| `test_a_concurrent_intake_would_collide_on_the_sequence_number_without_the_lock` | the Work Order lock, exercised |

### Acceptance status

**Not self-accepted.** The manual UI check named earlier in this file remains the one open item.


---

## Recorded acceptance result - twelfth correction pass, 8 September 2026

Three P2s and one P3; no P1. Two of the three P2s were guards that did not guard.

| Check | Result |
| --- | --- |
| `pytest tests/test_slice_9b_pilot_hardening.py -q` | **87 passed** |
| `pytest -q` | **1112 passed, 0 failed** |
| `alembic current` / `heads` | `20260906_0032 (head)` - unchanged, no migration |
| Frontend typecheck / tests / build | clean / 54 passed / clean |
| `check_tracked_secrets.py` | no findings |
| `validate_contract_fixtures.py` | 7 fixtures, all rules passed |

### Guards proven by decoy, not by reading

| Mutation | Test that fails |
| --- | --- |
| Remove `for_update=True` from a mutator, leave the words in a comment | `test_every_amendment_mutator_takes_the_row_lock`, `test_a_concurrent_cancellation_defeats_an_in_flight_amendment_line_add` |
| Replace the commercial-basis refusal message with a generic one | `test_a_concurrent_rejection_defeats_an_in_flight_amendment_validation` |

Both mutations were restored and the tests re-run green; no residue was left
(`TE1-SMOKE%` accounts: 0).

`_calls_with_keyword` additionally carries four tests of its own mechanism: the comment decoy, a
string-literal decoy, non-`True` values (`False`, `None`, a variable), and per-call reporting so a
second unlocked lookup beside a locked one cannot pass.

### Open items

Both remaining items need the same missing capability and are recorded in
`docs/agent/DEFERRED_REQUIREMENTS.md`:

- the manual UI check that the success confirmation survives the form unmounting;
- the reviewer's requested regression test for a successful `REJECTED_LOST` whose secondary
  refresh fails.

The browser-driver route has now been attempted twice and failed twice for the same reason: the
driver sets the date-time input's DOM value without triggering React's synthetic change event, so
the field is still reported as required on submit. No response was written and all seeded data was
removed. **A frontend behavioural test is the right instrument, and the frontend cannot currently
run one.**

### Acceptance status

**Not self-accepted.**
