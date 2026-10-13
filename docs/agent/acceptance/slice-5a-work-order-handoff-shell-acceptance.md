# Slice 5A Acceptance - Work Order Handoff Shell

## Automated checks

- Alembic head upgrades cleanly.
- Backend pytest passes.
- Frontend build passes.
- Frontend tests pass.

## Manual happy path

1. Login as `sales1 / password`.
2. Open an Accepted Commercial Offer with at least one active line.
3. Click `Create Work Order shell`.
4. Select one or more accepted offer lines.
5. Enter optional customer WO reference, received date and remarks.
6. Create the Work Order shell.
7. Confirm a `WO-` code is generated.
8. Confirm the Work Order profile shows Account, Opportunity, Commercial Offer and copied line context.

## Permission check

1. Login as `finance1 / password`.
2. Confirm Work Orders are visible.
3. Confirm creation from Commercial Offer is blocked by backend permission.

## Validation check

1. Try creating a Work Order from a non-Accepted Commercial Offer.
2. Confirm the backend blocks the action.
3. Try creating with no active lines selected.
4. Confirm the UI or backend blocks the action.

## Deferred checks

Confirm the Work Order profile clearly states that release/posting, Customer Master approval, equipment allocation, crew allocation, log sheets and billing are deferred.

## CS-04 part 1: each offer line's quantity once, whole or in parts (8 October 2026)

Added by TB-1 correction package 4 (`docs/continuity/TB1_103_WORK_ORDER_HANDOFF_ONCE_PER_LINE.md`). Test user
`sales1` (Sales); starting URL an Accepted Base Offer's page, Submission tab. Test data: an Accepted Base Offer with a
line of quantity 10 and a second line; an accepted Change Quotation and an accepted Supplementary Offer of it. The
seeded scenario `accepted-offer-no-work-order` gives the first; create the related offers from its page.

Positive path:

1. Open Create Work Order. Every line is ticked, each with a quantity box holding its whole quantity.
2. Change line 1's quantity to 6, untick line 2, create. The Work Order holds 6 of line 1, at 6 times the rate.
3. Back on the offer page, "Create another Work Order" is offered. On the Create page, line 1 shows "On a Work Order:
   WO-... (6). Left: 4"; create with both lines. The second Work Order holds 4 of line 1 and all of line 2.
4. The offer page now says "Every line of this offer is already on a Work Order in full." and offers no Create.
5. An accepted Supplementary Offer's page offers Create Work Order; creating one works.

Negative path:

1. With 4 of line 1 left, a second browser tab still showing 10 left asks for 6: refused beside the button, naming the
   Work Order and "4 of 10 left". Nothing is created.
2. An accepted Change Quotation offers no Create; its page says to cite it on an amendment. Opened directly at
   `/work-orders/new?commercialOfferId=...`, the button is disabled with that reason.
3. Record "On hold" as the customer's latest response on an Accepted offer with something left: no Create; the reason
   names the latest response. Record the acceptance again (dated after it): Create returns.
4. On an offer with a Work Order, record the customer response "Rejected / lost": refused with a message naming the
   Work Order; the offer stays Accepted and no response is added.

Permission check: unchanged - `finance1` sees Work Orders and cannot create one.

Customer reference (the owner's rule after review round 3): Create without a Customer WO reference is refused beside
the button. Create with a reference already on a Work Order of this offer - typed in another case, with spaces - is
refused, naming that Work Order; the same request in a second tab is refused the same way. A Supplementary Offer's
Work Order may carry the same reference as the Base Offer's.
