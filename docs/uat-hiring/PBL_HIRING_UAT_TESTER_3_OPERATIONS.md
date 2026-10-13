# Tester 3 - Operations: planning and allocating machines

**Sign in as `uat-operations-01`.** Read the [User Guide](PBL_HIRING_USER_GUIDE.md) and the
[Tester Guide](PBL_HIRING_TESTER_GUIDE.md) first. Work through this sheet in order, and record **Pass** or **Fail** for
every step in your tab of the Feedback Log.

Operations decides **what each Work Order line needs on site** (a resource requirement) and **which machine goes** (an
allocation). The system checks every machine's papers against the site and the days, and answers: can be allocated,
with a warning, or cannot (User Guide, 4.8). Nobody can override "cannot".

Your Work Orders come from **Tester 1 (Sales)**: two of them, for `T1-Saurashtra Port Infra`. **Start with Part A**,
which needs nobody; go on to Part B when Tester 1 says the first is ready. If you are doing every sheet yourself,
follow the [one-person route](PBL_HIRING_UAT_ONE_PERSON_ROUTE.md) instead.

| Who | What happens between you |
| --- | --- |
| Tester 1, Sales | Hands you two Work Orders (Parts B and C) |
| Tester 2, Fleet Admin | Records a new examination on a crane you allocated with a warning (step 8), and adds kit after you (step 6) |

"Day 0" is the day the machines were loaded - the day before testing, or its morning.

---

## Part A - The fleet, before any job

### 1. A machine's papers

**Equipment** > *Machines* > **UAT-AC100-02**. Read its *Certificates*: you see each paper's kind, issuer, dates and
status, not its number or copy. At the foot, **Check for a site**: *State* Gujarat, from 10 to 30 days after day 0,
**Check**. Then the same days in **Maharashtra**.

**Pass if** Gujarat answers **Cannot be allocated** (its permit covers Maharashtra only) and Maharashtra **Can be
allocated** (User Guide, 4.3).

### 2. Your reminders

Open **Alerts**.

**Pass if** you see reminders for machines whose papers run out within 15 days, and "A certificate not yet recorded"
for **UAT-CC250-06** and **UAT-AC100-08** (added 15 and 8 days before day 0) but **not** for UAT-AC100-09 (added on day
0: Admin only for the first 7 days). Mark one as seen and press **Refresh**: what happens to it, and to the count in the
menu?

---

## Part B - The first Work Order: jetty and yard

When Tester 1 says their first Work Order (customer reference `T1-PO-001`) is ready, open it from **Work Orders**.

### 3. What line 1 needs

Read the Work Order first: two lines, a jetty at Dahej (Gujarat) and a container yard at Uran (Maharashtra), and the
contract dates. Then *Resources needed*, line 1 > **Add a requirement**:

| Field | Type or choose |
| --- | --- |
| Number of machines | `2` |
| Kind of machine | `Crane` |
| Type | `Crawler` |
| Rated capacity, at least | `200` |
| Needed from | the contract's first day (5 days after day 0) |
| Needed until | 60 days after day 0 |
| Operators | `1` |
| Helpers | `1` |

**Save requirement**. **Pass if** it is saved with a code `RR-...` and appears under **Resource Planning**.

### 4. Allocate two crawlers

On the requirement, **Allocate a machine to unit 1** > **Find machines for these days**. Read every row before
choosing.

**Pass if** the six 250 t crawlers answer: **UAT-CC250-01** and **03** "Can be allocated"; **02** and **04** "Can be
allocated, with a warning" (their examination runs out during the job); **05** "Cannot be allocated" (a transport
registration wins over its marks, User Guide 4.3); **06** "Cannot be allocated" (nothing recorded). Once Tester 2
has confirmed Plum's second report, **UAT-CC250-07** is listed too: "Cannot be allocated" (nothing recorded yet).

Choose **UAT-CC250-01**, **Allocate**. Then **Allocate a machine to unit 2**: choose **UAT-CC250-02**, tick **I have
seen these warnings**, **Allocate, with these warnings**.

**Pass if** both allocations are made (`AL-...`), and the second keeps its warning.

### 5. Kit on the first crane's trips

Open the first allocation (UAT-CC250-01). Card *Trips (Own Load) to site* > **Add pieces to Trip (Own Load) 1**: hook
block **EQ-000020**, **8** counterweights from **EQ-000022**, sling **EQ-000025**. List them.

Then **Add a Trip (Own Load)** two days after the crane goes, and on it the two boom inserts **EQ-000023** and
**EQ-000024**.

**Pass if** both trips are listed with their pieces.

### 6. Kit on the second crane: what is left

Open the second allocation (UAT-CC250-02) > **Add pieces to Trip (Own Load) 1**. Try:

| Piece | Pass if |
| --- | --- |
| **8** counterweights from EQ-000022 | Refused or limited: only **4** are free - 8 travel with the first crane on the same days |
| hook block **EQ-000021**, examined 7 months ago | **Can go**: a hook block is examined every 12 months |
| sling **EQ-000026**, examined 7 months ago | **Cannot go**: a sling is examined every 6 months |
| a boom insert | Shows "Allocated to" the first crane: both are on its second trip |

List what can go. Then **tell Tester 2**: "I have finished with the kit." (They add two more boom inserts after you.)

### 7. The yard line, in Maharashtra

Line 2 > **Add a requirement**: `1` machine, `Crane`, `All-terrain`, at least `80`, from the contract's first day to
8 days after day 0, operator `1`. **Save requirement**, then allocate **UAT-AC100-02**.

**Pass if** UAT-AC100-02 "Can be allocated" here: its permit covers Maharashtra (step 1).

### 8. A warning cleared

**Tell Tester 2:** "UAT-CC250-02 is allocated with a warning; please record its new examination." When they say it is
done, open the second allocation and press **Check again**.

**Pass if** *Today's answer* now reads "Can be allocated", while the *stored answer* still shows the warning it was
allocated with. If it already read "Can be allocated" in step 4, Tester 2 got there first: note it, and pass.

---

## Part C - The second Work Order: a central-government site

When Tester 1 says their second Work Order (`T1-PO-002`) is ready, open it.

### 9. A requirement at the refinery

Read line 1: a refinery shutdown near Vadodara, Gujarat, **Central-government site? Yes**. **Add a requirement**: `1`
machine, `Crane`, `All-terrain`, at least `80`, from the contract's first day (10 days after day 0) to its last (40
days after), operator `1`, helper `1`. **Save requirement**, then **Allocate a machine to unit 1** > **Find machines for
these days**.

**Pass if** the all-terrain cranes answer:

| Machine | Answer | Why (User Guide) |
| --- | --- | --- |
| UAT-AC100-01 | Can be allocated | Non-transport; road papers on its carrier (4.3) |
| UAT-AC100-02 | Cannot be allocated | Permit for Maharashtra only (4.3). Its yard job ends before this one starts |
| UAT-AC100-03 | Can be allocated | All-India permit (4.3) |
| UAT-AC100-04 | Cannot be allocated | Transport, no fitness, no permit (4.3) |
| UAT-AC100-05 | Cannot be allocated | Insurance recorded without its copy (4.6) |
| UAT-AC100-06 | With a warning | First-year PUC marked not applicable only until day 25 (4.2) |
| UAT-AC100-07 | With a warning | Insurance ends on day 20; the renewal has no copy (4.6) - unless Tester 2 has attached it |
| UAT-AC100-08, 09 | Cannot be allocated | Nothing recorded - unless Tester 2 has recorded 09's papers |
| UAT-AC100-10 | Cannot be allocated | Nothing recorded - listed only once Tester 2 has confirmed Plum's second report |

### 10. Allocate, then replace before the job

Choose **UAT-AC100-06**, tick **I have seen these warnings**, **Allocate, with these warnings**. Then on the new
allocation, **Replace the machine** with **UAT-AC100-03**, from the first day, reason **Certificates**.

**Pass if** the old allocation is kept, marked replaced, with your reason, and the new one holds UAT-AC100-03.

### 11. A trip outside the job

On the UAT-AC100-03 allocation, **Add a Trip (Own Load)** going the day **before** the job starts.

**Pass if** it is refused - a trip goes on one of the allocation's own days - with a message you understand. Then add
it on the job's second day.

---

## Part D - Things Operations may not do

### 12. Refused, or allowed

| Try | Where | Pass if |
| --- | --- | --- |
| Upload Plum's report | **Equipment** > *Plum report* | "Only Admin uploads and confirms Plum's report." |
| Record a certificate, or mark one not applicable | a machine's *Certificates* | No such buttons |
| Add or end a certificate rule | **Equipment** > *Certificate rules* | No such buttons |
| Change a reminder setting | **Equipment** > *Reminder settings* | Read only |
| Change PBL's holiday calendar | **Holiday Calendar** | Read only |
| Record the customer's acceptance of an offer | Tester 1's offer, *Submission* | Not offered - Sales' job |
| Change a Work Order's site, terms or holidays | Tester 1's Work Order | **Allowed** - Operations may (User Guide, section 5). Change nothing; just check you could |
| See business events | **Events** | Refused |

**Pass if** each behaves as the table says. If anything that should be refused works, report it straight away.

### 13. What you would actually need

- When a Work Order reaches you, does it tell you enough to plan the job?
- Were the three answers enough to decide? What else would you look at before sending a machine?
- Trips (Own Load) and kit: is that how a crane really goes to site?

**Pass if** you wrote your answers in the Feedback Log's notes for this step.

---

When you have finished, go on to [Your own data](PBL_HIRING_UAT_YOUR_OWN_DATA.md).
