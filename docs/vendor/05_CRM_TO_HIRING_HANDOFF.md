# 05 - The handoff from CRM to Equipment Hiring

The handoff is the moment an awarded offer becomes a Work Order. It is the one place where the CRM and Equipment
Hiring meet, and both sides build on it, so it is **frozen**: you may read it and test it, and change it only with
PBL's written approval.

## What happens at the handoff

A user with the right permission (Admin, Sales User, Sales Manager or Operations User) opens an awarded offer and creates a Work
Order from it. The system checks, and refuses with a clear message beside the button when any check fails:

| Rule | In plain words |
| --- | --- |
| **Only an accepted offer** | The offer's status must be Accepted |
| **Only a Base or Supplementary Offer** | A Change Quotation never makes a Work Order: it changes work already ordered, and is recorded on a Work Order amendment instead. A Supplementary Offer may make its own Work Order or be recorded as an amendment - the business chooses each time |
| **The latest answer must be the award** | If, after the award, the customer's latest response is "on hold", a clarification or anything else, the offer waits until an award is recorded again |
| **The customer's order reference is required** | Every Work Order carries the customer's Work Order or Letter of Intent number. One offer never has two Work Orders with the same number. A Create pressed twice, a second tab, or two people at once all carry the same number, so the repeat is refused and the message names the Work Order that already has it |
| **Each awarded quantity is handed off once** | An offer line may go onto one Work Order whole, or be split across several by quantity (4 cranes as 3 and 1). Together they never hold more than the line's quantity. A request for more than is left is refused, naming the Work Orders that hold it |
| **Amounts split exactly** | A part of a line takes the line's amount up to the end of the part less its amount up to its start, rounded to the paisa, so the parts add up to the line exactly |
| **No "lost" after a handoff** | While an offer has a Work Order, its customer response cannot be recorded as lost, because a Work Order cannot be cancelled yet |
| **Traceability is kept** | Every Work Order line keeps the identity of the offer line it came from. The Work Order pages show the offer and its version ("CO-000123 v2"), and a Work Order from a later version is titled with it ("Work Order from CO-000123 v2") |
| **Versions** | Only the version the customer accepted can be handed off. A version replaced by a later one that was sent is refused. A later version abandoned before it was sent replaces nothing, so the one before it is still the live version |

The database itself enforces the quantity, reference, Change Quotation and same-offer rules, so they hold even if two
requests arrive at the same moment.

A new Work Order starts as **"Awaiting release to Ops"** (`HANDOFF_CREATED`). It is a shell: it is not released, no
customer is activated in Finance, and no machine or crew is committed. Those steps belong to Hiring and come later.

## What the handoff records

Two business events, written together with the Work Order:

- **`WorkOrderCreated`**, and
- **`CommercialOfferConvertedToWorkOrder`**, which lists each line handed off: the offer line, the Work Order line made
  from it, its quantity, unit, currency and amount. This is the record that credit exposure will count from when the
  awarded value moves from "potential" to "firm" (doc 03). Both events carry the offer's version.

A refused request writes nothing.

## Agreed for later

PBL has already approved how two further rules will work, as part of the shared request rules (the PF-1B work, a
separately priced option in doc 03):

- **A request key.** A request repeated with the same key will be answered with the Work Order it made, instead of
  being refused. Until then, a repeat is refused by its customer reference, as above.
- **A tracking id** (correlation id). One id per handoff, carried on both events, so related records can be traced together.

## Where the code and the frozen text differ

The frozen text was written before the code. These differences are known, allowed or harmless, and recorded so that
nobody mistakes the frozen text for what the code does (`docs/agent/contracts/work-order-contract.md`, "Where the
runtime differs from the frozen contract's text"):

- some header fields the frozen text lists for a later production stage are not passed (customer name and PAN, offer
  mode, award reference and date, document and credit references); the frozen text allows a thinner first version;
- each Work Order line starts with the Work Order's starting status (`HANDOFF_CREATED`) rather than copying the
  offer line's;
- the Account is taken from the offer, or else from its Opportunity, without checking that the two agree;
- an offer line in USD, GBP or EUR is copied in that currency, while Hiring's billing terms are in rupees only;
- the example data under `docs/agent/fixtures/accepted-offer-work-order/` predates both amendments and is illustrative
  only.

## What the CRM may change on its own

Anything that does not change what reaches the handoff, for example:

- screens, wording and layout of the offer and Create Work Order pages;
- offer-side rules that apply before an offer is accepted (approvals, checks before submission, terms);
- reports and views that read Work Orders without writing them;
- new information on the offer that the handoff does not pass on.

## What needs a contract change, and PBL's approval

Anything that changes what the handoff takes, checks, produces or records, for example:

- which offers may be handed off, or when;
- the fields the request takes or the Work Order it returns;
- the quantity, amount or reference rules;
- the two events or what they carry;
- the starting status of a Work Order.

A change is made by a dated amendment added at the end of the frozen contract, approved by PBL. Nothing above it is
edited. The change record lists the changed rule, the reason, the effect on CRM and Hiring, the effect on the
interface, the database and the events, the effect on user testing, and who approved it. The contract's fingerprint
(SHA-256) before and after each amendment is recorded in `docs/continuity/NEXT_STEPS.md`; check it before and after
any work near the handoff.

## The records

| Record | What it holds |
| --- | --- |
| `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` | The frozen contract, with its two dated amendments (8 and 12 October 2026) at the end |
| `docs/agent/contracts/work-order-contract.md` | The Work Order as built, including the runtime differences above |
| `docs/continuity/TB1_103_WORK_ORDER_HANDOFF_ONCE_PER_LINE.md` | Why the "handed off once" rules exist, and the checks to run before upgrading a database that already holds data |
| `docs/planning/ACCEPTED_OFFER_TO_WORK_ORDER_PAYLOAD_SPEC.md`, `docs/planning/CRM_HIRING_PARALLEL_AGENT_CONTRACT.md` | Earlier planning copies the change rule still names; the contract is the authority |
| `backend/app/modules/work_orders/services/handoff.py` | The code |
| `backend/tests/test_cs04_handoff_once_per_line.py` and the Work Order tests | The tests that prove the rules |
