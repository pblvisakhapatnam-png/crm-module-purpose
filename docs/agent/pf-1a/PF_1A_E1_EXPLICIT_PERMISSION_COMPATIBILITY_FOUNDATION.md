# PF-1A-E1 - Explicit Permission Compatibility Foundation

## Status

**CLOSURE UPDATE, 2 SEPTEMBER 2026: THIS PACKAGE IS COMPLETE AND INTEGRATED.** A fresh, read-only
C7 independent review (the gate the paragraphs below describe as open) returned **VERDICT:
ACCEPTED, no blocking findings**. The package was committed as
`d0b54d34347d33cdbcff1b3622befb317e8a5b32`, merged via PR #11, and is integrated on `main` as
commit `10cc2e49c2bc57cd85374abc31cb23a602fcb641`. Full closure record:
`docs/continuity/PF_1A_E1_INTEGRATION_CLOSURE_2026-09-02.md`. The narrative below (C1 through the
completed C7 deterministic reverification) is preserved unedited as the accurate historical record
of how the package reached that point; read it as history, not current status.

**Correction to this status summary, recorded during independent review of the integration
closure package:** the sentence below stating that "all seven correction passes" were applied to
test tooling and documentation only is not accurate as a description of C1. C1 also made one
introspection-only metadata change to `backend/app/modules/authorization/dependencies.py` (adding
`required_permission_code` on the `require_permission(...)` closure so C1's baseline/route
inventory proof could read which permission a live route requests); it did not alter
`has_permission(...)` evaluation, permission grants, route access, or any reconfirmed compatibility
fact. See `docs/continuity/PF_1A_E1_C1_CORRECTION_HANDOFF.md` section 3. **C2 through C6, and the
C7 re-review below, were each scoped exactly as the sentence below describes** - only to
`backend/tests/test_authorization_route_migration_guard.py` and current-state documentation, never
to a runtime authorization file.

Implemented; independently reviewed seven times (C1, C2, C3, C4, C5, C6, and a fresh C7
re-review). C1's correction is detailed in
`docs/continuity/PF_1A_E1_C1_CORRECTION_HANDOFF.md`; C2 through the C7 re-review each applied
their correction passes to test tooling and documentation only.
The C3
correction (including its own follow-on test-helper correction) was deterministically
reverified and passing (50/50 focused, 315/315 full, 20/20 targeted, Alembic sound, secret
scan PASS). **The subsequent fresh independent re-review (C4) re-confirmed the runtime
candidate is unchanged and correct by every deterministic measure, but issued a further
CORRECTION REQUIRED verdict on the same static guard file**, finding two narrower bypasses
(a dynamic `require_roles` reference via `getattr`/`vars`/`__dict__`, and spoofable
`.role_codes` allow-shapes via helper-name rebinding, a wrong base object, or a fabricated
event identity). The C4 guard correction has been applied, and **deterministic C4
reverification is COMPLETE**, executed by a human operator with process-execution
access: focused authorization suite 62/62 passed (7.01s), full backend suite 327/327 passed
(1 known pre-existing `PytestCollectionWarning`, 239.07s), Alembic current/heads both
`20260831_0030 (head)`, targeted `-k "detects or rejects"` selection 29/29 passed (2.43s),
tracked-secret scan PASS (740/737/3, no findings). Runtime authorization behavior did not
change: 31 permissions, exactly 110 grants, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY`
still `FINANCE_USER`-only.

**A further fresh independent re-review (C5) then AGAIN re-confirmed the runtime candidate
is unchanged and correct by every deterministic measure it independently re-ran (31
permissions, six transitional roles, exactly 110 grants, exactly 76 protected routes,
exactly 11 authenticated-only exceptions, exactly 87 live `/api/` method/path entries,
exactly one expected permission dependency per protected route, no privilege
widening/narrowing, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still
`FINANCE_USER`-only, fail-closed unknown-permission/unmapped-role/empty-role/
inactive-permission/inactive-grant behavior, independent baseline fixture, Alembic
`20260831_0030 (head)`, focused suite 62/62, full backend 327/327, targeted guard 29/29,
tracked-secret scan clean, `git diff --check` clean), but issued a further CORRECTION
REQUIRED verdict on the same static guard file**, finding exactly two further, narrower
bypass CLASSES in the guard itself (not runtime behavior): (P2-1) the C4 dynamic-literal
detector for `require_roles` recognized only a single unbroken string constant, so
`vars(deps).get("require_roles")`, `deps.__dict__.get("require_roles")` and
`getattr(deps, "require_" + "roles")` all independently evaded it; and (P2-2) the two
`.role_codes` allow-shapes proved callee/base-object SPELLING and enclosing-function NAME,
but not that the tracked helper name genuinely resolves to an EXISTING expected import
(a star import such as `from fake_policy import *` could silently supply it), that a
pattern-match capture (`case has_permission:`) counts as shadowing, that the `.role_codes`
base object and (for accounts) the permission constant resolve to genuine production
provenance rather than an in-function rebinding (`user = other`,
`ACCOUNT_TAX_VERIFY = ACCOUNT_READ`, `response = fake_response`), or that the enclosing
target function is unique in the module (a decoy duplicate `def login(...)` or
`def _assert_tax_verification_permission(...)`). The C5 guard correction has been applied
- a bounded compile-time string evaluator plus `.get(...)` recognition for P2-1, and an
explicit provenance model (unique target function, exactly-one-statement-per-function,
base-object/permission-constant/helper-import provenance, star-import fail-closed,
match-pattern-capture binding enumeration) for P2-2 - taking the guard file from 44 to 66
test functions. **Deterministic C5 reverification has since been executed by a human
operator with `docker`/`python` process-execution access, and it is now COMPLETE**: focused
authorization suite 84 collected / 84 passed / 0 failed (5.20s, up from 62 by exactly the
22 new C5 synthetic tests); full backend regression 349 collected / 349 passed / 0 failed,
1 known pre-existing `PytestCollectionWarning`, 258.68s (up from 327 by exactly the same 22
tests); `alembic current`/`alembic heads` both `20260831_0030 (head)`, unchanged; targeted
`-k "detects or rejects"` selection against the 66-function guard file, 49 selected / 49
passed / 0 failed / 17 deselected (3.61s); tracked-secret scan PASS (740 proposed-tree
files, 737 scanned as text, 3 binary/oversized skipped, no findings); `git diff --check`
clean; HEAD unchanged at `3c69355858ab352e246a8775f8a463ca7c9c15be`. Runtime authorization
behavior did not change during this reverification: 31 permissions, exactly 110 grants, no
implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still `FINANCE_USER`-only.

**That fresh, read-only independent re-review of the C5 correction pass has since
happened (referred to as "C6") and again independently reconfirmed the runtime candidate
is unchanged and correct by every deterministic measure it independently re-ran (the same
31-permission/six-role/110-grant/76-route/11-exception/87-entry facts, no privilege
widening/narrowing, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still
`FINANCE_USER`-only, fail-closed behavior, independent baseline fixture, Alembic
`20260831_0030 (head)`, focused suite 84/84, full backend 349/349, targeted guard 49/49,
tracked-secret scan clean, `git diff --check` clean), but issued a further CORRECTION
REQUIRED verdict on the same static guard file**, finding exactly two further, narrower
bypass CLASSES in the guard itself (not runtime behavior): (P3-1) import provenance was
proved per `ImportFrom` STATEMENT rather than per individual `ast.alias`, so
`from mod import ACCOUNT_TAX_VERIFY, ACCOUNT_READ as ACCOUNT_TAX_VERIFY` (and the
equivalent for `has_permission`, `record_business_event`, `login_user`) passed the guard
because the statement contained a genuine alias somewhere, even though a second,
conflicting alias in the same statement overwrote the tracked name; and (P3-2) the
occurrence-uniqueness check walked the target function's FULL `ast.walk` subtree rather
than only its own immediate lexical scope, so the allowed statement moved inside a nested
`def`/`async def`/`lambda` under the real target function - or a lambda whose OWN
parameter shadows the real outer `user`/`response` - still counted as belonging to the
target function's own body. The C6 guard correction has been applied - a per-alias
`(import_node, alias)` provenance marker for P3-1, and a new bounded
`_iter_immediate_scope_nodes` lexical-scope traversal (plus lambda-parameter binding
enumeration as defense in depth) for P3-2 - taking the guard file from 66 to 88 test
functions. See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 14 for the
full finding and correction record. **Deterministic C6 reverification has since been
executed by a human operator with `docker`/`python` process-execution access, and it is
now COMPLETE**: guard file alone 88 collected / 88 passed (4.75s); focused authorization
suite 106 collected / 106 passed (5.13s, up from 84 by exactly the 22 new C6 synthetic
tests plus the guard file's own growth to 88); full backend regression 371 collected /
371 passed (1 known pre-existing `PytestCollectionWarning`, 260.24s, up from 349 by
exactly the same 22 tests); `alembic current`/`alembic heads` both `20260831_0030
(head)`, unchanged; targeted `-k "detects or rejects"` selection against the 88-function
guard file, 65 selected / 65 passed / 23 deselected (3.34s); tracked-secret scan PASS
(740 proposed-tree files, 737 scanned as text, 3 binary/oversized skipped, no findings);
`git diff --check` clean; HEAD unchanged at `3c69355858ab352e246a8775f8a463ca7c9c15be`.
Runtime authorization behavior did not change during this reverification: 31 permissions,
exactly 110 grants, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still
`FINANCE_USER`-only. See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 15
for the full itemized evidence.

**That fresh, read-only independent re-review of the C6 correction pass has since
happened (referred to as "C7") and AGAIN independently reconfirmed the runtime candidate
is unchanged and correct by every deterministic measure it independently re-ran (the same
31-permission/six-role/110-grant/76-route/11-exception/87-entry facts, no privilege
widening/narrowing, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still
`FINANCE_USER`-only, fail-closed behavior, independent baseline fixture, Alembic
`20260831_0030 (head)`, focused suite 106/106, full backend 371/371, targeted guard
65/65, tracked-secret scan clean, `git diff --check` clean), but issued a further
CORRECTION REQUIRED verdict on the same static guard file**, finding exactly one further,
narrower bypass CLASS in the guard itself (not runtime behavior): (P4-1) the C6 bounded
lexical-scope model (`_SCOPE_INTRODUCING_NODE_TYPES`, `_iter_immediate_scope_nodes`)
recognized a nested `def`/`async def`/`lambda`/`class` as a scope boundary but did not
recognize a Python comprehension or generator expression
(`ast.ListComp`/`ast.SetComp`/`ast.DictComp`/`ast.GeneratorExp`), even though each of
these executes its element/key/value expression in its own implicit nested scope exactly
like a nested `def`/`lambda` does. This was independently demonstrated by wrapping the
real `has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)` statement (and,
separately, the real `record_business_event(...)` audit call) inside a bare generator
expression assigned to a local and never consumed - `check = (has_permission(...) for
item in (1,))` - which is especially dangerous at the runtime level independent of this
guard: the generator object itself is truthy, so `if not check:` never raises and the
wrapped permission call is never even executed. The C7 guard correction has been
applied - all four comprehension/generator node types were added to
`_SCOPE_INTRODUCING_NODE_TYPES`, so `_iter_immediate_scope_nodes` yields the
comprehension/generator node itself (its presence stays visible) but never descends into
its body, the same treatment already given to a nested `def`/`async def`/`lambda`/`class`
- taking the guard file from 88 to 99 test functions. See
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 16 for the full finding and
correction record. **Deterministic C7 reverification has since been executed by a human
operator with `docker`/`python` process-execution access, and it is now COMPLETE**: guard
file alone 99 collected / 99 passed (4.45s, up from 88 by exactly the 11 new C7 synthetic
tests); focused authorization suite 117 collected / 117 passed (5.74s, the unchanged 18
non-guard tests plus the guard file's new total of 99); full backend regression 382
collected / 382 passed (1 known pre-existing `PytestCollectionWarning`, 344.93s, up from
371 by exactly the same 11 tests); `alembic current`/`alembic heads` both `20260831_0030
(head)`, unchanged; a targeted lexical-scope subset selected specifically for the P4-1
change (`-k "comprehension or generator or scope"`) 15 selected / 15 passed / 0 failed /
84 deselected out of 99 collected (3.34s) - a deliberate, more precisely targeted filter
than the "detects or rejects" convention used for C4-C6, not a rerun of that exact prior
filter string; tracked-secret scan PASS (740 proposed-tree files, 737 scanned as text, 3
binary/oversized skipped, no findings); `git diff --check` clean; HEAD unchanged at
`3c69355858ab352e246a8775f8a463ca7c9c15be`. Runtime authorization behavior did not change
during this reverification: 31 permissions, exactly 110 grants, no implicit ADMIN bypass,
`ACCOUNT_TAX_VERIFY` still `FINANCE_USER`-only. See
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 17 for the full itemized
evidence. **No authorization runtime file changed as part of the C7 correction** - only
`backend/tests/test_authorization_route_migration_guard.py` and current-state
documentation. The candidate remains entirely uncommitted. **The current gate is:
obtain a fresh, read-only independent re-review of this C7 correction pass**; deterministic
testing is no longer the open item, but the package is not yet integration-ready.

**This paragraph is preserved as historical record. As recorded in the closure update at the top
of this document, that gate has since been satisfied (VERDICT: ACCEPTED, no blocking findings),
the package was committed as `d0b54d34347d33cdbcff1b3622befb317e8a5b32`, and it is integrated on
`main` as commit `10cc2e49c2bc57cd85374abc31cb23a602fcb641`. It is no longer uncommitted and is no
longer awaiting review. See `docs/continuity/PF_1A_E1_INTEGRATION_CLOSURE_2026-09-02.md`.**

Package within
the PF-1A (Organisation Authority activation) delivery line,
itself gated behind PF-1F-HR-E1 per `docs/agent/pf-1f-hr/PF_1F_HR_DECISION_GATE.md`.
This package satisfies the narrow slice of that gate that does **not** depend on
canonical HR/business-authority data: it introduces the ORA-owned explicit
application-permission layer and migrates existing backend route authorization from
direct application-role knowledge to it, while preserving the exact current effective
access matrix.

The independent C2 review found runtime authorization behavior compatible and sound (no
privilege widening/narrowing, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still
FINANCE_USER-only, the full 31x6 matrix and 76-route/11-ungated-exception inventory
still match the baseline) and issued a CORRECTION REQUIRED verdict on two items scoped
entirely to test tooling and documentation, not runtime code: the static route-migration
guard tests were bypassable by three synthetic evasions the guard did not anticipate
(P2), and this document plus `docs/continuity/NEXT_STEPS.md` still described pre-C1
guard mechanics (P3). The C2 correction was subsequently executed and deterministically
reverified: focused PF-1A-E1 authorization suite 37 passed, full backend suite 302
passed, `alembic current`/`alembic heads` both `20260831_0030 (head)`, targeted
"detects or rejects" selection 11 passed, tracked-secret scan PASS. **A later
independent re-review (C3) then re-confirmed the runtime candidate is unchanged and
correct by every deterministic measure** (exactly 76 protected baseline routes, exactly
11 authenticated-only exceptions, 31 permissions, exactly 110 grants, no privilege
widening/narrowing, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still
FINANCE_USER-only, fail-closed unknown-permission/unmapped-role/inactive-permission/
inactive-grant behavior, sound migration, no HR/business-authority/approval/delegation/
config-publication scope creep) but issued a further CORRECTION REQUIRED verdict on the
same static guard file: three additional, narrower static-analysis bypasses were found
(a route-migration guard that inspected only the top-level FastAPI dependency list and
missed a nested permission dependency; two `.role_codes` exceptions that matched a
broader shape than the literal real production statement; and a `require_roles`
call-only detector that a local rebinding such as `rr = require_roles` could evade).
See `docs/continuity/PF_1A_E1_C2_CORRECTION_HANDOFF.md` for the C2 finding/correction
record and `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` for the C3 finding and
correction record. **No authorization runtime file has changed as part of either the C2
or the C3 correction** - only `backend/tests/test_authorization_route_migration_guard.py`
and current-state documentation.

**This is a compatibility/migration foundation, not the complete Organisation
Authority implementation.** It is not an approval engine and it does not resolve any
business authority (`CREDIT_ASSESSOR`, `CREDIT_APPROVER`, or any future ORA authority
code). See "Explicit deferments" below.

## Objective

Replace every backend route-level `require_roles(*SOME_ROLES)` guard - a route-local
tuple of application role codes - with `require_permission(PERMISSION_CODE)`, an
explicit, named application-permission code resolved against a durable, ORA-owned
role-to-permission compatibility mapping. Ordinary business route code should ask
"does this caller hold permission X?", not "does this caller hold role A, B or C?".

## Boundary

In scope:

- A new `authorization` backend module (`backend/app/modules/authorization/`) owning
  the permission catalogue, the compatibility mapping and the `require_permission(...)`
  authorization dependency.
- A durable persistence layer (`authz_permission`, `authz_role_permission`) and a
  single Alembic migration that seeds the exact current access matrix.
- Migration of every active `require_roles(...)` route guard (Accounts, Commercial
  Offers, Leads, Opportunities, Terms and Conditions, Work Orders, Events, and the
  identity module's own role-catalogue read) to `require_permission(...)`.
- Deterministic tests proving the migration preserved the exact pre-existing access
  matrix, with no implicit ADMIN bypass.

Out of scope (see "Explicit deferments"):

- Canonical HR/person/position/business-authority resolution.
- The PF-1A four-concept business-authority configuration model (Role Catalogue,
  Authority Catalogue, Role -> Authority Rules, Person/Position -> Role Assignments,
  Configuration Change/Publication, protected-meta-authority, self-escalation
  prevention, the Q-10 bootstrap decision).
- Any approval-consumer workflow (credit assessment/approval, Commercial Offer
  approval, T&C deviation approval, Work Order release approval, Customer Master
  approval).
- Any frontend refactor. The frontend's existing role-array-based UI hiding is
  unchanged; it was already documented as a usability aid, never a security boundary,
  and backend enforcement (now permission-based) remains authoritative.

## Why a route-omission risk exists, and how this package addresses it

A backend route module could, in principle, still authenticate a caller with
`get_current_user()` alone and never call an authorization dependency at all - that
would not be a *regression* introduced by this package (no such gap existed or was
created here), but it is exactly the shape of bug this migration could introduce if a
route were missed. `test_every_protected_api_route_requests_the_expected_baseline_permission` (see
"Tests" below) inspects the live FastAPI route table and fails if any `/api/...` route
outside a small, explicit, documented allowlist does not depend on
`require_permission(...)`.

## Authentication versus authorization

Unchanged: JWT -> `get_current_user()` -> `AppUser` -> `AuthUser`. Login
(`POST /api/auth/login`), token issuance and the authenticated self endpoint
(`GET /api/auth/me`) are untouched; they still authenticate only, with no
authorization decision attached. `role_codes` on `AuthUser` is still resolved fresh
from the database on every request (via `get_user_with_roles_by_public_id`), never
trusted from a stale JWT claim, exactly as before this package.

New seam:

```text
get_current_user()  (unchanged - identity module)
  -> require_permission(PERMISSION_CODE)  (new - authorization module)
    -> has_permission(db, current_user.role_codes, PERMISSION_CODE)
      -> authz_role_permission / authz_permission compatibility mapping
```

`app.modules.authorization` imports from `app.modules.identity.dependencies`
(`get_current_user`) for authentication. `app.modules.identity` does not import
anything from `app.modules.authorization` for its own authentication routes
(`/login`, `/me`); its one administrative route (`GET /api/auth/roles`) imports
`app.modules.authorization.dependencies.require_permission` for its own
authorization, which is a one-directional dependency (authorization -> identity for
authentication only), not a cycle.

`require_roles(...)` remains defined in `app.modules.identity.dependencies` (its
implementation is unchanged) for the narrow, documented transitional purpose ORA-001
anticipates, but no route module calls it any longer - see the static guard test.

## Module ownership

New module: `backend/app/modules/authorization/`

```text
contract.py       permission codes, descriptions, and the compatibility matrix
                  (single source of truth; also seeded verbatim into the migration)
models.py         AuthzPermission, AuthzRolePermission (SQLAlchemy)
repository.py     DB access: list_active_permission_codes_for_role_codes,
                  list_role_permission_matrix
service.py        has_permission(db, role_codes, permission_code) -> bool
dependencies.py   require_permission(permission_code) - the FastAPI authorization seam
```

This does not fold authorization into Identity, and it does not create a CRM-owned
Employee/Organisation/Position master, SharePoint schema or Plum integration. It owns
exactly the coarse-grained application-permission compatibility mapping described by
ORA-001's migration rule: "The implementation slice must inventory every current
hard-coded role tuple and map each action to an explicit permission."

## Explicit permission catalogue

Every code below corresponds 1:1 to a pre-existing `*_ROLES` route constant (or, for
Events/Identity, an inline role tuple) as it existed at baseline commit
`3c69355858ab352e246a8775f8a463ca7c9c15be`. None were invented by inventing a new
capability boundary; see `app.modules.authorization.contract` for the authoritative,
enforced copy of this table (drift between the code and this document is not possible
for the matrix itself, because the migration seeds from a value copied from the same
source at authoring time - the contract module additionally self-checks its own two
internal structures for drift at import time).

| Permission code | Capability | Roles granted |
| --- | --- | --- |
| `ACCOUNT_CREATE` | Create an Account, Account Contact or Account Address | ADMIN, SALES_USER, SALES_MANAGER |
| `ACCOUNT_READ` | View Accounts and subordinate detail | ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER, OPERATIONS_USER, MANAGEMENT_READ_ONLY |
| `ACCOUNT_CLASSIFICATION_MANAGE` | Update Account ownership/classification | ADMIN, SALES_USER, SALES_MANAGER |
| `ACCOUNT_TAX_CAPTURE` | Capture/update PAN/GST tax-profile and GSTINs | ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER |
| `ACCOUNT_TAX_VERIFY` | Set a PAN/GST verification state to VERIFIED / REJECTED_INCORRECT | FINANCE_USER only |
| `ACCOUNT_DOCUMENT_CAPTURE` | Record Account document metadata | ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER |
| `COMMERCIAL_OFFER_CREATE` | Create a Commercial Offer (including related offers) | ADMIN, SALES_USER, SALES_MANAGER |
| `COMMERCIAL_OFFER_READ` | View Commercial Offers and subordinate views | ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER, OPERATIONS_USER, MANAGEMENT_READ_ONLY |
| `COMMERCIAL_OFFER_UPDATE` | Update header / mark submitted | ADMIN, SALES_USER, SALES_MANAGER |
| `COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE` | Add pricing evidence / select basis rate | ADMIN, SALES_USER, SALES_MANAGER, OPERATIONS_USER |
| `COMMERCIAL_OFFER_LINE_WRITE` | Add/update a Commercial Offer line | ADMIN, SALES_USER, SALES_MANAGER |
| `COMMERCIAL_OFFER_TC_CLAUSE_WRITE` | Attach/remove header T&C clauses | ADMIN, SALES_USER, SALES_MANAGER |
| `COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE` | Record submission evidence | ADMIN, SALES_USER, SALES_MANAGER |
| `COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE` | Record a manual credit/exposure review | ADMIN, SALES_USER, SALES_MANAGER |
| `COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE` | Record a customer response / award outcome | ADMIN, SALES_USER, SALES_MANAGER |
| `COMMERCIAL_OFFER_REVISION_WRITE` | Open/resubmit/cancel a revision | ADMIN, SALES_USER, SALES_MANAGER |
| `LEAD_CREATE` | Create a Lead | ADMIN, SALES_USER, SALES_MANAGER |
| `LEAD_READ` | View Leads and activities | ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER, OPERATIONS_USER, MANAGEMENT_READ_ONLY |
| `LEAD_UPDATE` | Update early Lead details | ADMIN, SALES_USER, SALES_MANAGER |
| `LEAD_QUALIFICATION_DECIDE` | Record a qualification/closure decision | ADMIN, SALES_USER, SALES_MANAGER |
| `LEAD_CONVERT` | Convert a qualified Lead | ADMIN, SALES_USER, SALES_MANAGER |
| `LEAD_ACTIVITY_CREATE` | Record a Lead activity/follow-up | ADMIN, SALES_USER, SALES_MANAGER |
| `OPPORTUNITY_CREATE` | Create an Opportunity | ADMIN, SALES_USER, SALES_MANAGER |
| `OPPORTUNITY_READ` | View Opportunities | ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER, OPERATIONS_USER, MANAGEMENT_READ_ONLY |
| `OPPORTUNITY_UPDATE` | Update an Opportunity | ADMIN, SALES_USER, SALES_MANAGER |
| `OPPORTUNITY_ACCOUNT_REPAIR` | Repair a missing Account link | ADMIN, SALES_USER, SALES_MANAGER |
| `TC_CLAUSE_READ` | View the T&C clause library | ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER, OPERATIONS_USER, MANAGEMENT_READ_ONLY |
| `WORK_ORDER_CREATE` | Create a Work Order shell / create-update Amendment | ADMIN, SALES_USER, SALES_MANAGER, OPERATIONS_USER |
| `WORK_ORDER_READ` | View Work Orders, lines, related offers, amendments | ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER, OPERATIONS_USER, MANAGEMENT_READ_ONLY |
| `EVENTS_READ` | View recent business events | ADMIN, MANAGEMENT_READ_ONLY only |
| `IDENTITY_ROLE_CATALOG_READ` | View the application role catalogue | ADMIN only |

Two permissions above are the deliberate proof that ADMIN is not an implicit
universal grantee: `ACCOUNT_TAX_VERIFY` excludes ADMIN (only FINANCE_USER), and
`EVENTS_READ` / `IDENTITY_ROLE_CATALOG_READ` exclude every other role including every
Sales/Finance/Operations peer ADMIN usually shares access with.

## Consolidation approach (why this is 31 codes, not fewer or far more)

Rather than re-deriving new capability boundaries (which would risk quietly merging
two endpoints that happen to share today's role tuple but are not really "the same
capability"), each pre-existing `*_ROLES` route constant became exactly one permission
code. Constants that were themselves plain Python aliases of another constant (for
example `COMMERCIAL_OFFER_LINE_WRITE_ROLES = COMMERCIAL_OFFER_UPDATE_ROLES`) still
became their own separate permission code, because the original code already
distinguished them as separate named concepts even though their current *value*
coincided; collapsing them now would be a new judgement call this package should not
make silently. This keeps the mapping traceable 1:1 back to the pre-existing guard
inventory rather than introducing a new, reviewer-unverifiable abstraction.

## Persistence / migration

- Alembic revision `20260831_0030` (`down_revision = "20260713_0029"`, the actual
  current head verified from the versions directory - not merely inferred from
  filenames).
- New tables: `authz_permission` (permission_code unique, description, is_active) and
  `authz_role_permission` (role_code FK -> `role.role_code`, permission_id FK ->
  `authz_permission.id`, unique on the pair, is_active).
- The migration seeds both tables from a **hardcoded, self-contained** copy of the
  compatibility matrix (not an import of `app.modules.authorization.contract`), for
  the same reason `20260629_0002_auth_seed_users.py` embeds its own seed data
  directly: a migration is a frozen historical snapshot and must not silently change
  meaning if the live contract module is edited later.
- No existing table, column, index or constraint is altered. `role.role_code`
  (already `UNIQUE`) is the FK target; no new column is added to `role` or `app_user`.
- The migration seeds exactly **110** `authz_role_permission` grant rows: the sum, across
  all 31 permission codes, of the number of roles each is granted to (18 permissions at
  3 roles = 54, 6 permissions at 6 roles = 36, 4 permissions at 4 roles = 16, 1
  permission at 2 roles = 2, 2 permissions at 1 role = 2; 54+36+16+2+2 = 110). This was
  independently recomputed during the C2 correction pass directly from
  `PERMISSION_SEED` in the migration and cross-checked against
  `BASELINE_PERMISSION_ROLE_MATRIX` in `backend/tests/fixtures/
  pf_1a_e1_baseline_authorization.py`, and the two agree. An earlier prose figure of 111
  grants, recorded in `docs/continuity/PF_1A_E1_C1_CORRECTION_HANDOFF.md`, does not match
  either source and is superseded by this recomputation; that earlier document is
  preserved unedited as historical record (see the C2 correction handoff for the full
  reconciliation).

## Route migration inventory

| Module | Guards migrated | Notes |
| --- | --- | --- |
| `accounts/routes.py` | 14 `require_roles(...)` call sites -> 5 permissions, plus 1 embedded (non-Depends) role check | The PAN/GST verification-state check (`_assert_tax_verification_permission`) was not a route dependency; it is a conditional in-body check gated on the *value* of a request field. It now calls `has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)` instead of comparing against a literal role tuple. |
| `commercial_offers/routes.py` | 30 call sites -> 10 permissions | |
| `leads/routes.py` | 8 call sites -> 6 permissions | |
| `opportunities/routes.py` | 5 call sites -> 4 permissions | |
| `terms_and_conditions/routes.py` | 2 call sites -> 1 permission | |
| `work_orders/routes.py` | 15 call sites -> 2 permissions | |
| `events/routes.py` | 1 call site -> 1 permission | |
| `identity/routes.py` | 1 call site (`GET /api/auth/roles`) -> 1 permission | `POST /api/auth/login` and `GET /api/auth/me` are untouched: pure authentication, never role-gated. |

Modules deliberately **not** touched, because they were never `require_roles(...)`
guarded (authenticated-only, no role distinction to preserve or replace):
`documents/routes.py` (`require_current_user`, a bespoke "any authenticated user"
dependency) and `workflow/routes.py` (`get_current_user` directly). Migrating these to
a permission would not preserve an existing policy - it would invent a new one - so
they are out of this package's compatibility-preservation scope.

`business_party/routes.py`, `activities/routes.py`, `addresses/routes.py` and
`contacts/routes.py` contain no `APIRouter` instantiation (confirmed by inspection);
they are dead stub files, not mounted in `app.main`, and were correspondingly excluded
from the inventory.

## Tests

`backend/tests/test_authorization_compatibility_matrix.py`:

- Full 31 x 6 equivalence check (permission code x known role) between the seeded
  database and `ROLE_PERMISSION_COMPATIBILITY_MATRIX` - the central deterministic
  proof this package exists to provide.
- The inverse check: the database grants no permission to a role the contract does
  not list.
- ADMIN-is-not-universal proof (`ACCOUNT_TAX_VERIFY`, `EVENTS_READ`,
  `IDENTITY_ROLE_CATALOG_READ`).
- Narrower-permission-does-not-imply-broader-permission proof
  (`ACCOUNT_TAX_CAPTURE` vs `ACCOUNT_TAX_VERIFY` for SALES_USER).
- Unknown role code / empty role list -> always denies.
- Unknown permission code -> raises `UnknownPermissionCodeError` (fails loudly, never
  silently allows or denies).
- `require_permission(...)` rejects an unregistered code at construction time.
- Every seeded role code is one of the six known transitional roles.

`backend/tests/test_authorization_repository.py`: focused repository-layer tests
(multi-role union, empty input, unrecognized role codes mixed with real ones, every
role appears in the full matrix).

`backend/tests/test_authorization_route_migration_guard.py`: three static guards, now on
their seventh rewrite (99 test functions: 9 original, +10 under C2, +13 under C3, +12
under C4, +22 under C5, +22 under C6, +11 under C7 - see
`docs/continuity/PF_1A_E1_C2_CORRECTION_HANDOFF.md` and
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` sections 10, 12, 14 and 16) -

1. **No route module may reference `require_roles`, under any name, in any executable
   position - not only a call.** AST-based and fails closed at the reference level: it
   rejects the `ImportFrom` statement itself (regardless of alias, even if never used
   again), any bare `Name` load of `require_roles` or a tracked alias of it, and any
   `Attribute` access whose final `.attr` is literally `require_roles` regardless of the
   module/alias used to reach it. (Pre-C2, this guard was a plain regex on the literal
   substring `require_roles(`, which an aliased import would have bypassed. Pre-C3, the
   AST version only inspected an actual `Call`, so a local rebinding such as
   `rr = require_roles` or `rr = deps.require_roles` passed the guard entirely as long as
   the eventual call used only the rebound name; the reference-level rewrite closes this
   because the reference to the ORIGINAL name/attribute is itself flagged at the
   assignment, before any call. Pre-C4, a dynamic lookup - `getattr(x, "require_roles")`,
   `vars(x)["require_roles"]`, `x.__dict__["require_roles"]` - produced neither a `Name`
   load nor a matching `Attribute` node, so it passed undetected; a new
   `_find_dynamic_literal_attribute_accesses` helper now recognizes all three literal
   idioms and is appended to this guard's findings. Pre-C5, that helper recognized only a
   single unbroken string constant and only the subscript form of the `vars(x)`/
   `x.__dict__` idiom, so `vars(x).get("require_roles")`, `x.__dict__.get("require_roles")`
   and `getattr(x, "require_" + "roles")` all independently evaded it; a bounded
   compile-time string evaluator (`_eval_compile_time_string` - a plain string constant, or
   an `Add` `BinOp`/`JoinedStr` whose parts are themselves compile-time strings, never a
   variable/call/method) plus `.get(...)` recognition against `vars(...)`/`.__dict__` now
   close all three.)
2. **Every protected route requests exactly the expected permission code, across its
   COMPLETE dependency graph.** Every FastAPI route under `/api/` not on the small, exact
   (not prefix-wide) baseline-derived "authenticated-only" allowlist (11 exact routes)
   must depend on `require_permission(...)`; a baseline-protected route (76 exact routes,
   from the independently baseline-derived `tests/fixtures/pf_1a_e1_baseline_authorization.py`
   snapshot) must carry **exactly one** such dependency anywhere in its full recursive
   FastAPI dependency graph, requesting exactly the permission the baseline inventory
   expects. The permission a route requests is read from the explicit
   `required_permission_code` metadata `require_permission(...)` attaches to its
   returned closure (C1-01), never from `__qualname__` inference. A minimum route-count
   assertion (`>= 70`) guards against the allowlist quietly growing wide enough to make
   the per-route check vacuous. (Pre-C2, the helper collecting a route's permission
   dependency returned only the *first* one found, so a route carrying the expected
   permission plus a second, undocumented permission dependency would silently pass.
   Pre-C3, the corrected helper still inspected only the route's top-level
   `dependant.dependencies` list, so a permission dependency nested one level inside
   another dependency's own signature was invisible; the C3 rewrite recursively walks the
   complete dependency graph, with cycle/identity-revisit protection so a malformed or
   cyclic graph cannot recurse forever or be double-counted.)
3. **No route module may reintroduce direct application-role authorization logic.**
   Fail-closed, not pattern-enumerated: every `.role_codes` attribute access anywhere in
   a route module is treated as an offense unless it matches one of exactly two
   documented, EXACT, structurally-constrained shapes, each pinned to the literal real
   production statement - not merely a file-scoped pattern match. `accounts/routes.py`'s
   exception matches only a bare-name (never qualified) `has_permission(db, user.role_codes,
   ACCOUNT_TAX_VERIFY)` call, with exactly that argument shape, positionally, inside
   exactly `_assert_tax_verification_permission(...)`. `identity/routes.py`'s exception
   matches only `.role_codes` as the `"role_codes"` entry of a dict that is itself
   precisely the `event_payload=` keyword argument of a bare-name call to
   `record_business_event(...)`, inside exactly `login(...)`. A wrong permission
   constant, a qualified `policy.has_permission(...)` call, a `role_codes` dict used for
   something other than the audit-event payload, or the identical-looking shape inside a
   different function are all still rejected. (Pre-C3, both exceptions matched a broader
   shape: any `.role_codes` positional argument to anything ending in `.has_permission`
   in the accounts file, and any `role_codes` dict-value anywhere in the identity file,
   regardless of enclosing function, call target or permission requested.) Pre-C4, both
   shapes matched on callee-name spelling alone (a local rebinding such as
   `has_permission = policy.has_permission` still matched), neither pinned `.role_codes`
   to its real base object (`user`, `response.user` - so `other.role_codes` still
   matched), and the identity shape never checked the event identity (a fabricated
   `event_name=` carrying the same payload still matched); a new bounded binding-site scan
   (`_name_is_shadowed`) plus explicit base-object and `event_name="UserLoginSucceeded"`
   checks now close all three, and the same dynamic-lookup helper used for guard 1 closes
   a `getattr(user, "role_codes")` equivalent, applied unconditionally since no legitimate
   production code accesses `role_codes` dynamically. A separate,
   unrelated check still rejects a reintroduced
   route-local `*_ROLES` tuple constant. (Pre-C2, this guard enumerated specific
   forbidden shapes - a comparison, a set operation, a set-method call - and was shown to
   miss a local alias assignment followed by a membership test, `.role_codes` passed to
   an arbitrary helper function, and `.role_codes` used as a comprehension/generator
   iterable, because none of those three is a Compare, BinOp or set-method Call at the
   point `.role_codes` itself appears.) Pre-C5, the C4 `_name_is_shadowed(...)` check
   rejected an explicit conflicting binding but never required the tracked helper name to
   genuinely resolve to an EXISTING expected import, so a module relying on
   `from fake_policy import *` (or `from fake_events import *`) to silently supply
   `has_permission`/`record_business_event` passed undetected; `_iter_binding_names` did
   not enumerate match-statement capture patterns at all, so `case has_permission:`
   likewise evaded the shadow check; and the base object (`user`, `response`) and, for
   accounts, the permission constant (`ACCOUNT_TAX_VERIFY`) were pinned only by NAME
   SPELLING, so an in-function rebinding (`user = other`,
   `ACCOUNT_TAX_VERIFY = ACCOUNT_READ`, `response = fake_response`) or a decoy duplicate
   target function (a second `def login(...)` or
   `def _assert_tax_verification_permission(...)` anywhere in the module) still matched.
   C5 replaces the enclosing-function-name/shadow checks with an explicit provenance
   model: the call/dict shape match is now a separate, reusable predicate
   (`_accounts_role_codes_shape_matches` / `_identity_role_codes_shape_matches`); the
   target function must be the UNIQUE `FunctionDef`/`AsyncFunctionDef` with the expected
   name and sync/async-ness (`_unique_target_function`); the shape-matching statement must
   occur EXACTLY ONCE inside that function; the base object's provenance is proved
   trustworthy (the real parameter position for `user`, or the one real
   `response = login_user(...)` assignment for `response`, with no other binding of that
   name anywhere in the function, and - defense in depth - `login_user` itself must also
   be the genuine imported production login service function, not a same-named local
   decoy); and every tracked helper/constant name must resolve to EXACTLY ONE genuine
   expected `ImportFrom` binding, with the whole module failing closed if it contains ANY
   star import at all (`_helper_provenance_is_trustworthy`). `_iter_binding_names` is
   extended to enumerate `ast.MatchAs`/`ast.MatchStar`/`ast.MatchMapping` binding sites.)
   Pre-C6, that "EXACTLY ONE genuine expected `ImportFrom` binding" check was proved per
   `ImportFrom` STATEMENT rather than per individual `ast.alias`, so
   `from mod import ACCOUNT_TAX_VERIFY, ACCOUNT_READ as ACCOUNT_TAX_VERIFY` (and the
   equivalent same-statement alias collision for `has_permission`, `record_business_event`,
   `login_user`, in either alias order) still passed, because the statement contained a
   genuine alias somewhere even though its second alias overwrote the tracked local name
   with a different symbol; `_iter_binding_names` now yields a `(import_node, alias)`
   marker identifying the SPECIFIC alias that produced each binding occurrence, and
   `_is_expected_import_binding`/`_count_expected_import_bindings` check that specific
   alias rather than "any alias in the same statement." Separately pre-C6, the
   occurrence-uniqueness check walked the target function's FULL `ast.walk` subtree, which
   descends through every nested lexical scope, so the allowed statement moved inside a
   nested `def`/`async def`/`lambda` under the real target function - or a lambda whose OWN
   parameter shadows the real outer `user`/`response` while the base-object name spelling
   still matched textually - still counted as belonging to the target function's own body;
   a new bounded `_iter_immediate_scope_nodes` traversal now collects occurrences only from
   the target function's own immediate lexical scope (a nested scope-introducing node is
   itself yielded, so its presence is still visible, but its contents are never descended
   into), used by both `_is_allowed_accounts_role_codes_usage` /
   `_is_allowed_identity_role_codes_usage` and `_find_legitimate_response_assignment`, and
   `_iter_binding_names` is further extended to enumerate `ast.Lambda` parameters as
   binding sites (defense in depth alongside the scope restriction). See
   `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 14 for the full C6 record.
   Pre-C7, the same immediate-scope traversal (`_SCOPE_INTRODUCING_NODE_TYPES`) treated a
   nested `def`/`async def`/`lambda`/`class` as a scope boundary but not a Python
   comprehension or generator expression, even though each executes its element/key/value
   expression in its own implicit nested scope exactly the same way; a bare generator
   expression wrapping the real `has_permission(...)` call (or the real
   `record_business_event(...)` audit call) and assigned to a local that was never
   consumed - `check = (has_permission(...) for item in (1,))` - therefore still counted
   as belonging to the target function's own immediate body, even though at runtime the
   generator object itself is truthy and the wrapped call is never executed at all. C7
   adds `ast.ListComp`, `ast.SetComp`, `ast.DictComp` and `ast.GeneratorExp` to
   `_SCOPE_INTRODUCING_NODE_TYPES`, closing the gap with the same yield-but-do-not-descend
   treatment already used for a nested function/lambda/class; comprehension/generator
   TARGET names (`for item in ...`) were already enumerated as binding sites via
   `ast.comprehension` before this correction and needed no change. See
   `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 16 for the full C7 record.

All three guards carry synthetic regression tests proving both the corrected detection
(each of the three evasions above) and that the two genuine, documented usages remain
permitted - and, for guard 3, that the same two shapes are rejected when the identical
source appears outside their own file, proving the exceptions are file-scoped rather
than a global pattern allowlist. Route source is read with `utf-8-sig` throughout
(several route modules carry a UTF-8 BOM that a plain `utf-8` read/`ast.parse` would
reject).

Pre-existing tests are the HTTP-level regression proof that this migration changed no
externally observable behavior: `test_auth.py` (`/api/auth/roles` 403 for `sales1`,
200 for `admin1`), `test_events.py` (`/api/events/recent` 403 for `sales1`, 200 for
`readonly1`), and `test_accounts_api.py`
(`test_sales_user_cannot_set_verified_tax_states`,
`test_finance_user_can_record_account_document_but_operations_cannot`) were read in
full and traced against the new permission mapping; none required modification.

## Verification executed

Deterministic verification could not be executed in the *initial* implementation
session (Docker Desktop's daemon was not running and `docker`/`python` process
execution required interactive approval unavailable in that session); see
`docs/continuity/PF_1A_E1_IMPLEMENTATION_HANDOFF.md` section 9 for that historical
record. **This was closed after the C1 correction pass**: the full required sequence
was actually executed against the corrected candidate and passed - focused PF-1A-E1
authorization suite 27 passed in 4.59s, full backend suite 292 passed / 0 failed (1
pre-existing `PytestCollectionWarning`) in 240.02s, `alembic current`/`alembic heads`
both `20260831_0030 (head)`, repository scripts 58 passed, tracked-secret validation
PASS. Manual acceptance checks (allowed action as `finance1`, denied action as
`admin1`) were also executed and recorded PASS. See
`docs/agent/acceptance/pf-1a-e1-explicit-permission-compatibility-foundation-acceptance.md`
("Post-C1 deterministic reverification") for the full, itemized evidence and exact
counts, and `docs/continuity/PF_1A_E1_C1_CORRECTION_HANDOFF.md` for the C1 correction
record.

**The C2 correction pass was subsequently executed and deterministically reverified.**
`docs/continuity/PF_1A_E1_C2_CORRECTION_HANDOFF.md` originally recorded that
`backend/tests/test_authorization_route_migration_guard.py` had been rewritten (9 test
functions -> 19) but not yet run, because process execution (`docker`/`python`) was
unavailable in that non-interactive session; that addendum's own instructions were then
actually carried out and the results were: focused PF-1A-E1 authorization suite 37
passed, full backend suite 302 passed, `alembic current`/`alembic heads` both
`20260831_0030 (head)`, targeted "detects or rejects" selection 11 passed, tracked-secret
scan PASS. See the dated post-reverification addendum in
`docs/continuity/PF_1A_E1_C2_CORRECTION_HANDOFF.md` for the exact commands and full
output.

**A later independent re-review (C3) then re-confirmed every one of those runtime
results independently** (same 76/11/31/110 counts, same 37/302 pass counts, no privilege
widening/narrowing, no implicit ADMIN bypass) but found three further static-analysis
bypasses in the same guard file - unrelated to runtime behavior - and issued a further
CORRECTION REQUIRED verdict. That C3 correction is recorded in
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md`. Deterministic reverification was not
executed by the non-interactive session that performed the C3 correction itself (process
execution was again unavailable there); the guard rewrite was independently confirmed
sound only by careful manual/static AST tracing against the real production source at
that time.

**Deterministic reverification of the C3-corrected guard file has since been executed by
a human operator with process-execution access, and it is now COMPLETE.** The first run
of the focused suite reproduced a genuine, previously untested defect in the C3 rewrite
itself: `test_route_required_permission_codes_handles_a_cyclic_dependency_graph_without_
infinite_recursion` failed (50 collected, 49 passed, 1 failed), because
`_iter_all_dependencies` yielded a cyclic child before checking whether it was already an
ancestor of the current recursion path. This was corrected narrowly - the helper now
tracks an immutable per-path ancestor-identity set and checks a child against it before
yielding, rather than checking only after the fact - documented in full in
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 8. The corrected file was
then rerun and every subsequent command passed:

- focused authorization suite: **50 collected, 50 passed, 0 failed, 5.27s**;
- full backend suite: **315 collected, 315 passed, 0 failed, 1 known pre-existing
  `PytestCollectionWarning`, 242.28s** (315 = the prior Post-C2 figure of 302 plus the 13
  C3 guard tests, confirming no other file changed);
- `alembic current` / `alembic heads`: both `20260831_0030 (head)`, unchanged;
- targeted `-k "detects or rejects"` selection: **32 collected, 20 selected, 20 passed, 0
  failed, 2.35s**;
- tracked-secret scan: **PASS**, 740 proposed-tree files evaluated, 737 scanned as text, 3
  binary/oversized skipped, no findings.

Runtime authorization behavior did not change during the C3 correction, the section-8
test-helper fix, or this reverification: 31 permissions, exactly 110 grants, no implicit
ADMIN bypass, and `ACCOUNT_TAX_VERIFY` remains `FINANCE_USER`-only throughout. The
candidate remains entirely **uncommitted**. Full exact commands and output are recorded
in `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 9.

**A fresh independent re-review then ran against that section-9 evidence and issued a
further CORRECTION REQUIRED verdict (C4).** It independently reconfirmed the runtime
candidate unchanged and correct by every deterministic measure the C3 review already
confirmed (31 permissions, six transitional roles, exactly 110 grants, exactly 76
protected routes, exactly 11 authenticated-only exceptions, no privilege widening or
narrowing, no implicit `ADMIN` bypass, `ACCOUNT_TAX_VERIFY` still `FINANCE_USER`-only,
fail-closed unknown/unmapped/inactive handling, Alembic current/head =
`20260831_0030 (head)`, no PF-1A-E2/E3 scope creep, and the section-9 50/50, 20/20 and
315/315 pass counts) and again instructed: do not change runtime authorization behavior.
It found two further, narrower bypasses in the same guard file, both unrelated to runtime
behavior:

- **P2-1**: `_scan_for_require_roles` (guard 1) caught every direct/aliased/qualified
  reference and local rebinding of `require_roles`, but a dynamic lookup -
  `getattr(identity_dependencies, "require_roles")` - produced neither a `Name` load nor
  an `Attribute` node the guard inspected, and so passed undetected.
- **P2-2**: the two `.role_codes` allow-shapes (guard 3) matched on call/dict structure
  and callee-name spelling, but never proved the callee name (`has_permission`,
  `record_business_event`) was still the genuine, unshadowed import - a local rebinding
  such as `has_permission = policy.has_permission` still matched the shape - and never
  pinned the `.role_codes` base object to the real production variable (`user`,
  `response.user`) or the identity allow-shape's event to the real
  `event_name="UserLoginSucceeded"`, so `other.role_codes` and a fabricated event
  identity carrying the identical payload shape both passed undetected. A dynamic
  `getattr(user, "role_codes")` equivalent also produced no `.role_codes` `Attribute`
  node at all, making it invisible to the guard regardless of module.

**The C4 guard correction has been applied**, entirely inside
`backend/tests/test_authorization_route_migration_guard.py`: a new
`_find_dynamic_literal_attribute_accesses(tree, banned_attr)` helper closes P2-1 (reused
for the `.role_codes` dynamic-access half of P2-2 too), and a new bounded binding-site scan
(`_iter_binding_names` / `_name_is_shadowed`) plus explicit base-object and event-identity
checks close the rest of P2-2. Twelve new synthetic tests were added (4 for guard 1, 8 for
guard 3); no existing assertion was weakened. Full detail, the exact correction, and the
full synthetic-test list are recorded in `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md`
section 10.

Runtime authorization behavior did not change during the C4 correction: no
`backend/app/modules/authorization/**` file, `routes.py` file, or
`backend/app/models_metadata.py` was touched. When the C4 correction itself was written, this
session's process-execution access was blocked identically to every prior pass (only
`python --version` succeeded), so at that time the C4 correction had been verified only by
manual/static AST tracing against the real production source, not by actually running pytest;
see section 10's "Verification status of this C4 correction" for that historical disclosure.

**Deterministic C4 reverification has since been executed by a human operator with
`docker`/`python` process-execution access, and it is now COMPLETE.** All results below are
from actual execution, not prediction or hand-tracing:

- focused authorization suite (`test_authorization_baseline_equivalence.py`,
  `test_authorization_compatibility_matrix.py`, `test_authorization_repository.py`,
  `test_authorization_route_migration_guard.py`): **62 collected, 62 passed, 0 failed,
  7.01s** (50 + 12 new C4 synthetic tests, exactly as predicted);
- full backend regression: **327 collected, 327 passed, 0 failed, 1 known pre-existing
  `PytestCollectionWarning`, 239.07s** (327 = the prior 315 plus the 12 new C4 guard tests);
- `alembic current` / `alembic heads`: both `20260831_0030 (head)`, unchanged;
- targeted `-k "detects or rejects"` selection: **44 collected, 29 selected, 29 passed, 0
  failed, 15 deselected, 2.43s**;
- tracked-secret scan: **PASS**, 740 proposed-tree files evaluated, 737 scanned as text, 3
  binary/oversized skipped, no findings.

Runtime authorization behavior did not change during this reverification either: 31
permissions remain, exactly 110 grants remain, there is no implicit ADMIN bypass, and
`ACCOUNT_TAX_VERIFY` remains `FINANCE_USER`-only. The candidate remains entirely
**uncommitted**. See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 11 for the
full itemized evidence.

**This paragraph is preserved as the accurate historical record of the gate as it stood
after C4 reverification, on 1 September 2026, before the fresh C5 re-review described
next; it is not the current gate.**

**A fresh independent re-review then ran against that C4 evidence and issued another
CORRECTION REQUIRED verdict (C5).** It independently re-reconfirmed the runtime candidate
unchanged and correct by every deterministic measure it independently re-ran (31
permissions, six transitional roles, exactly 110 grants, exactly 76 protected routes,
exactly 11 authenticated-only exceptions, exactly 87 live `/api/` method/path entries,
exactly one expected permission dependency per protected route, no privilege
widening/narrowing, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still
`FINANCE_USER`-only, fail-closed unknown-permission/unmapped-role/empty-role/
inactive-permission/inactive-grant behavior, independent baseline fixture, Alembic
`20260831_0030 (head)`, focused suite 62/62, full backend 327/327, targeted guard 29/29,
tracked-secret scan clean, `git diff --check` clean) and again instructed: do not change
runtime authorization behavior. It found exactly two further, narrower bypass CLASSES in
the same guard file, both unrelated to runtime behavior: **P2-1**, the C4 dynamic-literal
detector for `require_roles` recognized only a single unbroken string constant and only
the subscript form of `vars(x)`/`x.__dict__`, so `vars(deps).get("require_roles")`,
`deps.__dict__.get("require_roles")` and `getattr(deps, "require_" + "roles")` all
independently evaded it; and **P2-2**, the two `.role_codes` allow-shapes proved
callee/base-object spelling and enclosing-function name, but never proved the tracked
helper name genuinely resolves to an EXISTING expected import (a star import could supply
it undetected), never enumerated a pattern-match capture as a binding site, and pinned the
`.role_codes` base object and (for accounts) the permission constant only by name
spelling rather than genuine production provenance, so an in-function rebinding or a decoy
duplicate target function still matched. See
`docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 12 for the full finding and
correction record.

**The C5 guard correction has been applied**, entirely inside
`backend/tests/test_authorization_route_migration_guard.py`: a bounded compile-time string
evaluator (`_eval_compile_time_string` - a plain string constant, or an `Add`
`BinOp`/`JoinedStr` whose parts are themselves compile-time strings, never a
variable/call/method) plus `.get(...)` recognition against `vars(x)`/`x.__dict__` closes
P2-1 for both guard 1 and guard 3; `_iter_binding_names` is extended to enumerate
`ast.MatchAs`/`ast.MatchStar`/`ast.MatchMapping` binding sites; a new
`_helper_provenance_is_trustworthy(...)` supersedes the bare C4 `_name_is_shadowed(...)`
call, requiring EXACTLY ONE genuine expected import to exist for every tracked
helper/constant name and failing closed on any star import anywhere in the module; and the
two `.role_codes` allow-shape functions are restructured into a separate, reusable
shape-only predicate plus an explicit provenance model (`_unique_target_function`,
exactly-one-shape-matching-statement-per-function,
`_user_provenance_is_trustworthy`/`_response_provenance_is_trustworthy` for base-object
provenance, including a defense-in-depth check that `login_user` itself is the genuine
imported production function rather than a same-named local decoy). Twenty-two new
synthetic tests were added (6 for guard 1, 16 for guard 3), taking the guard file from 44
to 66 test functions; no existing assertion was weakened, relaxed, or removed - four
pre-existing "permits the real production shape" tests were updated to include the full
genuine production provenance the stronger C5 model now requires, which the real
production files always contain. **No authorization runtime file changed as part of the
C5 correction** - only `backend/tests/test_authorization_route_migration_guard.py` and
current-state documentation, the same scope every prior correction was scoped to.

**Deterministic C5 reverification has since been executed by a human operator with
`docker`/`python` process-execution access, and it is now COMPLETE.** All results below
are from actual execution, not prediction or hand-tracing:

- focused authorization suite (`test_authorization_baseline_equivalence.py`,
  `test_authorization_compatibility_matrix.py`, `test_authorization_repository.py`,
  `test_authorization_route_migration_guard.py`): **84 collected, 84 passed, 0 failed,
  5.20s** (62 + 22 new C5 synthetic tests, exactly as expected);
- full backend regression: **349 collected, 349 passed, 0 failed, 1 known pre-existing
  `PytestCollectionWarning`, 258.68s** (349 = the prior 327 plus the 22 new C5 guard
  tests);
- `alembic current` / `alembic heads`: both `20260831_0030 (head)`, unchanged;
- targeted `-k "detects or rejects"` selection against the 66-function guard file: **66
  collected, 49 selected, 49 passed, 0 failed, 17 deselected, 3.61s**;
- tracked-secret scan: **PASS**, 740 proposed-tree files evaluated, 737 scanned as text, 3
  binary/oversized skipped, no findings;
- `git diff --check`: clean, no output;
- repository state: `git status --short` shows only the expected uncommitted PF-1A-E1
  candidate files, nothing staged, HEAD unchanged at
  `3c69355858ab352e246a8775f8a463ca7c9c15be`.

Runtime authorization behavior did not change during this reverification: 31 permissions
remain, exactly 110 grants remain, there is no implicit ADMIN bypass, and
`ACCOUNT_TAX_VERIFY` remains `FINANCE_USER`-only. The candidate remains entirely
**uncommitted**. See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 13 for
the full itemized evidence.

**This paragraph is preserved as the accurate historical record of the gate as it stood
after C5 reverification, on 1 September 2026, before the fresh C6 re-review described
next; it is not the current gate.**

**A fresh independent re-review then ran against that C5 evidence and issued another
CORRECTION REQUIRED verdict (C6).** It independently re-reconfirmed the runtime candidate
unchanged and correct by every deterministic measure it independently re-ran (the same
31-permission/six-role/110-grant/76-route/11-exception/87-entry facts, no privilege
widening/narrowing, no implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still
`FINANCE_USER`-only, fail-closed unknown-permission/unmapped-role/empty-role/
inactive-permission/inactive-grant behavior, independent baseline fixture, Alembic
`20260831_0030 (head)`, focused suite 84/84, full backend 349/349, targeted guard 49/49,
tracked-secret scan clean, `git diff --check` clean) and again instructed: do not change
runtime authorization behavior. It found exactly two further, narrower bypass CLASSES in
the same guard file (guard 3 only - the `.role_codes` fail-closed checks - guard 1's
`require_roles` detection was not implicated this time), both unrelated to runtime
behavior:

- **P3-1**: the "EXACTLY ONE genuine expected `ImportFrom` binding" check
  (`_helper_provenance_is_trustworthy`) was proved per `ImportFrom` STATEMENT rather than
  per individual `ast.alias`, so a single statement carrying both a genuine alias and a
  conflicting one for the same tracked local name (`from mod import ACCOUNT_TAX_VERIFY,
  ACCOUNT_READ as ACCOUNT_TAX_VERIFY`, and the equivalent for `has_permission`,
  `record_business_event`, `login_user`, regardless of which alias came first) still
  passed, because the statement contained a genuine alias somewhere.
- **P3-2**: the occurrence-uniqueness check walked the target function's FULL `ast.walk`
  subtree, which descends through every nested lexical scope, so the allowed statement
  moved inside a nested `def`/`async def`/`lambda` under the real target function (for
  identity, both the `response = login_user(...)` assignment and the audit call moved
  together into one nested `def`) - or a lambda whose OWN parameter shadows the real outer
  `user`/`response` while the base-object name spelling still matched textually - still
  counted as belonging to the target function's own immediate body.

See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 14 for the full finding and
correction record.

**The C6 guard correction has been applied**, entirely inside
`backend/tests/test_authorization_route_migration_guard.py`: `_iter_binding_names` now
yields a `(import_node, alias)` marker for each `ImportFrom` binding, identifying the
SPECIFIC alias that produced each occurrence, and `_is_expected_import_binding` /
`_count_expected_import_bindings` check that specific alias rather than "any alias in the
same statement," closing P3-1; a new bounded `_iter_immediate_scope_nodes(func_node)`
traversal yields every node in a function's own body without crossing into a nested
`def`/`async def`/`lambda`/`class` (the scope-introducing node is itself yielded, so its
presence is still visible, but its contents are never descended into), and both
`_is_allowed_accounts_role_codes_usage` / `_is_allowed_identity_role_codes_usage` and
`_find_legitimate_response_assignment` now collect candidate occurrences through it instead
of `ast.walk`, closing P3-2; `_iter_binding_names` is further extended to enumerate
`ast.Lambda` parameters as binding sites (defense in depth alongside the scope
restriction, not the primary defense against it). Because the fail-closed `.role_codes`
visitor still visits every `.role_codes` access anywhere in the module regardless of scope
(a separate, unaffected full-tree `ast.NodeVisitor` traversal), a nested-scope occurrence
is never silently dropped from consideration - it is still visited, still fails the
immediate-scope occurrence check, and is still reported as an offense. Twenty-two new
synthetic tests were added (9 for P3-1, 13 for P3-2), taking the guard file from 66 to 88
test functions; no existing assertion was weakened, relaxed, or removed. **No
authorization runtime file changed as part of the C6 correction** - only
`backend/tests/test_authorization_route_migration_guard.py` and current-state
documentation, the same scope every prior correction was scoped to.

**Deterministic C6 reverification has since been executed by a human operator with
`docker`/`python` process-execution access, and it is now COMPLETE.** All results below
are from actual execution, not prediction or hand-tracing, and every one of the section-14
predictions is confirmed exactly:

- guard file alone: **88 collected, 88 passed, 0 failed, 4.75s** (66 + 22 new C6 synthetic
  tests, exactly as expected);
- focused authorization suite (`test_authorization_baseline_equivalence.py`,
  `test_authorization_compatibility_matrix.py`, `test_authorization_repository.py`,
  `test_authorization_route_migration_guard.py`): **106 collected, 106 passed, 0 failed,
  5.13s** (the three non-guard files' unchanged 18 tests plus the guard file's new total
  of 88, 18 + 88 = 106);
- full backend regression: **371 passed, 0 failed, 1 known pre-existing
  `PytestCollectionWarning`, 260.24s** (371 = the prior 349 plus the 22 new C6 guard
  tests);
- `alembic current` / `alembic heads`: both `20260831_0030 (head)`, unchanged;
- targeted `-k "detects or rejects"` selection against the 88-function guard file: **88
  total, 65 selected, 65 passed, 0 failed, 23 deselected, 3.34s**;
- tracked-secret scan: **PASS**, 740 proposed-tree files evaluated, 737 scanned as text, 3
  binary/oversized skipped, no findings;
- `git diff --check`: clean, no output;
- repository state: `git status --short` shows only the expected uncommitted PF-1A-E1
  candidate files, nothing staged, HEAD unchanged at
  `3c69355858ab352e246a8775f8a463ca7c9c15be`.

Runtime authorization behavior did not change during this reverification: 31 permissions
remain, exactly 110 grants remain, there is no implicit ADMIN bypass, and
`ACCOUNT_TAX_VERIFY` remains `FINANCE_USER`-only. The candidate remains entirely
**uncommitted**. See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 15 for
the full itemized evidence.

**A fresh, read-only independent re-review of the C6 correction pass then ran (referred
to as "C7") and AGAIN independently reconfirmed the runtime candidate is unchanged and
correct by every deterministic measure it independently re-ran** (31 permissions, six
transitional roles, exactly 110 grants, exactly 76 protected routes, exactly 11
authenticated-only exceptions, exactly 87 live `/api/` method/path entries, exactly one
expected permission dependency per protected route, no privilege widening/narrowing, no
implicit ADMIN bypass, `ACCOUNT_TAX_VERIFY` still `FINANCE_USER`-only, fail-closed
unknown-permission/unmapped-role/empty-role/inactive-permission/inactive-grant behavior,
independent baseline fixture, Alembic `20260831_0030 (head)`, focused suite 106/106, full
backend 371/371, targeted guard 65/65, tracked-secret scan clean, `git diff --check`
clean, C1-C6 protections all reconfirmed intact including per-import-alias provenance and
nested def/async def/lambda/class rejection with every lambda parameter form enumerated),
**but issued a further CORRECTION REQUIRED verdict on the same static guard file**,
finding exactly one further, narrower bypass CLASS in the guard itself (not runtime
behavior):

- **P4-1**: the C6 bounded lexical-scope model (`_SCOPE_INTRODUCING_NODE_TYPES`,
  `_iter_immediate_scope_nodes`) recognized a nested `def`/`async def`/`lambda`/`class` as
  a scope boundary but did not recognize a Python comprehension or generator expression
  (`ast.ListComp`/`ast.SetComp`/`ast.DictComp`/`ast.GeneratorExp`), even though each of
  these executes its element/key/value expression in its own implicit nested scope exactly
  the same way. Independently demonstrated by wrapping the real
  `has_permission(db, user.role_codes, ACCOUNT_TAX_VERIFY)` statement, and separately the
  real `record_business_event(...)` audit call, inside a bare generator expression
  assigned to a local and never consumed - `check = (has_permission(...) for item in
  (1,))`. This is especially dangerous at the runtime level, independent of the guard
  itself: the generator object is truthy, so `if not check:` never raises and the wrapped
  permission call is never even executed - a silent no-op that looks like an enforced
  check.

See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 16 for the full finding and
correction record.

**The C7 guard correction has been applied**, entirely inside
`backend/tests/test_authorization_route_migration_guard.py`: `_SCOPE_INTRODUCING_NODE_TYPES`
now also includes `ast.ListComp`, `ast.SetComp`, `ast.DictComp` and `ast.GeneratorExp`
alongside the existing `ast.FunctionDef`/`ast.AsyncFunctionDef`/`ast.Lambda`/`ast.ClassDef`,
so `_iter_immediate_scope_nodes` yields a comprehension/generator node itself (its presence
stays visible) but never descends into its element/key/value/generators - the same
yield-but-do-not-descend treatment already applied to a nested function/lambda/class.
Because the fail-closed `.role_codes` visitor still visits every `.role_codes` access
anywhere in the module regardless of scope (a separate, unaffected full-tree
`ast.NodeVisitor` traversal using `generic_visit`), a comprehension/generator-nested
occurrence is never silently dropped from consideration - it is still visited, still fails
the immediate-scope occurrence check, and is still reported as an offense. Eleven new
synthetic tests were added (4 accounts comprehension/generator rejections, 4 identity
comprehension/generator rejections, 2 positive regressions proving the genuine
immediate-scope statements remain accepted, and 1 direct unit test for
`_iter_immediate_scope_nodes` itself), taking the guard file from 88 to 99 test functions;
no existing assertion was weakened, relaxed, or removed. Comprehension/generator TARGET
names (`for item in ...`) were already enumerated as binding sites by `_iter_binding_names`
via `ast.comprehension` before this correction and needed no change. **No authorization
runtime file changed as part of the C7 correction** - only
`backend/tests/test_authorization_route_migration_guard.py` and current-state
documentation, the same scope every prior correction was scoped to.

**Deterministic C7 reverification has since been executed by a human operator with
`docker`/`python` process-execution access, and it is now COMPLETE.** All results below are
from actual execution, not prediction or hand-tracing:

- guard file alone: **99 collected, 99 passed, 0 failed, 4.45s** (88 + 11 new C7 synthetic
  tests);
- four-file focused authorization suite: **117 collected, 117 passed, 0 failed, 5.74s** (the
  unchanged 18 non-guard tests plus the guard file's new total of 99);
- full backend regression: **382 passed, 0 failed, 1 known pre-existing
  `PytestCollectionWarning`, 344.93s** (371 plus the same 11 new tests);
- `alembic current` / `alembic heads`: both `20260831_0030 (head)`, unchanged;
- a targeted lexical-scope subset selected specifically for the P4-1 change
  (`-k "comprehension or generator or scope"`): **15 selected, 15 passed, 0 failed, 84
  deselected, 3.34s** out of 99 collected. This is a deliberate substitution, not an
  omission: the operator chose a filter naming the exact P4-1 change
  (comprehension/generator/scope-boundary tests) directly, rather than repeating the C4-C6
  "detects or rejects" convention; that exact prior filter string was not independently
  re-run in this session, which is recorded honestly rather than assumed, and full-file
  coverage is nonetheless proven by the guard-file-alone result above;
- tracked-secret scan: **PASS**, 740 proposed-tree files evaluated, 737 scanned as text, 3
  binary/oversized skipped, no findings;
- `git diff --check`: clean, no output;
- repository state: `git status --short` shows only the expected uncommitted PF-1A-E1
  candidate files, nothing staged, HEAD unchanged at
  `3c69355858ab352e246a8775f8a463ca7c9c15be`.

Runtime authorization behavior did not change during this reverification: 31 permissions
remain, exactly 110 grants remain, there is no implicit ADMIN bypass, and
`ACCOUNT_TAX_VERIFY` remains `FINANCE_USER`-only. The candidate remains entirely
**uncommitted**. See `docs/continuity/PF_1A_E1_C3_CORRECTION_HANDOFF.md` section 17 for
the full itemized evidence.

**The current gate is: obtain a fresh, read-only independent re-review of this C7
correction pass.** Deterministic testing is no longer the open item. This document does
not itself constitute that review, does not claim final acceptance, and does not claim
integration readiness. The package is **not yet integration-ready**.

## Explicit deferments (not implemented by this package)

- Canonical HR runtime: no `person_id`, `org_unit_id`, `position_id`, `incumbency_id`
  resolution; no SharePoint or Plum integration; no application-user-to-canonical-
  person mapping.
- The PF-1A business-authority configuration model: no Role Catalogue, Authority
  Catalogue, Role -> Authority Rules, Person/Position -> Role Assignments, or
  Configuration Change/Publication record (see
  `docs/agent/pf-1f-hr/PF_1A_AUTHORITY_CONFIGURATION_MODEL.md`).
- No self-escalation prevention mechanism (there is nothing to escalate: this
  package's compatibility mapping is a migration-time database seed, not an
  administrator-editable configuration surface).
- The Q-10 `AUTHORITY_CONFIGURATION_ADMIN` bootstrap governance decision is untouched
  and unaffected; it gates production authority *administration*, not this package.
- No approval-consumer workflow (`CREDIT_ASSESSOR`, `CREDIT_APPROVER`, Commercial
  Offer approval, T&C deviation approval, Work Order release approval, Customer
  Master approval).
- No leaver/transfer/delegation handling (there is no HR feed to react to yet).
- No frontend change beyond what already existed; role-array-based UI hiding remains
  a usability aid only, unaffected by and irrelevant to this backend change.

## Why ADMIN is not universal business authority (or even universal application permission)

Structurally, `has_permission(...)` never special-cases any role name, including
`ADMIN`; it only ever consults the `authz_role_permission` compatibility rows. ADMIN's
current permissions are exactly the union of what the pre-existing `require_roles(...)`
guards already granted it - nothing more. Two permissions in the seeded matrix
(`ACCOUNT_TAX_VERIFY`, and the pair `EVENTS_READ` / `IDENTITY_ROLE_CATALOG_READ`)
deliberately exclude ADMIN or exclude every non-ADMIN role respectively, proving there
is no hidden `if role == "ADMIN": allow` branch anywhere in the authorization seam.
Administering the compatibility mapping itself (a future capability, not built by this
package) and holding a business authority remain, and must remain, separate concepts,
per ORA-001's existing rule that `ADMIN` is never an implicit `CREDIT_ASSESSOR` - this
package extends that same discipline to every application permission it introduces.
