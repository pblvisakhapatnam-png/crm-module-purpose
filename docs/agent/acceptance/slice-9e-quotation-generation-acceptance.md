# Slice 9E Acceptance - Quotation Generation

Written so a later tester can perform regression/UAT without this session's chat history.

## Preconditions

Stack running, Alembic at `20260908_0034 (head)` before this slice. This slice adds a
migration but no new Python dependency; after merging, rebuild the backend image before
testing (the migration file lives under `backend/alembic/versions/`, which is baked into the
image at build time, not bind-mounted):

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| New Slice 9E regression file | `docker compose exec backend pytest tests/test_slice_9e_quotation_generation.py -q` | 52 passed - 32 as first delivered, +11 from correction pass 1, +9 from correction pass 2 |
| Route migration guard (pins all 3 new routes to their exact permissions, and the frozen counts) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py -q` | 99 passed |
| Pre-existing Commercial Offer readiness tests (2 corrected by this slice - see continuity note) | `docker compose exec backend pytest tests/test_commercial_offers_api.py -q` | all pass |
| Pre-existing Slice 9C tests (2 corrected by this slice - a latent scoping bug, not a 9E regression - see continuity note) | `docker compose exec backend pytest tests/test_slice_9c_document_storage_foundation.py -q` | all pass |
| Full backend regression | `docker compose exec backend pytest -q` | see continuity note for the exact count and the flakiness investigation |
| Alembic head | `docker compose exec backend alembic current` | `20260908_0035 (head)` |
| Schema inspected directly | `psql -c "\d crm_commercial_offer_quote_document"` | 16 columns, `ck_quote_document_status`, `ck_quote_document_approval_is_complete`, `ux_quote_document_offer_version` unique constraint, all present exactly as designed |
| CHECK constraint holds against a direct INSERT | see `test_a_direct_insert_claiming_approved_without_an_approver_is_refused_by_the_database` and its DRAFT-with-approver counterpart | both refused by PostgreSQL, not merely by the API |
| Permission seed inspected directly | `SELECT ... FROM authz_permission JOIN authz_role_permission ...` | `COMMERCIAL_OFFER_QUOTE_GENERATE` granted to ADMIN/SALES_USER/SALES_MANAGER (3 rows); `COMMERCIAL_OFFER_QUOTE_APPROVE` granted to ADMIN/SALES_MANAGER only (2 rows) |
| Frontend typecheck | `MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run typecheck` | clean |
| Frontend tests | same, `npm test` | 54 passed (unchanged - no new public URL was added; this slice adds backend routes and a UI section on the existing Commercial Offer detail page, not a new page) |
| Frontend build | same, `npm run build` | clean |
| App import / route registration | `python -c "from app.main import app; ..."` | 3 new `/api/commercial-offers/*/quote-documents*` routes present |

## Manual happy path

Test user `sales1` / `password` (SALES_USER). Starting page: `/commercial-offers/{id}` for a
Draft or Submitted offer with at least one active line and Account traceability, on the
**Submission** tab.

1. Scroll to the **Quotation Document** section (between Submission Readiness and Record as
   Submitted). Confirm it shows "No quotation document has been generated yet."
2. Click **Generate quotation document**. Confirm a green "Quotation document CO-.../V1
   generated as Draft." message appears directly under the button, and a new card appears
   showing `CO-.../V1`, status **Draft**, a Download button, and (for `sales1`) **no** Approve
   button.
3. Click **Download**. Confirm the browser downloads an `.html` file. Open it - confirm it
   shows PBL's identity, the offer's Account name, active lines with quantities/rates/amounts,
   a total marked "EXCLUSIVE OF GST", and any attached header T&C clause text. Confirm it does
   **not** show pricing evidence, the selected basis rate, or any credit-review information.
4. Log out, log in as `manager1` / `password` (SALES_MANAGER). Return to the same offer's
   Submission tab. Confirm the same Draft version now shows an **Approve for Issue** button.
5. Click it. Confirm a green "Approved for issue: CO-.../V1." message appears under that
   specific version's own row (not only at the top of the page), the status badge changes to
   **Approved for Issue**, and Approved at / Approval note fields populate.
6. Return to the Submission Readiness panel above (reload the page). Confirm the
   **Quotation document approved for issue** row now shows **PASS**.

Expected result: a quote is generated as Draft, downloaded, and approved for issue by an
authorised role, with per-action feedback beside the triggering button throughout.

## Manual permission path

Test users: `sales1` / `password` (SALES_USER), `manager1` / `password` (SALES_MANAGER),
`admin1` / `password` (ADMIN).

1. As `sales1`, generate a quotation document (as above). Confirm the version appears with
   **no** Approve button visible (frontend role gating).
2. As `sales1`, attempt `POST /api/commercial-offers/{id}/quote-documents/{qid}/approve`
   directly (e.g. via a REST client). Confirm `403 Forbidden`.
3. As `manager1` or `admin1`, repeat step 2. Confirm `200` and the version becomes Approved for
   Issue.
4. As `readonly1` / `password` (MANAGEMENT_READ_ONLY), open the same offer's Submission tab.
   Confirm the Quotation Document section is visible (read access), the Download button works,
   but no Generate or Approve action is offered.

Expected result: generation follows the existing Commercial Offer create/manage role set;
approval is restricted to Sales Manager and Admin only, enforced by the backend regardless of
what the frontend shows.

## Manual validation path

1. On an `ACCEPTED`, `REJECTED`, `WITHDRAWN` or `CLOSED` offer, attempt
   `POST .../quote-documents`. Confirm `422` naming the current status.
2. On an offer with Account traceability missing, attempt the same. Confirm `422` naming the
   missing Account traceability.
3. On an offer with zero active lines, attempt the same. Confirm `422` naming the missing
   active line.
4. Generate a second version (V2) for an offer that already has an approved V1. Confirm V1 is
   now shown as "(superseded)" but **still shows its Approved for Issue status, approver and
   timestamp** - generating a new version must never erase an earlier version's own approval
   history.
5. Attempt to approve an already-approved version, or a superseded version. Confirm `422` in
   both cases, with a message naming the specific reason (already approved / superseded).
6. Edit the offer (e.g. add another line) after generating a quote. Reload the Submission tab.
   Confirm the existing version now shows a staleness notice ("The offer has changed since this
   version was generated...") while its downloaded content remains byte-for-byte identical to
   what was generated - staleness is advisory, never a block on downloading or approving that
   version.

## Correction pass 1 manual checks

Added after independent review. Each confirms a corrected finding through the normal application.

1. **The issued document does not say Draft.** Generate a quotation, approve it, download it, and
   open the file. Confirm it shows Quote Reference, Version, Generated, **Prepared by** and a
   closing line saying issue approval is recorded in the CRM against that quote reference - and
   that the word "Draft" appears nowhere in the document.
2. **An unapproved version is labelled at the point of download.** On a version still in Draft,
   confirm the button reads **"Download draft (not approved for issue)"**, and that it reads
   plain "Download" once the version is approved. This is where the Draft/approved distinction
   lives now that the frozen document cannot carry it.
3. **The preparer and approver are visible.** On a version generated by one user and approved by
   another, confirm the card shows **Prepared by** and **Approved by** with recognisable names,
   not bare identifiers.
4. **Account identity is filtered.** On an Account carrying a site, draft-billing or other
   address, and a GSTIN marked `REJECTED_INCORRECT`, generate a quotation and confirm the
   document shows only the registered-office and communication addresses (each labelled) and does
   not show the rejected GSTIN.
5. **An unpriced quotation does not claim a zero total.** On an offer whose active lines carry no
   rate, generate and confirm the total reads **"Not priced"** rather than `0.00`.
6. **Feedback does not follow you between offers.** Generate or approve on one offer, then
   navigate to a different Commercial Offer's Submission tab. Confirm no quotation confirmation
   from the previous offer is still displayed - and, separately, that approving a version still
   shows its confirmation on the version's own card (the message must survive the list reload
   that immediately follows it).

## Correction pass 2 manual checks

1. **A Draft document does not claim approval exists.** Generate a quotation and download it
   without approving. Confirm the footer reads **"Verify the current issue-approval status ... in
   the PBL CRM system against quote reference ..."** and does **not** say approval "is recorded".
   Approve it, download again, and confirm the wording is unchanged and the file is identical.
2. **A partly priced quotation shows no numeric total.** On an offer with one priced line and one
   line with no rate, generate and confirm the total reads **"Not fully priced"** and not a
   number. With no line priced at all, confirm it reads **"Not priced"**.
3. **Approval is refused once the offer has concluded.** Generate a quotation, then move the
   offer to Rejected through the Customer Response action (or Withdrawn/Closed through the edit
   form). Attempt to approve the quotation. Confirm `422` with a message saying the offer has
   concluded, and that the version is still Draft.

## Known limitations / deferred (see `docs/agent/DEFERRED_REQUIREMENTS.md`)

- No server-side PDF rendering; the frozen/stored artifact is HTML, and the customer's PDF is
  produced by the browser's own Print dialog, outside the system.
- The frozen document does not display its own approval status, because generation always
  precedes approval and the bytes are never rewritten. A Draft download and an approved download
  are therefore byte-identical; the UI labels the unapproved download, and the system record
  remains authoritative. Making the issued document itself assert "Approved for Issue" is a
  separate approved-artifact design needing owner confirmation.
- Generation is **deliberately not blocked** when an offer's lines are unpriced or only partly
  priced; the document says "Not priced" / "Not fully priced" rather than a number. Owner
  decision of 9 September 2026: allowed during the pilot, to be blocked afterwards. Trigger and
  the work involved are recorded in `docs/agent/DEFERRED_REQUIREMENTS.md`.
- Approval for issue **is** blocked once the offer is Accepted, Rejected, Withdrawn or Closed
  (owner decision, 9 September 2026).
- Approval is a procedural control with an audit record, not an access control - a Draft
  version is downloadable by anyone who can already read the offer, and a Sales Manager may
  both prepare and approve their own quote (full maker-checker needs `APR-001`).
- No margin-threshold evaluation or approval.
- No audit record of who downloaded a generated quote's content - inherits the existing
  Slice 9C/9D open policy question, extended, not duplicated.
- Retention (`document_metadata.retention_due_at`) is shape-only for a generated quote exactly
  as for any other document; nothing purges against it.
- The FRD's "communications logged before a quote is raised" rule is advisory
  (`INTERACTION_LOG` readiness row) only, per the existing `interaction-contract.md` decision.

## Lines in more than one currency (12 October 2026)

Added by the vendor-baseline package A, which makes the quotation total each currency separately (the Commercial Offer
contract, "Quotation totals per currency"). Test user `sales1` (Sales User); approval as `manager1`.

1. Open a Draft Commercial Offer in INR that has at least one priced line in INR. On **Lines & Pricing** add a line in
   `USD` with *Quantity* `2` and *Rate amount* `137.50`.
2. On **Submission**, press **Generate quotation document** and open the new version. **Pass if** the header reads
   "Currencies: INR, USD"; every rate and amount shows its currency code; there are two total rows, "Total (INR)" with
   the INR lines' sum and "Total (USD)" with `275.00`; no figure adds the two together; and a note under the GST note
   says each currency is totalled separately.
3. Add a second `USD` line with no *Rate amount* and generate again. **Pass if** "Total (USD)" reads "Not fully priced"
   while "Total (INR)" still shows its sum.
4. On an offer whose lines are all in its own currency, generate a quotation. **Pass if** it looks exactly as before:
   "Currency: INR", one "Total (INR)" row, no currency codes beside the amounts, no extra note.
5. Negative: a version generated for an offer with a line in another currency **before** this package reports, on the
   Submission tab, that the offer has changed since it was generated, and `manager1` cannot approve it for issue.
   Generate a new version; it can be approved once every line is priced.
