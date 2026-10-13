# Slice 7C Acceptance - Work Order Line Operational Detail

Written so a later tester can perform regression/UAT without this session's chat history. Design
and owner decisions: `docs/agent/slices/slice-7c-work-order-line-operational-detail.md`.

**Changed by Slice 7D, 14 September 2026.** The billing basis and contracted hours are no longer in the
Site and billing details section; the steps below that set them are now performed in the **Billing
terms** section (`docs/agent/acceptance/slice-7d-work-order-line-billing-terms-acceptance.md`), and the
missing items here are site, billing GSTIN and billing address only.

## Preconditions

Stack running. This slice adds migration `20260908_0036`; `alembic/` is baked into the backend
image, so after merging rebuild before testing:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic current
```

Expected: `20260908_0036 (head)`.

Frozen contract check, before and after:

```bash
sha256sum docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
```

Expected: `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| Slice 7C tests | `docker compose exec backend pytest tests/test_slice_7c_work_order_line_detail.py -q` | 41 passed (40 at merge, +1 in the follow-up) |
| Harness cleanup of a line detail | `docker compose exec backend pytest tests/test_smoke_data_harness.py -q -k line_detail` | 1 passed |
| Route guard (pins both new routes to their exact permission) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py -q` | all pass |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | recorded in the continuity note |
| Empty database to head, then `downgrade -1` and `upgrade head` | scratch database or fresh volume | clean both ways; table and permission rows removed on downgrade |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; route tests unchanged (no new URL); `workOrderLineDetailState.test.ts` added |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |

## Test data

Any accepted Commercial Offer with a Work Order. On the Work Order's **Account**, add first:

- one address of type **Site**;
- one address of type **Registered Office** (or **Billing**);
- one GST number.

## Manual happy path

User `sales1` (Sales User). Start at `/work-orders/{id}`.

1. In **Lines**, the new **Site and billing** column shows "Missing: site, billing GSTIN, billing
   address, billing basis" for every line.
2. Scroll to **Site and billing details**. For line 1 pick the Site, the GST number and the
   Registered Office address; choose billing basis **Shift**; enter **8** contracted hours; enter a
   customer line reference. Click **Save details**.
3. Expected: "Details saved." appears directly under the button; the card badge and the Lines
   column both read "Details complete", and the Lines column also shows the site city and
   "Billed by shift".
4. While the page is still loading, the line forms show no Save button until the saved details
   have arrived ("Loading the saved details...").
5. Change billing basis to **Hour**. The hours field disappears. Save. Expected: saved, still complete.
6. Click **Save details** again without changing anything. Expected: "Nothing changed, so nothing
   was saved."

## Follow-up checks (7C.1)

1. **Spacing.** In an open line card every label sits on its own line above its field, with visible
   space between one field and the next; the Notes label is above the notes box.
2. **Collapse.** Reload the Work Order: a line with missing details is open, a complete line is
   closed and its summary reads e.g. "Line 1 - ... (Pune - Shift)" with "Details complete".
3. Open a complete line, change a field and save: the card stays open.
4. On a Work Order with two or more lines, **Collapse all lines** closes every card and **Expand all
   lines** opens them.

## Manual negative and permission paths

1. **Conflict.** Open the same Work Order in two tabs as `sales1`. Save a change in tab A, then save
   a different change in tab B without reloading. Expected in tab B: "Someone else changed these
   details. Reload to see their version." Nothing from tab B is stored.
2. **No site on the Account.** On a Work Order whose Account has no Site address, the Site list is
   empty and the card says to add it on the Account first.
3. **Read-only.** Sign in as `finance1`. The section shows the saved values with no form and no
   Save button. A direct `PUT` returns `403`.
4. **Closed Work Order.** Not reachable from the screen today (nothing closes a Work Order); covered
   by `test_a_closed_work_order_refuses_changes`.

## Deferred, and not a defect

- No release block on incomplete details - that is Work Order release (7B).
- No lock at mobilisation or e-invoice - neither event exists yet.
- Overtime, breakdown, standby, minimum guarantee, mobilisation and fuel terms - Slice 7D.
- A GSTIN cannot yet be marked rejected after entry from the Account screen, so the "reads as
  missing again" behaviour is exercised only by tests that set the state in the database.
- No Playwright spec; frontend has no component tests (`DEFERRED_REQUIREMENTS.md`).
