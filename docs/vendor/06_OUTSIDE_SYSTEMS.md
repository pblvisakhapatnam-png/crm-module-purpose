# 06 - Outside systems

Today the application connects to no outside system. Some information is typed in by hand, and Hiring imports one
file from the existing ERP system. This page says, for each outside system, what the CRM needs from it, what exists today and what is
in this package.

## How we work with outside systems

**You will not have access to the inside of the existing ERP system or any other outside system.** Where the CRM needs something from
one, you write down exactly what it needs - an interface definition - and PBL arranges for it to be provided, through
whoever maintains that system. Please do not plan work that assumes direct access to another system's database.

An interface definition covers:

| Item | The question it answers |
| --- | --- |
| Business purpose | Why the CRM needs this, in plain words |
| Source of truth | Which system owns the information |
| Fields | Each field, its type and whether it is required |
| Identifiers | How a record is identified on each side, and how the two are matched |
| Filters | How the CRM asks for the records it needs |
| Changes over time | How changes reach the CRM, and "as of when" a value is |
| Examples | Sample requests and answers |
| Missing values and errors | What happens when a value is empty, wrong, or the system is down |
| Duplicates | How a repeated or duplicated record is recognised |
| Security | How each side proves who it is |
| Time limits and retries | How long to wait, how often to retry |
| Reconciliation | How the two sides check that they agree |

The rules for the code side are in doc 04, "Outside systems": each system has its own adapter, so replacing a
provider later is contained to that adapter. Contained is not the same as free; it means the rest of the system does
not change.

## System by system

| System | What the CRM needs it for | Today | In this package |
| --- | --- | --- | --- |
| **SurePass**, through the existing ERP system | Checking each Account's PAN and GST numbers, with people dealing only with the exceptions (AIV-001). PBL has chosen to route these checks through the existing ERP system first, which provides an interface to PBL's definition; a direct connection may follow later | Nothing. Numbers are checked for format, and Finance marks them verified by hand | Yes, priced as its own line: write the interface definition, and build the CRM side - verification states, the exception queue, retries, and an audited manual route for long outages (doc 03, group I) |
| **Existing ERP system - customers** | Activating the customer in Finance at the first Work Order: find it by PAN and GST number, reuse it or create it, with Finance's approval before release (CMA-001) | Nothing | No - later (doc 03, group G) |
| **Existing ERP system - amounts customers owe** | The final figure for "firm" credit exposure: unbilled Work Order value plus what the customer owes | Nothing | No - waits on decision D-02. The temporary figure the contract states does not need it |
| **Existing ERP system - historical rates** | Past rates as evidence when pricing a line | Typed in by hand as a kind of pricing evidence | No - an automatic import is later (group E) |
| **Existing ERP system - employees** | Who holds which position, for business authority such as credit approval | An interface definition inside the code, with no connection behind it; PBL plans a governed list in SharePoint alongside the existing ERP system's employee records | Only if the HR feed option is bought (group C) |
| **Existing ERP system - equipment** | Hiring only: PBL's machines and their papers | A file import (Hiring) | No |
| **SharePoint** (Microsoft 365) | Keeping documents, quotations and media: one PBL site, one library per module, reached only through the application (ADR-036) | A local-disk store behind a storage layer built to take SharePoint | Separately priced option (group C) |
| **Email** | Sending notifications and, later, quotations; logging emails as conversations | Email can be recorded as a conversation's channel, typed in by hand; nothing sends or receives | Sending notifications: separately priced option (group C). Capturing incoming email: later (group E) |
| **SMS** | Reminders and notifications | Can be recorded as a conversation's channel, typed in by hand; nothing sends | Separately priced option (group C) |
| **WhatsApp** | Logging WhatsApp conversations; a source of Leads | Can be recorded as a channel, typed in by hand | Later (group E) |
| **Customers' procurement and auction portals** | Submitting offers; taking part in reverse auctions | An offer records that it was submitted through a portal, with proof attached; nothing connects | The offer export only (group A). Connecting to portals, and reverse auctions through them, come later (doc 03, group E) |
| **Company and tender information services** (for example Probe42, D&B, Tender Tiger, Projects Today) | Leads and market information | Nothing | Later (group E) |
| **Call-logging services** | Logging calls as conversations | Their names exist only as a conversation's source-system values | Later (group E) |
| **GPS providers** (for example FleetX) | Not a CRM need; transport tracking and, for Hiring, checking log sheets | Nothing | No |
| **GitHub** | The automatic checks | In use | Unchanged |
| **Microsoft Azure** | Production hosting, unless PBL accepts another cloud you propose (doc 10) | Not yet set up | Yes: setting it up and handing it over (doc 10) |

## Where the detail is

| Record | What it holds |
| --- | --- |
| `docs/agent/architecture/EXTERNAL_DEPENDENCY_REGISTER.md` | Each outside system's readiness, owner and fallback |
| `docs/agent/contracts/account-identity-validation-contract.md` | What PAN and GST validation must do, including outages and mismatches |
| `docs/agent/DEFERRED_REQUIREMENTS.md`, "The route: relay through Plum first" | Why SurePass is routed through the existing ERP system first, and what that needs |
| `docs/agent/contracts/customer-master-activation-contract.md` | Activating a customer at the first Work Order |
| `docs/agent/contracts/notification-delivery-contract.md` | Notifications by any channel |
| ADR-036 in `docs/agent/ARCHITECTURE_DECISIONS.md` | SharePoint as the document store |
| `docs/continuity/OPEN_QUESTIONS.md`, Q-01 to Q-04 | PBL's decisions on identity validation |
