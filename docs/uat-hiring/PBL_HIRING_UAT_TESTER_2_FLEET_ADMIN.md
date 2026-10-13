# Tester 2 - Fleet Admin: the fleet, its papers and the holiday calendar

**Sign in as `uat-fleet-01`.** Read the [User Guide](PBL_HIRING_USER_GUIDE.md) and the
[Tester Guide](PBL_HIRING_TESTER_GUIDE.md) first. Work through this sheet in order, and record **Pass** or **Fail** for
every step in your tab of the Feedback Log.

The Fleet Admin keeps what the rest of the system relies on: **Plum's report** brings the machines in; **models** say
what each machine is; **certificates**, each with its copy, decide whether a machine may go to a site; **rules** say
which certificates a machine needs where; and **PBL's holiday calendar**, which every Work Order follows. Until a Fleet
Admin role exists, you use an Admin login - which can do everything, so this sheet says what is your job.

What you record changes what others see: a certificate you record can turn another tester's "cannot" into "can". Each
step says who is waiting for what. If you are doing every sheet yourself, follow the
[one-person route](PBL_HIRING_UAT_ONE_PERSON_ROUTE.md) instead.

You need **any small PDF file** for the certificates' copies (a blank page printed to PDF will do), and the file
**`PBL_HIRING_UAT_PLUM_REPORT_2.csv`** you were given.

"Day 0" is the day the machines were loaded - the day before testing, or its morning.

---

## Part A - Look first

### 1. The fleet

**Equipment** > *Machines*. Open **UAT-AC100-01**: its carrier, **UAT-AC100-01C**, is fitted to it, and the road papers
are on the carrier. Open **UAT-XC60-01**: it has no type, because Plum's model name for it is not mapped.

**Pass if** you can find both, and the carrier's papers from the crane's page. Then **Equipment** > *Certificates due*:
**Tell us** whether this is the renewal list you would work from.

### 2. Your reminders

Open **Alerts**.

**Pass if** "A certificate not yet recorded" lists **UAT-CC250-06**, **UAT-AC100-08** and **UAT-AC100-09**, and
**UAT-CC80-01**'s insurance, PUC and examination are there, running out about 20, 10 and 5 days after day 0, with its
load test already run out. Which would you deal with first?

---

## Part B - Plum's second report

Plum has sent a new report: the same machines, and three more.

### 3. A model for the unknown name

**Equipment** > *Models* > **Record a model**: *Maker* `XCRANE`, *Model name* `T2-XC 60 T`, *Kind* `Crane`, *Type*
`Truck-mounted telescopic`, *Rated capacity* `60` (tonnes). **Save model**.

**Pass if** the model is listed.

### 4. Upload and preview

**Equipment** > *Plum report* > choose `PBL_HIRING_UAT_PLUM_REPORT_2.csv`, report date today > **Upload and preview**.
On the preview:

- *Model names to map*: map "XCRANE 60 T TRUCK MOUNTED" to the model from step 3 (**Map name**).
- UAT-CC250-07's capacity reads **"250 T"**: read it as 250 tonnes, with a reason.
- *Crane halves to pair*: pair the carrier **UAT-AC100-10C** with its crane **UAT-AC100-10**.
- **Refresh**.

**Pass if** *What confirming would do* says three new machines, and UAT-XC60-01 **changed** - it now has a type.
**Tell us:** would you trust this preview with a real report?

### 5. Confirm

**Confirm**. Then find **UAT-AC100-10**, **UAT-CC250-07** and **UAT-XC60-01** under *Machines*.

**Pass if** all three are there, UAT-XC60-01 with its type, and "A certificate not yet recorded" for the two new
machines reaches you at once in **Alerts**.

---

## Part C - Papers

Each certificate counts only **with its copy attached** (User Guide, 4.6): after **Record a certificate**, attach the
copy from the certificate's row (**Attach its copy**).

### 6. A machine with nothing recorded

**UAT-AC100-09**: record its registration (registered **non-transport**), insurance, PUC, road tax, thorough
examination and load test, each with its copy - invented numbers beginning `T2-`, invented issuers, sensible dates.
Then **Check for a site**: Gujarat, next month, **Check**.

**Pass if** it answers **Can be allocated**, and its "not yet recorded" reminders leave your **Alerts**.

### 7. A wheeled crane is a motor vehicle

On UAT-AC100-09, look for **Mark not applicable** for its insurance.

**Pass if** it is not offered: a wheeled crane on its own power is a motor vehicle (User Guide, 4.2).

### 8. A renewal without its copy

**UAT-AC100-07**: its renewed insurance (from day 21) was recorded without its copy, so its cover still ends on day 20.
Attach the copy. Then **Check for a site** from day 15 to day 40.

**Pass if** it now answers **Can be allocated**.

### 9. A new examination for Operations

**Wait for Tester 3** to say UAT-CC250-02 is allocated with a warning (their step 8). Then on **UAT-CC250-02** record a
new **thorough examination**, done today, with its copy, and tell them.

**Pass if** UAT-CC250-02's examination is in date for the next 12 months. If Tester 3 has not got there by the time
you finish this sheet, record it anyway and tell them.

### 10. Correct a mistake

On **UAT-AC100-04** - it cannot go anywhere, so nobody's work changes - record a PUC with a wrong date, then
**Withdraw** it, with a reason.

**Pass if** the earlier PUC is in force again and the withdrawn one is still in the history.

### 11. A registration that wins

**UAT-CC250-05** cannot go anywhere although its road papers are marked not applicable. Read why on its page.

**Pass if** you can say why in your own words (User Guide, 4.3). **Tell us** what you would do about it in real life.

---

## Part D - A state's own rule (test only)

States may set their own rules (User Guide, 4.4). None is loaded, because none is law PBL has adopted. This shows the
effect safely: the rule starts four months ahead, so nothing anyone does today changes.

### 12. Add a test rule

**Equipment** > *Certificate rules* > **Add a rule**: *Certificate* `Thorough examination`, *Required of* `Crane`,
*Type* `Crawler`, *Where* `Gujarat`, *Applies* `Always`, *In effect from* **four months from today**, *Renew every
(months)* `6`, *Basis* PBL's own rule, *A lapse* stops the machine, *"Not applicable"* never, *Source* `TEST ONLY - T2 user test, not a real rule`. **Add rule**.

Then **UAT-CC250-01** > **Check for a site**: Gujarat, from a week after the rule starts, for two months; then the same
dates in Maharashtra.

**Pass if** Gujarat answers **with a warning** (its 6-month rule runs out in that time) and Maharashtra **Can be
allocated** (the all-India 12-month rule).

### 13. End it

On *Certificate rules*, **End this rule**: *Last day in effect* its first day, *Why* `Test over`, **End rule**. Check
Gujarat again.

**Pass if** Gujarat now answers as Maharashtra does.

---

## Part E - Kit

### 14. Two more boom inserts

**Wait for Tester 3** to say they have finished with the kit (their step 6): they expect the two inserts to be the only
ones. Then on **UAT-CC250-01**'s page, **Add kit**: two more *ACME CC 250 boom insert 9 m*.

**Pass if** two new pieces are listed, held for every CC 250, not for this crane alone. **Tell us:** no rule requires a
certificate of a boom section, while hook blocks and slings need examinations (User Guide, 4.1, 4.7). Is that right
for PBL?

---

## Part F - PBL's holiday calendar

### 15. Add a holiday to next year

**Wait for Tester 1** to say their first Work Order's contract runs over next year (their step 8). Then **Holiday
Calendar** > next year: **Add a holiday** - *Date* 14 January, *Holiday* `T2-Uttarayan`, *Kind* `Festival holiday`,
*Where* `These states`: **Gujarat**. Read the warning beside **Save** if one shows, then **Save**.

**Pass if** it says "Saved as version ...". Open Tester 1's first Work Order, card **Holidays that apply**: **Pass if**
"Line 1 - Gujarat" now shows `T2-Uttarayan` and "Line 2 - Maharashtra" does not.

### 16. A year not complete

On **Holiday Calendar**, this year: untick **This year's calendar is complete**, **Save**. Open **Alerts**.

**Pass if** a reminder says PBL's holiday calendar for this year is not marked complete, and Tester 1's first Work
Order's **Holidays that apply** says this year's calendar may change. Then tick it again, **Save**: **Pass if** the
reminder goes, and the count in the menu with it.

### 17. Who may change the calendar

**Pass if** you are the only tester who can: the others see it read only. Ask one of them to confirm.

---

## Part G - Reminder settings, and what you would need

### 18. Read the settings

**Equipment** > *Reminder settings*. **Read only - change nothing during the test**: a change applies at once, and
the others' Alerts would change under them.

**Pass if** you can find each kind's schedule and who it reaches, including PBL's holiday calendar. **Tell us:** are
60, 15 and 7 days the right points? Who else should a reminder reach?

### 19. What you would actually need

- Is anything Plum sends missing here, or anything here Plum could have sent?
- Is recording a certificate quick enough for a fleet of hundreds? What would you do in bulk?
- Would you trust the system's answer enough to stop checking papers by hand?

**Pass if** you wrote your answers in the Feedback Log's notes for this step.

---

When you have finished, go on to [Your own data](PBL_HIRING_UAT_YOUR_OWN_DATA.md).
