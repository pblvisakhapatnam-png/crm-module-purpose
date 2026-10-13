# Slice 6L Acceptance - Commercial Offer Customer Response / Award Outcome Foundation

## Automated Checks

- [x] Migration `20260712_0027` applied; current/head report `20260712_0027`.
- [x] Commercial Offer focused regression: 42 passed (`pytest tests/test_commercial_offers_api.py -q`).
- [x] Full backend suite: 139 passed (`pytest`).
- [x] `git diff --check` passed.
- [x] Frontend production build passed (`npm run build`) after clearing `.next`.
- [x] Frontend test script passed (reports automated frontend tests are not configured, consistent with prior slices).

## Human UAT

Test user: `sales1`; permission user: `readonly1`.

Starting route: `/commercial-offers/{submitted-commercial-offer-public-id}`, Submission tab.

Test data used for this pass: two Account/Opportunity/Commercial Offer chains were created via API and driven through the running app in the Browser pane (`http://localhost:3000`).

- [x] Confirm Customer Response / Award Outcome appears after Revisions and before Submission Evidence. Verified in rendered page text.
- [x] Record `CLARIFICATION_REQUESTED`; confirm response history/readiness updates and offer remains Submitted. Verified: offer stayed `SUBMITTED`, readiness item showed `ATTENTION_REQUIRED` / "Customer requested revision/clarification.", success message "No Work Order was created automatically." shown.
- [x] Record `ACCEPTED_AWARDED` (same offer, second response); confirm latest response and offer status Accepted. Verified: offer moved to `ACCEPTED`, `outcome_date`/`outcome_remarks` set, both responses retained in history (append-only, latest first).
- [x] Confirm no Work Order appears automatically. Verified: `GET /api/work-orders?commercial_offer_public_id=...` returned `[]` after the Accepted response.
- [x] Use the existing separate accepted-offer Work Order shell action; confirm the frozen handoff still works. Verified: `Create Work Order shell` link still present on the Accepted offer and `/work-orders/new?commercialOfferId=...` still loads the source offer, Account/Opportunity context and active line correctly.
- [x] On a separate offer record `REJECTED_LOST`; confirm status Rejected. Verified via a second Submitted offer.
- [x] Confirm long evidence/revision labels remain contained and full selected details appear below selectors. Verified visually in rendered section (compact dropdown option labels plus a "Selected evidence/revision" detail line); no layout overflow observed.
- [x] Confirm `readonly1` sees history but not the create form; backend POST returns 403. Verified: page text contained "Customer response history is visible to your role. Recording is restricted to Sales and Admin roles." and no "Record new customer response" form; `POST .../customer-responses` returned 403 for `readonly1` and 200 for the `GET` list.
- [x] Confirm Revisions, Submission Evidence, Credit / Exposure Review, T&C and linked Work Orders still render. Verified in page text for both roles.

## Expected Result

Response history is append-only and readable; clear award/loss aligns lifecycle status; attention outcomes do not force status; no automatic Work Order, Customer Master, approval, billing, document or execution action occurs. All of the above was confirmed against the running application.

## Notes on method

The Browser pane's accessibility-tree reader stopped enumerating interactive elements partway down this long tabbed page (a tool-side limitation, not an application defect — `document.querySelectorAll` confirmed all expected inputs/selects/buttons were present in the DOM). Form interaction for the deeper Submission-tab sections was driven via in-page JavaScript (native value setters + `input`/`change` events + real `click()` on the actual submit button), which exercises the same React handlers and network calls as a manual click. Read-only verification (`readonly1`) and page text were confirmed the same way. No source code was written via this method; it was used only to operate the existing UI.

## Deferred / Manual Gaps

Full award-to-Work-Order readiness gating, partial-award handling and production approval controls remain future work, as originally scoped.
