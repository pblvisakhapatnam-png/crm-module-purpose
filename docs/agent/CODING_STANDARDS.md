# Coding Standards

These standards apply to all agent-generated and human-written code.

## 1. General rules

- **Design principles (the project owner, 26 September 2026), for all development - backend, frontend,
  tooling, tests and documents:** DRY first; then KISS, YAGNI and SOLID, as far as they do not conflict.
  Before writing something, look for the existing helper, class, service or pattern and reuse it; extract a
  shared one when a second copy would appear. Build what the need requires, not what it might one day.
- Keep changes limited to the current slice.
- Do not refactor unrelated modules.
- Do not introduce a new library without documenting why.
- Do not change an API contract without updating the relevant file under `docs/agent/contracts/`.
- Do not change database schema without an Alembic migration.
- Do not bypass role/permission checks for convenience.
- Do not hide business controls only in UI code; backend must enforce important controls.

## 2. Backend structure

Backend framework: FastAPI.

Each module should follow this structure:

```text
backend/app/modules/<module>/
  models.py
  schemas.py
  routes.py
  service.py
  repository.py
  permissions.py      # where needed
  validators.py       # where needed
  events.py           # where needed
  tests/
```

Responsibilities:

- `models.py`: SQLAlchemy models only. *(Reconciled 8 October 2026, TB-1 TB1-400.)* The models are not the schema:
  modules read and write through SQL text, most tables have no model, and a new table needs none. Migrations are written
  by hand and `alembic revision --autogenerate` is refused (`db/notes/migration-rules.md`).
- `schemas.py`: Pydantic request/response DTOs.
- `routes.py`: HTTP route definitions and dependency wiring.
- `service.py`: business rules and use cases.
- `repository.py`: database access.
- `permissions.py`: role/action checks.
- `validators.py`: validation helpers that are not basic Pydantic validation.
- `events.py`: business event creation/emission helpers.

### When a service outgrows one file

Recorded by TE-6 (September 2026), which split `work_orders/service.py` - 3,529 lines across five
concerns - into a package. `commercial_offers/service.py` has the same shape; follow this when it is
split.

*Reconciliation, 8 October 2026 (TB-1 CS-11):* `commercial_offers/service.py` is now split this way, into thirteen
concern modules and `common` (`docs/agent/technical-enablement/CS_11_COMMERCIAL_OFFERS_SERVICE_SPLIT.md`); its 9B scan
below walks the package. CS-11 adds two lessons. A test that calls a private helper through the service
(`service._validate_currency(...)`) follows the code too, and only a fail-closed scan of every caller finds it. And
while another branch may still change the one-file service, generate the split with a script that can be run again on
the changed file, as CS-11's `split.py` did. CS-11's and TE-6's proof scripts are not part of this copy; their
records say what each checked.

```text
backend/app/modules/<module>/
  service.py              thin: re-exports, by name, every public name the module had
  services/__init__.py
  services/common.py      the module's exceptions, and helpers more than one concern calls
  services/<concern>.py   one per concern, named for what it does
```

- **A concern module imports `common` and nothing else under `services/`.** If two concerns need each
  other, that is a design finding to record, not an import to add.
- **A helper one concern alone uses lives with that concern**; one that several use goes to `common`.
  The module's exceptions stay together in `common` even where only one concern raises them: they are
  the error vocabulary `routes.py` maps to HTTP statuses.
- **Callers keep importing from `service.py`, and nothing it defined disappears.** Re-export every
  public name the module defined, whether or not anything imports it today, and name each one: a
  wildcard would hide a name that quietly stopped existing. Pin the list in a test that also checks each
  is the concern module's own object (TE-6's is `backend/tests/test_te6_work_orders_service_surface.py`),
  and set `__all__` to exactly that list.
- **Names the old module only imported are not its API** (owner's decision, 23 September 2026, for
  TE-6). A module without `__all__` also exposes everything it imports - repository functions, schemas,
  constants - and `import *` hands them all out. Do not re-export them: nothing should reach repository
  functions through a service, and a re-exported name invites a test to patch it on the service, where
  the moved code never looks. Show that no caller used one - with a scan that fails on anything it cannot
  resolve - and say in the package record that the surface narrowed and by how much.
- **Tests that patch or introspect follow the code, not the re-export.** A function looks names up in
  the module it is defined in, so `monkeypatch.setattr(service, "a_repository_function", ...)` stops
  reaching it once the function moves: patch the concern module. A test that walks `vars(service)`
  filtering on `fn.__module__ == service.__name__` finds nothing after a split: walk the package.
  `commercial_offers` has such a scan (`_status_writing_function_sources` in
  `backend/tests/test_slice_9b_pilot_hardening.py`). Before trusting a missed one to fail, check that
  it would.
- **Move verbatim, and prove it mechanically.** Compare every definition's source text before and
  after; allow only named exceptions, each with its own proof. A reviewer can check a proof; nobody can
  read three thousand moved lines. **Identical text is not enough on its own**: a moved function reads
  its globals from its new module, so also check that every name it looks up resolves to the same
  object as before. `docs/agent/technical-enablement/TE_6_WORK_ORDERS_SERVICE_SPLIT.md` describes the
  checks TE-6 ran, and what each review round found missing in its first versions.
- **Split long functions along a seam they already have**, not into a table for its own sake. TE-6
  split billing-term validation by the parts the terms arrived in, so Part 4 adds a
  `_part_4_term_values` and a `_check_part_4_terms` beside the others.

Writes in `work_orders` - and in the other Hiring modules - end `with rollback_on_error(db): ... db.commit()`
rather than repeating `try: ... except Exception: db.rollback(); raise`. The commit stays an explicit statement, so a
reader sees what is inside the transaction and where it becomes permanent. (TE-6 named it `_rollback_on_error`.)

Since TB-1 TB1-605 (October 2026) that helper is shared, with two others the Hiring modules had each copied: import
them, never copy them. `app/shared/transactions.py` holds `rollback_on_error` (the block above) and
`take_advisory_lock(db, key)` (a module's write lock: a text key is hashed by PostgreSQL, a number is used as it is);
`app/shared/business_time.py` holds `india_today()` and `india_date(moment)`. Call "today" through the module -
`business_time.india_today()` - so a test that fixes the date patches that one name. A Hiring module does not hold
India's zone itself; if it needs more than a date in India's time, add the function to `business_time`. The one
exception is Work Orders' `INDIA_TIME_ZONE`, which TE-6 pinned as public: it stays, as an alias of
`business_time.BUSINESS_TIME_ZONE` in `services/common.py`, re-exported by `service.py`, and no other Hiring module
binds the zone.

A create that carries a request key follows one rule (TB-1 TB1-102 part b, October 2026; MCF-001): store
`request_fingerprint(payload)` from `app/shared/request_keys.py` with what the request makes, and judge a later use of
the key with `is_same_request` - the very same request is answered with what it made, `replayed: true`, no event;
any other request is `409`. Never answer a used key on the key alone or on a few of the request's fields: that hands a
changed request the first one's record.

## 3. API standards

API base path:

```text
/api
```

Examples:

```text
GET    /api/health
POST   /api/auth/login
GET    /api/auth/me
GET    /api/accounts
POST   /api/accounts
GET    /api/accounts/{account_id}
PATCH  /api/accounts/{account_id}
```

Rules:

- API routes should use UI/business terminology where appropriate, e.g. `/api/accounts`.
- Internal code may use `business_party`.
- Responses must be predictable and documented.
- Validation errors must be understandable to business users where possible.
- Do not expose internal integer IDs as the only API identifier.
- Prefer UUID/public ID for external references.
- Avoid leaking implementation details in error messages.
- A date and time a request takes, in its body or query, is `ZonedDateTime` (`app/shared/zoned_datetime.py`): ISO text
  with its zone or refused - a number too - and held as UTC (ADR-028, "Timestamps", 11 October 2026).
  `tests/test_entered_time_zone.py` walks every route and fails otherwise; a new input is added to its list.

## 4. Database standards

Database: PostgreSQL (ADR-028). PostgreSQL is the only supported runtime. Do not add
dual-dialect code, a compatibility layer or per-dialect branches; write PostgreSQL SQL directly.

ORM/migrations:

- SQLAlchemy 2.x, `postgresql+psycopg` dialect.
- Alembic migrations.
- Psycopg 3 driver.

Write PostgreSQL SQL, not T-SQL. In particular use `LIMIT n [OFFSET n]` (not `SELECT TOP` or
`OFFSET ... ROWS FETCH NEXT ... ROWS ONLY`), `CURRENT_TIMESTAMP` (not `SYSUTCDATETIME()`),
`COALESCE` (not `ISNULL`), `||` for string concatenation (not `+`), `DELETE FROM t USING ...`
(not `DELETE alias FROM ... JOIN ...`), and real booleans (`IS TRUE` / `TRUE` / `FALSE`, never
integer `1`/`0`) for boolean columns. Bind Python `bool` values to boolean columns.
`backend/tests/test_postgresql_dialect_regression.py` guards these statically.

Naming:

- Use lowercase snake_case table and column names in SQLAlchemy definitions.
- Keep names readable for vendor review.
- Avoid cryptic abbreviations.
- Use explicit foreign keys.
- Use created/updated metadata on core business tables.

Common fields for major business records:

```text
id
public_id
business_reference
status
created_by
created_at
updated_by
updated_at
row_version / version where needed
is_deleted
```

Important:
- Avoid hard deletes for business records unless explicitly approved.
- Use status or soft delete where business history matters.
- Do not silently overwrite submitted/approved records in later modules.

## 5. Reference data

Use database lookup tables for business-controlled values where they may change.

Examples:
- roles
- account statuses
- service interests
- PAN/GST verification states
- document types

Stable internal technical states may use enums where appropriate.

## 6. Business events

Important changes should create a `business_event` record.

Examples:
- account created
- account status changed
- document linked
- workflow status changed
- role-restricted action attempted or blocked where relevant

Each event should include enough context for traceability:

```text
event_name
source_module
record_type
record_id / public_id
user_id
timestamp
status_before
status_after
reason / remarks
correlation_id where relevant
```

## 7. Frontend standards

Frontend framework: React 19 with Vite and React Router (ADR-016).

Structure:

```text
frontend/src/main.tsx           entry point; renders the router inside React.StrictMode
frontend/src/routes.tsx         route table - one entry per public URL
frontend/src/router.tsx         React Router route objects built from the route table
frontend/src/routes.test.ts     route-table regression tests
frontend/src/layout/            application shell
frontend/src/components/        shared components
frontend/src/pages/             one module per page
frontend/src/styles/            application stylesheet
```

A new public URL is added by editing the route table and its tests, not by adding a file in a
directory that a framework scans. Dynamic parameters come from React Router's `useParams`.

UI approach:
- Desktop-first.
- Responsive-ready.
- Workflow-style screens, not only CRUD forms.
- Use `Account` as the visible term for business_party records.

Account tabs:

```text
Profile
Contacts
Addresses
PAN / GST
Classification
Documents
Events
```

Rules:
- Style through the shared stylesheet, `frontend/src/styles/globals.css` - its classes and `--app-*`
  colour tokens - not inline `style={{...}}`, so a layout or colour fix is made once (the design
  principles in section 1). Use an existing class where one fits; otherwise add one there, named for what
  it is. Pages that still style inline predate this rule and are moved whole in their own package, never as
  scope creep inside an unrelated slice (`UI_UX_CARRY_FORWARD.md`, "Equipment", keeps the count).
- Every date or date-and-time box is `components/DateInput.tsx` (`withTime` for a time), never a plain
  `<input type="date">`: it stops the year at four digits. `components/dateInputs.test.ts` fails otherwise.
  A date-and-time box holds India's time: send it with `enteredIndiaTimeToUtc` and fill it from a saved time with
  `apiDateTimeToIndiaInput` (`components/enteredDateTime.ts`). `components/enteredDateTime.test.ts` fails when a file
  has fewer calls to `enteredIndiaTimeToUtc` than such boxes.
- A business time from the API is shown with `formatDateTime` from `components/dateTimeDisplay.ts`, never a page's
  own reader or formatter (TB-1 note N-06). A page that needs an API time as a moment (to sort or compare) adds the
  function to `dateTimeDisplay.ts`. `components/dateTimeDisplay.test.ts` reads the source with TypeScript's type
  checker and fails when any file but `dateTimeDisplay.ts` and `enteredDateTime.ts` makes a `Date` from a string
  (other than a date-only value at a fixed time, or now), uses `Date.parse` or `readApiDateTime`, uses `formatDateTime`
  or `apiDateTimeToIndiaInput` other than by calling it directly with a record's field as the API sent it, or shows a
  time of day.
- Say "Sign in" and "Sign out", never log in or log out; a page with no session, or a refused one, uses
  `SIGN_IN_FIRST` or `SIGN_IN_AGAIN` from `components/signInMessages.ts`.
- A page's Back link from `returnTo` comes from `readSafeReturnTarget` in `components/returnTarget.ts`, never a
  page's own reading of the address (TB1-805); `components/returnTarget.test.ts` fails otherwise.
- Keep forms simple and explicit.
- Show validation messages near fields.
- Do not rely only on frontend validation.
- Avoid large multi-purpose screens that cannot be manually tested quickly.
- Keep components small and reusable.

## 8. Error handling

Backend errors should have consistent shape.

Recommended format:

```json
{
  "error": {
    "code": "ACCOUNT_DUPLICATE_WARNING",
    "message": "A similar account already exists.",
    "details": {}
  }
}
```

**No route sends this shape yet** (reconciled 7 October 2026, TB-1 TB1-904): every route returns
FastAPI's `{"detail": ...}`, and the pages read errors in that shape. Adopting this envelope across
the API, with MCF-001's other conventions, is one retrofit - TB-1's corrective package CS-06
(PF-1B), which closes TB1-102 - shipped with the pages' shared error reader (CS-10). Until then a
package that keeps `{"detail": ...}` records it as an exception, as `interaction-contract.md` does.

Do not expose stack traces or sensitive internal details through API responses.

## 9. Logging

- Log technical failures with enough detail for support.
- Do not log passwords, tokens, secret values or sensitive commercial data.
- Never log the text of a database error from a statement that carries business data (`str(exc)`, or a traceback
  that ends in it): PostgreSQL's DETAIL line repeats a duplicated key or a whole failing row, which `hide_parameters`
  does not hide. Log what `app/core/errors.py` logs - the error's class, SQLSTATE and the constraint, table or column
  it names (TB1-503).
- For business traceability, use business events rather than only technical logs.

## 10. Documentation update rule

Every completed slice must update:

- relevant contract file under `docs/agent/contracts/`
- relevant slice file under `docs/agent/slices/`
- relevant acceptance checklist under `docs/agent/acceptance/`
- continuity notes if a project decision changed
