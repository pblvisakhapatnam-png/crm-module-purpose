# PF-1A-E1 Acceptance - Explicit Permission Compatibility Foundation

## Closure update, 2 September 2026

**This package is COMPLETE AND INTEGRATED.** The final gate recorded later in this document (a
fresh, read-only independent re-review of the C7 correction pass) returned **VERDICT: ACCEPTED,
no blocking findings**. The package was committed as
`d0b54d34347d33cdbcff1b3622befb317e8a5b32`, merged via PR #11 ("PF-1A-E1: Explicit permission
compatibility foundation") after hosted `Required validation` passed on that exact commit, and is
integrated on `main` as commit `10cc2e49c2bc57cd85374abc31cb23a602fcb641`. Every reference below
to the baseline HEAD (`3c69355858ab352e246a8775f8a463ca7c9c15be`), to the candidate as
"uncommitted", or to the package as "not yet integration-ready" describes the accurate historical
state as of when that section was written and is preserved unedited; it is not current status. See
`docs/continuity/PF_1A_E1_INTEGRATION_CLOSURE_2026-09-02.md` for the full closure record.

**Reconciliation, recorded during independent review of the integration closure package.** Later
in this document, the C6 and C7 correction sections each state, in shorthand, that a correction was
scoped "the same scope every prior correction was scoped to" - meaning only
`backend/tests/test_authorization_route_migration_guard.py` and current-state documentation. That
shorthand is accurate about **C2 through C7**, none of which touched a runtime authorization file.
It must not be read as also describing **C1**: C1 modified
`backend/app/modules/authorization/dependencies.py`, adding `required_permission_code`
introspection metadata to the `require_permission(...)` closure so C1's own baseline/route-inventory
proof could read which permission a live route requests (see
`docs/continuity/PF_1A_E1_C1_CORRECTION_HANDOFF.md` section 3). That edit is metadata-only - it did
not alter `has_permission(...)` evaluation, permission grants, route access, or any independently
reconfirmed compatibility fact in this document - but it is a runtime authorization-module change,
and every C1-inclusive summary in this document is corrected accordingly by this paragraph.

## Package

PF-1A-E1 - Explicit Permission Compatibility Foundation. Technical/architecture-foundation
package within the PF-1A (Organisation Authority activation) delivery line; see
`docs/agent/pf-1a/PF_1A_E1_EXPLICIT_PERMISSION_COMPATIBILITY_FOUNDATION.md` for the full scope
document and `docs/continuity/PF_1A_E1_IMPLEMENTATION_HANDOFF.md` / `docs/continuity/
PF_1A_E1_C1_CORRECTION_HANDOFF.md` for the implementation and correction (C1) run records.

## Objective

Replace every backend route-level `require_roles(*SOME_ROLES)` guard with
`require_permission(PERMISSION_CODE)`, an explicit application-permission code resolved
against a durable, ORA-owned `authz_permission` / `authz_role_permission` compatibility
mapping - while preserving the exact pre-existing effective access matrix. This is a
compatibility/migration foundation, not the full Organisation Authority implementation: no
business authority, HR reference data or approval workflow is introduced.

## Baseline

- Branch: `pf-1a-e1-permission-compatibility-foundation`.
- Protected baseline / unchanged HEAD: `3c69355858ab352e246a8775f8a463ca7c9c15be`.
- Work is uncommitted at both the initial-implementation and C1-correction stages; no commit,
  push, PR or merge has occurred as of this acceptance document.

## Scope covered by this acceptance record

- New `backend/app/modules/authorization/` module (31 permission codes, the compatibility
  matrix, `require_permission(...)`).
- Migration of 76 baseline `require_roles(...)` route guards (across 8 route modules) plus one
  embedded in-body role check (`accounts/routes.py`'s Account tax-verification guard) to the
  new permission layer.
- Alembic migration `20260831_0030` (`authz_permission`, `authz_role_permission`).
- C1 correction: an independent baseline-derived permission/route snapshot
  (`backend/tests/fixtures/pf_1a_e1_baseline_authorization.py`), a route-permission inventory
  proof with explicit dependency metadata, exact (not prefix-wide) ungated-route exceptions,
  and an AST guard against reintroduced direct-role authorization logic in route modules.

## Test users / roles

Seeded prototype users (Alembic revision `20260629_0002`; password `password` for all):

| Username | Role |
| --- | --- |
| `admin1` | `ADMIN` |
| `sales1` | `SALES_USER` |
| `finance1` | `FINANCE_USER` |
| `readonly1` | `MANAGEMENT_READ_ONLY` |

## Starting route

Backend API base: `/api/accounts/{public_id}/tax-profile` (Account PAN/GST verification
boundary). Frontend equivalent: Account detail page, `PAN / GST` tab
(`/accounts/{accountId}`), for a human running the UI path instead of the API directly.

## Required test data

One Account created by `sales1` (`POST /api/accounts` with a unique `account_name`), used as
the target for the PAN verification-state check. No other seed data is required; this boundary
does not depend on Opportunity, Commercial Offer or Work Order records.

## Deterministic verification evidence

### Pre-C1 evidence (historical)

Recorded here as the verification actually executed after the initial implementation
run, before the C1 correction pass described in `docs/continuity/PF_1A_E1_C1_CORRECTION_HANDOFF.md`.
Preserved as historical evidence; superseded for current acceptance purposes by the "Post-C1
deterministic reverification" section below, which records the corrected C1 candidate having
now actually been run.

**PostgreSQL / Alembic**
- A new isolated PostgreSQL Compose volume was created.
- `alembic heads` -> `20260831_0030 (head)`.
- `alembic current` -> `20260831_0030 (head)`.

**Focused PF-1A-E1 tests**
- 15 passed in 2.63s.

**Full backend suite**
- 280 passed, 0 failed, 1 `PytestCollectionWarning`, 236.91s.

**Frontend**
- `typecheck`: PASS.
- tests: 54 passed / 0 failed.
- production build: PASS.
- Only the pre-existing Vite >500 kB chunk warning; no new warnings.

**Repository scripts**
- 58 tests passed in 80.681s.

**Contract fixture validation**
- PASS, 7 candidate fixtures checked.

**Tracked-secret validation**
- PASS; 734 proposed-tree files evaluated, 731 scanned as text, 3 binary/oversized skipped, no
  findings.

**Playwright**
- 12 passed, 9 intentionally skipped `@demo-preflight`, 0 failed. Seeded bundle cleanup
  succeeded; login-audit cleanup succeeded.

None of the commands above were re-executed by the C1 correction session itself (process
execution - `python`, `docker`) required interactive approval this non-interactive session could
not obtain; see `docs/continuity/PF_1A_E1_C1_CORRECTION_HANDOFF.md` section 8 for the exact,
honestly-reported outcome of that attempt, and section 9 for what a reviewer or the project owner
must run before treating the C1 correction as deterministically verified.

### Post-C1 deterministic reverification (current)

The full required sequence from `docs/continuity/PF_1A_E1_C1_CORRECTION_HANDOFF.md` section 9 has
since actually been executed against the corrected C1 candidate. The corrected package is now
deterministically reverified, not merely pending reverification:

**Focused PF-1A-E1 authorization suite**
- 27 passed in 4.59s (includes the new C1-01/C1-02 test files: the baseline-derived permission/
  route snapshot check and the route-permission-inventory proof).

**Full backend suite**
- 292 passed, 0 failed, 1 `PytestCollectionWarning`, 240.02s.

**PostgreSQL / Alembic**
- `alembic current` -> `20260831_0030 (head)`.
- `alembic heads` -> `20260831_0030 (head)`.

**Repository scripts**
- 58 passed in 30.760s.

**Tracked-secret validation**
- PASS; 738 proposed-tree files evaluated, 735 scanned as text, 3 binary/oversized skipped, no
  findings.

These counts differ from the pre-C1 historical evidence above because the C1 correction pass
added new test files and fixtures (the baseline snapshot and route-permission-inventory proof);
the increase is expected and consistent with C1's own scope.

### Post-C2 correction - deterministic reverification (current)

Independent review C2 found runtime authorization behavior compatible and sound (see
`docs/continuity/PF_1A_E1_C2_CORRECTION_HANDOFF.md`) and issued a CORRECTION REQUIRED verdict
scoped entirely to `backend/tests/test_authorization_route_migration_guard.py` (bypassable static
guards) and documentation currency - not to runtime authorization code, the compatibility matrix,
the route inventory or the manual acceptance evidence above, none of which changed. That file was
rewritten (9 test functions -> 19) to close the bypass. The rewritten guard file's tests, and the
rest of the corrected C2 package, have now actually been run. The corrected package is
deterministically reverified, not merely pending reverification:

**Focused authorization suite**
- 37 collected, 37 passed, 5.61s.
- This included baseline equivalence tests, compatibility-matrix tests, authorization repository
  tests, the rewritten route-migration guard tests, and all new synthetic bypass regressions.

**Full backend regression**
- 302 collected, 302 passed, 0 failed, 1 known/pre-existing `PytestCollectionWarning`, 239.57s.
- The increase from the prior 292 full-backend tests (Post-C1 reverification, above) to 302 is
  the 10 new C2 regression tests introduced in the rewritten route-migration guard file.

**PostgreSQL / Alembic**
- `alembic current` -> `20260831_0030 (head)`.
- `alembic heads` -> `20260831_0030 (head)`.

**Targeted synthetic-regression sanity run**
- Command selected the rewritten guard tests matching `"detects or rejects"`.
- 19 collected, 11 selected, 11 passed, 8 deselected, 2.46s.

**Tracked-secret validation**
- PASS; 739 proposed-tree files evaluated, 736 scanned as text, 3 binary/oversized skipped, no
  findings.

These counts supersede the "Post-C1 deterministic reverification" counts above for the
authorization-suite and full-backend-suite totals; the Post-C1 section is preserved as historical
evidence of that earlier reverification pass. **This Post-C2 evidence remains valid, historical PASS
evidence** - it is not superseded or invalidated by the C3 finding below, which concerns three
further static-analysis bypasses in the guard file, not the runtime behavior this evidence proves.

### Post-C3 correction - deterministic reverification (current)

A later independent re-review (C3) independently reconfirmed every runtime result in the Post-C2
section above (exactly 76 protected baseline routes, exactly 11 authenticated-only exceptions, 31
permissions, exactly 110 grants, no privilege widening/narrowing, no implicit ADMIN bypass,
`ACCOUNT_TAX_VERIFY` still FINANCE_USER-only, fail-closed unknown-permission/unmapped-role/
inactive-permission/inactive-grant behavior, sound migration, no HR/business-authority/approval/
delegation/config-publication scope creep, the same 37/302 pass counts, candidate still uncommitted)
but issued a further **CORRECTION REQUIRED** verdict scoped entirely to
`backend/tests/test_authorization_route_migration_guard.py` - the same file C2 rewrote - for three
further, narrower static-analysis bypasses unrelated to runtime behavior: a route-migration
permission guard that inspected only a route's top-level FastAPI dependency list (missing a
permission dependency nested inside another dependency's own signature); two `.role_codes`
exceptions that matched a broader shape than the literal real production statement; and a
`require_roles` reintroduction guard that only inspected actual `Call` nodes (missing a local
rebinding such as `rr = require_roles` before any call). See
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` for the full finding and correction record.

The guard file was rewritten again to close all three. **Deterministic reverification of this
C3-corrected guard file has since been executed by a human operator with process-execution access,
and is now COMPLETE.**

**First deterministic run - historical failure evidence, not erased.** The first execution of the
focused suite found a genuine, previously untested defect introduced by the C3 rewrite itself:
50 collected, **49 passed, 1 failed**. The single failure was
`test_route_required_permission_codes_handles_a_cyclic_dependency_graph_without_infinite_recursion`,
because `_iter_all_dependencies` yielded a cyclic-graph child before checking whether it was already
an ancestor of the current recursion path, so the two-node cycle fixture was double-counted. This is
recorded as historical evidence of what was actually found, not erased or silently corrected away.

**Narrow correction applied.** `_iter_all_dependencies` was corrected to track an immutable,
per-recursion-path ancestor-identity set (`frozenset[int]`, unioned with `id(dependant)` at each
call and never mutated or shared across sibling branches) and to check a child's id against that set
*before* yielding it, rather than checking only after the fact. This yields a true cycle member
exactly once while still yielding a diamond-shared leaf once per independent branch. Full detail:
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 8. Only
`backend/tests/test_authorization_route_migration_guard.py` and documentation were touched; no
runtime authorization file changed.

**Successful rerun after the correction:**

- **Focused authorization suite** (`test_authorization_baseline_equivalence.py`,
  `test_authorization_compatibility_matrix.py`, `test_authorization_repository.py`,
  `test_authorization_route_migration_guard.py`): **50 collected, 50 passed, 0 failed, 5.27s.**
- **Full backend regression**: **315 collected, 315 passed, 0 failed, 1 known pre-existing
  `PytestCollectionWarning` (`tooling/smoke_data/auth_tokens.py:95`, `TestTokenError` has an
  `__init__` constructor), 242.28s.** 315 is exactly the prior Post-C2 figure of 302 plus the 13 C3
  guard tests recorded in the C3 correction handoff section 4 (302 + 13 = 315), confirming no other
  test file changed between the Post-C2 and Post-C3 runs.
- **PostgreSQL / Alembic**: `alembic current` -> `20260831_0030 (head)`; `alembic heads` ->
  `20260831_0030 (head)` - unchanged, as expected, since no migration file was touched by either the
  C3 correction or the ancestor-path fix.
- **Targeted static-guard regression** (`test_authorization_route_migration_guard.py -k "detects or
  rejects"`): **32 collected, 20 selected, 20 passed, 0 failed, 12 deselected, 2.35s.**
- **Tracked-secret validation**: **PASS**; 740 file(s) in the proposed tree, 737 scanned as text, 3
  skipped as binary or oversized, no committed-credential findings.

**What this confirms.** Runtime authorization behavior did not change during the C3 correction, the
ancestor-path test-helper fix, or this reverification. 31 permissions remain; the true grant count
remains 110; there is no implicit ADMIN bypass; `ACCOUNT_TAX_VERIFY` remains `FINANCE_USER`-only.
The candidate remains entirely **uncommitted**; HEAD remains
`3c69355858ab352e246a8775f8a463ca7c9c15be`. See
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 9 for the exact commands and full output.

**Gate as it stood on 1 September 2026, before the fresh re-review described next.** Deterministic
C3 reverification was complete. The remaining gate was a fresh, read-only **independent re-review**
of the C3 correction pass (including the ancestor-path fix) - not further deterministic testing.
This paragraph is preserved as the accurate historical record of that moment; it is not the current
gate. See "Post-C4 correction" below.

### Post-C4 correction - deterministic reverification COMPLETE (current)

The fresh independent re-review named above then ran against the Post-C3 evidence and issued
another **CORRECTION REQUIRED** verdict, still dated 1 September 2026. It independently reconfirmed
the runtime candidate unchanged and correct by every deterministic measure the C3 review already
confirmed - 31 explicit permissions, six transitional roles, exactly 110 grants, exactly 76
protected routes, exactly 11 authenticated-only exceptions, no privilege widening, no privilege
narrowing, no implicit `ADMIN` bypass, `ACCOUNT_TAX_VERIFY` remains `FINANCE_USER`-only, unknown/
unmapped/inactive conditions fail closed, Alembic current/head `20260831_0030 (head)`, no
PF-1A-E2/E3 scope creep, the focused suite independently 50/50 PASS, the targeted guard 20/20 PASS,
and the full backend 315/315 PASS - and again instructed: do not change runtime authorization
behavior.

It found two further, narrower bypasses in
`backend/tests/test_authorization_route_migration_guard.py` - the same file every prior correction
was scoped to - both unrelated to runtime behavior:

- **P2-1 - dynamic `require_roles` reference bypass.** `_scan_for_require_roles` caught every
  direct/aliased/qualified reference and local rebinding of `require_roles`, but a dynamic lookup -
  `getattr(identity_dependencies, "require_roles")` - produced neither a `Name` load nor an
  `Attribute` node the guard inspected, so it passed undetected.
- **P2-2 - spoofable `.role_codes` allow-shapes.** The two `.role_codes` allow-shapes matched on
  call/dict structure and callee-name spelling alone, but never proved the callee
  (`has_permission`, `record_business_event`) was still the genuine, unshadowed import - a local
  rebinding such as `has_permission = policy.has_permission` still matched the shape - and never
  pinned `.role_codes` to its real base object (`user`, `response.user`, so `other.role_codes` still
  matched) or the identity shape's event to the real `event_name="UserLoginSucceeded"` (a fabricated
  event identity carrying the identical payload still matched). A dynamic
  `getattr(user, "role_codes")` equivalent also produced no `.role_codes` `Attribute` node at all,
  invisible to the guard regardless of module.

**The C4 guard correction has been applied**, entirely inside
`backend/tests/test_authorization_route_migration_guard.py`:

- A new `_find_dynamic_literal_attribute_accesses(tree, banned_attr)` helper recognizes three
  AST-obvious dynamic-lookup idioms for a literal banned attribute-name string -
  `getattr(x, "<banned_attr>")`, `vars(x)["<banned_attr>"]`, `x.__dict__["<banned_attr>"]` - and is
  used both for guard 1 (`banned_attr = "require_roles"`, closing P2-1) and, applied unconditionally
  regardless of module, for guard 3 (`banned_attr = "role_codes"`, closing the dynamic-access half
  of P2-2).
- A new bounded binding-site scan (`_iter_target_names` / `_iter_binding_names` /
  `_is_expected_import_binding` / `_name_is_shadowed`) enumerates every place a name can be bound
  anywhere in the tree and fails closed if the tracked helper name (`has_permission`,
  `record_business_event`) is bound anywhere other than the one expected, unaliased import of it
  from the exact real module - closing the helper-rebinding half of P2-2.
- Both allow-shape functions now additionally require `.role_codes` to be accessed on exactly the
  real production base object (`ast.Name(id="user")` for accounts; `ast.Attribute(attr="user",
  value=ast.Name(id="response"))` for identity), and the identity allow-shape additionally requires
  the call to carry `event_name="UserLoginSucceeded"` - closing the remaining half of P2-2.

Twelve new synthetic tests were added (4 for guard 1's dynamic-lookup detection/permitted-unrelated-
usage regression; 8 for guard 3's rebinding/base-object/event-identity/dynamic-access rejection and
genuine-import-not-shadowed regression), taking the file from 32 to **44** test functions. No
existing assertion was weakened, relaxed, or removed. Full detail, the exact correction, and the
complete synthetic-test list are recorded in `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md`
section 10.

**No authorization runtime file changed as part of the C4 correction** -
`backend/app/modules/authorization/**`, every `routes.py` file, the Alembic migration, and
`backend/app/models_metadata.py` are all untouched by this correction.

**Verification status - deterministic C4 reverification is now COMPLETE.** When the C4 correction
was first written, process execution (`python`/`pytest`/`docker compose exec`) was unavailable in
that session: `python --version` succeeded (`Python 3.13.15`), but every attempt to actually run or
compile code returned "This command requires approval," so at that time the correction had been
verified only by re-reading the real production statements, grepping for false-positive risk, and
hand-tracing every test's expected outcome (full disclosure in
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 10, "Verification status of this C4
correction").

**A human operator with `docker`/`python` process-execution access has since actually executed the
full command set.** All results below are from real execution, not prediction or hand-tracing:

- **Focused authorization suite** (`test_authorization_baseline_equivalence.py`,
  `test_authorization_compatibility_matrix.py`, `test_authorization_repository.py`,
  `test_authorization_route_migration_guard.py`): **62 collected, 62 passed, 0 failed, 7.01s**
  (50 + 12 new C4 synthetic tests, exactly as predicted).
- **Full backend regression**: **327 collected, 327 passed, 0 failed, 1 known pre-existing
  `PytestCollectionWarning` (`tooling/smoke_data/auth_tokens.py:95`, `TestTokenError` has an
  `__init__` constructor), 239.07s.** 327 is exactly the prior 315-passed figure plus the 12 new
  C4 guard tests (315 + 12 = 327), confirming no other test file changed.
- **PostgreSQL / Alembic**: `alembic current` -> `20260831_0030 (head)`; `alembic heads` ->
  `20260831_0030 (head)` - unchanged, since no migration file was touched by the C4 correction.
- **Targeted static-guard regression** (`test_authorization_route_migration_guard.py -k "detects or
  rejects"`): **44 collected, 29 selected, 29 passed, 0 failed, 15 deselected, 2.43s.**
- **Tracked-secret validation**: **PASS**; 740 file(s) in the proposed tree, 737 scanned as text, 3
  skipped as binary or oversized, no committed-credential findings.

Full itemized evidence and exact commands are recorded in
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 11.

**What this confirms.** Runtime authorization behavior did not change during the C4 correction or
this reverification: 31 permissions remain, exactly 110 grants remain, there is no implicit ADMIN
bypass, and `ACCOUNT_TAX_VERIFY` remains `FINANCE_USER`-only. The candidate remains entirely
**uncommitted**; HEAD remains `3c69355858ab352e246a8775f8a463ca7c9c15be`.

**Current gate (superseded below by the C5 correction).** Deterministic C4 reverification is
complete. The remaining gate is a fresh, read-only **independent re-review** of this C4 correction
pass - not further deterministic testing. This record does not itself constitute that review and
does not claim final acceptance or integration readiness; until that independent review accepts the
package, it is **not** ready for commit/push per the integration gate (ADR-031).

### C5 correction (dated 1 September 2026)

**A fresh independent re-review of the C4-corrected guard (C5) AGAIN re-confirmed the runtime
candidate is unchanged and correct by every deterministic measure it independently re-ran**, and
issued a further CORRECTION REQUIRED verdict scoped to exactly two bypass classes in the static
guard file itself, not runtime behavior:

- **P2-1**: the C4 `_find_dynamic_literal_attribute_accesses(tree, banned_attr)` helper recognized
  only a single unbroken string constant as the `getattr(...)` name argument or subscript key, and
  only the subscript form of the `vars(x)`/`x.__dict__` idiom. `vars(deps).get("require_roles")`,
  `deps.__dict__.get("require_roles")` and `getattr(deps, "require_" + "roles")` were all
  independently demonstrated to evade it.
- **P2-2**: the `.role_codes` allow-shapes' C4 `_name_is_shadowed(...)` check rejected an explicit
  conflicting binding but never required the tracked helper name to genuinely resolve to an
  EXISTING expected import (a star import - `from fake_policy import *` /
  `from fake_events import *` - could silently supply it undetected), never enumerated
  match-statement capture patterns (`case has_permission:`) as a binding site at all, and pinned the
  `.role_codes` base object and (for accounts) the permission constant only by NAME SPELLING, not
  genuine production provenance, so an in-function rebinding (`user = other`,
  `ACCOUNT_TAX_VERIFY = ACCOUNT_READ`, `response = fake_response`) or a decoy duplicate target
  function (a second `def login(...)` / `def _assert_tax_verification_permission(...)` anywhere in
  the module) still matched. All were independently demonstrated as live bypasses of the guard.

**Correction to prior wording:** the sentence above at line 288 describing the C4 binding-site scan
as enumerating "every place a name can be bound anywhere in the tree" is corrected. It enumerates
the BOUNDED set of Python binding forms `_iter_binding_names` explicitly lists (assignment/
augmented-assignment/annotated-assignment/walrus targets, for-loop and comprehension targets,
`with`/`except` bindings, function/class definitions and parameters, and import aliases) - not
match-statement capture patterns, which C5 adds. That sentence is left as written above as an
accurate record of what C4 itself implemented at the time; this note is the correction, not a
rewrite of the historical claim.

**The C5 guard correction has been applied**, entirely inside
`backend/tests/test_authorization_route_migration_guard.py`:

- A bounded compile-time string evaluator (`_eval_compile_time_string`) - a plain string constant,
  or an `Add` `BinOp`/`JoinedStr` whose parts are themselves compile-time strings, never a variable,
  function call or string method - is now used everywhere `_find_dynamic_literal_attribute_accesses`
  compares against the banned attribute name, and the helper now also recognizes `.get(...)` method
  calls against `vars(x)`/`x.__dict__`, closing P2-1.
- `_iter_binding_names` is extended to enumerate `ast.MatchAs`/`ast.MatchStar`/`ast.MatchMapping`
  binding sites, so a match-statement capture of a tracked name is treated as shadowing the same as
  an ordinary assignment.
- A new `_helper_provenance_is_trustworthy(tree, name, expected_module, expected_original_name)`
  supersedes the bare C4 `_name_is_shadowed(...)` call for every tracked helper/constant name
  (`has_permission`, `ACCOUNT_TAX_VERIFY`, `record_business_event`): it requires EXACTLY ONE genuine
  expected `ImportFrom` binding to exist (not merely "no conflicting binding"), and fails closed if
  the module contains ANY star import at all.
- The two `.role_codes` allow-shape functions are restructured into a separate, reusable SHAPE-only
  predicate (`_accounts_role_codes_shape_matches` / `_identity_role_codes_shape_matches`) plus an
  explicit provenance model: the enclosing target function must be the UNIQUE
  `FunctionDef`/`AsyncFunctionDef` with the expected name and sync/async-ness
  (`_unique_target_function`); the shape-matching statement must occur EXACTLY ONCE inside that
  function; and the base object's provenance is proved trustworthy (`_user_provenance_is_trustworthy`
  - the real parameter position for `user`; `_response_provenance_is_trustworthy` - the one real
  `response = login_user(...)` assignment for `response`, with no other binding of that name
  anywhere in the function, plus, as defense in depth, `login_user` itself proved to be the genuine
  imported production login service function rather than a same-named local decoy).

Twenty-two new synthetic tests were added (6 for guard 1's `.get(...)`/compile-time-string-
concatenation detection and permitted-unrelated-usage regression; 16 for guard 3's missing-import/
star-import/match-capture/base-object-rebinding/permission-constant-rebinding/duplicate-target-
function/duplicate-statement/dynamic-access rejection, plus the `login_user`-decoy defense-in-depth
test), taking the file from 44 to **66** test functions. No existing assertion was weakened,
relaxed, or removed; four pre-existing "permits the real production shape" tests were updated to
include the full genuine production provenance (imports, and for identity the
`response = login_user(...)` assignment) that the stronger C5 model now requires the real accepted
shape to demonstrate - not weakened, but completed to match what the real production files actually
contain. Full detail is recorded in `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 12.

**No authorization runtime file changed as part of the C5 correction** -
`backend/app/modules/authorization/**`, every `routes.py` file, the Alembic migration, and
`backend/app/models_metadata.py` are all untouched by this correction.

**Verification status - deterministic C5 reverification is PENDING.** Process execution
(`python`/`pytest`/`docker compose exec`) was not available in the session that wrote this
correction: `python --version` succeeded once, but every other `python`/`docker` invocation
(including `python -m py_compile` against the corrected file) returned "This command requires
approval," so the correction has been verified only by re-reading the real production statements in
`backend/app/modules/accounts/routes.py` and `backend/app/modules/identity/routes.py`, hand-tracing
every new synthetic test's expected outcome against the new provenance-model code, and confirming
the real production statements still pass every new check. No test was claimed to have executed and
passed; this is stated explicitly rather than implied.

**Current gate as it stood before deterministic reverification (superseded below).** Deterministic
C5 reverification (the same command set used for C4: focused authorization suite, full backend
regression, Alembic current/heads, targeted `-k "detects or rejects"` selection, tracked-secret
scan), then a fresh, read-only **independent re-review** of this C5 correction pass. This paragraph
is preserved as the accurate historical record of the gate as it stood at that moment; it is not the
current gate. See "Post-C5 correction - deterministic reverification COMPLETE" below.

### Post-C5 correction - deterministic reverification COMPLETE (superseded by the C6 correction below; this section itself remains an accurate historical record)

A human operator with `docker`/`python` process-execution access subsequently ran the full command
set named above against the C5-corrected candidate (the compile-time string evaluator, `.get(...)`
recognition, match-pattern-capture binding enumeration, and the explicit helper/base-object/target-
function provenance model described in "C5 correction" above). All results below are from actual
execution, not prediction or hand-tracing:

**Focused authorization suite**
- `test_authorization_baseline_equivalence.py`, `test_authorization_compatibility_matrix.py`,
  `test_authorization_repository.py`, `test_authorization_route_migration_guard.py`: **84 collected,
  84 passed, 0 failed, 5.20s.** 84 is exactly the prior C4 figure of 62 plus the 22 new C5 synthetic
  tests (62 + 22 = 84).

**Full backend regression**
- **349 collected, 349 passed, 0 failed, 1 known pre-existing `PytestCollectionWarning`
  (`tooling/smoke_data/auth_tokens.py:95`, `TestTokenError` has an `__init__` constructor),
  258.68s.** 349 is exactly the prior C4 figure of 327 plus the same 22 new C5 tests
  (327 + 22 = 349), confirming no other test file changed.

**PostgreSQL / Alembic**
- `alembic current` -> `20260831_0030 (head)`.
- `alembic heads` -> `20260831_0030 (head)`.
- Unchanged, as expected, since no migration file was touched by the C5 correction.

**Targeted static-guard regression**
- `test_authorization_route_migration_guard.py -k "detects or rejects"`: **66 collected, 49
  selected, 49 passed, 0 failed, 17 deselected, 3.61s.** The guard file itself now totals 66 test
  functions (44 + 22 new C5 tests), of which 49 match the `"detects or rejects"` filter.

**Tracked-secret validation**
- **PASS**; 740 file(s) in the proposed tree (`git ls-files --cached --others --exclude-standard`),
  737 scanned as text, 3 skipped as binary or oversized, no committed-credential findings.

**Patch integrity**
- `git diff --check`: clean, no output.

**Repository state**
- `git status --short` showed only the expected PF-1A-E1 candidate files; no unexpected files
  appeared; nothing is staged.
- `git rev-parse HEAD`: `3c69355858ab352e246a8775f8a463ca7c9c15be` - unchanged.

**What this confirms.** Runtime authorization behavior did not change during the C5 correction or
this reverification: 31 permissions remain, exactly 110 grants remain, there is no implicit ADMIN
bypass, and `ACCOUNT_TAX_VERIFY` remains `FINANCE_USER`-only. The candidate remains entirely
**uncommitted**; HEAD remains `3c69355858ab352e246a8775f8a463ca7c9c15be`. See
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 13 for the exact commands and full
output.

**Current gate (superseded below by the C6 correction).** Deterministic C5 reverification is
COMPLETE. The remaining gate is a fresh, read-only **independent re-review** of this C5 correction
pass - not further deterministic testing. This record does not itself constitute that review and
does not claim final acceptance or integration readiness; until that independent review accepts the
package, it is **not** ready for commit/push per the integration gate (ADR-031).

### C6 correction (dated 1 September 2026)

**A fresh independent re-review of the C5-corrected guard (C6) AGAIN re-confirmed the runtime
candidate is unchanged and correct by every deterministic measure it independently re-ran (the same
31-permission/six-role/110-grant/76-route/11-exception/87-entry facts, no privilege
widening/narrowing, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still `FINANCE_USER`-only,
fail-closed unknown-permission/unmapped-role/empty-role/inactive-permission/inactive-grant behavior,
independent baseline fixture, Alembic `20260831_0030 (head)`, focused suite 84/84, full backend
349/349, targeted guard 49/49, tracked-secret scan clean, `git diff --check` clean), but again
issued a further CORRECTION REQUIRED verdict** scoped to exactly two bypass classes in the static
guard file itself (guard 3 - the `.role_codes` fail-closed checks - only; guard 1's `require_roles`
detection was not implicated):

- **P3-1 (import provenance counted per statement, not per alias).** A single `ImportFrom`
  statement carrying both a genuine alias and a conflicting one for the same tracked local name -
  `from mod import ACCOUNT_TAX_VERIFY, ACCOUNT_READ as ACCOUNT_TAX_VERIFY`, and the equivalent for
  `has_permission`, `record_business_event`, `login_user`, in either alias order - still passed,
  because the pre-C6 check asked only whether the enclosing statement contained a genuine alias
  somewhere, not whether the SPECIFIC alias that produced each binding occurrence was genuine.
- **P3-2 (allowed occurrences not pinned to the target function's immediate lexical scope).** The
  occurrence-uniqueness check walked the target function's FULL `ast.walk` subtree, which descends
  through every nested lexical scope, so the allowed statement moved inside a nested `def`/
  `async def`/`lambda` under the real target function (for identity, both the
  `response = login_user(...)` assignment and the audit call moved together into one nested `def`)
  - or a lambda whose OWN parameter shadows the real outer `user`/`response` while the base-object
  name spelling still matched textually - still counted as belonging to the target function's own
  immediate body.

Root causes and the full bypass demonstrations are recorded in
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 14.

**The C6 guard correction has been applied**, entirely inside
`backend/tests/test_authorization_route_migration_guard.py`: `_iter_binding_names` now yields a
`(import_node, alias)` marker for each `ImportFrom` binding rather than the bare statement, and
`_is_expected_import_binding` / `_count_expected_import_bindings` check that specific alias, closing
P3-1; a new bounded `_iter_immediate_scope_nodes(func_node)` traversal collects candidate
occurrences only from a function's own immediate lexical scope (a nested scope-introducing node is
itself yielded, so its presence is still visible, but its contents are never descended into), used
by both per-module allow-shape functions and `_find_legitimate_response_assignment`, closing P3-2;
and `_iter_binding_names` is further extended to enumerate `ast.Lambda` parameters as binding sites
(defense in depth alongside the scope restriction). Because the fail-closed `.role_codes` visitor
still visits every `.role_codes` access anywhere in the module regardless of scope, a nested-scope
occurrence is never silently dropped from consideration - it is still visited, still fails the
immediate-scope check, and is still reported as an offense. Twenty-two new synthetic tests were
added (9 for P3-1, 13 for P3-2), taking the guard file from 66 to **88** test functions; no existing
assertion was weakened, relaxed, or removed.

**No authorization runtime file changed as part of the C6 correction** -
`backend/app/modules/authorization/**`, every `routes.py` file, the Alembic migration file, and
`backend/app/models_metadata.py` are all untouched; only the guard test file and current-state
documentation changed, the same scope every prior correction was scoped to.

**Verification status - deterministic C6 reverification is COMPLETE.** A human operator with
`docker`/`python` process-execution access subsequently ran the full command set named above
against the C6-corrected candidate. See "Post-C6 correction - deterministic reverification
COMPLETE" below for the exact commands and full output.

### Post-C6 correction - deterministic reverification COMPLETE (superseded by the C7 correction below; this section itself remains an accurate historical record)

All results below are from actual execution, not prediction or hand-tracing, and every one of the
predictions recorded in `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 14 is confirmed
exactly.

**Guard file alone**
- `test_authorization_route_migration_guard.py -v`: **88 collected, 88 passed, 0 failed, 4.75s.**
  88 is exactly the prior C5 figure of 66 plus the 22 new C6 synthetic tests (66 + 22 = 88).

**Focused authorization suite**
- `test_authorization_baseline_equivalence.py`, `test_authorization_compatibility_matrix.py`,
  `test_authorization_repository.py`, `test_authorization_route_migration_guard.py`: **106
  collected, 106 passed, 0 failed, 5.13s.** 106 is exactly the three non-guard files' unchanged 18
  tests (84 - 66 = 18) plus the guard file's new total of 88 (18 + 88 = 106).

**Full backend regression**
- **371 passed, 0 failed, 1 known pre-existing `PytestCollectionWarning`
  (`tooling/smoke_data/auth_tokens.py:95`, `TestTokenError` has an `__init__` constructor),
  260.24s.** 371 is exactly the prior C5 figure of 349 plus the same 22 new C6 tests
  (349 + 22 = 371), confirming no other test file changed.

**PostgreSQL / Alembic**
- `alembic current` -> `20260831_0030 (head)`.
- `alembic heads` -> `20260831_0030 (head)`.
- Unchanged, as expected, since no migration file was touched by the C6 correction.

**Targeted static-guard regression**
- `test_authorization_route_migration_guard.py -k "detects or rejects"`: **88 total collected, 65
  selected, 65 passed, 0 failed, 23 deselected, 3.34s.**

**Tracked-secret validation**
- **PASS**; 740 file(s) in the proposed tree (`git ls-files --cached --others --exclude-standard`),
  737 scanned as text, 3 skipped as binary or oversized, no committed-credential findings.

**Patch integrity**
- `git diff --check`: clean, no output.

**Repository state**
- `git status --short` showed only the expected PF-1A-E1 candidate files; no unexpected files
  appeared; nothing is staged.
- `git rev-parse HEAD`: `3c69355858ab352e246a8775f8a463ca7c9c15be` - unchanged.

**What this confirms.** Runtime authorization behavior did not change during the C6 correction or
this reverification: 31 permissions remain, exactly 110 grants remain, there is no implicit ADMIN
bypass, and `ACCOUNT_TAX_VERIFY` remains `FINANCE_USER`-only. The candidate remains entirely
**uncommitted**; HEAD remains `3c69355858ab352e246a8775f8a463ca7c9c15be`. See
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 15 for the exact commands and full
output.

**Current gate (superseded below by the C7 correction).** Deterministic C6 reverification is
COMPLETE. The remaining gate was a fresh, read-only **independent re-review** of this C6 correction
pass - not further deterministic testing. See "C7 correction (dated 1 September 2026)" below.

### C7 correction (dated 1 September 2026)

**A fresh independent re-review of the C6-corrected guard (C7) AGAIN re-confirmed the runtime
candidate is unchanged and correct by every deterministic measure it independently re-ran (the same
31-permission/six-role/110-grant/76-route/11-exception/87-entry facts, no privilege
widening/narrowing, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still `FINANCE_USER`-only,
fail-closed unknown-permission/unmapped-role/empty-role/inactive-permission/inactive-grant behavior,
independent baseline fixture, Alembic `20260831_0030 (head)`, focused suite 106/106, full backend
371/371, targeted guard 65/65, tracked-secret scan clean, `git diff --check` clean, and every C1-C6
protection reconfirmed intact - per-import-alias provenance, nested def/async def/lambda/class
rejection, every lambda parameter form enumerated), but again issued a further CORRECTION REQUIRED
verdict** scoped to exactly one bypass class in the static guard file itself (guard 3 - the
`.role_codes` fail-closed checks - only; guards 1 and 2 were not implicated):

- **P4-1 (comprehension/generator implicit scopes missing from the bounded immediate-scope
  model).** The C6 bounded lexical-scope model (`_SCOPE_INTRODUCING_NODE_TYPES`,
  `_iter_immediate_scope_nodes`) recognized a nested `def`/`async def`/`lambda`/`class` as a scope
  boundary but did not recognize a Python comprehension or generator expression
  (`ast.ListComp`/`ast.SetComp`/`ast.DictComp`/`ast.GeneratorExp`), even though each of these
  executes its element/key/value expression in its own implicit nested scope exactly the same way.
  Independently demonstrated by wrapping the real
  `has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)` statement, and separately the real
  `record_business_event(...)` audit call, inside a bare generator expression assigned to a local
  and never consumed: `check = (has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY) for item in
  (1,))`. This is especially dangerous at the runtime level, independent of the guard: the generator
  object itself is truthy, so `if not check:` never raises, and the wrapped permission call is never
  even executed - a silent no-op that looks like an enforced check.

Root cause and the full bypass demonstration are recorded in
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 16.

**The C7 guard correction has been applied**, entirely inside
`backend/tests/test_authorization_route_migration_guard.py`: `_SCOPE_INTRODUCING_NODE_TYPES` now
also includes `ast.ListComp`, `ast.SetComp`, `ast.DictComp` and `ast.GeneratorExp` alongside the
existing `ast.FunctionDef`/`ast.AsyncFunctionDef`/`ast.Lambda`/`ast.ClassDef`, so
`_iter_immediate_scope_nodes` yields a comprehension/generator node itself (its presence stays
visible) but never descends into its element/key/value/generators - the same yield-but-do-not-
descend treatment already applied to a nested function/lambda/class. Because the fail-closed
`.role_codes` visitor still visits every `.role_codes` access anywhere in the module regardless of
scope (a separate, unaffected full-tree `ast.NodeVisitor` traversal using `generic_visit`), a
comprehension/generator-nested occurrence is never silently dropped from consideration - it is
still visited, still fails the immediate-scope occurrence check, and is still reported as an
offense. Eleven new synthetic tests were added (4 accounts comprehension/generator rejections - one
each for `GeneratorExp`, `ListComp`, `SetComp`, `DictComp` - 4 identity comprehension/generator
rejections in the same four forms, 2 positive regressions proving the genuine immediate-scope
statements remain accepted, and 1 direct unit test proving `_iter_immediate_scope_nodes` itself
excludes comprehension/generator bodies), taking the guard file from 88 to **99** test functions;
no existing assertion was weakened, relaxed, or removed. Comprehension/generator TARGET names
(`for item in ...`) were already enumerated as binding sites by `_iter_binding_names` via
`ast.comprehension` before this correction and needed no change.

**No authorization runtime file changed as part of the C7 correction** -
`backend/app/modules/authorization/**`, every `routes.py` file, the Alembic migration file, and
`backend/app/models_metadata.py` are all untouched; only the guard test file and current-state
documentation changed, the same scope every prior correction was scoped to.

**Verification status - deterministic C7 reverification is PENDING, not yet executed.** The
non-interactive session that performed the C7 correction attempted to run `python`/`docker` for
this reverification and both were denied without approval in this session, so none of the following
were executed here: the guard file alone, the four-file focused authorization suite, the full
backend regression, `alembic current`/`alembic heads`, the targeted `-k "detects or rejects"`
selection, or the tracked-secret scan. The only checks actually performed in this session were
static: the corrected file was confirmed to parse (`ast.parse` succeeds against the whole file) and
was confirmed by direct count (`grep -c '^def test_'`) to contain exactly 99 `test_` functions
(88 + 11 = 99, matching the prediction above), and `git status`/`git diff --stat HEAD`/
`git rev-parse HEAD` were used to confirm HEAD is unchanged at
`3c69355858ab352e246a8775f8a463ca7c9c15be`, the index is empty, and no file outside
`backend/tests/test_authorization_route_migration_guard.py` and the four permitted current-state
docs was touched. This is not a substitute for the deterministic command sequence and is not
claimed as one. A human operator with `docker`/`python` process-execution access must run the same
sequence C6 reverification ran before this correction can be considered verified; see "Post-C6
correction - deterministic reverification COMPLETE" above for the exact command set to repeat
against the C7-corrected candidate.

**Current gate as it stood before deterministic reverification (superseded below).** Deterministic
C7 reverification (guard file alone, the four-file focused authorization suite, full backend
regression, Alembic current/heads, a targeted lexical-scope subset, tracked-secret scan), then a
fresh, read-only **independent re-review** of this C7 correction pass. This paragraph is preserved
as the accurate historical record of the gate as it stood at that moment; it is not the current
gate. See "Post-C7 correction - deterministic reverification COMPLETE" below.

### Post-C7 correction - deterministic reverification COMPLETE (current)

A human operator with `docker`/`python` process-execution access subsequently ran deterministic
verification against the C7-corrected candidate (the `_SCOPE_INTRODUCING_NODE_TYPES` extension to
`ast.ListComp`/`ast.SetComp`/`ast.DictComp`/`ast.GeneratorExp` described in "C7 correction" above).
All results below are from actual execution, not prediction or hand-tracing.

**Guard file alone**
- `test_authorization_route_migration_guard.py -v`: **99 collected, 99 passed, 0 failed, 4.45s.**
  99 is exactly the prior C6 figure of 88 plus the 11 new C7 synthetic tests (88 + 11 = 99).

**Focused authorization suite**
- `test_authorization_baseline_equivalence.py`, `test_authorization_compatibility_matrix.py`,
  `test_authorization_repository.py`, `test_authorization_route_migration_guard.py`: **117
  collected, 117 passed, 0 failed, 5.74s.** 117 is exactly the three non-guard files' unchanged 18
  tests (106 - 88 = 18) plus the guard file's new total of 99 (18 + 99 = 117).

**Full backend regression**
- **382 passed, 0 failed, 1 known pre-existing `PytestCollectionWarning`
  (`tooling/smoke_data/auth_tokens.py:95`, `TestTokenError` has an `__init__` constructor),
  344.93s.** 382 is exactly the prior C6 figure of 371 plus the same 11 new C7 tests
  (371 + 11 = 382), confirming no other test file changed.

**PostgreSQL / Alembic**
- `alembic current` -> `20260831_0030 (head)`.
- `alembic heads` -> `20260831_0030 (head)`.
- Unchanged, as expected, since no migration file was touched by the C7 correction.

**Targeted C7 lexical-scope regression**
- Command: `test_authorization_route_migration_guard.py -k "comprehension or generator or scope"`.
- Result: **15 selected, 15 passed, 0 failed, 84 deselected, 3.34s**, out of 99 collected in the
  guard file.
- This is a deliberate substitution, not an omission: the operator chose a filter naming the exact
  P4-1 change (comprehension/generator/scope-boundary tests) directly, rather than repeating the
  C4-C6 "detects or rejects" convention. The "detects or rejects" filter specifically was not
  independently re-run under that exact string in this session, and that is recorded honestly
  rather than assumed; full-file coverage is nonetheless proven by the guard-file-alone result
  above (99 collected, 99 passed), which executes every test in the file regardless of which `-k`
  substring a narrower spot-check uses.

**Tracked-secret validation**
- **PASS**; 740 file(s) in the proposed tree (`git ls-files --cached --others --exclude-standard`),
  737 scanned as text, 3 skipped as binary or oversized, no committed-credential findings.

**Patch integrity**
- `git diff --check`: clean, no output.

**Repository state**
- `git status --short` showed only the expected PF-1A-E1 candidate files; no unexpected files
  appeared; nothing is staged.
- `git rev-parse HEAD`: `3c69355858ab352e246a8775f8a463ca7c9c15be` - unchanged.

**What this confirms.** Runtime authorization behavior did not change during the C7 correction or
this reverification: 31 permissions remain, exactly 110 grants remain, there is no implicit ADMIN
bypass, and `ACCOUNT_TAX_VERIFY` remains `FINANCE_USER`-only. The candidate remains entirely
**uncommitted**; HEAD remains `3c69355858ab352e246a8775f8a463ca7c9c15be`. See
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 17 for the exact commands and full
output.

**Current gate.** Deterministic C7 reverification is COMPLETE. The remaining gate is a fresh,
read-only **independent re-review** of this C7 correction pass - not further deterministic
testing. This record does not itself constitute that review and does not claim final acceptance or
integration readiness; until that independent review accepts the package, it is **not** ready for
commit/push per the integration gate (ADR-031).

**Superseded, 2 September 2026.** This paragraph is preserved as historical record of the gate as
it stood at that point. That fresh independent re-review has since run and returned VERDICT:
ACCEPTED with no blocking findings; the package was committed as
`d0b54d34347d33cdbcff1b3622befb317e8a5b32` and integrated on `main` as commit
`10cc2e49c2bc57cd85374abc31cb23a602fcb641` via PR #11. See
`docs/continuity/PF_1A_E1_INTEGRATION_CLOSURE_2026-09-02.md`.

## Happy path (automated, already covered by `backend/tests/test_accounts_api.py`)

1. `sales1` creates an Account (`POST /api/accounts`).
2. `finance1` submits `POST /api/accounts/{public_id}/tax-profile` with
   `{"pan": "<unique PAN>", "pan_verification_state_code": "VERIFIED"}`.
3. Expected: `201`/`200`, response `tax_profile.pan_verification_state_code == "VERIFIED"`.

Automated equivalent: `test_finance_user_can_capture_and_verify_tax_profile_and_gstin` in
`backend/tests/test_accounts_api.py` (unchanged by PF-1A-E1 or C1; traced against the new
permission mapping and confirmed to still hold, per the implementation handoff section 8).

## Negative / permission path (automated, already covered)

1. `sales1` creates an Account.
2. `sales1` submits `POST /api/accounts/{public_id}/tax-profile` with
   `{"pan": "<unique PAN>", "pan_verification_state_code": "VERIFIED"}`.
3. Expected: `403 Forbidden` (`ACCOUNT_TAX_VERIFY` is granted only to `FINANCE_USER`, never
   `SALES_USER`, `SALES_MANAGER` or `ADMIN`).

Automated equivalent: `test_sales_user_cannot_set_verified_tax_states` in
`backend/tests/test_accounts_api.py` (unchanged; re-traced against `ACCOUNT_TAX_VERIFY` and
confirmed to still hold).

## Manual acceptance checks - EXECUTED, PASS

Both checks below have been executed. They exercise the same narrow, already-supported
`ACCOUNT_TAX_VERIFY` boundary as the automated tests above, chosen because it is a real,
deliberately narrow permission (excludes `ADMIN`) reachable through the existing PAN/GST UI.

Manual acceptance Account used for both checks:

- `account_name`: `PF-1A-E1 Manual Acceptance 20260901-110536`
- `account_public_id`: `2abcadb1-0efc-42ca-ad28-4f3a83ff5c1b`

### Manual check 1 - allowed action - PASS

- Test user: `finance1`, role `FINANCE_USER`.
- Starting route: existing Account PAN/GST UI.
- Steps: entered PAN `PFAAA1234A`, set PAN verification state to `VERIFIED`, saved.
- Observed result: save succeeded; the UI showed the PAN as `VERIFIED`.
- Result: **PASS**.

### Manual check 2 - denied action - PASS

- Test user: `admin1`, role `ADMIN`.
- Note: there was initially browser-session ambiguity because the UI does not visibly display
  the logged-in username/role. The denied path was therefore independently proven through the
  live API with explicit `admin1` credentials against the same Account, rather than relying on
  UI-only session inference.
- Observed via API: authenticated as `admin1`; attempted
  `pan_verification_state_code = VERIFIED`; backend result `HTTP 403`; detail message: "PAN/GST
  verification states can be set only by Finance / Accounts role."
- Also observed in the UI: Admin did not have the option to select `VERIFIED`. Admin could
  change the PAN value and set the state to `VERIFICATION_PENDING`. This confirms
  `ACCOUNT_TAX_CAPTURE` remains available to `ADMIN` while `ACCOUNT_TAX_VERIFY` remains
  Finance-only, as intended by PF-1A-E1.
- Result: **PASS**.

## Non-blocking observations / follow-up candidates

Recorded during manual acceptance. Neither is an E1 authorization blocker and neither is an
approved requirement; both are candidates for future consideration only.

1. **UI identity visibility.** The application shell does not currently visibly show the
   logged-in username/role. This made human-session identification less obvious during manual
   check 2 and required independently confirming the denied path via the live API with explicit
   `admin1` credentials. Record as a UX/operational-context improvement candidate, not an
   E1 authorization blocker.
2. **Post-verification PAN mutability.** Because `ADMIN` currently retains
   `ACCOUNT_TAX_CAPTURE`, after a PAN is verified an Admin can still change the PAN value and
   move the state back to `VERIFICATION_PENDING`, although Admin cannot set `VERIFIED` or
   `REJECTED_INCORRECT`. This is recorded only as a candidate future Account legal-identity
   control: consider freezing PAN-value changes after successful verification except for
   Finance/Accounts (and later the governed SurePass exception path, per ADR-014/ADR-015). This
   is **not** stated as an approved requirement and is **not** implemented in PF-1A-E1.

## Deferred checks

- No frontend code changed in this package, so no frontend-specific UI acceptance beyond the
  two manual checks above is required.
- Broader manual regression across every migrated permission boundary (30+ Commercial Offer
  routes, Work Order Amendment routes, etc.) is not required for this package's acceptance;
  the deterministic route-permission-inventory proof (C1-02) is the intended safeguard for
  route-level correctness at this scale, with the two manual checks above as a representative,
  human-executed spot check of one deliberately narrow boundary.
- Hosted CI (`Required validation`) has not been run against this branch; per ADR-031 this is
  required before integration into `main`, independent of this acceptance record.

## Manual gaps

- Historical: the C1 correction session itself could not execute `docker compose exec backend
  pytest`, `alembic heads`/`current`, the frontend gate, repository scripts, or the Playwright
  suite (process execution was blocked at that time; see the C1 correction handoff section 8).
  This gap is closed: the "Post-C1 deterministic reverification" section above records that the
  required sequence has since actually been run against the corrected C1 candidate.
- Frontend gate (`typecheck`/tests/build) and Playwright were not re-listed in the Post-C1
  reverification results above; no frontend code changed in this package (see "Deferred
  checks"), so the pre-C1 frontend/Playwright evidence recorded earlier remains the applicable
  record for those two items.
- The two manual acceptance checks above are complete (both PASS); no manual gap remains for
  them.

## Integration acceptance criteria

Before this package may be committed, reviewed and integrated per
`docs/agent/architecture/INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md`:

```text
[x] All required reverification commands in the C1 correction handoff (section 9) pass,
    including the new C1-01/C1-02 test files.
[x] Manual check 1 (allowed action) executed and recorded PASS.
[x] Manual check 2 (denied action) executed and recorded PASS.
[x] Independent review (C2) confirms no privilege widening/narrowing versus the baseline
    snapshot at the runtime level.
[x] Deterministic reverification of the C2-corrected
    `backend/tests/test_authorization_route_migration_guard.py` (see "Post-C2 correction -
    deterministic reverification (current)" above) is executed and passes.
[x] Independent review (C3) re-confirms no privilege widening/narrowing versus the baseline
    snapshot at the runtime level, and independently reconfirms the C2 deterministic evidence
    above (76/11/31/110 counts, 37/302 pass counts).
[x] Deterministic reverification of the C3-corrected
    `backend/tests/test_authorization_route_migration_guard.py` (see "Post-C3 correction -
    deterministic reverification (current)" above) is executed and passes.
[x] A fresh independent re-review of the C3 correction pass (including the ancestor-path fix) ran
    and returned its verdict: CORRECTION REQUIRED (C4) - see "Post-C4 correction - deterministic
    reverification PENDING (current)" above. This satisfies "a fresh independent re-review ran and
    was recorded"; it does NOT satisfy "accepts the fully corrected package," which remains open
    below.
[x] C4 guard correction (P2-1 dynamic require_roles bypass; P2-2 spoofable role_codes allow-shapes)
    applied to `backend/tests/test_authorization_route_migration_guard.py` only; no runtime
    authorization file changed.
[x] Deterministic reverification of the C4-corrected
    `backend/tests/test_authorization_route_migration_guard.py` (see "Post-C4 correction -
    deterministic reverification COMPLETE (current)" above) is executed and passes (62/62 focused,
    327/327 full backend, Alembic sound, 29/29 targeted, secret scan PASS).
[x] A fresh, read-only independent re-review of the C4 correction pass ran and returned its
    verdict: CORRECTION REQUIRED (C5) - see "C5 correction (dated 1 September 2026)" above. This
    satisfies "a fresh independent re-review ran and was recorded"; it does NOT satisfy "accepts
    the fully corrected package," which remains open below.
[x] C5 guard correction (P2-1 bounded compile-time string evaluation and `.get(...)` dynamic-lookup
    coverage; P2-2 exact expected helper-import provenance, star-import fail-closed, match-pattern
    binding enumeration, unique target-function and unique allowed-statement enforcement) applied to
    `backend/tests/test_authorization_route_migration_guard.py` only; no runtime authorization file
    changed.
[x] Deterministic reverification of the C5-corrected
    `backend/tests/test_authorization_route_migration_guard.py` (see "Post-C5 correction -
    deterministic reverification COMPLETE" above) is executed and passes (84/84 focused,
    349/349 full backend, Alembic sound, 49/49 targeted, secret scan PASS, `git diff --check`
    clean).
[x] A fresh, read-only independent re-review of the C5 correction pass ran and returned its
    verdict: CORRECTION REQUIRED (C6) - see "C6 correction (dated 1 September 2026)" above. This
    satisfies "a fresh independent re-review ran and was recorded"; it does NOT satisfy "accepts
    the fully corrected package," which remains open below.
[x] C6 guard correction (P3-1 per-alias import provenance, closing a same-`ImportFrom`-statement
    alias-collision bypass; P3-2 bounded immediate-lexical-scope occurrence checking via
    `_iter_immediate_scope_nodes`, closing a nested-def/async-def/lambda and
    lambda-parameter-shadowing bypass, plus lambda-parameter binding enumeration as defense in
    depth) applied to `backend/tests/test_authorization_route_migration_guard.py` only; no runtime
    authorization file changed.
[x] Deterministic reverification of the C6-corrected
    `backend/tests/test_authorization_route_migration_guard.py` (see "Post-C6 correction -
    deterministic reverification COMPLETE" above) is executed and passes (106/106 focused,
    371/371 full backend, Alembic sound, 65/65 targeted, secret scan PASS, `git diff --check`
    clean) - every prediction confirmed exactly.
[x] A fresh, read-only independent re-review of the C6 correction pass ran and returned its
    verdict: CORRECTION REQUIRED (C7) - see "C7 correction (dated 1 September 2026)" above. This
    satisfies "a fresh independent re-review ran and was recorded"; it does NOT satisfy "accepts
    the fully corrected package," which remains open below.
[x] C7 guard correction (P4-1 comprehension/generator implicit scopes - ListComp/SetComp/DictComp/
    GeneratorExp - missing from the C6 bounded immediate-lexical-scope model, closing a bypass where
    the real allowed statement was wrapped in a bare, never-consumed generator/comprehension whose
    body the C6 traversal still walked into) applied to
    `backend/tests/test_authorization_route_migration_guard.py` only; no runtime authorization file
    changed.
[x] Deterministic reverification of the C7-corrected
    `backend/tests/test_authorization_route_migration_guard.py` (see "Post-C7 correction -
    deterministic reverification COMPLETE" above) is executed and passes (99/99 guard file alone,
    117/117 focused authorization suite, 382/382 full backend regression, Alembic sound at
    `20260831_0030 (head)`, targeted lexical-scope subset 15/15 selected of 99, secret scan PASS,
    `git diff --check` clean).
[ ] A fresh, read-only independent re-review of the C7 correction pass accepts the fully corrected
    package; project owner directs commit/push per the integration gate (ADR-031).
```
