# 03 - What remains, and what is in this package

The records hold a long list of work not yet done, much of it for later or for other parts of the platform. This page
sorts the work that bears on the CRM, so that a fixed price covers this package and nothing more by accident.

| Group | What it means for your quotation |
| --- | --- |
| **A. Complete the CRM** | In this package. Quote it |
| **B. Ready for go-live** | In this package. Quote it |
| **C. Shared foundations - separately priced options** | Quote each as its own line. PBL decides later whether, and when, to buy each |
| **D. Early tidy-up** | Not required. Tell us in Phase 0 which you would do and why, and price each as its own line |
| **E. Later CRM work** | Not in this quotation |
| **F. Equipment Hiring** | Not in this package. It comes later, as its own package |
| **G. Later platform work** | Not in this quotation; a later package |
| **H. Waiting on a PBL decision** | PBL will decide. Where an item in A or B depends on one, quote on the default stated here and say so |
| **I. Waiting on an outside system** | You define what the CRM needs (doc 06); the outside party provides it |

Where you think an item belongs in a different group, tell us rather than choosing yourself. The source column names
the record that describes each item in detail.

## A. Complete the CRM - in this package

| Item | Source |
| --- | --- |
| **An approvals facility** used across the CRM: settings say who approves which decision; every decision is recorded with who made it and when; the approval stays visible for the later Work Order release. Until the HR feed (group C) is bought, an admin names the approver for each kind of approval - markup, quotation, credit assessment, credit approval, a material change to a clause - as a role or a named person, and may change it at any time without a code change. Every change is recorded; approvals already given stand; requests still waiting move to the new approver; disabling a user ends their approval rights; and a screen lists who may approve what | `docs/agent/contracts/approval-policy-contract.md` (APR-001); ADR-038 in `docs/agent/ARCHITECTURE_DECISIONS.md`; `docs/agent/DEFERRED_REQUIREMENTS.md`, "Commercial Offer approvals and submission" |
| **Markup approval.** Each offer line shows its markup: the quoted rate over the line's basis rate. An admin sets one threshold (for example 10%) and who approves. The offer goes for approval before it is sent when any line is below the threshold, has no basis rate, or has a basis rate in another currency | PBL's decision of 12 October 2026 (`docs/continuity/OPEN_QUESTIONS.md`, Q-13); `DEFERRED_REQUIREMENTS.md`, "Markup over the basis rate is not modelled at all" |
| **Quotation approval as a setting.** An admin chooses "no approval" or "one approver"; with one, the admin picks a role or a person. The person who prepared a quotation never approves it. (Today a Sales Manager approves quotations for issue, and may approve their own) | PBL's decision of 12 October 2026 (`OPEN_QUESTIONS.md`); `DEFERRED_REQUIREMENTS.md`, "Blocking generation of an unpriced or partly priced quotation" |
| **Notifications inside the application**: people are told when something needs them - an approval, a message, a review that is due | `DEFERRED_REQUIREMENTS.md`, "Messages about a record, and a to-do list"; `docs/agent/contracts/notification-delivery-contract.md` (NTF-001) |
| **Messages about a record, and a to-do list.** From any record, a person sends a note to a colleague; it lands in their to-do list, linked to the record; they mark it done and the sender sees that | `DEFERRED_REQUIREMENTS.md`, "Messages about a record, and a to-do list" |
| **Terms and conditions on each offer line**, as well as on the offer: clauses chosen from the library, copied into the offer and adjustable there; new clauses proposed; a material change to a clause approved; every change recorded | `DEFERRED_REQUIREMENTS.md`, "Terms and conditions"; `docs/agent/FUTURE_SLICES.md`, "6G.1"; `docs/agent/contracts/terms-and-conditions-contract.md` |
| **Credit exposure, priced as its own line.** The awarded value moves from "potential" to "firm" exposure when a Work Order is created, only for the lines handed off, and only once. That needs two things not yet built: the Account's approved credit amount and credit days, assessed and approved (ACP-001), and the check of exposure against that approved credit before an offer is sent - the Commercial Offer credit/exposure gate (CEX-001) - with a review date for sent offers that have no expiry date. An offer in USD, GBP or EUR goes for approval rather than being counted as rupees, since exposure is in rupees only. Price all of it on this one line: PBL decides at award whether it is in the first package | `docs/agent/contracts/credit-exposure-contract.md` (CEX-001); `docs/agent/contracts/account-credit-profile-contract.md` (ACP-001); `DEFERRED_REQUIREMENTS.md`, "Credit and exposure"; `OPEN_QUESTIONS.md`, Q-05 to Q-07, D-02 |
| **Only Sales chooses the rate a line is priced on.** Operations and Sales enter the market rates they collect; choosing which one a line is priced on becomes a separate right, given to the Sales roles only | PBL's decision of 13 October 2026 (`OPEN_QUESTIONS.md`); `DEFERRED_REQUIREMENTS.md`, "Entering a market rate and choosing the basis rate are one permission" |
| **One log of customer contact.** Lead follow-up activities merge into the conversation log, which already carries a next follow-up date; existing follow-ups move across with nothing lost | PBL's decision of 13 October 2026 (`OPEN_QUESTIONS.md`); `docs/agent/contracts/interaction-contract.md`, "Relationship to Lead Activities - two different records, deliberately" |
| **An export of an offer** in JSON or XML (or a similar format): an offer version's header and lines with quantities, rates, currency and terms, documented field by field, so that it can be used to fill a customer's template, upload to a portal, or enter rates in a reverse auction by hand | PBL's decision of 13 October 2026 (`OPEN_QUESTIONS.md`) |
| **Screen-level tests** for the web pages, which do not exist yet; with them, the checks they currently hold back | `DEFERRED_REQUIREMENTS.md`, "Frontend component-test capability" (TB1-700, CS-10, first part) |
| **The other items doc 02 marks A** - in Leads, Accounts, Opportunities, offers and customer responses | `docs/vendor/02_CRM_CAPABILITY_MATRIX.md` |

## B. Ready for go-live - in this package

| Item | Source |
| --- | --- |
| **Production hosting in PBL's Azure account**, or another cloud you propose and PBL accepts: setting it up and handing it over. Monthly support afterwards is quoted separately (doc 10) | PBL's decision of 12 October 2026; `docs/vendor/10_HOSTING_USERS_AND_TARGETS.md` |
| **The targets in doc 10** - speed, availability, backups with a restore shown before go-live, security, monitoring - with evidence that they are met | `docs/vendor/10_HOSTING_USERS_AND_TARGETS.md`; `docs/agent/architecture/NFR_BASELINE_AND_VERIFICATION.md` |
| **A safer sign-in**: the sign-in kept in a secure cookie rather than the browser's storage, with Sign out ending the session on the server; the shared session handling the screens need for it (TB1-700, CS-10, second part) | `DEFERRED_REQUIREMENTS.md`, "Sign-in: what TB-1 TB1-204 part a left" |
| **Lock-out and passwords**: one person cannot lock another out by typing wrong passwords; users set their own passwords; the session time-out is a setting | `DEFERRED_REQUIREMENTS.md`, "Sign-in: what TB-1 TB1-204 part a left" |
| **Who sees which records**, once PBL has decided it (group H) | `OPEN_QUESTIONS.md`, Q-14; `DEFERRED_REQUIREMENTS.md`, "Roles and what each person sees" |
| **Documents**: deleting one uploaded by mistake (the file goes, the record of it stays); safe kinds (PDF, images, text) open in the browser | `DEFERRED_REQUIREMENTS.md`, "Document deletion and in-browser viewing"; `OPEN_QUESTIONS.md`, Q-12 |
| **How long records are kept**, and a record of who read a conversation or downloaded a document, once PBL has set the periods (group H) | `DEFERRED_REQUIREMENTS.md`, "Interactions (Slice 9D)"; `NFR_BASELINE_AND_VERIFICATION.md` |
| **Managing users from the screens**: adding, changing and disabling users and their roles. Today a command-line tool does it | `backend/tooling/user_admin/`; `docs/continuity/TB1_204A_SIGN_IN_HARDENING.md` |
| **The corrections annex A marks B**: security settings (CS-08, N-03); the application's own log, with a reference support can trace (CS-09); protection against two people saving over each other's work outside offers, with a clear message instead of an error when two requests arrive together (CS-05b); a file and its record saved together (TB1-309); a health check that reaches the database (N-02); an event history that cannot be edited (N-05) | `docs/vendor/A_KNOWN_ISSUES.md` |
| **Supported versions** of the tools the system is built with: off versions that are out of support or have known security advisories, with every library version pinned (CS-15) | `docs/vendor/A_KNOWN_ISSUES.md` |
| **Upgrades proved on a database that holds data**, not only from empty, and migrations run as their own deployment step (CS-03, TB1-701) | `docs/vendor/A_KNOWN_ISSUES.md`; `db/notes/migration-rules.md` |
| **Ready to hand over**: user testing by role, support and administration guides, training material, a tested way back from a failed release, and a final tagged version with its remaining risks written down | `docs/agent/architecture/PRODUCTION_READINESS_GATES.md`, "Final production-candidate Definition of Done" |

## C. Shared foundations - separately priced options

| Option | What it is | Source |
| --- | --- | --- |
| **Shared request rules (PF-1B)** | One consistent form for error messages, with a reference support can trace; a tracking id linking each request to what it recorded; protection everywhere against a repeated request doing the work twice (the handoff's agreed rule, doc 05, among them); the screens reading errors one way; version numbers on the interface and the events; and the three places where CRM modules write each other's records. The records treat this as due before production; if PBL does not buy it before go-live, the exceptions it would close stay recorded, with new dates (annex A) | `docs/agent/architecture/MCF_ADOPTION_RECORD.md`; `docs/agent/contracts/shared-module-contract-foundation.md` (MCF-001); TB1-700, CS-10, third part |
| **Email and SMS** | Notifications also sent by email and SMS; in-app notification is in group A | `NTF-001`; doc 06 |
| **Background jobs** | A job runner for reminders (offer review dates, credit reviews), rechecks and heavy reports | `docs/agent/ARCHITECTURE_DECISIONS.md`, ADR-019 |
| **SharePoint for documents** | Files kept in PBL's SharePoint site behind the storage layer that exists today; staff reach them only through the application | ADR-036; `OPEN_QUESTIONS.md`, D-05; doc 06 |
| **Organisation authority and the HR feed** | Authorities such as credit assessor and credit approver given to people and positions from PBL's HR records, and suspended automatically when someone leaves or moves. The authority engine is built and dormant | `docs/agent/contracts/organization-authority-authorization-contract.md` (ORA-001); `docs/agent/pf-1a/`, `docs/agent/pf-1f-hr/`; `OPEN_QUESTIONS.md`, Q-09, Q-10 |
| **Single sign-on and two-step sign-in** | Signing in with PBL's company accounts, and a second step at sign-in | `DEFERRED_REQUIREMENTS.md`, "Sign-in: what TB-1 TB1-204 part a left"; `NFR_BASELINE_AND_VERIFICATION.md` |

## D. Early tidy-up - optional, priced separately

| Item | Source |
| --- | --- |
| Split the Commercial Offer page (about 6,000 lines) by tab, once screen-level tests exist | `docs/agent/UI_UX_CARRY_FORWARD.md`, "Page decomposition" |
| Move the remaining inline styles into the shared stylesheet, a whole page at a time | `UI_UX_CARRY_FORWARD.md`, "Equipment (ERT-1, September 2026)" (TB1-608) |
| Error messages on older pages that name the field at fault; a page error that does not blank the whole application | `UI_UX_CARRY_FORWARD.md`, "Server refusals" (TB1-801, TB1-603) |
| Small leftovers from offer versions: clearer "locked" messages, a tested list of the fields each status allows to change, the version shown on dashboard reports and amendment pages | `DEFERRED_REQUIREMENTS.md`, "Commercial Offer versions and legacy revisions" |
| A separate right to attach a file to an offer, which today comes with the right to record market rates (the basis-rate split is in group A) | `DEFERRED_REQUIREMENTS.md`, "Entering a market rate and choosing the basis rate are one permission" |
| Upload checks: refuse a file for a record that does not exist; refuse a caller without permission before the whole file arrives | `DEFERRED_REQUIREMENTS.md`, "Document upload - gaps carried from the upload package" |
| Conversation log: paging and filters on screen; record what changed on an edit; stop calling an empty note "content redacted" | `DEFERRED_REQUIREMENTS.md`, "Interactions (Slice 9D) - recorded parkable items" |
| Screen polish: a person picker for the Account owner (an ID is typed today); upload on the Lead and Opportunity pages; readable status labels; consistent Back links | `UI_UX_CARRY_FORWARD.md`, "Pilot screen review", "Document upload", "Navigation" |
| The other items in annex A marked D: database conventions (CS-16), unused code (CS-17), test gaps (CS-19), keeping earlier values of the offer and Opportunity value (CS-14) | `docs/vendor/A_KNOWN_ISSUES.md` |

Some of these will be needed anyway by work in A or B. Where one is, include it there and say so.

## E. Later CRM work - not in this quotation

A phone layout; comparing offer versions line by line; a quotation PDF made by the server (today the user prints the
frozen quotation from the browser); a rate master, rate benchmarking and historical rates from the existing ERP system; tender and BOQ
upload; GST calculation on offers; more reports (potential exposure, pending actions, export); splitting an offer line
across Work Orders by period, or cancelling a Work Order to free its quantity; capturing incoming email and WhatsApp;
company-information services; document versions; currency conversion; filling customers' own templates
automatically; connecting to customers' procurement portals. Sources: `DEFERRED_REQUIREMENTS.md` and
`FUTURE_SLICES.md`, "Business areas deliberately deferred".

**Reverse auctions through customer portals** are a later package. Many customers buy this way, and PBL means to take
part through the system: pull auction enquiries from customers' portals at a frequency PBL sets, choose which to
examine and pull their detail, quote through the usual offer process, and send the rates back to the portal - with a
target or maximum price on each offer line, since a bid must not exceed the auction's ceiling. Until then, the offer
export in group A serves. `DEFERRED_REQUIREMENTS.md`, "Reverse auctions through customer portals", has the detail;
we mention it so that what you build now does not stand in its way.

## F. Equipment Hiring - a later package

The Work Order after the handoff (its release, each line's site, billing terms and contract period, applying
amendments), and machines, their papers, allocation, the holiday calendar, crew, hired-in machines, log sheets,
billing, invoicing and collections. Much is built; none is in this package. Sources: `FUTURE_SLICES.md`, "7A" to "8H".

## G. Later platform work - later packages

Activating a customer in Finance at the first Work Order; invoices, receivables and profitability; and further parts
of the platform such as a fixed asset register, maintenance, procurement, inventory and transport.

## H. Waiting on a PBL decision

| Decision | Default to quote on | Source |
| --- | --- | --- |
| What each role sees, and what a person's "own records" are | Nothing limits a person to their own records, as today; quote the mechanism to narrow it | `OPEN_QUESTIONS.md`, Q-14 |
| How long identity evidence, conversations, documents and quotations are kept | A setting, with no period filled in | `OPEN_QUESTIONS.md`, Q-04; D-05 |
| Whether people must write notes of what was said when they record a conversation | Optional, as today | `OPEN_QUESTIONS.md`, Q-11 |
| Deleting a document: a reason? who may? protected once a quotation cites it? | Uploader and admin may delete; no reason asked | `OPEN_QUESTIONS.md`, Q-12 |
| Whether the markup threshold varies by machine type, customer or duration | One threshold | `OPEN_QUESTIONS.md`, Q-13 |
| Messages: who may message whom; due dates; replies or only "done" | Anyone to anyone; a due date optional; "done" only | `DEFERRED_REQUIREMENTS.md`, "Messages about a record, and a to-do list" |
| When "firm" exposure switches to its final figure (unbilled Work Order value plus amounts the customer owes) | The temporary figure the contract states | `OPEN_QUESTIONS.md`, D-02 |
| Support response times, growth beyond the design figures, and the data volumes your design assumes | Yours, stated in your proposal | `docs/vendor/10_HOSTING_USERS_AND_TARGETS.md` |

## I. Waiting on an outside system

| Item | Source |
| --- | --- |
| **PAN and GST validation through SurePass**, which PBL routes through the existing ERP system. The CRM side - verification states, an exception queue for Accounts, retries and an audited manual route for long outages - is priced as its own line, built against the interface you define (doc 06) | `docs/agent/contracts/account-identity-validation-contract.md` (AIV-001); `DEFERRED_REQUIREMENTS.md`, "Account legal identity validation"; `OPEN_QUESTIONS.md`, Q-01 to Q-04 |
| Amounts customers owe, from the existing ERP system, for the final "firm" exposure figure | `OPEN_QUESTIONS.md`, D-02 |
| Employee records for the HR feed, only if that option is bought | `OPEN_QUESTIONS.md`, Q-09; `docs/agent/pf-1f-hr/` |
