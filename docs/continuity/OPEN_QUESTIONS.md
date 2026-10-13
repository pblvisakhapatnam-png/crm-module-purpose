# Decisions and open questions

What PBL has decided, and what is still open. The records cite these by number (Q-01, D-02 ...). Do not invent a value
for anything still open; quote on the default in `docs/vendor/03_REMAINING_AND_DEFERRED_SCOPE.md`, group H, and say
so. When PBL answers a question you raise, the answer is recorded here.

## The CRM package (PBL, 12 and 13 October 2026)

| Decision | What PBL decided |
| --- | --- |
| Scope | The present package is the CRM. Equipment Hiring stays in the repository for context and regression, outside this package. The handoff between them is frozen; it changes only with PBL's written approval |
| Technology | Vendors continue this codebase on its present technology. A change is considered only for a compelling reason, and only when it is cheap and quick |
| Quoted now | An approvals facility; notifications inside the application; markup approval; quotation approval as a setting; messages about a record with a to-do list, inside the application; terms and conditions on each offer line with approval of a material change; the move of credit exposure from potential to firm at the Work Order; screen-level tests |
| Separately priced options | The shared request rules (PF-1B); email and SMS; background jobs; SharePoint for documents; organisation authority with the HR feed; single sign-on and two-step sign-in. Each is priced on its own line; PBL decides later whether and when to buy it |
| Later | Activating the customer in Finance at the first Work Order; a phone layout |
| Markup approval | Measured on each offer line: the quoted rate over the line's basis rate. An admin sets the threshold (for example 10%) and who approves. A line below the threshold sends the offer for approval before it goes out; so does a line with no basis rate, or with a basis rate in another currency. This answers Q-13 for now |
| Quotation approval | An admin setting: "no approval" or "one approver". With one, the admin picks a role or a person. The person who prepared a quotation never approves it |
| Messages about a record | Inside the application now; delivery by email, SMS or WhatsApp later |
| Choosing a line's basis rate (13 October) | Only Sales chooses the rate a line is priced on; Operations and Sales enter the market rates. Built in this package |
| One log of customer contact (13 October) | Lead follow-up activities merge into the conversation log, which already carries a next follow-up date; existing follow-ups move across. Built in this package |
| Customer templates, portal submissions, reverse auctions (13 October) | For now, an export of an offer in JSON or XML (or similar) serves all three; built in this package. Filling customers' templates automatically and connecting to portals come later |
| Credit exposure (13 October) | One separately priced line covering the whole control: each customer's approved credit amount and credit days; the check against them before an offer is sent, with a review date for offers that have no expiry; and the move from potential to firm exposure when a Work Order is created. An offer in USD, GBP or EUR goes for approval rather than being counted as rupees. PBL decides at award whether the line is in the first package |
| Approvers until the HR feed exists (13 October) | An administrator names the approver for each kind of approval - a role or a named person - and may change it at any time without a code change. Changes are recorded; approvals already given stand; waiting requests move to the new approver; disabling a user ends their approval rights; a screen lists who may approve what. A recorded exception to the rule that approval rights come from HR records, ending when the HR feed is bought (ADR-038) |
| Reverse auctions through customer portals (13 October) | A later package: pull auction enquiries from customer portals, choose which to quote, quote the usual way, send the rates back, with a target or maximum price per line (`docs/agent/DEFERRED_REQUIREMENTS.md`, "Reverse auctions through customer portals") |
| Hosting | PBL's own Microsoft Azure account, unless PBL accepts another cloud a vendor proposes. Once hosting is set up, moving it to another cloud is a change request. Vendors quote setting it up and handing it over, and monthly support separately |
| Database version | PostgreSQL 17 today. A vendor may propose a later version; it then carries out the move and proves it (PBL, 13 October 2026) |
| Users | Under 10 now, about 25 in two to three years, about 5 at the same time (`docs/vendor/10_HOSTING_USERS_AND_TARGETS.md`) |
| Backups | Continuous, kept for 30 days; a restore shown before go-live |
| Targets (13 October) | Design and test for 50 users, 10 at the same time; 95% of ordinary actions within 2 seconds at that load; 99.5% availability a month in India's working hours; no more than 15 minutes of data lost and back in service within 4 hours after a failure; a test environment beside production; Azure's managed PostgreSQL; monitoring that alerts the support contact (`docs/vendor/10_HOSTING_USERS_AND_TARGETS.md`) |
| The handoff (CS-04 part 2) | The offer's version on the Work Order, and the handed-off lines in the handoff event, built and recorded by the frozen contract's second amendment. A request key and a tracking id agreed for the shared request rules, not yet built |

## Identity validation, credit and currency

**Q-01 - Which actions need a verified identity?** *Decided, 11 August 2026.* None is blocked only because SurePass
is temporarily unavailable: the Account stays "pending", the outage and the retries are recorded, and work continues.
A failed check, an invalid PAN or GST number, or a mismatch SurePass returns is never treated as a pass; it is a
problem someone must put right (Q-02). If SurePass is unavailable for a long time, PBL sets up an authorized manual route, and its result and
evidence are recorded.

**Q-02 - Who puts right a problem found when a customer's PAN or GST number is checked?** *Decided, 11 August 2026.*
When the check with SurePass finds a problem - the number is invalid, the check fails, or the name or address SurePass
returns does not match what was entered - someone must look into it and put it right. That is Accounts by default;
authorized Sales staff may also be given the task. Who does it is a setting, not fixed in the code.

**Q-03 - Whose values win?** *Decided, 11 August 2026.* The legal name, registered address, PAN and GST details and
registration status that SurePass returns are authoritative over what was typed or what a customer's document says.
The original value and the mismatch are kept as evidence, never destroyed. If a customer's Work Order disagrees with
SurePass, the PAN is checked first; if it is right, the customer is asked for a corrected Work Order.

**Q-04 - How long the records of PAN and GST checks are kept, and checking customers again.** *Left open by PBL,
11 August 2026.* Two settings whose values PBL will choose later:

- how long the system keeps the record of each check - what SurePass returned, and any document copies. Data-protection
  law requires personal data to be kept no longer than needed, so this is a set period, not forever;
- whether, and how often, a customer's PAN and GST registration is checked again with SurePass, because a
  registration can later be cancelled or changed.

Until PBL fills them in, nothing is deleted and no customer is checked again automatically. The time to the next check
is counted from the date SurePass made the check, not the date the existing ERP system passed the answer on.

**Q-05 - Where approved credit lives.** *Decided, 11 August 2026 (closes D-01).* The CRM's Account, at legal-entity
(PAN) level, holds the approved credit amount and credit days, with their dates, status, approval and history, and
offers them to the modules that need them.

**Q-06 - Who approves credit.** *Decided, 11 August 2026; the values are settings.* The Department Head or the
Managing Director, as configured - never hard-coded. The approval record keeps who approved, their authority at the
time, the decision, when and any conditions; never a password. No "a second person must check" rule applies until
PBL configures one. An administrator may change the approver to another role or a named person at any time (PBL,
13 October 2026; ADR-038).

**Q-07 - Who may assess credit.** *Decided, 11 and 13 August 2026.* Someone holding the **credit assessor** authority
for the relevant scope. Sales Manager holds it by default; an authorized administrator may give it to, or take it from,
any eligible person without a code change. Being an administrator does not by itself make someone an assessor.
Preparing a credit proposal is open to the Sales roles; assessing it is not. There is no separate "Pre-Sales" role.

**Q-08 - Currency.** *Decided 12 August 2026; refined 4 October 2026.* INR is the default and the operating currency.
An offer or an amendment may be recorded in USD, GBP or EUR when chosen, and in nothing else. Never convert; never add
amounts in different currencies; reports total each currency separately. Credit exposure and billing terms stay in
INR (`AGENTS.md`, "Currency").

## Organisation authority

**Q-09 - Does the existing ERP system hold a stable employee number?** *Open; a question about the source, to be answered with whoever
maintains the existing ERP system.* Matters only for the HR feed option. The existing ERP system does not hold organisation units, positions or who holds
them; that is settled. Whether it holds a reliable employee number is not yet confirmed. The platform's own person
identifier does not depend on the answer.

**Q-10 - Who is the first authority-configuration administrator?** *Open; PBL's decision.* Someone must hold this role
before the authority engine can be configured. Matters only for the HR feed option.

## Raised during user testing

**Q-11 - Must people write what was said when they record a conversation?** *Open; PBL will decide from what testers
do.* When someone records a conversation with a customer - a call, a meeting, an email - the system asks for the
channel, the direction and when it happened, and offers a box for notes of what was said. Today the notes are optional.

**Q-12 - What happens when a document is deleted?** *Partly decided, 12 September 2026.* Deleting a document removes
the file; the record that it existed and was deleted stays. No reason is asked for now. Still open: whether a reason
should be required; who besides the uploader and an administrator may delete; whether a document an approved
quotation cites should be protected.

**Q-13 - Markup policy.** *Decided for now, 12 October 2026* - see "Markup approval" above. Still open: whether the
threshold should vary by machine type, customer or duration. Until PBL says so, there is one threshold.

**Q-14 - What each role sees.** *Open; PBL's decision; accepted for testing only.* Nothing limits a person to their own records today,
reports group by status but not by person, and Finance reads every CRM record. Before real customer data PBL must
decide what a person's "own records" are for each kind of record, which measures make up a salesperson's view, and
Finance's real scope.

## Decisions carried from the system-of-record matrix

| Decision | Position |
| --- | --- |
| D-01 Where approved credit lives | Decided by Q-05 |
| D-02 Credit exposure | The rule is decided: an offer line's value moves from potential to firm exposure, once, when its Work Order is created; partial and unawarded value is reconciled. The temporary "firm" figure is the allocated value of active Work Orders; the final figure is unbilled Work Order value plus what the customer owes, from the existing ERP system. Open: when to switch to the final figure, once the data is available |
| D-03 Representing a vendor's crew | Open (Equipment Hiring) |
| D-04 A purchase order before every hired-in machine | Open (Equipment Hiring) |
| D-05 SharePoint design | Decided by ADR-036: one site, one library per module, the application owns the content, people reach files only through the application. Retention is still open |
| D-06 Where the first draft invoice is made | Open (Equipment Hiring and Finance) |
| D-07 Applying a Work Order amendment | Open, deliberately later. Amendments are recorded and checked today, not applied |
