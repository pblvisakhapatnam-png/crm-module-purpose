# Equipment Reference API Contract - models, machines, the Plum report (ERT-1) and detachable kit (ERT-2)

Implementation contract for ERT-1 (25 September 2026) and ERT-2 (26 September 2026). The designs and the
owner's answers are `docs/agent/slices/ert-1-plum-machines-into-the-equipment-reference.md` and
`docs/agent/slices/ert-2-detachable-kit.md`; ownership is ADR-037 with its refinement of 25 September 2026;
the logical reference contract is `RMR-001` (`resource-master-reference-contract.md`, `APPROVED`). The
structure route itself (`GET /structure`) is in `resource-requirement-api-contract.md`; ERT-2 adds to its
response (section "Detachable kit" below). This file states what the routes accept, return and refuse.

```text
backend/app/modules/equipment_reference/
  plum_report.py        the transformer: reads the report, applies the Fleet Admin's rules and
                        corrections, computes the preview (pure; no database)
  plum_source.py        EquipmentSourcePort's Plum adapter: canonical machines for consumers
  services/common.py    errors, the write lock and change count, events, context, writing facts
  services/models.py    models and the mapping of Plum's model names
  services/machines.py  machines: reads, details, own values, corrections, fitted parts
  services/imports.py   upload, preview, refresh, confirm, discard
  services/rules.py     value rules, the corrections to send to Plum, category rules
```

No other module's table is read or written. "Fleet Admin" means whoever holds
`EQUIPMENT_REFERENCE_MANAGE`: Admin, until a Fleet Admin role exists.

**Read by Eligibility (ELG-1)** through `service.py`, never its tables: `get_asset_with_fitted_parts` (one asset -
machine, fitted part or piece of kit - with the parts fitted below it through open fitted links and the asset
it is fitted to) and `list_active_assets_with_fitted_parts` (every active asset, each with its own), both as
`AssetFacts` - public id, reference, kind, origin, class, type, machine number, serial number, status,
version, and (ELG-2) `added_on`, the day the asset was added (its record's creation, in Asia/Kolkata), from which a
certificate never recorded is reminded. No route changes, and no table. Eligibility's certificates key on an asset's public id
(`eligibility-api-contract.md`).

## Permissions

| Code | Roles | Guards |
| --- | --- | --- |
| `EQUIPMENT_REFERENCE_READ` | all six (as `WORK_ORDER_READ`) | machines, models, value rules, corrections to send, category rules, the structure |
| `EQUIPMENT_REFERENCE_MANAGE` (new) | `ADMIN` only (owner, comment 1) | every write, and every import route including its reads |
| `EQUIPMENT_IDENTITY_READ` (new) | `ADMIN` only (owner, 25 September 2026) | seeing engine and chassis numbers - no route of its own |

Every route is pinned in `backend/tests/fixtures/post_baseline_tightened_routes.py`
(`POST_BASELINE_NEW_ROUTES`), ERT-2's two with `EQUIPMENT_REFERENCE_MANAGE`. A Fleet Admin role, when it exists, is given `EQUIPMENT_REFERENCE_MANAGE` by
a grant with no code change.

**Engine and chassis numbers are confidential** (owner, 25 September 2026): shown only to a holder of
`EQUIPMENT_IDENTITY_READ`. For anyone else, a machine's `engine_number` and `chassis_number` are `null` with
`identity_numbers_withheld: true`; a correction of either field shows its field, who and when, with
`plum_value`, `corrected_value`, `corrected_value_label` and `reason` `null` and `values_withheld: true`; a
value rule in either column shows `plum_value: null` and `reason: null` with `value_withheld: true`. The
reason is withheld with the values because Admin may well repeat the numbers in it (independent review,
round 2, ERT1-R2-002); a correction or rule of any other field keeps its reason for every read role. This holds for every response that
can carry them - one machine, the machine writes, `/corrections`, `/value-rules` and a value rule's write.
Nothing else carries them: the machine list, import previews (Admin only) and events never do. The
machine number (registration) is shown to every read role. Whether Operations - and Finance, for audits -
should see them is the owner's to decide; either is a grant, with no code change.

## Conventions

- Errors are `{"detail": "..."}` in plain words: `404` not found, `409` someone changed it since it was
  read (or a preview is out of date, or the report was already imported), `422` refused, `413` too large,
  `401` / `403` as elsewhere. Unknown request fields are refused (`422`).
- Every write takes the version it was made against (`expected_asset_version`, `expected_model_version`,
  `expected_preview_version`) and refuses a stale one with `409`. Fitting and removing a part change the
  part as well as the machine, so they also take `expected_part_version`.
- A machine's version moves on exactly once for every write that changes its record - a fact, a flag, a
  correction, a fitted part, what its latest report says of it, or its model - whether the change comes
  from a write on its page, a model's change, or a confirmed report. The date of the report its facts are
  from, and which import last read it, are bookkeeping: a draft is never made against them, so they move
  nothing (independent review, round 1, ERT1-R1-004).
- Every write takes the module's one write lock for its transaction; writes are few and made by one or
  two people, so they are simply serialized.
- A create that carries a `create_request_key` - a model, a lot of kit - follows the platform's one replay rule
  (MCF-001: a retry or repeated submission has no duplicate effect; TB-1 finding TB1-102 part b, 8 October 2026;
  `app/shared/request_keys.py`, the rule Resource Assignments built first). The record keeps the SHA-256 of the
  request that made it: the fields sent with their values - a field left out is not the field sent empty - without
  the key. The same request with the key again is answered `201` with that record, `replayed: true` and no event;
  the key with any other request is `409` ("This form was already used to ..."), and nothing is recorded. A record
  made before migration `20260908_0050` kept no fingerprint, so its key is `409` whatever is sent - never taken for
  a request it may not have been. Two requests with one key at once make one record: the write lock serializes
  them, and the second is answered as above. A key is looked up within its kind of create: models among models, a
  lot among kit. **Reconciled 8 October 2026:** until then a model's key replayed on the key alone and a lot's on
  its kit model alone, so a changed request was answered with the first record and the change dropped silently.
- The request body of every route is counted as it arrives and refused past 5 MB plus 256 KB, before it
  is parsed and so before authentication (Slice 9C's rule).
- A capability value is always in the capability's own unit, which is never sent.

## The Plum report import

```text
POST /api/equipment-reference/imports                   multipart: file, report_date    201
GET  /api/equipment-reference/imports?limit&offset       summaries, newest first         200
GET  /api/equipment-reference/imports/{id}               one import with its preview     200
POST /api/equipment-reference/imports/{id}/refresh       {expected_preview_version}      200
POST /api/equipment-reference/imports/{id}/publish       {expected_preview_version, pairs[]}  200
POST /api/equipment-reference/imports/{id}/discard       {expected_preview_version}      200
```

**Upload.** A CSV of at most 5 MB (`413` beyond it). The header is looked for in the first five lines
(line 1 of Plum's export is a title); every used column must be present - `VehicleNo,
ScheduleMaintanceType, Make, Model, VehCategory, Status, Capacity, LoadCapacity, EngineNo, ChassisNo,
CommencedYear, Owner, BedNo` - or the upload is refused naming the missing ones (`422`). UTF-8 with or
without a byte-order mark, or Windows-1252. At most 20,000 rows. `report_date` may not be in the future
(Asia/Kolkata). The file is read in memory and discarded: the import keeps its SHA-256 fingerprint, its
row count, the report date and, for each row, only the used values. The same file as any confirmed
import is refused (`409`, "This report was already imported on 25 September 2026."); the same file as a
preview still waiting returns that preview (`201`, `replayed: true`).

**Response** (`ImportActionResponse`): `equipment_import`, `replayed`, `event` (only on confirmation).
`equipment_import` carries `import_public_id, import_status_code (PREVIEWED | PUBLISHED | DISCARDED),
report_date, row_count, fingerprint_prefix (12 characters), uploaded/published/discarded by and at,
discard_reason_code (BY_FLEET_ADMIN | SUPERSEDED), counts, preview_version, preview_computed_at,
is_current, stale_reason, based_on_import_public_id, preview`.

`preview`:

```text
counts                  NEW, CHANGED, UNCHANGED, RETIRED, REACTIVATED, NOT_BROUGHT_IN, SET_ASIDE, MISSING
rows[]                  row_number (the line in the file), machine_number, outcome_code, reason_code,
                        asset_public_id / asset_reference (a machine already held), kind_code,
                        class_code / class_label, type_code / type_label, model_public_id / model_label,
                        status_code, changed_facts[], flags[{flag_code, subject_code}],
                        rules_applied[{rule_public_id, column_code, action_code, plum_value, result_number,
                          result_unit_code, result_class_code, result_type_code}],
                        corrections[{correction_public_id, field_code, effect_code, corrected_value_label}],
                        closing_links[] (below), plum{category, model_name, capacity, commenced_year, status},
                        needs_attention
missing[]               machines held but not in this report: asset_public_id, asset_reference, machine_number
closing_links[]         fitted-part links confirming will close: machine_asset_public_id, machine_machine_number,
                        part_asset_public_id, part_machine_number, because (KIND_CHANGED | CLASS_CHANGED)
unmapped_model_names[]  source_name, category, class_code, make, model, machine_count
pair_proposals[]        part_machine_number, proposed_machine_number (only when exactly one machine of
                        the part's model name has no such part), candidates[{machine_number, asset_reference}]
```

Outcome reasons: set aside - `NO_MACHINE_NUMBER`, `VALUE_TOO_LONG`, `DUPLICATE_SOURCE_KEY`,
`CATEGORY_NOT_MAPPED`, `STATUS_NOT_RECOGNISED`; not brought in - `INACTIVE_NOT_KNOWN`, `CLASS_NOT_USED`.
Correction effects: `APPLIED`, `PLUM_AGREES` (closes on confirmation), `PLUM_CHANGED` (applied and flagged).
A row set aside takes nothing in, a correction's lifecycle included: it shows no correction effects, an
agreeing value in it closes nothing and a third value in it flags nothing, until a row that is taken in
says so (independent review, round 4, ERT1-R4-003).

Each row names every correction and every value reading it was read with, and such a row is
`needs_attention` even with no flag left, so a confirmation never takes a corrected or re-read value in
unseen (ERT1-R1-006). The preview is kept as the import's record, so it never repeats an engine or chassis
number: for those fields `corrected_value_label` and a reading's `plum_value` are `null`.

When the report changes the kind or class of a machine or part so that a fitted part no longer fits its
machine - the same rules as fitting one - the preview says so before anything changes: the link is in
`closing_links` and in both rows (each then `needs_attention`), the part's row is flagged
`PART_NOT_FITTED`, and the pairs proposed start from the state confirming will leave, so the part can be
paired again in the same confirmation. Confirming closes exactly those links, first (independent review,
round 3, ERT1-R3-001).

**Currency of a preview.** `is_current` is false, with `stale_reason`, when another report was confirmed
after the preview was made, or when anything it is computed from changed since - a model, a mapping, a
value rule, a correction, a machine's own values, a pair (the change count in `equipment_reference_state`).
A machine's serial number and year of manufacture do not change a preview.

**Refresh** recomputes the preview from the rows already read (`preview_version` + 1). Refused (`422`) for
a confirmed or discarded import.

**Publish** confirms. Refused `409` for a stale version, another confirmed report, or a changed context
("Refresh it"); `422` for a discarded preview or a pair that breaks the rules (the message names the two
machine numbers). A second call on a confirmed import returns it with `replayed: true` and `event: null`:
nothing is done twice. In one transaction it registers new machines and parts, updates the ones held
(version + 1, once, for each whose facts, flags, corrections, links or reported values changed; a machine
the report leaves as it was keeps its version), retires and reactivates, flags the missing (`NOT_IN_LATEST_REPORT`,
never retired), closes corrections Plum now agrees with, closes the preview's `closing_links` - each on
the report date, or on the day it was fitted if the report is older, never before (ERT1-R3-005) - fits the
confirmed `pairs[{part_machine_number,
machine_machine_number}]` dated the report date, recomputes `PART_NOT_FITTED` for every part, keeps the
preview as the import's record, and discards every other waiting preview (`SUPERSEDED`).

**Discard** marks a preview discarded (`BY_FLEET_ADMIN`); discarding a discarded one returns it; a
confirmed one is refused (`422`).

## Machines

```text
GET  /api/equipment-reference/machines?kind_code&class_code&type_code&status_code&flagged_only
                                          &details_to_complete&search&limit&offset         200
GET  /api/equipment-reference/machines/{id}                                                200
PUT  /api/equipment-reference/machines/{id}/details        {expected_asset_version, serial_number, year_of_manufacture}
PUT  /api/equipment-reference/machines/{id}/capabilities   {expected_asset_version, capabilities[{capability_code, value | choice_value, reason}]}
POST /api/equipment-reference/machines/{id}/corrections    {expected_asset_version, field_code, corrected_value, reason}   201
POST /api/equipment-reference/machines/{id}/corrections/{correction_id}/close   {expected_asset_version}
POST /api/equipment-reference/machines/{id}/fitted-parts   {expected_asset_version, part_public_id, expected_part_version, fitted_on}   201
POST /api/equipment-reference/machines/{id}/fitted-parts/{part_id}/remove   {expected_asset_version, expected_part_version, removed_on}
```

The list (`MachineSummaryResponse`): `asset_public_id, asset_reference (EQ-000001), asset_kind_code
(MACHINE | PART), machine_number, class/type/model codes and labels, key_capability, asset_status_code
(ACTIVE | RETIRED), flag_codes[], details_missing, facts_report_date, asset_version`. `search` matches the
machine number or reference, literally. One machine (`MachineResponse`) adds Plum's facts (`engine_number,
chassis_number, commenced_year, owning_company`), the platform's (`serial_number, year_of_manufacture`),
`capabilities[]` (each with `source_code` OWN | MODEL | NONE and, for OWN, the reason, who and when),
`flags[]`, `corrections[]` (open first), `fitted_parts[]`, `fitted_to`, `link_history[]`, `plum{category,
model_name, capacity}` - Plum's own words from the latest report, for the Fleet Admin - and freshness.

- **Details** are the platform's facts; the transformer never writes them. An identical save records
  nothing (`event: null`). The year of manufacture is not later than the current year in Asia/Kolkata
  (`422`); ERT-1 had allowed next year, with no recorded reason, until the owner's ERT-2 screen check (27
  September 2026). The same holds for a piece of kit, on its details and when it is added.
- **Own values** replace the machine's own values as a whole; one left out takes the model's rating again.
  Each needs a reason. Parts have none. Plum's capacity figure is checked against them, so the machine is
  re-read at once: a `DIFFERS_FROM_MODEL` flag is cleared or raised in the same save (ERT1-R1-007).
- **A correction** replaces one Plum value of one machine: `CATEGORY` (a class code), `MODEL` (a model
  public id), `ENGINE_NUMBER`, `CHASSIS_NUMBER`, `COMMENCED_YEAR` (four digits), `OWNING_COMPANY`,
  `STATUS` (`ACTIVE` | `INACTIVE`), `CAPACITY` (a plain figure in the category's unit, for the check). The
  machine number cannot be corrected (`422`). The Plum value it replaces is taken from the latest report,
  never from the request; a value Plum already holds is refused. It applies at once - the machine is
  re-read from its latest report's values - and on every later import; a newer correction of the same
  field replaces the open one (`SUPERSEDED`). Closing one re-reads the machine as Plum gives it. When the
  re-reading changes the record's kind or class, every fitted-part link it is in is checked again by the
  rules below, and each that no longer holds - a carrier on what is now a forklift, say - is closed, dated
  today (Asia/Kolkata); a part left unfitted is flagged `PART_NOT_FITTED` at once (ERT1-R2-003). A report
  does the same through its preview's `closing_links`.
- **Fitting a part**: the part must be a part, active, fitted nowhere else, of a class that fits the
  machine's class; the machine active and carrying no part of that class; the date not in the future
  (Asia/Kolkata). Both are guarded - the part by `expected_part_version`, as the list or the machine page
  showed it (`409` when it changed since) - and both versions move on. Removing is guarded the same way,
  keeps the link as history, dated, and flags the part `PART_NOT_FITTED` (ERT1-R1-003). A fitting never
  begins before the part was last removed from a machine, or the machine last lost a part of that class: the
  history would show one part on two machines at once. The page refuses such a date (`422`, naming the
  day); a pair confirmed with a report is dated the report's date or, if later, that day (ERT1-R4-004).

## Models and mappings

```text
GET  /api/equipment-reference/models                                                  200
POST /api/equipment-reference/models          {maker, model_name, class_code, type_code, capabilities[], create_request_key}   201
PUT  /api/equipment-reference/models/{id}     {maker, model_name, class_code, type_code, capabilities[], is_retired, expected_model_version}
PUT  /api/equipment-reference/model-mappings  {source_name, model_public_id | null}   200
```

A model (`EquipmentModelResponse`) carries its class (a machine class or a part class), type, rated
capabilities, the Plum names mapped to it, and how many machines use it. Maker and name are unique within
a class (`409`): a crane "ACME AC 100" and its carrier "ACME AC 100" are two models of two classes, which
is how a carrier is proposed to its crane. A write answers `EquipmentModelActionResponse`: `model`, `event`
(`null` when nothing was recorded) and `replayed`. The same request with the same `create_request_key` again
returns the first model with `replayed: true` and `event: null`; the key with any other request is `409`
(Conventions). A model's class cannot change while machines use it (`422`); a retired model keeps its
machines and mappings but cannot be newly mapped. A change of a model's type or ratings re-reads every
machine of it at once: its type follows the model's, and the capacity check is made again against the new
rating. A machine whose facts changed records `EQUIPMENT_ASSET_CHANGED`. Every machine of the model moves
its version on, whatever changed - what a machine shows of its model and ratings comes from the model
(ERT1-R1-007). A mapping names a model for a Plum model name
(normalized: spacing and case do not matter); with `model_public_id: null` it is removed. Mappings take
effect on the next preview.

## Value rules, corrections to send, category rules

```text
GET  /api/equipment-reference/value-rules?open_only                                   200
PUT  /api/equipment-reference/value-rules     {column_code, plum_value, action_code, result_number,
                                               result_unit_code, result_class_code, result_type_code,
                                               reason, import_public_id}              200
POST /api/equipment-reference/value-rules/{id}/close                                  200
GET  /api/equipment-reference/corrections                                             200
GET  /api/equipment-reference/category-rules                                          200
```

A value rule reads one Plum value wherever it appears in a column (`CAPACITY`, `COMMENCED_YEAR`,
`ENGINE_NUMBER`, `CHASSIS_NUMBER`, `OWNING_COMPANY`): `SPLIT_NUMBER_AND_UNIT` (capacity only: a number and
a unit), `REASSIGN_TO_TYPE` (capacity only: a live type of a live machine class; applies to machines of
that class, whose model gives no type), `NOT_A_VALUE` (nothing was entered). A rule for the same value in
the same column replaces the open one; the same rule again records nothing. A rule stays open until the
Fleet Admin closes it: an export may be partial, so a report without the value does not close it.
`import_public_id` records the preview it was recorded on. `/corrections` lists every open rule (with how
many rows of the latest confirmed report still carry its value) and every open machine correction (with
whether Plum now holds a third value). `/category-rules` lists section 6 of the design: what Plum's
capacity figure means in each category, in what unit, within what plausible range - changed by migration.

## Detachable kit (ERT-2)

Kit is recorded on the platform, never read from Plum, and **held for the crane models it fits** - shared
by every machine of them, never linked to one (owner, Q6 and Q12). Nothing below changes the Plum report
import: a report never creates, changes, retires or flags a piece of kit.

```text
POST /api/equipment-reference/kit                         {create_request_key, machine_public_id,
                                                           expected_asset_version, kit_model_public_id,
                                                           expected_model_version, count, serial_number,
                                                           year_of_manufacture}                          201
POST /api/equipment-reference/machines/{id}/retire        {expected_asset_version, reason_code, note,
                                                           retired_on, count}                            200
```

**The structure, version 3** (`GET /structure`). Four part classes are kinds of kit, offered to no business
line: `BOOM_JIB_SECTION` (key capability `LENGTH`, m), `COUNTERWEIGHT` (`WEIGHT`, t), `HOOK_BLOCK` and
`LIFTING_TACKLE` (`RATED_CAPACITY`, t); every one is also measured by `WEIGHT` (owner, Q13). Each class now
carries `tracking_code` (`SINGLE`, or `COUNTED` - counterweight - where one record holds a counted set) and
`kit_for_class_codes` (the machine classes it is kit for: `CRANE`); `fits_class_codes` lists only fitted
part fits, so the crane carrier's is unchanged and a kind of kit's is empty. The response and each version
carry `component_depth`, the depth setting (3): a machine is level 1, and fitted parts nest no deeper.

**Kit models.** `POST /models` and `PUT /models/{id}` take `fits_model_public_ids[]` - for a model of a kind
of kit, one or more crane models of the classes it is kit for, none twice, none newly chosen once retired
(`422` otherwise, `404` for one not found); for any other model the list must be empty (`422`). Both take
an optional `maker_part_number` (up to 100 characters) for any model. A model response adds `is_kit`,
`fits_models[{model_public_id, label}]`, `pieces_held` (active pieces, a counted set by its quantity),
`fits_no_active_crane` (none of the models it fits has an active machine: kit left behind, owner Q7),
`active_unit_count` (a machine model's active machines) and `maker_part_number`. A machine model that kit
fits cannot change class (`422`); nor can a kit model while pieces use it. `PUT /model-mappings` refuses a
kit model (`422`: no Plum model name is mapped to one), and so does a `MODEL` correction; and a model Plum
names are mapped to cannot change into a kind of kit (`422`, ERT2-R3-001).

**Adding pieces** (`POST /kit`). Kit is added from a machine's page, so the request names that machine and the
versions of it and of the kit model the page showed: a changed machine or kit model is refused (`409`), and so
is a kit model that does not fit the machine's current model (`422`), rather than adding pieces on a premise
that no longer holds (independent review, ERT2-R1-001). The machine and the model must exist (`404`), and the
model must be a live kit model (`422`). For a kind tracked one by
one, `count` records of one piece each are made - "add several alike" - and `serial_number` (the piece's own
number) is accepted only when `count` is 1; for a counted kind, one record of `count` pieces, with no number.
`count` is 1 to 50. The records are one lot: the same request with the same `create_request_key` again
returns them with `replayed: true` and no events (ADR-023); the key with any other request - another kit model,
count, number or year included - is refused (`409`, Conventions; until 8 October 2026 only another kit model was).
The request is judged as it was sent, kept with each record and never changed, so a piece later moved to another
model changes nothing (ERT2-R2-001). Response (`KitAddResponse`): `pieces[]` (machine summaries),
`replayed`, `events[]`. A piece is in no report, so adding one leaves every waiting preview current.

**A piece of kit** reads through the machine routes. Its summary has `origin_code: PLATFORM`,
`machine_number: null` and `quantity`; its page adds `fits_models[]` and, once retired, `retired_on`,
`retirement_reason_code` and `retirement_note`. Its details (`PUT /machines/{id}/details`) are its own number
(one tracked one by one), year of manufacture, `quantity` (a counted set's count - raised only: a set shrinks
only by retiring pieces, `422` otherwise) and `model_public_id` (another model of the same kind, not
retired). A Plum machine refuses `quantity` and `model_public_id` (`422`). A piece may hold its own
capability values, with a reason, where its kind has capabilities (`PUT /machines/{id}/capabilities`).
`details_missing` is true for a piece tracked one by one without its own number. Kit is never fitted:
`POST /machines/{id}/fitted-parts` refuses a kind of kit (`422`), and "belongs to no machine"
(`PART_NOT_FITTED`) is raised only on parts of fitted classes.

**A machine** (`GET /machines/{id}`) adds `kit[]` - every kit model fitting its model, with `pieces_held`,
`records_held`, `tracking_code`, `key_capability` and `fits_models` - and `model_active_unit_count`, the
active machines of its model that share that kit. A machine with no model yet has no kit.

**Retiring** (`POST /machines/{id}/retire`). Kit only: a Plum machine or carrier is refused (`422`, "Plum
retires this machine; correct its status if Plum is wrong"). `reason_code` is `SCRAPPED`, `LOST`, `SOLD`,
`RECORDED_BY_MISTAKE` or `OTHER`; `note` is required with `OTHER`; `retired_on` may not be in the future
(Asia/Kolkata). `count` retires that many pieces of a counted set - between 1 and its quantity - leaving the
set active and smaller; left out, or equal to the quantity, the whole record is retired. A retired piece
stays readable and is not counted as held; retiring it again returns it unchanged with `event: null`,
whatever version is sent. A stale version otherwise is refused (`409`). A counted set may not shrink below what
its trips list at once on any day from today on (Asia/Kolkata): `422` naming that number and the allocations, with
nothing changed - list fewer on those trips first, or retire fewer (TB-1 finding TB1-307, 4 October 2026). Retiring
a whole set or piece stays allowed; its allocations then show it as retired and need replacing or freeing (8A,
from RMR-001). The check reads Resource Assignments' listings under its lock, taken before this module's and the
piece's row - the order Eligibility's "seen" marks take - through the port `KitListingSource` (`ports.py`), which
Resource Assignments registers.

**The machine list** (`GET /machines`) takes `kit_model_public_id` (one kit model's pieces) and
`fits_model_public_id` (the kit held for one machine model); `search` also matches a piece's own number.

**Events.** No new event name. `EQUIPMENT_ASSET_REGISTERED` for each piece, with `origin_code`, `class_code`,
`model_public_id`, `quantity` and `records_in_lot`; `EQUIPMENT_ASSET_RETIRED` with `reason_code`,
`retired_on`, `quantity_retired`, `quantity_after` and `whole` - the note is the event's reason, never its
payload; `EQUIPMENT_MACHINE_DETAILS_SET` names `quantity` and `model` among the changed fields, with the
counts or models before and after; `EQUIPMENT_MODEL_RECORDED` and `EQUIPMENT_MODEL_CHANGED` carry a kit
model's `fits_model_public_ids`, and which were added and removed. No payload carries a piece's number or
free text.

**For the Fixed Assets module, later** (owner, 26 September 2026). A piece's public id and `EQ-` reference
never change and are never reused; nothing is deleted; each "add" is one lot; every change of state is an
event with its day and reason, and a counted set shrinks only by a retirement that says how many and why. A
future Fixed Assets module links its own records to these by public id and needs nothing more from here.

## Flags

`CATEGORY_NOT_MAPPED, MODEL_NOT_MAPPED, CLASS_DISAGREES, NOT_A_NUMBER, OUT_OF_PATTERN, DIFFERS_FROM_MODEL,
UNIT_UNCLEAR, VALUE_MISSING, NOT_IN_LATEST_REPORT, POSSIBLY_RENUMBERED, PART_NOT_FITTED,
DUPLICATE_SOURCE_KEY, PLUM_CHANGED_CORRECTED_VALUE`, each with a subject (a capability or field code, or
empty for the whole machine). A flag stays until an import no longer raises it or its cause is removed.

## Events

Record types: `equipment_import`, `equipment_asset`, `equipment_model`, `equipment_value_rule`.

`EQUIPMENT_IMPORT_PUBLISHED` (counts, fingerprint prefix, report date, row count, parts fitted,
corrections closed), `EQUIPMENT_ASSET_REGISTERED`, `EQUIPMENT_ASSET_CHANGED` (changed facts by name),
`EQUIPMENT_ASSET_RETIRED`, `EQUIPMENT_ASSET_REACTIVATED`, `EQUIPMENT_MODEL_RECORDED`,
`EQUIPMENT_MODEL_CHANGED`, `EQUIPMENT_MODEL_MAPPED` (model and previous model; not the name - recorded
under record type `equipment_model_mapping` and the mapping's own identity: a UUID v5 of its provider and
normalized name, the mapping's key, in the namespace `contract.MODEL_MAPPING_NAMESPACE`, so it never lands
on a model the mapping merely points at - ERT1-R3-004),
`EQUIPMENT_PART_FITTED`, `EQUIPMENT_PART_REMOVED` (`because` `KIND_CHANGED` or `CLASS_CHANGED` when a
re-reading, not the Fleet Admin, removed it), `EQUIPMENT_MACHINE_CAPABILITY_SET`,
`EQUIPMENT_MACHINE_DETAILS_SET`, `EQUIPMENT_VALUE_RULE_RECORDED`, `EQUIPMENT_VALUE_RULE_CLOSED`,
`EQUIPMENT_CORRECTION_RECORDED`, `EQUIPMENT_CORRECTION_CLOSED` (by the Fleet Admin, or `PLUM_AGREES`).
Payloads carry public ids, references, codes, versions, counts and dates only: no machine, engine or
chassis number, no Plum value, no reason text.

## Consumers

Consumers read machines through `plum_source.PlumReportEquipmentSource` (`EquipmentSourcePort`), which
returns `CanonicalMachine`s - public id, reference, class, type, model, status, version, `facts_as_of` and
capabilities in their own units - never a binding, an import row or a Plum value.

*Reconciled 8 October 2026 (TB-1 TB1-610):* no consumer does. Nothing calls the port or its Plum adapter.
8A core reads through the service functions below, Eligibility through `service.py`'s asset reads
(`get_asset_with_fitted_parts`, `list_active_assets_with_fitted_parts` and others), and Resource Requirements
through its structure and class reads - which equally return no binding, import row or Plum value. The port
is kept, not wired, as ADR-037's seam for a second source of machines (`ports.py` says so).

8A core (28 September 2026) reads through four service functions, with no route:

```python
service.machines_for_allocation(db, *, class_code) -> list[AllocationAsset]   every active machine of the class
service.allocation_asset(db, public_id) -> AllocationAsset | None             one machine or piece, whatever its status
service.kit_for_machine(db, machine_public_id) -> list[AllocationAsset]       the active pieces of every kit model
                                                                              that fits the machine's model (ERT-2);
                                                                              none when it has no model
service.asset_references(db, public_ids) -> dict[str, str]                    each asset's EQ- reference
```

An `AllocationAsset` carries the public id, reference, kind, origin, machine and serial numbers, class, type,
model, status, version, quantity, tracking, flags, and each capability that has a value - the machine's own where
the Fleet Admin set one, else its model's rating. A capability with no value is left out: unknown is never a value.
Eligibility's stored decisions name their assets through `asset_references`.

## Data

Migration `20260908_0042`: structure version 2 (`equipment_class.class_kind_code`, `equipment_part_fit`,
the class `CRANE_CARRIER`); `equipment_model`, `equipment_model_capability`, `equipment_model_source_key`;
`equipment_asset`, `equipment_asset_capability`, `equipment_asset_link`, `equipment_asset_flag`;
`equipment_source_import`, `equipment_source_import_row`, `equipment_source_binding`,
`equipment_source_category_rule`, `equipment_reference_state`; `equipment_source_value_rule`,
`equipment_asset_correction`; the permission and its grant to Admin.

Migration `20260908_0043` (ERT-2): structure version 3 (`equipment_taxonomy_version.component_depth`,
`equipment_class.tracking_code`, `equipment_part_fit.fit_kind_code` with a part class allowed as the parent of
a fitted fit, the capabilities `LENGTH` and `WEIGHT`, the four kinds of kit); `equipment_model.maker_part_number`;
`equipment_model_fit` (a kit model and a crane model it fits, held to the part fits by composite keys);
`equipment_asset.origin_code` (`PLUM` or `PLATFORM`; `machine_number` now only for `PLUM`), `quantity`,
`create_request_key`, `create_request_position` and `create_request_model_id` (the kit model the request asked
for), `retired_on`, `retirement_reason_code`, `retirement_note`; the trigger `equipment_asset_matches_tracking`
(a quantity above one only on a counted kind, a piece's own number only on one tracked one by one, a platform
record only of a kind of kit and a kind of kit only on the platform, and the request that made a record never
changed); the CHECK `ck_equipment_asset_retirement` (a retired piece with its day and reason); and the trigger
`equipment_class_tracking_matches_assets` (a kind's tracking never changed under records it would no longer
fit). No permission is added.

Migration `20260908_0050` (TB-1 TB1-102 part b): `create_request_fingerprint` on `equipment_model` and
`equipment_asset` (every record of a lot carries its request's), and on Resource Requirements'
`resource_requirement` - 64 hexadecimal digits, only on a record a request key made
(`ck_<table>_create_request_fingerprint`); null on a record made before it, which is not given one. The trigger
function `create_request_kept` refuses a change to a record's key or fingerprint, as ERT-2's trigger already did
for a lot's key, place and model asked for. No route, permission or event is added; a model's answer gains
`replayed`.

## What is unchanged

The structure's other rows, the requirement routes and the frozen Slice 6D.1 handoff.
