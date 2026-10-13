# ELG-1 Machine eligibility - design and implementation record

**Built 27 September 2026**: section 20 is the implementation record.

Status of the design: **Design proposed, 27 September 2026; revised twice the same day** with the owner's answers
(section 1.1):

- PBL works at central-government sites;
- the **conservative principle** for ambiguous law;
- a question on spreadsheet uploads;
- then **every other question as recommended**, with Q4 refined: a certificate running out before a job
  starts, or during it, is flagged, with configurable repeated reminders and configurable escalation paths,
  on screen for now, and other channels configured when integrated.

The reminders and escalation are designed in section 19. The questions they raise, Q14 to Q18 in section 1.3,
were **answered as recommended** the same day, with **"go ahead and build it"**: reminders and escalation
are ELG-2, after 8A's core and before the Hiring user test. The statutory research is in section 2. Section
20 is the implementation record.
Under the owner's direction for this package, where the research contradicts the brief, the research is
treated as more authoritative; section 2, E lists where it does.

Hiring lane (Track 2). Worktree `<a separate worktree>`, branch `hiring/elg-1-machine-eligibility`,
based on `main` at `aa91305`. Migration slot `20260908_0044`, parent `20260908_0043` - the single Alembic
head on `main`. No branch on `origin` holds a `0044` revision (checked 27 September 2026). Foundation Slice
Mode: the shape is built properly, the screens minimally.

This is the **machine half** of the Eligibility foundation (`FUTURE_SLICES.md`, "Eligibility foundation
(before 8B)", "Built in two halves"). It comes before 8A's core, so that allocating a machine can ask
whether the machine may work. The people half - crew licences, and what operating a machine requires of
its operator - comes with 8B.

In plain words:

- **The Fleet Admin records each machine's certificates.** There are two kinds:
  - road papers: registration, insurance, pollution certificate (PUC) and road tax, and for transport
    vehicles also fitness and permits;
  - lifting examinations: the thorough examination and the load test.

  Each certificate is recorded with its number, who issued it, the dates it runs from and to, and a copy.
  A registration certificate also says whether the machine is registered as a transport vehicle, which
  decides whether it needs fitness and permits.
- **Where the law is not clear, the cautious reading is the rule** (owner, 27 September 2026). A
  certificate is then required, and the Fleet Admin may mark it **not applicable** for one machine, with
  the reason - a crawler crane that cannot travel on a road, say. Where the law is clear, there is no
  "not applicable".
- **Parts and kit carry their own certificates.** A crane's road papers often belong to its carrier, which
  ERT-1 fits to the crane. Hook blocks and lifting tackle, from ERT-2's kit, are examined piece by piece.
- **Which certificates each kind of machine needs is held as rules, not written into the program.** A rule
  says:
  - which machines need a certificate;
  - how often it must be renewed;
  - whether a lapse stops the machine;
  - the law or PBL rule it comes from.

  A rule belongs to a jurisdiction and has a start date. The jurisdiction is all of India, the central
  government's own sites, or one state. The start date matters because the states are replacing their
  rules at different times.
- **Eligibility answers one question: may this machine work at this site from this date to that?** There
  are four answers, with the reason for each certificate:

  | Answer | `ELA-001` code |
  | --- | --- |
  | Can be allocated | `ELIGIBLE` |
  | Can be allocated, with a warning | `WARNING` |
  | Cannot be allocated | `BLOCKED` |
  | Needs approval | `OVERRIDE_REQUIRED` |

  8A asks this question when it allocates a machine, and keeps the answer.
- **Certificates due** is the Fleet Admin's renewal list. It shows what is missing, what has run out, and
  what runs out in the next 60, 30 or 15 days.

"Fleet Admin" means whoever holds `EQUIPMENT_REFERENCE_MANAGE`. That is **Admin, until a Fleet Admin role
exists** (ERT-1 design, comment 1).

**Reuse, not a second structure** (CODING_STANDARDS.md section 1, DRY first):

- **Assets.** A certificate belongs to an `equipment_asset`: a machine, a fitted part or a piece of kit,
  all ERT-1's and ERT-2's own records. There is no second register of machines.
- **Classes and types.** A rule names a class, and a type where needed, from the Equipment Reference's
  structure. These are the same codes WRR-001's requirements use.
- **Copies.** A certificate's copy is a Slice 9C document, attached to the certificate. This needs an
  entry in each of the documents module's two permission maps, and a document type. Under ADR-036 the
  files move to SharePoint when its provider is built; this package does not change that.
- **Fitted parts.** A crane's certificates include its fitted carrier's, through ERT-1's dated links.
- **Events.** Events go through `record_business_event`, as in every module, with codes, ids and dates
  only.

What is new is what nothing carries today: the certificate, the "not applicable" mark, the rule, the
jurisdiction and the decision. Section 5 explains why none of the existing records can carry them. The
Equipment Reference's tables do not change.

---

## 1. Questions for the owner

### 1.1 Answered by the owner (27 September 2026)

| # | Question | Answer |
| --- | --- | --- |
| Q8 | Does PBL work at sites where the central government's rules apply - ports, mines, railways, oil fields, central public sector plants? | **"Yes PBL works at such sites."** So the central government's rules are held as their own jurisdiction (`IN`), and 8A records the site as a central-government site. The recommendation - 8A records it on the Work Order line's site - stands unless the owner says otherwise |
| - | How to treat unclear law | **"We operate on a conservative basis - if a regulation is ambiguous we err on the side of caution; apply this principle when designing. Option of N/A in cases where it is not applicable are accepted in such cases - not if the law is clear."** Applied below |
| - | Spreadsheet uploads (Q12): "will AI figure out what goes where irrespective of column names or will a template be specified? If a template is to be specified, there should be provision for the user to download the template and fill it per that before uploading." | Answered in Q12 and designed in section 18: a template the user downloads, fills and uploads |
| Q1-Q3, Q5-Q7, Q9-Q13 | Section 1.2 | **"Rest all as recommended."** So: the certificate table of section 5.4; PBL's examination rule where the law is silent, with slings every 6 months; "not applicable" marks; copies required; numbers and copies for Admin only; rules kept on a screen by Admin; alerts on screen now; the platform holds the whole insurance certificate; no overridable rule now; certificates entered on screen, with the template upload as its own package before go-live; slot `20260908_0044` |
| Q4 | A certificate that runs out before the job starts | **As recommended - allowed, with a warning - and more:** "A certificate that runs out before the job starts should be flagged and configurable reminders repeated with configurable escalation paths as well as certificates that run out during the job currency should be flagged and configurable reminders repeated with configurable escalation paths. Of course, for now, alerts can be screen based and when other channels are available and integrated, they can be configured for use for these alerts." Designed in section 19 |
| Q9-Q13 | Alerts elsewhere in these answers | **"The last sentence applies to Q9-13 also."** Every alert this design raises is shown on screen now, and each can be given other channels - email, SMS, messaging - once they are integrated (section 19, "Channels") |

**How the conservative principle is applied.** Where the law is unclear, the design takes the stricter
reading. "Not applicable" is offered only where the law is unclear, and never where the law clearly
requires the certificate:

| Where the law is unclear | The cautious reading, now in the design | "Not applicable"? |
| --- | --- | --- |
| No interval for examining cranes at central-government sites, in Gujarat, or in factories (section 2, A) | PBL's own rule everywhere: a thorough examination every 12 months and a load test every 5 years (Q2) | No |
| How often slings must be examined: 12 months in the old rules, 6 months in the Indian Standard IS 12735 | **6 months for slings**; 12 months for other tackle and hook blocks. Changed from the first proposal | No |
| Whether forklifts and man lifts are lifting machines under factory rules | They are examined like cranes | No |
| Whether a crawler crane is a motor vehicle ("very likely" not) | Road papers required, as for any crane | Yes, for a crawler crane, with the reason |
| Whether a crawler excavator, a tracked or towed man lift, or a forklift used only inside a plant is a motor vehicle | Road papers required | Yes, with the reason |
| A pollution certificate in a vehicle's first year after registration, which the law does not require | Required | Yes, for at most 12 months, with the reason |
| The law is clear: a wheeled crane on its own power is a motor vehicle, and registration, insurance, a pollution certificate and road tax are required; a transport vehicle needs fitness and a permit | Required | **No** |
| A crane whose type is not known (its model not yet mapped) | Judged by the rule for every crane, which offers no "not applicable" | No, until its type shows it is a crawler or a derrick |

This replaces the first proposal's per-machine choice of "transport, non-transport or not a motor
vehicle". There, the Fleet Admin could have called any machine "not a motor vehicle", even a wheeled crane
the law clearly covers. Now:

- whether a machine is registered as a transport vehicle is read from its registration certificate;
- "not a motor vehicle" becomes a "not applicable" mark on each road paper, with the reason, allowed only
  where the rules say the law is unclear.

### 1.2 The questions as put - answered as recommended (record)

All answered as recommended on 27 September 2026, Q4 with the owner's addition (section 1.1). Kept as
asked, so the answers can be read against them.

#### Q1. Which certificates does each kind of machine need?

**Recommendation:** the table in section 5.4:

- **Road papers.** Every crane, man lift, forklift and excavator needs registration, insurance, a
  pollution certificate and road tax. One registered as a transport vehicle also needs a fitness
  certificate and a permit covering the site's state.
- **Lifting examinations.** Cranes, man lifts, forklifts, hook blocks and each piece of lifting tackle need
  a thorough examination and a load test.
- **No certificates of their own.** Boom and jib sections are examined as part of their crane.
  Counterweight needs no certificate. (Hook blocks are examined with their crane too, and on their own
  as well, as above.)
- **Left out.** Fire extinguishers and first-aid boxes, which the FRS mentions, are left to 8A's check
  before a machine goes to site. The research found no law requiring certificates for them.
- **Transportation's vehicles** - prime movers, trailers, trucks - get their rules when Transportation
  needs them. Admin can add them as rules (Q7).

Please add any certificate PBL wants that is not in the table.

#### Q2. Examinations where the law is silent

The research found that the law now sets no interval for examining a crane in three places:

- **Central-government sites since 8 May 2026.** The OSH Central Rules 2026 hold no lifting rules.
- **Gujarat.** Its new rules hold none.
- **Factories.** Their yearly examination was written in the Factories Act itself, which has been
  repealed.

The central standard that will set the interval has not been published. Most other states still apply
their old rules, which require:

- a thorough examination every 12 months;
- a load test every 5 years on construction sites.

**Recommendation**, following the conservative principle: make these PBL's own rule everywhere, until the
law sets one:

- a thorough examination every 12 months, and a load test every 5 years, by a competent person;
- for cranes, man lifts, forklifts, hook blocks and each piece of tackle;
- **slings every 6 months**, as the Indian Standard IS 12735 says, because the law's 12 months and the
  standard's 6 differ;
- a machine or piece whose examination has lapsed cannot be allocated, and nobody may override that.

#### Q3. "Not applicable"

**Recommendation:** the Fleet Admin may mark a required certificate "not applicable" for one machine, with
the reason, only where the rules allow it - the "Yes" rows of the table in section 1.1.

- A mark may run until a date. The first-year pollution certificate needs one, at most 12 months ahead.
- A mark counts only where the rule in force at the site allows it. If a state's own rule does not allow
  it, the certificate is required at that state's sites.
- Marks show on the machine, in each check and on Certificates due. They can be withdrawn, and their history
  is kept.
- Nobody may mark a certificate "not applicable" where the rule does not allow it.

#### Q4. A certificate that runs out before the job starts

Suppose a crane's insurance runs out next week, and the crane is being allocated today to a job that
starts in three weeks.

**Recommendation:**

- Allow the allocation, with a warning: "insurance runs out on 5 October, before the job starts - renew it."
- Refuse it once the certificate has actually run out.
- 8A checks again before the job starts.

The alternative is to refuse any allocation that a certificate does not cover for the whole period. That
is the more cautious reading, but it is a business choice rather than unclear law, so it is yours to make.

#### Q5. A copy of each certificate

**Recommendation:** a certificate counts only once its copy (a scan or PDF) is attached. The reasons:

- the FRS asks for the load test certificate to be uploaded;
- customers ask for copies;
- a record without the paper is only an assertion.

Until the copy is attached, the certificate shows as "copy missing".

#### Q6. Who sees certificate numbers and copies

Registration and insurance papers show the engine and chassis numbers. Since 25 September 2026 only Admin
may see those numbers.

**Recommendation:**

- Everyone who sees machines sees each certificate's kind, issuer, dates and status.
- Only those who may see engine and chassis numbers (Admin, today) see certificate numbers and copies.
- Customers usually want copies before a machine arrives, so Operations may need that permission before
  the Hiring user test. Granting it needs no code change.

#### Q7. Keeping the rules up to date

**Recommendation:** Admin keeps the rules on a screen:

- When a state publishes its own rules, Admin adds a rule with the notification it comes from.
- Admin ends a rule with a date.
- Nothing is edited or deleted, so every earlier answer can still be explained.
- The package comes with the first rules (section 5.4).

The alternative is that a developer changes the rules, as for the Plum category rules.

#### Q9. Alerts

`ELA-001` asks for alerts 60, 30 and 15 days before a certificate runs out. The research found these
intervals are PBL's policy, not the law. Emails and messages need the notification service, which no
package has built yet.

**Recommendation:**

- Now: the **Certificates due** page, with its counts shown on the Equipment pages.
- Later: emails or messages, when the notification service is built. They go to the Fleet Admin, and to
  Operations where an allocated machine is affected.

#### Q10. Plum's insurance number

Plum's report holds each machine's insurance policy number and insurer, but not the dates, so it cannot
say whether a machine is insured.

**Recommendation:**

- The platform holds the whole insurance certificate, entered by the Fleet Admin: number, insurer, dates
  and copy. This follows ADR-037's refinement, point 1: where Plum does not hold what the job needs, the
  platform holds it.
- Comparing Plum's number with the platform's, so that Plum can correct its own, is left for later.

The alternative is to take Plum's number through the import and have the Fleet Admin add only the dates
and the copy.

#### Q11. Requirements that are not the law

`ELA-001` allows an authorised Risk Approver to accept a gap that is not a legal requirement. Every rule
proposed here either is the law or is PBL's own rule of Q2, and neither can be overridden.

**Recommendation:**

- No overridable rule now.
- The approval screen comes with the approval capability (`APR-001`), when PBL first wants such a rule -
  for example, a customer's third-party inspection.

Please name any such requirement PBL wants now.

#### Q12. Entering the fleet's papers, and the spreadsheet upload

About 290 machines, each with four to six certificates, means over a thousand entries.

**Your question: will AI work out which column is which, or is there a template?** A template, which the
user downloads, fills and uploads. The design is in section 18. In short:

- **Download the template** from the Certificates due page. It is a spreadsheet with:
  - fixed columns;
  - a sheet of instructions;
  - the lists of valid entries: the fleet's machine numbers and `EQ-` references, the certificate kinds and
    the states.
- **Upload.** The file is read exactly as the template says. The platform shows a preview first - each
  row's certificate, and every row it cannot take, with the reason - and nothing is saved until the Fleet
  Admin confirms. This is the same upload, preview and confirm as the Plum report (ERT-1).
- **The copies** are attached afterwards, per certificate (Q5), or by uploading the scans with their file
  names written in the sheet.

**Why not AI.** Guessing columns from their names would give a different reading of the same file on
different days. ADR-030 keeps repeatable processing deterministic, and uses AI only where judgement adds
value, with a separately approved business need. Certificate numbers would also have to be sent to an AI
service outside the platform. If the Fleet Admin's own spreadsheets use other column names, a later step
can let them match their columns to the template's once, on screen, and keep that match - as Plum's model
names are matched once in ERT-1. AI could then *suggest* the match for the Fleet Admin to confirm, when
AI is approved for the platform.

**Recommendation:**

- ELG-1 enters certificates on screen; the Hiring user test needs only a few machines.
- The template upload of section 18 is a small package of its own before go-live, so ELG-1's screen check
  stays within twenty minutes.

Or say if you want it inside ELG-1.

#### Q13. Migration slot

**Recommendation:** `20260908_0044`, parent `20260908_0043`.

### 1.3 New questions: reminders and escalation (section 19)

**All five answered as recommended** (owner, 27 September 2026: "All as recommended, go ahead and build
it").

#### Q14. When to build the reminders

Two of the three reminders - a certificate running out before a job starts, and one running out during the
job - need 8A's allocations, which do not exist yet. The third, a certificate running out on a machine
whether or not it is allocated, needs only ELG-1.

**Recommendation:** a package of its own, **ELG-2**, right after 8A's core and before the Hiring user test.
All three reminders are then built together, tested against real allocations, and seen by the testers.

- Until then, ELG-1 still flags each case: on the check, on Certificates due, and on the allocation's
  answer (section 6).
- ELG-1's screen check stays within twenty minutes.

The alternative is to build the first reminder in ELG-1 now, and the other two with 8A.

#### Q15. The standard reminder schedule

**Recommendation:** the same schedule for all three reminders to start with, changeable for each:

- first reminder 60 days before the certificate runs out, then at 30 days;
- weekly from 15 days before;
- daily from 7 days before;
- daily after it has run out, until someone deals with it.

A machine allocated inside those dates is flagged at once, when it is allocated, and then follows the
schedule. The 60, 30 and 15 days are `ELA-001`'s.

#### Q16. The standard escalation path

There is no position structure yet to say whose manager is whose (`ORA-001` is not active). So the path
names roles now, and positions later.

**Recommendation:** each step adds people; nobody drops off:

1. **Fleet Admin** (Admin today), from the first reminder;
2. **Operations**, from 15 days before - and at once, from the allocation, when an allocated machine is
   affected;
3. **Management**, from 7 days before.

All on screen for now. Please say who else should be on it. For example, Sales could be added when a
customer's job is affected.

#### Q17. "Seen" does not mean "dealt with"

**Recommendation:** anyone who receives a reminder may acknowledge it. That quiets it for them until the
next reminder in the schedule. Acknowledging never stops the escalation and never ends the reminders. Only
dealing with the certificate does:

- a renewal is recorded with its copy;
- or a "not applicable" mark is recorded where the rule allows one;
- or the machine is released or replaced on the job;
- or the machine is retired.

#### Q18. Who changes the schedule and the path

**Recommendation:** Admin, with the same permission as the rules (`ELIGIBILITY_RULE_MANAGE`), on a
settings screen. Each change applies from the moment it is saved, and records who made it and when.

### 1.4 Already settled, not asked again

| Point | Settled by |
| --- | --- |
| Admin acts as Fleet Admin until that role exists | ERT-1 design, comment 1 |
| A missing or lapsed statutory certificate always blocks, and nobody can override it | `ELA-001` |
| Where a regulation is ambiguous, the cautious reading; "not applicable" only where the law is not clear | Owner, 27 September 2026 (section 1.1) |
| Alerts at 60, 30 and 15 days | `ELA-001` (the research shows they are policy, not law) |
| Alerts on screen now; other channels configured when they are integrated | Owner, 27 September 2026 (section 1.1) |
| A certificate running out before or during a job is flagged, with configurable repeated reminders and escalation | Owner, 27 September 2026 (Q4) |
| A warning at allocation when a certificate is within 15 days of running out | FRS Controls, "Asset Documentation Warning" |
| Examination rules held as data for each jurisdiction | Owner, 27 September 2026; ERT-2 section 2, H1 |
| Facts Plum does not hold are entered by the Fleet Admin, and the platform is their source | ADR-037 refinement, point 1 |
| Kit is shared by model, not held by one crane, so a crane's answer does not include kit, and 8A asks about each piece it sends | ERT-2, Q6 |
| A piece's identification mark is its own number, or its `EQ-` number stencilled on it | ERT-2, Q5 |
| People's licences are left out | Owner, 27 September 2026 ("Built in two halves") |

### 1.5 The first proposal's Q3 (record)

Put on 27 September 2026 in commit `9a1057d`: "the Fleet Admin states, once for each machine, whether it is
a transport vehicle, non-transport (a construction equipment vehicle) or not a motor vehicle; until stated,
the machine cannot be allocated." It is replaced by the new Q3 and the registration certificate's
"registered as", for the reason given at the end of section 1.1.

---

## 2. What the law says (research, 27 September 2026)

This section was researched from government and gazette texts where they could be read (**primary**), and
otherwise from law firms, compliance trackers and news (**secondary**). It is not legal advice. It updates
ERT-2's section 2, H, and corrects it where noted in E.

### A. Labour safety: examining cranes, lifting machines and tackle

**The Acts are repealed.** The OSH Code 2020 came into force on 21 November 2025 (S.O. 5321(E)).

- Section 143(1) repeals 13 Acts, including the Factories Act 1948, the Mines Act 1952, the Dock Workers
  Act 1986 and the BOCW Act 1996.
- Under section 143(3), rules made under those Acts stay in force, where not contrary to the Code, until
  they are repealed.

Sources: [S1], [S2].

**The central rules say nothing about lifting.** The OSH (Central) Rules 2026 are G.S.R. 345(E) of 8 May
2026, in force on publication. They supersede 15 rule sets, including the BOCW Central Rules 1998, the Dock
Workers Rules 1990 and the Mines Rules 1955. Their full text mentions cranes only twice:

- a crane collapsing or overturning is a dangerous occurrence, to be reported within 12 hours (rule 7(4));
- registers are kept for 5 years (rule 72).

The Code leaves lifting machines, chains, ropes and tackle to **section 18 standards** (Second Schedule,
items 9, 56 and 67). The Labour Ministry's FAQ of 13 March 2026 says these standards "will be prescribed".
None has been found. Sources: [S1], [S3], [S4].

**The central government's own sites.** Section 2(1)(d)(i) makes the central government the authority for
these establishments, **including their contractors**:

- central public sector undertakings;
- railways and metros;
- major ports;
- oil fields;
- mines.

For those sites, BOCW Central Rules 56 and 70 lapsed on 8 May 2026, and nothing replaced them. Docks keep
the Dock Workers Regulations 1990, which were not superseded.

**The states are moving at different times** [S5]-[S10]:

| Stage | States |
| --- | --- |
| Final rules | Gujarat (in force 21 November 2025); Andhra Pradesh (final 7 August 2026, secondary); Bihar and Arunachal Pradesh (secondary) |
| Drafts only, so their old Factories and BOCW rules continue | Maharashtra, Karnataka, Uttar Pradesh, Haryana, Madhya Pradesh, Punjab, Odisha, Tamil Nadu |
| Nothing found | West Bengal, Delhi |
| Not established | Telangana, Rajasthan |

Gujarat's final rules and Andhra Pradesh's 2026 text hold no general interval for examining lifting
machines either. They define "lifting appliance" and "lifting gear" and list dangerous occurrences.

**What the old rules require, where they still apply** [S11], [S12], [S14]:

| Regime | Test before first use | After repair or alteration | Periodic test | Thorough examination | Other |
| --- | --- | --- | --- | --- | --- |
| Factories: section 29 and Model Rule 61 | Yes, with a certificate stating the safe working load | Re-test | None | Every 12 months, but this was in section 29 itself, now repealed. Whether it still binds is unresolved | Safe working load marked; a jib crane has a safe-load or angle indicator; a register of each item's mark and certificate |
| BOCW rules (states that have not replaced them) | Yes | Yes, and **after erection on a construction site** | Every 5 years | Every 12 months | Chains monthly; wire rope every 3 months; automatic safe load indicator; safe working load and mark on each item; operator at least 18 |
| Dock Workers Regulations 1990 | Yes | Yes | Every 5 years | Every 12 months | Chains monthly; wire rope every 3 months |

**How jurisdictions differ now.** Four concrete differences show why the rules must be data:

1. **Different forms.** Maharashtra's surviving rules use Form 11 (rule 62). Gujarat's old Form 10 is
   superseded. The Model Rules use a register with no form number. [S12], [S13]
2. **Gujarat may not accept another state's certificate.** A draft amendment of 13 December 2025 would let
   its Chief Inspector require re-certification of cranes and tackle certified by another state's
   competent person. It is not confirmed as final. [S6]
3. **Two regimes in one state.** A private construction site in a state whose BOCW rules continue has
   12-month examinations, 5-yearly tests and a test after erection. A central public sector site in the same
   state has no rule text found.
4. **Road fees and taxes.** A late fee on fitness renewal was struck down in Rajasthan but is charged
   elsewhere. Road tax is one-time in some states and periodic in others. [S25], [S28]

**Forklifts and man lifts.**

- The Factories Act's list of lifting machines does not name forklifts or man lifts, so how factories
  rules treat them is a matter of interpretation.
- The BOCW definition of a lifting appliance - "other equipment used for lifting materials, objects or
  building workers" - covers both on construction sites, as does Gujarat's.
- IS 4357 (forklift stability) is voluntary.
- No Indian standard was found for man lifts; ISO 16368 and ISO 18893 are voluntary. [S16]

**Tackle, hook blocks and kit.**

- **Tackle.** Every piece carries its own mark and its own certificate (the factories register; BOCW rule
  61 and Form VII). The statutory interval is 12 months. **Six months is not the law.** It comes from IS
  12735:1994, clause 5.3, and from customers' contracts. [S15]
- **Hook blocks, boom inserts and jibs** are examined as part of their crane: section 29 covered "all
  parts", and BOCW rule 56 covers "all parts and gears thereof, whether fixed or movable". A detachable
  hook block is also lifting gear in its own right.
- **Counterweight** needs no statutory certificate; at most its weight is marked.
- **What customers ask for** is contractual: a third-party inspection, a "load test certificate",
  6-monthly tackle certificates, and site standards such as OISD and NTPC's.

**Who examines.** A competent person recognised by the Chief Inspector (OSH Code section 2(1)(l)). Running
a machine against the Code's standards is punishable by ₹2 to 3 lakh, and up to ₹2,000 a day if it
continues after conviction (section 94).

### B. Road transport

**Mobile cranes are construction equipment vehicles.** CMVR rule 2(ca) covers these when self-propelled
and able to work on or off the highway:

- excavator, loader, backhoe, compactor roller, dumper, motor grader, dozer;
- **mobile crane**;
- **fork lift truck**.

Its Explanation (G.S.R. 642(E), 28 July 2000) makes such a vehicle **a non-transport vehicle**. It excludes
off-highway equipment "not equipped to travel on public roads on their own power", which very likely
includes crawler cranes. [S17]

**A wheeled machine that never leaves a site is still a motor vehicle.**

- Section 39 requires registration to drive "in any public place or in any other place".
- The courts test what a machine can do, not where it is used:
  - *Bose Abraham v State of Kerala* (Supreme Court, 2001): excavators and road rollers;
  - Bombay High Court (2023): a crane working inside a coal mine;
  - Andhra Pradesh High Court (2025): an excavator.
- So a wheeled machine used only on site still needs registration and insurance. [S18], [S27]

| Paper | For | Validity | If it has run out |
| --- | --- | --- | --- |
| Registration (sections 39 and 41; CMVR rule 52) | every motor vehicle | Non-transport: 15 years, then renewed every 5 years. A 2026 amendment reportedly adds a fitness test to each 5-yearly renewal (secondary; its gazette number not found) | Hard block anywhere: section 192, ₹5,000, then ₹10,000 |
| Insurance, third party (section 146) | every motor vehicle | the policy's term | Hard block in a public place: section 196, ₹2,000, then ₹4,000. Accident-claim liability on site as well |
| Pollution certificate (CMVR rule 115(7)) | every motor vehicle, from one year after first registration | 6 months, or 12 for BS-IV and BS-VI vehicles. Whether a CEV's Stage IV or V engine counts as BS-IV is not verified | Hard block in a public place: section 190(2), ₹10,000 and 3 months' licence disqualification |
| Road tax (each state's Motor Vehicles Taxation Act) | every registered vehicle | one-time or periodic, by state and class (Rajasthan: one-time 7% of cost for a CEV, 8% for a crane-mounted vehicle or forklift) | Detention |
| Fitness (section 56; CMVR rule 62) | **transport vehicles only** | 2 years when new, then 2-yearly to 8 years of age, then yearly (secondary) | Hard block: section 192 |
| Permit (section 66) | **transport vehicles only**. A CEV registered as non-transport needs none, and state transport departments list cranes as exempt | per permit | Section 192A, ₹10,000 |

Penalties are from MoRTH's 2019 table [S19]. Other sources: [S20]-[S24], [S26], [S29].

**Emission stage.** CEV Stage IV and V are a type-approval fact about the engine, not a certificate that
lapses. They are not needed for eligibility. [S24]

### C. Alerts

No law requires advance notice of expiry. The law sets only application windows, for example: a
registration renewal may be applied for no more than 60 days before expiry (rule 52(1)). The 60, 30 and
15-day alerts of `ELA-001` are **PBL policy**.

### D. Not verified

- Whether any section 18 standard has been notified.
- Whether Gujarat's draft amendment was made final.
- Maharashtra's and Karnataka's final rules.
- The current primary text of rule 62, and the gazette number of the 2026 amendment on registration and
  fitness.
- Whether testing at automated stations was extended beyond 1 October 2024.
- Whether a CEV's pollution certificate runs 12 months.
- The clause of section 66(3) that exempts cranes from permits.
- An Indian standard for man lifts.
- Fire-extinguisher and PESO duties.

### E. Where the research differs from the brief and the earlier records

| The brief or earlier record said | The research found | Effect on this design |
| --- | --- | --- |
| Brief: examination rules under "the OSH Code 2020 and its 2026 Central Rules" | The Central Rules hold no lifting provisions; the standards under section 18 are not yet published | The first lifting rules are PBL's own (Q2); states' surviving rules are added as they matter (Q7) |
| Brief and FUTURE_SLICES: every machine needs "insurance, fitness, pollution, road tax, load test, permits" | Fitness and permits are for **transport** vehicles; most cranes are non-transport. Registration itself expires | Fitness and permits apply when the registration says transport; registration is a certificate kind; "not applicable" only where the law is unclear (Q3) |
| ERT-2, H1: "the same substance survives in every regime found" | Not at central-government sites since 8 May 2026, not in Gujarat, and not in factories, whose interval was in the repealed section 29 | Q2 |
| ERT-2, H1: Gujarat's "Forms 37 and 38 recognise competent persons" | Those forms are in the **draft** amendment of 13 December 2025; the notified rules end at Form 36 | Nothing is built on them |
| ERT-2, H1: a test "every 5 years" | Under BOCW and the dock rules only, not factories. BOCW also requires a test **after erection on a construction site** | Q2 adopts 5 years everywhere (the conservative principle); the test after erection is 8A's, at mobilisation (section 13) |
| ERT-2, H4: slings "examined at least every 6 months" (IS 12735), beside the rules' 12 months | The 6 months is the standard's, not the law's | Slings every 6 months: the stricter reading (section 1.1) |
| ERT-2, H2: "crawler cranes probably are not motor vehicles" | Likely right; but wheeled machines used only on site are motor vehicles | Q3 |
| `ELA-001` and NTF-001: "accepted statutory-document alerts at 60, 30 and 15 days" | No law requires advance notice | The bands stay, as PBL policy (section 1, "Already settled") |

### F. Sources

- [S1] OSH Code 2020, DGFASLI copy (primary): `https://dgfasli.gov.in/public/Admin/Cms/AllPdf/OSH_Gazette.pdf`
- [S2] S.O. 5321(E), 21 November 2025 (secondary):
  `https://www.taxmann.com/post/blog/govt-notifies-enforcement-of-occupational-safety-health-working-conditions-code`
- [S3] OSH (Central) Rules 2026, G.S.R. 345(E), 8 May 2026 (gazette copy):
  `https://www.staffnews.in/wp-content/uploads/2026/05/The-Occupational-Safety-Health-and-Working-Conditions-Central-Rules-2026.pdf`
- [S4] Labour Ministry FAQ, 13 March 2026 (primary):
  `https://www.labour.gov.in/static/uploads/2026/03/d7a1038bf00f763484aa27a79a4c6306.pdf`
- [S5] Gujarat OSH Rules 2025, Extra No. 87, 12 June 2025 (gazette copy):
  `https://www.lawrbit.com/wp-content/uploads/2025/11/gujarat-occupational-safety-health-and-working-conditions-rules-2025.pdf`
- [S6] Gujarat draft amendment, Extra No. 163, 13 December 2025 (gazette copy), via simpliance.in
  (`https://simpliance.in/download/file/dXBsb2Fkcy9nb3Z0bm90aWZpY2F0aW9uL0RyYWZ0IG5vdGlmaWNhdGlvbiBvZiB0aGUgR3VqYXJhdCBPY2N1cGF0aW9uYWwgU2FmZXR5LCBIZWFsdGggYW5kIFdvcmtpbmcgQ29uZGl0aW9uKEFtZW5kbWVudClSdWxlcywgMjAyNS5wZGY=`)
- [S7] Andhra Pradesh G.O.Rt.No.68, 1 April 2026 (primary):
  `https://www.lawrbit.com/wp-content/uploads/2026/04/occupational-safety-health-and-working-conditions-andhra-pradesh-rules-2026.pdf`;
  final (secondary): `https://ascent-hr.com/notification/occupational-safety-health-working-conditions-andhra-pradesh-rules-2026/`
- [S8] State tracker, updated 17 September 2026 (secondary): `https://www.indianhrm.com/guides/labour-code-rules-by-state`
- [S9] Maharashtra drafts (secondary):
  `https://www.teamleaseregtech.com/updates/article/55645/draft-maharashtra-occupational-safety-health-and-working-conditions-la/`,
  `https://tmservices.co.in/maharashtra-osh-draft-rules-2026/`
- [S10] Karnataka draft (secondary):
  `https://lexplosion.in/karnataka-government-issues-draft-occupational-safety-health-and-working-conditions-karnataka-rules-2026/`
- [S11] BOCW Central Rules 1998: `https://indiankanoon.org/doc/49335675/`
- [S12] Factories Act section 29: `https://indiankanoon.org/doc/640593/`; Model Factories Rules (DGFASLI, 15
  December 2020): `https://dgfasli.gov.in/public/Admin/Cms/AllPdf/Model_Factories_Rules_as_on_15_12_2020.pdf`
- [S13] Maharashtra Form 11: `https://www.comply4hr.com/docs/mah/Mafr/MAFRF11.doc`; Gujarat Form 10:
  `https://www.deskera.com/blog/gujarat-factories-rules-1963-forms/`
- [S14] Dock Workers Regulations 1990:
  `https://www.legitquest.com/act/dock-workers-safety-health-and-welfare-regulations-1990/C867`
- [S15] IS 12735:1994: `https://law.resource.org/pub/in/bis/S08/is.12735.1994.pdf`
- [S16] IS 4357:2004: `https://archive.org/details/gov.in.is.4357.2004`
- [S17] CMVR rule 2(ca): `https://indiankanoon.org/doc/28072254/`
- [S18] Motor Vehicles Act 1988: `https://indiankanoon.org/doc/785258/`; section 66:
  `https://indiankanoon.org/doc/770795/`; section 190: `https://indiankanoon.org/doc/32624072/`
- [S19] MoRTH penalty table (2019): `https://images.assettype.com/barandbench/import/2019/09/Penalty_Table.pdf`
- [S20] CMVR rule 62: `https://indiankanoon.org/doc/21520809/`;
  `https://swarajyamag.com/ideas/green-push-road-transport-ministry-proposes-new-vehicle-fitness-rules`
- [S21] The 2026 amendment on registration and fitness (secondary): `https://www.taxheal.com/new-rules-for-vehicles-fitness-and-renewal.html`
- [S22] Automated testing stations:
  `https://www.teamleaseregtech.com/updates/article/26551/morth-extended-the-date-for-mandatory-testing-of-transport-vehicles-th/`
- [S23] Pollution certificate validity:
  `https://www.latestlaws.com/latest-news/validity-of-puc-for-vehicles-manufactured-under-bs-iv-or-bs-vi-categories-should-be-12-months-from-the-date-of-registration-209039`
- [S24] CEV emission stages: `https://www.pib.gov.in/Pressreleaseshare.aspx?PRID=1661781`;
  `https://dieselnet.com/standards/in/nonroad.php`
- [S25] Rajasthan one-time tax:
  `https://transport.rajasthan.gov.in/content/transportportal/en/transport/howtoget/vehicle-registration/vehicleTax/ntVehiclesPayingOTT.html`
- [S26] Assam permits: `https://comtransport.assam.gov.in/portlets/motor-vehicle-permit-issuerenewal`
- [S27] Court rulings: `https://www.casemine.com/judgement/in/56b49642607dba348f01781c`;
  `https://www.livelaw.in/high-court/bombay-high-court/bombay-high-court-motor-vehicle-crane-coal-mine-227003`;
  `https://www.verdictum.in/court-updates/high-courts/andhra-pradesh-high-court/the-national-insurance-company-limited-anantapur-v-keshoram-pache-keshevarav-somya-tikapache-pachekesharam-macmano3169-of-2012-mact-excavator-motor-vehicle-1578112`
- [S28] Rajasthan High Court, 29 December 2024:
  `https://www.verdictum.in/court-updates/high-courts/rajasthan-jaipur-shyam-prakash-meena-v-union-of-india-2024-rjjp-50573-db-vehicle-fitness-certificate-1562649`
- [S29] Form 25 and rule 52: `https://parivahan.gov.in/sites/default/files/DownloadForm/cmvr/FORM-25.pdf`
- [S30] DGFASLI renamed DGOSH (secondary): `https://www.taxmann.com/post/blog/govt-renames-dgfasli-as-directorate-general-occupational-safety-and-health`

---

## 3. Authority and required reading

What this design relies on, per PBL's internal working instructions "Reading discipline". Each was read in full unless a section is
named.

- **Backlog and deferred requirements:**
  - `FUTURE_SLICES.md`:
    - "Eligibility foundation (before 8B)", with "Built in two halves";
    - "8A - Equipment Hiring Execution Shell", with its two parts;
    - "Hiring user test";
    - "8B".
  - `DEFERRED_REQUIREMENTS.md`:
    - "Statutory requirements found with ERT-2";
    - "Asset component hierarchy";
    - "Detachable kit: what ERT-2 left out";
    - "Plum's machines: what ERT-1 left out";
    - "Fixed Assets: what the Equipment Reference keeps for it";
    - "Equipment documents";
    - "Trailer beds and prime movers".
- **Contracts:**
  - `eligibility-assignment-contract.md` (`ELA-001`, APPROVED), in full: the decision this package builds
    for machines.
  - `resource-master-reference-contract.md` (`RMR-001`, APPROVED), in full, with its ADR-032 and ADR-037
    notes.
  - `resource-planning-assignment-contract.md` (`RPA-001`, APPROVED), in full: 8A is the consumer.
  - `equipment-reference-api-contract.md`, in full: the assets, fitted links, kit, details and permissions
    reused.
  - `notification-delivery-contract.md` (`NTF-001`) and `approval-policy-contract.md` (`APR-001`), in full.
    Neither is built, which shapes section 7 and Q11.
  - `documents.md`: Slice 9C, "Record-scoped write rights" and "Where users attach files".
- **Decisions:**
  - ADR-037 and its refinement of 25 September 2026;
  - ADR-036 (SharePoint);
  - ADR-013 (source guidance is directional);
  - ADR-017 (module-owned data);
  - ADR-019 (the job queue, not built);
  - ADR-023 (a repeated request has one effect);
  - ADR-032 (the HR reference, for where the people half's boundary lies).
- **Designs this one follows,** both in full:
  - `docs/agent/slices/ert-1-plum-machines-into-the-equipment-reference.md`;
  - `docs/agent/slices/ert-2-detachable-kit.md`, including its section 2, H (the statutory research of 26
    September 2026, which section 2 here updates).
- **Architecture:**
  - `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`: the Equipment Reference, Resource Assignment and Compliance /
    Eligibility rows;
  - `EXTERNAL_DEPENDENCY_REGISTER.md`: the Plum Equipment Master row;
  - `pf-1f-hr/PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`, section F: the crew credential shape the certificate
    follows.
- **Source:**
  - the FRS (`docs/reference/erp-source-extracts/ERP_FUNCTIONAL_SPEC_FULL_TEXT_EXTRACT.md`):
    - Annexure-20 (the machine's validity fields and permits);
    - 3.6 "Maintenance Compliance & Statutory Gating";
    - the Controls' "Asset Documentation Warning";
    - Transportation's "Compliance Gating";
  - `TOOLS_AND_ASSET_ANNEXURES_EXTRACT.md`, Annexure-20.
- **Code:**
  - `equipment_reference/`: `contract.py`; `services/common.py` (`record_event`, the write lock); the
    details route; the migrations `0041` to `0043`;
  - `resource_requirements/service.py`: how a module reads the Equipment Reference;
  - `documents/contract.py` and `documents/service.py`: the linked record maps and `upload_document`;
  - `frontend/src/components/DocumentsPanel.tsx`;
  - the Equipment pages;
  - the dummified Plum fixture's columns.
- **Outside the repository:** the research of section 2.

---

## 4. What it builds

1. **Certificates on assets.** The Fleet Admin records certificates on a machine, a fitted part or a piece
   of kit, with a copy, and withdraws one recorded by mistake. Nothing is edited or deleted, so each
   machine's history of papers stays complete.
2. **"Not applicable", where the law is unclear.** The Fleet Admin marks a required certificate not
   applicable for one asset, with the reason and, where needed, an end date, only where the rule allows it
   (Q3).
3. **Jurisdictions.** A list of every state and union territory, plus the central government's own sites,
   for rules and decisions to refer to.
4. **Rules as data.** Each rule says which certificate an asset needs, depending on:
   - its class and type, and whether its registration says transport;
   - where and from when the rule applies.

   It also says how often the certificate is renewed, what a lapse does, whether "not applicable" may be
   claimed, and where the rule comes from. The first rules come with the package (section 5.4). Admin adds
   and ends rules on a screen (Q7).
5. **The decision.** Given a machine (with its fitted parts) or a piece of kit, a site and a period, the
   answer is `ELIGIBLE`, `WARNING`, `BLOCKED` or `OVERRIDE_REQUIRED`. It comes with a result for every
   certificate required, and the date until which the answer holds. A screen shows it. 8A calls the same
   service and stores the answer with the allocation.
6. **Certificates due.** Everything missing, run out, or running out within 60, 30 or 15 days, and every
   "not applicable" mark that ends within them.

---

## 5. The records

```text
Jurisdiction       each state and union territory, and the central government's sites    NEW
Certificate kind   registration, insurance, pollution, road tax, fitness, permit,         NEW
                   thorough examination, load test (section 5.4)
Certificate        one certificate of one asset: kind, number, issuer, dates, where      NEW
                   it is valid (a permit), registered as (a registration), a copy;
                   withdrawn only if recorded by mistake
Not applicable     one asset and one kind, where the rule allows it: the reason and     NEW
                   an optional end date; withdrawn when no longer true
Rule               a kind required of a class or type; where and from when; how often;   NEW
                   what a lapse does; whether "not applicable" may be claimed; its source
Decision           one answer for one asset, site and period, with a result for each     NEW
                   certificate required
Asset              the machine, fitted part or piece of kit                              unchanged (ERT-1, ERT-2)
Class, type        what a rule applies to                                                unchanged (WRR-001)
Fitted link        which parts count with their machine                                  unchanged (ERT-1)
Document           a certificate's copy                                                  unchanged; + a linked record type
```

### 5.1 Why the existing records do not carry certificates

| Existing record | Why it cannot hold a certificate |
| --- | --- |
| `equipment_asset` columns (ERT-1 section 5A put the platform's own facts there) | An asset has many certificates, of many kinds, each renewed again and again. A column holds one value, with no history, no issuer and no copy. Annexure-20's layout - one "validity" column per kind, one per state permit - is the shape this avoids |
| `equipment_asset_capability` | A capability measures what the machine can do, in a unit, from its model. A certificate is dated evidence from a third party |
| `equipment_asset_flag` | A flag says a Plum value is doubtful, and goes away when the cause does. A certificate is a record kept for years |
| `equipment_asset_correction` | A correction replaces a Plum value, and Plum holds no certificate dates (ERT-1, Q9) |
| `document_metadata` (Slice 9C) | A document holds the file, not what it certifies or until when. It is kept for the copy, attached to the certificate |
| The structure (class, part fit) | The structure says what a class is and what it takes. Which papers a class needs changes with the law and differs by state, so it is kept as dated rules instead (section 5.3) |

The assets, their fitted links and kit, the structure's codes and the documents are all reused as they are.

**Transport or not comes from the registration certificate, not a machine column.** The first proposal
added a per-machine choice of transport, non-transport or not a motor vehicle. Under the conservative
principle it is dropped (section 1.1):

- the registration certificate already says whether the vehicle is registered as transport - that is the
  evidence;
- "not a motor vehicle" is a claim that road papers do not apply. It is a "not applicable" mark on each
  road paper, allowed only where the law is unclear.

### 5.2 Where the records live

**The new module.** The certificates, "not applicable" marks, jurisdictions, rules and decisions live in a
new module, `backend/app/modules/eligibility/`. It is the **Compliance / Eligibility** row of
`MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`: "licence/certification/skill evidence and assignment eligibility
decision". It owns neither assignment state nor the Equipment Master.

- It reads the Equipment Reference only through that module's service, as Resource Requirements does.
- The Equipment Reference never reads it, and its tables do not change.
- The people half joins the same module in 8B, with the same rules, the same "not applicable" marks and the
  same decision. 8B decides whether a person's licence shares the certificate record. The certificate's
  fields already follow the crew credential shape of `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`, section F.

**Who is the source of a certificate** follows ADR-037 and its refinement:

- In Phase 1, statutory documents are Plum's where Plum holds them.
- Plum's report holds no certificate dates (ERT-1, Q9), only an insurance policy number and insurer (Q10).
- So each certificate is the platform's, entered by the Fleet Admin (refinement, point 1).
- The request to Plum for the Annexure-20 dates (route A) still stands.

### 5.3 The records in detail

**Jurisdiction.**

- One row for the central government's own sites: code `IN`.
- One row for each of the 36 states and union territories, coded by ISO 3166-2:IN: `IN-GJ`, `IN-MH`, and so
  on.
- Each row has its code, name, kind (`CENTRAL`, `STATE` or `UNION_TERRITORY`) and, where there is one, its
  GST state code.
- The migration loads them. A new state is added by a migration.

**Site** (what a decision is asked about, never stored on its own):

- its **state**: a state or union territory;
- whether it is **a central-government site** (Q8: PBL works at such sites).

Rules are then taken:

- for labour safety: from `IN` at a central-government site, and from the state everywhere else;
- for a permit: whether it covers the site's state.

**Certificate kind.** A short fixed list, loaded by the migration (section 5.4). Each kind says:

- whether its end date may be left empty (a one-time road tax, or an examination whose interval the rule
  sets);
- whether it is valid only in a named place (a permit);
- whether it is an examination, whose renewal interval a rule may set;
- whether it states how the vehicle is registered (a registration).

**Certificate.** One certificate of one asset. Its fields follow the crew credential shape (section 5.2):

```text
certificate public id
asset                  a machine, fitted part or piece of kit (equipment_asset)
kind
number                 as printed: the policy, registration, certificate or report number
issued by              the insurer, the registering authority, or the competent person with their
                       recognition number
issued on              the day it was issued, or the day of the examination
valid from, valid until    valid until may be empty only where the kind allows it
valid in               a permit only: the state, or IN for a national permit
registered as          a registration only: transport or non-transport, as the certificate says
copy                   a Slice 9C document linked to the certificate
status                 recorded, or withdrawn (recorded by mistake: reason, who, when)
recorded by, recorded at, request key (a repeated save has one effect, ADR-023)
```

- **A certificate is never edited.** A mistake is withdrawn, with a reason, and recorded again.
- **The certificate in force on a day.** For each asset, kind and "valid in", this is the one that is not
  withdrawn and has the latest "valid from" on or before that day. So:
  - a renewal recorded ahead of time takes over on its own start date;
  - withdrawing a wrong certificate brings the previous one back into force;
  - nothing is marked "superseded": it is worked out.
- **Cover.** A certificate covers until the earlier of two dates: its "valid until", and, for an
  examination, its "issued on" plus the renewal interval that the site's rule sets. So an examination made
  under a 12-month rule stops counting after 6 months where a 6-month rule applies.
- **Chained certificates.** A renewal that starts on or before the day after the old one ends continues its
  cover.

**Not applicable.** One asset and one certificate kind:

```text
not applicable public id
asset, kind
reason                 required: why the certificate does not apply to this asset
until                  optional; required where the rule limits how long (the first-year pollution
                       certificate: at most 12 months from the day it is recorded)
status                 in force, or withdrawn (reason, who, when)
recorded by, recorded at, request key
```

- **It counts only where the rule in force allows it.** A mark recorded under the baseline does not count at
  a site whose own rule allows none: there, the certificate is required.
- **It is refused** when no rule in force today allows it for that asset and kind, or when its end date
  goes past what the rule allows.
- **It is never edited.** It is withdrawn when it stops being true, or when recorded by mistake, and a new
  one recorded if needed.
- **On a machine**, a mark for a road paper covers the machine and its fitted parts, as a certificate does.

**Rule.** One requirement, in force for a period, in one jurisdiction or in all of them:

```text
rule public id
kind                   the certificate required
class, type            which assets; an empty type means every type of the class
applies when           always, or only when the registration in force says transport
jurisdiction           empty: the baseline for all of India, used where the site's own jurisdiction
                       has no rule for that kind
in effect from, to     "to" is empty until the rule is ended
renew every            months; needed on an examination; empty where the certificate states its own end
basis                  STATUTORY      the law, cited
                       PBL_RULE       PBL's own rule, where the law is silent or unclear (Q2)
lapse                  BLOCK          cannot be allocated, and nobody may override it
                       OVERRIDE       an authorised approver may accept it (Q11); never on STATUTORY
                       WARN           shown, never stops the allocation; never on STATUTORY
                       NOT_REQUIRED   this jurisdiction does not require what the baseline does
not applicable         may it be claimed for one asset: no, yes, or yes for at most N months - only
                       where the law is unclear (section 1.1)
source                 required: the Act, rule, form and notification, or PBL's decision and its date
note
recorded by and at; ended by and at, with a reason
```

- **Choosing the rule.** For an asset, a kind and a day:
  1. the site's jurisdiction's rule, if one is in effect; otherwise the baseline;
  2. within that, a rule for the asset's type first, then its class.

  If there is no rule, or the rule is `NOT_REQUIRED`, the certificate is not required.
- **No overlaps.** Two rules for the same kind, class, type, "applies when" and jurisdiction may not be in
  effect on the same day.
- **No edits.** A rule is ended on a date, and a new one added from the next day, so every past decision
  can be explained by the rules it used.
- **Unknown never counts as exempt.** An asset whose type is not known, because its Plum name is not yet
  mapped to a model, is judged by its class's rule, which allows no "not applicable" where any type of the
  class is clearly covered (section 5.4).

**Decision.** The answer of section 6, stored when 8A allocates on it:

```text
decision public id
asset and its version; the site's state and whether it is a central-government site; period from
and to ("to" may be empty: open-ended)
evaluated at; requested by; what asked for it - 8A's requirement or assignment public id
overall                ELIGIBLE, WARNING, BLOCKED or OVERRIDE_REQUIRED
valid until            the day the earliest required cover or "not applicable" mark ends
results                one per certificate required, for each asset of the unit: the rule, the
                       jurisdiction it came from, the certificate in force (or none), the "not
                       applicable" mark (or none), the outcome, what the lapse does, and the day
                       its cover ends; and the asset's own check (retired)
```

Rules, certificates and marks are never edited, so a decision's results name exactly the evidence and rule
versions it used (`ELA-001`: "rule results with rule/evidence versions").

### 5.4 The certificate kinds and the first rules

**Kinds:**

| Kind | What it is | End date | Also records |
| --- | --- | --- | --- |
| Registration | the registering authority's certificate | required (non-transport: 15 years, then 5-yearly) | registered as transport or non-transport |
| Insurance | motor insurance, at least third party | required | - |
| Pollution under control | the PUC certificate | required | - |
| Road tax | the state's tax receipt | may be empty, for a one-time tax | - |
| Fitness | the fitness certificate | required | - |
| Permit | a goods-carriage permit | required | valid in: a state, or all India for a national permit |
| Thorough examination | by a competent person | may be empty: the rule's interval sets it | - |
| Load test | test and examination by a competent person | may be empty: the rule's interval sets it | - |

**The first rules** are all baseline rules, applying everywhere. They are in effect from 21 November 2025,
the day the OSH Code replaced the old Acts. Nothing earlier is ever judged. Every one blocks when it lapses,
and none can be overridden.

*Road papers* - the law (MV Act 1988 and CMVR 1989), for the four Hiring classes:

| Certificate | Required of | Applies when | "Not applicable" | Source |
| --- | --- | --- | --- | --- |
| Registration, insurance, pollution certificate, road tax | every crane | always | no: a crane on wheels is a motor vehicle | ss.39, 41, 146; CMVR rr.52, 115(7); the state's Taxation Act; penalties ss.192, 196, 190(2) |
| the same | a crawler crane; a derrick | always | yes, with the reason: very likely not a motor vehicle (CMVR r.2(ca), Explanation) | the same |
| the same | every man lift, forklift and excavator | always | yes, with the reason: a tracked or towed machine, or one adapted for use only inside a plant (MV Act s.2(28)), may not be a motor vehicle | the same |
| Pollution certificate | every class above | always | also yes, for at most 12 months: the first year after registration (CMVR r.115(7)) | CMVR r.115(7) |
| Fitness | any of them | registered as transport | no | s.56; CMVR r.62; s.192 |
| Permit covering the site's state | any of them | registered as transport | no | s.66; s.192A |

*Lifting examinations* - PBL's rule where the law is silent or unclear (Q2):

| Certificate | Required of | Renew every | "Not applicable" | Source |
| --- | --- | --- | --- | --- |
| Thorough examination | cranes, man lifts, forklifts | 12 months | no | the old rules' 12 months (Factories s.29, BOCW r.56, Dock reg. 41), continuing in most states; no section 18 standard yet |
| Load test | cranes, man lifts, forklifts | 60 months | no | BOCW r.56; Dock reg. 41 |
| Thorough examination | each hook block, and each piece of tackle other than a sling | 12 months | no | BOCW rr.61, 70 and Form VII; the factories register |
| Thorough examination | each sling | **6 months** | no | IS 12735:1994, clause 5.3 - stricter than the rules' 12 months |
| Load test | each hook block and piece of tackle | 60 months | no | BOCW r.70 |

**Not required:**

- **Boom and jib sections** are examined with their crane.
- **Counterweight** needs no certificate.
- **A crane carrier** has no rule of its own. Its crane's road papers are usually recorded on it and count
  for the crane (section 6).
- **Excavators** need no lifting examinations: they are not lifting appliances.
- **Transportation's classes** - prime movers, trailers, trucks, hydraulic axles, power packs - get their
  rules when Transportation needs them (Q1). The fitness and permit rules already apply to any of the Hiring
  classes registered as transport.
- **Classes no business line uses** need nothing.

Where the law requires the same examination, PBL's rule holds it too, and both block. So the answer is the
same wherever the crane works. When a state's own rule needs to show as the law, or differs, Admin adds a
statutory rule for that state (Q7).

### 5.5 Authority by phase

| Fact | Phase 1 (now) | Changed on the platform by |
| --- | --- | --- |
| A machine's, part's or piece's certificates: number, issuer, dates, how it is registered, copy | **The platform**. Plum holds no dates (ERT-1, Q9); see Q10 for Plum's insurance number | the Fleet Admin |
| That a certificate does not apply to one asset, where the law is unclear | **The platform** | the Fleet Admin, with the reason |
| Which certificates an asset needs, where and how often | **The platform's rules**, from the law and PBL's rules (section 2) | Admin (Q7) |
| Whether a machine may work at a site | **Eligibility** (`ELA-001`) | nobody: it is computed |
| The site's state, and whether it is a central-government site | 8A (Q8) | - |
| Whether it was allocated, and on which decision | 8A (`RPA-001`) | - |

### 5.6 Room for change

As in ERT-2, room is left only where a later change would be expensive.

| What may vary | How the design takes it | Cost if it comes later |
| --- | --- | --- |
| A state publishes its own rules | A rule row for that state, from its date | None: Admin adds it (Q7) |
| The central standards under section 18 | Rule rows for `IN` and the baseline, from their date | None |
| The law becomes clear where it is unclear now | End the rule allowing "not applicable" and add one that does not; marks stop counting from that day | None: Admin (Q7) |
| A new certificate kind, such as a customer's third-party inspection | A row of the kinds | Small: a migration |
| A rule that is not the law | `PBL_RULE`, with `OVERRIDE` or `WARN` | Small: the approval route (Q11) |
| A state that accepts only its own competent persons (Gujarat's draft) | Not held: "issued by" keeps the recognition number as printed | Small: a "recognised in" field and a rule flag |
| Factory and construction sites in one state following different rules | Not held: the answer is the same today (section 5.4) | Small: a regime on the rule and on the site |
| People's licences (8B) | The same module, rules, marks and decision; the certificate follows the crew credential shape | Small |
| Emails, SMS and messages | Each escalation step carries its channels, screen only for now (section 19) | Moderate: `NTF-001` and ADR-019 are not built; then a channel is a setting |
| Escalation to a person's manager rather than a role | Steps name roles now | Small: a step names an `ORA-001` authority once positions are live (section 19) |
| Loading many certificates at once | The template upload of section 18 records through the same service | Small: its own package (Q12) |
| Checking against the government's records (Vahan) | "Issued by" and the number are kept as printed | Moderate: an integration (section 13) |
| Several permits in force for one vehicle | "Valid in" separates them | None |

---

## 6. The decision, step by step

The decision is asked about an asset, a site (its state, and whether it is a central-government site) and a
period (from, and to or open-ended). It is evaluated today, in Asia/Kolkata:

1. **The asset.**
   - It must exist and be active. A retired asset is `BLOCKED` ("retired", `RMR-001`).
   - A machine is judged together with its **fitted parts** (its open `FITTED` links, down to the depth
     setting), as one unit.
   - A piece of kit is judged alone. Kit is not part of a crane's decision, because kit is shared by model
     and not held by one crane (ERT-2, Q6). 8A asks about each piece it puts on a trip.
2. **The rules.** For each asset of the unit and each kind, take the rule in effect on the later of today
   and the period's start (section 5.3). Then:
   - a rule chosen for the machine's class is met by a certificate on the machine **or on one of its fitted
     parts**, because the carrier usually holds the road papers;
   - a rule for a part or a piece is met by that part or piece itself;
   - a rule that applies only to transport vehicles applies when the registration in force on the unit
     says transport. If no registration is in force, it applies: the cautious reading, since the machine's
     registration is then missing anyway.

     > **Changed by the owner, 1 October 2026** (at ELG-2's screen check; `elg-2-certificate-reminders.md`,
     > section 1.5 and refinement 12): with no registration recorded, a machine is **not** a transport vehicle;
     > fitness and a permit are needed once a registration saying transport is entered. A transport registration
     > that has run out still counts, unless the registration is then marked not applicable. This record is kept as
     > it was agreed; refinements 3 and 16 below are superseded in the same way.
3. **Each certificate required** is judged. A "not applicable" mark in force counts only if the rule
   chosen allows it. A permit must also be valid in the site's state, or in all of India.

   | Found | Outcome | Effect |
   | --- | --- | --- |
   | A "not applicable" mark the rule allows, in force today | `NOT_APPLICABLE` | none; its end date counts as the cover's end below |
   | No certificate in force today, or one without its copy (Q5) | `MISSING` or `COPY_MISSING` | the rule's lapse |
   | Cover ended before today | `RUN_OUT` | the rule's lapse |
   | Cover ends before the period starts | `RUNS_OUT_BEFORE_START` | warning (Q4) |
   | Cover ends within the period | `RUNS_OUT_IN_PERIOD` | warning |
   | Cover ends within 15 days (FRS, "Asset Documentation Warning") | `RUNS_OUT_SOON` | warning |
   | Otherwise | `VALID` | none |

4. **Overall.**
   - Any `BLOCK` lapse gives `BLOCKED`.
   - Otherwise, any `OVERRIDE` lapse gives `OVERRIDE_REQUIRED`.
   - Otherwise, any warning, or a `WARN` lapse, gives `WARNING`.
   - Otherwise the answer is `ELIGIBLE`.

   **Valid until** is the day the earliest required cover, or "not applicable" mark, ends.
5. **Kept or not.**
   - The screen's check keeps nothing.
   - When 8A allocates, it calls the same service inside its own transaction. The decision and its results
     are stored, `ELIGIBILITY_EVALUATED` is recorded, and the allocation keeps the decision's public id
     (`ELA-001`, `RPA-001`).
   - 8A cannot turn `BLOCKED` into an allocation (`ELA-001`).

A period whose end is before its start, or an unknown state, is refused (`422`).

**What 8A does with it** (recorded here so 8A need not work it out again):

- take the site's state from the Work Order line's site, and record whether it is a central-government site
  (Q8);
- check again before the planned start;
- show on an active allocation when a certificate's cover ends during it. Until a job runner exists, this is
  worked out when the allocation is read, from the decision's "valid until" and the certificates;
- ask about each piece of kit it puts on a trip;
- where a crane is erected on a construction site whose state's BOCW rules continue, record the test after
  erection (section 13).

---

## 7. Certificates due, and alerts

`ELA-001` asks for alerts 60, 30 and 15 days before a statutory document runs out, sent by the notification
service (`NTF-001`) from a recheck job (ADR-019). **Neither the notification service nor the job runner
exists yet**, so this package builds what needs neither (Q9).

**Certificates due** is worked out each time it is read, taking today's date in Asia/Kolkata.

- **What it covers.** Every active asset: machines, fitted parts and pieces of kit. For each, every
  certificate the **baseline** rules require today. A machine's road papers count when recorded on its
  fitted carrier, as in the decision (section 6).
- **Why the baseline.** Renewal is about the machine, not a site. A state's shorter interval shows when a
  machine is checked for a site there.
- **Bands:** missing, copy missing, run out, within 15 days, within 30 days, within 60 days. A "not
  applicable" mark with an end date is listed as it approaches, like a certificate running out.
- **Finding things.** Filters by band, class and kind; a search by machine number or reference; the count in
  each band at the top.

**Nothing is stored and nothing is sent by ELG-1.** The list is worked out by one service. That same answer
then feeds:

- the configurable reminders and escalation the owner asked for (Q4). They are designed in section 19, to be
  built as ELG-2 after 8A's core (Q14);
- later, a notification job, rather than a second copy of the rules.

`EligibilityExpiring`, `EligibilityRecheckScheduled`, `EligibilityLapsed` and `EligibilityRestored` need
the job runner and 8A's allocations, so they are left to those packages (section 13).

---

## 8. Screens

This package adds two new pages under Equipment, and two sections on the existing machine page. Messages sit
beside the button that caused them. Styling uses `globals.css` classes (CODING_STANDARDS.md section 7).

**A machine's page** gains **Certificates**, on every asset: machine, fitted part or piece of kit.

- It shows each kind required of the asset today by the baseline, and any other kind recorded. For each, it
  shows the certificate in force, or the "not applicable" mark:
  - kind, number (Q6), issued by, valid from and until, and for a registration "registered as transport"
    or "non-transport";
  - its status in words: "valid until 12 March 2027", "runs out in 12 days", "ran out on 3 September 2026",
    "missing", "copy missing" or "not applicable: <reason>";
  - its copy (Q6).
- On a crane, it also shows its fitted carrier's certificates, marked "on its carrier EQ-000123".
- Earlier and withdrawn certificates and marks are under "Earlier".
- For the Fleet Admin:
  - **Record a certificate**: kind, number, issued by, issued on, valid from and until, "valid in" for a
    permit, and "registered as" for a registration;
  - then **Attach its copy**, with the shared `DocumentsPanel`;
  - **Mark not applicable**, with the reason and, where needed, the end date - offered only for the kinds
    whose rule allows it, with the rule's wording on when it applies;
  - **Withdraw** a certificate or a mark, with a reason.
- For a piece of tackle or a hook block, the form shows its mark - its own number, or "stencil EQ-000512 on
  it" - so the certificate can be matched to the piece (ERT-2, Q5).

**A machine's page** also gains **Check for a site**, for everyone who sees machines.

- Enter the site's state, whether it is a central-government site, and the dates.
- The answer is shown in words, with the result for each certificate.
- For a piece of kit, the section reads "Check for a trip".

**Certificates due** (`/equipment/certificates`) is the list of section 7, with its counts. It is linked
from the header of the Equipment pages, beside Models and Plum report.

**Certificate rules** (`/equipment/certificate-rules`) lists the rules by jurisdiction and kind, each with
its source, its basis and whether "not applicable" may be claimed, and the rules that have been ended. For
Admin: **Add a rule** and **End a rule** (Q7).

**A screen check fits in twenty minutes**, on a seeded wheeled crane with a fitted carrier, a crawler crane
and a hook block:

1. Open Certificates due: the seeded cranes show their papers missing.
2. On the wheeled crane's carrier, record the registration (non-transport), insurance, pollution
   certificate and road tax, attaching a copy to each. On the crane, record the thorough examination and the
   load test.
3. Check the wheeled crane for a site in Gujarat for the next month: *can be allocated*.
4. On the crawler crane, mark the road papers not applicable, with the reason. Try the same on the wheeled
   crane: it is not offered.
5. On a second wheeled crane, record a registration as transport and a fitness certificate that ran out
   last week. Check it: *cannot be allocated*, with the reason.
6. Record an insurance certificate running out in ten days: *can be allocated, with a warning*.
7. Withdraw a certificate recorded by mistake: the previous one is in force again.
8. Add a rule for a state, and see a check there use it.
9. As a read-only user: certificates, marks and checks are visible, numbers and copies are withheld (Q6),
   and there are no buttons.

---

## 9. Permissions

| Permission | Granted to | Allows |
| --- | --- | --- |
| `EQUIPMENT_REFERENCE_READ` (exists) | the six current roles | seeing certificates (kind, issuer, dates, status) and marks, the check, Certificates due and the rules |
| `EQUIPMENT_IDENTITY_READ` (exists) | Admin | seeing certificate numbers, and reading and downloading copies (Q6) |
| `EQUIPMENT_REFERENCE_MANAGE` (exists) | Admin | recording and withdrawing certificates and "not applicable" marks, and attaching copies |
| `ELIGIBILITY_RULE_MANAGE` (**new**) | Admin | adding and ending rules (Q7) |

There is one new permission, for two reasons:

- rules are law rather than fleet data;
- the people half's rules will sit under the same permission, so a compliance officer can be given it
  without the fleet's rights.

A Fleet Admin role, when it exists, is given `EQUIPMENT_REFERENCE_MANAGE` by a grant, as before.

---

## 10. Routes

**The new routes** are under `/api/eligibility`, each pinned in `POST_BASELINE_NEW_ROUTES`. A new contract,
`docs/agent/contracts/eligibility-api-contract.md`, states what they accept, return and refuse.

```text
GET  /jurisdictions                                                                   READ
GET  /certificate-kinds                                                               READ
GET  /assets/{asset_public_id}/certificates      in force and earlier, with marks      READ
POST /assets/{asset_public_id}/certificates      record one                            MANAGE    201
     {create_request_key, kind_code, number, issued_by, issued_on, valid_from, valid_until,
      valid_in_code, registered_as_code}
POST /certificates/{certificate_public_id}/withdraw    {reason}                         MANAGE
POST /assets/{asset_public_id}/not-applicable    mark one                              MANAGE    201
     {create_request_key, kind_code, reason, until}
POST /not-applicable/{mark_public_id}/withdraw   {reason}                               MANAGE
GET  /assets/{asset_public_id}/check?state_code&central_government_site&period_from&period_to
                                                                                      READ
GET  /certificates-due?band&class_code&kind_code&search&limit&offset                    READ
GET  /rules?jurisdiction_code&kind_code&class_code&in_effect_on                         READ
POST /rules                                      add one                               RULE_MANAGE  201
     {create_request_key, kind_code, class_code, type_code, applies_when_code, jurisdiction_code,
      effective_from, renew_every_months, basis_code, lapse_code, not_applicable_code,
      not_applicable_max_months, source, note}
POST /rules/{rule_public_id}/end                 {effective_to, reason}                 RULE_MANAGE
```

**Copies** go through the existing `POST /api/documents/upload`, with linked record type
`eligibility_certificate` and a new document type `CERTIFICATE`.

- The documents module's two maps each gain one entry: reading and downloading need
  `EQUIPMENT_IDENTITY_READ` (Q6); attaching needs `EQUIPMENT_REFERENCE_MANAGE`.
- A withdrawn certificate refuses a new copy.

**Refusals** follow the Equipment Reference's conventions: `{"detail": "..."}` in plain words; `404`, `409`,
`422`; unknown fields refused.

- A certificate is refused when:
  - its end is before its start;
  - its end is missing on a kind that needs one;
  - "valid in" is missing on a permit, or given on another kind;
  - "registered as" is missing on a registration, or given on another kind;
  - its kind is not one any rule could require of that asset.
- A "not applicable" mark is refused when:
  - no rule in force today allows it for that asset and kind;
  - its end date is missing, or too far ahead, where the rule limits how long;
  - it has no reason.
- A rule is refused when:
  - it overlaps another rule;
  - it has no source;
  - it is statutory with a lapse other than block or not required;
  - it is an examination without an interval.
- A rule's end may not be before its start.

**For 8A**, two service functions, with no route of their own:

- `evaluate_asset(...)`: the check;
- `record_decision(...)`: the check, stored in the caller's transaction, returning the decision's public id.

**Numbers are withheld** from a caller without `EQUIPMENT_IDENTITY_READ`, as engine and chassis numbers are:
`number: null`, `number_withheld: true`.

**No existing route changes.** The Equipment Reference gains one read in its service, for Eligibility.

---

## 11. Events

The record types are `eligibility_certificate`, `eligibility_not_applicable`, `eligibility_rule` and
`eligibility_decision`. The source module is `eligibility`.

| Event | Payload |
| --- | --- |
| `ELIGIBILITY_CERTIFICATE_RECORDED` | the asset's public id and reference, kind, issued on, valid from and until, valid in, registered as |
| `ELIGIBILITY_CERTIFICATE_WITHDRAWN` | the same ids and kind. The reason is the event's reason, not its payload |
| `ELIGIBILITY_NOT_APPLICABLE_RECORDED`, `ELIGIBILITY_NOT_APPLICABLE_WITHDRAWN` | the asset's public id and reference, kind, until, the rule that allowed it. The reason is the event's reason, not its payload |
| `ELIGIBILITY_RULE_RECORDED`, `ELIGIBILITY_RULE_ENDED` | kind, class, type, applies when, jurisdiction, dates, interval, basis, lapse, "not applicable" |
| `ELIGIBILITY_EVALUATED` | decision public id, asset, the site's state and whether it is a central-government site, period, overall answer, valid until, the count of each outcome, and what asked for it |
| `DocumentUploaded` (exists) | attaching a copy, as for every upload |

As in ERT-1 and ERT-2, payloads carry public ids, references, codes, versions, counts and dates only. They
never carry a certificate number, a machine number, an issuer's name, a source text or a reason's text.
`ELIGIBILITY_EVALUATED` is recorded only when a decision is stored, never for the screen's check.

---

## 12. Data, module and migration

**Module** `backend/app/modules/eligibility/`:

```text
contract.py      kinds, outcomes, basis, lapse, "not applicable" and band codes, the 15-day warning
                 and the 60/30/15 bands, events
evaluation.py    the decision, pure: choosing rules, cover, marks, outcomes, overall. No database,
                 as ERT-1's plum_report.py is pure
repository.py, service.py, schemas.py, routes.py
```

- `service.py` is split into `services/` only if it outgrows one file (CODING_STANDARDS.md, "When a service
  outgrows one file").
- It reads assets, their fitted parts and their classes through one new read in
  `equipment_reference.service`: the asset with its open fitted links, and the active assets for the due
  list.

**Migration `20260908_0044_machine_eligibility`**, parent `20260908_0043` (Q13). It follows the convention
of migrations 0033 to 0043: its rows are spelled out, not imported, so the revision stays a frozen snapshot.

- **`eligibility_jurisdiction`** (code, name, kind, GST state code), with its 37 rows.
- **`eligibility_certificate_kind`** (code, label, end date optional, valid in a place, examination, states
  registration), with the kinds of section 5.4.
- **`eligibility_certificate`.**
  - Keys to `equipment_asset`, the kind and the jurisdiction.
  - CHECKs that:
    - the end is not before the start;
    - an end is missing only where the kind allows it;
    - "valid in" is given exactly where the kind needs it;
    - "registered as" is given exactly on a registration;
    - a withdrawn certificate has its reason, who and when.
  - The request key is unique.
- **`eligibility_not_applicable`.**
  - Keys to `equipment_asset` and the kind.
  - CHECKs that it has a reason, and that a withdrawn mark has its reason, who and when.
  - The request key is unique.
  - The rule that allowed it is checked by the service under the module's write lock; the rule is kept on
    the mark for the event and for the record.
- **`eligibility_rule`.**
  - Keys to the kind, `equipment_class`, (`equipment_class`, `equipment_type`) as a composite, and the
    jurisdiction.
  - CHECKs on:
    - the dates, and the interval (above zero, and only on an examination kind);
    - the codes, and a non-blank source;
    - "statutory means block or not required";
    - "not applicable" limited to at most some months only where it is allowed.
  - Overlapping rules are refused by an exclusion constraint on the period (PostgreSQL's `btree_gist`), and
    by the service under the module's write lock.
- **`eligibility_decision`** and **`eligibility_decision_result`.**
- **The rules of section 5.4.**
- **`ELIGIBILITY_RULE_MANAGE`** and its grant to Admin.

No other table changes. The documents module changes in code only (its two maps and its type list), because
`linked_record_type` is free text.

---

## 13. Not in this package

| Left out | Where it goes |
| --- | --- |
| The people half: crew licences and certificates, what operating a machine requires, the HR reference | 8B, with the same module, rules, marks and decision |
| Configurable repeated reminders and escalation paths, on screen, for certificates running out, and running out before or during a job (Q4) | ELG-2, after 8A's core and before the Hiring user test (Q14); designed in section 19 |
| Emails, SMS and messages for those reminders; the recheck job; `EligibilityExpiring`, `EligibilityLapsed`, `EligibilityRestored` | the notification service (`NTF-001`) and the job runner (ADR-019), when built: each escalation step is then given its channels (section 19); 8A consumes the lapse |
| Blocking an active allocation whose certificate lapses (`COMPLIANCE_BLOCKED`, `RPA-001`) | 8A, worked out when read until a job runner exists |
| The site's state, and marking central-government sites | 8A (Q8: PBL works at such sites) |
| The test and examination after a crane is erected on a construction site (BOCW, where continuing) | 8A, at mobilisation, recorded per erection |
| Approving a gap that is not the law | the approval capability (`APR-001`, `ORA-001`), when such a rule is wanted (Q11) |
| Customers' own requirements: third-party inspection, NTPC's standard, OISD | a Work Order's requirements, later. A kind and a `PBL_RULE` rule can carry them |
| Monthly chain and 3-monthly wire-rope checks, the automatic safe load indicator's test, pre-use checks | log sheets (8C) and Maintenance: they are checks by a responsible person, not certificates |
| A repair or alteration calling for a new load test | Maintenance, when built. Until then, the Fleet Admin records the new test |
| Preventive maintenance due, which the FRS makes a warning at allocation | Maintenance, when built (`RPA-001`: its restrictions come from Plum Maintenance) |
| Fire extinguishers and first-aid boxes (FRS 3.6, component-level certification) | 8A's check before a machine goes to site (Q1) |
| Rules for Transportation's vehicles: prime movers, trailers, trucks, hydraulic axles, power packs | Transportation, as rules (Q1, Q7) |
| Comparing Plum's insurance number with the platform's | later, if wanted (Q10) |
| Reading certificates from the government's Vahan records | a later integration (section 5.6) |
| The spreadsheet upload of certificates | its own package before go-live, as designed in section 18 (Q12) |
| An emission-stage field | not needed: the pollution certificate states its own validity |

Requirements (WRR-001), the Work Orders module, the Equipment Reference's tables and the frozen Slice 6D.1
handoff contract do not change. The Equipment Reference gains one read in its service.

---

## 14. What would stop implementation and come back to the owner

- A finding while building that changes a rule's lapse from blocking to warning, or the reverse, or that
  makes the law clear where "not applicable" is now allowed (or unclear where it is not).
- Plum beginning to send certificate dates, which makes Plum their source (ADR-037).
- A need for emails before the notification service exists. That needs an email provider, which is an
  external dependency.
- A central standard under section 18 published before the package is built. It would be added as rules;
  it would come back to the owner only if it changes Q2.

---

## 15. Differences from earlier records (recorded per ADR-013)

| Earlier record | ELG-1 | Why |
| --- | --- | --- |
| ERT-1, Q9: statutory dates "are Plum's facts in this phase ... stay on the list we ask Plum for"; how they come in to be "decided when Eligibility is designed" | Entered by the Fleet Admin on the platform. The request to Plum stands | Plum holds no dates; ADR-037 refinement, point 1 |
| ERT-1, section 5A: later packages add their facts "the same way" as serial number and year | Certificates and "not applicable" marks are records of their own, keyed on the asset; the Equipment Reference's tables do not change | Many certificates per asset, renewed, each with an issuer and a copy (5.1) |
| This design's first proposal (`9a1057d`): a per-machine choice of transport, non-transport or not a motor vehicle | Transport or not read from the registration certificate; "not a motor vehicle" becomes a "not applicable" mark, allowed only where the law is unclear | The owner's conservative principle (section 1.1) |
| `RMR-001`: the equipment reference carries "required document/evidence references" | The Eligibility module holds the certificates, keyed on the asset's public id; the machine page shows them | The boundary matrix gives certification evidence to Compliance / Eligibility; no fact has two owners |
| FRS Annexure-20: one validity column per kind, one per state permit | One certificate record per certificate, with "valid in" for permits | History, issuer and copy; any state, not only the five named |
| FRS 3.6 and FUTURE_SLICES: every machine needs fitness and permits | Transport vehicles only; registration added | The research (section 2, B and E) |
| FRS 3.6: load test certificates block deployment | Every required certificate blocks | The same law stops a machine without insurance or registration (section 2) |
| FRS Controls: warn when the load test or fitness certificate is within 15 days of expiry | A warning for every required certificate within 15 days | A lapse of any of them stops the machine |
| FRS 3.6: a 30-day look-ahead report for insurance renewals | Certificates due, in 60, 30 and 15-day bands, for every kind | `ELA-001`'s bands include 30 |
| `ELA-001`: alerts sent at 60, 30 and 15 days by a job | ELG-1: shown on a list worked out when read; nothing is sent. ELG-2: a configurable schedule of repeated reminders - 60, 30 and 15 days by default, then weekly and daily - with a configurable escalation path, on screen, with other channels added when integrated (section 19) | Neither the notification service nor the job runner exists (Q9); the owner's addition to Q4 |
| `ELA-001` and NTF-001: alerts "to the employee and HR manager, plus the operational owner where assignment is affected" | For machines, a configurable path of roles: the Fleet Admin, Operations and Management by default (Q16), and positions once `ORA-001` is live | Machines have no employee; the owner asked for configurable escalation |
| ERT-2, section 2, H1 and H4, and `DEFERRED_REQUIREMENTS.md` "Statutory requirements found with ERT-2" | Corrected by section 2, E; the deferred record is updated when this package is built | Research of 27 September 2026 |
| `FUTURE_SLICES.md`: what operating a machine requires is held "in the Equipment Reference beside what the class can do" | Not affected: that is the people half. The machine's own requirements are Eligibility's rules, because they change with the law and differ by state. 8B may follow the same pattern | The owner's rule: examination rules as data per jurisdiction |
| ERT-2 Q5: the Eligibility foundation "will require a mark on every piece of tackle and every hook block" | The mark is the piece's own number, or its `EQ-` number stencilled on it. The record form shows it | ERT-2 Q5 itself: "the platform's `EQ-` number can be stencilled on it" |

---

## 16. Tests and checks

- **The pure decision** (`evaluation.py`):
  - rule choice: a state's rule before the baseline; `IN` at a central-government site; type before class;
    `NOT_REQUIRED`;
  - rules by date, including one ending and its successor starting;
  - cover: by "valid until", by an examination's interval, by the earlier of both, and by chained renewals;
  - a renewal recorded ahead of its start;
  - a withdrawn certificate bringing back the one before;
  - "not applicable": counted where the rule allows it; not counted at a site whose rule does not; its end
    date as the cover's end;
  - the transport-only rules: applying on a transport registration, not on a non-transport one, and applying
    while no registration is in force;
  - a permit valid in another state not counting;
  - an unmapped crane judged by its class rule;
  - the carrier's certificates counting for its crane;
  - every outcome of section 6, the overall answer, and an open-ended period.
- **Certificates:**
  - recording; the same request key twice has one effect;
  - each CHECK refused by both the service and the database;
  - withdrawing, twice with one effect;
  - a copy attached and read only with the right permission;
  - a withdrawn certificate refusing a copy.
- **"Not applicable":**
  - recorded where a rule allows it; refused where none does (a wheeled crane's registration), with no
    reason, or with an end past the rule's limit (the first-year pollution certificate);
  - withdrawn, twice with one effect.
- **Rules:**
  - adding and ending;
  - an overlap refused by both the service and the database;
  - a statutory rule that does not block, refused;
  - a missing source refused;
  - the seeded rules loading, with "not applicable" exactly where section 5.4 allows it.
- **Checks and the due list:** a retired asset blocked; every band; an ending mark listed; the counts; the
  filters; a fitted carrier's papers on its crane.
- **Permissions:**
  - every write refused to every role but Admin;
  - rules refused without the new permission;
  - numbers and copies withheld without `EQUIPMENT_IDENTITY_READ`.
- **Events:** payloads carry no number, issuer, source or reason text; `ELIGIBILITY_EVALUATED` only when
  stored.
- **Migration:** from the empty database to the single head; downgrade removes it cleanly.
- **Smoke data and cleanup:**
  - `equipment-plum-import` and the core bundle's seventh record set gain certificates on the invented
    crane and carrier, and a crawler crane with its road papers marked not applicable;
  - cleanup removes the run's certificates, marks, copies and decisions by the run's assets;
  - it refuses, deleting nothing, when a certificate or mark it did not make is on one of them.
- **E2E:**
  - Admin records a certificate with its copy and checks a crane, first blocked and then allowed;
  - Admin marks a crawler crane's road papers not applicable;
  - a read-only user sees certificates without numbers or buttons.
- **Full gate:**
  - full backend regression, the frontend gate and E2E;
  - the frozen handoff contract's hash, before and after;
  - independent review;
  - the owner's screen check, with the steps in the chat.

---

## 17. Shared files this package touches

- `backend/app/main.py`: the new router.
- `backend/app/modules/authorization/contract.py`: `ELIGIBILITY_RULE_MANAGE`.
- `backend/tests/fixtures/post_baseline_tightened_routes.py`: the new routes. Read it by eye after any merge.
- `frontend/src/routes.tsx` and its tests: two URLs.
- `backend/app/modules/documents/contract.py`: the linked record type and the document type.
- `backend/app/modules/equipment_reference/service.py`: one read.
- `backend/tooling/smoke_data/` and `e2e/`.

**Documents updated when it is built:**

- the new `eligibility-api-contract.md`;
- `CONTRACT_REGISTRY.md` (a note on `ELA-001` that its machine half is built);
- `documents.md`;
- this design's implementation record, and an acceptance record;
- `FUTURE_SLICES.md`, and `DEFERRED_REQUIREMENTS.md` (including the corrections of section 2, E);
- the Compliance / Eligibility row of `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`;
- `NEXT_STEPS.md`, and a continuity note.

---

## 18. The spreadsheet upload of certificates (for its own package, Q12)

Designed now, in answer to the owner's question of 27 September 2026, so that ELG-1's records suit it. It is
built as a small package of its own before go-live unless the owner wants it in ELG-1 (Q12).

**A template, not a guess.** The platform reads the file exactly as the template says. It does not guess
which column is which from the column names, for three reasons:

- the same file must always be read the same way: ADR-030 keeps repeatable processing deterministic, and
  allows AI only where judgement adds value and a business need is separately approved;
- certificate numbers are confidential (Q6), and guessing with AI would send them to a service outside the
  platform;
- a statutory record read wrongly would allow a machine that should be blocked.

**The steps** are the same as the Plum report's (ERT-1): download, fill, upload, preview, confirm.

1. **Download the template** from Certificates due: a spreadsheet (`.xlsx`) with three sheets.
   - **Certificates.** One row per certificate, in fixed columns: machine number or `EQ-` reference; kind;
     number; issued by; issued on; valid from; valid until; valid in (a permit); registered as (a
     registration); the copy's file name (optional).
   - **Instructions.** What each column means, the date format, and an example row.
   - **Lists.** The valid entries, from the platform on the day of download: the fleet's active machines,
     parts and pieces of kit, with numbers and references; the certificate kinds; the states.
   - The kind, "valid in" and "registered as" columns offer drop-downs from these lists, so most mistakes
     cannot be typed.
2. **Fill it in** in Excel, and save it.
3. **Upload it.** The header is checked against the template: a missing, renamed or extra column refuses
   the file and names the column. The file is read in memory and not kept, as the Plum report is (it holds
   certificate numbers).
4. **Preview.** Nothing is saved yet. Each row shows the certificate it would record, or the reason it cannot
   be taken, for example:
   - a machine not found, or retired;
   - a kind the rules never require of it;
   - an end before its start;
   - a permit without "valid in", or a registration without "registered as";
   - the same certificate twice in the file, or one already recorded.
5. **Confirm.** Every row that can be taken is recorded in one step, through the same service as the screen,
   with the same checks and events. Repeating a confirmation records nothing twice (ADR-023).
6. **Copies.** Each certificate is then shown "copy missing" (Q5) until its copy is attached, either one at a
   time on the machine page, or by uploading the scans together, each matched to its row by the file name in
   the sheet.

**Later, if the Fleet Admin's own spreadsheets use other headings,** a one-time step can match their columns
to the template's on screen, and keep that match for the next upload, as Plum's model names are matched once
in ERT-1. AI could then *suggest* the match for the Fleet Admin to confirm, once AI is approved for the
platform (ADR-030).

**One new library.** Writing a template with sheets and drop-downs, and reading the Excel file back, needs a
library the backend does not have: `openpyxl`, the usual pure-Python one. CODING_STANDARDS.md section 1 asks
for the reason to be recorded, and that package records it. A plain CSV template, like Plum's report, would
need no new library, but has no instructions sheet and no drop-downs, so more rows would come back refused.
The `.xlsx` template is recommended.

**What it needs from ELG-1:** nothing more. Recording a certificate is one service function with its checks,
and the upload calls it for each row. The template's lists come from the existing reads.

---

## 19. Reminders and escalation (designed now, built as ELG-2, Q14)

The owner's addition to Q4, 27 September 2026 (section 1.1):

> A certificate that runs out before the job starts should be flagged and configurable reminders repeated
> with configurable escalation paths as well as certificates that run out during the job currency should be
> flagged and configurable reminders repeated with configurable escalation paths. Of course, for now, alerts
> can be screen based and when other channels are available and integrated, they can be configured for use
> for these alerts.

This section designs it now, so that ELG-1's records suit it. It is built after 8A's core, unless the owner
says otherwise (Q14).

### 19.1 What raises a reminder

| Reminder | Raised for | Its date | Ends when |
| --- | --- | --- | --- |
| **A certificate running out** | every active asset whose required certificate (baseline rules, as on Certificates due) is missing, has no copy, has run out, or runs out within the schedule's first reminder; and every "not applicable" mark ending that soon | the day its cover ends (today, when missing) | a certificate in force, with its copy, covers past the schedule's reach; or a mark applies; or the asset is retired |
| **A certificate running out before the job starts** | a machine or piece allocated by 8A, whose cover ends before its allocation starts, judged by the site's rules (section 6) | the day its cover ends | the cover reaches the start; or the allocation is released or the machine replaced |
| **A certificate running out during the job** | a machine or piece allocated by 8A, whose cover ends before its allocation ends | the day its cover ends | the cover reaches the allocation's end; or it is released or replaced; or the allocation ends |

- The first reminder is worked out from Certificates due.
- The other two are worked out from 8A's allocations, through the same decision service, for the site each
  allocation is at.
- One certificate can raise several reminders: one for the renewal list, and one for each allocation it
  affects.

### 19.2 The schedule, set for each reminder

A schedule is a list of bands. Each band says: from N days before the date, repeat every M days.

| From | Every | Reminders, in the standard schedule (Q15) |
| --- | --- | --- |
| 60 days before | 30 days | 60 and 30 days before |
| 15 days before | 7 days | 15 and 8 days before |
| 7 days before | 1 day | every day from 7 days before |
| the day it runs out, and after | 1 day | every day until dealt with |

- **Allocation reminders.** A reminder is also raised on the day the machine is allocated, if that day
  falls inside the schedule. This is the "flag" the owner asked for, beside the warning on the
  allocation's answer.
- **Each reminder has an occurrence date, which is its identity.** Acknowledging it happens once per
  reminder, per person, per occurrence, and so will sending it by other channels later. This is what
  `NTF-001` asks: never the same notification twice for the same occurrence.

### 19.3 The escalation path, set for each reminder

A path is an ordered list of steps. Each step adds an audience from a point in the schedule. Nobody drops
off.

```text
step           1, 2, 3 ...
audience       a role now: Admin (the Fleet Admin), Operations, Management, Sales, Finance.
               Later, an ORA-001 authority, once positions are live - "the Operations head for the
               site's region", say
from           N days before the date (negative: after it has run out); or, for the allocation
               reminders, "from the allocation"
channels       SCREEN now; email, SMS or a messaging channel once integrated (NTF-001)
```

**The standard path (Q16):**

1. the Fleet Admin, from the first reminder;
2. Operations, from 15 days before, and from the allocation for an allocated machine;
3. Management, from 7 days before.

All steps are on screen.

### 19.4 On screen, for now

- **The menu** shows **Alerts**, with a count: the reminders due today for the signed-in person's roles
  that they have not acknowledged.
- **The Alerts page** lists them. For each it shows:
  - the machine and the certificate, and the certificate's date;
  - what it means, for example "runs out on 5 October, before the job at <site> starts on 20 October";
  - how many reminders have been raised so far, and who it has reached;
  - links to the machine and, for an allocation, to the allocation.
- **Acknowledge** quiets a reminder for that person until its next occurrence (Q17). It never stops the
  escalation and never ends the reminders.
- **Nothing is sent.** The screen is the only channel until others are integrated.

### 19.5 Channels, once integrated

Each step already names its channels, which today can only be SCREEN. Once `NTF-001` is built with a
provider (email first, for example):

- Admin adds that channel to a step;
- a job (ADR-019) sends each reminder occurrence to that step's audience, once;
- the screen keeps showing the reminder.

Nothing else in the reminders changes. The same holds for every alert this design raises (the owner's note
on Q9 to Q13).

### 19.6 Records, settings and permissions

**Worked out when read**, as Certificates due is, so the screen needs no job runner:

- a reminder is due when today reaches one of its occurrence dates;
- it has reached a step's audience once today is past the step's start.

**Stored:**

- **`eligibility_alert_setting`**: one version for each kind of reminder, holding its bands and its steps.
  A version is in effect from when it was saved, with who saved it and when. Nothing is edited: a change
  is a new version.
- **`eligibility_alert_acknowledgement`**: who acknowledged which reminder occurrence, and when.

**Settings screen** (`/equipment/alert-settings`): for Admin, with `ELIGIBILITY_RULE_MANAGE` (Q18). The
standard schedule and path of Q15 and Q16 come with the package.

**Reading and acknowledging:** anyone the reminder has reached, with `EQUIPMENT_REFERENCE_READ`. The
service checks the person's roles against the steps reached.

**Events:**

- `ELIGIBILITY_ALERT_SETTING_CHANGED`: the kind of reminder, and the new version's bands and steps, as codes
  and numbers.
- Acknowledging records no business event. The acknowledgement is itself the record of who saw what, and
  when.

### 19.7 What ELG-1 already provides for it

- **The sources.** Certificates due, and the decision's outcomes, are what raises the reminders.
- **Fixed dates.** Certificates and marks are never edited, so a reminder's date moves only when a new
  certificate or mark is recorded.
- **The flags.** The check's `RUNS_OUT_BEFORE_START` and `RUNS_OUT_IN_PERIOD` outcomes, which 8A shows on
  each allocation.

ELG-2 then adds:

- the settings;
- the acknowledgements;
- the Alerts page and its count;
- with 8A's allocations, the two allocation reminders.

---

## 20. Implementation record (27 September 2026)

Built on `hiring/elg-1-machine-eligibility` in worktree `<a separate worktree>`, from the design commits and
`main` at `d4c2dd5` (merged into the branch as `49c795a`). The owner's "go ahead and build it", 27 September
2026 (section 1.3). Migration `20260908_0044`, parent `20260908_0043`; no branch on `origin` held a `0044`
(checked when the build began). Sections 4 to 17 are built; section 18 (the spreadsheet upload), section 19
(reminders and escalation, ELG-2) and the people half are not.

### What exists now

```text
backend/alembic/versions/20260908_0044_machine_eligibility.py
        eligibility_jurisdiction (IN and the 36 states and union territories, with GST state codes),
        eligibility_certificate_kind (8), eligibility_certificate, eligibility_not_applicable,
        eligibility_rule (the exclusion constraint on overlapping periods, btree_gist), the 43 first rules
        of section 5.4, eligibility_decision, eligibility_decision_result; ELIGIBILITY_RULE_MANAGE for Admin
backend/app/modules/eligibility/
        contract.py, evaluation.py (the decision, pure), repository.py, service.py, schemas.py, routes.py
backend/app/modules/equipment_reference/service.py, repository.py
        one read for Eligibility: an asset with its fitted parts, and every active asset with its own
backend/app/modules/documents/contract.py, service.py, repository.py, routes.py
        linked record type eligibility_certificate in both maps; document type CERTIFICATE; the owning
        module's attach check (register_attach_check); whether records have a document
backend/app/modules/authorization/contract.py     ELIGIBILITY_RULE_MANAGE
backend/app/main.py                                the router
backend/tests/fixtures/post_baseline_tightened_routes.py    the 12 routes
backend/tooling/smoke_data/                        a second wheeled crane with its carrier, certificates, marks
                                                   and a sling in equipment-plum-import and the core bundle;
                                                   cleanup of certificates, marks, decisions and copies
frontend/src/pages/equipment/MachineCertificates.tsx       Certificates and "Check for a site" on every asset
frontend/src/pages/equipment/CertificatesDuePage.tsx       /equipment/certificates
frontend/src/pages/equipment/CertificateRulesPage.tsx      /equipment/certificate-rules
frontend/src/pages/equipment/certificatesState.ts          the screens' rules, tested
frontend/src/components/DocumentsPanel.tsx, PageLayout.tsx  two optional props; a tone for StatusBadge
e2e/tests/equipment-certificates.spec.ts
docs/agent/contracts/eligibility-api-contract.md
```

### Refinements made while building (recorded per ADR-013)

None changes an answer of the owner's, a rule's lapse, or where "not applicable" is allowed (section 14).

| # | Design said | Built | Why |
| --- | --- | --- | --- |
| 1 | Certificates, marks and decisions "key to `equipment_asset`" | Keyed on `equipment_asset.asset_public_id`, with a foreign key to it | Only public ids cross the module boundary (ADR-007, ADR-017); the database still refuses an unknown asset |
| 2 | A machine's rule is met by it or its fitted parts; a part's or piece's rule by itself | Every asset's rule is met by the asset and the parts fitted below it | The same rule, stated once; the same answers today, as fitted parts carry no rules of their own |
| 3 | "If no registration is in force, [a transport-only rule] applies" | ... unless the registration itself is marked not applicable | A crawler crane's marks say it is not a motor vehicle; without this it would need fitness and a permit, which the law clearly limits to transport vehicles and which cannot be marked, so it could never be allocated |
| 4 | Labour-safety rules from `IN` at a central-government site | The examinations follow `IN` there; road papers always follow the site's state | The two regimes of section 2, named by the kind's own "examination" flag |
| 5 | An examination covers "issued on plus the renewal interval" | Until the day before the anniversary | The cautious reading of "every 12 months"; a mark's limit ("at most 12 months") is counted the same way |
| 6 | - | A retired fitted part's certificates do not count for its machine | The conservative principle: a part no longer in use is no evidence |
| 7 | "Cover ends within the period" | With an open-ended period, any cover with an end runs out within it | The period has no end, so the cautious reading warns |
| 8 | "Valid until is the day the earliest required cover ... ends" | Empty when the answer is `BLOCKED` | A blocked machine is not allocated; a date would suggest otherwise |
| 9 | "A withdrawn certificate refuses a new copy" | The documents module lets the owning module register a check on one record (`register_attach_check`), fail-closed for the types listed; the check runs on both write paths | The documents module must not import a business module; the check also refuses an unknown certificate |
| 10 | Numbers withheld without `EQUIPMENT_IDENTITY_READ` | The withdrawal reason is withheld with the number | As ERT-1 review round 2 (ERT1-R2-002): the Fleet Admin may repeat the number in it |
| 11 | - | A Plum part is not checked on its own: "A part is checked with the machine it is fitted to"; a piece of kit is | Section 6 judges a machine with its parts and kit alone |
| 12 | - | No certificate or mark is recorded on a retired asset | Nothing is allocated from it; its history stays |
| 13 | - | A write answers with the view of the asset the certificate is on; the page reads its own again when that is a fitted part | A carrier's certificate is withdrawn from its crane's page |
| 14 | Rules "may not overlap" | An overlap is `409`; ending a rule again on the same day changes nothing, on another day is `409` | The conventions of the Equipment Reference |
| 15 | Smoke data: "a crawler crane" and certificates on "the invented crane and carrier" | ERT-2's two cranes of `CC 100` are crawlers already: the second gets its road papers marked not applicable, the first is left for the tester and Playwright. A second wheeled crane (`AC 250`) with its carrier, paired when the first report is confirmed, carries the certificates - all but the load test - and a sling held for the crawlers carries its examinations | A crane with its carrier from the start; the first crane's carrier arrives only with the second report, for ERT-1's own flow. The harness's report upload gained the pairs to confirm |
| 16 | - | Certificates due lists fitness and permits as missing for a machine with no registration yet | The same cautious reading as the check (row 3): until the registration says non-transport, they may be needed |
| 17 | Jurisdictions "coded by ISO 3166-2:IN" | As revised in 2023: `IN-CG`, `IN-OD`, `IN-TS`, `IN-UK`; Dadra and Nagar Haveli and Daman and Diu as `IN-DH`, GST 26 | The current codes |
| 18 | The downgrade "removes it cleanly" | Removes the tables, the permission and `btree_gist`; copies stay in the documents table | The documents table is not this revision's; the revision below has no rights entry for them, so nobody can read them |
| 19 | A document type `CERTIFICATE` | One a user may choose on any record, as `OTHER`; the machine page offers only it | The documents module's type list is one list |
| 20 | - | A registration rule always applies: one "only for transport vehicles" is refused (`422`), and the database refuses it too | The registration decides whether the transport rules apply, so its own rule cannot depend on that answer (independent review, round 4) |
| 21 | Rules per jurisdiction, `IN` for central-government sites | A rule for the central government's sites is refused (`422`, and by the database) for any kind but the examinations; the form offers those sites only for an examination | Refinement 4: at those sites road papers follow the state, so such a rule would be recorded and never used (independent review, round 5) |
| 22 | Numbers withheld without `EQUIPMENT_IDENTITY_READ` | A "not applicable" mark's reason and withdrawal reason are withheld with them (`reason_withheld`), and the mark's events carry fixed reasons | As refinement 10: the reasons are the Fleet Admin's free text, which may repeat a certificate number (independent review, round 6). Those who see machines still see that a kind is marked, until when, by whom and under which rule |
| 23 | Refinement 3: a transport-only rule applies unless the registration is marked not applicable | Where the records disagree - a registration in force, and a mark saying none applies - the registration wins: the mark does not count while it is in force and not run out, today or on the day the job starts. A registration that has run out no longer decides the transport question either | The owner's decision, 28 September 2026 (independent review, round 7): the cautious reading. To rely on the mark, the registration must run out or be withdrawn, with its reason (for example surrendered to the RTO) |

### Tests and checks

Recorded in `docs/agent/acceptance/elg-1-machine-eligibility-acceptance.md` and the continuity note
`docs/continuity/ELG_1_MACHINE_ELIGIBILITY.md`, with the tree each was measured on.

### Independent review

the independent reviewer, bounded packets; the owner's cap is three rounds, and the owner approved a fourth on 27
September 2026, a fifth and a sixth the same day, and a seventh and an eighth on 28 September. Results are
recorded here round by round.

**Round 1** (packet `11e10868...`, tree `d19bb29`, commit `f884327`): `CORRECTION_REQUIRED`, two blocking and five
material findings. All seven corrected, each with a test that fails when the correction is undone:

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ELG1-R1-001 (blocking) | Any document linked to a certificate counted as its copy, whatever its type, and a link to a file kept elsewhere could be recorded as one | Only an uploaded document of type `CERTIFICATE`, not rejected or archived, counts. The attach check now receives the document type and storage mode, and a certificate refuses any other type and any link (`422`) - on the upload and the metadata routes alike |
| ELG1-R1-002 (blocking) | The machine's and its fitted parts' certificates of a kind formed one sequence, so a newer record on one hid a valid one on another; and transport was read only from the latest-starting registration | Each asset's certificates (and each permit place's) are their own sequence, and the one covering longest counts. A unit is judged as a transport vehicle when the registration in force on any of its assets says transport - today, or on the day the job starts, so a registration changed ahead of the job counts |
| ELG1-R1-003 | A request key replayed when any field but the asset and kind differed | Only an exact repeat - every field, normalized as stored - is answered with the first record; any other use of the key is `409`, for certificates, marks and rules |
| ELG1-R1-004 | `record_decision` read the evidence without the module's write lock | It takes the lock, held until the caller commits or rolls back |
| ELG1-R1-005 | A certificate's withdrawal reason, which may repeat its number, was the event's reason | The event carries a fixed reason; the Fleet Admin's stays on the certificate, withheld without `EQUIPMENT_IDENTITY_READ` |
| ELG1-R1-006 | The check's answer stayed under changed inputs, and an older check could replace a newer; Certificates due and Certificate rules reloaded after a session change with their first filters under the filters shown | Changing the check's inputs clears its answer, and only the latest check's answer is shown; both pages reload with the filters they show |
| ELG1-R1-007 | A kind already marked was offered again (the server refuses a second mark), and the rule form accepted intervals and limits the server refuses | A kind carrying a mark is not offered; the form holds the server's bounds (1 to 240 months, 1 to 120) |

**Round 2** (packet `4835f321...`, tree `36aeece`, commit `a92a919`): `CORRECTION_REQUIRED`, five material findings,
none blocking; the reviewer judged round 1's corrections right. All five corrected:

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ELG1-R2-001 | Attaching a copy was not serialized with withdrawing its certificate: the check could read "recorded" just before a withdrawal committed | The attach check takes the module's write lock, held until the documents module's transaction ends, then reads the certificate. A test holds the lock from each side in turn |
| ELG1-R2-002 | Certificates due and Certificate rules kept the previous rows under changed filters while a request was slow, and a rule saved just before the place filter changed reloaded the old place | Both pages load through one tested controller (`createQueryController`, the machines list's rule for one answer): a new request clears the old answer at once, only the latest answer is shown, and every reload - after a save or a session change - asks for what the controls show |
| ELG1-R2-003 | A certificate or mark saved on one machine's page could land on another machine's page opened before the answer came | The page's certificates load through the same controller, keyed to the asset; a save's answer that comes after the page moved on changes nothing, and the page reads its own asset again rather than install the save's view |
| ELG1-R2-004 | Certificate rules did not re-read who may manage rules after a session change | It does, and closes the add and end forms of someone who may no longer |
| ELG1-R2-005 | A mark still in force but no longer counted - ended, or not allowed by the rule chosen - could not be withdrawn from the screen, and could be missing from it | Every certificate and mark is shown once: those outside the status rows are listed under "Also recorded" with their Withdraw, why each is not counted (ended, starts later, replaced, not required), and what was withdrawn under "Earlier" |

The controller's rules - a new request clears the old answer; an older answer never replaces a newer; a save made
under another query reloads nothing - are tested with deferred answers (`certificatesState.test.ts`); the
components themselves have no test of their own, as the frontend suite tests pure modules and route tables.

**Round 3** (packet `67c2456a...`, tree `91cbb81`, commit `85a437f`): `CORRECTION_REQUIRED`, two blocking and two
material findings; the reviewer judged round 2's corrections right. All four corrected. Round 3 was the last within
the owner's cap of three.

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ELG1-R3-001 (blocking) | A "not applicable" mark had only to stand today: one ending before the job, or during it, still answered "can be allocated", and a registration's mark ending before the job still exempted the machine from the transport rules | A mark is held to the period as a certificate's cover is: ending before the job starts, during it, or with an open-ended job, it warns, and the result names the mark ("not applicable until ..., before the job starts - the certificate is needed after that"). A registration's mark exempts from the transport rules only if it still stands on the day the job starts; otherwise fitness and a permit are needed, the cautious reading |
| ELG1-R3-002 (blocking) | After a session change on the same machine page, numbers and copies loaded under Admin stayed on screen | The certificates section clears everything it shows on a session change - in this window or another - re-reads who may manage, and reads the asset again under the new session. A Playwright test signs in as a read-only user on the page and sees the number withheld and no button |
| ELG1-R3-003 | A certificate outside the status rows - a renewal starting later - could not have its copy attached once the page was left | Every recorded certificate listed under "Also recorded" shows whether its copy is attached and offers its copies (and "Attach its copy" to Admin); withdrawn ones offer their copies to read. Playwright records a renewal starting in 400 days, reloads, attaches its copy from there, and sees "copy attached" |
| ELG1-R3-004 | The harness cleanup's refusal checked only the asset a stored result is about, not the certificate or mark that met it, and its test used a shape the service does not store | The refusal also follows a result's certificate and mark to their asset. The test covers both shapes `record_decision` stores: a result about the run's part, and a result about an outside machine met by a certificate on the run's carrier |

**Round 4** (packet `18cdaa2c...`, tree `830aa28`, commit `3d9b5cd`), run on the owner's yes beyond the cap of
three: `CORRECTION_REQUIRED`, two material findings and one advisory, none blocking; the reviewer raised nothing
further on round 3's corrections. All three corrected. A fifth round needs the owner's yes.

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ELG1-R4-001 | Whether a unit is a transport vehicle read a registration's "not applicable" mark against the all-India registration rule, while the registration itself was judged by the rule for the site: a state's rule allowing the mark still brought in fitness and a permit, and a state's rule allowing none left them out | The transport question uses the registration rule the check judges the registration by - for the site's state, in effect on the day the job starts. A registration in force on the day the job starts counts as well as today's, so a non-transport one starting before the job asks for no fitness or permit (the registration is still missing today). A registration rule can no longer be "only for transport vehicles" (refinement 20), so choosing it never depends on the answer. Four tests: a state's rule allowing the mark, one allowing none, a rule ending before the job, a registration starting before it |
| ELG1-R4-002 | A site check's answer on the machine page stayed after the certificates changed - a certificate or mark withdrawn or recorded, a copy attached - and a check begun before such a change could show its answer after it | Every change made on the page, and every reading of the certificates again, takes the answer away before the new records are shown, and a check still on its way is not shown. Playwright checks the crane ("Can be allocated"), withdraws its load test, sees the answer gone before any new check, and checks again ("Cannot be allocated"). A change made elsewhere - another window, another page - shows on the next check: the answer is about the records when asked |
| ELG1-R4-003 (advisory) | The acceptance record still said 373 frontend tests | 377, with the tree it was measured on |

**Round 5** (packet `250edd17...`, tree `3be8a08`, commit `db3ba20`), run on the owner's yes:
`CORRECTION_REQUIRED`, one blocking, two material and one advisory finding; the reviewer raised nothing further
on round 4's corrections. All four corrected. A sixth round needs the owner's yes.

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ELG1-R5-001 (blocking) | The cover looked for a renewal only on the day after the current certificate ended. A renewal recorded ahead but starting before that day - which section 5 says takes over on its own start date - was ignored until then: one without its copy, or one ending sooner, left the machine "can be allocated" for a job its papers no longer covered, and Certificates due missed it | The cover follows the certificate in force day by day: at each later start date the renewal takes over (of two starting the same day, the one recorded last), and the cover runs through a takeover only when the renewal has its copy and covers its start date. Tests for a renewal without its copy, one ending sooner and one ending later - each through the cover, the site check and Certificates due - for two renewals on one day, and for a one-time road tax replaced by a periodic one; four fail on round 5's code, the fifth guards the chain |
| ELG1-R5-002 | Certificate rules still offered "only when registered as a transport vehicle" for a registration rule, which round 4 made the server refuse | The form offers it only for other certificates, sets a registration rule to "always", and names the refusal beside **Add rule** |
| ELG1-R5-003 | A rule for the central government's sites could be recorded for a road paper, though at those sites road papers follow the state's rule, so it would never be used | Refused by the service and the database (refinement 21); the form offers those sites only for an examination. Changing the certificate on the form now also drops what the new one cannot have - an interval on a kind that states its own end was kept hidden before and blocked **Add rule** |
| ELG1-R5-004 (advisory) | The continuity note counted nineteen refinements | Twenty-one, with refinement 21 above |

**Round 6** (packet `de1dd548...`, tree `55d65d7`, commit `56a0749`), run on the owner's yes:
`CORRECTION_REQUIRED`, one blocking and two material findings; the reviewer raised nothing further on round 5's
other corrections. All three corrected. A seventh round needs the owner's yes.

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ELG1-R6-001 (blocking) | Round 5's cover looked at only the first 100 later start dates, so a 101st renewal without its copy, or ending sooner, was never seen | Every takeover counts: the limit is gone, as the list is finite. A test records 101 daily renewals, the last without its copy, through the cover, the check and Certificates due |
| ELG1-R6-002 | A request key of only spaces passed the schema, then the database refused it: a mark's request failed with a server error, a rule's as a misleading overlap | Refused first, with a plain message, for certificates, marks and rules alike (`422`); a test sends one for each and finds nothing written - no row, no event |
| ELG1-R6-003 | A mark's reason and withdrawal reason - free text that may repeat a certificate number - reached every reader and the events | Withheld with the numbers (refinement 22), shown as "reason shown to Admin only"; the events carry fixed reasons. A test puts a number in both reasons and finds it in Admin's view only |

**Round 7** (packet `3df010f0...`, tree `738ba68`, commit `a9d0bf8`), run on the owner's yes:
`CORRECTION_REQUIRED`, two material findings, none blocking; the reviewer raised nothing further on round 6's
corrections. Both corrected; the second by the owner's decision. An eighth round needs the owner's yes.

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ELG1-R7-001 | A certificate valid until 31 December 9999 - accepted and stored - followed by any renewal made the cover add a day past the last date Python can hold: the save and every later read of the machine failed | The cover compares without adding to that date. Tests: the cover with a certificate valid to the last possible day, and through the routes a certificate valid to 9999 with a renewal taking over in five days - the machine's page, the check and Certificates due |
| ELG1-R7-002 | A registration in force saying transport and a "not applicable" mark on the registration together: the registration's row counted the mark, while the transport question counted the registration - one answer, two readings | The owner chose the cautious reading, 28 September 2026 (refinement 23): a registration in force and not run out wins, today or on the job's first day, so the mark does not count and the page lists it "not counted while a registration is in force". Once the registration runs out or is withdrawn, the mark counts. Five tests, each failing on round 7's code: a transport registration with the mark (the check, the machine's page, Certificates due), a non-transport one, one run out with the mark, one run out without it, and through the routes the registration withdrawn as surrendered |

**Round 8** (packet `01a2b2df...`, tree `ac53d28`, commit `555c377`), run on the owner's yes:
`CORRECTION_REQUIRED`, one material finding, none blocking; the reviewer raised nothing further on round 7's
corrections, the owner's decision included. Corrected. A ninth round needs the owner's yes.

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ELG1-R8-001 | Recording a "not applicable" mark, and the form's "no later than", took the first rule allowing one - all of India's where it allowed any, otherwise the first state's by code - so a state's rule letting it run longer (or without end) was never offered, and which state's limit applied depended on alphabetical order | The mark is recorded under the rule letting it run longest - no limit, else the longest; of equals, all of India's, then by code - so any mark some rule allows can be recorded; at each site it counts only where that site's own rule allows it, as before. Tests: the choice among limits in either order of state codes, no limit, equals, and a state allowing one where all of India allows none; through the routes, an 18-month mark refused under all of India's 12, recorded once a Gujarat rule allows 18, counted in Gujarat and not in Maharashtra. The form needs no change: it shows the limit and rule the server offers |
