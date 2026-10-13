# PBL Hiring User Test - Guide for Testers

How this test runs. **What the system does is in the User Guide** - read that first, and keep it open while you test.

## What the test is

- It tests the **Hiring part** of PBL's new system: from an accepted offer to Work Orders with their sites, terms and
  holidays, machines allocated, their papers checked, and the reminders that follow.
- The site is **the Hiring test site** - not the CRM test's site.
- It starts with only **PBL's machines** - invented, from an invented Plum report, with their papers - and **PBL's
  holiday calendar** for this year and next. Every customer, offer and Work Order is typed in by a tester.
- **All the data is invented.** Every machine begins `UAT-`. Never type a real customer, rate, registration number or
  certificate number.

## Signing in

You sign in twice:

1. A **shared site login** (a box the browser shows). It keeps the site private.
2. **Your own username and password.** What you can see and do depends on your job.

Both are given to you separately. Do not share them. Your username and password are the same as on the CRM test site.

## Who does what

Up to four testers, each with **one job and one set of data**:

| Tester | Job | Sign in as | Your sheet |
| --- | --- | --- | --- |
| 1 | Sales | `uat-sales-01` | [Tester 1 - Sales](PBL_HIRING_UAT_TESTER_1_SALES.md) |
| 2 | Fleet Admin | `uat-fleet-01` | [Tester 2 - Fleet Admin](PBL_HIRING_UAT_TESTER_2_FLEET_ADMIN.md) |
| 3 | Operations | `uat-operations-01` | [Tester 3 - Operations](PBL_HIRING_UAT_TESTER_3_OPERATIONS.md) |
| 4 | Accounts | `uat-finance-01` | [Tester 4 - Accounts](PBL_HIRING_UAT_TESTER_4_ACCOUNTS.md) |

When one person does all four, they follow the [one-person route](PBL_HIRING_UAT_ONE_PERSON_ROUTE.md): which login, in
which order, with which data.

If a button you expect is missing, check the User Guide's section 5 (who can do what): many buttons show only to some
jobs, on purpose. A missing button is worth reporting only if the guide says your job should have it.

## How the test runs

| | What you do |
| --- | --- |
| **First** | Read the User Guide, then this guide |
| **Your sheet** | Work through it in order, with its data, exactly as written. Some steps hand work to another tester, or wait for one: the sheet says what to do meanwhile |
| **Your own data** | Only when your sheet is finished: [Your own data](PBL_HIRING_UAT_YOUR_OWN_DATA.md). Invent your own work and try to break the system. Every name starts `OWN-` |
| **Throughout** | The **Feedback Log**: **Pass** or **Fail** for every step of your sheet, in your own tab, and one row in **Findings** for every problem, at the time |

## Rules of the test

- **Use only your own sheet's data**, typed exactly as written. Every name from a sheet starts `T1-` or `T2-`; your own
  data comes last and starts `OWN-`. Never mix the two.
- **The fleet is shared.** A machine allocated by one tester is not free for another on the same days. The sheets are
  written so that this never gets in the way; if a machine your sheet names shows "Allocated to ..." something else,
  tell the person running the test rather than freeing it.
- **Dates count from day 0**, the day the machines were loaded - the day before the test, or its morning. "Runs out in
  20 days" means 20 days after that day. The Alerts move on each day - that is the system working.
- **Your job is to find faults.** If a step does not do what the sheet says, it has **failed**: write down what
  happened, then carry on. If something goes wrong, do it again: a fault we can repeat is a fault we can fix.
- **Everyone can see every record** in this test. That is known; tell us if it is not what you want.

## Not in the system yet - please do not report these

The User Guide's section 6 lists what is not built: release of the Work Order to Operations, hired (vendor) machines,
crew, gate passes, log sheets, billing and invoices. Also:

| Thing | Position |
| --- | --- |
| Reminders by email or SMS | Not built. Reminders show in Alerts only |
| A Fleet Admin role of its own | Not built. An Admin login does that job |
| Reminder paths by position or region | Not built. They name roles today |
| A machine typed in by hand | Not built. Machines come only from Plum's report |
| Deleting a certificate | Not built, on purpose. A mistake is withdrawn, with a reason, and stays in the history |

If you think something on these lists should not have been left out, say so. That is worth more to us than a fault.

## Reporting

The **Feedback Log** is a spreadsheet with a tab for each tester's steps, one for your own data, and **Findings**:

- In **your tab**, give every step a result: **Pass**, **Fail**, **Could not try** (an earlier step failed, or another
  tester has not got there), or **Not done**. For a Fail, write the Findings row number beside it.
- In **Findings**, one row per problem, at the time. It asks for four things that are easy to leave out and hard for us
  to work without: **which login** you used, **roughly what time** it was, **the record's code** from the screen - such
  as `WO-000001`, `RR-000003`, `AL-000002` or `EQ-000008` - and **whether it happened again**.

If you are not sure whether something is a fault, report it. A screenshot helps a lot. If you think the system has lost
data, shown you something it should not have, or allowed something that should never be allowed, tell the person
running the test straight away, and leave the screen as it is.
