# WRR-001 Resource Requirement Foundation - design proposal

Status: **Design agreed, 24 September 2026.** Every question is answered (sections 1 and 2); the
owner's standing rule (section 1) replaced the Q10 and Q12 recommendations with a canonical equipment
structure of our own. **Implemented 24 September 2026** - see section 22, "Implementation record".
Independent review and the owner's screen check follow; not yet committed as reviewed.

Hiring lane (Track 2). Worktree `<a separate worktree>`, branch
`hiring/wrr-001-resource-requirements`, based on `main` at `3e22136`. Migration slot
`20260908_0041`, confirmed. Foundation Slice Mode: the shape is built properly, the screens minimally.

A Resource Requirement is Operations' record of what a Work Order line needs on site - what kind of
machine, how capable, how many, when, with what crew - so planning can
start before the Work Order is released. It does not change the Work Order, reserve anything, or
assign anything. `WRR-001` allows exactly this: "A valid Work Order shell line may create a Resource
Requirement and begin non-committing planning."

To say *what kind of machine*, the platform needs a proper equipment structure. Plum's is not good
enough (section 21), so this package also defines ours: the **Equipment Reference**, owned by the
platform, which Plum's data will be transformed into.

---

## 1. Owner decisions so far

### The standing rule (owner, 24 September 2026)

> We do not compromise on quality because of Plum's existing models. We propose a better structure.
> If Plum cannot update its master, we build an intermediate transformer from whatever is in Plum
> into the superior structure. At some point the new structure becomes the primary data source, and
> Plum ingests from it - by combining some fields, or transforming them in other ways. Our build must
> be superior and future-proof.

### Answered

| # | Question | Answer |
| --- | --- | --- |
| Q1 | Which lines need a requirement? | **As recommended.** Operations adds requirements line by line, only where a line needs a machine or crew. Nothing is created automatically, and a line without one is not reported as missing. Whether release (7B) should refuse a machine line with no requirement is 7B's question |
| Q2 | How many machines? | **As recommended.** The requirement records how many are needed. A line's quantity counts billing units ("8 Days", "3 Mon") and is shown for reference only |
| Q3 | What kind of machine? | Superseded by the standing rule: see sections 4-6 and Q14 |
| Q4 | Crew numbers | **As recommended.** Start from the Work Order's Part 4 operators and helpers in force when the requirement starts; Operations may change them; differences are shown. Never pay terms |
| Q5 | Continuous or on call? | **No such choice.** Every deployment is continuous: the machine goes to site, and how the customer uses it is their lookout. Billing follows the billing terms (minimum hours, overtime). No deployment-pattern field |
| Q6 | Who may add, change, cancel? | **As recommended.** Operations and Admin. Everyone else reads |
| Q7 | Different needs in different periods on one line | **Several requirements per line**, each with its own kind of machine, capability, number and dates. Usually already split into two Work Order lines; the flexibility is there when not. No split button |
| Q8 | Contract dates change afterwards | **As recommended.** A warning on the requirement; the contract change is not blocked |
| Q9 | Migration slot | **`20260908_0041` confirmed** |
| Q10 | Use Plum's categories? | **Withdrawn** by the standing rule. Plum's categories become one input to a transformer, not our structure |
| Q11 | Sample equipment data | **Supplied**: Plum's "Own Vehicle Complete Information Report", 24 September 2026. Real fleet data: kept in `<a PBL folder outside the repository>`, never committed, never test data. Findings in section 21. The owner is also asking for a sample of Plum's vehicle type master |
| Q12 | A trailer is two machines | Replaced by Q15 |
| Q13 | Record as ADR-037 | **As recommended** - section 16 |
| Q14 | Is the structure right? | **As recommended, with two corrections.** Trucks are hired, but by the **Transportation module (its GTA sub-module)**, not Hiring. Generators are not hired. Prime movers, trailers, modular hydraulic trailers and power packs are Transportation too. So each class records **which business lines use it** rather than a yes/no "hired" (section 5). Fleet's Equipment Master owner owns the structure from here |
| Q15 | Combinations of machines | **Not needed by Hiring.** Combinations (prime mover + bed) are Transportation's. Keep the provision, ignore it for now: the data holds items under a requirement, but a Hiring requirement has exactly one item. Usually 1 prime mover + 1 bed; 1 + 2 has not been seen, so if Transportation adopts this logic, a rule "one prime mover takes at most one bed" can be added then |
| Q16 | How Plum's data comes in | **As recommended.** Our transformer now (B), ask Plum for its improvements in parallel (A), our structure primary once Hiring assignment runs on the platform (C) |
| Q17 | One package or two | **As recommended.** One package, migration `20260908_0041` |

---

## 2. The questions as they were put (record)

Kept as asked, so the answers above can be read against them.

### Q13. Record the standing rule and the equipment structure as ADR-037

The rule changes who defines equipment categories. `RMR-001` (approved) says Plum's Equipment Master
is authoritative for owned equipment; under the rule, **the platform defines the structure** and Plum
is a source feeding it, until our structure becomes primary. This is the same move ADR-032 made for
employees and organisation.

**Recommendation:** record it as ADR-037 (draft text in section 16), add a short note to `RMR-001`
pointing to it (as ADR-032 did, without rewriting the contract), and update the contract registry,
the dependency register and the module boundary matrix to match.

### Q14. Is the equipment structure right?

Section 5 is a first version: **classes** (Crane, Aerial Work Platform, Prime Mover, Trailer, ...),
**types** within each (Crawler, All-terrain, Truck-mounted, Pick-and-carry cranes ...), and the
**capabilities** that describe them, each in one fixed unit (a crane's rated capacity in tonnes, a
manlift's working height in metres). It takes in all 15 Annexure-21 types and all of Plum's
categories.

**Recommendation:** accept it as version 1. It is data, not code: adding a type or a capability later
needs no programming. Please check especially:

- the crane and manlift types;
- which classes are hired to customers (marked "Hired" in section 5). Are trucks or generators ever
  hired?
- who at PBL should own the structure from here - the Fleet Equipment Master owner?

### Q15. A requirement can ask for a combination of machines

A trailer on site is a prime mover plus a bed; hydraulic axles need a power pack. These are separate
machines in any master, but the customer's need is one thing.

**Recommendation:** a requirement asks for a number of **units**, and a unit is one machine or a
fixed combination - for example "2 units, each: 1 prime mover (at least 55 t combined weight) + 1
low-bed trailer (at least 40 t payload)". Most requirements will be a single machine. This replaces
Q12's "two requirements".

### Q16. How Plum's data comes in

Three routes, and they combine:

- **A. Plum improves its master** - adds type, model and capability fields in our units. Best, but
  depends on the Plum vendor.
- **B. Our transformer.** We read Plum's report (and its interface, when there is one), and map each
  machine into our structure using mapping tables we keep: Plum category and model to our class,
  type and model; units converted; every doubtful value flagged for Fleet to fix, never silently
  corrected. Works without any change in Plum.
- **C. Our structure becomes primary.** Fleet maintains machines in our system, and Plum receives
  them through a transformer the other way (our class and type combined into its category, capacity
  converted to its unit).

**Recommendation:** B now, ask Plum for A in parallel (section 21 gives the list), and move to C when
Hiring assignment runs on our platform. The transformer itself is the **next** package; this one
builds the structure it transforms into.

### Q17. One package or two?

**Recommendation:** one package, one migration (`20260908_0041`): the equipment structure and the
requirements that use it. The structure's only user today is the requirement, and its contents are
data that can be corrected after Q14 without holding the code. If you would rather review the
structure on its own first, it splits cleanly into two packages with slots `0041` and `0042`.

---

## 3. Authority and required reading

What this design relies on, per PBL's internal working instructions "Reading discipline". Each was read in full unless a
section is named.

- `docs/agent/contracts/work-order-resource-requirement-contract.md` (`WRR-001`, APPROVED)
- `docs/agent/contracts/resource-master-reference-contract.md` (`RMR-001`, APPROVED)
- `docs/agent/contracts/resource-planning-assignment-contract.md` (`RPA-001`, APPROVED)
- `docs/agent/contracts/eligibility-assignment-contract.md` (`ELA-001`, APPROVED)
- `docs/agent/contracts/work-order-contract.md` - Slices 7C, 7D Parts 1-4 sections
- `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` - FROZEN; must stay
  byte-identical (since 8 October 2026, but for the owner-approved dated amendment CS-04 part 1 appended at
  its end; its current SHA-256 is in `docs/continuity/NEXT_STEPS.md`)
- `docs/continuity/PF_1A_E3_INTEGRATION_CLOSURE_AND_WAY_FORWARD_2026-09-07.md` - "Recommended next
  work", Track 2
- `docs/agent/architecture/EXTERNAL_DEPENDENCY_REGISTER.md` - Plum Equipment Master row
- `docs/agent/architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` - Equipment Master, Resource
  Catalogue, Requirement, Availability, Assignment, Eligibility rows
- `docs/agent/architecture/MODULE_DEPENDENCY_AND_DELIVERY_WAVES.md` - Waves 1 and 2
- `docs/agent/pf-1f-hr/PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` - section headings and the boundary
  architecture: the pattern this design follows
- `docs/reference/erp-source-extracts/TOOLS_AND_ASSET_ANNEXURES_EXTRACT.md` and
  `FIELD_ANNEXURES_INDEX.md`; the FRS `.docx` itself for Annexure-20 and Annexure-21 and its embedded
  workbooks
- Plum "Own Vehicle Complete Information Report", 24 September 2026 (Q11) - outside the repository
- `docs/agent/FUTURE_SLICES.md` - 7B, 8A, 8B
- `docs/agent/DEFERRED_REQUIREMENTS.md` - "Operators' pay", "Contracts are independent of each
  other", "Line-detail locks and a dependency"
- `docs/agent/slices/slice-7d-part-4-remaining-billing-terms.md` - answers 21 and 23, decision 28
- `docs/uat-source/PBL_CRM_UAT_DATA_SHEET.md` - the quoted lines
- ADR-007, ADR-013, ADR-017, ADR-018, ADR-023, ADR-030, ADR-032

---

## 4. The equipment structure

Four levels. This package builds the first three; the fourth comes with the transformer.

```text
Class        what the machine is for            Crane, Aerial Work Platform, Prime Mover, Trailer ...
  Type       how it is built, within the class  Crawler, All-terrain, Truck-mounted, Pick-and-carry
Capability   what it can do, in a fixed unit    Rated capacity (t), Working height (m), Axle lines
Model        a maker's model, with its rated    SANY SCC1000A: Crane / Crawler / 100 t     (next package)
             capabilities
Machine      one physical machine               class, type, model, actual capabilities,  (next package)
             registration, status; its fitted parts (a crane's carrier) are its children in the
             component hierarchy
```

A machine's parts are not a level of this structure. A crane's carrier and upperworks are its fitted
parts, and boom inserts, counterweights, hook blocks and tools its detachable kit, all recorded as the
machine's children in the component hierarchy (`DEFERRED_REQUIREMENTS.md`, "Asset component hierarchy", recorded 24 September
2026), built with the machine records. The part classes they need are added to the Equipment Reference
then, as an additive change (section 22).

Rules that make it better than a flat category list:

- **Every capability has exactly one unit**, fixed by the structure. A requirement cannot say
  "80000" and mean kilograms for one crane and tonnes for another. The transformer converts.
- **Each class says which capabilities apply**, and which one is its **key** capability - the one
  planners compare first (rated capacity for a crane, working height for a manlift).
- **Codes never change; labels may.** Nothing is deleted: a type or capability is retired, and
  anything saved with it keeps it.
- **The structure is versioned.** Version 1 is loaded by this package's migration, with its source
  recorded. Later versions add, retire or relabel.
- **Known words map to it.** An alias table records what other systems and people call things:
  Plum's "CRANES" and "TRAILERS", Annexure-21's "Farana" and "Puller", trade words such as "Hydra".
  The transformer uses it to read Plum; the requirement form uses it to suggest a class from the
  line's own category text ("Crane").
- **Which business lines use a class is recorded with the class** (Hiring, Transportation, or
  neither), so one structure serves both modules and holds light vehicles and workshop assets without
  their appearing where Operations plans hiring (Q14). A class can serve both lines.

It lives in a new platform module, **Equipment Reference**, the counterpart of `hr_reference`:
canonical, provider-neutral, and never showing a Plum field to anything that consumes it.

---

## 5. Version 1 of the structure (agreed, Q14)

Built from Annexure-21, Plum's categories and models, and the machines in the FRS workbooks. "Key"
marks the capability planners compare first. "Used by" is the business lines that deploy the class
to customers.

| Class | Used by | Types | Capabilities (unit) | Takes in |
| --- | --- | --- | --- | --- |
| **Crane** | Hiring | Crawler; All-terrain; Truck-mounted telescopic; Rough-terrain; Pick-and-carry; Knuckle-boom loader; Mobile tower; Derrick | **Rated capacity (t)**, main boom length (m), maximum tip height (m) | Plum CRANES, CRANE; Annexure-21 Telescopic, Mobile Tower and Crawler Cranes, Derrick, Farana, Palfinger; "Hydra" |
| **Aerial Work Platform** | Hiring | Telescopic boom; Articulating boom; Scissor; Vertical mast | **Working height (m)**, platform capacity (kg), horizontal outreach (m) | Plum MAN LIFTS; Annexure-21 Manlifts |
| **Forklift** | Hiring | - | **Rated capacity (t)**, lift height (m) | Plum FORK LIFT; Annexure-21 Forklift |
| **Excavator** | Hiring | - | **Operating weight (t)**, bucket capacity (m³) | Plum Excavator; Annexure-21 Excavator |
| **Prime Mover** | Transportation | Tractor unit; Ballast tractor (puller) | **Gross combination weight (t)**, axle configuration (4x2, 6x2, 6x4, 6x6, 8x4, 8x8) | Plum TRAILERS; Annexure-21 Prime Movers, Puller |
| **Trailer** | Transportation | Low-bed; Semi-low-bed; Flatbed; Extendable | **Payload (t)**, deck length (m), axles (count) | Plum TRAILER BED; Annexure-21 Trailer Bed |
| **Modular Hydraulic Trailer** | Transportation | Towed modular; Self-propelled (SPMT) | **Axle lines (count)**, payload (t) | Plum HYDRAULIC AXLES; Annexure-21 Hydraulic Axles |
| **Power Pack** | Transportation | - | Power (kW) | Plum Power Packs |
| **Truck** | Transportation (GTA) | - | **Payload (t)** | Plum TRUCKS |
| **Generator** | Neither | - | Rated output (kVA) | Plum Genertor |
| **Light Vehicle** | Neither | Two-wheeler; Four-wheeler; Van | - | Plum TWO WHEELER, FOUR WHEELER, VAN; Annexure-21 Two Wheelers, Four Wheeler |
| **Workshop Asset** | Neither | - | - | Plum GARAGE ASSETS, GENERAL |

Which lines use each Transportation class is recorded now so the structure is complete; Transportation
confirms it when that module is designed.

Units: tonne, kilogram, metre, cubic metre, kilowatt, kilovolt-ampere, count; and a fixed list for
axle configuration. Annexure-21's "Telescopic Cranes" maps to the class only: it covers all-terrain,
truck-mounted, rough-terrain and pick-and-carry cranes, so the type has to come from the model.

---

## 6. Getting Plum's data in: the transformer and its phases

Designed now, built in the next package (Q16). It follows ADR-032's pattern for HR.

```text
Plum report / interface  ->  source binding (adapter-owned)  ->  mapping + unit conversion + flags
                                                              ->  canonical Model and Machine records
                                                              ->  consumers (Requirement, Availability,
                                                                  Assignment, Eligibility)
```

- **Source binding.** Each machine keeps which Plum row it came from, the import version and the few
  raw values it was built from - owned by the adapter, never shown to consumers. Plum's PAN and
  insurance-policy numbers are not copied at all.
- **Mapping tables we keep:** Plum category to class (from the alias table); Plum model and
  maintenance-schedule type to our Model; each Model to its type and rated capabilities.
- **Unit conversion per class:** Plum's trailer and axle capacities are kilograms, crane capacities
  tonnes; the transformer converts into the structure's one unit.
- **Flags, never silent fixes.** A crane at "80000", a bed with no payload, "PULLER" in a number field:
  the machine is imported with a data-quality flag for Fleet to correct at the source.
- **Fitted parts.** Where Plum has a superstructure and a carrier as two rows, the transformer records
  one Machine - the crane - with the carrier as its fitted part in the component hierarchy
  (`DEFERRED_REQUIREMENTS.md`, "Asset component hierarchy"): a child of the machine, not a second machine. Plum's per-vehicle tools list
  comes in the same way, as the machine's detachable kit.

Authority by phase, written down so no two systems claim the same fact:

| Phase | Machine identity, status, statutory documents | Class, type, model, capabilities |
| --- | --- | --- |
| 1 - now to Hiring assignment | Plum, through the transformer | **The platform's Equipment Reference**; Fleet curates the mappings |
| 2 - Hiring assignment on our platform | **The platform**; Fleet maintains machines in our system | The platform |
| 3 - Plum follows | The platform; Plum ingests through the reverse transformer | The platform |

---

## 7. What a Resource Requirement records

One requirement belongs to exactly one Work Order line; a line may have several (Q7). Work Order lines
have no active or cancelled status of their own: every line is `HANDOFF_CREATED` until amendments can
be applied (`D-07`).

A requirement asks for **a number of units, over a period**. The data holds a unit as one or more
**items**, so that Transportation's combinations (prime mover + bed) fit later without reshaping the
tables; **in this slice a requirement has exactly one item**, and the screen calls the number
"Number of machines" (Q15). A rule such as "one prime mover takes at most one bed" attaches to the
items when Transportation needs it. A Work Order requirement may only use a class Hiring uses.

### The requirement

| Field | Meaning | Rule |
| --- | --- | --- |
| `requirement_public_id`, `requirement_reference` | Identity; `RR-000001`, derived from the identity as `CO-` and `WO-` are (ADR-007) | |
| `work_order_public_id`, `work_order_code`, `work_order_line_public_id`, `work_order_line_number`, `source_offer_line_public_id`, `account_public_id` | Which line, and its traceability to the offer line | Copied once at creation. All immutable facts about the line, so copying them is the "approved immutable reference" ADR-017 permits. A foreign key to the line guarantees it exists |
| `units_required` | How many units | Whole number, at least 1 (Q2) |
| `required_from`, `required_to` | When the units must be on site | `required_from` required; `required_to` blank means until the line ends. Both inside the contract and the line's own dates (Q8) |
| `crew_operators_required`, `crew_helpers_required` | People needed on site, for the whole requirement | Whole numbers, zero allowed; start from the Work Order's Part 4 numbers (Q4) |
| `crew_notes` | Licences and skills needed, in words | Optional; up to 2000. Structured licence checks belong to Eligibility (`ELA-001`) |
| `priority_code` | `NORMAL` or `URGENT` | Sorts the planning list |
| `planning_notes` | Site access, tide windows, anything planning must know | Optional; up to 4000 |
| `requirement_status_code`, `requirement_version`, cancellation fields | Section 9 | |
| `create_request_key` | A double-click or retry creates one requirement, not two (ADR-023) | UUID from the form; unique |
| `created_by`, `created_at`, `updated_by`, `updated_at` | | |

### Each item in a unit

| Field | Meaning | Rule |
| --- | --- | --- |
| `item_number` | 1 in this slice | Exactly one item per requirement for now |
| `equipment_class_code` | Crane, Aerial Work Platform, ... | Required; an active class used by Hiring |
| `equipment_type_code` | Crawler, Articulating boom, ... | Optional - blank means any type in the class; must belong to the class |
| `equipment_specification` | Anything the structure does not hold: fly jib, attachments, counterweight | Optional; up to 1000 |

A "how many of this item per unit" field is deliberately not added: with one item it is always 1, and
it can be added later with a default of 1 without touching existing rows.
| capability minimums | For each capability stated: the least value (or, for axle configuration, the value) | Only capabilities that apply to the class; one per capability; greater than zero; the unit is the capability's and cannot be sent |

### Read from the Work Order, not copied

Read live on every request through the `work_orders` module's own query functions: the line's scope
description, category text, quantity and unit; the line's site (7C); the billing basis of the terms
in force on `required_from` (7D), and whether they charge a night shift; the Work Order's crew
numbers in force on `required_from` (Part 4); the contract period, extensions and gaps (Part 3); the
line's own dates. No rate, amount or commercial term is copied (`WRR-001`).

### Warnings, computed on every read

Never a refusal.

```text
SITE_NOT_RECORDED              the line has no site yet (7C)
OUTSIDE_CONTRACT               the dates no longer fit the contract, a gap, or the line's own dates (Q8)
CREW_DIFFERS_FROM_WORK_ORDER   operators or helpers differ from the Part 4 numbers (Q4)
KEY_CAPABILITY_NOT_STATED      an item gives no value for its class's key capability
```

---

## 8. How it uses the site, the contract period and the crew numbers

- **Site.** Read live from the line's detail; the line's site is the requirement's site. Events record
  the site public id at the time of the change.
- **Contract period.** On save, the dates are checked with
  `contract_period_rules.classify_date_against_contract` - the rule Slice 7D Part 3 built for this
  reuse - against the contract and its gaps, then against the line's own dates. Refusals name the
  dates, as Part 3's do. A bound not recorded is never treated as broken. Afterwards, only a warning.
- **Crew numbers.** A new requirement starts with the Part 4 numbers in force on `required_from`;
  "Equipment only" starts at zero. Never pay terms.
- **Suggested values.** A read-only defaults route returns the above for a line, plus a suggested
  class when the line's category text matches an alias ("Crane" suggests Crane). The server owns what
  the defaults are.

---

## 9. Statuses, partial fulfilment, splitting and cancellation

```text
OPEN        recorded; planning may use it. The only open state this slice can reach
CANCELLED   ended by Operations with a reason. Final; kept, never deleted
```

Reserved for later slices, not accepted by this one's constraint: `PARTLY_FULFILLED`, `FULFILLED`,
`COMPLETED` (Assignment, 8A).

- **Partial fulfilment.** When Assignment exists it owns the assigned count, and "remaining" is
  `units_required` minus it (`RPA-001`). Nothing stored here pretends to it.
- **Splitting.** Several requirements per line (Q7). No split button.
- **Changing.** Whole replacement of the requirement and its items while `OPEN`, checked against
  `expected_requirement_version` (`409` on a mismatch); version up by one; one event naming what
  changed. An identical save records nothing.
- **Cancelling.** From `OPEN` only; reason required; nothing is reserved yet, so nothing to release.
  `WRR-001`'s rule is recorded for later: cancellation releases uncommitted reservations, and a
  committed assignment needs its own explicit release. No un-cancel.
- **Closed Work Order.** Refuses every write, as 7C and 7D do.

---

## 10. Permissions

```text
RESOURCE_REQUIREMENT_READ    the roles that can view Work Orders (WORK_ORDER_READ)
RESOURCE_REQUIREMENT_WRITE   ADMIN, OPERATIONS_USER   (Q6)
EQUIPMENT_REFERENCE_READ     the roles that can view Work Orders
```

New codes, seeded by the migration and added to `POST_BASELINE_ROLE_PERMISSION_MATRIX`. The structure
has no write permission yet: in version 1 it changes only by migration. A maintenance screen for its
owner (Q14) comes later, with its own permission.

---

## 11. Routes

```text
GET  /api/equipment-reference/structure              EQUIPMENT_REFERENCE_READ   classes, types,
                                                     capabilities, units and aliases, current version
GET  /api/resource-requirements                      READ   planning list: filters work order, line,
                                                     status, class; urgent first, then earliest start
GET  /api/resource-requirements/defaults             READ   ?work_order_line_public_id=
GET  /api/resource-requirements/{public_id}          READ
POST /api/resource-requirements                      WRITE  201; 404 unknown line; 422 validation
PUT  /api/resource-requirements/{public_id}          WRITE  200; 404; 409 version; 422
POST /api/resource-requirements/{public_id}/cancel   WRITE  200; 404; 409 version; 422
```

`/defaults` is registered before `/{public_id}`. Unknown request fields are refused with `422`. All
seven are new, so they go in `POST_BASELINE_NEW_ROUTES`, never the frozen baseline.

---

## 12. Events

```text
ResourceRequirementCreated | ResourceRequirementUpdated | ResourceRequirementCancelled
source_module = resource_requirements, record_type = resource_requirement
payload: requirement_reference, work_order_public_id, work_order_line_public_id,
         source_offer_line_public_id, site_address_public_id (as read at the time),
         requirement_version, requirement_status_code, units_required, required_from, required_to,
         crew_operators_required, crew_helpers_required, priority_code, taxonomy_version,
         items[]: item_number, equipment_class_code, equipment_type_code,
                  capabilities[]: capability_code, value
         changed_fields[]
```

No free text (specification, notes, reason) and no amounts. The structure records no events in
version 1: only a migration changes it.

---

## 13. Data, modules and migration

- **`backend/app/modules/equipment_reference/`** - the canonical structure (section 4). Tables:
  `equipment_taxonomy_version`, `equipment_class`, `equipment_class_business_line` (class, `HIRING` or
  `TRANSPORTATION`), `equipment_type`, `equipment_capability`, `equipment_class_capability` (applies,
  key, order), `equipment_term_alias` (term, source - Plum category, Annexure-21 or trade word -
  class, optional type). Codes are the primary keys and never
  change; each row records the version that introduced and, if any, retired it. Read through its
  service only. A `ports.py`, as in `hr_reference`, names the source-adapter interface the transformer
  will implement; nothing implements it yet.
- **`backend/app/modules/resource_requirements/`** - tables `resource_requirement`,
  `resource_requirement_item`, `resource_requirement_item_capability`. Foreign keys to
  `crm_work_order_line(id)` and to the structure's codes. CHECK constraints for every code set,
  positive numbers, non-negative crew, `required_to >= required_from`, cancellation fields present
  exactly when `CANCELLED`. The rule that a type belongs to its class, and a capability to the class,
  is enforced by the service and by composite foreign keys where the structure allows. Row lock on
  update and cancel. It never writes a Work Order table, and reads Work Order facts only through
  `work_orders` service functions (`list_work_order_lines`, `list_work_order_line_details`,
  `list_work_order_billing_terms`, `get_work_order_contract_period`) - not repository imports, the
  gap the ADR-030 review recorded against `leads` and `opportunities`.
- **No `crm_` prefix** on any new table: none is CRM's.
- **Migration `20260908_0041_resource_requirement_foundation`** (confirmed; one package, Q17): all ten
  tables, version 1 of the structure with its business lines and aliases, three permission codes and
  their grants. Empty-database upgrade and downgrade checked.

---

## 14. Screens

- **Work Order page:** a "Resources needed" section, in the Jump-to row, listing each line's
  requirements - reference, units x items in one line ("2 x Crawler crane, at least 220 t"), dates,
  status, warnings - with "Add a requirement" beside each line for those who may write. Its own
  component; the Work Order page grows by a few lines.
- **New requirement page** `/resource-requirements/new?work_order_line=...`: filled from the
  defaults, with the line's facts shown beside the fields: number of machines, then class (Hiring's
  only), type ("Any"), and the class's capabilities with their units, key first. No combinations in
  this slice. Messages below the Save button.
- **Requirement page** `/resource-requirements/:id`: view, change, cancel (reason asked), warnings.
- **Planning list** `/resource-requirements`, in the sidebar: open requirements, urgent first, then
  earliest start, filterable by class.

---

## 15. Differences from `WRR-001`'s minimum list (recorded per ADR-013)

| `WRR-001` item | This slice | Why | When it closes |
| --- | --- | --- | --- |
| Required resource category/type | Class, type and capability minimums from the platform's Equipment Reference | Standing rule; ADR-037 (Q13) | - |
| Skill/licence/certification requirements | `crew_notes` text | Licences and their evidence belong to Eligibility (`ELA-001`), which does not exist | Eligibility foundation |
| Work Order version, line version | Work Order and line public ids only | A Work Order has no versions until amendments are applied (`D-07`) | With `D-07` |
| Site/location reference | Read live from the line, recorded in events | The site is the line's; copying it would let the two disagree | - |
| Correlation/source event reference | The requirement's own business events | No separate column is needed to find them | - |
| Billing basis where relevant | Read live and shown | Commercial terms are referenced, not copied | - |

---

## 16. Draft ADR-037 (for Q13)

> **ADR-037: Canonical platform data structures; external masters enter through transformers**
>
> Decision: the platform designs its own canonical structure for each kind of master data it depends
> on, to the standard the domain needs, and does not inherit the structure of Plum or any
> other existing system. Where the existing system holds the data today, an adapter-owned
> transformer maps it into the canonical structure - converting units, combining or splitting fields,
> and flagging doubtful values rather than silently correcting them. Authority is stated per phase,
> so no two systems claim the same fact. When the platform becomes primary, a reverse transformer
> feeds the existing system in whatever shape it still needs.
>
> First application - equipment: the Equipment Reference (class, type, capability with one unit each,
> model, machine) is platform-owned, serves both Hiring and Transportation, and is owned on the
> business side by Fleet's Equipment Master owner. Phase 1: Plum remains the source of machine identity, status and
> statutory documents; the platform owns classification. Phase 2: the platform is primary for
> machines as well. Phase 3: Plum ingests from the platform.
>
> Relationship: follows ADR-032's pattern for HR and ADR-030's direction of capability moving out of
> Plum. Refines `RMR-001`'s statement that Plum's Equipment Master is authoritative for owned
> equipment: that remains true for machine identity, status and statutory documents in Phase 1; the
> structure is the platform's. `RMR-001` gains a short note; its text is not rewritten.

Documents updated with it: `ARCHITECTURE_DECISIONS.md`, `RMR-001` (a note), `CONTRACT_REGISTRY.md`,
`EXTERNAL_DEPENDENCY_REGISTER.md` (Plum Equipment Master row), `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`
(Equipment Master and Resource Catalogue rows), and the PBL's internal working instructions ADR index.

---

## 17. Not in this slice

The transformer, the Model and Machine records, any Plum import or reverse feed; the component
hierarchy of fitted parts and detachable kit, and the part classes it needs (`DEFERRED_REQUIREMENTS.md`, "Asset component hierarchy", with the machine records); a maintenance screen for the structure; availability, reservation, assignment or fulfilment counts; Eligibility checks;
Market Hire or own-versus-hired (`MHA-001` is `PROPOSED`); automatic requirements; a release gate
(7B); a split action; alerts. The billing cycle belongs to each machine at assignment (8A).

---

## 18. Tests and checks

- **Equipment Reference:** version 1 loads exactly as section 5, business lines included; every
  class's key capability applies to it; every alias points at an existing class and a type of that
  class; retired rows stay readable; the structure route has no write counterpart.
- **Requirements**, new `backend/tests/test_wrr001_resource_requirements.py`: create requirements
  with suggested values and events; several per line; validation (zero units, no item, two items, a
  class Hiring does not use such as Prime Mover or Generator, a retired class, a type of another
  class, a capability that does not apply, a capability twice, a unit sent by the caller, a value of
  zero,
  dates after each other or outside the contract, a gap or the line's dates, unknown fields, another
  Work Order's line, a Closed Work Order); permissions (read for every read role; write refused for
  Sales, Finance and Management); `409` on a stale version for change and cancel; cancel needs a
  reason and is final; a repeated `create_request_key` returns the first requirement (since 8 October 2026
  only for the very same request: TB-1 TB1-102 part b); each warning
  appears and clears; the class suggestion from the line's category text; event payloads carry no
  free text or amount; the frozen handoff file's hash and the handoff response keys are unchanged.
- **Route guard:** the seven routes pinned in `POST_BASELINE_NEW_ROUTES` with exact permissions.
- **Frontend:** pure-rule tests for the form state (items, capabilities by class), route-table tests
  for the three new URLs; the typecheck, test and build gate.
- **Test data:** a `create_resource_requirement` builder and a scenario with a crane requirement and a
  manlift requirement on different lines. Cleanup deletes capability rows, items and requirements owned by the run's
  Work Order lines, and their events, before the lines themselves (TE-4's downward cascade). The
  structure is reference data and is never cleaned up. No row of Plum's report is copied into tests.
- **E2E**, one spec: add a requirement to a seeded line, see it on the Work Order page and the planning
  list, cancel it; a read-only user sees no Add button. Run with `pwsh`.
- **Full backend regression, the frontend gate and E2E**, then independent review, at most three rounds.
  Then your screen check, with the steps in the chat.

## 19. Shared files this slice touches

`backend/app/main.py` (two routers), `frontend/src/routes.tsx`,
`backend/app/modules/authorization/contract.py`, `backend/tests/fixtures/post_baseline_tightened_routes.py`
(the one that fails silently on a bad merge - read it by eye after any merge), the sidebar,
`backend/tooling/smoke_data/cleanup.py`, and - if Q13 is accepted - the architecture documents in
section 16. No CRM lane is known to be active on them now.

## 20. What would stop implementation and come back to you

- An answer that needs a Work Order table to change - that is Work Order work, not this slice.
- Any need to change the frozen handoff contract or its output.
- Plum's vehicle type master arriving with a structure that version 1 cannot take in without a new
  level.

## 21. What Plum's report shows

From the owner's export of 24 September 2026 (681 rows, 32 columns). Counts are of active machines in
the eight categories that hold machines deployed to customers by Hiring or Transportation (289).
Recorded for the transformer package and for Plum (route A in Q16).

- **Categories are coarse.** One "CRANES" for crawler, all-terrain, truck-mounted and pick-and-carry
  cranes alike; "TRAILERS" means the prime movers; no Farana, Hydra, Prime Mover or Puller category.
  The maintenance-schedule type ("SANY-SCC1000A", "XCMG QAY 220 SUPER") is the most consistent model
  key, and is what the transformer will map from.
- **One field, many units.** `Capacity` is tonnes for cranes and forklifts, kilograms for manlifts,
  prime movers and axles, and unclear for excavators ("370"). `LoadCapacity` repeats it in every row
  where both are filled (658 of 681).
- **Values that break the pattern:** two active cranes at 48,620 and 80,000 (kilograms, not tonnes),
  one at 1; text in the number field ("PULLER", "230 KG", "select"); 88 of 93 active trailer beds with
  no capacity.
- **Missing:** make on 21 of 69 active cranes; model often blank; no machine name, no HSN, and none of
  Annexure-20's validity dates (insurance, fitness, pollution, road tax, load test, permits), which
  Eligibility will need.
- **A machine and its fitted part as two records:** some cranes are registered as superstructure and
  carrier (LTM 1070, LTM 1400, XCMG QAY 220). In the platform the carrier is the crane's fitted part in
  the component hierarchy (`DEFERRED_REQUIREMENTS.md`, "Asset component hierarchy").
- **Stray values:** "CRANE" beside "CRANES", one row with no category, and a few owners other than
  PBLTCPL.

**What to ask Plum for (route A):** a type field (or our type code), a model key, capabilities in our
fixed units, the Annexure-20 validity dates, and a link from a crane's superstructure to its carrier, so
the transformer can record the carrier as the crane's fitted part.

---

## 22. Implementation record (24 September 2026)

Built on `hiring/wrr-001-resource-requirements` in worktree `<a separate worktree>`, from the
design commit `4b1aecd` (itself on `main` at `3e22136`). Migration `20260908_0041`, parent
`20260908_0040`. ADR-037 recorded with the document updates section 16 lists.

### What exists now

```text
backend/alembic/versions/20260908_0041_resource_requirement_foundation.py   ten tables, version 1, three permissions
backend/app/modules/equipment_reference/     contract, ports (the transformer's interface), schemas,
                                             repository, service (structure, lookups, class suggestion), routes
backend/app/modules/resource_requirements/   contract, schemas, repository, service, routes
backend/app/modules/work_orders/             one read-only service function, get_work_order_line_reference
backend/app/modules/authorization/contract.py  RESOURCE_REQUIREMENT_READ / _WRITE, EQUIPMENT_REFERENCE_READ
backend/tooling/smoke_data/                  create_resource_requirement builder, scenario
                                             work-order-resource-requirements, a sixth core-bundle record,
                                             cleanup of requirement rows and their events
frontend/src/pages/resource-requirements/    planning list, new requirement, requirement page, shared form
                                             fields, pure rules and their tests, a shared session helper
frontend/src/pages/work-orders/WorkOrderResourceRequirementsSection.tsx   "Resources needed" on the Work Order
e2e/tests/resource-requirement.spec.ts       add, see on the Work Order and the planning list, cancel; read-only view
docs/agent/contracts/resource-requirement-api-contract.md                 the routes, as built
```

### Refinements made while building (recorded per ADR-013)

None changes a business answer. Each is an implementation choice the design left open, or a detail it
needed to work.

| # | Design said | Built | Why |
| --- | --- | --- | --- |
| 1 | Create names the line (`work_order_line_public_id`) | Create names **both** the Work Order and the line; a line not on that Work Order is `404`, worded as an unknown line | Section 18's "another Work Order's line" test needs a Work Order to compare with, and a form cannot then pair a line with a Work Order it does not show |
| 2 | Read Work Order facts through four named service functions | Those four, plus `get_work_order` and one new **read-only** function, `get_work_order_line_reference` | None of the four finds a line's Work Order from the line's public id. The new function returns only what the requirement uses from it: the line's and Work Order's identity and traceability (copied once), the Work Order's status (the Closed check), the line's category text (the class suggestion), the Account, and the line's internal id for the foreign key. Everything else about the line is read through `list_work_order_lines`. It is pinned with the other post-split names in `test_te6_work_orders_service_surface.py`. No Work Order table or route changed |
| 3 | `RR-000001`, derived from the identity | A **generated column**: `'RR-' || lpad(id, at least 6 digits)` | Cannot be missing or disagree with the id, and never truncates past six digits |
| 4 | Axle configuration is "a fixed list" | A capability of kind `CHOICE` with its `allowed_values` on the capability row; the other capabilities are `MINIMUM` | Keeps section 13's seven structure tables; the database refuses a unit on a list or a list without values |
| 5 | Units: tonne, kilogram, metre, cubic metre, kilowatt, kilovolt-ampere, count | A fixed set in `equipment_reference/contract.py`, enforced by a CHECK; `COUNT` takes whole numbers only | Units are not data that changes with a version; the structure route still returns them |
| 6 | "Takes in" Annexure-21 and Plum words (section 5) | Aliases name a type where the word names one: Farana and Hydra -> pick-and-carry crane; Palfinger -> knuckle-boom loader; Crawler Cranes, Mobile Tower Cranes, Derrick; Puller -> ballast tractor; Plum's and Annexure-21's two- and four-wheelers and vans -> light-vehicle types. Telescopic Cranes and Hydraulic Axles name the class only | Telescopic cranes span four types (section 5); hydraulic axles may be towed or self-propelled. Data, correctable by a later version |
| 7 | Structure is versioned | Each requirement records the `taxonomy_version` it was last saved against; the events carry it | So a later reader knows which version's codes a requirement used |
| 8 | "Anything saved with it keeps it" (section 4) | A change may keep a class, type or capability retired since the requirement was saved, but may not newly choose one | Otherwise a retired type would block changing a requirement's dates |
| 9 | Crew starts from the Part 4 numbers | Equipment only starts at 0 and 0; an unanswered Work Order crew term suggests nothing and the form asks. `CREW_DIFFERS_FROM_WORK_ORDER` appears only when the Work Order's crew is answered | A bound not recorded is never treated as broken - the same rule as the dates |
| 10 | Suggested `required_from` | The line's own start, else the contract start, else none | Nothing else is known to start from |
| 11 | "A suggested class when the category text matches an alias" | A whole match on a class label or alias first; else a label or alias found as whole words inside the text, only when every such match names one class; only live Hiring classes | "250MT Crane" should suggest Crane; "Crane and Forklift" should suggest nothing rather than guess |
| 12 | A repeated key creates one requirement | The same key returns the first requirement, `201` with `event: null`, whatever else was sent; the same key for another line is `409`; a race on the key replays the winner | ADR-023's replay, as Slice 9D's interactions do it. **Superseded 8 October 2026** (TB-1 TB1-102 part b): only the very same request replays, with `replayed: true`; the key with any other request is `409`, so a changed form is no longer answered with the first requirement |
| 13 | Warnings "computed on every read" | Only for an open requirement; a cancelled one has none | A cancelled requirement needs no attention |
| 14 | E2E spec on "a seeded line" | A sixth record set, `resource_requirement_target`, in `core-regression-bundle`, not a fourth manifest | The existing manifest shape fits; `run-e2e.ps1` is unchanged |
| 15 | Planning list "in the sidebar" | Sidebar link **Resource Planning**; the page is titled **Resources needed**, showing Open by default, filterable by status and kind of machine | - |

### Part classes later: an additive change (owner, 24 September 2026)

The component hierarchy's part classes - boom section, hook block, counterweight, tool and the like - are
added to the Equipment Reference with the machine records, and nothing in version 1 stands in their way:

- a part class is another row in `equipment_class`, with its own types, capabilities and aliases; codes
  are free text under the same pattern, and a new version introduces them;
- a class with no row in `equipment_class_business_line` is offered to no business line, so a part class
  never appears where Operations asks for machines - the requirement form lists only classes Hiring
  deploys, and the service refuses any other;
- what a class is - machine or part - and which part classes may be fitted to which classes are new
  columns or a new table, each additive: a column with a default for the rows already there, a table
  referring to `equipment_class` by code;
- a requirement names a class by foreign key and never assumes every class is a machine it could ask
  for, beyond the Hiring check above.

### Independent review

the independent reviewer, bounded packets per `BOUNDED_INDEPENDENT_REVIEW_METHOD.md`; the owner's cap is
three rounds.

**Round 1** (tree `703312aa`, packet `17262b9d`): CORRECTION_REQUIRED, six material findings, all
corrected.

| # | Finding | Correction |
| --- | --- | --- |
| F-01 | Refresh on the requirement page kept an open change's draft but took the new version, so saving it after a `409` would silently undo the other person's change | A successful load now discards the draft, its messages and a half-confirmed cancellation; the `409` message says the draft will be discarded. No component test: the frontend has none yet (`DEFERRED_REQUIREMENTS.md`, "Frontend component-test capability") |
| F-02 | The Work Order section fetched one page of 200 and could then say a line had no requirement | It reads every page (`fetchAllRequirementPages`, tested with more than one page), and fails loudly rather than show a partial list past fifty pages |
| F-03 | The database did not check a capability value against the capability's kind, list or whole-number unit | Trigger `trg_rr_item_capability_matches_kind`, raising a check violation named `ck_rr_item_capability_matches_kind`; each case tested by a direct insert, with a counterpart that valid values pass |
| F-04 | A cancelled requirement could be stored without who cancelled it | `ck_resource_requirement_cancellation` requires `cancelled_by`; the service refuses a cancellation with no actor; both tested |
| F-05 | The request-key tests were sequential, so the race branch was untested | Two tests run two creates at once in separate sessions, held at a barrier until both have found no row: same line - one row, one event, both answered with it; different lines - one row, the other `409` |
| F-06 | `get_work_order_line_reference` returned scope, quantity and unit, which nothing uses | Removed; refinement 2 above now lists exactly what it returns and why |

Also in round 2's tree, not findings: `main` merged in (`cd9debe`, the asset component hierarchy record),
and, at the owner's request, a crane Plum holds as superstructure and carrier described as the machine and
its fitted part in that hierarchy, and part classes recorded as an additive change ("Part classes later").

**Round 2** (tree `0f879410`, packet `bcd2a99c`): CORRECTION_REQUIRED, five material findings, all
corrected.

| # | Finding | Correction |
| --- | --- | --- |
| F-07 | Moving "Needed from" kept the crew and billing facts of the first date, though crew starts from the Work Order's numbers in force when the requirement starts (Q4) | A new start date reads `/defaults` for that date: the facts beside the fields become that date's, and crew numbers the user has not typed are refilled (or emptied where the Work Order's crew is unanswered then); typed numbers are never overwritten. Save waits while that answer is on its way. On a change to a saved requirement the facts shown follow the new date; the saved crew numbers stay as they are, and a difference is warned after saving. Only the latest date's answer is applied. `formAfterLineDefaults` and `createLatestOnly` are tested |
| F-08 | The database accepted a blank or unknown canceller | `fk_resource_requirement_cancelled_by` to `app_user(public_id)` (users are disabled, never deleted); tests for no one, a blank and an unknown id |
| F-09 | Refresh left a typed cancellation reason behind, and the reload rule had no test | The requirement page's state is one reducer (`resourceRequirementDetailState.ts`); a load resets every draft - change form, the tried date's facts, reason, confirmation, messages - while installing the new version, tested, and the test shown to fail when a load keeps the drafts |
| F-10 | Planning-list answers arriving out of order could show one filter's rows under another's controls | Each request takes a ticket (`createLatestOnly`); only the latest answer is applied, tested with answers resolving out of order |
| F-11 | The acceptance and continuity records gave stale counts and called checks green on the candidate before its full runs finished | The records now say which tree each result was measured on, and record the candidate's full regression and E2E only once finished |

**Round 3** (tree `b321698a`, packet `9a7e78b0`): CORRECTION_REQUIRED, three material findings, all in how
the screens handle answers that arrive late, out of order or not at all; all corrected. Round 3 is the
last within the owner's cap: a fourth round needs the owner's yes.

| # | Finding | Correction |
| --- | --- | --- |
| F-12 | A failed read of the Work Order for a new start date re-enabled Save with the earlier date's crew and facts; the change form did not wait for the read at all | Both forms keep whether the facts for the date on the form are in (`DateFacts`: current, loading, failed, each tied to the request awaited). Save waits while they load; after a failure it stays refused, says why beside the button, and offers "Read the Work Order again". Only the awaited answer counts. Tested in the reducer and the date-facts rules, including a failed read and a stale answer |
| F-13 | An older Refresh answering last could put an older version back and wipe a draft opened on the newer one; so could a load asked before a save or cancellation | Loads are numbered; the reducer installs only the answer to the load it awaits, and a save or cancellation - which installs a newer version itself - leaves no load awaited. Tested with answers out of order, and across a save and a cancellation; the tests fail when the ticket check is removed |
| F-14 | The planning list's session-change reload used the first render's filters, and signing out did not make an answer still on its way stale | The list's loading lives in a controller (`createPlanningListController`) that holds the filters itself, so every reload asks for the filters the controls show, and takes a ticket before it looks for a session. Tested: a reload after changing filters, an answer arriving after sign-out (the test fails when the ticket is taken after the session check), and answers out of order |

The reviewer asked for component tests for these. The frontend has none yet (`DEFERRED_REQUIREMENTS.md`,
"Frontend component-test capability"), so the rules were moved out of the components into pure code that
is tested, and each test was shown to fail when the rule it names is broken. The components now only
start requests and hand their answers to that code.

**Round 4** (tree `17b9499f`, packet `0e6cfd73`), run on the owner's yes: CORRECTION_REQUIRED, three
material findings, again in the screens' handling of answers; all corrected. A fifth round needs the
owner's separate yes.

| # | Finding | Correction |
| --- | --- | --- |
| F-15 | Typing either crew number stopped both from following a new start date | Each number is the user's own only once typed (`CrewTouched`, `crewTouchedAfterEdit`); `formAfterLineDefaults` refills the other from the new date, and clears it where that date's crew is not answered. Tested both ways round, and that a typed number stays typed while other fields are edited |
| F-16 | While a new filter's request was pending, the table still listed the previous filter's rows under the new controls | What the list shows is one pure rule, `planningListView`: the moment a request starts, the previous rows go and the page shown is the one asked for. Tested with a request that never answers |
| F-17 | After a failed read of the date's facts, the refusal was copied into the save message and could outlive a successful retry; Save could still be pressed | Save is disabled unless the facts for the date on the form are in (`dateFactsAllowSave`); the reason beside the button comes from the facts themselves, and a new read - a retry or a new date - clears any earlier save message. Tested: failure, retry, success leaves no refusal behind |

Each new test was shown to fail when its rule is broken: six mutations, one or two per finding, all caught.

**Round 5** (tree `1d85ad9a`, the branch's commit `7dea3f7`; packet `372f4dc5`), run on the owner's yes and
scoped to round 4's corrections and anything they could have broken: **ACCEPTED**, no findings. The
reviewer's residual uncertainty: the E2E suite did not complete on this tree (the host short of memory),
and the frontend has no component tests; a completed E2E run, or component tests later, would add
integration assurance.

**After acceptance.** The owner's screen check (25 September) found the **Type** box out of line with the
fields beside it. The correction is layout only, in `ResourceRequirementFormFields.tsx`: each field grid
aligns its fields to the top instead of stretching them, and the key capability's hint moves beneath its
box. No rule, request or state changed. It is the only change to code since the accepted tree, and the
owner decided on 25 September that it needs no further review round.

### Tests and checks

Recorded in `docs/agent/acceptance/wrr-001-resource-requirement-foundation-acceptance.md`, with the
counts measured on this tree, and in the continuity note
`docs/continuity/WRR_001_RESOURCE_REQUIREMENT_FOUNDATION.md`.
