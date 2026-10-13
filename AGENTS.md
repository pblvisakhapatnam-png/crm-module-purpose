# Working in this repository

For anyone - a person or a coding tool - who changes this code. Read `VENDOR_START_HERE.md` first; it says what this
package is, what you may change and how to raise a question. `docs/vendor/04_ENGINEERING_RULES.md` gives the full
set of rules and where each is recorded. This file keeps the rules a change most often touches, under the headings the
code and the records cite.

## Current prototype state

Where the system stands, and what each part owns: `docs/vendor/01_CURRENT_STATE_AND_SCOPE.md`. What works today and
what is left in the CRM: `docs/vendor/02_CRM_CAPABILITY_MATRIX.md`. The latest status and the frozen handoff's
fingerprint: `docs/continuity/NEXT_STEPS.md`.

## Rules for every change

- **Keep to the agreed work.** Do not change unrelated modules, and do not change Equipment Hiring
  (`VENDOR_START_HERE.md`, "What you may change, and what you may not").
- **Backend authorization is the security.** Every business route checks the user's permission on the server. Hiding a button
  on screen helps the user; it protects nothing.
- **A database change is always a new migration**, written by hand, added at the end of the single chain. Never edit
  one that exists (`db/notes/migration-rules.md`).
- **An interface change updates its contract** under `docs/agent/contracts/` in the same change.
- **Say "Account" on screen**, and `business_party` inside the code and the database.
- **Screens call the server by relative addresses** (`/api/...`), never a fixed host or port. The browser keeps the
  sign-in token under `pbl_auth_token`.
- **A message about an action appears beside the button that triggered it**, not only at the top of the page; each
  action has its own message, cleared when its input changes.
- **Style screens through the shared stylesheet** (`frontend/src/styles/globals.css`), not inline styles.
- **Do not weaken, skip or delete a test** to make a change pass. A changed rule gets a test that fails when the rule
  is broken.
- **Every meaningful business action should create a business_event** unless the change explicitly records why it
  does not. Reads are not business actions and write none.

## Currency

INR is the default and the operating currency. An offer, offer line, pricing evidence, awarded amount or amendment line
may be recorded in USD, GBP or EUR when chosen, and in nothing else. The list lives in `backend/app/shared/currency.py`
and is offered on screen from `frontend/src/components/currency.ts`; add a currency in both. **Never convert, and never
add amounts in different currencies together**: reports and quotations total each currency separately. Credit exposure
and Work Order billing terms remain INR only.

## Date/time display rule

PBL's users work in India's time (Asia/Kolkata). The database and the server keep times in UTC.

- **Showing a time:** always through `formatDateTime` in `frontend/src/components/dateTimeDisplay.ts`, never a page's
  own formatting. Do not label every time "IST"; the screen makes the zone clear.
- **A time a person types** is India's time. Send it with `enteredIndiaTimeToUtc` from
  `frontend/src/components/enteredDateTime.ts`; the server refuses a date and time without a zone.
- **A date box** is always `frontend/src/components/DateInput.tsx`.

Tests in `frontend/src/components/` fail when a page breaks one of these.

## Checking a change

In this order, for a change of any size:

1. the tests for what you changed;
2. the whole server test suite: `docker compose exec backend pytest`;
3. for a screen change, the type check, the tests and the production build:

   ```powershell
   docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run typecheck
   docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm test
   docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run build
   ```

   then `docker compose up -d --build frontend` to see it in the browser;
4. the browser walk-throughs, `pwsh -NoProfile -File scripts/run-e2e.ps1`, when the change touches a flow they cover;
5. trying the new behaviour by hand;
6. a review of your own change before you hand it over.

After a change to server code, rebuild the server before trying it by hand:
`docker compose up -d --build --force-recreate backend`. Migrations are built into the server's image, so this is also
needed after pulling a change that adds one.

A change that touches the contract fixtures, or adds a file that could hold a password or key, also runs the
repository checks (`README.md`, "Repository checks").

## Parallel lanes and worktrees

### Only one stack runs at a time on a developer machine

`docker-compose.yml` publishes fixed ports - 5432, 8000 and 3000 - so a second copy of the system collides with the
first whatever it is called. Stop a copy when you stop working on it (`docker compose stop`), and remove it before you
delete its folder (`docker compose down --remove-orphans`, from inside that folder).

### The migration chain is single and linear

One chain of migrations, one head. PBL decides the order when two pieces of work both need a new migration; the later
one changes its `down_revision` and re-runs the check from an empty database.

### Where two lanes meet inside one module

`backend/app/modules/work_orders/` holds both the CRM's handoff (`services/handoff.py`) and Equipment Hiring's Work
Order detail. The handoff is frozen: check the contract's fingerprint before and after any work near it
(`docs/vendor/05_CRM_TO_HIRING_HANDOFF.md`). Four files both sides edit: `backend/app/main.py`,
`frontend/src/routes.tsx`, `backend/app/modules/authorization/contract.py` and
`backend/tests/fixtures/post_baseline_tightened_routes.py`. A bad merge in the last one does not fail; it records the
wrong permission for a route, so read it by eye after any merge that touches it.

## Pull requests and CI cost

Every push to a branch with an open pull request runs the full automatic checks, about half an hour of machine time.
Raise a pull request when the change is ready to be accepted, push it once, and push again only to fix a failed check
or to bring the branch up to date. Group small fixes together. A change reaches `main` only when `Required validation`
has succeeded on it, the branch is up to date with `main`, and PBL has accepted it
(`docs/vendor/08_MILESTONES_AND_CHANGE_CONTROL.md`).

## PBL review and approval language

Anything that asks PBL to review, decide or approve is written in short, plain business language that a reader with
no software background - and limited English - can follow: what should happen in the real work, who may act, what
information is needed, and what happens when something goes wrong. Technical detail goes in a separate section for
PBL's technical reviewer. Do not ask PBL again about something already decided in the records
(`docs/continuity/OPEN_QUESTIONS.md`); cite the decision.

## Never commit

`.env`, passwords or keys, ZIP files, caches, generated test reports (`e2e/playwright-report/`, `e2e/test-results/`,
`e2e/.manifest/`), practice-data run records (`backend/.smoke-runs/`) or the demo tool's local state (`.vendor-demo/`).
`.gitignore` covers most of these; the committed-credential check (`scripts/check_tracked_secrets.py`) catches passwords and keys.
