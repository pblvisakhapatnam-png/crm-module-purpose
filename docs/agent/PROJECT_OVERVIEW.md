# Project Overview

## Project name

PBL CRM + Equipment Hiring

## Purpose

This repository began as a production-style CRM-first prototype and is now transitioning to a
production-candidate modular CRM + Equipment Hiring application that preserves future
Transportation integration paths.

The prototype is intended to support three possible outcomes:

1. A working reference implementation for PBL.
2. A technical design aid for the vendor building/refining the Plum ERP modules.
3. A reusable base if the vendor chooses to adapt or integrate parts of it.

The prototype planning phase is complete through Slice 6P. PAF-1 records the production
architecture foundation under `docs/agent/architecture/`. Since then the technology migration
(TE-2A, TE-2B, TE-2CI, TE-2C) and the authority foundation through PF-1A-E3 are complete, the CRM
has been deployed for its pilot on a hosted test site, and the Hiring lane has taken the Work Order past its shell
(`AGENTS.md`, "Current prototype state"). What is next changes with every package and is in
`docs/continuity/NEXT_STEPS.md`, not here. Sixteen of eighteen foundation contracts are approved; Market Hire and invoice preparation wait
only for their named open decisions and do not delay unrelated work.

**Platform scope.** CRM + Equipment Hiring are the first substantial implementations of a broader
PBL application-platform direction, not a standalone architecture built only for this project. The
architectural principles recorded under `docs/agent/architecture/` — most directly ADR-030 in
`docs/agent/ARCHITECTURE_DECISIONS.md` and
`docs/agent/architecture/PBL_PLATFORM_ARCHITECTURE_AND_FUTURE_AI_READINESS.md` — apply by default to
future PBL-developed modules and to modules progressively replacing existing Plum ERP functionality
(for example Transportation/TMS, Maintenance, Fixed Assets, Finance-related operational
integrations, or Document Management), unless an approved ADR records a justified exception.

## Business baseline

The business baseline is the set of CRM + Equipment Hiring requirement and architecture documents supplied by PBL. The solution must preserve the lifecycle traceability from:

Lead â†’ Account / Qualified Prospect â†’ Opportunity â†’ Commercial Offer â†’ Work Order â†’ Customer activation â†’ Execution â†’ Log Sheet â†’ Billing â†’ Invoice â†’ Collection.

The first implementation focus is CRM, but design decisions should not block later Equipment Hiring or Transportation integration.

## First business object

The UI term is **Account**.

The internal backend/domain model is **business_party**.

This is intentional. The same real-world party may later become a customer, vendor, transporter, project owner, billing entity or other role-bearing party.

## First development goal

The first real business slice is Account / Qualified Prospect foundation.

Before that, Slice 0 must create the platform foundation:

- Docker Compose local stack.
- Database container. Slice 0 built this on SQL Server Developer Edition; TE-2B replaced it with
  PostgreSQL 17 (ADR-028, which supersedes ADR-006 for the production baseline).
- FastAPI backend shell.
- Frontend shell. Slice 0 built this with Next.js; TE-2A replaced it with React 19 + Vite +
  React Router (ADR-016).
- SQLAlchemy + Alembic foundation.
- Simple auth and role model.
- Business event foundation.
- Workflow status foundation.
- Document metadata foundation.
- Test command structure.
- Agent instruction and documentation structure.

## Repository documentation model

There are two documentation sets:

1. `docs/agent/`
   - Used by coding agents and agent-style workflows.
   - Contains contracts, slice plans, acceptance criteria, coding standards and testing rules.

2. `docs/continuity/`
   - Used by the project owner and future chats.
   - Contains decisions, handoff notes, lessons learned, source document register and next steps.

## Development principle

The project is contract-first, slice-based and test-quality-driven.

No slice should be so large that a human cannot test the main UI flow in about 10-20 minutes using seeded data or clearly described test data.

Production module work is additionally governed by explicit contract maturity, module/data
ownership and dependency-based delivery waves. A documented `PROPOSED` contract is review input,
not authorization to implement or a frozen compatibility boundary.
