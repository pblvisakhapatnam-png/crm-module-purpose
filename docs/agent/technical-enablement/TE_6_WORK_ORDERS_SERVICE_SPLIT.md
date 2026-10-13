# TE-6 - Splitting the Work Orders service

## Status

**IMPLEMENTED AND MERGED, 23 September 2026**: committed as `79f8342`, merged through PR #66 as
`dc0d119`. Four independent review rounds - the fourth authorized by the owner beyond the three-round cap - found nine
material points, all corrected or, for one, settled by the owner's decision. **The owner chose to commit
without a fifth round**: round 4's one finding is corrected but was not re-reviewed, so there is no
ACCEPTED verdict. Every finding from round 2 on concerned the importer scan. That scan is review
evidence, not application code, and nothing in the application runs it. Round 4's reviewer called the
rest of the evidence strong.
See "As built" below; the brief that follows it is kept as written.

**The proof scripts are kept in `te-6-proof-scripts/`**, beside this file. It holds every script
exactly as it ran, their outputs and the four review verdicts. Its README says how to adapt them. It is
the place to start when `commercial_offers/service.py` is split.

*Reconciliation, 8 October 2026 (TB-1 TB1-605, corrective package CS-12):* `services/common.py` no longer defines
`_rollback_on_error` or `_india_today`. The Work Orders writes use `rollback_on_error` from `app/shared/transactions.py`
and read today through `app/shared/business_time.py`, which the other Hiring modules share; `INDIA_TIME_ZONE` is still
on the service, now the shared zone object. What this record says TE-6 built and proved is unchanged.

*Reconciliation, 8 October 2026 (TB-1 CS-11):* `commercial_offers/service.py` is now split by this record's method; see
`CS_11_COMMERCIAL_OFFERS_SERVICE_SPLIT.md` beside this file. Its adapted scripts, in `cs-11-proof-scripts/`, are the
place to start a next split.

The brief was written at the project owner's direction immediately after Slice 7D Part 3 merged
(`944af54`), so the next session starts from a defined scope rather than re-deriving it. Technical
enablement, not a numbered business slice: **no behaviour changes, at all.**

```text
Baseline              944af54 (origin/main, PR #64 merged)
Branch                technical-enablement/te-6-work-orders-service-split (suggested)
Migration             NONE. If this package needs a migration, its scope is wrong.
Frozen contract hash  70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a, must not change
Review                bounded packet, three-round cap; a fourth needs the owner's authorization
Sequencing            BEFORE Slice 7D Part 4, which adds terms to the very functions this moves
```

## As built, 23 September 2026

Built on `technical-enablement/te-6-work-orders-service-split` in its own worktree, from `1d7515f`
(`944af54` plus this brief; no backend file differs between them). No behaviour, API, route,
permission, event, schema or migration changed.

### The layout

```text
backend/app/modules/work_orders/
  service.py                    109  re-exports, by name, all 40 public names the original defined; __all__ matches
  services/__init__.py            1
  services/common.py            267  the 11 exceptions; the helpers two or more concerns call, among them
                                     reading the contract bounds and gaps; _rollback_on_error
  services/handoff.py           229  creating a Work Order from an accepted offer, and the reads
  services/amendments.py        886  Slice 6O.2, with the six validators only it used
  services/line_detail.py       428  Slice 7C
  services/billing_terms.py    1305  Slice 7D Parts 1 and 2, and copying terms between lines (Part 3)
  services/contract_period.py   693  Slice 7D Part 3: the contract period and its extensions
```

No module under `services/` imports another except `common`, and nothing needed an exception to that.
The total grew from 3,529 lines to 3,918: each module carries its own imports and docstring, and the
functions item 2 broke up gained `def` lines and docstrings. The split makes the code easier to
navigate, not shorter.

The longest functions are now ones this package did not touch: `create_work_order_contract_extension`
(130), `create_work_order_from_commercial_offer` (128) and `save_work_order_line_detail` (118). The
three it did touch went from 191, 152 and 112 lines to 73, 21 and 6, with helpers of at most 74.

### Where the build departs from the brief, and why

1. **Copying terms lives with billing terms, not the contract period.** The brief suggested
   `contract_period.py`. The copy is built on the billing-terms read-back (`_work_order_billing_terms`,
   which brings the response builders and the missing-items rules with it) and on the billing-terms
   conflict message; from the contract-period section it needs only the Work Order lock. Placed with
   the contract period, half of billing terms would have had to move to `common`. It is also a write of
   billing terms, under the billing-terms permission.
2. **Item 3 is a rollback helper, not a preamble helper.** The fifteen writes share their close word for
   word - `except Exception: db.rollback(); raise` - but not their opening. The eight 7C, 7D and Part 3
   writes lock and validate inside the `try`. The seven handoff and amendment writes lock and validate
   before it, so a refusal there is not rolled back by the write and the lock lasts until the session
   ends. Folding the lock into one helper would roll those back earlier: a behaviour change, however
   harmless. The openings also differ among themselves - three lock helpers with their own
   closed-Work-Order messages and check orders, and version checks over different fields raising
   different errors. So `with _rollback_on_error(db):` replaces exactly the shared close in all fifteen,
   and each keeps its explicit `db.commit()` as the block's last statement, where a reader sees what the
   transaction holds. It is a small class rather than `@contextmanager`, so no generator sits between
   the error and the rollback.
3. **Item 2 splits along seams, not into a table.** The brief allowed this conclusion. The field
   dictionary in `_normalize_billing_terms` already is the table - one entry per column - and its order
   is behaviour: it decides which refusal a request with two faults receives, and the order of
   `changed_fields` in every event. A loop over a rule table would keep every message and add lambdas for
   the conditions. What makes Part 4 cheap is the seam the terms arrived by: `_normalize_billing_terms`
   now reads `_part_1_term_values` and `_part_2_term_values`, sets the rates, then runs
   `_check_part_1_terms` and the existing `_check_part_2_terms`; `_period_missing_items` is
   `_part_1_missing_items` + `_part_2_missing_items`. Part 4 adds a third of each. The copy is split
   along its own sequence: `_copy_source_line`, `_copy_source_periods`, `_copy_target_lines`, and
   `_copy_terms_to_line` for one line in its savepoint.
4. **The exceptions stay together in `common`** although the rule "a helper one concern uses moves with
   it" would scatter most of them. They are the module's error vocabulary, which `routes.py` maps to
   HTTP statuses in one place.
5. **Four test files changed, which the brief did not foresee.** Five monkeypatches swapped repository
   functions on `service`. After the move a function looks those names up in its own module, so the
   patches now target `services.line_detail` and `services.billing_terms`. And the Slice 9B
   amendment-accessor inventory walked `vars(service)`, keeping only functions defined in `service`
   itself; after the split there are none, so it now walks every module of the package. No assertion
   changed. Each original was run against the split and failed - none could have passed vacuously -
   which is recorded below. The brief's "do not tidy" instruction was about import paths, and none was
   touched.
6. **The brief mislabelled one count.** "351 passed together" is Part 3 rules (47) + Part 3 routes
   (128) + route guard (99) + harness (77), not 7C and 7D. The ten files that test Work Orders come to
   725 on the baseline.
7. **`service.py` re-exports every public name the original defined - 40 - not only the 37 other files
   import today.** The brief asked for the 37. Independent review round 1 (finding F-01) pointed out that
   the owner's no-API-change rule outranks that: `contract_bounds_for_work_order`,
   `contract_gaps_for_work_order` and `INDIA_TIME_ZONE` were public on the original module, and code
   written against it would have lost them. A new test,
   `backend/tests/test_te6_work_orders_service_surface.py`, pins the 40 names, requires `__all__` to be
   exactly them, and requires each to be the very object its concern module defines.

   **The names the original only imported are not re-exported, by the owner's decision of 23 September
   2026.** Round 2 (finding R2-F01) pointed out that, having no `__all__`, the original also exposed every
   non-underscore name it imported - 221 of them: repository functions, schemas, contract constants, even
   `date` - and that `from ... import *` handed all 261 out. It offered two ways forward: restore them
   all, or have the owner approve the narrower surface. The owner approved the narrower surface. Nothing
   in the repository takes any of the 221 through the service (the importer scan, below, is fail-closed
   and says so), and re-exporting repository functions through the service would re-open the trap item 5
   fixed: a test patching a name on the service rather than where the function looks it up, silently
   patching nothing. The 221 are listed by name in the review packet's runtime-check output.

### What proves nothing moved

Eight checks. Each script was carried in the review packet and is now kept, with its output, in
`te-6-proof-scripts/`. The first four were in round 1; the other
four answer review findings F-02 and F-03 (round 1), R2-F02 and R2-F03 (round 2), R3-F01 (round 3)
and R4-F01 (round 4), which showed that
byte-identical text alone did not rule out a moved function reading a same-named object from somewhere
else, and that a check must fail on what it cannot resolve rather than pass it:

- **Text.** Each of the original 104 top-level definitions exists exactly once under `services/`. 87 are
  byte-identical to `944af54`; the other 17 are the declared exceptions below, and nothing new appears
  undeclared. Every top-level comment survives - the five section banners became module docstrings,
  set side by side in the packet. No module imports a name it does not use, or uses one it neither
  defines nor imports.
- **The rollback helper.** For each of the fourteen writes not otherwise rewritten, the original's AST,
  with its one outer `try/except Exception: db.rollback(); raise` replaced by
  `with _rollback_on_error(db):` around the same body, equals the new AST. (Stage 2 on its own showed
  the same for all fifteen, before the copy was split.)
- **The two pure rewrites.** The original module, loaded from the `944af54` text, and the new one gave
  identical results on 300,000 generated inputs each - the same values in the same key order, or the
  same error and message. 86,967 of the payloads were accepted. The inputs reached 48 of the 49
  refusal messages, and all 16 missing-item codes. The one not reached is a defensive check in
  `_check_part_2_terms`, unchanged by this package, which earlier checks make unreachable, as its own
  comment says.
- **The copy.** The original and the new copy ran 21 scenarios against the same recording fakes: every
  refusal, the success paths, a failure injected at each write step of one line, a failed read-back and
  a failed commit. The traces - every call and its arguments, savepoints, commit and rollback, in order -
  and the results were identical.

- **Every import binding.** Each of the 318 names the new modules import is imported from the same
  module, under the same name and alias, as the original imported it - or is a name the original
  defined itself, now imported from `common` under its own name, or `types.TracebackType` for the new
  helper. Nothing else runs at import: every top-level statement is a docstring, an import, a `def`, a
  `class` or an assignment. And nothing reaches a global another way - there is no decorator, no
  dynamic lookup such as `globals()` or `eval`, no default argument that is not a constant, no dunder
  attribute such as `fn.__globals__` or `module.__dict__`, and no `getattr`-family call except seven
  declared ones, each reading a request payload or event object passed in as a parameter - so the
  runtime check below, which reads global loads from bytecode, sees every route. That last part fails
  closed (round 2, finding R2-F02): any other reflective call is a failure, not a pass.
- **Every global lookup, at runtime.** With the original module loaded beside the package, every name
  the bytecode of every function in `services/` loads as a global - 665 lookups across 96 functions and
  methods - resolves to the identical object the original held (302 imported names), to that name's
  moved definition (240), to its one new definition (24), or to an unshadowed builtin (99). The nine
  module-level constants equal the original's, with the same types. The same run compares the
  original's whole namespace with the new service module: every one of the 40 names the original defined
  is there and is its moved definition, the new module exposes nothing else, and the 221 imported names
  are listed as not re-exported.
- **Who uses the service.** A scan of every other file in the backend tracks every name bound to the
  service or to any package on its path (`app`, `app.modules`, `app.modules.work_orders`) - by
  `import`, `from ... import`, relative imports resolved against the file's own package, or
  `import_module` with a constant, at any scope - and follows each use to its full dotted path. It fails
  closed (round 2, finding R2-F03; round 3, R3-F01) on anything it cannot resolve to a literal name: the
  module or a package on its path used as a value, a dunder other than `__all__`, `__name__`, `__file__`
  or `__doc__` (so `service.__dict__[...]` fails), `getattr` with a computed name, a wildcard import, or
  the path in any other string. And it tracks dynamic importing by what it is rather than what it is
  called (round 4, R4-F01): every binding of `importlib`, `importlib.util`, `sys`, `builtins`,
  `pkgutil` and `runpy`, and of any importer function taken from them. An importer - `import_module`,
  `__import__`, `find_spec`, `resolve_name`, `run_module`, `sys.modules` and the like - passes only as a
  direct call with a constant module name (or `sys.modules` with a constant key); aliasing it, passing it
  on or calling it with a computed name fails, as do `eval`, `exec`, `compile`, `globals()` and any
  string that is a piece of the service's path (`"app.modules."`, `"work_orders.service"`). 37 names
  are taken; all are exported. Sixteen sites it cannot resolve are declared, each by file, function and
  source text with its reason - ten computed `import_module` calls loading test modules, authorization
  modules, the split's own submodules, or every module only to read its source text; two loads of fixed
  Alembic migration files; two `'__import__'` strings in lists of tokens tests assert are absent; and the
  surface test's two loops over the pinned names - and a declaration whose site has gone fails the scan
  too. The one limit, stated: a path assembled character by character, or from pieces none of which
  contains `app.modules` or `work_orders.service`, is not seen.
- **The candidate is the generator's output.** Regenerating the package from the base commit's
  `service.py` with the two scripts reproduces all eight files byte for byte, so the proofs about the
  scripts' output are proofs about the files under review.

Every check was then shown able to fail. Six deliberately broken versions (terms read in another order,
a rule skipped, a missing item dropped, a check removed from the copy, target reads reordered with the
same result, a wrong count reported) were each reported by the comparisons. Five rebinds in the live
modules (an imported name, a moved helper, an imported name in `common`, a module constant, a builtin
shadowed) were each reported by the runtime check. An import of the right name from the wrong module,
a planted decorator, a string-selected global reached through `__globals__` on an input no generator
produces, and a `getattr` on a function were each reported by the static one. And the importer scan
reported each of forty-nine planted forms of reaching the service - from a module-level
`import_module`, `service.__dict__["..."]`, relative imports and a route through the parent package to
an aliased `import_module` on a path assembled from pieces, `sys.modules` with a computed key, and
`exec` - and fails when a declared site disappears. And the export check fails on the round-1 `service.py`, and on a planted
import of a name the service never had.

### Verification

On the worktree stack (Compose project `pbl-crm-hiring-te6`), 23 September 2026. The host had about 1 GB
free, which roughly triples run times; the counts, not the times, are the evidence.

```text
Check                                       Baseline 1d7515f         Candidate
Full backend regression, run alone          2015 passed, 0 failed    2019 passed, 0 failed (the 2015 + 4 new)
  (after review round 1; the round-1 candidate had also passed 2015 of 2015, in a run spanning a laptop
   sleep, which can fail a test spuriously but cannot pass one)
Public names of service (new test file)     -                        4 passed
The ten Work Order test files               725                      725 passed after stage 1; 725 in the 2019
Part 3 rules / routes                       47 / 128                 47 / 128
Part 3 rules + routes + guard + harness     351                      351
Frontend typecheck / tests / build          -                        clean / 188 passed / built (frontend untouched)
E2E (run-e2e.ps1, with pwsh)                -                        17 passed, 9 skipped, 0 failed; cleanup succeeded
                                                                     (run on the round-1 candidate and again after its fixes)
check_tracked_secrets / validate_contract_fixtures / scripts unit tests / git diff --check    all clean
Frozen handoff contract                     70debad7...0cb0b86a      unchanged
Alembic head                                20260908_0039            unchanged; no migration
```

Baseline counts for the focused sets are collected counts; the baseline full run passed all 2015, so
each is also its pass count. The E2E ran after the backend container was recreated, so the server under
test loaded the split code, which was checked before the run.

The nine original tests (the pre-change versions of the four changed test files) were run against the
split and all failed: the five monkeypatch tests with `AttributeError`, because `service` no longer
holds those repository names, and the four inventory tests because the inventory came back empty -
`assert 0 >= 8`, an inventory-drift assertion naming the eight missing functions, and two `KeyError`s.
None of the changes was optional, and none could have hidden a skipped patch.

## Why this exists

Measured on 23 September 2026, and recorded in `docs/agent/DEFERRED_REQUIREMENTS.md`, "Code structure
in the Work Orders module":

```text
backend/app/modules/work_orders/service.py   3,529 lines, 84 top-level functions, 18 over 60 lines
  largest: copy_work_order_line_billing_terms 191, _normalize_billing_terms 152,
           create_work_order_contract_extension 133, create_work_order_from_commercial_offer 131
  five concerns in one file, by line range:
     1 -  520  the handoff and Work Order reads (Slices 5A, 6A, 6O)
   521 - 1331  amendments (6O.2)
  1332 - 1721  line operational detail (7C)
  1722 - 2634  billing terms (7D Parts 1 and 2)
  2635 - 3528  the contract period, extensions and copying terms (7D Part 3)
```

The module is otherwise in good order: `routes.py` (653 lines, nothing over 22) and `repository.py`
(1,646, one function over 60) are fine, the layout follows `CODING_STANDARDS.md`, the SQL is
PostgreSQL-only and statically guarded, and Part 3's `contract_period_rules.py` is the pattern worth
copying - pure logic, no database, no clock, exhaustively testable.

`commercial_offers/service.py` is 3,712 lines with the same shape. **Whatever convention this package
settles, record it so the Commercial Offer module can follow it later.** Do not change that module here.

## In scope

1. **Split `service.py` into a package by concern.** Suggested, not mandated:

```text
backend/app/modules/work_orders/
  service.py                    a thin module that re-exports the public names, so no caller changes
  services/__init__.py
  services/handoff.py           creating a Work Order from an accepted offer, and the reads
  services/amendments.py        Slice 6O.2
  services/line_detail.py       Slice 7C
  services/billing_terms.py     Slice 7D Parts 1 and 2
  services/contract_period.py   Slice 7D Part 3, including copying terms between lines
  services/common.py            only what genuinely spans concerns (see "The shared helpers" below)
```

2. **Break up the three longest functions**, without changing what they do:
   - `copy_work_order_line_billing_terms` (191) has a real sequence - verify targets, read the source,
     write each line under its savepoint - and splits along it.
   - `_normalize_billing_terms` (152) and `_period_missing_items` (112) are field-by-field chains. A
     table of field rules would shorten both and make Part 4's extra terms cheap to add. **If a table
     costs more clarity than it saves, say so and leave them long** - this package is allowed to
     conclude that.
3. **A context manager for the write preamble.** Fifteen functions open with the same lock, row read and
   version check, and close with the same commit/rollback. One helper, used by all of them.

## Explicitly out of scope

- **Any behaviour change.** No new validation, no changed message, no reordered check, no "while I am
  here" fix. If something looks wrong, record it; do not correct it in this package.
- Any change to API shapes, routes, permissions, events, database schema or migrations.
- `commercial_offers`, or any module other than `work_orders`.
- The frontend. `WorkOrderBillingTermsSection.tsx` (1,282 lines) and its neighbours wait for the
  frontend component-test capability - that ordering is recorded and is not reopened here.
- Moving test cases down from the route level (item 4 of the deferred entry). Separate, later, optional.
- `contract_period_rules.py`, `contract.py`, `schemas.py`, `repository.py`, `routes.py` - untouched
  except for imports that must follow the move.

## The shared helpers, which decide whether this is easy or a mess

Roughly a third of `service.py` is private helpers, and some are used by more than one concern -
`_clean_optional`, `_same_value`, `_record_billing_terms_event`, `_get_work_order_and_id`,
`_contract_period_row`, `_contract_bounds`, the line-lock helpers. Before moving anything, list every
`_`-prefixed function with the concerns that call it. Then:

- a helper used by exactly one concern moves with it;
- a helper used by several goes to `services/common.py`;
- **no module under `services/` may import another except `common`.** If two concerns need each other,
  that is the finding: say so in the handoff rather than inventing a cycle-breaking import.

## Method

Work concern by concern, not all at once. For each: move the functions unchanged, fix imports, run that
concern's tests, commit. A failure then points at one move rather than at 3,500 lines.

**Every moved function must be byte-identical apart from its imports.** Prove it mechanically rather
than by eye: before starting, write each top-level function's name and normalised body from `944af54`
to a file; after the split, do the same across the new modules; the two sets must match exactly, minus
the three functions item 2 deliberately rewrites and the fifteen touched by item 3. Put that comparison
in the review packet. A reviewer cannot read 3,500 moved lines; it can check a proof.

## Watch for

- **Seven files import this module**: `routes.py`, four test files, and the smoke-data harness's
  `builders.py` and `scenarios.py`. The thin `service.py` re-export is what keeps them working. Do not
  "tidy" their imports to the new paths in this package - that widens the diff for no gain.
- **A test introspects the module by name.** `backend/tests/test_slice_9b_pilot_hardening.py` asserts
  lock-before-read ordering for `("app.modules.work_orders.service", "create_work_order_from_commercial_offer", ...)`.
  It should survive a re-export, because `inspect` follows the function to wherever it is defined - but
  run that test early, not at the end.
- **Circular imports.** `service.py` imports from `contract.py`, `repository.py`, `schemas.py` and
  `contract_period_rules.py`, none of which import it back. Keep it that way.
- **The BOM.** Several files in this module start with a UTF-8 BOM. Preserve it when writing files, or
  the diff fills with noise.
- **`__all__` in the thin `service.py`** should list exactly the names other files import today - no
  more. A wildcard re-export would hide a name that quietly stopped existing.

## Acceptance

```text
[x] Every check below passes, with the SAME counts as on 944af54 - a changed count means behaviour moved
[x] Full backend regression, run alone                     2015 passed, 0 failed
    (as built: 2019 - the same 2015, all passing, plus 4 new tests pinning the module's public names)
[x] Part 3 rules / routes                                  47 / 128
[x] 7C, 7D Parts 1 and 2, route guard, harness             351 passed together
    (as built: 351 is Part 3 rules + routes + guard + harness; see "As built", item 6)
[x] Frontend typecheck / tests / build                     clean, 188 tests (the frontend is untouched)
[x] E2E                                                    17 passed, 9 skipped, 0 failed
[x] scripts/check_tracked_secrets.py, validate_contract_fixtures.py, git diff --check   clean
[x] Frozen handoff contract file                           hash unchanged
[x] The equivalence proof above, in the review packet
[x] No migration, no schema change, no route or permission change in the diff
[x] docs: this file updated to as-built; CODING_STANDARDS.md gains the convention chosen, so
    commercial_offers can follow it; DEFERRED_REQUIREMENTS.md items 1-3 struck through
[ ] Independent review ACCEPTED - not reached: four rounds, every finding corrected; the owner chose
    to commit without a fifth (23 September 2026)
```

Ticked by the implementer on 23 September 2026 from the evidence in "As built"; acceptance itself is
the independent reviewer's to record.

A screen check is **not** required: nothing a user can see changes. If the owner wants one anyway, the
Work Order page exercises every concern in one place.

## Estimated shape

About 3,500 lines moved, roughly 400 rewritten, no new behaviour. The expensive part is verification,
not editing: the regression takes about 23 minutes per run and should be run at least twice - once on
the finished split, once after any review correction.
