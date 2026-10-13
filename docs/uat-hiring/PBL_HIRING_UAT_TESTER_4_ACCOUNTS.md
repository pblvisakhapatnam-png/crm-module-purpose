# Tester 4 - Accounts: reading the Work Orders as the person who will bill them

**Sign in as `uat-finance-01`.** Read the [User Guide](PBL_HIRING_USER_GUIDE.md) and the
[Tester Guide](PBL_HIRING_TESTER_GUIDE.md) first. Work through this sheet in order, and record **Pass** or **Fail** for
every step in your tab of the Feedback Log.

Billing is not built yet: no log sheets, no invoices. But everything billing will need is being recorded now - each
line's terms, the contract period, the holidays that apply, how often each machine is invoiced. Accounts reads all of
it and changes none of it (User Guide, section 5). **Your job is to tell us whether you could bill from what is
recorded**, before billing is built on it.

The Work Orders you read come from **Tester 1 (Sales)**. **Start with Part A**, which needs nobody. If you are doing
every sheet yourself, follow the [one-person route](PBL_HIRING_UAT_ONE_PERSON_ROUTE.md) instead.

---

## Part A - Before the Work Orders exist

### 1. PBL's holiday calendar

**Holiday Calendar**: this year and next.

**Pass if** both read "Complete", with their holidays - national ones for all of India, Gujarat Day and Maharashtra
Day for their states only - and you cannot change anything.

### 2. A machine's papers for a site

**Equipment** > *Machines* > **UAT-AC100-02** > **Check for a site**: Gujarat, next month; then Maharashtra, the same
dates.

**Pass if** the answers differ - cannot in Gujarat, can in Maharashtra - and you can say why (User Guide, 4.3).
**Tell us:** is there anything in a machine's papers Accounts needs - insurance, for example?

### 3. Things you may not do

| Try | Where | Pass if |
| --- | --- | --- |
| Change PBL's holiday calendar | **Holiday Calendar** | Read only |
| Record a certificate, or upload Plum's report | **Equipment** | Not offered |
| See your reminders | **Alerts** | Empty: Accounts is on no reminder path, by design |
| See business events | **Events** | Refused |

**Pass if** each is refused or not offered. If any works, report it straight away.

---

## Part B - The terms, line by line

When Tester 1 says their first Work Order (customer reference `T1-PO-001`) is ready, open it from **Work Orders**.

### 4. Line 1, billed by the month

Read line 1's **Billing terms**: the monthly rate, the contracted hours and days, two shifts of 10 hours at the one
rate, overtime counted over the month and per shift, breakdown, idle time, the part month, the crew, the crew's trip to
and from the job at INR 2,500 per person per trip deducted from PBL's invoice, and mobilisation credited back after
three months.

**Pass if** you could work out a month's bill from this alone. **Tell us** what you would still have to ask Sales or
Operations.

### 5. Line 2, billed by the shift

Read line 2's terms: the shift rate, hours a shift, overtime by the hour, and the operator's food at INR 150 a day
deducted from PBL's invoice.

**Pass if** you could work out a week's bill, including what comes off it for the operator's food. Is a "shift"
clear? **Tell us:** when the customer bills PBL separately for the crew's upkeep instead, how should Accounts hear of
it?

### 6. The contract and the holidays that apply

Read **Contract period**, then **Holidays: PBL's calendar and this Work Order's changes** and its **Holidays that
apply**.

**Pass if** the holidays are grouped by state - "Line 1 - Gujarat", "Line 2 - Maharashtra" - and you can tell, for each
day, whether it is a holiday or a working day and how it is charged: Diwali is a working day **at the overtime rate**;
Tester 1's site festival is a holiday added by the Work Order; Gujarat Day applies to line 1 only.

**Tell us:** which days would you bill as holidays? Is "charged as each line's off-day term says" clear enough?

### 7. You may read, not change

On the same Work Order, try to change a billing term, the contract dates or the holidays.

**Pass if** there are no Save buttons for you: read only.

---

## Part C - The second Work Order and the machines

### 8. A day-rate line at a central-government site

Open Tester 1's second Work Order (`T1-PO-002`). Read its line, contract and holidays.

**Pass if** it says it follows PBL's calendar unchanged, and you can tell how a day is billed.

### 9. Which machine is billed

When Tester 3 has planned, read **Machines allocated** on the second Work Order: one crane was **replaced** by another
before the job.

**Pass if** you can tell which crane goes and which was replaced, and why. **Tell us:** when billing is built, which
crane's days should the customer see?

### 10. How often a machine is invoiced

Open an allocation on the first Work Order. Read *How often this machine is invoiced* - "Not stated yet", or what
Tester 1 set.

**Pass if** you can read it but not change it. **Tell us:** who should decide it?

### 11. Allocations starting soon

**Allocations** > *Starting in the next 15 days*.

**Pass if** Tester 3's allocations are listed. **Tell us:** is this list useful to Accounts?

---

## Part D - What you would actually need

### 12. In your own words

- Before billing is built: what must be recorded here that is not?
- Should Accounts approve the billing terms, or only read them?
- Is anything on these screens you would never use?

**Pass if** you wrote your answers in the Feedback Log's notes for this step.

---

When you have finished, go on to [Your own data](PBL_HIRING_UAT_YOUR_OWN_DATA.md).
