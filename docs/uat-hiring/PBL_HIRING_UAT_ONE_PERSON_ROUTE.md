# One person doing every sheet

Use this route **only when one person does all four testers' sheets**. It runs the four sheets in the one order that
works: each block signs in as one tester, does the steps listed, then signs out. Do the steps exactly as the sheet for
that tester says, with that tester's data - never your own - and record each step's **Pass** or **Fail** in **that
tester's** tab of the Feedback Log.

Open the four sheets side by side:
[Tester 1](PBL_HIRING_UAT_TESTER_1_SALES.md),
[Tester 2](PBL_HIRING_UAT_TESTER_2_FLEET_ADMIN.md),
[Tester 3](PBL_HIRING_UAT_TESTER_3_OPERATIONS.md),
[Tester 4](PBL_HIRING_UAT_TESTER_4_ACCOUNTS.md).
Where a sheet says "Tell Tester N" or "Wait for Tester N", there is nobody to tell or wait for: the block that does it
is listed below.

**Sign out** between blocks, then sign in as the next login.

| # | Sign in as | Sheet | Steps | What it does |
| --- | --- | --- | --- | --- |
| 1 | `uat-fleet-01` | Tester 2 | 1 to 8 | Look at the fleet; Plum's second report; papers; a renewal's copy |
| 2 | `uat-operations-01` | Tester 3 | 1 and 2 | A machine's papers for a site; Operations' reminders |
| 3 | `uat-finance-01` | Tester 4 | 1 to 3 | The calendar; a machine for a site; what Accounts may not do |
| 4 | `uat-sales-01` | Tester 1 | 1 to 12 | The customer, the offer, the customer's yes, two Work Orders; the first one's sites, contract, terms and holidays |
| 5 | `uat-operations-01` | Tester 3 | 3 to 7 | The first Work Order's requirements, two crawlers, kit on trips, the yard crane |
| 6 | `uat-fleet-01` | Tester 2 | 9 to 17 | The new examination on UAT-CC250-02; a mistake withdrawn; a test state rule; more kit; the holiday calendar |
| 7 | `uat-operations-01` | Tester 3 | 8 | **Check again** on UAT-CC250-02 |
| 8 | `uat-sales-01` | Tester 1 | 13 | The second Work Order |
| 9 | `uat-operations-01` | Tester 3 | 9 to 13 | The refinery: the answers, allocate and replace, a trip; what Operations may not do |
| 10 | `uat-sales-01` | Tester 1 | 14 to 17 | The billing cycle; read the plans; what Sales may not do |
| 11 | `uat-finance-01` | Tester 4 | 4 to 12 | Read the terms, contract, holidays and machines as the person who bills |
| 12 | `uat-fleet-01` | Tester 2 | 18 and 19 | Reminder settings |
| 13 | `uat-fleet-01` | [Your own data](PBL_HIRING_UAT_YOUR_OWN_DATA.md) | all | Your own work, names starting `OWN-T1-`, numbers from Tester 1's block. The Fleet Admin login is an Admin: it can do every step - customers to Work Orders, requirements and allocations, papers, kit and rules |

In block 6, step 17 asks another tester to confirm they cannot change the calendar: do it yourself in block 11 (Tester
4's step 1 covers it). Block 1 confirmed Plum's second report, so in block 5 the crawlers include **UAT-CC250-07** and
in block 9 the all-terrain cranes include **UAT-AC100-10**, both with nothing recorded; and in block 9 UAT-AC100-07 and
UAT-AC100-09 answer **Can be allocated**: block 1 recorded their papers.

Steps that a sheet marks "Waits for ..." are recorded as **Not done** until the sheet is updated. A step you could not
reach because an earlier one failed is **Could not try**, with the earlier step's number in the notes.
