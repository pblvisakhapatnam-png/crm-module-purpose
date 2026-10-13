# Start here

Thank you for taking the time to look at this. This page tells you what PBL is building, what we are asking you to
do now, how to get the system running, what to read, and how we would like to work with you.

## What PBL is building

PBL hires out heavy equipment - cranes and similar machines - and runs transport. We are building a new business
platform, one part at a time. The first two parts are:

- **the CRM** - the sales side. An enquiry comes in as a Lead, becomes a customer Account and an Opportunity; we make
  a Commercial Offer; the customer awards it; and the awarded work is handed over as a Work Order;
- **Equipment Hiring** - everything after that: where the work is, the billing terms, which machines go, their
  papers, and later the crew, hired-in machines, daily log sheets and billing.

## What we are asking for now

**This package is the CRM.** We would like you to complete it, make it ready for real use, and hand it over in a
state we can run and you can support. `docs/vendor/02_CRM_CAPABILITY_MATRIX.md` shows what works today and what is
left; `docs/vendor/03_REMAINING_AND_DEFERRED_SCOPE.md` says which of the remaining work is in this package and which
is not.

**Equipment Hiring is in the same repository, and much of it already works.** You will see it, and its automatic
tests run with everyone else's, but it is not part of this package. Please do not change it.

## This is the first package

We are looking for a long-term partner. After the CRM we expect to follow with the rest of Equipment Hiring - releasing
Work Orders, crew, hired-in equipment, daily log sheets and billing - and then further parts of the platform, such as a
fixed asset register, maintenance, procurement and inventory. Each will be its own package, agreed on its own terms,
built on the same foundations and the same way of working as this one.

We also see this first package as an ice-breaker for both sides: a well-defined piece of work through which we learn
how each other works before we take on larger packages together.

## How we would like to work with you

PBL is a business, not a software company. We have built what you see over the past few months with technical help,
and we have taken care that it is sound:

- every change is checked by several thousand automatic tests before it is accepted;
- the important decisions are written down, with their reasons, so they are not argued again;
- what each part of the system owns, and how the parts talk to each other, is written down;
- a full technical review of the code found 79 issues; the most urgent are corrected, and everything still open is
  listed in `docs/vendor/A_KNOWN_ISSUES.md`, with whether it is part of this package.

We are a business client. Please talk to us about our business, your plan, the risks you see and what you need from
us, in plain language. Where technical detail matters - and sometimes it does - put it in a separate technical note.
Our technical reviewer reads every one.

## What it is built with

| Part | Built with |
| --- | --- |
| The screens | A web application that runs in a browser (React) |
| The server | Python (FastAPI) |
| The database | PostgreSQL (version 17 today) |
| Running it | Docker containers, so every machine runs it the same way |
| Automatic checks | GitHub Actions, gathered into one result, `Required validation` |

We ask you to continue this codebase on this technology. If you see a compelling reason to change part of it, tell us
what, why, what it costs and how long it takes. We will consider a change only when the reason is compelling and the
change is cheap and quick.

## Getting it running

You need Git, Docker, PowerShell 7 and this folder - nothing else, no old database and no files from anyone's
machine. Follow "Setting up a local copy" in `README.md`; `docs/vendor/07_SETTING_UP_AND_TESTING.md` takes you from a
clean computer to every test passing.

## What to read, in order

| # | Read | For |
| --- | --- | --- |
| 1 | This page | The picture |
| 2 | `docs/vendor/01_CURRENT_STATE_AND_SCOPE.md` | What exists, who owns what |
| 3 | `docs/vendor/02_CRM_CAPABILITY_MATRIX.md` | Each CRM capability: built, left to do, waiting on whom |
| 4 | `docs/vendor/03_REMAINING_AND_DEFERRED_SCOPE.md` | What this package includes, what is a separately priced option, what is later |
| 5 | `docs/vendor/05_CRM_TO_HIRING_HANDOFF.md` | The one boundary you may test but not change |
| 6 | `docs/vendor/04_ENGINEERING_RULES.md` | How we build, and where each rule is recorded |
| 7 | `docs/vendor/06_OUTSIDE_SYSTEMS.md` | The existing ERP system, SharePoint, email, SurePass and the others |
| 8 | `docs/vendor/07_SETTING_UP_AND_TESTING.md` | From a clean computer to every test passing |
| 9 | `docs/vendor/08_MILESTONES_AND_CHANGE_CONTROL.md` | How milestones, payment and changes work |
| 10 | `docs/vendor/09_PHASE_0_KICKSTART.md` | How we start together |
| 11 | `docs/vendor/10_HOSTING_USERS_AND_TARGETS.md` | Where it runs, how many people use it, what it must achieve |
| 12 | `docs/vendor/A_KNOWN_ISSUES.md`, `docs/vendor/B_GLOSSARY.md` | Known issues; what the reference IDs mean |
| 13 | `docs/continuity/OPEN_QUESTIONS.md` | Decisions PBL has made, and questions still open |

Then, for any part you work on, its contract under `docs/agent/contracts/` and the architecture decisions in
`docs/agent/ARCHITECTURE_DECISIONS.md`.

## What you may change, and what you may not

| Area | Where | You may |
| --- | --- | --- |
| **The CRM** - this package | Server: `backend/app/modules/` `leads`, `accounts`, `opportunities`, `commercial_offers`, `terms_and_conditions`, `interactions`, `reports`, and the Work Order amendment intake (`work_orders/services/amendments.py`). Screens: `frontend/src/pages/` `leads`, `accounts`, `opportunities`, `commercial-offers`, the dashboard, documents, events and terms pages, and in `work-orders/` the Create Work Order page and the two amendment pages (`NewWorkOrderPage.tsx`, `NewWorkOrderAmendmentPage.tsx`, `WorkOrderAmendmentDetailPage.tsx`) | Change what the agreed work needs; on the Create Work Order page, only what doc 05 allows |
| **Shared foundations** | Sign-in (`identity`), roles and permissions (`authorization`), business events (`events`), statuses (`workflow`), document storage (`documents`, which Hiring also uses), the HR reference (`hr_reference`), `backend/app/core`, `backend/app/shared`, the screens' shared parts (`frontend/src/components`, `frontend/src/layout`) | Change only where agreed CRM work needs it, without breaking other parts. Tell us first |
| **The handoff from CRM to Hiring** | `backend/app/modules/work_orders/services/handoff.py`, the handoff's parts of `work_orders/routes.py`, `repository.py`, `schemas.py` and `contract.py`, and the frozen contract `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` | Read and test. Change only with PBL's written approval (doc 05). Those four files also hold Hiring's Work Order detail and the CRM's amendment intake: change only the CRM's parts |
| **Equipment Hiring** | `eligibility`, `equipment_reference`, `holiday_calendar`, `resource_assignments`, `resource_requirements`, the other files in `work_orders/services/`, and their screens | Do not change. Run their tests; if your work breaks one, tell us |
| **The database's structure** | `backend/alembic/versions/` | Add a new step at the end of the single chain when agreed work needs it; never edit an existing one. PBL keeps the order (doc 04) |
| **The main line of the code** | The `main` branch | PBL owns it. A change reaches it only through a pull request that PBL accepts after review and with every automatic check passed (doc 08) |

## Ground rules

- **Do not silently redesign business rules.** If a rule looks wrong to you, ask us.
- **Do not change Equipment Hiring** because the code is visible.
- **Do not change a frozen contract** without PBL's written approval.
- **Do not rewrite working code** to make it look the way you usually build.
- **Refactor only for a reason you can show us**: correctness, security, maintainability, a breach of a recorded
  boundary, readiness for production, or performance. Tell us the reason before you start.

## When something is unclear

Ask; do not assume. Write the question down with what you found and what you would propose, and send it to us. We
answer in writing, and record each decision in `docs/continuity/OPEN_QUESTIONS.md`.

The records sometimes disagree with each other or with the code. When they do, tell us which. Until we answer, the
order of authority is: a written PBL decision; then frozen contracts and approved architecture decisions; then accepted
requirements; then the module contracts and records; then the source documents; then history (ADR-013 in
`docs/agent/ARCHITECTURE_DECISIONS.md`).

## About the records

The records were written as the work went along. They refer to IDs such as TB1-103, CS-04 or Slice 9F;
`docs/vendor/B_GLOSSARY.md` explains them. Some mention documents that are not in this copy; the glossary lists those
too. The copy you receive has no history: it starts at a single commit, and
`docs/vendor/VENDOR_BASELINE_MANIFEST.md` says what it was made from.
