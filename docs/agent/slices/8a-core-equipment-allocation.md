# 8A core - Own machines allocated to the resource requirements: design and implementation record

Status: **Design proposed and agreed, 28 September 2026.** The owner accepted Q2 and Q3 as recommended, and Q1
as recommended for now - hold before release - with a leaning recorded for 7B (section 1.0). Built on that
agreement.

Hiring lane (Track 2). Worktree `<a separate worktree>`, branch `hiring/8a-core-equipment-allocation`,
based on `main` at `d2f23f3`. Migration slot `20260908_0045`, parent `20260908_0044` - the single Alembic
head on `main`. No branch on `origin` holds a `0045` revision (checked 28 September 2026). Foundation Slice
Mode: the shape is built properly, the screens minimally. The frozen Slice 6D.1 handoff contract's SHA-256 is
`70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a` before this package.

This is **8A's core**, the part agreed for before the Hiring user test (`FUTURE_SLICES.md`, "8A - Equipment
Hiring Execution Shell", "8A core, before the test"; owner, 27 September 2026). Hired machines, vendors, gate
passes, general tools, crew, reminders, log sheets and billing are not in it (section 12).

In plain words:

- **Operations allocates PBL's own machines to what a Work Order line needs.** A resource requirement
  (WRR-001) asks for a number of machines of one kind over a period - "2 crawler cranes of at least 220 t,
  10 January to 31 March". Operations fills each of those places - each **unit** - with a machine.
- **Only a machine that fits is offered.** The machine must be of the kind asked for - its class, its type if
  one is named, and at least every capability stated - in the Equipment Reference's own terms (ADR-037). A
  machine whose type or rating is not known is not offered for a requirement that names them: unknown never
  counts as meeting a requirement.
- **A machine is never in two places at once.** A machine already allocated for any of the same days is shown
  as busy, with where it is, and cannot be chosen. If two people pick the same machine at the same moment, the
  first to save wins and the second is told to look again (`RPA-001`).
- **Eligibility decides whether the machine may work there.** For the site's state, whether it is a
  central-government site, and the dates, ELG-1 answers "can be allocated", "with a warning", "cannot be
  allocated" or "needs approval". The answer is stored with the allocation (`ELA-001`). A machine that
  cannot be allocated is never allocated.
- **Before the Work Order is released, an allocation holds the machine** (question 1): the machine is kept
  for this job and nobody else can take it for those days, but it is not yet committed. Release, which is not
  built yet (7B), will turn holds into firm allocations.
- **Nothing is lost.** Every allocation stays on the Work Order's history: which machine, for which unit, from
  when to when, and what became of it. A **replacement** - a breakdown, say - ends the old machine's days the
  day before the new one starts, and keeps both. A machine that is no longer needed is **freed**, with the
  reason.
- **Checked again before the job starts.** Each allocation shows today's eligibility answer beside the
  stored one, and **Check again** stores a fresh answer. A list shows the allocations starting in the next
  15 days.
- **Each machine's billing cycle, weekly or monthly,** is recorded with its allocation (FRS 2.8.1; the owner's
  answer 21 of Slice 7D Part 4). Invoicing (8G) will read it from there.
- **The kit going to site.** For each allocated crane, Operations lists the pieces of kit that go with it -
  boom sections, counterweight, hook blocks, lifting tackle - picked from the kit ERT-2 holds for the
  crane's model, trip by trip. A piece cannot be on two jobs at once, and each hook block and piece of tackle
  is checked for eligibility as the crane is.

**Reuse, not a second structure** (CODING_STANDARDS.md section 1, DRY first):

- **Machines and kit** are ERT-1's and ERT-2's `equipment_asset` records, read through the Equipment
  Reference's service. There is no second register.
- **What is needed** is WRR-001's requirement, read and updated only through its own service.
- **The eligibility answer** is ELG-1's `record_decision`, called in the allocation's own transaction, and
  its stored decision; ELG-1's `evaluate_asset` gives today's answer on every read.
- **The site** is the Work Order line's site (Slice 7C), read through the Work Orders service; its state is
  matched to one of ELG-1's jurisdictions.
- **Dates** are checked with the rules Slice 7D Part 3 built for reuse (`contract_period_rules.py`).
- **Events** go through `record_business_event`, codes, ids and dates only.

What is new is the allocation itself, its trips and the kit on them, and one answer on a Work Order line:
whether its site is a central-government site.

---

## 1. Questions for the owner

### 1.0 Answered by the owner (28 September 2026)

| # | Answer |
| --- | --- |
| Q1 | **Hold, as recommended, for now.** The owner asked whether, when every line of a Work Order can be released but one cannot - no machine can be allocated to it - the whole Work Order waits or only that line, and leans to **only that line**, to be refined later. And: "If the question is whether a committed machine should be disallowed from further allocation, I agree, yes it should be held. If the commitment is removed, it becomes free to allocation" |
| Q2 | **Accepted as recommended**: a warning allows the allocation once the user confirms having seen it; "needs approval" is refused until the approval step exists; "cannot be allocated" is always refused |
| Q3 | **Accepted as recommended**: one package, one migration (`20260908_0045`), one review |

**How Q1's question is answered here.** A hold belongs to one machine on one unit of one line's requirement,
never to the Work Order as a whole, so this package does not decide it. Whether release (7B) releases the
whole Work Order or a line at a time is 7B's design; either works on these holds - a line released alone
turns that line's holds firm and leaves the others held. The owner's leaning, line by line, and the release
check it implies - a line's required machines held before it is released - are recorded in `FUTURE_SLICES.md`,
7B, for that package. The second half of the answer is the design as it stands: a held machine cannot be
allocated elsewhere for those days, and once it is freed, or a replacement ends its days, it is free again
from the day after.

### 1.1 The questions as put (record)

#### Q1. Before the Work Order is released: hold the machine, or allocate it outright?

A Work Order cannot be released yet. Release needs the customer set up by Finance (7A) and the release
checks (7B), and neither is built. What the records say:

- `WRR-001` (approved): planning may start from an unreleased Work Order, but **committing** a machine needs
  release.
- The frozen handoff contract: an unreleased Work Order must not, by itself, allow assignment.
- `RPA-001` (approved): machines may be **held** (reserved) before they are finally assigned.

**Recommendation: hold.** Everything in this package works on a hold:

- Operations picks the machine, eligibility is checked, and the answer is stored.
- Nobody else can take the machine for those days.
- The requirement shows the unit as covered.
- Replacing, freeing, the billing cycle and the kit list all work.

The allocation reads **"Held for this Work Order"**. When release is built (7B), releasing the Work Order
checks each held machine's eligibility again and turns the hold into a firm allocation. Holds do not run out
for now: `RPA-001` allows a time limit on holds, and one can be set later if held machines sit idle.

**The alternative: allocate outright now.** This changes an approved rule. A machine could then be committed
to a customer before Finance has approved that customer, and before the Work Order is complete. For the
testers, only one word differs ("Held" or "Allocated"), and 7B would have no hold to confirm.

#### Q2. What happens when the answer is "with a warning" or "needs approval"?

The records settle most of this. **Recommendation:**

| Answer | What happens | Settled by |
| --- | --- | --- |
| Can be allocated | Allocated (held) | - |
| Can be allocated, with a warning | **Allowed.** The screen lists each warning - "insurance runs out on 5 October, before the job starts". The user ticks "I have seen these warnings", then allocates. The warnings stay on the allocation until they are dealt with, and ELG-2 will remind people about them | Your answer to ELG-1's Q4 |
| Needs approval | **Refused, with the reason, until the approval step exists** (`APR-001`). Today nobody can approve | `ELA-001`: an approval must come from the approval step, and the approver cannot be chosen by the person allocating |
| Cannot be allocated | Refused, with the reason. Nobody can override it | `ELA-001` |

**No rule today can give "needs approval".** Every rule loaded by ELG-1 blocks, and ELG-1's Q11 decided there
is no approvable rule for now. So this answer can arise only if Admin adds a rule that allows approval.

**The alternative for "needs approval":** let Admin accept it, with a reason, until the approval step exists.
Not recommended: the approver must be decided by the approval step (`ELA-001`, ADR-033), not by a role.

#### Q3. One package, or two?

This package is larger than ELG-1:

- allocating, eligibility, history, replacement, freeing, date changes and the billing cycle;
- the kit list, with its trips.

**Recommendation: one package, one migration (`20260908_0045`), one review.** The user test needs all of it.
The screen check takes about 25 minutes, in two sittings: allocating first, then the kit list.

**The alternative: two packages.** The kit list would come second, with its own migration and screen check.
That means two review cycles, so it is slower overall.

### 1.2 Already settled, not asked again

Each point follows from a record. It is stated so the owner can object, not asked again (ADR-023).

| Point | Settled by |
| --- | --- |
| Hired machines, vendors, the own/hired flag, the vendor placeholder and the Purchase Order gate wait | Owner, 27 September 2026 (`FUTURE_SLICES.md`, "8A core"); `D-03`, `D-04` open; `MHA-001` `PROPOSED` |
| Gate passes, general tools and crew wait | The same; general tools wait for the inventory integration (owner, 25 September 2026); crew is 8B |
| Reminders and escalation are ELG-2, after this package | Owner, 27 September 2026 (ELG-1 Q14) |
| Operations and Admin allocate; every role that reads Work Orders sees allocations | As for requirements (WRR-001, Q6) |
| The billing cycle is set by whoever may change a line's billing terms - Admin, Sales, Sales Manager, Operations - and may be left "not stated yet" until release, which will refuse it missing | 7D: "who may change a line's rates should be one answer, not two"; 7C decision 5: missing details block at release, not before |
| The cycle is weekly or monthly, and belongs to the machine's allocation, not the line | FRS 2.8.1; the owner's answer 21 of Slice 7D Part 4 |
| Whether the site is a central-government site is recorded with the Work Order line's site | ELG-1 Q8: "8A records it on the Work Order line's site", which stood as recommended |
| It must be answered before a machine is allocated to the line | The conservative principle: which rules apply depends on it, and unknown never counts as exempt |
| The site's state comes from the site address on the Account; a state name the platform does not recognise is refused, asking for the address to be corrected | ELG-1: "take the site's state from the Work Order line's site"; one fact, one owner (ADR-037) |
| A machine is offered only when it is known to meet the requirement: a machine whose type or rating is unknown is not offered where the requirement names them. The page says how many were left out for that, so the Fleet Admin can map their models | ADR-037; the conservative principle - unknown is never taken as meeting a safety-relevant requirement |
| Cancelling a requirement frees the machines held for it, keeping their history | `WRR-001`: "Cancellation ... releases uncommitted reservations" |
| Changing a requirement is never blocked by its allocations; an allocation that no longer fits shows a warning | WRR-001, Q8: a contract change is not blocked by a requirement, which shows a warning instead - the same rule one level down |
| The kit is picked from the kit held for the machine's model, per trip; it is never put in the machine's parts tree | Owner, 24 and 26 September 2026 (ERT-2, Q6; `DEFERRED_REQUIREMENTS.md`, "Asset component hierarchy") |
| Each piece of kit going to site is checked for eligibility on its own | ELG-1 section 6: "8A asks about each piece it puts on a trip" |
| A retired machine cannot be allocated; one retired while allocated is shown as an exception needing replacement or freeing | `RMR-001` |

---

## 2. What the sources say

The FRS is directional guidance under ADR-013. Each requirement below is read against the later decisions
that refine it.

| Source | What it asks | In this package |
| --- | --- | --- |
| FRS 2.5.5 "Equipment Transshipment" | On replacement, stop the old unit's log sheets and start the new unit's, preserving the audit trail | **Replacement** ends the old machine's days the day before the new one starts; both stay on the history, linked. Log sheets (8C) will follow the allocations |
| FRS 2.6.1 "Equipment Assignment History" | A complete history of every asset assigned to a Work Order, with registration, HSN and asset value | **The Work Order's allocation history**: every allocation, whatever became of it, with the machine's registration (as held when allocated, and now), class, type, model, periods, and how each ended. **HSN and asset value are not held anywhere yet** (section 12) |
| FRS 2.8.1 "Draft Invoice Generation" | Invoices follow the billing frequency (weekly or monthly) | The **billing cycle** on each allocation (owner's answer 21) |
| FRS 3.1 "Parent-Child Asset Relationship"; Annexure-11 | Major assemblies and returnable tools tracked with the machine, including during mobilisation | The **kit list** per trip, from ERT-2's kit. General tools wait for inventory |
| FRS "Mobilization Integration" | A mobilisation transport order on Work Order posting | Posting is 7B. Nothing here raises a transport order |
| FRS Controls, "Asset Documentation Warning" | Warn when a certificate is within 15 days of expiry | ELG-1's warning, shown and kept on the allocation |
| BOCW rules, where they continue | A load test after erection on a construction site | At dispatch, after release; not in the core (section 12) |

---

## 3. Authority and required reading

Read in full unless a section is named, per PBL's internal working instructions "Reading discipline".

- **Backlog and deferred requirements:**
  - `FUTURE_SLICES.md`: "8A - Equipment Hiring Execution Shell" with its two parts; "Eligibility foundation
    (before 8B)"; "ELG-2"; "Hiring user test"; "7B"; "8B"; "8C".
  - `DEFERRED_REQUIREMENTS.md`: "Resource requirements and the Equipment Reference"; "Plum's machines: what
    ERT-1 left out"; "Equipment Hiring execution"; "Asset component hierarchy"; "Equipment documents";
    "Detachable kit: what ERT-2 left out"; "Fixed Assets"; "Statutory requirements found with ERT-2".
- **Contracts:**
  - `resource-planning-assignment-contract.md` (`RPA-001`, APPROVED): the contract this package implements.
  - `work-order-resource-requirement-contract.md` (`WRR-001`, APPROVED) and its implementation
    `resource-requirement-api-contract.md`.
  - `eligibility-assignment-contract.md` (`ELA-001`, APPROVED) and its implementation
    `eligibility-api-contract.md`.
  - `resource-master-reference-contract.md` (`RMR-001`, APPROVED), with its ADR-032 and ADR-037 notes.
  - `work-order-billing-terms-contract.md` (`WBT-001`, APPROVED).
  - `equipment-reference-api-contract.md`: machines, models, kit.
  - `work-order-contract.md`: Slices 7C, 7D Part 3 and Part 4 sections, and the status section.
  - `accepted-offer-to-work-order-handoff-contract.md` (FROZEN): hash checked before and after.
  - `market-hire-assignment-contract.md` (`MHA-001`, PROPOSED): read only to keep hired machines out.
- **Decisions:** ADR-017 (module-owned data), ADR-018 (Requirement, Availability and Assignment as one shared
  capability), ADR-023 (settled defaults), ADR-033 (authority is configuration, never a role check in
  approval code), ADR-037 (the Equipment Reference) with its refinement of 25 September 2026; ADR-013 for the
  source guidance.
- **Designs this one builds on**, in full: `elg-1-machine-eligibility.md` (sections 5 and 6, "What 8A does
  with it", 13, 19 and 20); `wrr-001-resource-requirement-foundation.md`; `ert-2-detachable-kit.md` (sections
  1, 5, 12 and 18); `slice-7c-work-order-line-operational-detail.md` (the line's site); and
  `slice-7d-part-4-remaining-billing-terms.md` (answer 21).
- **Architecture:** `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`, the Resource Requirement, Availability,
  Assignment, Equipment Reference and Compliance / Eligibility rows; `CONTRACT_REGISTRY.md`.
- **Source:** the FRS extract (`ERP_FUNCTIONAL_SPEC_FULL_TEXT_EXTRACT.md`), "Site Execution & Log Sheet
  Management" (2.5.5), "Fleet & Crew Operations" (2.6.1), "Compliance & Logistics Control" and "Invoicing &
  Financial Governance" (2.8.1), 3.1; treated as directional (ADR-013).
- **Code:** `resource_requirements/service.py` in full; `eligibility/service.py` (`evaluate_asset`,
  `record_decision`, the write lock); `equipment_reference/service.py`, `ports.py`, `plum_source.py`;
  `work_orders/service.py`; `documents/service.py` (`register_attach_check`, the pattern for a registered
  reaction); `authorization/contract.py`; the jurisdictions of migration `0044`; the frontend's
  resource-requirement and equipment pages and their state modules.
- **The owner's standing rules:** the platform's own canonical structures (ADR-037); the conservative principle for
  law; DRY, then KISS, YAGNI and SOLID; time over polish.

---

## 4. What it builds

1. **The central-government answer** on a Work Order line's site: Yes or No, beside the site (Slice 7C's line
   details).
2. **Finding machines** for a unit of a requirement over a period: the machines that fit, free or busy, each
   with today's eligibility answer for the site.
3. **Allocating** a machine to a unit, held for the Work Order, on a stored eligibility decision.
4. **The requirement's fulfilment**: each unit covered or not, "remaining" = units not yet covered, and the
   statuses `PARTLY_FULFILLED` and `FULFILLED`.
5. **Replacing** a machine from a date, **freeing** it with a reason, and **changing** an allocation's dates.
6. **Checking again**: today's answer on every read, and a stored fresh decision on request; a list of the
   allocations starting soon.
7. **The billing cycle** of each allocation: weekly, monthly or not stated yet.
8. **The kit list**: trips, and the pieces on each, from the kit held for the machine's model, each piece
   checked.
9. **The history**: every allocation of a Work Order, and every allocation of a machine.

---

## 5. The records

```text
Allocation         one machine on one unit of one requirement, for a period; held; how it       NEW
                   ended (replaced or freed); its billing cycle; its eligibility decision
Trip               a delivery to site within an allocation: trip 1 goes with the machine          NEW
Kit line           one piece (or a count from a counted set) on a trip, with its decision         NEW
Central-government a Yes/No answer beside a Work Order line's site                                NEW column
Requirement        gains two statuses in use (PARTLY_FULFILLED, FULFILLED)                        changed
Machine, kit       ERT-1's and ERT-2's assets, models and kit fits                                unchanged
Decision           ELG-1's eligibility decision, stored by record_decision                        unchanged
```

### 5.1 Why the existing records do not carry an allocation

| Existing record | Why it cannot hold an allocation |
| --- | --- |
| `resource_requirement` | It is the demand: how many, what kind, when. An allocation is one machine filling one unit of it for a period; a unit may be filled by several machines over time (a replacement), each with its own history |
| `equipment_asset`, its links | The machine's own facts and fitted parts. Where it is working belongs to Assignment (`RMR-001`: "Availability, maintenance restrictions and assignment state remain outside Equipment Master") |
| `eligibility_decision` | The answer about a machine at a site for a period. It says whether the machine may work, not that it was chosen (`ELA-001`: Assignment owns the commitment) |
| `crm_work_order_line_detail` | The line's own facts. A line may need several machines, over time |

### 5.2 Where the records live

**A new module, `backend/app/modules/resource_assignments/`** - the **Resource Availability** and **Resource
Assignment** rows of `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`, in one module as ADR-018 allows ("Availability and
assignment remain distinct concepts even if implemented in one module initially"). A hold is the
reservation; 7B's firm allocation is the commitment; one record carries both, as `RPA-001` asks ("creates an
assignment public ID/version and reservation/commitment atomically").

- It reads the requirement through `resource_requirements.service`, machines and kit through
  `equipment_reference.service`, the answer through `eligibility.service`, and the site through the
  requirement's live line facts (which the requirements module reads from `work_orders.service`). It writes
  none of their tables.
- **Names.** The code and contracts say *assignment*, `RPA-001`'s word; the screens say **allocation**, the
  word ELG-1's answers already use ("can be allocated"), as `Account` is shown for `business_party`. The
  reference is `AL-000001`.
- **Crew** (8B) joins the same module with its own table.

**How the requirement learns of its allocations** (ADR-017: a module never reads another's tables). The
requirements module does not import this one. It declares a small interface, `AssignmentPort`, which this
module registers when it is loaded - the pattern the documents module already uses for ELG-1
(`register_attach_check`):

- `coverage(requirement)`: which units are covered, in full or in part - a read;
- `release_for_cancelled_requirement(requirement)`: frees the held machines when the requirement is
  cancelled, inside the cancellation's own transaction. This is Assignment reacting to the requirement's
  published "cancelled" fact, which `WRR-001` names, done in process because no event bus exists.

If the port is not registered when a requirement is cancelled or changed, the requirements service refuses
rather than guess (fail closed). The application always registers it: `app.main` loads the module.

**The central-government answer lives with the line's site**, on `crm_work_order_line_detail`, written only by
the Work Orders module through its line-detail route (Slice 7C), as ELG-1 Q8 settled.

### 5.3 The records in detail

**Allocation** (`resource_assignment`):

```text
assignment public id, reference AL-000001 (generated from the id)
requirement public id, unit number          which place of which requirement it fills (1 .. units required)
Work Order public id, line public id,       copied once from the requirement; never change
source offer line public id
machine public id                           an active machine (never a part or kit)
as allocated: the machine's registration,   the snapshot RMR-001 asks for: history shows what was
class, type, model and version              allocated, even if the machine is later renumbered or re-rated
units fulfilled                             1: a unit is one machine in Hiring (CHECK = 1, as WRR-001 pins
                                            one item per requirement)
planned from, planned to                    to may be empty only where nothing bounds the requirement
ended on                                    set when replaced or freed: the last day on the job, or the day
                                            before its start when it never started
status                                      HELD; REPLACED; RELEASED ("Freed" on screen)
                                            reserved, not accepted yet: ALLOCATED (7B), COMPLETED (8E)
replaces                                    the allocation this one replaced, if any (at most one replacer)
end reason code, note, ended by, ended at   exactly when REPLACED or RELEASED
billing cycle                               WEEKLY, MONTHLY, or empty (not stated yet); set by and at
decision public id                          the latest eligibility decision stored for it (ELA-001)
notes                                       up to 2000; never read by a rule
version, request key, created and updated by and at
```

- **Busy days.** An allocation keeps a machine busy from `planned from` to the earlier of `planned to` and
  `ended on`, both days included; open-ended when neither is set; none at all when it ended before it
  started. This is a stored, generated range.
- **Never two at once.** The database refuses two allocations of one machine whose busy days overlap, and
  two allocations of one unit whose busy days overlap (exclusion constraints, `btree_gist`, which ELG-1
  installed). Days an allocation actually held stay in the history, so a machine can never be recorded on
  two jobs on one day, even in the past. Once an allocation's first day has come (on or before today, India
  date), only freeing it as recorded by mistake may take all its days away (owner, 1 October 2026; 6.6, 6.7).
- **Never edited, only moved on.** An allocation changes only by the actions of section 6, each recorded as an
  event. Its decision is replaced by a newer one on each check; every decision stays in Eligibility, naming
  the allocation it was for (`requested_for`).

**Trip** (`resource_assignment_trip`): the allocation, the trip number (1, 2, ...), the day it goes (empty for
trip 1, which goes with the machine on its first day), a note (up to 500), who added it and when.

**Kit line** (`resource_assignment_kit`):

```text
kit line public id
allocation, trip
piece public id                a piece of kit, or a counted set (ERT-2)
as listed: its kit model and how it is tracked (one by one, or counted)
quantity                       1 for a piece tracked one by one; for a counted set, how many of it go
status                         LISTED; REMOVED (taken off the list before it went: who and when)
decision public id             the piece's own eligibility decision
busy from, busy to             the trip's day to the allocation's end; kept in step with the allocation
request key and position, created by and at
```

- A piece tracked one by one is never on two listed lines whose busy days overlap: the database refuses it
  (exclusion constraint), as for machines.
- For a counted set, the pieces listed on lines overlapping any day never exceed the set's quantity: the
  service checks it under the module's write lock.

**Central-government answer**: `crm_work_order_line_detail.site_central_government`, a nullable boolean. Empty
means not answered.

### 5.4 Authority by phase

| Fact | Phase 1 (now) | Changed by |
| --- | --- | --- |
| Which machine fills which unit, when, and what became of it | **The platform** (`RPA-001`) | Operations |
| Whether a machine may work at a site over a period | **Eligibility** (`ELA-001`) | nobody: it is computed |
| The site, and its state | the Work Order line's site, an Account address (7C) | Sales, Operations |
| Whether the site is a central-government site | the Work Order line's details (this package) | the roles that record line details |
| The billing cycle of each allocated machine | **The platform** (answer 21) | the roles that change billing terms |
| Which kit went with which machine, per trip | **The platform** (owner, 24 September 2026) | Operations |
| The machine's own facts and status | Plum through the transformer, as corrected (ADR-037) | the Fleet Admin |

### 5.5 Room for change

| What may vary | How the design takes it | Cost if it comes later |
| --- | --- | --- |
| Release (7B) turns holds into firm allocations | `ALLOCATED` is reserved in the status list; release calls this module with a fresh eligibility check | Small: a status and one action |
| Hired machines (`MHA-001`) | The allocation names a machine by its public id; a hired machine would name a secured external resource instead | Moderate: an origin column and the vendor records |
| A time limit on holds (`RPA-001`) | Holds do not expire now | Small: a setting and a list filter |
| Crew (8B) | The same module, its own table, against each allocation | Small |
| Log sheets (8C) | One per active allocation per day; a replacement already ends one and starts the other | None here |
| Kit coming back (8E) | Each kit line keeps its piece and trip | Small: a return date per line |
| Transportation's combinations (a prime mover and a bed) | `units fulfilled` is a column, pinned to 1 | Small: lift the pin |
| Which pieces a crane configuration needs (boom foot and head on every job) | Pieces are picked by hand | Moderate: a configuration record per model |

---

## 6. The rules, step by step

### 6.1 The site

The site is the requirement's line's site (7C), read live every time. Three facts are needed, and each
missing one refuses an allocation with a message naming the line:

1. **A site is recorded** on the line. "Record the site on line 2's details first."
2. **Its state is recognised.** The site address's state (free text on the Account) is matched to one of
   ELG-1's 36 states and union territories, by its name or code, ignoring case and spaces ("Gujarat", "gujarat",
   "GJ", "IN-GJ"). "The site's state 'Guj.' is not a state name the platform knows. Correct the site address on
   the Account." A new read in the Eligibility service does the matching, beside the jurisdictions it owns.
3. **The central-government question is answered** on the line. "Say on line 2's details whether its site is a
   central-government site: a central public sector plant, a railway or metro, a major port, an oil field or a
   mine, including work there as a contractor."

Afterwards the line's site may still change (until mobilisation, 7C decision 3). An allocation whose stored
decision was for another state or answer shows `SITE_CHANGED`, and **Check again** answers for the site as it
now is.

### 6.2 Finding machines

For a unit of a requirement and a period (by default, the unit's first days not yet covered, to the
requirement's end):

1. **Candidates** are the active machines (not parts, not kit) of the requirement's class.
2. **The type.** Where the requirement names one, the machine's type must be it. A machine with no type - its
   model not mapped - is left out, and counted.
3. **The capabilities.** Each stated capability must be met by the machine's own value, else its model's (ERT-1):
   a least value by a value at least as large; a choice by the same choice. A machine with no value for a
   stated capability is left out, and counted.
4. **Free or busy.** A machine allocated for any day of the period is busy. Busy machines are listed after the
   free ones, not selectable, each with where it is: the allocation, the Work Order and the dates.
5. **Today's answer.** Each free machine is checked for the site and period (`evaluate_asset`; nothing is
   stored). A machine that cannot be allocated, or needs approval, is listed with its reason and cannot be
   chosen.
6. **The order**, advisory only (`RPA-001`): can be allocated, then with a warning, then the rest; within each,
   the smallest key capability first, so a bigger machine is not taken when a smaller one will do; then the
   registration.
7. **Left out.** The page says how many machines of the class were left out, and why: type not known, rating
   not known, below what is asked. The Fleet Admin can then map their models.

Data-quality flags on a machine (ERT-1) are shown beside it and do not stop it.

### 6.3 Allocating

A request names the requirement, the unit, the machine, the dates, and optionally the billing cycle and a note;
`accept_warnings` says the user ticked "I have seen these warnings". In one transaction, in this order (section
6.12):

1. The requirement is locked and read: it must not be cancelled; the unit must be between 1 and its units
   required; the Work Order must not be closed.
2. **The dates.** `planned from` on or after the requirement's start; `planned to` on or after `planned from`,
   and not after the requirement's end. The requirement's end is its own, else its line's end, else the
   contract's fixed end; `planned to` may be empty only when none of these exists. Dates in the past are
   allowed, so machines already on site can be recorded; eligibility is still judged today.
3. **The site** (6.1).
4. **The machine** must still fit (6.2, steps 1 to 3) and be free for every day (6.2, step 4): otherwise
   `409` "EQ-000123 is held for WO-000045 from 1 March. Choose another machine." The database's exclusion
   constraint is the backstop, turned into the same message.
5. **The unit** must be free for every day of the period: another allocation on the same unit may cover other
   days (a planned hand-over), never the same ones.
6. **Eligibility.** `record_decision` for the machine with its fitted parts, the site's state and
   central-government answer, and the period, `requested_for` this allocation (its public id is chosen before
   the row is written):
   - `BLOCKED` or `OVERRIDE_REQUIRED`: refused (`422`), naming each reason; nothing is stored.
   - `WARNING` without `accept_warnings`: refused (`409`) with the warnings, so the screen can show them;
     nothing is stored.
   - Otherwise the decision is kept.
7. **The billing cycle**, when given, needs `WORK_ORDER_LINE_BILLING_TERMS_WRITE` as well (`403` otherwise).
8. The allocation is written `HELD`, with trip 1; the requirement's fulfilment is refreshed (6.5); the events
   are recorded; one commit.

The same request key again returns the first allocation with `replayed: true` and no event, when every field
is the same; the key used for anything else is `409` (ADR-023, as ELG-1).

### 6.4 Eligibility after allocation

- **Today's answer on every read.** Every held allocation, and each listed piece of its kit, is checked with
  `evaluate_asset` for the site as it now is and the allocation's period. Nothing is stored. The allocation
  shows it beside the stored decision, and its **compliance state** is the worst of them:
  - `CLEAR` - can be allocated;
  - `WARNING` - with the warnings;
  - `BLOCKED` - cannot be allocated today, or needs approval: "Renew the certificate, or replace or free the
    machine" (`RPA-001`: an explicit release or replacement path);
  - `SITE_UNKNOWN` - the site's facts are missing now (6.1).

  Until a job runner exists, this is how a lapsed certificate reaches an allocation (`ELA-001`'s
  `EligibilityLapsed`, worked out when read; ELG-1 section 13).
- **Check again** stores a fresh decision for the machine and for every listed piece, for the site as it now
  is, and makes them the allocation's. A `BLOCKED` answer is stored too: the allocation stays held, shows
  that it cannot be allocated, and waits for renewal, replacement or freeing. It is never freed
  automatically.
- **Starting soon.** The allocations list filters held allocations by their start; its preset is "starting in
  the next 15 days", each row with today's answer. This is the check before the planned start. When dispatch
  exists (after release), it will require a fresh stored decision.
- A history allocation (replaced or freed) is not checked: its stored decision stands as the record.

### 6.5 Units, coverage and the requirement's status

- A **unit is covered** when the busy days of its held allocations together cover every day of the
  requirement's period, from its start to its end (as in 6.3, step 2); an open-ended requirement needs an
  open-ended allocation at the end of the chain. A unit with some of those days is **partly covered**.
- The requirement's **status**, recomputed by the requirements service whenever it or its allocations change,
  through the port:
  - `OPEN` - no held allocation on any of its units;
  - `PARTLY_FULFILLED` ("Partly allocated") - some;
  - `FULFILLED` ("Allocated") - every unit covered;
  - `CANCELLED` - as now.

  `COMPLETED` stays reserved: nothing in the core ends a job (8E).
- **Remaining** is units required less units covered, shown on the requirement and the planning list
  (`RPA-001`: "the remaining quantity stays visible").
- A status change records `ResourceRequirementFulfilmentChanged` on the requirement, and moves its version on,
  so a change form opened before it is refused as stale (`409`) and reread.
- **Changing a requirement** is never refused because of its allocations. An allocation that no longer fits
  shows a warning: `OUTSIDE_REQUIREMENT` (its dates), `NO_LONGER_MATCHES` (the kind of machine or a
  capability), `UNIT_NOT_REQUIRED` (its unit is above the units now required). Its unit then counts for
  nothing until it is freed or its dates changed.
- **Cancelling a requirement** frees every machine held for it, in the same transaction: each allocation is
  `RELEASED` with the reason "requirement cancelled", ending the day before its start, or today if it has
  started; its kit is cut with it. The cancel form says first how many machines will be freed.

### 6.6 Replacing a machine

For a held allocation, a request names the new machine, the first day it replaces the old one, optionally a
new end (by default the old one's), the reason - `BREAKDOWN`, `COMPLIANCE`, `CUSTOMER_REQUEST`, `PLANNING` or
`OTHER` with a note - and `accept_warnings`.

- The first day must fall within the old allocation's days. A replacement from the old one's first day (before
  it started) leaves the old one with no days. Once the old one's first day has come (on or before today, India
  date), the replacement must start after it, so the old one keeps the days it held; one recorded by mistake is
  freed as `RECORDED_BY_MISTAKE` and allocated again instead (owner, 1 October 2026). The finder's default first
  day for a started allocation is today - or its last day if that has passed while it is still held - and never
  earlier than the day after its first day.
- Finding the new machine uses the finder of 6.2 for the replacement's days, told which allocation is being
  replaced, so that allocation's own days from the first day replaced do not count as taking the unit.
- The old allocation becomes `REPLACED`, ending the day before; its kit lines end with it.
- The new allocation is checked exactly as a new one (6.3), on the same unit, with `replaces` pointing at the
  old. It takes the old one's billing cycle unless another is given.
- Both are written in one transaction, each with its event, so the history reads: "EQ-000123, 10 January to
  3 February, replaced (breakdown) by EQ-000456 from 4 February".
- A replaced allocation cannot be replaced again, and at most one allocation replaces it.

The kit on site is not carried over automatically: the new machine's list is made as for any allocation, and
the pieces the old one had are free from its end. A "carry the kit over" button is left for later (section 12).

### 6.7 Freeing a machine

For a held allocation: the last day it is on the job - empty when it never goes - and the reason:
`NOT_NEEDED`, `RECORDED_BY_MISTAKE`, `MACHINE_UNAVAILABLE` or `OTHER` with a note. The allocation becomes
`RELEASED`; its kit lines end with it; the requirement's status is refreshed. The last day must be within its
days. Once its first day has come (on or before today, India date - the test the requirement's cancellation
already uses, 6.5), the last day is needed unless the reason is `RECORDED_BY_MISTAKE`: only a machine recorded by
mistake may lose the days it held (owner, 1 October 2026). Before the first day, nothing changes. A fifth reason, `REQUIREMENT_CANCELLED`, is set only by a requirement's cancellation (6.5), never
chosen.

### 6.8 Changing an allocation's dates

For a held allocation: new dates, checked as in 6.3 (steps 1 to 6), against every other allocation of the
machine and of the unit, and its kit's pieces against theirs. A later trip must still fall within the new
dates, or the change is refused naming the trip. A fresh decision is stored for the machine and every listed
piece. This is how a machine follows a contract extension (`RPA-001`: a blocked allocation cannot be
extended, and a blocked decision refuses the change). Once the allocation's first day has come, that day stays
and only the last day can change, as 6.6 and 6.7 keep the days it held (owner, 1 October 2026; added 4 October
2026 after TB-1 found the date change did not, `docs/continuity/SLICE_8A_KEEP_HELD_DAYS.md`).

### 6.9 The billing cycle

`WEEKLY`, `MONTHLY`, or empty ("not stated yet"). Set when allocating, or later on the allocation page, by the
roles that change billing terms (`WORK_ORDER_LINE_BILLING_TERMS_WRITE`); each change records an event with
before and after. An allocation without one shows `BILLING_CYCLE_NOT_STATED`; release (7B) will refuse it.
The cycle is not dated: invoicing (8G) adds a date from which a change applies, if it needs one.

### 6.10 The kit going to site

- **What is offered.** The pieces of the kit models that fit the allocated machine's model (ERT-2's fits), not
  retired. A machine with no model has no kit: "Map this machine's model to see its kit." Each piece shows
  whether it is free over the trip's days, where it is if not, and today's answer. A counted set shows how many
  of it are free over those days.
- **Trips.** Trip 1 goes with the machine, on the allocation's first day, and follows it when its dates change.
  A later trip has its own day, within the allocation's days, and an optional note.
- **Listing pieces** on a trip, several at once: each must fit the machine's model, be active, and be free
  over its busy days - the trip's day to the allocation's end - and a counted set's count must be free
  (6.3's refusals, per piece). Each is checked with `record_decision` for the site and those days: blocked or
  needs approval refuses (naming the piece); a warning needs `accept_warnings`. The lines, their decisions and
  one event are written together.
- **Removing** a piece from the list keeps the line, `REMOVED`, with who and when; the piece is free again.
- **Kept in step.** When the allocation's end moves - dates changed, replaced, freed - every listed line's busy
  days move with it, in the same transaction.
- **No return yet.** A piece stays with its allocation until the allocation ends. Checking kit back at the
  yard is 8E.
- A line whose piece no longer fits the machine's model (the model re-mapped) shows `KIT_DOES_NOT_FIT`.

### 6.11 A closed Work Order, and history

- A closed Work Order refuses every write on its allocations, as it does for 7C, 7D and requirements.
- Nothing is deleted. A replaced or freed allocation stays readable on the Work Order, the requirement and the
  machine.

### 6.12 Locks, and their order

Locks are always taken in one order: the requirement's row lock (`SELECT ... FOR UPDATE`, through the
requirements service); then this module's one write lock (a transaction advisory lock, as the Equipment
Reference and Eligibility take theirs); then Eligibility's, which `record_decision` takes.

- A write that can change a requirement's coverage - allocating, replacing, freeing, changing dates - starts
  with the requirement's row lock, then re-reads its allocation under this module's lock.
- A write that cannot - checking again, the billing cycle, trips and kit - starts at this module's lock.
- A requirement change or cancellation takes its row lock, then, through the port, this module's lock.

Because every path keeps that order, no two writes can wait on each other. Writes are few and made by a few
people, so they are simply serialized.

### 6.13 Warnings on an allocation

Computed on every read of a held allocation; advisory only.

```text
SITE_CHANGED                the site's state or central-government answer differs from the stored decision's
OUTSIDE_REQUIREMENT         its dates are no longer inside the requirement's
NO_LONGER_MATCHES           the machine no longer meets the requirement's class, type or a capability
UNIT_NOT_REQUIRED           its unit is above the units now required
OUTSIDE_CONTRACT            a day of it is outside the contract or in a gap (Slice 7D Part 3's rule)
BILLING_CYCLE_NOT_STATED    no billing cycle yet
KIT_DOES_NOT_FIT            a listed piece no longer fits the machine's model
ANSWER_CHANGED              today's answer differs from the stored decision's: check again
```

---

## 7. Screens

Messages sit beside the button that caused them. Styling uses `globals.css` classes only; every date box is
`DateInput`; a page with no session says `SIGN_IN_FIRST`, a refused one `SIGN_IN_AGAIN`. Each page's loading
goes through a tested pure controller in which only the latest answer is shown and a new request clears the
old one - the rules WRR-001's and ELG-1's reviews asked for, reused rather than rewritten
(`createLatestOnly`, `createQueryController`).

1. **Line details** (Work Order page, 7C): **Central-government site?** Yes / No / Not answered, under the
   site, with the hint "a central public sector plant, a railway or metro, a major port, an oil field or a mine,
   including work there as a contractor".
2. **The requirement page** gains **Machines**: one row per unit - its allocations over time (machine, dates,
   status, today's answer, billing cycle), "2 of 3 units covered", and **Allocate a machine** on a unit not
   covered, for those who may.
3. **Allocate a machine** (`/resource-assignments/new?requirement=...&unit=...`): the requirement and the site
   (or what is missing about it); the dates; **Find machines**; the machines found, free first, each with its
   answer and reasons; the machines left out, counted by reason; choosing one shows its full answer; the
   billing cycle (to those who may set it) and a note; **Allocate**, or, on a warning, the tick box "I have seen
   these warnings" and **Allocate with these warnings**.
4. **The allocation page** (`/resource-assignments/:id`): what it is for (Work Order, line, requirement, unit),
   the machine, the site, the dates, the status and history (replaces, replaced by, how it ended); the stored
   answer and today's, with **Check again**; the warnings; the billing cycle, with **Change**; **The kit going
   to site**: each trip with its pieces, **Add pieces** (a picker per trip), **Remove**, **Add a trip**; and the
   actions **Change the dates**, **Replace the machine** (the same finder as 3) and **Free the machine** (last
   day, reason).
5. **The Work Order page** gains **Machines allocated**, in the Jump-to row: every allocation of the Work Order,
   by line and requirement, held ones first, replaced and freed ones kept and marked - FRS 2.6.1's history.
6. **The machine page** gains **Allocations**: where the machine is held, and where it was.
7. **Allocations** (`/resource-assignments`), in the sidebar: filters by status and start dates, with the
   preset "Starting in the next 15 days"; each row with today's answer.
8. **The planning list** shows each requirement's status and remaining units; its default filter becomes
   "Needs machines" (open and partly allocated).

**A screen check fits in about 25 minutes, in two sittings,** on a seeded Work Order with a crane requirement
of two units, cranes with their certificates (one with insurance running out in ten days, one with a lapsed
fitness), a crawler, and kit for the cranes' model:

*Sitting 1 - allocating (15 minutes)*

1. On the Work Order's line details, answer "Central-government site?" No.
2. Open the requirement; unit 1: **Allocate a machine**. See the machines found, the lapsed crane unselectable
   with its reason, and the machines left out.
3. Choose the crane whose insurance runs out: the warning; allocate only after ticking it. "Held for this
   Work Order"; the requirement "Partly allocated", 1 remaining.
4. Allocate unit 2; the requirement "Allocated". Try the same crane for unit 2's dates: shown busy.
5. On unit 1's allocation, set the billing cycle to Monthly.
6. Replace unit 1's machine from a date (breakdown): both on the Work Order's **Machines allocated**, linked.
7. Free unit 2's machine: the requirement back to "Partly allocated".
8. As a read-only user: everything visible, no buttons.

*Sitting 2 - the kit (10 minutes)*

9. On unit 1's allocation, **Add pieces** to trip 1: two boom inserts, a hook block, 4 of the counterweight.
10. Try the same hook block on another allocation over the same days: shown busy.
11. **Add a trip** later in the job, with a sling: its eligibility answer shown.
12. **Check again**: stored, today's answer beside it; the allocations list's "Starting in the next 15 days".

---

## 8. Permissions

| Permission | Granted to | Allows |
| --- | --- | --- |
| `RESOURCE_ASSIGNMENT_READ` (**new**) | the six roles (as `WORK_ORDER_READ`) | the list, one allocation, finding machines, the kit options |
| `RESOURCE_ASSIGNMENT_WRITE` (**new**) | `ADMIN`, `OPERATIONS_USER` (as `RESOURCE_REQUIREMENT_WRITE`) | allocating, replacing, freeing, changing dates, checking again, the kit list and trips |
| `WORK_ORDER_LINE_BILLING_TERMS_WRITE` (exists) | Admin, Sales User, Sales Manager, Operations | setting the billing cycle, when allocating or later |
| `WORK_ORDER_LINE_DETAIL_WRITE` (exists) | Admin, Sales User, Sales Manager, Operations | the central-government answer, with the line's other details |

Two new codes, rather than reusing the requirement's, so who may commit machines can later differ from who may
record what is needed, with no code change. Backend checks are authoritative; the screens only hide buttons.

---

## 9. Routes

**New**, each pinned in `POST_BASELINE_NEW_ROUTES`; `/candidates` registered before `/{id}`. A new contract,
`docs/agent/contracts/resource-assignment-api-contract.md`, states what they accept, return and refuse.

```text
GET  /api/resource-assignments?work_order_public_id&requirement_public_id&machine_public_id
                              &status_code&starts_from&starts_to&limit&offset                READ
GET  /api/resource-assignments/candidates?requirement_public_id&unit_number&period_from&period_to
                                          &replacing_assignment_public_id                    READ
GET  /api/resource-assignments/{id}                                                          READ
POST /api/resource-assignments                                                               WRITE   201
     {create_request_key, requirement_public_id, unit_number, machine_public_id, planned_from,
      planned_to, billing_cycle_code, notes, accept_warnings}
POST /api/resource-assignments/{id}/replace                                                  WRITE   201
     {create_request_key, expected_assignment_version, machine_public_id, replace_from,
      planned_to, billing_cycle_code, reason_code, note, accept_warnings}
POST /api/resource-assignments/{id}/release     {expected_assignment_version, last_day,
                                                 reason_code, note}                          WRITE
PUT  /api/resource-assignments/{id}/dates       {expected_assignment_version, planned_from,
                                                 planned_to, accept_warnings}                WRITE
POST /api/resource-assignments/{id}/check       {expected_assignment_version}                WRITE
PUT  /api/resource-assignments/{id}/billing-cycle   {expected_assignment_version,
                                                     billing_cycle_code}            BILLING_TERMS_WRITE
GET  /api/resource-assignments/{id}/kit-options?trip_number                                  READ
POST /api/resource-assignments/{id}/trips       {expected_assignment_version, goes_on, note} WRITE   201
POST /api/resource-assignments/{id}/kit         {create_request_key, expected_assignment_version,
                                                 trip_number, pieces[{piece_public_id, quantity}],
                                                 accept_warnings}                            WRITE   201
POST /api/resource-assignments/{id}/kit/{kit_line_id}/remove   {expected_assignment_version} WRITE
```

- **Conventions**, as the Equipment Reference and Eligibility: errors are `{"detail": "..."}` in plain words;
  `404` not found; `409` a stale version, a machine or piece or unit busy, a warning not accepted, a request key
  used for something else; `422` refused; unknown fields refused. Every write takes an expected version, except
  the creates, which take a request key.
- **Changed routes:**
  - `PUT /api/work-orders/{id}/lines/{line}/detail` and `GET .../line-details`: `site_central_government`
    (true, false or null). Omitted, it keeps what is recorded, as the line's dates do; sent as null, it clears.
  - `GET /api/resource-requirements` and `/{id}`: the statuses `PARTLY_FULFILLED` and `FULFILLED`;
    `units_covered` and `units_remaining`; `line.site_central_government`; the list's `status_code` also takes
    `NEEDS_MACHINES` (open and partly allocated).
  - `PUT` and `POST .../cancel` on a requirement: allowed from open, partly allocated and allocated; the cancel
    answer says how many machines were freed.

**New reads in other modules' services** (no route): in `equipment_reference`, the active machines of a class
with their effective capabilities, and a machine's kit with its pieces; in `eligibility`, a state's
jurisdiction from address text, and stored decisions by public id; in `resource_requirements`, the locked
requirement for allocation, the fulfilment refresh and the port's registration.

---

## 10. Events

Source module `resource_assignments`, record type `resource_assignment`. Payloads carry public ids, references,
codes, dates, versions and counts: never a registration number (as ERT-1's events never do), a note or a
reason's text; the note stays on the record and the event's reason is a fixed sentence.

| Event | Payload |
| --- | --- |
| `RESOURCE_ASSIGNMENT_HELD` | allocation, requirement, Work Order, line and source offer line ids; unit; machine public id and reference, its version; dates; billing cycle; decision id and answer; the allocation it replaces, if any |
| `RESOURCE_ASSIGNMENT_REPLACED` | the old allocation; the new one's id; the first day replaced; the reason code |
| `RESOURCE_ASSIGNMENT_RELEASED` | the last day, or none; the reason code (`REQUIREMENT_CANCELLED` when the requirement's cancellation freed it) |
| `RESOURCE_ASSIGNMENT_DATES_CHANGED` | dates before and after; the new decision's id and answer |
| `RESOURCE_ASSIGNMENT_CHECKED` | the machine's decision id and answer, before and after; how many pieces were checked, and their answers |
| `RESOURCE_ASSIGNMENT_BILLING_CYCLE_SET` | the cycle before and after |
| `RESOURCE_ASSIGNMENT_TRIP_ADDED` | trip number and day |
| `RESOURCE_ASSIGNMENT_KIT_LISTED` | trip; each piece's public id, reference, quantity, decision id and answer |
| `RESOURCE_ASSIGNMENT_KIT_REMOVED` | the line, piece and quantity |
| `ResourceRequirementFulfilmentChanged` (requirements module) | status before and after; units required, covered and remaining |
| `WorkOrderLineDetailUpdated` (exists) | gains `site_central_government` |
| `ELIGIBILITY_EVALUATED` (exists) | one per stored decision, naming the allocation or kit line it was for |

---

## 11. Data, module and migration

**Module** `backend/app/modules/resource_assignments/`:

```text
contract.py       statuses, reason codes, billing cycles, warnings, compliance states, events, record types
coverage.py       pure: busy days, a unit's coverage, the requirement's status, the order of candidates,
                  the counted-set arithmetic - no database, no clock (as eligibility/evaluation.py)
repository.py     its own tables only: three designed; a fourth, the request-key registry
                  (resource_assignment_request), was added in review (8A-R2-002) - section 17 has the tree as built
service.py        reads, the finder, the writes; split into services/ only if it outgrows one file
schemas.py, routes.py
```

**Migration `20260908_0045_equipment_allocation`**, parent `20260908_0044`:

- `resource_assignment`, `resource_assignment_trip`, `resource_assignment_kit`, as section 5.3:
  - foreign keys to `resource_requirement(requirement_public_id)`, `equipment_asset(asset_public_id)` and
    `eligibility_decision(decision_public_id)`, by public id as ELG-1 does (refinement 1);
  - CHECKs for every code set, the unit (at least 1), `units fulfilled` = 1, dates in order, the end fields
    present exactly when replaced or freed, and a counted quantity only on a counted set;
  - the generated busy ranges and the three exclusion constraints (machine, unit, piece tracked one by one);
  - `AL-` references as a generated column, as `RR-`.
- `resource_requirement`: its status CHECK accepts `PARTLY_FULFILLED` and `FULFILLED`.
- `crm_work_order_line_detail.site_central_government` (boolean, nullable).
- `RESOURCE_ASSIGNMENT_READ` and `_WRITE`, and their grants.
- **Downgrade**: drops the tables (four as built, with the request-key registry), the column and the permissions; puts requirements partly or fully
  allocated back to `OPEN` and restores the CHECK. It leaves `btree_gist`, which is `0044`'s. The stored
  decisions stay in Eligibility, naming allocations that no longer exist.

No other module's table changes; `crm_work_order` and `crm_work_order_line` are untouched.

---

## 12. Not in 8A core

| Left out | Where it goes |
| --- | --- |
| Hired machines and vendors: the own/hired flag, the vendor placeholder, the Purchase Order gate | 8A after the user test, once `D-03`, `D-04` are decided and `MHA-001` is approved |
| Firm allocation, and anything needing release | 7B, which turns holds into allocations after a fresh check (Q1) |
| Dispatch and arrival: the mobilisation transport order, the check of fire extinguishers and first-aid boxes before a machine leaves (ELG-1 Q1), the load test after erection on a construction site (BOCW), delivery challans and e-way bills, over-size permits, mats and timber | with dispatch, after release (8A after the user test); challans need Finance and the tax adviser (HSN, declared value) |
| Gate passes | 8A after the user test; the closure check is 8E |
| General tools issued from inventory | the inventory integration |
| Kit coming back to the yard, and a completed job (`COMPLETED`) | 8E |
| Carrying the kit over to a replacement machine in one step | later, if the screen check asks for it |
| Which pieces a crane configuration needs | later (`DEFERRED_REQUIREMENTS.md`, "Detachable kit") |
| Crew | 8B |
| Reminders and escalation for certificates running out before or during a job | ELG-2, reading this module's allocations |
| `EligibilityLapsed` and `EligibilityRestored` as events, and a recheck job | the job runner (ADR-019); until then, worked out when read (6.4) |
| Approving "needs approval" | the approval capability (`APR-001`, `ORA-001`) |
| A time limit on holds | a setting, when wanted (`RPA-001`) |
| HSN and asset value in the history (FRS 2.6.1) | nothing holds them: Plum's report has neither, and Fixed Assets does not exist. With Finance, when the challans need them |
| Where a machine is when not allocated | a location source; Plum's report has none (ERT-1) |
| Maintenance restrictions on availability | Plum Maintenance, when integrated (`RPA-001`) |
| Equipment documents - load charts, manuals - shown on an allocation | `DEFERRED_REQUIREMENTS.md`, "Equipment documents" |
| An availability calendar across machines | later |

---

## 13. What would stop implementation and come back to the owner

- An answer to Q1 other than hold, or to Q2 other than as recommended - both change the design.
- A need to change what the frozen handoff produces, or a Work Order table other than the line detail's one
  column.
- Finding that the Account's site addresses hold states the platform cannot match in numbers large enough to
  block the user test - a small alias list would then be the owner's to approve.
- A rule's answer that ELG-1 gives differently from what this design assumes.

---

## 14. Differences from earlier records (recorded per ADR-013)

| Earlier record | 8A core | Why |
| --- | --- | --- |
| `FUTURE_SLICES.md`: `PARTLY_FULFILLED`, `FULFILLED` and `COMPLETED` "come into use" | The first two do; `COMPLETED` stays reserved | Nothing in the core ends a job (8E) |
| WRR-001 design, section 9: "Assignment owns the assigned count ... Nothing stored here pretends to it" | The requirement stores its status; the counts are read from Assignment through the port, never stored on the requirement | The planning list filters by status; the status is the requirement's own workflow state |
| `RPA-001`: availability owns reservations, assignment owns commitments | One module, one record carrying both | ADR-018 allows one module initially; `RPA-001` asks for reservation or commitment "atomically" |
| `RPA-001`: reservation duration is a configurable parameter | Holds do not expire for now | No value is set; a setting when wanted (section 12) |
| `RPA-001`'s candidate result: last-known location, maintenance restriction, ownership | Where it is allocated; no location source, maintenance or hired machines exist | Section 12 |
| FRS 2.6.1: registration, HSN and asset value in the history | Registration, as allocated and now; not HSN or value | No source holds them (section 12) |
| ELG-1, section 13: fire extinguishers, first-aid boxes and the load test after erection are "8A's, at mobilisation" | With dispatch, after release | The core has no dispatch; release comes first (Q1) |
| `DEFERRED_REQUIREMENTS.md`: the mobilisation BOM includes general tools | Kit only | Issuing a tool moves stock: the inventory integration (owner, 25 September 2026) |
| ELG-1 Q8: "8A records it on the Work Order line's site" | A column on the line's details (7C), written through the Work Orders module | The line's site is chosen there; the Account's addresses are CRM's and shared by every business line |
| `ELA-001`: Assignment consumes `EligibilityLapsed` | Today's answer on every read; **Check again** stores one | No job runner (ELG-1 section 13) |

---

## 15. Tests and checks

- **The pure rules** (`coverage.py`): busy days (open, cut, empty); a unit's coverage across a planned hand-over
  and a replacement, and with an open end; the status from coverage; remaining; the candidate order; the
  counted-set arithmetic over overlapping days.
- **The finder:** class, type, capabilities (least, choice, unknown left out and counted); busy machines listed
  with where; each answer; retired machines and parts never offered.
- **Allocating:** every refusal of 6.3 (cancelled requirement, unit out of range, closed Work Order, dates
  outside, site not recorded, state not recognised, central answer missing, machine not fitting, busy, unit busy,
  blocked, needs approval, warning not accepted, billing cycle without its permission); the stored decision
  naming the allocation; the request key replayed and reused; two allocations of one machine at once - one
  wins, the other `409`, with the database's constraint shown to refuse on its own.
- **Coverage and status:** partly and fully allocated; a planned hand-over; a replacement keeping the unit
  covered; freeing; the requirement's own change moving its status; the event on each change; cancelling a
  requirement freeing its machines in one transaction; the port failing closed when not registered.
- **Replacing, freeing, changing dates:** each rule of 6.6 to 6.8, the kit cut or moved with the allocation, a
  later trip refusing a date change, a blocked decision refusing a change.
- **Checking:** today's answer on read; `SITE_CHANGED`; a lapsed certificate making a held allocation
  `BLOCKED` on read; **Check again** storing, including a blocked answer; the "starting soon" filter.
- **Billing cycle:** set, changed, cleared; refused without `WORK_ORDER_LINE_BILLING_TERMS_WRITE`; carried to a
  replacement.
- **Kit:** fit, retired pieces, a piece busy, a counted set's free count, each piece's decision, removing,
  trips, `KIT_DOES_NOT_FIT`; the exclusion constraint on its own.
- **Line details:** the central-government answer saved, kept when omitted, cleared when null; in the event.
- **Permissions:** reads for every role; writes refused to Sales, Finance and Management; the billing cycle
  for its four roles.
- **Events:** each payload carries no registration, note or reason text.
- **Migration:** from the empty database to the single head; downgrade and upgrade again.
- **Frontend:** pure state and controllers for the finder, the allocation page's actions and the kit picker,
  each tested with answers late and out of order; route-table tests for the new URLs; typecheck, tests, build.
- **Smoke data and cleanup:** a scenario seeding a Work Order through to requirements, machines with their
  certificates and kit, and one held allocation with a replacement for the history; an eighth record set in
  `core-regression-bundle` for Playwright. Cleanup removes the run's allocations, trips, kit lines and their
  decisions by provenance - allocations of the run's requirements - and refuses, deleting nothing, when an
  allocation it did not make is on one of the run's machines or pieces.
- **E2E:** allocate with a warning, see it held and the requirement partly allocated; replace; list kit; a
  read-only user sees no buttons. Run with `pwsh`.
- **Full gate:** the full backend regression, one suite at a time; the frontend gate; the full E2E suite; the
  migration from empty and back; `check_tracked_secrets.py` and `validate_contract_fixtures.py`; the frozen
  handoff contract's hash before and after; independent review, capped at three rounds; the owner's screen check,
  with the steps in the chat.

---

## 16. Shared files this package touches

- `backend/app/main.py`: the new router.
- `backend/app/modules/authorization/contract.py`: two permissions.
- `backend/tests/fixtures/post_baseline_tightened_routes.py`: the fourteen routes (thirteen designed; the
  fourteenth, saving what a Trip (Own Load) carries, added on the owner's decision of 29 September 2026). Read it
  by eye after any merge.
- `frontend/src/routes.tsx` and its tests: three URLs; the sidebar.
- `backend/app/modules/resource_requirements/`: statuses, the port, the fulfilment refresh, the line facts.
- `backend/app/modules/work_orders/`: the line detail's one field.
- `backend/app/modules/equipment_reference/service.py` and `eligibility/service.py`: new reads.
- `backend/tooling/smoke_data/` and `e2e/`.

**Documents updated when it is built:** the new `resource-assignment-api-contract.md`;
`resource-requirement-api-contract.md`; `work-order-contract.md` (the line detail field);
`eligibility-api-contract.md` and `equipment-reference-api-contract.md` (the new reads);
`CONTRACT_REGISTRY.md` (a note on `RPA-001`, whose maturity stays the reviewer's); the Resource Availability and
Assignment rows of `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`; this design's implementation record and an acceptance
record; `FUTURE_SLICES.md`, `DEFERRED_REQUIREMENTS.md`, `NEXT_STEPS.md` and a continuity note.

---

## 17. Implementation record (28 September 2026)

Built on `hiring/8a-core-equipment-allocation` in worktree `<a separate worktree>`, from the design commits and
`main` at `d2f23f3`, on the owner's answers of 28 September 2026 (section 1.0). Migration `20260908_0045`, parent
`20260908_0044`. Sections 4 to 11 are built; section 12 lists what is not.

### What exists now

```text
backend/alembic/versions/20260908_0045_equipment_allocation.py
        resource_assignment (AL- references; generated busy_range; exclusion constraints on a machine's days
        and a unit's days), resource_assignment_trip (unique on its id and allocation), resource_assignment_kit
        (exclusion constraint on a piece tracked one by one; a composite key to its own allocation's trip),
        resource_assignment_request (every request key once, its kind, requirement and fingerprint);
        triggers: the lock per statement (resource_assignment_serialize), an allocation keeping its
        requirement, a trip within its allocation's period, kit days derived and following, kit tracking
        matching its piece; resource_requirement's status CHECK widened; crm_work_order_line_detail.
        site_central_government; RESOURCE_ASSIGNMENT_READ and _WRITE with their grants
backend/app/modules/resource_assignments/
        contract.py, errors.py, rules.py (pure), repository.py, views.py (reading), service.py (writing, and
        the port), schemas.py, routes.py - 14 routes
backend/app/modules/resource_requirements/
        ports.py (new: the port Resource Assignments registers); contract.py, schemas.py, repository.py,
        service.py: two statuses, units covered and remaining and which, the NEEDS_MACHINES filter, the
        fulfilment refresh, cancelling freeing the machines, requirement writes under the Work Order's lock
backend/app/modules/work_orders/            the line detail's central-government answer; the end-dates
                                            listener (contract period, extensions, a line's end date), and
                                            the Work Order's shared status lock, re-exported by service.py
backend/app/modules/eligibility/            jurisdiction_for_state_text, get_stored_decisions
backend/app/modules/equipment_reference/    machines_for_allocation, allocation_asset, kit_for_machine,
                                            asset_references
backend/app/modules/authorization/contract.py, backend/app/main.py
backend/tests/fixtures/post_baseline_tightened_routes.py    the 14 routes
backend/tests/test_8a_allocation_rules.py, test_8a_equipment_allocation.py
backend/tooling/smoke_data/                 the scenario equipment-allocation, the core bundle's eighth record
                                            set allocation_target, cleanup by provenance
frontend/src/pages/allocations/             Allocations (/resource-assignments), Allocate or replace
                                            (/resource-assignments/new), an allocation (/resource-assignments/:id),
                                            the machines sections on a requirement, a Work Order and a machine;
                                            allocationState.ts, tested
frontend/src/pages/resource-requirements/, work-orders/, equipment/MachinePage.tsx (the way back to where
it was opened from), equipment/certificatesState.ts (queryViewKeeping), layout/AppShell.tsx, routes.tsx,
styles/globals.css
e2e/tests/equipment-allocation.spec.ts
docs/agent/contracts/resource-assignment-api-contract.md
```

### Refinements made while building (recorded per ADR-013)

None changes an answer of the owner's.

| # | Design said | Built | Why |
| --- | --- | --- | --- |
| 1 | `coverage.py` for the pure rules; `service.py` for reads and writes | `rules.py` (it holds the candidate order and the left-out reasons too); `views.py` reads, `service.py` writes and registers the port; `errors.py` | Each file one concern; `service.py` stays one file |
| 2 | A unit is covered by "the busy days of its held allocations" | By the days every allocation of the unit kept - held ones, and replaced or freed ones up to their last day | Counting held ones only, a replacement from a later day left the days before it uncovered, and the unit with them (found by a test). A machine freed partway leaves its days covered and the rest to find |
| 3 | A status change "moves [the requirement's] version on" | It moves neither the version nor who last changed the requirement | The status is worked out, not edited: moving the version would make a planner's open change form stale whenever Operations allocates. A save works the status out again anyway, and the event records each change |
| 4 | An allocation that no longer fits: "its unit then counts for nothing" | Days outside the requirement's period and units above the number required count for nothing; a machine that no longer matches the kind asked still covers its days, with `NO_LONGER_MATCHES` | The machine is still held for the job: the warning asks Operations to replace or free it, which then shows the unit needing one. Judging the match inside the port would pull the Equipment Reference into Resource Requirements |
| 5 | The port "fails closed" | With no port registered, reading a requirement or cancelling one fails with a server error | Nothing is shown or cancelled on a guess; `app.main` always loads the module, so this happens only if that line is removed |
| 6 | - | The line detail's central-government answer, left out of a save, keeps what is recorded; sent empty, it clears | A caller that predates the field never erases an answer, as the line's dates already work |
| 7 | "The cancel form says first how many machines will be freed" | It says every machine held for the requirement will be freed; the Machines section above it lists them, and the response's `machines_freed` gives the number | The list is already on the page; a second count would be a second request to keep in step |
| 8 | - | Whether the user may set a billing cycle when allocating or replacing is resolved by the service (`can_set_billing_cycle`) | The route guard allows no role reading in a route module; Eligibility resolves its identity permission the same way |
| 9 | Cleanup refuses "when an allocation it did not make is on one of the run's machines or pieces" | ... holds or held one: a replaced or freed allocation of another Work Order refuses too | A freed allocation keeps its machine and kit on that Work Order's history, so deleting the machine would break it (found while writing the harness test) |
| 10 | - | The harness loads the allocation module itself (`tooling/smoke_data/builders.py`) | It runs without `app.main`, so the port was not registered and the requirement it seeded failed closed - found by the first E2E run; a test in a fresh interpreter guards it |

### Independent review, round 1 (28 September 2026)

the independent reviewer, on tree `879a004` (HEAD `31bac05`): `CORRECTION_REQUIRED`, seven material findings, all corrected.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-R1-001: a requirement without its own end keeps a stale status when the contract's or line's end moves, and drops out of "Still needs machines" | The Work Orders module keeps a listener registry (`register_end_dates_listener`, `services/common.py`) and calls it, in its own transaction and under the Work Order's row lock, from saving the contract period, adding or removing an extension, and saving a line's details with a new line end. Resource Requirements registers a listener that locks the Work Order's live requirements without their own end, in id order, and works their status out again. No requirement or allocation write takes the Work Order's lock, so the order holds | contract end moved later and back, an extension added and removed, a line end set and cleared: the status follows each time, the version does not move, the planning filter follows |
| 8A-R1-002: a request key replays a request that differs from the first | Each allocation and kit line stores the SHA-256 of the request that made it - the fields sent, and only those, with the allocation acted on (`create_request_fingerprint`); a replay compares it, any difference is `409` | create (billing cycle changed or left out, notes, the tick, the end), replacement (reason, note, end, cycle, tick), kit (the tick, the pieces), and a replacement's key used to allocate |
| 8A-R1-003: checking again, the billing cycle, trips and removing kit skip the closed-Work-Order refusal | One helper locks the held allocation and refuses a closed Work Order before anything else, a write that would change nothing included; every write uses it | all ten writes on a closed Work Order refused, the version unchanged |
| 8A-R1-004: a date change checks only later trips carrying kit; kit options for a trip after the allocation's end build an inverted range | Every later trip must stay within the new dates (a later trip can be neither moved nor removed yet, recorded as a known limitation); the kit window refuses a trip after the allocation's last day with `422` | a trip with no kit refuses the change; a freed allocation's later trip refuses kit options |
| 8A-R1-005: lists judge compliance from the machine alone | Every read works out the listed kit's today answers and whether each piece still fits; the page only adds the trip and line details | a blocked hook block makes the allocation `BLOCKED` in the Work Order, machine and requirement lists |
| 8A-R1-006: after the finder's dates are edited, the old machines stay choosable and the old period is saved | Changing a date clears the choice; choosing and saving wait until machines are found for the dates in the boxes (`answerIsForDates`) | the state function and `allocateProblem` refusing stale dates |
| 8A-R1-007: the screens offer allocation when the site cannot be judged | The requirement's Machines section says what to put right in place of its links (`lineSiteProblem`); the finder disables choosing and saving and shows the site's message; `allocateProblem` refuses a site problem and a missing answer | all three site problems, and the line checks |

### Independent review, round 2 (28 September 2026)

the independent reviewer, on tree `b5d8e1d` (HEAD `92c7dbc`): `CORRECTION_REQUIRED`, four material findings, all corrected.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-R2-001: replays skip the closed-Work-Order check; nothing serializes a write with a Work Order's closure; the screens offer actions on a closed Work Order | Every write first takes the Work Order's row in shared mode and reads its status there (`hold_work_order_status`, new in the Work Orders service), before any replay: a closure - which, like every Work Order write, will take the row's update lock - waits for the write or is seen by it. The order is now Work Order (shared), requirement, this module's lock, Eligibility's, the same direction as the end-dates listener (Work Order, then requirements). No code closes a Work Order yet; the lock is ready for it. Both allocation pages read the Work Order's status and offer no action on a closed one | replay after closure for an allocation, a replacement and kit; a write started while another transaction holds the Work Order's row and closes it waits, then is refused; the screens' rule |
| 8A-R2-002: one key can make an allocation and a kit lot | One registry, `resource_assignment_request`, holds each key once across allocating, replacing and listing kit, with its kind and fingerprint (the fingerprint columns on the two record tables are gone); a key is claimed under this module's lock in the writing transaction | a key used for an allocation refused for kit, and one used for kit refused for an allocation and a replacement; the database refusing a second row for a key |
| 8A-R2-003: a requirement edit that moves its status records the move twice | The update event's status pair is the status it leaves; the move is `ResourceRequirementFulfilmentChanged`'s alone | the exact events and pairs when a change from 1 to 2 units moves Allocated to Partly allocated |
| 8A-R2-004: the database accepts a kit line on another allocation's trip | A unique key on the trip's `(id, resource_assignment_id)` and a composite foreign key from the kit line | the database refusing a kit line moved to another allocation's trip |

### Independent review, round 3 (28 September 2026)

the independent reviewer, on tree `09c5ede` (HEAD `ff2b809`): `CORRECTION_REQUIRED`, five material findings, all corrected. Round 3
was the last within the cap of three; a fourth waits for the owner.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-R3-001: requirement writes take no Work Order lock, and four allocation writes skip the requirement's | Creating, changing and cancelling a requirement take the Work Order's row, shared, first and re-check closure there; checking again, the billing cycle, trips, kit and removing kit take the requirement's row after it. Every write now keeps one order: Work Order, requirement, this module's lock, Eligibility's | a cancellation, a requirement change, checking again and the billing cycle each started while another transaction closes the Work Order: each waits, then is refused, and a cancellation frees nothing |
| 8A-R3-002: the harness's cleanup leaves the request registry's rows | Each registry row names its requirement (a foreign key, so it cannot outlive it); cleanup deletes the run's by its requirements and counts them; `status` reports any left | three keys removed with the run, none left |
| 8A-R3-003: the replacement finder defaults to the requirement's period | With no dates asked, the finder takes the replaced allocation's own days - from today when it has started and is not over, else its first day, to its end; the screen refuses a start outside the old allocation's days | a replacement of an allocation shorter than the requirement; the screen's rule |
| 8A-R3-004: the finder offers Allocate while the unit is taken on the days shown | The unit's conflicts block choosing and saving, with the reason beside the button | the screen's rule |
| 8A-R3-005: a kit line can misstate its piece's tracking to slip past the exclusion constraint | A trigger requires a kit line's tracking to be its piece's class's | the database refusing a misstated line, inserted or updated |

### Independent review, round 4 (29 September 2026, on the owner's yes beyond the cap)

the independent reviewer, on tree `1f7c13c` (HEAD `45ff92a`): `CORRECTION_REQUIRED`, four material findings, all corrected. A fifth
round waits for the owner.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-R4-001: creating a requirement replays, and checks its dates against the Work Order, before the Work Order's lock | The lock comes first in the transaction; the request key's replay, the fields' checks and the Work Order's dates are read after it | a replay after closure refused; a create waiting while another transaction shortens the contract is checked against the shortened end |
| 8A-R4-002: the replacement finder accepts an allocation on another unit, or one no longer held | The finder refuses both (`422`); the page checks the allocation it loaded against the unit and requirement it was opened for | another unit, and a freed allocation, refused; the page's rule |
| 8A-R4-003: the database trusts a kit line's days | A trigger derives a kit line's days from its trip and allocation on every insert and update, and triggers on the allocation's dates and the trip's day move its lines; the service no longer writes them | days written untrue put back, so the same hook block is refused on an overlapping allocation; a line moving with its allocation's end |
| 8A-R4-004: the kit picker offers pieces that are blocked, need approval or are not judged | Only a free piece judged "can be allocated", with a warning or without, can be ticked; a piece not judged is refused before sending, and the site's message shows beside the picker | the picker's rules |

### Independent review, round 5 (29 September 2026, on the owner's yes)

the independent reviewer, on tree `9eb21ad` (HEAD `6519ce0`): `CORRECTION_REQUIRED`, two material findings, both corrected. A sixth
round waits for the owner.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-R5-001: the database lets a later trip, or an allocation's planned period, move so the trip lies outside the period, and the derived kit days follow it | A trigger refuses a later trip written or moved outside its allocation's planned period, and a change to the period that would leave one outside. The day an allocation ended is not its period: replacing or freeing it early still ends a later trip's kit with no days | the four moves and an insert refused; moves within the period allowed; a later trip cut off by freeing leaves its hook block free for another allocation over those days |
| 8A-R5-002: kit listing and removal messages appear below every trip, not beside their button | Each listing's message shows in its own trip, each removal's beside its own line; the page's repeated message markup is one component | the keys' rule (the frontend has no component tests: `DEFERRED_REQUIREMENTS.md`) |

### Independent review, round 6 (29 September 2026, on the owner's yes)

the independent reviewer, on tree `7259e8a` (HEAD `531a56b`): `CORRECTION_REQUIRED`, one material finding, corrected. A seventh round
waits for the owner.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-R6-001: the triggers reading one table's dates to hold another's do not serialize two transactions - a key-share lock does not conflict with a date update - so a direct write can commit a trip outside its period, or a kit line missing an extension | The three cross-table trigger functions take the module's transaction advisory lock (the key the service takes, `WRITE_LOCK_KEY`) before they read or move dates; a statement after the lock sees what the other transaction committed | both orders of each race, two sessions: a period shortened while a later trip is being added, and a trip added while the period is being shortened - each waits, then is refused; an allocation extended while a kit line is being written, and a kit line written while the allocation is being extended - the line ends up with the extended end. The trip-or-line-first order is already serialized by the allocation row's lock (a probe showed the date update waiting on the foreign key's lock), so only the other order proves the new lock: without it, the trip is committed outside the period and the line keeps the old end. The triggers' key is the service's |

### Independent review, round 7 (29 September 2026, on the owner's yes)

the independent reviewer, on tree `8f658e8` (HEAD `00c1d54`): `CORRECTION_REQUIRED`, two material findings, both corrected. An eighth
round waits for the owner.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-R7-001: round 6's lock, taken in row triggers, comes after PostgreSQL has locked the row - the reverse of the service's order - so a direct write and a service write on the same allocation or kit line can deadlock | One statement-level BEFORE trigger function, `resource_assignment_serialize`, takes the lock on every statement writing an allocation's dates or end, a trip or a kit line, before any row is locked; the row triggers no longer take it | a service-shaped transaction holding the lock, a direct update of the same allocation, then of the same kit line, started meanwhile: the direct one waits before the row, the first locks the row at once and commits, neither is a deadlock victim; the lock is taken per statement on the three tables and nowhere per row |
| 8A-R7-002: "outside the contract" judged only an allocation's first and last days, missing a gap between extensions inside it | The whole of the allocation is judged: its ends by Slice 7D Part 3's rule, any gap overlapping it, and an open end under a fixed contract end | an allocation spanning a gap with both ends inside the contract warned; one within the first period not |

### Independent review, round 8 (29 September 2026, on the owner's yes)

the independent reviewer, on tree `0239e1a` (HEAD `fe83b51`): `CORRECTION_REQUIRED`, two material findings, both corrected. A ninth
round waits for the owner.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-R8-001: the statement-level lock triggers leave out DELETE, so a direct delete of a kit line or trip locks its row before the lock and can deadlock with the kit follower | The triggers fire on INSERT, UPDATE and DELETE of trips and kit lines, and of allocations (their date updates, and adding or removing one) | a direct delete of a kit line, then of a trip, started while a service-shaped transaction holds the lock: each waits before its row, the first commits; the triggers' events checked exactly |
| 8A-R8-002: the requirement page offers "Allocate a machine" on a unit already covered on every day - the known limitation recorded earlier contradicted the agreed screen rule | The requirement's reply names the covered units (`covered_unit_numbers`, from the rule that sets its status); the page offers allocation only on a required unit not among them, so a partly covered unit keeps its link. The known limitation is withdrawn | the covered units in the rules and in a requirement's reply (one unit covered, one partly); the page's rows for covered, partly covered and empty units |

### Independent review, round 9 (29 September 2026, on the owner's yes)

the independent reviewer, on tree `b91d6e4` (HEAD `094012f`): `CORRECTION_REQUIRED`, three material findings, all corrected. No tenth
round was run (below). Rounds 6 to 9 all concerned statements that bypass the service; this round's correction
settles the lock order for every such statement at once rather than one event at a time.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-R9-001: round 8 put adding an allocation under the module's lock, before its foreign key locks the requirement's row - the reverse of the service's order | Adding an allocation takes no part in the lock: it reads no other table's dates, and the exclusion constraints decide overlaps safely under concurrency. The requirement an allocation fills never changes (a trigger), so no update reaches for a requirement's row after the lock | a direct insert started while a service-shaped transaction holds the requirement's row waits on that row without the lock, and the service then takes the lock and commits; changing an allocation's requirement refused |
| 8A-R9-002: the lock triggers on allocations and trips fire only for listed columns, and the events test could not see a column list | Every UPDATE and DELETE of an allocation, and every INSERT, UPDATE and DELETE of a trip or kit line, takes the lock first - no column list; the events test checks the column list is empty | an update of an allocation's billing cycle, and of a trip's note, started while the lock is held: each waits before its row |
| 8A-R9-003: every list of allocations stops silently at 200 | The screens fetch page after page, by `offset`, until a page comes back short; the list's order ends with the allocation's id, so pages never overlap | 401 rows fetched in three pages, and an exact multiple ending with an empty page |

### Where the review stopped

**Round 10 was not run (owner, 29 September 2026).** Nine rounds of independent review were run - the first three within the usual cap, rounds 4 to 9 each on the owner's yes - and every finding was corrected. The owner stopped there: a full review of 8A core, together with documentation and UAT corrections, is to be done later. The package is therefore not independently accepted; round 9's corrections have not been reviewed.

### The owner's decision after the review stopped: Trips (Own Load) (29 September 2026)

While reading the screen-check steps, the owner found two things:

> the name 'trip' can be confusing but so can 'Dispatch'. For now change it to Trip (Own Load) which clarified.
> Second issue - one crane may need multiple trips depending on how many parts the crane might have to be broken
> down into. So, having just one trip is not adequate.

The owner agreed this split ("yes, go ahead with that split"):

| Now, in 8A core | Deferred (`DEFERRED_REQUIREMENTS.md`, 8A, "Trips (Own Load)") |
| --- | --- |
| Screens and messages say **Trip (Own Load)**; field, route, table and event names keep `trip` | Moving or removing a Trip (Own Load) |
| Trip 1 is no longer "the machine": it goes on the allocation's first day, as before, and every trip is one load | Each crane model's standard loads, with weight and size, held on the Equipment Reference |
| Each trip's note is **what this load carries**, and can now be changed - trip 1's too, which is written with the allocation (`PUT .../trips/{trip_number}/note`, event `RESOURCE_ASSIGNMENT_TRIP_NOTE_CHANGED`, the note not in the event) | The crane's major parts as records, so a load names them and 8E checks them back |
| **Add a Trip (Own Load)** starts at the allocation's first day, so several loads on day 1 are quick to enter (a later trip could already go on the first day) | Each Trip (Own Load) linked to Transportation's "PBL Own Loads" order; loads leaving before the allocation's first day |

This supersedes "trip 1 goes with the machine" in the design above (sections 5 and 6). No new table and no
migration: the note column exists. The change came after round 9, so it is not independently reviewed; it goes into
the full review with the rest.

### The owner's screen check (29 September 2026)

Run `te1-d38e094b`, as `ops1` then `readonly1`. What the owner found, and what was done:

| Found | Done |
| --- | --- |
| After Listed, Saved and the other actions the page jumped back to its top, so the message beside the button was out of sight | Read again after a save, the allocation already shown stays on the page until the fresh copy arrives (`queryViewKeeping`, beside `queryView` in `certificatesState.ts`); "Loading the allocation..." shows only when nothing is shown yet |
| The counterweight's number box was too wide, and did not say a number was wanted | Up to three digits, "0" as a hint, "nos." beside it (`.count-field`) |
| "Save what it carries" was not clear | The label "What this load carries" stays (the owner: it "is fine"); the button is **Save**, and the empty box hints "e.g. Base & carbody" |
| A machine opened from the finder or an allocation led back only to the machines list | The machine page leads back to where it was opened from ("Back to allocating", "Back to the allocation") |
| The seeded cranes' numbers, ending AL1 to AL4, read like the allocations' numbers, AL-000... | The `equipment-allocation` scenario's cranes end CW1 to CW4 (crawler; CR1 and CR2 were taken by ERT-1's cranes) |
| The steps said "Left out"; the screen says "Not offered, of this class: ..." above the table | The acceptance record says what the screen says |
| Two inserts on a later trip looked greyed out | Not reproduced: in the owner's screenshots their boxes were active (only the taken hook block and the unexaminable sling were grey). No listing reached the server, on the first try or the second, so listing inserts on a later trip is repeated in the re-check |

Everything else in the steps behaved as expected: the finder's answers, the warning's tick, trips and kit, replacing,
the date refusals (a day the unit already has a machine; a day after the requirement's end), freeing, the lists, the
central-government refusals and the read-only view. The last two steps - putting the central-government answer back,
and listing the inserts - did not reach the server before the run was cleaned up, and are repeated in the re-check.

**The re-check passed (the owner, 29 September 2026), run `te1-a32c89e5` on `4fb3c27`**: the way back from a machine's
page, the description saved on trip 1 and a second trip added with the page staying put, two inserts and two
counterweight blocks listed on the later trip, and the central-government answer taken away and put back - each write
confirmed in the server's log and rows. One point, deferred by the owner: an earlier action's message stays when the
next one's appears (`UI_UX_CARRY_FORWARD.md`, "Allocations").

### Full review (30 September 2026, the owner's request)

In place of round 10, the owner asked for a full review of the complete candidate, with documentation and UAT
corrections, before ELG-2. The records were brought to the final tree first (`8970a96`, `6abcde5`); then the independent reviewer
reviewed the whole candidate against the base in two bounded packets - the reviewer's input limit cannot carry it once: part
A, the backend and database (packet `3c34a863...`), and part B, the screens and records (packet `3982d4fb...`), both
on tree `296641d` (HEAD `6abcde5`). Part A: `CORRECTION_REQUIRED`, one material finding; part B:
`CORRECTION_REQUIRED`, seven material and one advisory. All corrected.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-FA-001: a requirement's status, worked out when the requirement changes or its end moves with the Work Order's, read the allocations without this module's lock, so an allocation write in progress - a direct one - could leave it wrong | The port gains `hold`, which takes this module's write lock; the status refresh takes it after the Work Order's and the requirement's locks and before reading coverage | a direct change to an allocation's end held open while the contract's end moves, and while the requirement's own end moves: each waits, then stores `FULFILLED` |
| 8A-FB-001: text typed into a box while its own save was in flight was replaced by the saved value | Every box, list and tick on the allocation page waits with the buttons while an action is sent or the page is read again; adding a trip clears its note from the form as it now stands | the draft rule (tested before); the page itself has no component tests |
| 8A-FB-002: signing out, or in as someone else, left the allocation page and the finder showing the old record and the old role's controls | Both pages listen for the session changing: the roles are read again, the record, choices, messages and picker dropped, requests in flight ignored, and the page read again - with no session, it asks to sign in | by hand, see the acceptance record |
| 8A-FB-003: an open kit picker kept its options after the allocation changed, so it could offer pieces the server would refuse | The picker carries the allocation version its options answer for; when the allocation changes, the options are read again, keeping the choices, and an answer for an older version or trip is ignored | by hand |
| 8A-FB-004: lists paged by a count of rows to skip over an order that changes, so a row changing between two pages could make another skipped or read twice | The list comes in the order allocations were recorded, and `after` an allocation gives the next page; the screens read each page after the last row read, and order the rows for display | a row freed between two pages of the held list: skipping one row loses the next, reading after it does not (API and pure rule); the order recorded; `after` an unknown allocation `422`; the display order |
| 8A-FB-005: "Free the machine" with "Other" and no note was offered, then refused by the server | Refused beside the button before asking to confirm: "Say what the other reason is, in the note." | the rule |
| 8A-FB-006: after a refusal as out of date, the page kept offering the old copy | A refused write keeps the server's status; on `409` the allocation is read again at once, controls waiting | by hand |
| 8A-FB-007: a successful action followed by a failed re-read emptied the page, hiding the success | The action's response - the allocation as it now stands - is shown at once, with no second read (`answered`, beside `refreshIf` in the shared loader) | the loader: an answer in hand shown, and a read in flight unable to replace it |
| 8A-FB-008 (advisory): the API contract's module inventory said three tables | Four, naming the request-key registry | - |

**Round 2** (the owner's yes, 30 September 2026), on tree `718b5a3` (HEAD `331480b`), section 0 carrying every change
since the first round: part A `CORRECTION_REQUIRED`, one material; part B `CORRECTION_REQUIRED`, five material and two
advisory. The first round's corrections were not found wrong; round 2 went a level further.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-FA2-001: an allocation written by a statement around the service leaves its requirement's stored status behind - "allocated" with a day uncovered | The database refuses any statement adding, changing or removing an allocation unless its transaction is marked as the service's own (`resource_assignment_guard`, a statement trigger that runs before the lock trigger); the service marks it with its lock, the harness's cleanup when it removes a run's allocations with their requirements | an update, a delete and an insert written around the service refused, the status unchanged; the mark gone with the transaction; the database tests' own direct statements marked as the service's |
| 8A-FB2-001: the finder's boxes, choice and Find stayed live while an allocation was saved; on the allocation page Refresh, the picker's Close, Keep it and Replace stayed live during an action | All of them wait with the save or the action | by hand |
| 8A-FB2-002: an answer to a request sent before a session change could still show, navigate or add a message; typed trip and free-form drafts survived it | Both pages count session changes; an answer for an earlier session changes nothing, and every form, draft, message, busy state and request key is reset | by hand |
| 8A-FB2-003: kit options did not say which allocation version they answered for; a reload kept choices no longer possible; a 409 left the picker's offer in place | The options carry the allocation's version, and show only under it; a reload keeps only choices still selectable and within what is free; a refusal as taken or out of date reads the options again | the version on the options, before and after a change; the choices kept |
| 8A-FB2-004: the next Trip (Own Load)'s day kept the old first day when the allocation's start moved later | The day follows the first day unless the user chose another; a day outside the allocation is refused beside **Add a Trip (Own Load)** | the day following and staying; the days refused |
| 8A-FB2-005: the results sections credited the latest candidate with checks run on earlier trees | Each result names its tree; the latest candidate's own checks are listed apart | - |
| 8A-FB2-006 (advisory): the line details' new central-government answer is styled inline | Left as it is: the page styles every field inline, and moving a page to the shared stylesheet is its own package (`CODING_STANDARDS.md`, section 7) | - |
| 8A-FB2-007 (advisory): design section 11 said three tables | Four as built, with the request-key registry | - |

**Round 3, focused** (the owner's yes, 30 September 2026): round 2's corrections only, on tree `7d39298` (HEAD
`8afa52c`), one packet. `CORRECTION_REQUIRED`: two material and two advisory; no defect in round 2's code corrections.

| Finding | Correction | Tests |
| --- | --- | --- |
| 8A-F3-001: NEXT_STEPS still called the round-2 regression and E2E next; some results named no exact tree | NEXT_STEPS records them done; every result names its commit, or the uncommitted tree it ran on and how that differs from the commit | - |
| 8A-F3-002: the guard's proof said all four cases failed "DID NOT RAISE"; the DELETE case could not - trip 1's foreign key blocked the delete without the guard | The DELETE case removes the allocation's trips first in the same transaction, so only the guard can stop it; the proof rerun and recorded case by case | with the guard disabled all five cases fail "DID NOT RAISE"; enabled, they pass |
| 8A-F3-003 (advisory): the port's `hold` marked Resource Requirements' transactions as allocation writes, though they write none | `take_lock` takes the lock alone for `hold`; `take_write_lock` takes it and marks | an allocation statement in a transaction holding only the port's lock is refused |
| 8A-F3-004 (advisory): the repository's and the migration's headers said three tables | Four, the request-key registry named | - |

### Results

Recorded, each with the tree it ran on, in the continuity note (`docs/continuity/SLICE_8A_CORE_EQUIPMENT_ALLOCATION.md`),
and summarised in the acceptance record, which says which checks the latest candidate has had and which are still
to run. A result holds for the tree it names, not for a later one.

### Keeping the days held (1 October 2026, after the merge)

A check of the records against the code found that freeing an allocation with no last day, or replacing it from
its first day, took away every day it had held even after the machine had gone - contrary to "Busy days" above,
where the days an allocation held stay in the history. The owner decided on 1 October 2026: once an allocation's
first day has come (on or before today, India date, the test `release_for_cancelled_requirement` already uses), it
may lose all its days only by being freed with no last day as `RECORDED_BY_MISTAKE`. Freeing for any other reason
then needs a last day; a replacement must start after the old one's first day. Before the first day nothing
changes, and replacing from a later day stays allowed.

Built on main at `82acebd`. No migration. `release_assignment` and `replace_assignment` refuse with a `422` naming
the first day and saying what to do instead; the finder's default first day for replacing a started allocation is
never earlier than the day after its first day; the free form says when a last day is needed and refuses, beside
its button, before asking to confirm; the replace page shows the same refusal as the server. Sections 6.6 and 6.7
above and `resource-assignment-api-contract.md` carry the rule. `RPA-001`'s text is unaffected: it says history is
kept, which this enforces. Tests: five backend tests that fail on `82acebd` (freeing a started allocation for each
of three other reasons without a last day; replacing it from its first day; the finder's default) and one that
passes on both (recorded by mistake still frees with no days), plus the existing before-start tests unchanged;
three frontend tests. Results are in `docs/continuity/SLICE_8A_KEEP_HELD_DAYS.md`.

Merged as PR #81 (`1cc2671`). The independent review after the merge found the finder's default still used "started
and not over", so a held allocation past its last day was offered its first day, which the server refuses; the
finder now uses the server's test alone (6.6). Recorded in the same continuity note.
