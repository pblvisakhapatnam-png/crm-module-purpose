# ERT-1 Plum machines into the Equipment Reference - design proposal

Status: **Design agreed, 25 September 2026. Built the same day** - see section 20, the implementation
record, for what exists and every refinement made while building. Every question is answered - all as
recommended, with four comments from the owner that refine the design (section 1). The comments are
applied throughout; sections 5A, 5B and 19 are theirs.

Hiring lane (Track 2). Worktree `<a separate worktree>`, branch
`hiring/equipment-reference-transformer`, based on `main` at `b5603e5` (WRR-001 merged). Migration slot
`20260908_0042`, confirmed (Q11). Foundation Slice Mode: the shape is built properly, the screens
minimally.

WRR-001 built the platform's **Equipment Reference** - classes, types and capabilities, each capability
in one unit - and ADR-037 settled that Plum's machines enter it through a transformer the platform owns
(route B). This package is that transformer, and the two levels it fills: **Models** and **Machines**.

In plain words: the Fleet Admin uploads Plum's vehicle report; the platform shows what would change and
every doubtful value, and the Fleet Admin confirms. Each machine is then described in the platform's own terms - a
**crawler crane, SANY SCC1000A, 100 t** rather than "CRANES, capacity 100" - and planning (8A) can
choose machines against the requirements WRR-001 records. Nothing in Plum changes. Plum stays the source
of each machine's identity and active status, **as corrected by the Fleet Admin** where Plum's values are
mixed or wrong (section 5B); facts the job needs and Plum does not hold are entered on the platform
(section 5A); how machines are classified and described is the platform's (ADR-037, Phase 1).

"Fleet Admin" in this document means whoever holds the permission to manage equipment: **Admin, until a
Fleet Admin role exists** (section 1, comment 1).

---

## 1. Owner decisions (25 September 2026)

### Answered

| # | Question | Answer |
| --- | --- | --- |
| Q1 | How the report comes in | **As recommended.** Upload, preview, confirm |
| Q2 | Who does it | **Admin**, not a new Fleet role - see comment 1 |
| Q3 | Which machines | **As recommended** |
| Q4 | Models | **As recommended.** The Fleet Admin maps each Plum model name once |
| Q5 | Capacities | **As recommended.** From the model; Plum's figure is a check. Comment 3 adds how a mixed or wrong figure is dealt with |
| Q6 | Crane halves | **As recommended** |
| Q7 | Prime mover and bed | **As recommended** |
| Q8 | What else Plum holds | **As recommended.** Comment 2 adds the facts Plum does not hold |
| Q9 | Statutory validity dates | **As recommended**: with the Eligibility foundation. Under comment 2, dates Plum cannot give are entered by the Fleet Admin |
| Q10 | One package or two | **As recommended.** ERT-1 now, ERT-2 for the kit. No tools report is needed - there is none: see comment 5 |
| Q11 | Migration slot | **`20260908_0042`** |
| Q12 | Crew qualifications | **As recommended.** An Eligibility foundation package goes on the roadmap before 8B (`FUTURE_SLICES.md`, `DEFERRED_REQUIREMENTS.md`) |

### The owner's comments

**1. Admin, for now (Q2).**

> Right now Admin can be the user to set up equipment and map to Plum equipment. The job of setting up
> equipment will eventually rest with one or two responsible people who may not be in day to day
> operations. So Admin is appropriate - later we may have someone called a Fleet Admin, who will be
> responsible for this job.

No new role. The permission to manage equipment, `EQUIPMENT_REFERENCE_MANAGE`, is granted to Admin. A
Fleet Admin role later is given the same permission by a grant, with no code change.

**2. Build for the job, not for what Plum holds.**

> We need not be constrained by what Plum has or can give. We need to build something that is
> appropriate to the job at hand and if Plum cannot provide that data, then the approach is to take
> whatever Plum can provide and then ask the Fleet Admin to obtain the remaining data and input into
> the system. This approach is for additions to the database.

A machine arrives from Plum with what Plum holds; the Fleet Admin then completes what the job needs and
Plum does not hold. Section 5A.

**3. Mixed or wrong values are split or reassigned in the transformation.**

> If Plum data has disparate information in one field or wrong information in fields, during the
> transformation, that data needs to be split and / or reassigned as appropriate. Again, the Fleet
> Admin will own this responsibility.

The Fleet Admin records how each such value is read - once for a value wherever it appears, or once for
one machine's field - and the transformer applies it on every import. Section 5B.

Comments 2 and 3 refine ADR-037, which had Plum's facts never edited on the platform. The refinement
is drafted in section 19 and recorded when this package is built.

**4. Equipment documentation.**

> Finally, there needs to be a provision to attach links to Equipment documentation - load charts and
> the like - to the assigned equipment. This can be set up whenever it is appropriate.

It was not recorded; it is now, in `DEFERRED_REQUIREMENTS.md` ("Equipment documents"). Not in ERT-1.
The models and machines ERT-1 creates are what those documents will be attached to.

**5. Tools (the same day, on Q10's request for a "tools report").**

> I do not understand what you mean by Tools Report. Anything that is of the nature of a fixed asset
> associated with and specific to an equipment is in the equipment list I shared. There will be other
> tools such as spanners, screw drivers etc. which are not specific to an equipment are in the inventory
> system and we will have to associate them from that system. We probably can add that piece later
> because when a tool is assigned to an equipment to be deployed / mobilized, then it impacts the
> inventory system

So there is no per-vehicle tools list to import. Two kinds of item, two homes:

- **Equipment-specific fixed assets are rows of Plum's equipment list** and come in through this
  transformer. The report of 24 September holds none apart from the crane halves (Q6): its other
  categories are whole machines, workshop assets (compressors, lathes, welding sets) and "GENERAL".
  So ERT-2 records a machine's detachable kit - boom inserts, counterweights, hook blocks, tackles -
  on the platform, entered by the Fleet Admin (comment 2); should Plum list such items later, they come
  in through the transformer like any other row.
- **General tools** - spanners, screwdrivers, socket sets - belong to no machine. They are the
  inventory system's, and are associated with a machine only when issued to it for a mobilisation,
  which moves stock. That comes later, with the inventory integration and the mobilisation BOM (8A).

`DEFERRED_REQUIREMENTS.md` ("Asset component hierarchy") and `FUTURE_SLICES.md` (ERT-2, 8A) are
corrected to match.

### The questions as they were put (record)

Kept as asked, so the answers above can be read against them.

#### Q1. How does Plum's report come in?

Plum has no interface, only the report a person exports.

**Recommendation:** Fleet **uploads the report on a screen**. The platform reads it and shows a
preview - machines that would be added, changed or retired, rows it could not take in and why, model
names not yet mapped - and **nothing changes until Fleet confirms**. Upload as often as needed: after
any change to the fleet, or weekly. Each upload is compared with the last one confirmed. When Plum
offers an interface, the same steps run from it instead of from a file.

#### Q2. Who does it?

There is no Fleet role in the application today: the roles are Admin, Sales, Sales Manager, Finance,
Operations and Management (read only).

**Recommendation:** add a **Fleet** role. Fleet and Admin may upload, map model names, record models
and pair crane halves (Q6). Everyone who can see Work Orders can see machines and models. **Please
name who at PBL will hold the Fleet role** - the Equipment Master owner you named for Q14 of WRR-001,
and anyone else.

#### Q3. Which of Plum's machines come in?

**Recommendation:**

- Machines of the classes Hiring or Transportation deploy: cranes, manlifts, forklifts, excavators,
  prime movers, trailer beds, hydraulic axles, power packs and trucks - **about 290 active machines**
  in the report of 24 September.
- **Not** two- and four-wheelers, vans, garage assets, "GENERAL" or the generator (about 60 active).
  They are counted in the preview, not brought in. They can be added later by marking their class as
  used by a module.
- Inactive machines: one the platform already knows is **retired** when Plum marks it inactive, and
  comes back if Plum makes it active again. An inactive machine the platform has never seen is not
  brought in: the report holds about 330 such rows, mostly machines sold or scrapped long ago.
- A machine missing from a report is **not** retired: an export may be partial. It is flagged "not in
  the latest report" for Fleet to look at.

#### Q4. Models

Plum names each machine's model in its maintenance-schedule type ("SANY-SCC1000A", "XCMG QAY 220
SUPER"). The platform keeps its own **Model** list: maker, model name, class, type, and the model's
rated capabilities - SANY SCC1000A: crane, crawler, 100 t rated capacity.

**Recommendation:** Fleet **maps each Plum model name to a Model once**, on the import screen; every
later import uses that mapping. Today's active machines carry about **60 distinct names** - roughly an
hour's work the first time. The screen lists each unmapped name with its category and how many
machines carry it, and offers "map to an existing model" or "record a new model". A machine whose name
is not mapped yet still comes in - as "a crane", without type or model - and is flagged until it is.

The mapping is not prepared from the report in advance: that would put real fleet data into the build,
which your rule for the report forbids.

#### Q5. Capacities: model first, Plum's figure as a check

Plum's one `Capacity` column means a different thing in each category - tonnes of lifting capacity for
a crane, kilograms for a manlift or an axle, unclear for an excavator (WRR-001 design, section 21).
Two active cranes stand at 48,620 and 80,000, one at 1.

**Recommendation:** a machine's capabilities **come from its Model**. Plum's figure is used only to
**check**: where it disagrees with the model, the machine is flagged for Fleet, and nothing is taken
from it. A machine that genuinely differs from its model - a crane de-rated after repair, say - gets
its own value, entered by Fleet on the platform with a reason. Section 6 lists what Plum's figure is
taken to mean in each category, for the check; please confirm it or correct it.

#### Q6. A crane held in Plum as two records

Some cranes are two records in Plum: the superstructure ("DEMAG AC 200 SUPERSTRUCTURE") and the carrier
("DEMAG AC 200 CHASSIS"). Seven active records are like this today. Plum does not say which carrier
goes with which superstructure.

**Recommendation:** the superstructure record becomes **the crane**; the carrier record becomes the
crane's **fitted part** (the asset component hierarchy you recorded on 24 September). The import
screen **proposes pairs** from the model names, and **Fleet confirms each pair**. A carrier not yet
paired is flagged and is never offered to planning as a machine.

#### Q7. Prime mover and bed

On each prime mover, Plum records the trailer bed it currently pulls (`BedNo`, 151 records). Pairing
prime movers and beds is Transportation's (your answer to Q15 of WRR-001).

**Recommendation:** not taken into the platform now. The value is kept with the prime mover's source
record, so Transportation can use it when it designs combinations.

#### Q8. What else Plum holds

**Recommendation:**

- **Taken:** machine number, engine number, chassis number, the year Plum records the machine as
  commenced, the owning company, active or inactive.
- **Not taken:** PAN, insurance policy number and insurer, purchase and invoice dates and numbers, the
  six finance posting accounts, tyre counts, GPS and fuel-sensor devices, gross and unladen weights,
  tank capacity. Each belongs to a module designed later - Finance, Fixed Assets, Maintenance, log
  sheets (8C) - and is taken in then, by that module's own decision.
- **The uploaded file is not kept**: it holds the PAN and policy numbers. The platform keeps what it
  takes, plus the file's fingerprint, its row count and the date you give the report, so it can always
  show which report a machine's facts came from.

#### Q9. Statutory validity dates

Insurance, fitness, pollution, road tax, load test and permit dates (FRS Annexure-20) are not in
Plum's report. They are needed before a machine can be assigned to a job (8A, Eligibility). Under
ADR-037 they are Plum's facts in this phase.

**Recommendation:** not in this package. They stay on the list we ask Plum for (route A), and how they
come in is decided when Eligibility is designed (Q12).

#### Q10. One package or two?

**Recommendation: two.**

- **ERT-1 (this one):** Models, Machines, the import, crane halves paired.
- **ERT-2:** the detachable kit - boom inserts, counterweights, hook blocks, tackles, tools - Plum's
  per-vehicle tools list, and the depth setting (default 3). **Please obtain a sample of Plum's tools
  report**, as you did the vehicle report.

8A needs the machines first; the kit needs a sample we do not have; and one package would not be
testable on screen in twenty minutes.

#### Q11. Migration slot

**Recommendation:** `20260908_0042`, parent `0041`, unless the CRM lane needs it first.

#### Q12. Crew qualifications - roadmap, not this package

You asked today whether matching crew to machines by licences and certifications had been missed. It
is **partly** on the roadmap:

- The rules are approved (`ELA-001`): an expired or missing statutory licence always blocks an
  assignment; a named non-statutory gap may be accepted by an authorised approver; validity is watched
  continuously, with alerts 60, 30 and 15 days before expiry.
- 8B, "Crew Eligibility / Assignment", assigns crew from the Employee Master, but lists the checks only
  as "hooks".
- **What no package builds yet:** (a) each person's licences and certificates, with their validity;
  (b) what operating each kind of machine requires - "a crawler crane over 100 t needs licence X and
  certificate Y"; (c) the machine's own statutory certificates (Q9). Whether Plum holds crew licences
  at all is still an open question to Plum (`PF_1F_HR_PLUM_GAP_ANALYSIS_PACKET.md`, question 8).

**Recommendation:** add an **Eligibility foundation** package to the roadmap, before 8B, covering (a),
(b) and (c). The Equipment Reference is the natural place for (b): which qualifications each class or
type requires, alongside what the class can do. Nothing in ERT-1 stands in its way. On your yes this is
recorded in `FUTURE_SLICES.md` and `DEFERRED_REQUIREMENTS.md` with this package's documents.

---

## 2. Authority and required reading

What this design relies on, per PBL's internal working instructions "Reading discipline".

- ADR-037 and the WRR-001 design it came from:
  `docs/agent/slices/wrr-001-resource-requirement-foundation.md` - sections 1, 2 (Q13-Q17), 4, 5, 6,
  13, 16, 17, 21 and section 22's "Refinements" and "Part classes later" - read in full
- `docs/agent/contracts/resource-master-reference-contract.md` (`RMR-001`, APPROVED), with its ADR-032
  and ADR-037 notes - in full
- `docs/agent/contracts/resource-planning-assignment-contract.md` (`RPA-001`, APPROVED) - in full: the
  consumer of machines in 8A
- `docs/agent/contracts/eligibility-assignment-contract.md` (`ELA-001`, APPROVED) - in full (Q9, Q12)
- `docs/agent/pf-1f-hr/PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` - boundary architecture, canonical
  identity rule, sections F (crew credentials), G (source binding), H (adapter contract), staleness,
  phases: the pattern this design follows
- `docs/agent/DEFERRED_REQUIREMENTS.md` - "Resource requirements and the Equipment Reference",
  "Equipment Hiring execution", "Asset component hierarchy"
- `docs/agent/FUTURE_SLICES.md` - the transformer entry, 8A, 8B, 8C, 8E
- `docs/agent/architecture/EXTERNAL_DEPENDENCY_REGISTER.md` - the Plum Equipment Master row
- `docs/agent/architecture/MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` - Equipment Master, Resource
  Catalogue, Requirement, Availability, Assignment, Compliance / Eligibility rows
- `docs/agent/architecture/MODULE_DEPENDENCY_AND_DELIVERY_WAVES.md` - Equipment Master dependencies
- `docs/agent/architecture/DATA_CLASSIFICATION_AND_HANDLING.md` - restricted fields (Q8)
- `docs/reference/erp-source-extracts/TOOLS_AND_ASSET_ANNEXURES_EXTRACT.md` - Annexures 11(A), 11(B),
  20 and 21, in full
- `backend/app/modules/equipment_reference/` - `contract.py` (the canonical shapes and data-quality
  codes WRR-001 left for this package) and `ports.py` (`EquipmentSourcePort`); `hr_reference/ports.py`
  for comparison
- `backend/app/modules/documents/` - the upload handling and size limits of Slice 9C
- ADR-013, ADR-019 (no job queue is built; this import runs in the request), ADR-023 (repeated
  submissions create one effect), ADR-030, ADR-032, ADR-036 (the report file is not a document to keep)
- Plum's "Own Vehicle Complete Information Report" of 24 September 2026 - outside the repository,
  read for its columns and counts only (section 3). Never committed, never test data.

---

## 3. What Plum's report holds

681 rows, 32 columns; line 1 is a title, line 2 the header. Counts from the report of 24 September.

| Plum column | What it is | ERT-1 |
| --- | --- | --- |
| `VehicleNo` | the machine's number in Plum; unique, one blank | **Machine number** and the source key |
| `ScheduleMaintanceType` | the maintenance schedule's model name; the most consistent model key | **Model key**, mapped to a Model (Q4) |
| `Make`, `Model`, `Manufacturer` | maker and model; `Model` equals `Manufacturer` in every row | Model key when the schedule type is blank; shown to the Fleet Admin when mapping |
| `VehCategory` | 16 values | **Class**, through the alias table |
| `Status` | Active or Inactive | **Active or retired** (Q3) |
| `Capacity`, `LoadCapacity` | one figure, repeated in both wherever both are filled | **Checked** against the model (Q5, section 6) |
| `EngineNo`, `ChassisNo` | identity numbers | **Taken** |
| `CommencedYear` | four digits in 458 rows, "0" or one character in 205, blank in 16 | **Taken** as the year commenced; anything not a plausible year is left empty and flagged |
| `Owner` | the owning company; five values | **Taken** as the owning company, from a short list the Fleet Admin confirms |
| `BedNo` | on prime movers only: the bed currently pulled | Kept in the source record only (Q7) |
| `PAN`, `InsPolicyNo`, `InsuranceCo` | owner's PAN; insurance | **Not taken** (Q8) |
| `DateOfPurchase`, `InvoiceNo`, `InvoiceDt` | purchase | Not taken (Fixed Assets) |
| `ConsPostingAcc`, `TollTagAcc`, `MaintAcc`, `DieselAcc`, `TollPostingAcc`, `PostingAccount` | finance posting accounts | Not taken (Finance) |
| `GPS` | telematics and fuel-sensor devices | Not taken (log sheets, 8C) |
| `StandardTyre`, `StepneyTyre` | tyre counts | Not taken (Maintenance) |
| `TankCapacity`, `GrossVehicleWeight`, `UnladenWeight` | weights and tank | Not taken now |

The model mapping is small. Active machines in the classes of Q3 carry 58 distinct schedule-type names
(31 on cranes, 10 on prime movers, 9 on manlifts); four have none. Nine crane names carry more than
one capacity figure between their machines - the case Q5's check exists for.

---

## 4. The records

```text
Class, type, capability   the structure (WRR-001, version 1)                       unchanged
Model                     maker, model name, class, type, rated capabilities       new - the Fleet Admin's
Machine                   one physical machine: class, type, model, number,        new - identity and
                          identity numbers, owning company, active or retired,           status from Plum,
                          serial number, year of manufacture, capabilities from          as corrected;
                          its model unless the Fleet Admin sets its own                  the rest ours
Part                      an individually tracked part, fitted to a machine:        new - the carrier
                          a crane's carrier                                              only, in ERT-1
```

- **A machine and a part are both assets**, one record kind each, in one asset table with a kind of
  `MACHINE` or `PART`. A part is fitted to its machine by a dated link - fitted on, removed on - so
  replacing a carrier keeps its history (the asset component hierarchy). ERT-1 creates only `FITTED`
  links, one level deep; ERT-2 adds detachable kit, counted accessories and the depth setting.
- **A part has a class of kind `PART`.** Version 2 of the structure adds the class **Crane carrier**,
  kind `PART`, fitted to **Crane**, used by no business line - so it is never offered where Operations
  asks for machines. This is the additive change WRR-001 recorded ("Part classes later"): a kind column
  with default `MACHINE` for every existing class, and a table of which part classes fit which classes.
- **A model belongs to one class.** "DEMAG AC 200 CHASSIS" maps to a Crane-carrier model, so the
  mapping itself says which Plum records are carriers; no separate role is needed.
- **Capabilities are read from the model at the time they are asked for**, never copied onto the
  machine, so correcting a model's rating corrects every machine of it. A machine's own value, where
  the Fleet Admin sets one, overrides the model's for that capability, with its reason and who set it.
- **Identity:** each asset has the platform's own public id and a reference, `EQ-000001`, generated
  like WRR-001's `RR-` numbers. Plum's machine number is shown beside it, but it is Plum's key, kept in
  the source binding, and never the platform's identity (canonical identity rule, PF-1F-HR).
- **Where a fact came from** stays with the adapter: each asset's **source binding** records Plum as
  the provider, the machine number, the import that last saw it, and the few raw values it was built
  from - category, model key, capacity text, make, model, bed number. Consumers never see it.
- **Doubtful values are flags**, kept on the asset until an import no longer raises them or the Fleet Admin
  resolves the cause - never silent corrections (ADR-037).

Every machine read carries **the date of the report its facts came from**, so a consumer can tell how
fresh it is - the canonical freshness indicator of PF-1F-HR, section H. What staleness blocks what is
decided by the consumer that needs it (8A), not here.

---

## 5. The import, step by step

1. **Upload.** The Fleet Admin chooses the report file and states the report's date (today by default). The
   platform checks it is a CSV of at most 5 MB whose header carries every column the transformer reads;
   otherwise it refuses and says which column is missing. It records the file's SHA-256 fingerprint and
   row count; the file itself is read in memory and discarded (Q8).
2. **Same file again.** If the fingerprint matches the last confirmed import, the platform says so and
   stops: "This report was already imported on 25 September 2026."
3. **Read each row** into its used values only (section 3). A row with no machine number is set aside
   with a reason. Two rows with the same machine number are both set aside and flagged.
   **The Fleet Admin's value rules and machine corrections are applied here** (section 5B), so every
   later step works on values as the Fleet Admin has said they are to be read.
4. **Class.** The category is looked up in the alias table. An unknown category is set aside
   (`CATEGORY_NOT_MAPPED`); a class no business line uses is counted, not brought in (Q3).
5. **Model.** The schedule type (or, when blank, make and model) is looked up in the Fleet Admin's model mapping.
   Mapped: the machine takes the model's class, type and capabilities. The model's class must be the
   category's class, or a part class that fits it (a Crane-carrier model under CRANES); otherwise the
   row is flagged `CLASS_DISAGREES` and keeps the category's class without the model. Not mapped: the machine comes in with the category's class only, flagged
   `MODEL_NOT_MAPPED`.
6. **Check Plum's figure** against the model's rated value, after converting it from the category's
   unit (section 6). Text, zero, or a value outside the category's plausible range is flagged
   (`NOT_A_NUMBER`, `OUT_OF_PATTERN`); a value that disagrees with the model is flagged
   `DIFFERS_FROM_MODEL`. Nothing is taken from it.
7. **Compare with what the platform holds**, by machine number: new, changed, unchanged, retired
   (known and now inactive), reactivated, not brought in (inactive and never seen), missing from this
   report (flagged `NOT_IN_LATEST_REPORT`, not retired). A new record whose chassis number equals a
   missing machine's is flagged `POSSIBLY_RENUMBERED`, for the Fleet Admin to look at.
8. **Crane halves.** Records whose model is a Crane-carrier model become parts, not machines. For each
   unpaired carrier the preview **proposes** the crane of the same model name - only where exactly one
   such crane has no carrier - and the Fleet Admin confirms or chooses. An unpaired carrier is flagged
   `PART_NOT_FITTED`.
9. **Preview.** Counts of each outcome, the flags, the corrections applied, the model names to map
   (with category and number of machines), the proposed pairs, and the new machines whose details the
   Fleet Admin still has to complete (section 5A). Mapping a name or recording a model on the preview screen, then
   **Refresh**, recomputes the preview from the rows already read - no second upload.
10. **Confirm (publish).** In one transaction: assets created or changed, each changed asset's version
    increased, source bindings and flags updated, confirmed pairs linked, one business event per asset
    change and one for the import. Refused if another import was confirmed after this preview was made -
    "Another report was confirmed since this preview. Refresh it." A second click publishes nothing
    twice (ADR-023).

An unconfirmed preview may be discarded, and is discarded when a newer one is confirmed. Previews hold
only the used values of section 3.

---

## 5A. Facts Plum does not hold (comment 2)

The machine record holds what the job needs, not what Plum happens to hold. A machine is added to the
platform by the import, with what Plum gives; the Fleet Admin then obtains and enters the rest.

- **In ERT-1:** the machine's **serial number** and **year of manufacture** (FRS Annexure-20; Plum's
  report holds neither - its commenced year is kept as Plum's). The model's maker, name, type and
  ratings are the platform's already (Q4), which also covers the 21 active cranes Plum records with no
  maker.
- A fact entered on the platform is the platform's: the transformer never overwrites it. Should Plum
  later begin to hold it, which source wins is decided then, for that fact, and recorded.
- **Details to complete:** the machine list filters to machines still missing a platform fact, so the
  Fleet Admin can work through new arrivals. A missing detail is not a data-quality flag: nothing in
  Plum is wrong.
- Later packages add their facts the same way: statutory validity dates with the Eligibility
  foundation (Q9, Q12), base location with 8A, documents when "Equipment documents" is taken up.

---

## 5B. Corrections during transformation (comment 3)

Where Plum's value is mixed - two facts in one field - or wrong, the **Fleet Admin decides how it is to
be read**, once; the transformer applies that on every import. Nothing is corrected silently: every
correction names the person, the time, the reason and the Plum value it replaces (ADR-037's "flag, never
silently correct" is kept - a correction is a decision by an accountable person, not a guess by code).

Two kinds:

- **Value rules** - for a value wherever it appears in a column:
  - **split:** "230 KG" in the capacity column is the number 230 in kilograms;
  - **reassign:** "PULLER" in the capacity column names a type, not a figure - the machine is a
    ballast tractor, and there is no figure to check;
  - **not a value:** "select", or "0" in the commenced year, means nothing was entered.
  The model mapping (Q4) and the category rules (section 6) are rules of the same kind, for the
  columns they cover: "XCMG QAY 220 SUPER" is the model XCMG QAY 220 and the machine itself; "DEMAG AC
  200 CHASSIS" is a crane carrier.
- **Machine corrections** - for one machine and one field: the class, type, model, engine or chassis
  number, commenced year, owning company, active or inactive, or the figure for the capacity check. A
  crane recorded under FORK LIFT; an engine number entered as the chassis number; 80,000 where 80 t is
  meant. The machine number cannot be corrected: it is the key Plum and the platform share (a
  renumbered machine is `POSSIBLY_RENUMBERED`, section 5).

On each import, a correction whose Plum value is:

- **unchanged** - is applied;
- **now the corrected value** - is closed automatically: "Plum now agrees";
- **something else** - stays applied and is flagged `PLUM_CHANGED_CORRECTED_VALUE`, for the Fleet Admin to
  keep or close.

**Corrections to send to Plum** lists every open value rule and machine correction: the request to fix
at source (ADR-037, route A), always current. As Plum fixes them, they close themselves.

---

## 6. What Plum's figure is taken to mean, for the check (Q5)

From the WRR-001 design, section 21. **To be confirmed by the Fleet Admin.** Held as data - one row per Plum
category - so a correction is not a code change.

| Plum category | Class | Plum's figure is | In | Plausible range |
| --- | --- | --- | --- | --- |
| CRANES, CRANE | Crane | rated capacity | tonnes | 1 to 1,500 |
| MAN LIFTS | Aerial Work Platform | platform capacity | kilograms | 100 to 1,500 |
| FORK LIFT | Forklift | rated capacity | tonnes | 1 to 50 |
| Excavator | Excavator | unclear | - | not checked; flagged `UNIT_UNCLEAR` |
| TRAILERS | Prime Mover | gross combination weight | kilograms | 10,000 to 500,000 |
| TRAILER BED | Trailer | payload | kilograms | 1,000 to 200,000 |
| HYDRAULIC AXLES | Modular Hydraulic Trailer | payload | kilograms | 1,000 to 1,000,000 |
| Power Packs | Power Pack | unclear | - | not checked |
| TRUCKS | Truck | payload | kilograms | 1,000 to 60,000 |

---

## 7. Authority by phase, as ERT-1 builds it

| Fact | Phase 1 (now) | Changed on the platform by |
| --- | --- | --- |
| Machine number | **Plum** | nobody: it is the key both share |
| Engine and chassis numbers, commenced year, owning company, active or retired | **Plum, as corrected by the Fleet Admin** (5B) | the Fleet Admin, by a recorded correction, which is also sent to Plum |
| Serial number, year of manufacture | **The platform** (Plum does not hold them; 5A) | the Fleet Admin |
| Class, type, model, capabilities | **The platform** | the Fleet Admin: model mapping, models, a machine's own values |
| Which carrier is fitted to which crane | **The platform** (Plum does not record it) | the Fleet Admin: confirm or remove a pair |
| Statutory documents and their dates | Plum where it holds them; otherwise the platform, entered by the Fleet Admin (Q9, with the Eligibility foundation) | - |

No fact has two masters. Each is Plum's, read through the Fleet Admin's recorded corrections, or the
platform's; a correction is one visible record with its reason, never a quiet second copy.

---

## 8. Data-quality flags

WRR-001 defined five codes in `equipment_reference/contract.py`; ERT-1 uses them and adds the rest.

| Code | Raised when |
| --- | --- |
| `CATEGORY_NOT_MAPPED` | the category is not in the alias table (the row is set aside) |
| `MODEL_NOT_MAPPED` | the model name has no mapping yet |
| `CLASS_DISAGREES` | the mapped model's class differs from the category's |
| `NOT_A_NUMBER` | Plum's figure is text ("PULLER", "230 KG") |
| `OUT_OF_PATTERN` | Plum's figure is outside the category's plausible range, or the commenced year is not a year |
| `DIFFERS_FROM_MODEL` | Plum's figure, converted, disagrees with the model's rating |
| `UNIT_UNCLEAR` | the category's figure has no known meaning (section 6) |
| `VALUE_MISSING` | a figure the check needs is blank |
| `NOT_IN_LATEST_REPORT` | a known machine was not in the confirmed report |
| `POSSIBLY_RENUMBERED` | a new record's chassis number matches a missing machine's |
| `PART_NOT_FITTED` | a carrier is not paired with its crane |
| `DUPLICATE_SOURCE_KEY` | two rows carry one machine number (both set aside) |
| `PLUM_CHANGED_CORRECTED_VALUE` | Plum now holds a third value where the Fleet Admin had corrected one (5B) |

A flag stays on the asset until an import no longer raises it or the Fleet Admin removes its cause (a
mapping, a value rule, a correction, a pair). The machine list can show only flagged machines.

---

## 9. Permissions

| Permission | Granted to | Allows |
| --- | --- | --- |
| `EQUIPMENT_REFERENCE_READ` (exists) | the six current roles | the structure, models, machines, corrections |
| `EQUIPMENT_REFERENCE_MANAGE` (new) | **Admin** (comment 1) | imports, models, model mapping, value rules, corrections, a machine's details and own values, pairs |
| `EQUIPMENT_IDENTITY_READ` (new, added while building) | **Admin** (owner, 25 September 2026) | seeing engine and chassis numbers, wherever they appear - see section 20, refinement 18 |

No new role (comment 1). The screen check and E2E use `admin1`, and a read-only user for the refusals.

---

## 10. Routes

All under `/api/equipment-reference`, each pinned in `POST_BASELINE_NEW_ROUTES`.

```text
GET   /machines                                   list; class, type, status, flagged, machine-number search
GET   /machines/{public_id}                       one machine, its fitted parts, flags and freshness
PUT   /machines/{public_id}/capabilities          the Fleet Admin's own values for a machine, with a reason
PUT   /machines/{public_id}/details               facts Plum does not hold: serial number, year of manufacture
POST  /machines/{public_id}/corrections           correct one field, with the Plum value it replaces and why
POST  /machines/{public_id}/corrections/{correction_public_id}/close
GET   /value-rules, PUT /value-rules              how a Plum value is read wherever it appears; record or close
GET   /corrections                                every open rule and correction: the list to send to Plum
POST  /machines/{public_id}/fitted-parts          fit a part (confirm a pair)
POST  /machines/{public_id}/fitted-parts/{part_public_id}/remove
GET   /models                                     list
POST  /models                                     record a model
PUT   /models/{public_id}                         change a model (versioned)
PUT   /model-mappings                             map a Plum model name to a model, or remove the mapping
POST  /imports                                    upload (multipart) - reads and returns the preview
GET   /imports, GET /imports/{public_id}
POST  /imports/{public_id}/refresh                recompute the preview after mapping
POST  /imports/{public_id}/publish                confirm
POST  /imports/{public_id}/discard
```

Writes take the version they were made against and refuse a stale one (`409`), and a repeated request
key has one effect (ADR-023). The upload's size is bounded before it is read, as Slice 9C's documents
routes do.

---

## 11. Events

`EQUIPMENT_IMPORT_PUBLISHED` (counts of each outcome, the fingerprint's first characters, the report
date), `EQUIPMENT_ASSET_REGISTERED`, `EQUIPMENT_ASSET_CHANGED` (which facts changed, by name),
`EQUIPMENT_ASSET_RETIRED`, `EQUIPMENT_ASSET_REACTIVATED`, `EQUIPMENT_MODEL_RECORDED`,
`EQUIPMENT_MODEL_CHANGED`, `EQUIPMENT_MODEL_MAPPED`, `EQUIPMENT_PART_FITTED`, `EQUIPMENT_PART_REMOVED`,
`EQUIPMENT_MACHINE_CAPABILITY_SET`, `EQUIPMENT_MACHINE_DETAILS_SET`, `EQUIPMENT_VALUE_RULE_RECORDED`,
`EQUIPMENT_VALUE_RULE_CLOSED`, `EQUIPMENT_CORRECTION_RECORDED`, `EQUIPMENT_CORRECTION_CLOSED` (by the
Fleet Admin, or because Plum now agrees).

Payloads carry public ids, codes, versions, counts and dates only: no machine, engine or chassis number,
no Plum value, no reason text.

Uploading, refreshing and discarding a report record no business event (added 7 October 2026, TB-1 P5):
until it is confirmed a report is a preview that changes no machine, model or rule, and the import row
itself keeps who uploaded, published or discarded it and when - it is that action's audit record.
Confirmation, which does change the fleet, records `EQUIPMENT_IMPORT_PUBLISHED`.

---

## 12. Data, module and migration

All in `backend/app/modules/equipment_reference/`, which stays read-only to every other module except
through its service. No `crm_` prefix. Migration `20260908_0042_equipment_models_and_machines` (Q11):

- **Structure, version 2:** `equipment_class.class_kind_code` (`MACHINE` default, `PART`);
  `equipment_part_fit` (part class, parent class); the class **Crane carrier**. The model mapping has a
  table of its own (below), not the alias table: an alias names a class or type, a mapping names a model.
- **Models:** `equipment_model` (public id, maker, model name, normalized key unique, class, type,
  version, retired), `equipment_model_capability` (rated value or choice per applicable capability,
  under the same NULL-safe and finite rules as WRR-001's requirement capabilities),
  `equipment_model_source_key` (provider, normalized Plum model name -> model).
- **Assets:** `equipment_asset` (public id, `EQ-` reference generated from the id, kind, class, type,
  model, machine number, engine and chassis numbers, commenced year, owning company code, status
  `ACTIVE` / `RETIRED`, serial number and year of manufacture (the platform's, 5A), version, report
  date of its facts), `equipment_asset_capability` (the Fleet Admin's own
  value, reason, who, when), `equipment_asset_link` (parent, child, link kind `FITTED`, fitted on,
  removed on; one open link per child), `equipment_asset_flag`.
- **Adapter-owned:** `equipment_source_binding` (asset, provider `PLUM`, provider key, raw used values,
  reconciliation status `CONFIRMED` / `AMBIGUOUS` / `UNMATCHED`, last import), `equipment_source_import`
  (public id, fingerprint, row count, report date, status `PREVIEWED` / `PUBLISHED` / `DISCARDED`, the
  import it was compared against, who and when), `equipment_source_import_row` (the used values and
  outcome of each row), `equipment_source_category_rule` (section 6), `equipment_owner_company` (Plum
  owner value -> company code, Q8).
- **The Fleet Admin's corrections (5B):** `equipment_source_value_rule` (column, normalized Plum value,
  action `SPLIT_NUMBER_AND_UNIT` / `REASSIGN_TO_TYPE` / `NOT_A_VALUE`, the resulting number, unit or
  type, reason, open or closed, who and when) and `equipment_asset_correction` (asset, field, the Plum
  value replaced, the correct value, reason, open or closed and why, who and when). Both are applied in
  step 3 of section 5, before anything else reads the row.
- The composite-key, CHECK and trigger rules of WRR-001 apply: a type of the model's class, a capability
  that applies to the class, a unit never stored with a value, numbers finite.
- **`EquipmentSourcePort`** (WRR-001's `ports.py`) is implemented by the Plum report adapter, and
  `CanonicalMachine` gains the fields it now needs (model, machine reference, status, freshness).
  Consumers read machines through the service, never a binding or an import row.
- The permission code and its grant to Admin, and the version-2 structure rows, in the migration.

---

## 13. Screens

Sidebar **Equipment**, for everyone who may read it, with three pages:

- **Machines:** reference, machine number, class, type, model, key capability, status, flags; filter
  by class, status, "flagged only" and "details to complete". A machine's page shows Plum's facts as of
  the report date - each corrected one marked, with the Plum value and the reason - the details the
  platform holds, the classification and capabilities (marking any value the Fleet Admin set), its
  fitted parts, its flags and its events, with **Correct**, **Details** and **Pair** for the Fleet Admin.
- **Models:** list; record and change a model (Fleet Admin).
- **Plum report:** upload, the preview of section 5 with **Map**, **Read as** (a value rule) and **Pair**
  actions beside each item, **Refresh**, **Confirm**, and past imports; and **Corrections to send to
  Plum**. Messages sit beside the button that caused them.

---

## 14. Differences from the WRR-001 sketch (recorded per ADR-013)

| WRR-001 design, section 6 | ERT-1 | Why |
| --- | --- | --- |
| Map Plum model to the platform's Model through "mapping tables we keep" | The Fleet Admin builds the mapping on the import screen; none is prepared from the report | The report is real fleet data (Q4) |
| Units converted per class | Plum's figure is converted only to **check** it; capabilities come from the model | One figure in mixed units cannot be trusted as a capability (Q5) |
| Machines and parts as separate records | One asset table with a kind, and dated links | The component hierarchy's depth is a setting: parts of parts need no new table |
| "Plum's per-vehicle tools list comes in the same way" | No such list | Equipment-specific fixed assets are rows of the equipment list; general tools are the inventory system's (comment 5) |
| `CanonicalMachine` as drafted | Gains model, reference, status and freshness | What 8A's candidate search needs (`RPA-001`) |
| Doubtful values "flagged for Fleet to fix at the source, never silently corrected" | Flagged, **and** corrected on the platform by the Fleet Admin's recorded rule or correction, which is also sent to Plum | Owner, comment 3 |
| Plum the source of machine facts in Phase 1 | Plum for what it holds, as corrected; the platform for what it does not | Owner, comment 2 |

---

## 15. Not in this package

Detachable kit and the depth setting (ERT-2); general tools, issued from the inventory system at
mobilisation (later, with the inventory integration; comment 5); statutory validity dates and
every Eligibility check (Q9, Q12); prime-mover and bed pairing (Q7); a maintenance screen for classes,
types and capabilities (still by migration); machine location (8A); equipment documents (comment 4,
deferred); a Fleet Admin role (comment 1); creating a machine Plum does not hold; any feed back into Plum
(Phase 3); availability, reservation and assignment (8A). Requirements (WRR-001) do not change.

---

## 16. Tests and checks

- **Test data is invented, never Plum's.** Tests build CSV files in the report's shape - its title line
  and 32 column names - with made-up machines ("TEST-CR-001", "ACME AC 100 SUPER"). No row or list of
  model names from the real report enters a test, a fixture or a migration; this design quotes its
  counts and a few model names only to size the work, as WRR-001's did.
- **Import:** header refused without a used column; title line and byte-order mark handled; the same
  file twice; blank and duplicate machine numbers; unknown category; unused classes counted; mapped and
  unmapped models; `CLASS_DISAGREES`; each flag of section 8 raised and cleared; inactive-new skipped,
  known-inactive retired, reactivated; missing flagged not retired; renumbering suspected; carriers
  become parts; pair proposals only when unambiguous; refresh after mapping; stale preview refused;
  publish twice one effect; Plum facts unchanged by any platform route.
- **Corrections:** a value rule splits "230 KG" and reassigns "PULLER" on every row that carries them;
  a machine correction applies on each import, closes itself when Plum takes the corrected value, and is
  flagged when Plum changes to a third; the machine number cannot be corrected; the list to send to
  Plum holds exactly the open ones; details entered on the platform survive every import.
- **Records:** model capabilities follow WRR-001's rules; a machine's capability is its model's unless
  set; a model correction reaches its machines; one open link per part; a removed link keeps history.
- **Permissions:** read for every read role; every write refused to every role but Admin.
- **Events:** payloads carry no identity number, Plum value or free text.
- **Smoke data and cleanup:** a scenario that publishes a small invented import; cleanup removes only the
  assets, models, imports and bindings its run created (TE-4 provenance), never a real import's.
- **E2E:** Admin uploads an invented report, maps a model, records a value rule, pairs a crane,
  confirms, and sees the machine; a read-only user sees machines and no upload.
- Full backend regression, the frontend gate and E2E; migration from an empty database; the independent reviewer
  review; your screen check with the steps in the chat.

---

## 17. Shared files this package touches

`backend/app/main.py` (one router already registered; new routes on it), `frontend/src/routes.tsx`,
`backend/app/modules/authorization/contract.py` (a permission),
`backend/tests/fixtures/post_baseline_tightened_routes.py` (read it by eye after any merge),
`backend/tooling/smoke_data/`, the sidebar.

## 18. What would stop implementation and come back to you

- Plum's vehicle type master arriving with a level the structure cannot take in.
- A need for the uploaded file to be kept (Q8).

---

## 19. Draft refinement of ADR-037 (comments 1 to 3)

Recorded in `ARCHITECTURE_DECISIONS.md` under ADR-037 when this package is built, as WRR-001 recorded
ADR-037 itself.

> **Refinement, 25 September 2026 (owner).** The platform's records are built for the job at hand, not
> limited by what Plum holds or can give.
>
> 1. Where Plum does not hold a fact the job needs, the Fleet Admin obtains it and enters it on the
>    platform, which is then that fact's source; the transformer never overwrites it. Machines are
>    still added through Plum in Phase 1: Plum's facts first, the rest by the Fleet Admin.
> 2. Where a Plum value is mixed or wrong, the Fleet Admin decides how it is read - split into its
>    facts, or reassigned to the field it belongs in - by a recorded rule or correction that the
>    transformer applies on every import, and that is listed for Plum to fix at source. A correction is a
>    decision by an accountable person, so "flag doubtful values rather than silently correct them"
>    stands.
> 3. Until a Fleet Admin role exists - one or two responsible people outside day-to-day operations -
>    Admin holds these duties.
>
> The Phase 1 row of the authority table reads: machine identity, status and statutory documents -
> **Plum, through the transformer, as corrected by the Fleet Admin; facts Plum does not hold, the
> platform.**

Documents updated with it: `ARCHITECTURE_DECISIONS.md` (ADR-037), `RMR-001` (its ADR-037 note gains a
sentence), `EXTERNAL_DEPENDENCY_REGISTER.md` (the Plum Equipment Master row) and
`MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` (the Equipment Master row).

---

## 20. Implementation record (25 September 2026)

Built on `hiring/equipment-reference-transformer` in worktree `<a separate worktree>`, from the design
commits `03465ce` and `a8cfcbe` on `main` at `b5603e5`. Migration `20260908_0042`, parent `20260908_0041`.
The ADR-037 refinement of section 19 is recorded in `ARCHITECTURE_DECISIONS.md`, with `RMR-001`'s note,
the external dependency register and the module boundary matrix.

### What exists now

```text
backend/alembic/versions/20260908_0042_equipment_models_and_machines.py
        structure version 2 (class kind, part fits, Crane carrier); 15 tables; the category rules of
        section 6; EQUIPMENT_REFERENCE_MANAGE granted to Admin
backend/app/modules/equipment_reference/
        plum_report.py     the transformer, pure: reading the report, rules and corrections, the preview
        plum_source.py     EquipmentSourcePort's Plum adapter (canonical machines for consumers)
        services/          common, models, machines, imports, rules - one module per concern
        contract.py, schemas.py, repository.py, routes.py, service.py (the structure read gains kinds and fits)
backend/app/modules/authorization/contract.py        EQUIPMENT_REFERENCE_MANAGE, EQUIPMENT_IDENTITY_READ
backend/tooling/smoke_data/                          scenario equipment-plum-import, a seventh record set in
                                                     core-regression-bundle, cleanup and status of equipment
frontend/src/pages/equipment/                        Machines, a machine, Models, Plum report, a report's
                                                     preview; equipmentState.ts holds the rules, tested
e2e/tests/equipment-import.spec.ts                   upload, map, read, pair, confirm; read-only view
docs/agent/contracts/equipment-reference-api-contract.md   the routes, as built
```

### Refinements made while building (recorded per ADR-013)

Refinements 1 to 17 and 19 change no answer of the owner's: each is a choice the design left open, or a detail it needed to work. Refinement 18 is the owner's own decision of 25 September 2026, made during implementation.

| # | Design said | Built | Why |
| --- | --- | --- | --- |
| 1 | Owning company "from a short list the Fleet Admin confirms" (`equipment_owner_company`) | Kept as Plum gives it, trimmed; a wrong value is corrected like any other (`OWNING_COMPANY`); the confirmed company-code list is deferred (`DEFERRED_REQUIREMENTS.md`, "Owning company codes") | Nothing consumes a company code yet, and a list needs its own screen; the value is still correctable |
| 2 | Correctable fields include "type" | Not a correction field: type follows the model, or a value rule that names one. To change one machine's type, correct its model | Type is the platform's fact (section 7), not a Plum value, so a "correction" of it has no Plum value to replace or to send |
| 3 | Rules and corrections "close themselves" as Plum fixes them | Machine corrections do (`PLUM_AGREES`). Value rules stay open until the Fleet Admin closes them; the list to send to Plum shows how many rows of the latest confirmed report still carry each value | An export may be partial (Q3): a report without a value would close a rule that is still needed, and every E2E run would close real rules |
| 4 | Corrections are applied on every import | Also at once: recording or closing a correction on a machine re-reads it from the values its latest report gave | The Fleet Admin sees the machine corrected, without waiting for the next report |
| 5 | The binding keeps "the few raw values it was built from" | It keeps every used value of the row | Needed to re-read a machine after a correction (4) |
| 6 | "Refused if another import was confirmed after this preview" | That, and also refused when anything the preview is computed from changed since - models, mappings, rules, corrections, own values, pairs - counted in `equipment_reference_state`; every write takes one lock | A preview confirmed after someone changed a mapping would apply what the Fleet Admin never saw |
| 7 | Routes: `PUT /value-rules` records or closes | `PUT /value-rules` records; `POST /value-rules/{id}/close` closes. `GET /category-rules` added, so the Fleet Admin can see section 6 to confirm it | Clearer requests; section 6 is "to be confirmed by the Fleet Admin" |
| 8 | Import routes | Their reads need `EQUIPMENT_REFERENCE_MANAGE` too | A preview is the Fleet Admin's working record, not a machine read |
| 9 | Models: "normalized key unique" | Maker and name are unique **within a class** | A crane "DEMAG AC 200" and its carrier "DEMAG AC 200" are two models; matching their names is how a carrier is proposed to its crane |
| 10 | "The Fleet Admin confirms or chooses" a pair | Confirmed pairs are sent with the confirmation; a proposal starts unticked; one machine cannot take two parts of a class | Nothing is paired without an explicit tick |
| 11 | Same file again: refused once confirmed | And the same file while its preview waits returns that preview (`replayed`) | ADR-023: a repeated upload has one effect |
| 12 | - | A status that is neither Active nor Inactive sets the row aside (`STATUS_NOT_RECOGNISED`); a value longer than the platform keeps sets it aside (`VALUE_TOO_LONG`, kept on refresh); a held machine whose row is set aside is flagged, not left untouched | The design named no rule for these |
| 13 | - | A machine that becomes a part (its name mapped to a carrier model later), or the reverse, leaves the links it was in, dated the report's date; a change of class drops the machine's own values the new class does not take, and the event names them | Otherwise the database would refuse the change |
| 14 | Plum's figure is checked against the model | Against the machine's own value first, where the Fleet Admin set one | A de-rated crane's figure should agree with its own rating |
| 15 | E2E "uploads an invented report" | The seed confirms a first invented report and writes a second into the manifest, as a seventh record set in `core-regression-bundle` (WRR-001's precedent) - no fourth manifest | `run-e2e.ps1` and the compose file are unchanged |
| 16 | Cleanup "never a real import's" | Provenance (TE-4): models and the first import named by the manifest; the uploaded report's import by its fingerprint, which only the run's own file has; machines by the import that first brought them in; value rules by the import they were recorded on; mappings by the Plum model names the run's own reports carry, recorded exactly in the manifest (whoever made the mapping, whatever model it points at). Cleanup refuses, deleting nothing, if another machine uses a run's model or was read from a run's import; if a fitted-part link - open or removed - joins one of the run's assets to one it did not bring in; if a name the run's reports do not carry is mapped to a run's model; or if an import the run did not make - a waiting preview included - was compared with one of the run's | A name or prefix match is never the safety check. Mappings are claimed by provenance rather than by TE-4's downward containment: a mapping is configuration that steers every later import of the real fleet, so one of a real name is someone's, even on a test model - as a machine using a test model already was |
| 17 | "Test data is invented, never Plum's" (section 16) | Invented reports for every behaviour test; and, under the owner's rule of 25 September 2026, a **dummified copy** of the 24 September report (`backend/tests/fixtures/plum_vehicle_report_dummified_2026-09-24.csv`) for one realistic test of the transformer | The owner: the confidential fields are registration and chassis numbers, PAN, insurance numbers and the like; the rest is manufacturer information. Registration, bed, engine and chassis numbers are replaced by stable dummies (placeholders such as "0" and "NIL" kept), PAN, insurance, invoice, purchase, posting-account and GPS values by "DUMMY". Its expected counts were taken from the file independently, with PowerShell |
| 19 | Corrections apply on every import, close themselves when Plum agrees, and are flagged when Plum changes (section 5B) | A row set aside - an unknown category, a status neither Active nor Inactive, a machine number on two rows - takes nothing in, a correction's lifecycle included: an agreeing or third value in it closes or flags nothing | Set aside means nothing about the row is taken in (section 5); a correction closing on a row the platform otherwise refused to read would be the only exception, and the preview promised it without confirmation doing it (independent review, round 4, ERT1-R4-003) |
| 18 | Machines, models and corrections readable by the six read roles (section 9) | Unchanged, except **engine and chassis numbers**: shown only with a new permission, `EQUIPMENT_IDENTITY_READ`, granted to Admin. Others see every other fact, and that a correction or value rule of those fields exists, but not the values | Owner, 25 September 2026, during implementation: "restrict chassis and engine numbers to Admin for now"; Operations, and Finance for audits, may need them later - a grant, with no code change |

### The owner's screen check (26 September 2026)

Pass with minor issues: every step passed; three screen notes - the preview's line numbers, where Refresh
is, and the details form's buttons - were resolved in wording and layout, and one (highlighting what a
refresh changed) deferred. The same day the owner set the rule that styling goes through the shared
stylesheet (DRY, then KISS, YAGNI and SOLID), and the Equipment pages were moved onto `globals.css`
classes. The acceptance record has the detail.

### Tests and checks

Recorded in `docs/agent/acceptance/ert-1-plum-machines-into-the-equipment-reference-acceptance.md` and
the continuity note `docs/continuity/ERT_1_PLUM_MACHINES_INTO_THE_EQUIPMENT_REFERENCE.md`, with the tree
each was measured on.

### Independent review

the independent reviewer, bounded packets; the owner's cap is three rounds, a fourth needs the owner's yes.
Results are recorded here round by round.

**Round 1** - tree `ce9c9645`, packet SHA-256 `4db5a59e19386d74...`: `CORRECTION_REQUIRED`, one blocking,
six material, one advisory. All eight were accepted and corrected. Each correction has a test, and each
test was shown to fail with its correction undone (a mutation check, one per correction).

| Finding | What was wrong | Correction | Test |
| --- | --- | --- | --- |
| R1-001 blocking | Cleanup deleted any fitted-part link touching a run's asset, including one a person or another run made | Cleanup refuses, deleting nothing, when a link - open or removed - joins a run's asset to one the run did not bring in | Both directions: an outside part on a run's machine, a run's part moved to an outside machine; nothing deleted, events kept |
| R1-002 material | The same file was refused only when it was the latest confirmed report | Refused when it matches any confirmed import | A first report, uploaded again after a second was confirmed, is refused |
| R1-003 material | Fitting and removing did not guard the part's version, and a retired part could be fitted | Both take `expected_part_version` (the screens send the version they showed); a retired part is refused | A part changed since it was read is refused on fit and on removal; a retired part is refused |
| R1-004 material | A confirmation that only closed a correction or raised a flag left the machine's version unchanged | Each machine a confirmation changes in any way shown - facts, flags, corrections, links, reported values - moves its version once; the report date and last import are bookkeeping and move none | Correction-close-only and missing-flag-only machines move on and refuse a stale write; an untouched machine keeps its version |
| R1-005 material | A late answer for the machine page's previous machine could start that machine's events under the new one | The machine page's loading is a tested controller: each load clears the events shown, a stale answer installs nothing and asks for no events, a late save for another machine installs nothing; a load of another machine stops showing the one before | Out-of-order answers across two machines; a save racing a load |
| R1-006 material | The preview did not show the corrections and value readings a row was read with | Each row names them, in words, beside its flags; such a row is shown by default even with no flag; engine and chassis values are never repeated in the stored preview | Backend: an unchanged, unflagged corrected row is shown and names both corrections; the reading of a chassis number omits the value. Frontend: the wording of every effect and action |
| R1-007 material | A machine's own value, or its model's rating, left the capacity flags as they were until the next report | Both re-read the machine at once; a model change also carries its type to its machines, records `EQUIPMENT_ASSET_CHANGED` where facts changed, and moves the version of every machine of the model, since each shows its model | An own value clears then raises `DIFFERS_FROM_MODEL`; a model's new rating and type reach both its machines at once; a new name alone moves each machine's version |
| R1-008 advisory | The package docstring described ERT-1 as future work and the structure as version 1 | Rewritten: version 2, the managed records, the transformer, the identity permission | - |

The controller's own check of the corrections added one more: a model's change moves the version of every
machine of it, since each shows its model's name and ratings (a rename alone moves each machine).

**Round 2** - tree `218dcbcb` (commit `58bd513`), packet SHA-256 `de6b366aa545a9a7...`: `CORRECTION_REQUIRED`,
two blocking, three material. The first packet for this round (1,210,107 characters) was refused unread by
the reviewer's input limit of 1,048,576; it was rebuilt without duplication - no backend file both whole and as a
diff, the harness's large `cleanup.py` as its diff, no documentation in the since-round-1 diff - to
1,010,594. All five findings were accepted and corrected, each with a test shown to fail with its
correction undone.

| Finding | What was wrong | Correction | Test |
| --- | --- | --- | --- |
| R2-001 blocking | Cleanup could change records made outside the run by two more paths: an import compared with a run's import (deleting it emptied the other's comparison), and a mapping of another name to a run's model (deleted with the model) | Cleanup refuses, deleting nothing, in both cases. Mappings are claimed by the exact Plum model names the run's reports carry, now listed in the manifest (`equipment_source_names`), whichever model they point at | A waiting preview compared with a run's import: refused, the preview unchanged. Another name mapped to a run's model: refused, the mapping kept. A run's name mapped to an outside model: the mapping removed, the model kept. Malformed names refuse the whole manifest |
| R2-002 blocking | The reason of an engine or chassis number correction or reading was shown to every read role, though it may repeat the numbers | The reason is withheld with the values (`reason: null`), on the machine, in `/corrections` and in `/value-rules`; the screens read "The reason is shown to Admin only." | Reasons that carry both numbers: absent from every non-Admin response, present for Admin; another field's reason still shown |
| R2-003 material | A re-reading that changed a machine's class left a part fitted that no longer fits it; one that closed a link left the parts unflagged until the next report | A change of kind or class checks each link by the fitting rules and closes those that fail; `PART_NOT_FITTED` is set at once for the asset and the other end of every link it left; each changed asset moves its version | A crane corrected to a forklift loses its carrier, flagged at once; a crane made a carrier by a model correction leaves its link, and both parts are flagged and offered for pairing |
| R2-004 material | The preview page could keep one import, or put a late action's answer, under another import's address | A tested controller loads and acts; every answer names its import and is installed only on that import's page; asking for another import clears the one shown and its pair choices at once; copies of one import are ordered (confirmed or discarded after any preview, then by preview version), so an earlier never replaces a later | Navigation during a refresh; a mapping answered after the page moved; out-of-order load and action answers on one import |
| R2-005 material | A delayed save's answer could replace a newer version of the same machine, and cancelled a reload begun since | The version decides, not the arrival: an earlier version never replaces a later, the same version keeps the forms made on it, and a save cancels no reload | A delayed version-2 save against a version-3 reload, in both orders; a load older than a save |

**Round 3** - tree `1e0bbe49` (commit `edf56f8`), packet SHA-256 `99e6db693961b528...`: `CORRECTION_REQUIRED`,
five material, none blocking. This was the last round within the owner's cap of three. All five were
accepted and corrected, each with a test shown to fail with its correction undone; a fourth round needs the
owner's yes.

| Finding | What was wrong | Correction | Test |
| --- | --- | --- | --- |
| R3-001 material | A report that changed a machine's kind or class closed its carrier's link on confirmation without the preview saying so, and pairs were proposed as if it stayed fitted | The transformer projects the links confirming will close (`_closing_links`, judging both ends as they will stand); the preview names each in both rows and in `closing_links`, flags the part `PART_NOT_FITTED`, and proposes pairs from that state; confirming closes exactly those, before any row is written | A report calling a paired crane a forklift: the preview shows the closing link and the unfitted carrier, proposes the other free crane of its model, and confirming closes exactly that link |
| R3-002 material | A late answer from an older Refresh, Confirm or Discard could replace a newer one's message or unlock the buttons while it was awaited | Each action carries a ticket; only the awaited action's answer gives the message and unlocks; a load never unlocks | An old refresh answering, as success or refusal, after a confirmation; an older refusal while a newer action waits |
| R3-003 material | A failed save's message for one machine could appear under another after the page moved, and unlock its forms | Each save carries a ticket and its machine; only the awaited save's answer, on its own machine's page, gives a message or unlocks | A refusal for the machine left behind, then the current machine's own |
| R3-004 material | Mapping events were recorded on the model mapped to, so cleanup left a run's event on someone else's model | A mapping's events are its own: record type `equipment_model_mapping`, under an identity derived from its provider and normalized name (UUID v5); cleanup derives the run's from the manifest's names and deletes their events | A run's name mapped to an outside model: after cleanup the mapping and its event are gone, the outside model's own events unchanged, residue clear |
| R3-005 material | A report dated before a part was fitted, and ending that fit, failed with a database error (500) | A link is closed on the report's date or, if the report is older, on the day it was fitted - never before; so is a link closed by a re-reading, dated today where PBL works | A report three days older than the fitting closes the link on the fitting day |

Also found after round 3's E2E run: two harness runs left in the database. Both were leaked by one harness
test that failed under a mutation check before its cleanup step. The test now cleans its run in a
`finally`; both runs were removed through `cleanup_manifest`.

**Round 4** - tree `ddbaba9f` (commit `1c00030`), packet SHA-256 `1076257f85a81b25...`, authorized by the owner
beyond the cap: `CORRECTION_REQUIRED`, one blocking, four material. All five were accepted and corrected,
each with a test shown to fail with its correction undone. **The owner then chose to end the independent
review here and go to the screen check (25 September 2026)**: round 4's corrections were not reviewed again
by the reviewer. They are small, each is tested and mutation-checked, and they are recorded below.

| Finding | What was wrong | Correction | Test |
| --- | --- | --- | --- |
| R4-001 blocking | The equipment scenarios confirm invented reports; on a database already holding machines that flags them all missing, re-reads them as unmatched, moves their versions and discards waiting previews - changes cleanup cannot undo | `equipment-plum-import` and `core-regression-bundle` seed only where no machine is held and no preview waits, and refuse otherwise before any record set - CRM ones included - is written (`require_no_equipment_fleet`) | Both scenarios, over a waiting preview and over a held machine: refused, nothing written; should a broken refusal seed after all, the test removes what it seeded |
| R4-002 material | An old action's answer carrying the same copy of the import could still reset the page's pair choices and "changed since" state | An action's answer that is not the one awaited changes nothing at all | The same version answered late, after the import was left, opened again and a mapping recorded |
| R4-003 material | A known machine's row set aside still showed its correction effects, promising a closure confirmation would not make | A set-aside row carries no correction effects: it takes nothing in, a correction's lifecycle included (refinement 19) | An agreeing value and a third value, each in a row set aside: no effect shown, the correction stays open, nothing flagged |
| R4-004 material | A part could be fitted to one machine on a day before it came off another, on the page or by a report's pair | A fitting never begins before the part's last removal, or the machine's last part of that class came off: the page refuses (`422`), a report's pair is dated no earlier | On the page, the day before the removal is refused; an older report re-pairing a carrier dates it the removal day |
| R4-005 material | The Models page kept a model's form open against an older version after a newer one was loaded | Loading the models closes a form whose model has a newer version, with a message | A newer version closes the form; a current or new one stays open |
