# CS-11 - Splitting the Commercial Offers service

## Status

**BUILT 8-9 October 2026; ACCEPTED BY THE OWNER on 9 October 2026, as it stands, after eleven review rounds, each with
corrections** (three within the owner's cap, the fourth to eleventh on the owner's authorisation; see "Independent
review" below - every finding was about the evidence scripts or these records; none about the split itself). The owner
accepted it without a twelfth round, so round 11's corrections were not re-reviewed. Merging waits for `Required
validation` on the exact head of the pull request. TB-1 corrective package CS-11, closing
finding TB1-601 (`docs/agent/tb-1/TB_1_CORRECTIVE_SLICE_REGISTER.md`, CS-11; `TB_1_FINDINGS_REGISTER.md`, TB1-601).
Row 9 of the register's correction sequence: due before the next package that changes the file - CS-05a, stale-form
protection for offers, comes next. Branch `refactor/cs-11-commercial-offers-split`, built on `main` at `5e19123`;
**CS-04 merged on 8 October at 23:53 (`b4dd8fe`), `main` was merged in, and the split was regenerated from `main`'s
`service.py` and every proof and test repeated on that base**; `main` was merged in again at `a4f8df2` (PR #110, a
documentation change), at `d33a9ae` (PR #107, TB1-102 part b, which changes no Commercial Offer file) and at `fb381c6`
(PRs #111 and #113, tests and Hiring code only). **The figures in this record describe the current candidate, the split
of `main`'s `service.py` (3,760 lines, unchanged from `b4dd8fe` to `fb381c6`)**; those of the first split, of `5e19123` (3,729 lines), which
review rounds 1 to 3 read, are kept only in "History" below.

**No behaviour change, at all**: no route, request, response, permission, event, schema or migration changed, and no
function's text. The TB-1 records under `docs/agent/tb-1/` are pinned and are not edited; TB1-601 is closed by this
record and `docs/continuity/NEXT_STEPS.md`.

```text
Baseline              5e19123 (origin/main, PR #102 merged); then main merged in at b4dd8fe (CS-04, PR #106),
                      a4f8df2 (PR #110), d33a9ae (PR #107) and fb381c6 (PRs #111, #113) - fb381c6 is the base
                      the current candidate is compared with
Branch                refactor/cs-11-commercial-offers-split
Migration             none (main's head is 20260908_0050, TB1-102 part b's)
Frozen contract hash  70debad7...0cb0b86a at 5e19123, 0f16ff22...2cd39080 after CS-04 amended it; this package does
                      not touch the file - its hash on the merged branch is main's
Method                TE-6's (TE_6_WORK_ORDERS_SERVICE_SPLIT.md), its scripts adapted in cs-11-proof-scripts/
Review                bounded packet, the independent reviewer, three-round cap; rounds 4 to 11 on the owner's authorisation
```

## The layout

```text
backend/app/modules/commercial_offers/
  service.py                       154  re-exports, by name, all 54 public names the original defined; __all__ = them
  services/__init__.py               1
  services/common.py               322  the 8 exceptions; the helpers two or more concerns call, among them reading
                                        an offer, the offer lock for content changes, and the T&C readiness view
  services/offers.py               442  the offer record: create, list, update (Slices 4A, 4C)
  services/related_offers.py       224  Supplementary Offers and Change Quotations (6O.1)
  services/pricing_evidence.py     237  pricing evidence and the basis rate (4D)
  services/lines.py                294  offer lines (4E)
  services/tc_clauses.py           287  T&C clauses: list, attach, attach recommended, remove (6F, 6G)
  services/submission_readiness.py 521  the submission readiness checklist (6H)
  services/submission_evidence.py  138  submission evidence (6I)
  services/credit_reviews.py       136  the manual credit/exposure readiness review (6I.2)
  services/mark_submitted.py       174  marking an offer submitted (6J)
  services/revisions.py            307  revisions and resubmission (6K)
  services/customer_responses.py   234  customer responses (6L, 6M.1)
  services/lifecycle_guidance.py   255  what the offer's lifecycle allows next (6M)
  services/quote_documents.py      631  quotation documents (9E)
```

Thirteen concern modules, one per route group, as TB1-601 counted them; each is one section of
`docs/agent/contracts/commercial-offer-contract.md`. No module under `services/` imports another except `common`, and
nothing needed an exception to that. Each module keeps the original's order of definitions, except that `common` lists
its eight exceptions first (three were declared halfway down the original). The total grew from 3,760 lines to 4,357:
each module carries its own imports and docstring. The split makes the code easier to navigate, not shorter.

What `common` holds, and why each is there - every one is called by two or more concerns:

| In common | Called by |
| --- | --- |
| The 8 exceptions | `routes.py` maps them to HTTP statuses in one place (TE-6's rule: the error vocabulary stays together) |
| `get_commercial_offer` | 7 concerns read the offer they act on |
| `_lock_offer_for_content_change` | submission evidence, credit reviews, pricing evidence, lines, T&C clauses |
| `_clean_optional`, `_normalize_code`, `_normalize_lower`, `_event_dict` | nearly every concern |
| `_validate_offer_value`, `_validate_dates` | offers, related offers |
| `_validate_currency` | offers, related offers, pricing evidence, lines, customer responses |
| `_validate_required_text` | related offers, pricing evidence, lines |
| `_ensure_account_traceability_for_lifecycle_action` and its status set | offers, customer responses |
| `_revision_evidence_context` | revisions, customer responses |
| The T&C readiness view - `get_commercial_offer_tc_clause_readiness`, `normalize_tc_recommendation_basis`, `_tc_readiness_status_text` and their two constants | T&C clauses (attach recommended) and the submission readiness checklist |

The T&C readiness view backs a route of its own, and would sit with the T&C clauses but for the submission readiness
checklist, which reads it too; with the rule that a concern imports only `common`, it can only be in `common`, as TE-6's
contract bounds were.

## Reproducible, because CS-04 changes the same file

CS-04 part 1 (PR #106, built the same night) changes two functions of `service.py` - customer responses and the
lifecycle guidance - and its imports. A hand-merge into the split would be a second, unproved edit of moved code. So the
split is made by a script, `cs-11-proof-scripts/split.py`, from whatever `service.py` it is given:

- every top-level definition is copied verbatim, with the comment block directly above it and a comment block directly
  below it that ends at a blank line (one such note follows the submission readiness constant);
- each module's imports are the original's import block filtered to the names that module's code uses, in the
  original's order and paragraphs, with the original's comments (the two 9E notes on reading Account identity and
  storing documents travel with the imports they explain);
- where each name goes is a table, `PLACEMENT`; the script refuses, writing nothing, when the file it is given has a
  top-level name the table does not place, a comment it cannot attach to one definition, a statement other than an
  import or a definition, an assignment that binds two names in one statement (review round 4, CS11-R4-002: it would
  be written twice), a definition that binds any module name besides its own with `:=`, or an annotation with no value
  (review round 5, CS11-R5-001: the extra name would be neither placed nor re-exported), a nested `global` of any name,
  the function's own included (review round 6, CS11-R6-001: from its new module it would rebind the concern module's
  name, not the one the service's callers read), a definition that runs code at import other than a declared call -
  a value, default or base that is not a literal or a name, a class body other than `pass` (review round 7,
  CS11-R7-001: moved, it would run in its concern module's turn, not the original's order) - or a concern that would
  need another concern's code; and a class created through anything but the built-in `ValueError` or `LookupError`
  (not rebound in the input) or a class the input defines, or with a keyword such as `metaclass=` (review round 8,
  CS11-R8-002: creating a class runs its base's `__init_subclass__` and its metaclass, in the class's turn); and
  (review round 9) a set element or dictionary key that is not plainly a literal, or a `**` in a dictionary (CS11-R9-004:
  hashing runs `__hash__` and `__eq__`), a wildcard import (CS11-R9-003: its names cannot be placed), a relative import
  (moved into `services/`, it would name another module), and a name both imported and defined (CS11-R9-002: a class
  "based on" the defined class could be built on the import). It does not judge what the modules the service imports
  do at import: `import_order.py` does, and is one of the checks every regenerated candidate is put through. Since
  round 10 (CS11-R10-001) it also refuses a name bound by more than one import - Python keeps the last, and a check
  reading another would judge the wrong object. The rules for what may run at import live once, in
  `import_time_rules.py`, which `split.py`, `proof.py` and `import_order.py` all use (round 10, CS11-R10-002: three
  copies had drifted). Since round 11 (CS11-R11-001) the checks that a name is what it seems - not both imported and
  defined, not bound twice by imports or by definitions, `ValueError` and `LookupError` not rebound, a same-file
  base defined further up - are one list, `binding_problems`, used by all three; `split.py` refuses a class based on
  a same-file class the input defines only further down.

Run on CS-04's `service.py` (`593da89`), the script carried its changes into `customer_responses.py` and
`lifecycle_guidance.py` and passed every static proof below. CS-04 merged at 23:53 on 8 October (`b4dd8fe`, with two
later review rounds' changes); `main` was merged into this branch, the script re-run on `main`'s `service.py`, and every
proof and the test run repeated on the new base ("Verification", "After CS-04 merged").

## What proves nothing moved

Each script is kept, with its output, in `cs-11-proof-scripts/`; its README says what each is adapted from. TE-6's
review rounds shaped them: identical text is not enough (a moved function reads its globals from its new module), and a
check must fail on what it cannot resolve rather than pass it.

- **Text** (`proof.py`). Each of the original's 97 top-level definitions - 81 functions, 8 exception classes and 8
  constants, one of them an annotated assignment - exists exactly once under `services/` and is byte-identical to the
  original. There are no declared exceptions: nothing is rewritten. Every comment attached to a definition is attached
  to it in its new home, and every other top-level comment line of the original survives, except the three lines of the
  9E section banner, which `quote_documents`' docstring replaces. No module imports a name it does not use, or uses one
  it neither defines nor imports. Since review round 5 (CS11-R5-001), in the original, every new module and
  `service.py`, each top-level statement binds only its own one name - not two, not one more by `:=`, not none (an
  annotation with no value) - and no name is bound by two statements, so the comparison by name cannot miss a name
  bound in passing or a statement written twice. Since round 6 (CS11-R6-001), none holds a nested `global` either,
  whatever the name: a moved function declaring even its own name `global` would rebind its concern module's name,
  not the one the service re-exported. Since round 7 (CS11-R7-001), what each definition evaluates at import - an
  assignment's value, a function's defaults, a class's bases - is a literal or a name, every class body `pass`, and
  every module with a definition imports `annotations` from `__future__`, so no annotation runs: the one call, `ZoneInfo("Asia/Kolkata")`
  for `INDIA_DISPLAY_TIME_ZONE`, is declared (the zone is cached by its key, the same object whichever module asks
  first). Since round 8 (CS11-R8-002), every class is created through the built-in `ValueError` or `LookupError` -
  neither rebound in any of the modules - or a class the original defines, with no keyword such as `metaclass=`, so
  creating it runs no hook. Since round 9 (CS11-R9-002 to -004), every set element and dictionary key built at import
  is a plain literal or a name bound to one where it is defined - here, the four status and address-type codes, each
  a string in a contract module - no dictionary unpacks, no import is a wildcard or relative, and no name is both
  imported and defined. Since round 10 (CS11-R10-001), no name is bound by two imports, and a name is followed to its
  last binding, as Python leaves it. Since round 11 (CS11-R11-001), no class is based on a same-file class defined
  only further down. So the new modules' load order cannot change what their definitions do at import.
- **Every import binding** (`proof.py`). Each of the 471 names the new modules import is imported from the same module,
  under the same name and alias, as the original imported it, or is a name the original defined, imported from `common`
  under its own name. Two names the original imported are imported by no new module, because the original never read
  them: `get_account` (from `accounts.service`) and `COMMERCIAL_OFFER_ALLOWED_QUOTE_DOCUMENT_STATUSES`. Each is declared,
  and the proof checks that the original reads neither. Nothing else runs at import; there is no decorator, dynamic
  lookup, dunder read or non-constant default, and the three `getattr` calls are declared, each on a parameter holding a
  request model or an event.
- **Every global lookup, at runtime** (`bindings.py`, in the backend container). With the original loaded from its text
  beside the package, every name the bytecode of every function in `services/` loads as a global - 687 lookups across 81
  functions - resolves to the identical object the original held (351 imported names), to that name's moved definition
  (215), or to an unshadowed builtin (121). The eight constants equal the original's, with the same types. The service
  module holds every one of the 54 names the original defined, each its moved definition, and nothing else. Six
  deliberate rebinds in the live modules - an imported name, a moved helper, an imported name in `common`, two
  constants and a builtin shadowed - are each reported.
- **Who uses the service** (`importers.py --repo`, host). Every other Python file in the backend is scanned for every
  way it could reach `app.modules.commercial_offers.service` - by import, relative import, a package on its path,
  `import_module`, `sys.modules`, a patch-target string or a parametrised tuple - failing closed on anything it cannot
  resolve to a literal name. The same file under another `sys.path` root is followed the same way (review round 2,
  CS11-R2-001): `backend.app.modules.commercial_offers.service`, `modules.commercial_offers.service` and
  `commercial_offers.service`, and the packages on the way to each. A string naming the service's file or its
  package's directory by path fails, and a loader that takes a location (`spec_from_file_location`, `SourceFileLoader`,
  `run_path` and the like) passes only when every argument is a constant string. 43 names are taken, all exported.
  Twenty sites it cannot resolve are declared by file, function and source text, each with its reason (TE-6 declared
  the same kinds; each was read again), and each with its **whole flow** (round 2, CS11-R2-002): every function of its
  file that reaches the declared function, transitively, and every module-level value they read, by the SHA-256 of its
  source text - and, since round 3 (CS11-R3-001), the whole source of the declared function and of every caller,
  decorators included, by the same hash. The scan recomputes each flow on every run and fails on a new caller, a
  changed caller, a changed constant, a reference at module level or in a class, or a reference from another file that
  names the declared one - by name, under an alias, or as a string (round 3, CS11-R3-002) - so a module loaded at a
  declared site, `_production_modules()`'s for one, cannot reach a new or changed use unseen. The review packet carries
  every declared flow whole. The limit, stated: a reference to a flow function built at run time from pieces, in a
  file that does not name the declared file, is not seen statically; the runtime trap below covers what the tests run.
  **The rest of the repository** (review round 1, finding CS11-R1-001): every other file of the proposed tree - `git
  ls-files --cached --others --exclude-standard`, as the secret scan enumerates it - is checked too. The 10 Python files
  outside `backend/` that are not evidence (`scripts/`, `scripts/tests/`, `tools/review/`) get the same fail-closed scan
  and take nothing. Every other text file, the backend's included (1,622 on the current candidate: shell and
  PowerShell scripts, workflows, compose and configuration files, TypeScript, CSV, JSON), fails the scan if it names the
  service's path or a piece of it, unless it is Markdown, which imports nothing (29 documents name it; they are
  listed). Class bodies are scopes of their own (review round 4, CS11-R4-001): a method is scanned with the names the
  class inherited, not the class's own; a class-body read of a name the class rebinds, and the service bound as a class
  attribute, fail closed; and a comprehension's loop name no longer hides an outer binding. Before round 5 (a
  self-audit, not a finding): a name declared `global` or `nonlocal` no longer hides the outer binding when the function
  assigns it, and the service bound to such a name from inside a function fails closed; and a declared flow counts a
  test that reaches it through a pytest fixture - named only as a parameter - or by name in a string. Three directories of
  evidence - TB-1's pinned records, and TE-6's and this package's proof scripts - are scanned the same way but reported
  rather than failed, because nothing imports or runs them: they are records of checks run by hand against the tree of
  their time. What each would take is listed. Two of TB-1's pinned evidence scripts, `P6_currency_probe.py` and its
  round-1 rerun, call `_validate_currency` through the service; re-run on this tree they would need the same change as
  the currency test, and this package may not edit them. 38 binary files are skipped.
  `importer_mutants.py` plants 55 ways of reaching the service inside `backend/` (TE-6's 49; from round 4 a method
  reading a name a class attribute shadows, a class-body read before the rebinding, the service as a class attribute,
  and a comprehension's loop name; before round 5 a `global` name read and then rebound, and the service bound to a
  global from inside a function) and 17 outside it - a script, Python at
  the repository root with `backend/` on its path, a tool importing a computed name, a shell command, a CI workflow, a
  compose file, a TypeScript string, a piece of the path in PowerShell, a backend configuration file, five other
  spellings of the module path, and three loads by location - and the scan reports every one; two controls, a Markdown
  mention and an evidence script, are listed and do not fail. It also changes a declared flow seven ways - a new
  caller of `_production_modules()` reading a removed name with a default, the existing caller changed to do the same
  with its call graph and constants untouched, another file importing that helper, importing it under an alias, or
  fetching it by name, a constant the flow reads, and a test reaching the helper through a fixture - and the scan
  reports each, while the unchanged file passes. The
  counts in this paragraph are those of `outputs/after-cs04/importers_out.txt` and `importer_mutants_out.txt`, on the
  current candidate; `importer_mutants_before_r4_fix.txt` shows the scan round 4 read missing the three class forms.
- **What actually runs reads nothing the split removed** (`missing_name_trap.py`, backend container). A static scan
  argues about code; this watches it run. For one run of the touched test files and of every file holding a declared
  site, the service module was given a module-level `__getattr__`, which Python calls only for a name the module does
  not hold: it recorded each such lookup - an attribute read, `getattr`, `hasattr`, `from ... import` - and raised
  `AttributeError` as the lookup would have anyway, so no test behaved differently. On the current candidate, with
  CS-04's test file too, all 714 tests passed (686 on the split of `5e19123`). The trap saw
  20 lookups of four names - `__path__` (the import machinery, on every `from ... import`), `__test__`,
  `_pytestfixturefunction` and `__bases__` (pytest, collecting a test module that binds the service) - none of them a
  name the original module held, so none a name the split removed. A planted test that reads a removed name with a
  default, through a module loaded by a computed name, passes as a test, and the trap reports the read.

  The trap also showed that `_production_modules()` in `test_business_authority_store_wiring.py`, declared as loading
  every production module, loads four: `pkgutil.walk_packages` does not descend into `app/modules`, which has no
  `__init__.py`. Its declaration says so. That test's guard - no production module imports a synthetic provider -
  therefore checked four modules, not the application; a gap in that test, older than this package and outside it,
  recorded here and in `NEXT_STEPS.md` for its owner. Since fixed: PR #111 (NS-PR-01, merged 9 October as `dfabff1`)
  imports every file under `app/`. Merged into this branch at `fb381c6`, it changed that declared site; the scan's
  declaration was rewritten for the new helper - which now loads the service and `services/`, while its one caller
  still reads only each module's file, name and source - and its flow re-fingerprinted.
- **The moved patches reach what the old ones reached** (`patch_reach.py`). Patching a name on the one-file service
  replaced it for every function in the file; patching it on one concern module replaces it only there. For each of the
  three 9E tests, the service functions it calls while its patch is in force are read from the test's own text; every
  original function they can reach that looks the patched name up is now in `quote_documents.py`, the module the test
  patches. (The one other function that looks `list_commercial_offer_tc_clauses_for_offer` up, the T&C list in
  `tc_clauses.py`, is off that test's path.) Since the pre-round-5 self-audit it also reads the replacement each patch
  installs and the teardown of each fixture the test takes (after its `yield`; here none calls the service), and every
  other call made while the patch is in force through the application or its tooling - an imported name, or a name
  bound to one (`client = TestClient(app)`, `real = module.function`, a helper's parameter passed one) - must go to
  modules whose static import closure holds neither the service nor any services module; a receiver it cannot name
  fails. Every such call here goes to the database session, settings, document storage or the repository.
  `patch_reach_mutants.py` plants eight routes it must report - a `builders` call, the module's `TestClient`, a local
  alias inside the replacement, a handle passed to a helper, a fixture teardown call, a fixture from outside the file,
  an unnamed receiver and an undeclared service call - and the unchanged file must pass: 8 of 8, and it does.
- **The candidate is the generator's output.** Regenerating from `main`'s `service.py` into a fresh directory gives
  all sixteen files byte for byte.
- **The proofs can fail.** `proof_mutants.py` plants thirty-three changes - a changed character, a same-named import
  from another module, a decorator, a `__globals__` read, a `getattr` on a function, a concern importing another, a
  definition in two modules, a definition dropped, an attached comment dropped, an unused import, a statement run at
  import, a public name dropped, a default read from a global, and, since rounds 5 to 11, twenty that keep the moved
  text byte-identical (made to the original and its moved copy alike, or a moved statement written twice): a second
  name bound by `:=`, a nested `global` of a new name, a public function declaring its own name `global` (round 6), an
  annotation with no value, a chained assignment, two constants in different concerns calling the same function at
  import, an exception class whose body runs code, no `from __future__ import annotations` (round 7), an exception
  class created through an imported Pydantic model, one given a metaclass, `LookupError` rebound by an import (round
  8), a wildcard import, a relative import, an earlier class based on a later class's name that an import also binds,
  a set holding an imported class, a dictionary unpacking a mapping (round 9), an import binding one name twice with
  both bindings literals, and with the last not a literal (round 10), an exception class based on one defined only
  further down (round 11), and a statement duplicated in its new module - and `proof.py` reports every one. Earlier
  versions report 15 (before round 5), 20, 21, 24, 27, 30 and 32 (before rounds 6 to 11), each missing the cases added
  since (`outputs/after-cs04/proof_mutants_against_946b925.txt`, `-51a052d.txt`, `-fa4f824.txt`, `-56b5be4.txt`,
  `-c50df2e.txt`, `-2034726.txt`, `-b84d422.txt`).
- **The generator refuses what it cannot place** (`split_mutants.py`, rounds 4 to 11). Twenty-three changes to the
  original - a chained assignment of two names placed together, a placed assignment also binding a new name by `:=`, a
  placed function declaring a new module name `global`, a placed public function declaring its own name `global` and
  rebinding it (round 6), a placed name annotated with no value, a function `PLACEMENT` does not place, a statement
  among the imports, a concern reaching another concern's helper, a comment between two definitions attached to
  neither, (round 7) two placed constants in different concerns calling the same function at import, an exception
  class whose body runs code, an input without `from __future__ import annotations`, (round 8) an exception class
  created through an imported Pydantic model, one given a metaclass, an input that rebinds `LookupError`, (round 9) a
  wildcard import, a relative import, an earlier class based on a later class's name that an import also binds, a set
  holding an imported class, a dictionary unpacking a mapping, (round 10) an import binding one name twice with both
  bindings literals, and with the last not a literal, and (round 11) an exception class based on one the input defines
  only further down - and `split.py` refuses each, writing nothing, while the unchanged original splits. Each case is
  load-bearing for its own refusal (round 5, CS11-R5-002): run against a copy of `split.py` with only that refusal
  switched off, no other check refuses it - except two that two rules refuse by design (a name bound twice whose last
  binding is not a literal: the duplicate binding and the hashing rule; an earlier class based on a later class's name
  that an import binds: the collision and the base defined later), each accepted only with both switched off.
  Twenty-one are then accepted (the chained assignment written twice, the stray comment and the wildcard import
  dropped, the `__future__` import written into fifteen files whose input lacked it), and two stop on a Python error
  before writing anything. Against earlier versions of `split.py`: before round 4, 5 of 23 are refused; before rounds 5
  to 11, 6, 9, 10, 12, 15, 20 and 22 - each missing the cases added since (`split_mutants_against_3ee3abc.txt`,
  `-946b925.txt`, `-51a052d.txt`, `-fa4f824.txt`, `-56b5be4.txt`, `-c50df2e.txt`, `-2034726.txt`, `-b84d422.txt`).
- **The load order** (`import_order.py`, round 7, in the backend container). Importing the whole application
  (`app.main`) loads 152 `app` modules with the original service and 167 with the split - the same 152 and the fifteen of
  `services/`. Two load at another point in the order: `app.shared`, a namespace package with no file,
  and `app.shared.currency`, each eleven places earlier. `currency.py` imports nothing and defines three constants -
  one a message joined from its own codes, declared - and one function: nothing it does at import can depend on, or
  change, when it runs. Every other module loads in the same order as before. `split.py` cannot see what an imported
  module does at import, so this check is part of every regeneration, not only of this one. Since round 10
  (CS11-R10-002) a moved module is judged by the same rules as the split's own definitions
  (`import_time_rules.module_import_problems`), since round 11 with the same binding checks too (CS11-R11-001).
  `import_order_mutants.py` plants fifteen forms in copies of `currency.py` - a set holding an imported class, `**`,
  a class built on an imported model, a metaclass, a class body running code, annotations without the `__future__`
  import, a decorator, an undeclared call, the declared message changed, a name bound by two imports, a statement,
  and (round 11) an earlier class based on a name an import binds and a later class defines, `LookupError` rebound
  before a class is based on it, a same-file class name rebound before a class is based on it, and a class based on
  a same-file class defined only further down - and the rules report 15 of 15, the unchanged module inert; the
  versions before rounds 10 and 11, each with its own rules, report 4 and 11 of 15.

### What it narrows

As TE-6 settled (the owner's decision of 23 September 2026; `CODING_STANDARDS.md`, "When a service outgrows one file"),
`service.py` re-exports the 54 names the original **defined** and not the 226 it only imported. Having no `__all__`, the
original exposed 280 public names - its 54, and every repository function, schema, contract constant and type it
imported - and `from ... import *` handed all 280 out; it now hands out 54.

What the scan found taken through the service that the split no longer keeps there: two of the 226 imported names, the
repository functions the 9E tests patched and read (`insert_commercial_offer_quote_document`,
`list_commercial_offer_tc_clauses_for_offer`), and two private helpers the original defined (`_normalize_create_payload`,
`_validate_currency`), never part of its public surface. All four were taken by tests, which now follow the code
(below). Nothing else that runs against the current tree - the application, its tooling, its tests, `scripts/`,
`tools/`, CI, Compose or the frontend - takes any of them. Of the evidence, the two pinned TB-1 scripts named above take
`_validate_currency`; other evidence scripts that touch the service do so in ways the scan reports but cannot resolve to
a name (dynamic imports, module paths in strings), and each is listed with its count in `outputs/importers_out.txt`.

Importing the service also no longer imports `app.modules.accounts.service`, because its only import from there was the
unused `get_account`. Compared in the container: the application modules a fresh `import
app.modules.commercial_offers.service` loads are the same before and after, plus the fourteen new modules, minus
`accounts.service`, which has no side effects at import (it defines functions and compiles five patterns), and which the
running application loads anyway through the Accounts routes.

## Tests that followed the code

TB1-601 named three monkeypatches and one introspecting scan. The importer scan found two more tests reaching names
the service no longer holds. All five are pointed at the concern module now holding the code, as
`CODING_STANDARDS.md` requires; no assertion changed.

| Test | Was | Now |
| --- | --- | --- |
| `test_slice_9e_quotation_generation.py`, the two failed-generation tests | patched `insert_commercial_offer_quote_document` on `service` | on `services.quote_documents` |
| the same file, `test_approval_cannot_validate_a_combination_of_offer_data_that_never_existed` | read and patched `list_commercial_offer_tc_clauses_for_offer` on `service` | on `services.quote_documents` |
| `test_slice_9b_pilot_hardening.py`, `_status_writing_function_sources` (used by three tests) | walked `vars(service)` for functions defined in `service` itself | walks every module of `services/`, as TE-6 did for the amendment scan, and refuses a name found in two modules |
| the same file, `test_offer_creation_locks_the_opportunity_before_reading_its_status` (not named by TB1-601) | read the source of `service._normalize_create_payload` | of `services.offers._normalize_create_payload` |
| `test_operating_currency.py`, `test_each_module_refuses_with_its_own_error_and_the_one_message` (not named by TB1-601) | called `service._validate_currency` | `services.common._validate_currency`, as it already called the Work Orders one on `work_orders.services.amendments` |

`backend/tests/test_cs11_commercial_offers_service_surface.py` (new, six tests) pins the 54 names, requires `__all__` to
be exactly them, and requires each to be the very object the one concern module defining it holds.

Each change was shown necessary and load-bearing (outputs in `cs-11-proof-scripts/outputs/`):

- On the base, the three 9E tests with their patches removed (`probe_9e.py`) fail: the two failed-generation tests with
  "DID NOT RAISE", the approval test because the interleaved write never fires (`[] == ['fired']`). On the split, the
  retargeted tests with their patches removed fail the same three ways.
- Run unchanged against the split, all eight changed tests fail: the three 9E tests with `AttributeError`, because the
  service no longer holds the repository names and `monkeypatch.setattr` refuses a name a module lacks (so they could
  not have passed while proving nothing); the three 9B status-writing tests because the old scan finds nothing
  (`assert {}`, the set check naming all three writers as no longer found, `0 == 3`); and the two private-helper tests
  with `AttributeError`.
- A status writer planted for one run in a new module under `services/` is found by the retargeted 9B scan: the set
  test, the lock-order test and the count test each fail, naming it. The file was then removed.

## Verification

The current candidate: the split of `main`'s `service.py`, after CS-04 merged.

CS-04 part 1 merged as `b4dd8fe` at 23:53 on 8 October. Its changes to `service.py` are in
`create_commercial_offer_customer_response` and `get_commercial_offer_lifecycle_guidance`, with three new imports.
`main` was merged into the branch; Git's conflict in `service.py` was resolved by running `split.py` on `main`'s
`service.py` (SHA-256 `5a5a53d4...`), not by hand, and the one in `NEXT_STEPS.md` by keeping both entries. Only
`services/customer_responses.py` and `services/lifecycle_guidance.py` differ from the split of `5e19123`. Every check
was then repeated on the new base, the baseline first; outputs in `cs-11-proof-scripts/outputs/after-cs04/`. `main` was
merged in again at `a4f8df2` (PR #110, 52 lines of `DEFERRED_REQUIREMENTS.md`, nothing else): the host-side checks
gave identical output on it, and the runtime rows, run on `e2d7e55`, cover code that did not change. The round-4
corrections, the self-audit before round 5 and the round-5 corrections changed only the evidence scripts and these
records; their outputs are regenerated in the same folder. `main` was merged in a third time at `d33a9ae` (PR #107,
TB1-102 part b: request keys for equipment models, kit and resource requirements, migration `20260908_0050`; no
Commercial Offer file, and `service.py` still `5a5a53d4...`), Git's conflict in `NEXT_STEPS.md` resolved by keeping both
entries. On the merged tree `proof.py`, `patch_reach.py` and `importer_mutants.py` gave identical output, `split.py`
regenerated all sixteen files byte for byte, and the repository scan passed, its only change one more text file
searched. The runtime rows were not repeated for it: PR #107 changed none of their test files and no Commercial Offer
code, and CI runs the whole backend regression on the merged head. `main` was merged in a fourth time at `fb381c6`
(PR #111, NS-PR-01's guard, and PR #113, the Hiring tests' business day: test files and Hiring code, no Commercial Offer
file; `service.py` still `5a5a53d4...`), without a conflict. PR #111 rewrote `_production_modules()`, a site the caller
scan declares, so the scan failed on it until its declaration and flow were rewritten (above); then it passed.
`importer_mutants.py`, `proof.py` and `patch_reach.py` gave identical output, `split.py` regenerated all sixteen files,
and `import_order.py`, re-run in the backend container, gave the same order as before. The runtime rows were not
repeated: PR #111 changed one file of their run, `test_business_authority_store_wiring.py` (the helper above), and no
Commercial Offer code; CI runs the whole backend regression on the exact head.

```text
Check                                              Main b4dd8fe                Merged candidate
Touched files + CS-04's test file + the five       708 passed, 1 skipped       714 passed, 1 skipped: the same
  other declared-site files, run alone             (one test crossed midnight  708 ids and the 6 surface tests
                                                   in India and failed; alone
                                                   after midnight it passed)
proof.py / proof_mutants.py                        -                           PASS (97 of 97 byte-identical) / 32 of 32
                                                                               (15-32 before rounds 5-11)
bindings.py --self-test                            -                           PASS, 687 lookups / 6 of 6
importers.py --repo / importer_mutants.py          -                           PASS, 43 names, 20 declared sites and their
                                                                               flows / 55, 17 and 7 of 7; controls pass
split_mutants.py (rounds 4 to 11)                  -                           23 of 23 refused, nothing written; with
                                                                               only its own refusal(s) off, none
                                                                               refused by another check (5 to 22 of
                                                                               23 before rounds 4 to 11)
import_order.py (round 7, backend container)       152 app modules              167: the same 152 in the same order
                                                                               but app.shared and app.shared.currency,
                                                                               11 places earlier, both inert, + the 15
                                                                               of services/; import_order_mutants.py:
                                                                               15 of 15 (4 and 11 before rounds 10, 11)
patch_reach.py / patch_reach_mutants.py            -                           PASS; every other call under the patches
                                                                               cannot reach the service / 8 of 8; the
                                                                               control passes
split.py regenerated from main's service.py        -                           16 of 16 files byte-identical
The 3 9E tests without their patches               3 failed                    3 failed
The 8 changed tests, unchanged, against the split  -                           8 failed, each as expected
9B scan with a planted writer                      -                           3 failed, naming it
missing_name_trap.py over the whole run above      -                           no removed name looked up (20 lookups of
                                                                               __path__ and pytest probes, as before)
Modules loaded by importing the service            40                          54: the same, + services/ and its 14
                                                                               modules, - app.modules.accounts.service
Frozen handoff contract                            0f16ff22...2cd39080         the same; not touched
docs/agent/tb-1/, alembic/, frontend/, e2e/        -                           no difference from main
```

### History: the split of `5e19123`, which review rounds 1 to 3 read

On the worktree's own Compose stack (project `pbl-crm-hiring-cs11`, no published ports, `PASSWORD_HASH_ITERATIONS=10000`
as CI sets it), 8 October 2026. Other lanes shared the machine, so by the owner's rule for the night the full backend
regression and Playwright were not run locally: CI runs both on the pull request.

```text
Check                                              Base 5e19123                Candidate
The fifteen touched test files, run alone          566 passed, 0 failed        572 passed, 0 failed: the same 566 test
                                                                               ids, and the 6 new surface tests
  (the Commercial Offer suite - the offers API, related offers, currency, 9B and 9E files - the smoke-data harness,
   which calls the service, Work Orders, amendments, reports, interactions, display names, and the four guard files
   that read app modules or routes: authorization route guard, business-authority boundary and wiring,
   PostgreSQL dialect)
proof.py / proof_mutants.py                        -                           PASS / 13 of 13 reported
bindings.py --self-test (backend container)        -                           PASS, 681 lookups / 6 of 6 reported
importers.py --repo / importer_mutants.py          -                           PASS, 43 names, 20 declared sites and their
                                                                               flows, the rest of the repository / 49 of
                                                                               49, 17 of 17, 6 of 6 flow changes; controls
                                                                               pass
missing_name_trap.py over the touched and          -                           686 passed; no removed name looked up; a
  declared-site test files                                                     planted read with a default reported
patch_reach.py                                     -                           PASS
split.py regenerated from the base                 -                           16 of 16 files byte-identical
split.py + proof.py on CS-04's service.py          -                           PASS (dry run, 593da89)
The 3 9E tests without their patches               3 failed                    3 failed
The 8 changed tests, unchanged, against the split  -                           8 failed, each as expected
9B scan with a planted writer                      -                           3 failed, naming it
check_tracked_secrets / validate_contract_fixtures -                           clean / all rules passed
scripts unit tests (Windows host)                  -                           160 run, OK, 28 skipped
git diff --check, and the new files                -                           clean
Frozen handoff contract                            70debad7...0cb0b86a         unchanged; the file is not touched
docs/agent/tb-1/                                   -                           untouched
Alembic head                                       20260908_0048               unchanged; no migration
Frontend                                           -                           untouched
```

Per-file counts are in `cs-11-proof-scripts/outputs/suite_base_5e19123.txt` and `suite_candidate.txt`. These rows, and
`outputs/`, describe the split of `5e19123` - the code the three review rounds read, with round 3's scan corrections.

## Independent review

the independent reviewer, one bounded hashed packet per round: the owner's cap of three rounds, then a fourth to eleventh the owner
authorised on 9 October - on the head merged with `main` (`3ee3abc`), on round 4's corrections with a self-audit
(`5eec962`), on round 5's corrections merged with `main` again (`e3b75ad`), on round 6's corrections (`fa4f824`), on round 7's corrections merged with `main` again (`56b5be4`), on round 8's corrections (`c50df2e`), on round 9's corrections (`2034726`), and on round 10's corrections (`37cad8d`). The verdicts are in
`cs-11-proof-scripts/review/`, with how each was handled.

| Round | Packet | Verdict | Findings |
| --- | --- | --- | --- |
| 1 | `d027910d...` | CORRECTION_REQUIRED | CS11-R1-001: the caller scan covered `backend/` only, while this record spoke of the repository. Corrected by scanning the whole repository (`--repo`), with 9 mutants outside `backend/`. |
| 2 | `b2e716d3...` | CORRECTION_REQUIRED | CS11-R2-001: the same file importable as `backend.app...service` was not followed. CS11-R2-002: a declared site's returned module could reach a new use unseen. Corrected by following every spelling and location loader, and by declaring and checking each declared site's whole flow; the runtime trap added. |
| 3 | `d18b3762...` | CORRECTION_REQUIRED | CS11-R3-001: a declared flow's functions were not fingerprinted, so changing an existing caller passed. CS11-R3-002: another file importing a flow function under an alias was missed. CS11-R3-003: this record said 1,551 text files where the output said 1,553. Corrected - each function of a flow fingerprinted, aliases and string names found, counts taken from the output. |
| 4 | `aeeada14...` | CORRECTION_REQUIRED | CS11-R4-001: a method reading a module-level name that a class attribute shadows was missed (class scopes were treated as visible to methods). CS11-R4-002: `split.py` would write a chained assignment (`A = B = ...`) twice. CS11-R4-003: these records mixed the first split's figures with the current candidate's. Corrected - class scopes and comprehensions modelled, a chained assignment refused, the figures taken from `outputs/after-cs04/` with the first split's kept under "History". |
| 5 | `6caa1a56...` | CORRECTION_REQUIRED | Round 4's corrections, and the self-audit before this round, raised nothing. CS11-R5-001: `split.py` and `proof.py` counted only a statement's own name, so a placed assignment that also bound a new name (`A = (B := ...)`) would be split and pass, the new name neither placed nor re-exported. CS11-R5-002: two of `split_mutants.py`'s cases (the chained assignment, the stray comment) were also refused by another check, so they did not show their own refusal could fail. CS11-R5-003: the continuity note led with the first split's figures. Corrected - every module-level binding of a statement counted by both scripts, each `split.py` mutant shown refused by its own rule alone, the note rewritten with the first split under "History". |
| 6 | `b9446c59...` | CORRECTION_REQUIRED | CS11-R6-001: a placed function declaring its own name `global` and rebinding it bound nothing besides its own name, so both scripts passed it; moved, it would rebind the concern module's name while the service's re-export kept the old function. CS11-R6-002: the continuity note said the CI run on `e2d7e55` had the candidate's code, which since PR #107 was merged in is not exactly so. Corrected - any nested `global` refused by `split.py` and failed by `proof.py` as a rule of its own, with mutants in both; the note says what that CI run covered and that the exact head's run is the push's. |
| 7 | `132ad175...` | CORRECTION_REQUIRED | CS11-R7-001: a definition may run code at import - a constant whose value calls a function, a class body - and the split loads the concern modules in another order than the original's lines ran: two constants in different concerns calling the same recorder would run in the other order, while `split.py`, `proof.py` and `bindings.py` all passed. Corrected - `split.py` refuses and `proof.py` fails any value, default or base other than a literal or a name, unless declared (one: `ZoneInfo("Asia/Kolkata")`), any class body other than `pass`, and a module without `from __future__ import annotations`, with mutants in both; and `import_order.py` shows, at runtime, that importing the application loads every other module in the same order but two inert ones. |
| 8 | `f36d5e49...` | CORRECTION_REQUIRED | CS11-R8-001: the continuity note said the CI run on `e2d7e55` had the same test files as the candidate, though PR #111 has since rewritten one of them. CS11-R8-002: creating a class runs its base's `__init_subclass__` and its metaclass, in the class's turn, which the split can move; a class with a custom base or a metaclass passed both scripts. Corrected - the note says what that run did not cover; `split.py` refuses and `proof.py` fails a class created through anything but the built-in `ValueError` or `LookupError` (not rebound) or a class the original defines, or with a keyword, with mutants in both. |
| 9 | `281597a6...` | CORRECTION_REQUIRED | CS11-R9-001: the packet left out `import_order.py`'s source. CS11-R9-002: a name both imported and defined let a class "based on" a class of the file be built on the import. CS11-R9-003: `split.py` would drop a wildcard import silently. CS11-R9-004: a set element or dictionary key that is not a plain literal runs `__hash__`/`__eq__` at import, and `{**m}` a mapping's protocol. Corrected - the packet carries every script in the folder; both scripts refuse or fail a name both imported and defined, a wildcard or relative import, a key or element not plainly a literal (an imported name is followed to its binding), and `**`, with mutants in both. |
| 10 | `09ce4be0...` | CORRECTION_REQUIRED | CS11-R10-001: an import binding one name twice (`from m import A as K, B as K`) was judged by its first alias, while Python keeps the last. CS11-R10-002: `import_order.py` judged a moved module by a weaker copy of the rules - sets, dictionaries, class bases, metaclasses and annotations passed. Corrected - the rules live once in `import_time_rules.py`, which all three scripts use; a name bound by two imports is refused, and a binding read as the last; mutants in each script, and `import_order_mutants.py` for the moved-module test. |
| 11 | `82a35bd2...` | CORRECTION_REQUIRED | CS11-R11-001: the moved-module test lacked the binding checks `split.py` and `proof.py` apply - a name both imported and defined, `ValueError`/`LookupError` rebound, a name bound twice - and accepted a class based on a same-file class name before that class exists, which an import could bind. Corrected - one shared list, `binding_problems`, used by all three scripts, with a new rule for a base defined only further down; mutants in each, and four more for the moved-module test - but **not re-reviewed**. |

Every finding concerned the evidence scripts or these records. No round raised anything about the split - the moved
code, the re-exports, the retargeted tests. The first findings of rounds 5 to 7, round 8's second, round 9's last three and round 10's both and round 11's concerned kinds of input the current
`service.py` does not contain (no `:=`, no `global`, no import-time call but the one declared): the scripts' refusals
for a future input, not the candidate. The owner authorised the fifth round on 9 October, asking that the pull request's checks run once, when the
package is ready. Before sending it, a self-audit of the evidence scripts closed edges no round had raised - in the
caller scan, `global`/`nonlocal` names and a test reaching a helper through a fixture; in `patch_reach.py`, the
replacement each patch installs, fixture teardown and calls into the application through any binding (all described
above, each with mutants; `review/self-audit-before-r5.md`). Round 11's corrections are committed and their mutants pass
(`outputs/after-cs04/`). On 9 October the owner accepted the package as it stands, without a twelfth round ("let us
accept the package as it stands"): round 11's corrections were not re-reviewed, and CI runs on the exact head once it
is pushed to the pull request.

## Records that name the old layout

Living records that told a reader where this code is, or that it was still to be split, carry a dated reconciliation
note: `CODING_STANDARDS.md` ("When a service outgrows one file"), `DEFERRED_REQUIREMENTS.md` (the code-structure entry,
and the open entry on the one-active-Base-Offer index, which says where the Opportunity lock is taken),
`SKILLS_AND_TOOLS.md`, the TE-6 record and its scripts' README, and the "Where things are" table in PBL's internal working instructions. Slice records, acceptance notes and continuity notes that name
`commercial_offers/service.py` describe the code as it was when they were written and are left as written: since this
package, the function each names is in the `services/` module above that holds its concern. So are three code comments
in other modules (`documents/service.py`, `work_orders/contract.py`, `work_orders/repository.py`), which this package
does not touch because it changes no other module; `_validate_related_work_order`, which one of them names, is in
`services/related_offers.py`.
