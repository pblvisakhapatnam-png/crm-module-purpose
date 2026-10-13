# One person doing every sheet

Use this route **only when one person does all four testers' sheets**. It runs the four sheets in the one order that
works: each block signs in as one tester, does the steps listed, then signs out. Do the steps exactly as the sheet for
that tester says, with that tester's data - never your own - and record each step's **Pass** or **Fail** in **that
tester's** tab of the Feedback Log.

Open the four sheets side by side:
[Tester 1](PBL_CRM_UAT_TESTER_1_SALES.md),
[Tester 2](PBL_CRM_UAT_TESTER_2_SALES_MANAGER.md),
[Tester 3](PBL_CRM_UAT_TESTER_3_OPERATIONS.md),
[Tester 4](PBL_CRM_UAT_TESTER_4_ACCOUNTS.md).
Where a sheet says "Tell Tester N", there is nobody to tell: the next block is you, as Tester N.

**Sign out** (top of the page) between blocks, then sign in as the next login. Signing in again with the browser's
Back button is not the same: use **Sign out**.

| # | Sign in as | Sheet | Steps | What it does |
| --- | --- | --- | --- | --- |
| 1 | `uat-operations-01` | Tester 3 | 1 | What Operations may not make |
| 2 | `uat-finance-01` | Tester 4 | 1 | What Accounts may not make |
| 3 | `uat-sales-01` | Tester 1 | 1 to 12 | Two Leads, the customer, the enquiry, the offer and its lines. Write down the offer's code |
| 4 | `uat-operations-01` | Tester 3 | 2 | Market rates on lines 1 and 3 of Tester 1's offer, and the vendor's quote |
| 5 | `uat-sales-01` | Tester 1 | 13 to 16 | Terms, each line's basis rate, the draft quotation |
| 6 | `uat-manager-01` | Tester 2 | 1, then 3 to 5, then 6 up to "You need not wait" | Approve Tester 1's quotation; then the euro customer, enquiry and offer, and ask Operations for its rates. Write down this offer's code |
| 7 | `uat-operations-01` | Tester 3 | 3 to 6 | The euro rates on Tester 2's offer; choosing the basis; what Operations may not change; a file |
| 8 | `uat-manager-01` | Tester 2 | 6 from "Once they say so", then 7 to 11 | Line 1's basis rate and its history, the unpriced quotation, the out-of-date version, two currencies |
| 9 | `uat-finance-01` | Tester 4 | 2 to 9 | Check the three customers' numbers; a document; wrong numbers |
| 10 | `uat-sales-01` | Tester 1 | 17 to 22, then 23 up to "Tell Tester 2" | Send it; the negotiation; version 2 and its quotation |
| 11 | `uat-manager-01` | Tester 2 | 2 | Approve version 2's quotation |
| 12 | `uat-sales-01` | Tester 1 | the rest of 23, then 24 and 25 | Send version 2; the customer's yes |
| 13 | `uat-operations-01` | Tester 3 | 7 to 10 | Tester 1's Work Order |
| 14 | `uat-sales-01` | Tester 1 | 26 to 28 | Read the Work Order; a file; what Sales may not do |
| 15 | `uat-manager-01` | Tester 2 | 12 to 20 | The order in two parts; an amendment; what a Manager may not do |
| 16 | `uat-finance-01` | Tester 4 | 10 and 11 | What Accounts may not change |
| 17 | `uat-manager-01` | [Your own data](PBL_CRM_UAT_YOUR_OWN_DATA.md) | all | Your own work, names starting `OWN-T1-`, numbers from Tester 1's block. The Sales Manager can do every step: enquiries to Work Orders, market rates, quotations and their approval |

Steps that a sheet marks "Waits for ..." are recorded as **Not done** until the sheet is updated.

At the end every tab of the Feedback Log should have a result on every step. A step you could not reach because an
earlier one failed is **Could not try**, with the earlier step's number in the notes.
