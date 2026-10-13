# Boundary Exception Register

## Status and owner

Recorded 8 October 2026 (TB-1 findings TB1-100 and TB1-101, corrective package CS-07). **Owner: PF-1B**, the API and
event retrofit (`MODULE_DEPENDENCY_AND_DELIVERY_WAVES.md`), which this register's rows are the scope of - the follow-up
`PLATFORM_PRINCIPLES_IMPLEMENTATION_REVIEW.md` names first, now complete - apart from section 4's five database rules,
a permanent exception to ADR-017 the owner approved on 9 October 2026 (`docs/agent/ARCHITECTURE_DECISIONS.md`, under
ADR-017), owned by the Commercial Offer to Work Order handoff, which the CRM lane owns.

Measured at `main` `5e19123` (Alembic head `20260908_0048`) by re-running TB-1's own scan, which found the same 183
cross-module table accesses there as at TB-1's baseline - only their line numbers had moved. Measured again on 9
October 2026 at this package's commit `464fb0a` - `main` at `fb381c6` merged in, Alembic head `20260908_0050` - with
the same scan, its dispositions only moved to their new lines: **186**, the 183 and three reads CS-04 part 1 (HOF-2)
added (R3 and R4 below). The scan reads application SQL; the database rules CS-04 part 1's migration added between the
two modules' tables are not application SQL, so they were read from the migration and are listed by hand in section 4.
Both runs' outputs, the adaptations and the commands are in `docs/agent/technical-enablement/tb1-handover-evidence/`.
Line numbers below are at `464fb0a`; function names are the stable reference.

## What the rules say, and what an entry here means

- ADR-017: another module must not write a module's tables; cross-module reads use an owning-module query interface, a
  documented read model, or an approved immutable identifier - "ad hoc joins do not create ownership".
- `PRODUCTION_ARCHITECTURE_DIRECTION.md`, dependency rule 4: a module does not write another module's tables or import
  its repository.
- `MCF-001`: no direct cross-module repository or table writes.

Each row below departs from those rules. Recording it makes it a **known exception with an owner and a retirement** -
or, for section 4's five rules, the owner's approval as permanent - as the Interactions row of
`MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` already is for its link checks. It is not permission to add more of the same: a
package that adds a cross-module table access - a read, a write, a row lock, or a database rule that reads another
module's table - or imports another module's repository, either goes through the owning module's interface or adds
its row here with its reason, and a package that retires one removes its row (`PRODUCTION_READINESS_GATES.md`,
module-slice Definition of Done).

Of the packages merged after `5e19123`, only CS-04 part 1 added a cross-module access (its three reads and the
database rules of section 4). The second run's imports grew by six, none of them a repository: two of Commercial
Offers' `contract` by Work Orders (CS-04 part 1) and four of platform infrastructure, TB1-102 part b's shared
`app/shared/request_keys.py` among them.

## 1. Writes into another module's tables (TB1-100)

| # | Writer | Into (owner) | What, and why it matters | Retired by |
| --- | --- | --- | --- | --- |
| W1 | Leads: `convert_lead` (`leads/service.py:483`) | `business_party` (Accounts), `crm_opportunity` (Opportunities) | Lead conversion builds the Account and the Opportunity itself and inserts them through those modules' repositories (`insert_business_party`, `insert_opportunity`), in one transaction, and records `AccountCreated` and `OpportunityCreated` in those modules' names. The conversion is a coordinator, which the consistency model allows, but it holds a second copy of their creation rules: a rule Accounts adds - SurePass validation (`AIV-001`), a duplicate check - is not applied to a converted Account unless it is added in Leads too | PF-1B: an Account create interface and an Opportunity create interface, which conversion calls inside its transaction; their rules and events stay in their modules |
| W2 | Opportunities: `repair_opportunity_account` (`opportunities/service.py:345`) | `business_party` (Accounts) | Opportunity Account repair (Slice 6B.1) inserts an Account through `accounts.repository` and records `AccountCreated` | The same Account create interface |
| W3 | Accounts: `insert_account_document_metadata` (`accounts/repository.py:867`), from `POST /api/accounts/{public_id}/documents` | `document_metadata` (Documents) | The Account documents route writes the Documents capability's table by its own SQL, with its own event (`AccountDocumentRecorded`), beside Documents' own upload; it reads the rows back the same way (`get_account_document_by_public_id`, `list_account_document_metadata`). A field Documents adds to its table - a checksum, version lineage, retention - is missed by Account documents unless Accounts adds it too | PF-1B: Account document capture goes through the Documents service |

## 2. Imports of another module's repository, or of a unit it does not declare as an interface

| From | Imports | Where (`464fb0a`) | Used for | Retired by |
| --- | --- | --- | --- | --- |
| Leads | `accounts.repository`: `active_account_status_exists`, `get_business_party_id_by_public_id`, `insert_business_party` | `leads/service.py:20` | W1 | W1 |
| Leads | `opportunities.repository`: `active_opportunity_status_exists`, `get_opportunity_by_source_lead_id`, `insert_opportunity` | `leads/service.py:70` | W1 | W1 |
| Opportunities | `accounts.repository`: `active_account_status_exists`, `get_business_party_by_public_id`, `get_business_party_id_by_public_id`, `insert_business_party` | `opportunities/service.py:16` | W2 | W2 |
| Commercial Offers | `accounts.repository`: `list_business_party_addresses`, `list_business_party_gstins` | `commercial_offers/service.py:235` (since CS-11, `commercial_offers/services/quote_documents.py`) | Reads: the Account's addresses and GSTINs offered on an offer | An Accounts query interface (PF-1B) |
| Eligibility | `identity.repository`: `list_active_roles` | `eligibility/alerts.py:73` | Reads: role names shown beside a reminder setting's audiences (`_role_labels`) | An Identity query interface; audiences by position come with `ORA-001` |

Five more import a module's pure rules - functions that touch no database - from a unit that module does not name as
its interface: Resource Assignments (`service.py:133`, `views.py:89`) and Resource Requirements (`service.py:110`) take
`work_orders.contract_period_rules`, and Work Orders (`holiday_rules.py:26`, `services/resulting_holidays.py:24`) takes
`holiday_calendar.rules`. They are coupling to code, not to data; retire them by naming those units in their owners'
contracts, or by re-exporting them through `contract.py` or `service.py`, when either module is next changed.

## 3. Reads of another module's tables by SQL (TB1-101)

183 reads, all `SELECT`, two of them taking a row lock (R3 and R4). With W3's insert and two reads of
`document_metadata`, they are the 186 cross-module accesses the scan counts at `464fb0a` (183 at `5e19123`; the three
added are CS-04 part 1's, in R3 and R4).

| # | Reader -> owner: table (reads) | What for | Retired by |
| --- | --- | --- | --- |
| R1 | Eleven modules -> Identity: `app_user` (83): Accounts 4, Commercial Offers 10, Eligibility 18, Equipment Reference 10, Holiday Calendar 3, Interactions 1, Leads 3, Opportunities 4, Resource Assignments 16, Resource Requirements 3, Work Orders 11 | The display name of who created, changed or decided a record, joined into its list and detail queries; Interactions' `app_user_exists` checks a participant is a real user | One Identity display-name lookup, which removes all 83 at once |
| R2 | Accounts, Commercial Offers, Leads, Opportunities -> Workflow: `workflow_status` (4) | `active_<record>_status_exists`: before a status is written, the code must be active in the status list | A Workflow query interface |
| R3 | Commercial Offers -> Accounts: `business_party` (9); Opportunities: `crm_opportunity` (10); Work Orders: `crm_work_order` (9), `crm_work_order_line` (1); Interactions: `interaction` (1); Terms and Conditions: `tc_clause_library` (4) | An offer's reads join its Account and Opportunity for context and names, and its Work Orders for lineage and the offer's lifecycle view; since CS-04 part 1, `list_offer_line_handoff` counts what Work Order lines hold of each offer line, for the lifecycle view's `line_handoff` (two of these reads); `lock_opportunity_row` **row-locks the parent Opportunity** while an offer is created (the one-active-Base-Offer rule, and no closing in between); `count_interactions_in_commercial_offer_chain` counts the conversations on the offer's chain; the T&C reads join the clause library. `list_related_commercial_offers_for_work_order`, one of these readers, is itself unused (TB1-905) | Query interfaces of Accounts, Opportunities, Work Orders, Interactions and the clause library (PF-1B); the lock with an Opportunity interface that takes it |
| R4 | Work Orders -> Commercial Offers: `crm_commercial_offer` (7), `crm_commercial_offer_line` (6), `commercial_offer_customer_response` (1); Accounts: `business_party` (4); Opportunities: `crm_opportunity` (3) | The handoff's context (`get_commercial_offer_handoff_context`), which since CS-04 part 1 also reads the offer's latest customer response, which must be the acceptance; `lock_commercial_offer_row` **row-locks the source offer** during the handoff; Work Order, line, billing-term and amendment reads join the source offer, its lines, Account and Opportunity for names, quantities and rates | A Commercial Offer query interface, **the handoff's reads and lock first** (HOF-2; TB1-103 item 8) |
| R5 | Leads -> Accounts: `business_party` (3); Opportunities: `crm_opportunity` (3) | A converted Lead's list and detail show the Account and Opportunity it became | Query interfaces of Accounts and Opportunities |
| R6 | Opportunities -> Accounts: `business_party` (4); Leads: `crm_lead` (3) | An Opportunity's list and detail show its Account and source Lead; Account repair reads its context | Query interfaces of Accounts and Leads |
| R7 | Reports -> `crm_lead`, `crm_opportunity`, `crm_commercial_offer` (6), `crm_work_order` (4), `business_party` (13 in all) | The dashboard's four reports: a read model, now with its contract and sources | `docs/agent/contracts/reports-contract.md`. A documented read model is allowed by ADR-017; what remains is its owners' notice of a change (the contract's "When a source changes") |
| R8 | Interactions -> Accounts: `business_party` (2), `business_party_contact` (1); Commercial Offers: `crm_commercial_offer` (1); Leads: `crm_lead` (3); Opportunities: `crm_opportunity` (3); Work Orders: `crm_work_order` (1) | **The recorded exception** (matrix, Interactions row): proving a link target exists (`linked_record_exists`), and Lead conversion lineage for inherited history (`get_account_source_lead_public_ids`, `get_opportunity_source_lead_public_id`). One read the matrix row does not name: `contact_exists`, which checks a participant is one of the Account's contacts | Already recorded; the contact check is recorded here |
| R9 | Eligibility -> Equipment Reference: `equipment_class` (4) | Rule rows join the class for its name and display order (`RULE_SELECT`) | An Equipment Reference read (Eligibility already calls its services for everything else) |

## 4. Database rules that read another module's tables

The scan above reads application SQL; these are trigger functions, read from the migration that creates them,
`20260908_0049_offer_line_quantity_handed_off_once.py` (CS-04 part 1, HOF-2). Each fires before a write to one
module's table and reads, or locks, the other's. They make the handoff's quantity and offer rules hold for any writer,
the application or not, as the handoff contract's dated amendment of 8 October 2026, approved by the owner, records.

**Permanent exceptions, approved by the owner on 9 October 2026** (pull request #108, review round 3), and recorded
as an exception to ADR-017 under it in `docs/agent/ARCHITECTURE_DECISIONS.md`, with the principle varied, the reason,
the alternatives, the consequences and the integration and security effects. Only the database can make a rule hold
for any writer, so these five stay in it: PF-1B does not retire them, and the handoff's move behind a Commercial Offer
interface (R4) leaves them in place. **Owner:** the Commercial Offer to Work Order handoff, which the CRM lane owns;
the rules change only when the handoff contract's rules do, by a dated amendment the project owner approves, each
change made in a migration and recorded here. They are looked at again only if the amendment's rules change or the
two modules are to be split into separate databases.

| # | Rule (trigger function), on | Reads of the other module's table | Basis |
| --- | --- | --- | --- |
| D1 | `crm_work_order_line_within_offer_quantity`, before a Work Order line is written or its offer line or quantity changes (Work Orders) | `crm_commercial_offer_line` (Commercial Offers): the offer line's `quantity`, **row-locked** (`FOR NO KEY UPDATE`), so two lines of one offer line queue | The amendment: an offer line's quantity goes onto Work Orders at most once in all. Permanent |
| D2 | `crm_commercial_offer_line_keeps_its_work_orders`, before an offer line's quantity or offer changes (Commercial Offers) | `crm_work_order_line` (Work Orders): what its Work Order lines hold, and whether any does | The same rule from the offer line's side: its quantity cannot go below what Work Orders hold, and a held line cannot move offer. Permanent |
| D3 | `crm_work_order_line_from_its_offer`, before a Work Order line is written or moved (Work Orders) | `crm_commercial_offer_line` (Commercial Offers): the offer line's offer, **row-locked** as D1 locks it | The amendment: a Work Order line comes from its own Work Order's offer. Permanent |
| D4 | `crm_work_order_not_from_change_quotation`, before a Work Order is written or moved to another offer (Work Orders) | `crm_commercial_offer` (Commercial Offers): the offer's `offer_purpose`, **share-locked**; on a move, `crm_commercial_offer_line` for its lines' offer | The amendment: no Work Order from a Change Quotation. Permanent |
| D5 | `crm_commercial_offer_keeps_its_work_orders_purpose`, before an offer's purpose changes (Commercial Offers) | `crm_work_order` (Work Orders): whether the offer has a Work Order | D4's rule from the offer's side. Permanent |

The same migration's customer-reference rule and its unique index (`crm_work_order_has_customer_reference`,
`ux_crm_work_order_customer_reference`) are on Work Orders' own table and read nothing else. Foreign keys between the
two modules' tables (for example `crm_work_order.commercial_offer_id`) are not in this register, as TB-1's scan does
not count them: each holds the other module's row identifier, as `CODING_STANDARDS.md` asks ("Use explicit foreign
keys"), and its check reads only whether the referenced row exists.

## The order TB-1 recommends

When each area is next changed, or in PF-1B, and before production: the handoff's reads and lock of the Commercial
Offer first (with HOF-2), then the display-name lookup (R1, one change for 83 reads), then the writers W1 to W3. An
optional architecture test over the scan's matrix would fail a new cross-module read or repository import (CS-07's
"Tests"); it is not built here.
