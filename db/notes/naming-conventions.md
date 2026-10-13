# Database Naming Conventions

Written 8 October 2026 (TB-1 corrective package CS-16; findings TB1-401, TB1-402 and TB1-407). It states the conventions
**as they are**, measured on a database migrated from empty to `20260908_0048` and, on 9 October, again to
`20260908_0050` - 99 tables, Alembic's own included (the queries and their outputs:
`docs/agent/technical-enablement/tb1-handover-evidence/naming_catalogue.sql`, `naming_catalogue_20260908_0048.txt` and
`naming_catalogue_20260908_0050.txt`). The counts below are at `20260908_0050`; the two outputs differ only in three
check constraints (`20260908_0050`'s) and one partial unique index (`20260908_0049`'s customer reference). Where two
conventions live side by side, it says which tables follow which. Converting the older ones is CS-16's
migration work, due before any reader outside the application connects to the database; until then, a new table follows
the newer convention each section names.

## Tables

- Lower-case `snake_case`, singular: `crm_lead`, `business_party_contact`, `equipment_asset`.
- The name starts with its owning module's name, with two older exceptions. The CRM chain's tables built before the
  Hiring lane start `crm_` (`crm_lead`, `crm_opportunity`, `crm_commercial_offer` and its lines and pricing evidence,
  `crm_work_order` and its lines and amendments), and the Account Master's start `business_party` (ADR-003: Account in
  the user interface, `business_party` inside). Offer satellites start `commercial_offer_`, the clause library is
  `tc_clause_library`. The platform's are `app_user`, `role`, `user_role`, `sign_in_*`, `authz_*`, `business_event`,
  `workflow_status` and `document_metadata`. The Hiring modules' start with the module: `equipment_*`, `eligibility_*`,
  `resource_requirement*`, `resource_assignment*`, `holiday_calendar_*`; Interactions' start `interaction`.
- Which module owns each table, and which other modules read it, is in
  `docs/agent/architecture/BOUNDARY_EXCEPTION_REGISTER.md`.

## Keys and public identifiers (ADR-007)

- **`id`** - on 84 tables, from the table's own sequence (`nextval('<table>_id_seq')`): an `integer` on 83 and a
  `bigint` on `sign_in_attempt`. Internal only: never in a route, a response or an event.
- **No `id`** on 14 application tables, and on Alembic's `alembic_version` - 15 in the catalogue: reference, link
  and configuration rows keyed by their codes (`equipment_class`, `equipment_type`, `equipment_capability`,
  `equipment_class_capability`, `eligibility_jurisdiction`, `eligibility_certificate_kind` and the like), state rows
  keyed by what they describe (`equipment_reference_state`, `holiday_calendar_holiday_state`), and `sign_in_stop`,
  keyed by its digest.
- **Public identifier** - a UUID kept as text, `character varying(36)` (90 columns; three actor columns of the dormant
  authority engine are `text`). Twelve tables name it `public_id` - the platform's (`app_user`, `role`,
  `business_event`, `workflow_status`, `authz_permission`, `authz_role_permission`), the clause library and the
  offer's satellite tables; the rest name it after the record - `lead_public_id`, `offer_public_id`,
  `equipment_asset_public_id`. A column holding another record's public identifier carries that record's name:
  `work_order_public_id`, `linked_record_public_id`.
  Keeping UUIDs as text rather than PostgreSQL's `uuid` type is recorded as no action (TB1-407).
- **Foreign keys** - 97 of 183 are on an `*_id` column holding the other table's `id`; the rest reference a public
  identifier, a code or a version number, as the Hiring and authority tables do.

## Business references

Three ways, all recorded:

| Records | Reference | How it is made |
| --- | --- | --- |
| Resource requirements, machines and kit, allocations | `RR-`, `EQ-`, `AL-` and six digits or more (`requirement_reference`, `asset_reference`, `assignment_reference`) | A generated column: `'RR-' \|\| lpad(id::text, GREATEST(6, length(id::text)), '0')`. Past `id` 999,999 it grows a digit |
| Commercial Offers, Work Orders | `CO-`, `WO-` and six digits (`offer_code`, `work_order_code`) | An `UPDATE` straight after the insert: `'CO-' \|\| RIGHT('000000' \|\| CAST(id AS VARCHAR(20)), 6)`. From `id` 1,000,001 the code repeats an earlier one and its unique index refuses the insert - not reachable at PBL's volume (TB1-402). **Kept as it is** (the owner, 8 October 2026: ADR-007's exception) |
| Accounts, Leads, Opportunities | None - known by name | **ADR-007 exception**, approved by the owner on 8 October 2026 (`docs/agent/ARCHITECTURE_DECISIONS.md`, ADR-007) |

A new record type that needs a reference uses the generated column.

## Columns

- Lower-case `snake_case`.
- A status is a code in `<thing>_status_code` (`lead_status_code`, `asset_status_code`), upper-case with underscores
  (`QUALIFIED_PROSPECT`, `ACTIVE`); the one older exception is `document_metadata.status`, free text (TB1-401).
- Who and when: `created_at`, `created_by`, `updated_at`, `updated_by`. The `_by` columns hold the acting user's public
  identifier (`app_user.public_id`), never an integer id or a name.
- Money: `NUMERIC(18,2)` (30 columns); rates, quantities and capability values use the precision their contract names.
- Booleans: 18 of the 61 are named `is_*` or `has_*`; there is no rule beyond `snake_case`.

## Timestamps: two conventions

- **105 columns are `timestamp with time zone`**, in every other table that has a timestamp. New tables use this.
- **56 columns are `timestamp without time zone`**, in the 21 tables migrations `0006` to `0029` created, written for
  SQL Server and carried over by TE-2B: `business_party` and its address, contact, GSTIN and tax profile tables;
  `crm_lead` and `crm_lead_activity`; `crm_opportunity`; `crm_commercial_offer`, its lines and pricing evidence, and
  `commercial_offer_credit_review`, `_customer_response`, `_revision`, `_submission_evidence` and `_tc_clause`;
  `crm_work_order`, its lines, `crm_work_order_amendment` and its lines; `tc_clause_library`.
- **The naive ones hold UTC.** Every connection the application, Alembic and the test-data harness open sets the
  session's time zone to UTC (`CONNECT_ARGS` in `backend/app/core/database.py`; ADR-028, "Timestamps"), so the values
  are right and the screens show them in India's time. A reader that does not - `psql` on a server whose default zone
  is Asia/Kolkata, a reporting tool, an integration - reads 10:00 UTC as 10:00 local. **Until CS-16 converts them, any
  such reader must first `SET TIME ZONE 'UTC'`.** The conversion is exact given that rule:
  `ALTER COLUMN ... TYPE timestamptz USING ... AT TIME ZONE 'UTC'`.

## Status columns: two conventions

- **The Hiring tables and three CRM tables check their status codes in the database** (a `CHECK` constraint):
  every `equipment_`, `eligibility_` and `resource_` status, and `crm_commercial_offer_line`, the quotation document
  and `crm_work_order_amendment`. New tables do this.
- **Eight are checked only by the application**: `business_party.account_status_code`, `crm_lead.lead_status_code`,
  `crm_opportunity.opportunity_status_code`, `crm_commercial_offer.offer_status_code`,
  `crm_work_order.work_order_status_code` and `.source_offer_status_code`, `crm_work_order_line.line_status_code`, and
  `document_metadata.status`. The CRM services accept only codes active in `workflow_status` (a Work Order copies its
  offer's); the document status is free text a route takes as it comes. The database accepts any text. A status written by SQL outside the services - an import, a support fix - is not checked, and the reports and
  lifecycle rules keyed on the known codes would quietly pass it by. CS-16 adds the checks (TB1-401).

## Constraint and index names

| Kind | Name | Count | Exceptions |
| --- | --- | --- | --- |
| Primary key | `pk_<table>` on 30 tables - most CRM tables of `0006` to `0029`, `authz_permission` and `authz_role_permission`, Interactions' and some Equipment Reference tables; PostgreSQL's own `<table>_pkey` on the other 69 | 30 and 69 | No rule by module; both are left as they are |
| Foreign key | `fk_<table>_<column>` | 181 | `user_role`'s two, PostgreSQL's names |
| Unique constraint | `uq_<table>_<columns>` | 119 | One PostgreSQL name (truncated) and `ux_quote_document_offer_version` |
| Unique index (10 of them partial) | `ux_<table>_<what>` | 20 | - |
| Check constraint | `ck_<table>_<what>` | 301 | - |
| Exclusion constraint (`btree_gist`) | `ex_<table>_<what>` | 4 | - |
| Index | `ix_<table>_<columns>` | 135 | - |

TB-1 recorded as no action (TB1-407) ten redundant single-column indexes and the two names PostgreSQL chose.

## Migration files

`backend/alembic/versions/YYYYMMDD_NNNN_<what>.py`, with the same `YYYYMMDD_NNNN` as its revision id and the previous
head as `down_revision`. Since `20260908_0033` the date part has stayed `20260908` - the number after it is what
orders the chain, not the date. One file has no date in its name, `0005_document_metadata_api_foundation.py`
(revision `20260629_0005`): no action (TB1-407). How a migration is written is in `migration-rules.md`, beside this file.
