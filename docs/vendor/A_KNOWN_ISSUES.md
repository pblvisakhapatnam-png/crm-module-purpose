# Annex A - Known issues

In October 2026 a full technical review of the code - called TB-1 - recorded 79 findings (IDs `TB1-nnn`) and grouped
the corrections into packages (IDs `CS-nn`). The most urgent are corrected. This annex lists what is still open, so
that you see the code as it is, and so that an ID you meet in a code comment can be looked up here.

Not all of it is this package's work. The last column gives each item's group in doc 03: **A** or **B** in this
package, **C** a separately priced option, **D** optional tidy-up, **F** Equipment Hiring. If you believe an item must
be corrected before production and it is not marked A or B, tell us why; that is exactly the kind of view we want from
Phase 0.

TB-1 rated each finding: **Critical** (correct before anything else), **Material** (correct before relying on it),
**Scheduled** (correct in planned work), **Advisory** (worth doing) or **Evidence required** (needs measuring).

## Correction packages still open

| ID | What is still open | Findings | Area | Rating | Group |
| --- | --- | --- | --- | --- | --- |
| CS-03 | No test upgrades a database that already holds data; migrations are proved only from empty. For production, running migrations as their own deployment step rather than when the server starts | TB1-701 | Platform | Scheduled | B |
| CS-04 (rest) | A repeated handoff request should get back the Work Order it made (today it is refused), and the handoff's events should carry a tracking id. Both agreed in the frozen contract's second amendment (doc 05) | TB1-103 part a | CRM and Hiring | Material | C (PF-1B) |
| CS-05b | Accounts, Leads, Opportunities, Work Order amendments and conversation records have no check against an out-of-date save, so the last save silently wins (offers have it). Two requests at the same moment can cause a server error instead of a clear refusal on a GST number, PAN, Lead conversion or amendment reference | TB1-303, TB1-304, TB1-506 | CRM | Material | B |
| CS-06 | The shared request rules: one error format, a tracking id on every request, one retry rule for every command (the CRM's creates and the handoff have none), event naming and versions, a test that fails when a change records no event | TB1-102, TB1-305, TB1-501, TB1-607, TB1-702, TB1-1000 | Platform | Material | C (PF-1B) |
| CS-07 | Three CRM commands write another module's tables; five modules import another module's data layer; many reads use other modules' tables directly. All recorded (below); to move behind the owning module's interface | TB1-100, TB1-101 | Mostly CRM | Material | C (PF-1B) |
| CS-08 | Two diagnostic addresses answer without sign-in; the allowed browser origin is a fixed development address; the application does not send the "nosniff" security header itself; the sign-in token sits in the browser's storage; signing out does not end the session on the server | TB1-204, TB1-205, TB1-207 | Platform | Critical (as a group) | B |
| CS-09 | The application keeps no log of its own, has no request reference, logs other unexpected errors as raw tracebacks, does not log slow database statements, and six places swallow a failure without a trace | TB1-310, TB1-504 | Platform | Advisory to Scheduled | B |
| CS-10 | Older pages keep their own session code (29 files read the token); screens decide what to offer from copied role lists, not from permissions; few pages use the shared error reader; no screen-level tests; the Commercial Offer page is one very large component | TB1-603, TB1-804, TB1-602, TB1-1002, TB1-1003, TB1-700 | Mainly CRM screens | Scheduled | A (tests), B (session), C (error reader), D (the rest) |
| CS-13 | Nothing has been measured at production volume. Fifteen or more simultaneous quotation listings may exhaust the database connections; Hiring's allocation lists make many queries per row | TB1-403, TB1-406 | CRM and Hiring | Evidence required | B (CRM part) |
| CS-14 | Replaced or deleted values are not kept: on the CRM side the offer value and an Opportunity's estimated value; a record's event history is shown only as its latest 100 events, and no screen shows it | TB1-308, TB1-507, TB1-502 | CRM and Hiring | Scheduled | D (CRM part), F |
| CS-15 | The screens' build uses Node.js 20, out of support since 30 April 2026; no lock file for indirect Python packages; the test tool ships in the running image; FastAPI and Starlette need upgrading, which clears two known Starlette advisories reachable through the upload routes | TB1-200, TB1-900, TB1-901 | Platform | Material | B |
| CS-16 | 56 older CRM timestamps have no time zone (they hold UTC by agreement); the database does not check eight status columns; the CO- and WO- number generator wraps at 1,000,000. Accounts, Leads and Opportunities have no business reference number, by an approved exception to ADR-007 | TB1-401, TB1-402 | CRM | Scheduled | D |
| CS-17 | Seven unused names in Work Orders and Commercial Offers; an unused connection point for the existing ERP system's machine data, kept on purpose for now | TB1-905, TB1-610 | CRM and Hiring | Advisory | D |
| CS-19 | Test gaps: the route guard does not pin the five conversation routes' permissions; ten permission-guarded routes have no "forbidden" test; changing or removing a proposed amendment line has no test; eight refusals are never exercised | TB1-201, TB1-703, TB1-704, TB1-1001 | CRM and Hiring | Scheduled | D |

## Single findings still open

| ID | What is open | Area | Rating | Group |
| --- | --- | --- | --- | --- |
| TB1-106 | The organisation-authority engine is dormant until approvals use it, and its code does not say so | Platform | Advisory | D |
| TB1-108, TB1-206 | One permission both records and decides Work Order amendments; splitting it waits for decision D-07 or the approvals facility | Work Orders | Advisory | F |
| TB1-109 | Machine eligibility counts a part as checked with its machine because the part came from the existing ERP system | Hiring | Scheduled | F |
| TB1-302 | A closed Lead can be reopened; an Opportunity can be marked lost while its offer or Work Order is live; Lead conversion reads without a lock | CRM | Scheduled | A |
| TB1-306 | Replacing a machine does not check the unit against the units required; the page only warns | Hiring | Advisory | F |
| TB1-309 | A stored file and its record are written in two steps, so a crash can leave a file with no record | Documents | Scheduled | B |
| TB1-311 | A Lead whose company name is 244 characters or more fails to convert with a server error | CRM | Scheduled | A |
| TB1-803 | Some server features have no screen (correcting a Work Order amendment; closing an equipment value rule); the conversation form sends no request key | CRM and Hiring | Scheduled | D, C |

## Notes for before production

| ID | Note | Group |
| --- | --- | --- |
| N-02 | No health check reaches the database through the application | B |
| N-03 | No Content-Security-Policy header | B |
| N-04 | The screens' main script file is over 1 MB | D |
| N-05 | The business event table is append-only by agreement, not enforced | B |
| N-09 | Some foreign keys have no index | D |

## Exceptions to the shared module rules (MCF-001)

Recorded in `docs/agent/architecture/MCF_ADOPTION_RECORD.md`; each is to be retired by the shared request rules
(group C, PF-1B).

| Rule | Exception | Area |
| --- | --- | --- |
| G1 | Only the conversation log states an interface version | Platform |
| G2 | Two diagnostic addresses need no sign-in (CS-08) | Platform |
| G3 | Only the conversation log carries a tracking id | Platform |
| G4 | No retry key on Accounts, Leads, Opportunities, Commercial Offers, Work Orders (the handoff included) and Documents; some on the Hiring modules | CRM; Hiring |
| G5 | No module returns the structured error format; the conversation log's exception is recorded in its contract | Platform |
| G6 | Only Documents and the conversation log version their events; some Hiring events are named in a different style | CRM and Hiring |
| G7 | Accounts, Leads and Opportunities write other modules' tables (W1 to W3) | CRM |

## Recorded crossings of module boundaries

Recorded in `docs/agent/architecture/BOUNDARY_EXCEPTION_REGISTER.md`. Each is known and allowed for now; a change that
adds one adds its row.

| ID | Crossing | Area |
| --- | --- | --- |
| W1 | Lead conversion writes the Account and the Opportunity itself | CRM |
| W2 | Repairing an Opportunity's Account link writes an Account | CRM |
| W3 | The Account documents route writes the Documents table directly | CRM |
| Imports | Leads uses Accounts' and Opportunities' data layer; Opportunities and Commercial Offers use Accounts'; Eligibility uses Identity's | CRM; Hiring |
| Rules | Two Hiring modules use Work Orders' contract-period rules; Work Orders uses the holiday calendar's rules | Hiring |
| R1-R9 | Reads of other modules' tables: user names for display; status lists; Commercial Offers reading Accounts, Opportunities, Work Orders, conversations and terms; the handoff reading the offer, Account and Opportunity; Leads and Opportunities reading each other and Accounts; Reports (an allowed read model); the conversation log's link checks; Eligibility reading equipment classes | CRM; Hiring |
| D1-D5 | Five database rules of the handoff read the other side's tables: a permanent, approved exception, owned with the handoff | CRM and Hiring |

## Already corrected

CS-01, CS-02, CS-05a, CS-05c, CS-11, CS-12 and CS-18 are complete, with the emergency corrections TB-1 asked for. The
handoff's version and line details (CS-04 part 2, items c and d) were completed on 12 October 2026.
