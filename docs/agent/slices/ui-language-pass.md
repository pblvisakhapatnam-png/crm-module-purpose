# UI Language Pass and Tester Guide

Follows the UI cleanup reskin, step 4 of the road to the UAT pilot
(`docs/continuity/NEXT_STEPS.md`). Foundation Slice Mode.

## Status

Implemented 11 September 2026 on branch `ui-language-pass`, base commit `8b7b5ff` (PR #34 merge).
Accepted by independent review in round 4 and merged to `main` through PR #35 as `22ba9fc` on
11 September 2026. (As committed, this line read "uncommitted, pending independent review": the
commit had to reproduce the reviewed tree exactly, so the outcome is recorded here by the next
package.)

**Status update, 11 September 2026:** accepted after independent review and merged to `main`
through PR #35 (merge commit `22ba9fc`). The sentence above describes the reviewed tree, which the
commit had to reproduce exactly.

No migration: Alembic head unchanged at `20260908_0035`. No route, permission, request or response
field, status code, business-event name or identifier changed. The frozen Accepted Offer -> Work
Order handoff contract is unchanged: `HANDOFF_CREATED` stays the Work Order status code, and only
the words shown for it change.

## Owner decisions, 11 September 2026

The project owner listed six terms a tester would not understand - "Handoff provenance", "Work
Order Shells", "New revision cycle allowed", "Open revision awaiting resubmission", "Another
customer response allowed", "Work Order handoff" - and asked for the language to change or for a
plain guide to each part of the CRM. Testers and reviewers also need to be told why a Work Order is
created and how the hand-over to the Hiring or Transportation module works.

| Question | Decision |
| --- | --- |
| "Work Order shell" | Call it a **Work Order**, with its status shown as **Awaiting release to Ops**. The owner's reasoning: it records the whole awarded order, so "shell" misdescribes it; what is missing is release, and the status should say so. |
| Status-panel labels | The wording in the table below. |
| Guide | Both: a document in the repository, and a shareable web page. |
| Backend "Slice N" wording | Included in this package, not left for later. |

| Before | After |
| --- | --- |
| New revision cycle allowed | Can start a revised offer |
| Open revision awaiting resubmission | Revised offer in progress, not yet re-sent |
| Another customer response allowed | Can record a customer response |
| Work Order handoff | Ready to create the Work Order |
| Work Order handoff review | Before you create the Work Order |
| Handoff provenance | How this Work Order was created |

## What changed

### Frontend

- **Work Order status.** `HANDOFF_CREATED` is shown as "Awaiting release to Ops" wherever a Work
  Order status appears: Work Order list, detail and create pages, the Commercial Offer page, the
  amendment and related-offer pages, and the dashboard. One shared helper,
  `formatWorkOrderStatusLabel` in `frontend/src/components/PageLayout.tsx`, does it. The Work
  Order page shows one status badge where it used to show both "Handoff shell" and "Handoff
  Created".
- **"Work Order shell" becomes "Work Order"** in every user-visible string, including the menu,
  the sidebar step guide, buttons ("Create Work Order", "Open Work Order") and messages.
- **Commercial Offer page.** The status-panel labels above. Revisions are "revised offers": the
  section is "Revised offers", the actions are "Start revised offer" and "Mark as re-sent", and a
  revision's status shows as In progress, Re-sent or Cancelled. Readiness items not yet built show
  "Not built yet" instead of "Deferred". Six messages that ended "for traceability" now say what
  happened.
- **Work Order page.** "Handoff provenance" is "How this Work Order was created". The "Later steps"
  list said its steps come after release to Ops while two of them were the release itself; it now
  says the Hiring or Transportation module adds them, in the order the guide gives.
- **Dashboard.** Status and purpose columns show words ("Quote Pending", "Change Quotation")
  instead of codes. "Demo", "prototype" and "handoff" wording removed.
- **Elsewhere.** "Prototype", "foundation", "source-derived", "seeded" and "Account traceability"
  wording removed from page text and messages. The login page says "Test users"; its prefilled
  credentials are unchanged, because the pilot deployment handles them.

### Backend

About 45 user-visible messages reworded, with no code change around them: the lifecycle labels,
the lifecycle guidance, business-event reasons that read "through Slice N foundation API",
validation errors naming a slice, readiness notes beginning "Future control. This slice...", and
every "Account traceability is missing" message, which now says the Opportunity is not linked to an
Account and what to do. The submission-readiness checklist's items for revised offers, the
Account and Opportunity links and the submitted record were reworded the same way; their codes
are unchanged. Seven test assertions were updated to the new wording, each still a substring
check of the same strength.

### Tests

Text assertions in seven Playwright specs follow the new wording. Their test titles still say
"shell"; titles are not user-visible.

The sentence "No Work Order has been created yet from this Commercial Offer." is kept word for
word on the Commercial Offer and Create Work Order pages, because two Playwright specs check it.
The first end-to-end run failed on exactly this: the Commercial Offer page had reworded it. The
fix restored the shared sentence rather than loosening the check.

### Documents

- **New:** `docs/uat/PBL_CRM_TESTER_GUIDE.md`, the plain guide to each screen, with the Work Order
  explanation, a glossary of the status-panel labels, what is not built, and how to report a
  problem. The same content is published as a private shareable page for the owner to pass on.
- **Data sheet:** logins are no longer printed with passwords, which are given to testers
  separately; wording follows the new screen labels.
- **Runbook:** links to the guide; "Work Order shells" is "Work Orders"; the long-page note says
  what the reskin did and did not do.
- **Contracts:** the Work Order contract records the display label. No contract quotes a changed
  message, which was checked before the messages were changed.

## Data-sheet steps that would have stopped a tester

Aligning the data sheet with the new labels, then reading it as a tester would, showed five places
where the typed-in half of the pilot would have stopped, independent of any wording:

1. **Step 6** created an Opportunity by hand. A hand-made Opportunity is not linked to an Account,
   and quotation generation refuses an offer without one. The step now links it.
2. **Step 7** added market rates to "the Opportunity's Commercial Offer", which no step had
   created. It now creates one first; Step 9 does the same for its customer.
3. **Step 10** added conversations to "the Kakinada Steel quotation". The Commercial Offer page has
   no conversation log; it is on the Lead, Account and Opportunity pages, and a conversation logged
   on the Opportunity counts for its offer. The step now uses the Opportunity.
4. **Step 11** recorded a customer response on an offer that had never been submitted, which the
   system refuses. It now records the submission first.
5. **Step 12** uploaded a file against the Commercial Offer. No screen lets a tester do that: the
   only upload control is a test tool on the Documents page that always files to one fixed sample
   Account as document type KYC. The step now checks the stored quotation files instead, and the
   data sheet and the guide list uploading as not built yet. It is not a wording fix: the owner
   decided on 11 September 2026 to build an upload control before the pilot, as its own package.

## Deliberately not changed

- Identifiers, status and field codes (`HANDOFF_CREATED`, `with_work_order_shell`), API paths
  (`/api/reports/work-order-handoff`), code comments, docstrings and test titles.
- Wording still to consider, recorded in `docs/agent/UI_UX_CARRY_FORWARD.md`: network errors that
  say "Check that the backend and frontend services are running."; "intake" on the amendment
  pages; the "Future SharePoint reference" storage option; the button "Record as Submitted /
  Commercially Committed"; raw status codes in list pages other than the dashboard; credit review
  messages that show the raw review code; and the "Login first..." messages, which remain in about
  eighty places in several wordings.
- The Work Order page has two rows labelled "Created at": one in the summary, one under "How this
  Work Order was created".

## Checks

See `docs/agent/acceptance/ui-language-pass-acceptance.md`.
