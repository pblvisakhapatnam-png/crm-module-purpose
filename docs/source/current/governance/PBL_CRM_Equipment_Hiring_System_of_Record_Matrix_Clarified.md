# CRM + Equipment Hiring System-of-Record Matrix

**PBL Transport Corporation Pvt. Ltd.**  
**Clarified working draft for review**

> [!IMPORTANT]
> ## Status and authority of this document
>
> This document records the current preferred direction for system-of-record ownership, business accountability, control boundaries, data sources, evidence and integration responsibilities. It is a **directional reference and current working design**, not a binding prescription for database tables, code structure, screens, API routes, services, workflows or other implementation details.
>
> During detailed design or implementation of a module, sub-module or slice, the developer or agent may adopt a different approach where it is demonstrably clearer, safer, simpler, more maintainable, more extensible or better suited to the actual business requirement. The better approach should be chosen when it preserves or improves the intended business outcome, authorization, segregation of duties, auditability, traceability, security, non-functional requirements and cross-module compatibility.
>
> A deviation must not be made silently. The slice or design record must identify the suggestion being departed from, the alternative selected, why it is better, and the effect on contracts, modules, data, migrations, events, security and tests. Human approval is required before changing an approved business rule, mandatory control, frozen contract, accepted architecture decision or explicit current instruction.
>
> When this document conflicts with a later approved decision or frozen contract, the later approved decision or frozen contract takes precedence. Historical records should remain unchanged and should be treated as evidence of the earlier position. Entries marked as a working assumption or decision pending are not final prescriptions.

> [!WARNING]
> ## Entries superseded by a later approved decision
>
> The entries listed below are preserved verbatim in this document as evidence of the earlier position, in line with the rule above. They no longer state the current approved direction. Read them together with `docs/agent/ARCHITECTURE_DECISIONS.md` (ADR-014, ADR-015 and ADR-023 through ADR-027), `docs/continuity/ACCOUNT_IDENTITY_VALIDATION_CORRECTION_2026-08-11.md` and `docs/continuity/OPEN_QUESTIONS.md`, which record the reconciliation in full.
>
> Superseded on 11 August 2026:
>
> 1. **Section 3, ownership principle** — "Finance owns legal, statutory, **credit**, customer-activation, invoicing, receivable and accounting controls." Still correct for statutory, customer-activation, invoicing, receivable and accounting controls. Superseded for *legal identity at Account onboarding* (now established by integration-driven SurePass validation, with Finance as consumer rather than approver) and for *credit assessment/approval* (`SALES_MANAGER` assesses; the configured Department Head or Managing Director approves).
> 2. **Section 5, "Account legal identity reference" row** — "Finance verifies and approves PAN, legal name and statutory identity" and "Legal identity fields must be Finance-controlled". Superseded: PAN/GSTIN are validated through SurePass, initiated by Sales (`SALES_USER` / `SALES_MANAGER`) at Account creation. No routine manual Finance approval is required to reconfirm a successfully validated identity; human review is exception-driven only.
> 3. **Section 4 "Prospect credit profile" and Section 6 "Credit profile" rows** — primary business owner "Finance - Credit Control". Superseded in respect of the *assessment*, which sits with `SALES_MANAGER`, and approval authority, which is configurable and currently the applicable Department Head or Managing Director. Consumption and monitoring of actual financial exposure against approved credit remains a Finance/Accounts concern.
> 4. **Section 16, decision D-01 — Credit profile authority.** Resolved by PBL on 11 August 2026 and clarified by ADR-025: the CRM Account Master's legal-entity/PAN-level credit profile is authoritative for approved Credit Amount and Credit Days. Sales prepares the proposal, `SALES_MANAGER` performs the assessment, and the configured Department Head or Managing Director makes the authenticated approval decision. The original D-01 row remains below as historical evidence of the question that was resolved.
>
> Resolved or narrowed on 12 August 2026:
>
> 5. **Section 16, decision D-02 — Target exposure formula and cutover.** ADR-024 defines the settled allocation rule: creating a Work Order shell transfers only its selected-line value from Potential to Firm; a live remainder stays Potential and an explicitly unawarded remainder leaves exposure. Temporary Firm Exposure is allocated active Work Order shell/Work Order value; target Firm Exposure is unbilled effective Work Order value plus outstanding receivables from Plum. Only target-formula cutover readiness remains open and depends on reliable, reconciled Plum/Work Order data.
> 6. **Currency for current CRM/Hiring operations.** All current sales, hiring, customer billing, vendor hire and other operating amounts use INR. Multi-currency is deferred until overseas customer business enters scope. Purchases of assets and spares are the present exception and remain part of their future Purchase/Finance design.
> 7. **Submitted offer/tender with no expiry or response.** ADR-027 requires either an explicit `valid_until` or a mandatory system-calculated exposure review date. Overdue unresolved value remains Potential and holds new exposure decisions for the Account until Sales confirms it remains live or records the final/not-awarded outcome; it neither consumes headroom silently without review nor drops to zero automatically.
>
> Clarified on 13 August 2026:
>
> 8. **Credit assessment authority.** Bullets 1, 3 and 4 above, and the original matrix rows they refer to, are preserved unchanged. Their references to `SALES_MANAGER` assessing credit represent the initial/default mapping, not the authorization rule. The current rule is the configurable `CREDIT_ASSESSOR` business authority: the assessment may be performed only by an authenticated user holding a current, active `CREDIT_ASSESSOR` assignment for the relevant organizational/data scope, resolved through `ORA-001`. Authorized administrators may assign, suspend, revoke or reassign that authority without a code change. Preparing a credit proposal remains a Sales activity and is not the assessment. Credit approval remains separate and unchanged under `CREDIT_APPROVER`, currently the configured Department Head or Managing Director. See `ADR-015` (amended 13 August 2026), `ACP-001`, `ORA-001` and `docs/continuity/OPEN_QUESTIONS.md` Q-07.
>
> Not affected: Customer Master activation remains Finance-approved before Work Order release/posting; GSTN and billing identity used for statutory invoicing remain Finance-controlled; PAN-level credit governance, the Potential/Firm Exposure distinction and all document, integration, audit and security ownership entries are unchanged.
>
> The companion `.docx` in this folder has not been altered and therefore does not carry this notice. Where the two differ, this notice and the ADRs it points to state the current position.

---

This version separates the authoritative system from the business owner, supporting roles, source data and evidence repository. It incorporates the current CRM design, the CRM-to-Hiring handoff, the planned Hiring execution model, billing boundaries, vendor-hire treatment and document governance.

| **Item**          | **Detail**                                                                                                                                         |
|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| Document status   | Working draft for PBL and implementation-partner review                                                                                            |
| Scope             | CRM, Commercial Offer, Work Order handoff, Equipment Hiring, billing, vendor hire, Finance interfaces, documents, integration, reporting and audit |
| Primary objective | Identify one authoritative record and one accountable business owner for each important data area                                                  |
| Source basis      | Reworked from the earlier System-of-Record Matrix and updated using the current CRM prototype decisions and Hiring design direction                |

**PRIVATE & CONFIDENTIAL**

# 1. Purpose and status of this matrix

This matrix identifies the authoritative system and record for each important CRM, Commercial Offer, Work Order, Equipment Hiring, billing, vendor-hire and Finance-related data area. A record may be displayed in several screens and consumed by several functions, but the controlled value must be maintained in one authoritative place.

The matrix is a logical ownership and control document. It does not prescribe internal table names, source-code structure or a particular implementation language. It should be used to guide field mapping, API and event contracts, role permissions, document linkage, data migration, testing and future UAT.

**Important:** This document states the intended target ownership model. It is not an implementation-status report. Where a current PBL/Plum practice remains to be confirmed, the decision is identified explicitly in Section 16.

# 2. How to read the matrix

| **Term**                              | **Meaning**                                                                                                                                                                                                   |
|---------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Record / data area                    | The business record, decision, calculation, evidence item or controlled group of fields being discussed.                                                                                                      |
| Authoritative system and module       | The application and module that maintains the controlled business record. The format 'System - Module' denotes hierarchy, not joint ownership.                                                                |
| Primary business owner                | The one accountable PBL function and role that owns the record's correctness, lifecycle and policy. The entry uses the format 'Function - Role', for example 'Sales - Commercial Offer Owner'.                |
| Supporting roles / approval authority | Roles that provide data, review, advise, approve or act on the record without becoming its primary owner. Each role is written separately and its responsibility is stated.                                   |
| Main consumers                        | Modules, functions, reports or external processes that read or use the record.                                                                                                                                |
| Primary source / evidence repository  | Where the original input, master data, raw feed or supporting file comes from. A source or repository is not automatically the system of record.                                                              |
| Key controls and ownership rules      | Mandatory rules needed to prevent duplicate, inconsistent, unauthorized or unauditable changes.                                                                                                               |
| Function - Role naming convention     | A hyphen identifies a role within a function. 'Sales - Commercial Offer Owner' means the Sales role accountable for preparing and controlling a specific Commercial Offer; it does not mean two joint owners. |
| Designated policy owner               | This means one named PBL role must be nominated before the matrix is final. For T&C governance, the default working assumption is the Commercial Head unless PBL assigns another role.                        |
| Use of separators                     | A slash is not used to express ownership. Separate responsibilities are written as complete role names and are placed in either the Primary Business Owner or Supporting / Approval Roles column.             |

# 3. System-of-record principles

- Each business record must have one authoritative system and one primary business owner expressed as one accountable role in the format 'Function - Role'.

- A shared screen may contain fields controlled by different functions. The record still has one primary owner; each controlled field must separately identify its data owner or approval authority.

- A source system, evidence repository and system of record are different concepts. Raw data may originate in one system, be reviewed in another and be stored as a controlled business value in the authoritative module.

- Structured business data, document metadata and the file binary are separate records. The ERP must retain the business link, document type, version, status, hash or integrity evidence, access group and retention metadata even when the file is stored in SharePoint or another repository.

- Transaction snapshots must preserve the values used at the time of approval, submission, assignment, billing or handoff even if the source master changes later.

- Sales owns the commercial relationship and opportunity process. Finance owns legal, statutory, credit, customer-activation, invoicing, receivable and accounting controls.

- A Qualified Prospect / Account is the long-lived commercial relationship record. Each RFQ, enquiry, tender or customer requirement is a separate Opportunity.

- Customer Master activation occurs when the first Work Order is received and must be Finance-approved before Work Order release/posting and invoicing.

- Credit is controlled at PAN/legal-entity level. Credit Amount and Credit Days are separate controlled values. The authoritative source may be Plum Finance or CRM, subject to the decision in Section 16.

- Commercial Offer is the common control record for system-generated quotes, customer-format/external quotes and tender bids.

- Commercial Offer revisions and resubmissions are revisions within one offer series. Base Offers, Supplementary Offers and Change Quotations are separate offer series under the same Opportunity.

- A customer-facing submitted Commercial Offer revision must be finalised, numbered and linked to an immutable or tamper-evident submitted document artefact before production submission.

- Acceptance of a Commercial Offer does not automatically create a Work Order. Work Order creation is an explicit controlled handoff that preserves offer-line traceability.

- Work Order Amendment is an intake and review record. A status of Validated does not mean that the Work Order or its lines have been changed.

- The Billing Worksheet is the authoritative billable record. Manual entry and automated calculation engines are alternative producers of the same controlled worksheet and maker-checker process.

- Customer billing and vendor payable calculations are separate. Vendor payment is not dependent on customer payment receipt, and customer deductions do not automatically become vendor deductions.

- Equipment Hiring consumes HR, Equipment/Maintenance, Finance and other masters through controlled contracts. It must not silently become the owner of those masters.

- Direct integrations may evolve, but changes must not disturb the logical ownership, API contracts, audit trail or traceability defined in this matrix.

# 4. Core lifecycle and ownership summary

| **Lifecycle stage**                | **Authoritative system and module**                                      | **Primary owner**                         | **Main control**                                                                      |
|------------------------------------|--------------------------------------------------------------------------|-------------------------------------------|---------------------------------------------------------------------------------------|
| Lead                               | CRM - Lead Management                                                    | Sales - Lead Process Owner                | Capture source, duplicate review, owner, activities and qualification decision.       |
| Qualified Prospect / Account       | CRM - Account Management                                                 | Sales - Account Owner                     | Long-lived relationship record reused across Opportunities.                           |
| Prospect credit profile            | Plum Finance - Credit Profile or CRM - Credit Profile (decision pending) | Finance - Credit Control                  | PAN-level Credit Amount, Credit Days, status, effective date and audit.               |
| Opportunity                        | CRM - Opportunity Management                                             | Sales - Opportunity Owner                 | Separate record for each RFQ, enquiry, tender or requirement.                         |
| Commercial Offer                   | CRM - Commercial Offer Management                                        | Sales - Commercial Offer Owner            | Common control record for Base, Supplementary and Change Quotation series.            |
| Commercial approval and submission | CRM - Approval and Submission Control                                    | Sales - Commercial Approval Process Owner | T&C, authority and credit-exception approvals gate submission.                        |
| Customer response / award          | CRM - Commercial Offer Management                                        | Sales - Commercial Offer Owner            | Award, rejection, revision request, clarification, hold and decision history.         |
| Work Order handoff                 | Work Order Management - CRM-to-Hiring Handoff                            | Sales - Commercial Offer Owner            | Explicit handoff from accepted offer with line-level source traceability.             |
| Customer activation                | Plum Finance - Customer Master                                           | Finance - Customer Master Owner           | Must be active before Work Order release/posting and invoicing.                       |
| Work Order release                 | Equipment Hiring - Work Order Release                                    | Operations - Work Order Release Owner     | Checks customer activation, commercial completeness and required decision references. |
| Equipment and crew execution       | Equipment Hiring - Assignment Management                                 | Operations - Hiring Execution Owner       | Consumes Equipment/Maintenance and HR/Crew Master data.                               |
| Log sheet                          | Equipment Hiring - Log Sheet Management                                  | Operations - Site Execution Owner         | Approved usage evidence linked to Work Order line, equipment, crew, site and period.  |
| Billing Worksheet                  | Equipment Hiring - Billing Management                                    | Billing - Billing Process Owner           | Receives manual or automated calculation components; maker-checker applies.           |
| Customer invoice handoff           | Equipment Hiring - Finance Handoff                                       | Billing - Invoice Handoff Owner           | Approved billing package sent to Plum Finance.                                        |
| Final invoice and AR               | Plum Finance - Invoicing and Accounts Receivable                         | Finance - Accounts Owner                  | Statutory invoice, submission, receivable, collection and credit-note ownership.      |
| Vendor hire                        | Equipment Hiring - Vendor Hire Management                                | Operations - Vendor Hire Owner            | Separate vendor agreement, assignment, evidence, payable and T&C pass-through.        |

# 5. CRM relationship, Account and activity records

<table style="width:100%;">
<colgroup>
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Record / data area</strong></th>
<th><strong>Authoritative system and module</strong></th>
<th><strong>Primary business owner<br />
(one accountable role)</strong></th>
<th><strong>Supporting / approval roles<br />
(not owners)</strong></th>
<th><strong>Main consumers</strong></th>
<th><strong>Primary source / evidence repository</strong></th>
<th><strong>Key controls and ownership rules</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Lead</td>
<td>CRM - Lead Management</td>
<td>Sales - Lead Process Owner</td>
<td>Assigned Sales Executive maintains the Lead. Marketing supplies campaign/source data. Sales Manager approves exceptions where policy requires.</td>
<td>Account, Opportunity, Reporting</td>
<td>Manual entry, referral, campaign, import or approved external feed</td>
<td>Capture source, duplicate review, status, owner, qualification decision and closure reason.</td>
</tr>
<tr class="even">
<td>Lead source metadata</td>
<td>CRM - Lead Management</td>
<td>Sales - Lead Process Owner</td>
<td>Marketing owns campaign definitions and source-channel reference data. The assigned Sales Executive confirms the source used for the Lead.</td>
<td>BI, Audit, Opportunity</td>
<td>Source message, campaign, upload, referral or external feed</td>
<td>Preserve source name, date received, reference, contact and linked document.</td>
</tr>
<tr class="odd">
<td>Lead activity timeline</td>
<td>CRM - Activity Management</td>
<td>Sales - Activity Process Owner</td>
<td>The assigned user records and completes each activity. The relevant Lead, Account, Opportunity or Offer owner reviews overdue or disputed activities.</td>
<td>Lead, Account, Opportunity, Offer, Work Order</td>
<td>User-entered calls, visits, emails, WhatsApp, tasks and notes</td>
<td>Each activity must link to the correct business object and retain owner, date, status and outcome.</td>
</tr>
<tr class="even">
<td>Lead qualification decision</td>
<td>CRM - Lead Management</td>
<td>Sales - Lead Process Owner</td>
<td>The assigned Sales Executive proposes the decision. Sales Manager approval applies only where the qualification policy requires it.</td>
<td>Account, Opportunity, Reporting</td>
<td>Lead data and reviewed qualification evidence</td>
<td>Decision, reason, date and resulting Account/Opportunity links must be retained.</td>
</tr>
<tr class="odd">
<td>Qualified Prospect / Account</td>
<td>CRM - Account Management</td>
<td>Sales - Account Owner</td>
<td>Finance controls legal identity and credit fields. Sales maintains relationship, classification and ownership fields.</td>
<td>Opportunity, Credit, Offer, Reporting</td>
<td>Registration, enquiry/RFQ or registration-in-progress information</td>
<td>One long-lived commercial relationship record; do not create a new Account for each Opportunity.</td>
</tr>
<tr class="even">
<td>Account classification</td>
<td>CRM - Account Management</td>
<td>Sales - Account Policy Owner</td>
<td>The assigned Account Owner maintains the classification. Sales Management approves key-account or exceptional classifications.</td>
<td>Credit, Reporting, Sales review</td>
<td>Sales review</td>
<td>Segment, industry, geography, key-account status and relationship owner are Sales-controlled.</td>
</tr>
<tr class="odd">
<td>Account legal identity reference</td>
<td>CRM - Account Management</td>
<td>Finance - Customer Master Owner</td>
<td>Sales initiates or proposes legal details. Finance verifies and approves PAN, legal name and statutory identity.</td>
<td>Credit, Customer Master, Offer, Work Order</td>
<td>PAN, legal name and statutory evidence</td>
<td>Legal identity fields must be Finance-controlled and linked to the appropriate PAN/legal entity.</td>
</tr>
<tr class="even">
<td>Contact record</td>
<td>CRM - Contact Management</td>
<td>Sales - Account Owner</td>
<td>Finance or Billing may designate invoice and payment contacts but does not own the general contact record.</td>
<td>Opportunity, Offer, Work Order, Billing follow-up</td>
<td>Customer-provided contact details</td>
<td>Capture contact role, site/HO relevance, email/mobile, communication preference and active status.</td>
</tr>
<tr class="odd">
<td>Customer activation request</td>
<td>CRM - Customer Activation Workflow</td>
<td>Sales - Account Owner</td>
<td>Sales initiates the request. Finance - Customer Master Owner approves or rejects activation. Operations and Billing consume the result.</td>
<td>Plum Customer Master, Work Order release</td>
<td>Accepted offer, first Work Order and legal/statutory information</td>
<td>Sales initiates at first Work Order; Finance approval and activation result must be traceable.</td>
</tr>
</tbody>
</table>

# 6. External intelligence, credit, exposure and approval records

<table style="width:100%;">
<colgroup>
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Record / data area</strong></th>
<th><strong>Authoritative system and module</strong></th>
<th><strong>Primary business owner<br />
(one accountable role)</strong></th>
<th><strong>Supporting / approval roles<br />
(not owners)</strong></th>
<th><strong>Main consumers</strong></th>
<th><strong>Primary source / evidence repository</strong></th>
<th><strong>Key controls and ownership rules</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Reviewed external intelligence</td>
<td>CRM - Intelligence Review</td>
<td>Owner of the business decision that uses the review</td>
<td>Sales - Opportunity Owner owns pursuit-related reviews. Finance - Credit Control owns credit-related reviews. Management reviews only where policy requires.</td>
<td>Lead, Account, Opportunity, Credit</td>
<td>External reports, project/tender sources, manual research</td>
<td>The record must state whether it supports a Sales pursuit decision or a Finance credit decision. The corresponding decision owner is accountable; external sources are evidence only.</td>
</tr>
<tr class="even">
<td>Tender / project intelligence</td>
<td>CRM - Opportunity Input</td>
<td>Sales - Opportunity Owner</td>
<td>Tender or Commercial Support prepares the reviewed input. Sales Management reviews strategic or high-value opportunities.</td>
<td>Opportunity, Offer, Reporting</td>
<td>Manual review, upload or processed feed</td>
<td>Link intelligence to the relevant Opportunity; direct source integration may be added without changing ownership.</td>
</tr>
<tr class="odd">
<td>Rate benchmark / rate discovery</td>
<td>CRM - Rate Discovery</td>
<td>Sales - Commercial Pricing Owner</td>
<td>Sales Management or the designated Pricing Approver approves exceptions to pricing policy.</td>
<td>Opportunity, Offer approvers</td>
<td>Historical offers, awards, approved external benchmarks</td>
<td>Historical source results must be read-only; filters should include service/equipment, customer/segment, site/region, date and UOM.</td>
</tr>
<tr class="even">
<td>Credit profile</td>
<td>Plum Finance - Credit Profile or CRM - Credit Profile (decision pending)</td>
<td>Finance - Credit Control</td>
<td>Authorized Management approves exceptions. Sales and Operations have view access only, subject to role permissions.</td>
<td>Sales, Offer approval, Work Order release</td>
<td>Finance-approved PAN/legal-entity data</td>
<td>Must include Credit Amount, Credit Days, currency, effective date, status, source system and audit history.</td>
</tr>
<tr class="odd">
<td>Firm exposure snapshot</td>
<td>CRM - Credit Exposure Service</td>
<td>Finance - Credit Control</td>
<td>Finance Integration Owner supplies receivable data when the target formula is activated. Sales and Operations do not edit the exposure.</td>
<td>Offer approvers, Management, Work Order handoff</td>
<td>Temporary: active Work Order value. Target: unbilled Work Order value plus outstanding receivables from Plum</td>
<td>Store basis/version, source cut-off, component values and timestamp. Do not combine with Potential Exposure.</td>
</tr>
<tr class="even">
<td>Potential exposure snapshot</td>
<td>CRM - Credit Exposure Service</td>
<td>Finance - Credit Control</td>
<td>Sales maintains the underlying Commercial Offer status and value. Finance owns the exposure policy and calculation.</td>
<td>Offer approvers, Sales, Management</td>
<td>Latest submitted revision of each active Commercial Offer series</td>
<td>Exclude Draft, Withdrawn, Rejected/Lost, Closed and superseded revisions. Prevent double counting when value moves to Work Order exposure.</td>
</tr>
<tr class="odd">
<td>Credit decision</td>
<td>CRM - Credit Approval Workflow</td>
<td>Finance - Credit Control</td>
<td>Authorized Management approves an over-limit exception. Sales may submit only after the required decision is complete.</td>
<td>Commercial Offer submission, Work Order handoff, Audit</td>
<td>Credit profile and exposure snapshot</td>
<td>Within-limit or approved-exception decision must identify offer revision, exposure basis, excess amount, approver, date, reason and conditions.</td>
</tr>
<tr class="even">
<td>Credit exception approval</td>
<td>CRM - Approval Workflow</td>
<td>Finance - Credit Control</td>
<td>Authorized Management Approver makes the exception decision. Finance records the policy basis and conditions.</td>
<td>Commercial Offer submission, Audit</td>
<td>Credit decision request</td>
<td>An over-limit Commercial Offer is held from submission until approved. Material revision must trigger re-evaluation.</td>
</tr>
<tr class="odd">
<td>Commercial approval case</td>
<td>CRM - Approval Workflow</td>
<td>Sales - Commercial Approval Process Owner</td>
<td>Designated T&amp;C Policy Owner decides clause deviations. Finance - Credit Control decides credit status. Authorized Management decides exceptions above delegated authority.</td>
<td>Commercial Offer, Audit</td>
<td>T&amp;C deviation, authority, price/margin and credit decision inputs</td>
<td>One approval case may coordinate several required decisions without duplicating the underlying records.</td>
</tr>
</tbody>
</table>

# 7. Opportunity, Commercial Offer, T&C and submitted-document records

**T&C ownership rule: The Sales - Commercial Offer Owner selects clauses for a specific offer. One Designated T&C Policy Owner (working assumption: Commercial Head) owns the clause catalogue and decides deviations or new clauses. Finance, Legal Adviser and Management participate only when the clause category or delegated-authority rule requires their review.**

<table style="width:100%;">
<colgroup>
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Record / data area</strong></th>
<th><strong>Authoritative system and module</strong></th>
<th><strong>Primary business owner<br />
(one accountable role)</strong></th>
<th><strong>Supporting / approval roles<br />
(not owners)</strong></th>
<th><strong>Main consumers</strong></th>
<th><strong>Primary source / evidence repository</strong></th>
<th><strong>Key controls and ownership rules</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Opportunity</td>
<td>CRM - Opportunity Management</td>
<td>Sales</td>
<td>Account owner; Management review</td>
<td>Account, Commercial Offer, Pipeline reporting</td>
<td>RFQ, enquiry, tender or customer requirement</td>
<td>One separate Opportunity per requirement; must link to one Account and preserve source reference.</td>
</tr>
<tr class="even">
<td>Opportunity status and outcome</td>
<td>CRM - Opportunity Management</td>
<td>Sales</td>
<td>Sales manager</td>
<td>Pipeline, Reporting</td>
<td>Sales updates and customer outcome</td>
<td>Capture stage, next action, hold/loss/win reason and closure date.</td>
</tr>
<tr class="odd">
<td>Commercial Offer series</td>
<td>CRM - Commercial Offer Management</td>
<td>Sales - Commercial Offer Owner</td>
<td>Finance, Credit Control, the Designated T&amp;C Policy Owner and Management act only as approvers when a rule requires their decision.</td>
<td>Customer, Credit, Work Order, Reporting</td>
<td>Opportunity and customer requirement</td>
<td>One control record per Base, Supplementary or Change Quotation series. Related offers are not revisions of the Base Offer.</td>
</tr>
<tr class="even">
<td>Commercial Offer line</td>
<td>CRM - Commercial Offer Management</td>
<td>Sales - Commercial Offer Owner</td>
<td>Billing reviews billing terms and UOM. Finance reviews tax, payment and credit-sensitive fields. Neither becomes owner of the Commercial Offer.</td>
<td>Readiness, Document generation, Work Order handoff</td>
<td>Customer requirement, rate evidence and approved terms</td>
<td>Preserve service/scope, quantity, UOM, rate, tax context and source references.</td>
</tr>
<tr class="odd">
<td>Commercial Offer revision</td>
<td>CRM - Commercial Offer Revision Management</td>
<td>Sales - Commercial Offer Owner</td>
<td>Any approval role whose controlled term changes must re-review the affected revision.</td>
<td>Submission, Customer response, Audit</td>
<td>Prior offer revision</td>
<td>Structured revision and resubmission history is authoritative; prior revisions remain immutable.</td>
</tr>
<tr class="even">
<td>Commercial Offer purpose relationship</td>
<td>CRM - Commercial Offer Management</td>
<td>Sales - Commercial Offer Owner</td>
<td>Operations confirms the linked Work Order context but cannot alter the Base Offer or related-offer lineage.</td>
<td>Opportunity, Work Order, Amendment intake</td>
<td>Base Offer and related Work Order</td>
<td>Supplementary and Change Quotations link directly to the Base Offer; Change Quotation requires an eligible Work Order.</td>
</tr>
<tr class="odd">
<td>T&amp;C clause library</td>
<td>CRM - T&amp;C Library</td>
<td>Designated T&amp;C Policy Owner (working assumption: Commercial Head)</td>
<td>Legal Adviser reviews legal-risk wording. Finance reviews clauses affecting payment, tax, credit or financial exposure. IT Administration maintains access, not clause policy.</td>
<td>Commercial Offer, Document generation</td>
<td>Approved clause catalogue and source legal/commercial review</td>
<td>The Designated T&amp;C Policy Owner is one named PBL role accountable for the approved clause catalogue. Before final approval of this matrix, PBL must confirm whether that role is the Commercial Head or another named role.</td>
</tr>
<tr class="even">
<td>T&amp;C selection</td>
<td>CRM - Commercial Offer T&amp;C</td>
<td>Sales - Commercial Offer Owner</td>
<td>The Designated T&amp;C Policy Owner approves any non-standard clause. Finance reviews clauses with financial impact. Legal Adviser reviews clauses with legal or liability risk.</td>
<td>Approval workflow, Document generation</td>
<td>T&amp;C Library and customer requirement</td>
<td>The Sales - Commercial Offer Owner selects clauses for a specific offer but cannot approve a deviation or new clause. Each selection must retain the clause code/version and classification: Standard, Approved Alternative, Deviation, or Proposed New Clause.</td>
</tr>
<tr class="odd">
<td>T&amp;C deviation / new-clause decision</td>
<td>CRM - Approval Workflow</td>
<td>Designated T&amp;C Policy Owner (working assumption: Commercial Head)</td>
<td>Finance Approver decides financial-term impacts. Legal Adviser reviews legal-risk wording. Authorized Management approves matters above the T&amp;C Policy Owner's delegated authority.</td>
<td>Commercial Offer submission, Audit</td>
<td>Proposed clause wording and reason</td>
<td>One named T&amp;C Policy Owner is accountable for the decision. Required Finance, Legal or Management reviews depend on the clause category; they are supporting approvals, not alternative owners. Proposed wording, reason, decision, conditions, approver and date must be retained before finalisation or submission.</td>
</tr>
<tr class="even">
<td>Commercial Offer readiness</td>
<td>CRM - Readiness Service</td>
<td>Sales - Commercial Offer Owner</td>
<td>Finance - Credit Control, the Designated T&amp;C Policy Owner and other approvers supply their own decision records. Sales cannot override missing approvals.</td>
<td>Submission control</td>
<td>Current offer revision, evidence and decisions</td>
<td>Readiness is derived, not manually overridden; each mutation must validate its own preconditions.</td>
</tr>
<tr class="odd">
<td>Commercial Offer number</td>
<td>CRM - Commercial Offer Numbering</td>
<td>Sales - Commercial Offer Process Owner</td>
<td>IT Administration configures the approved number sequence but does not own the business reference.</td>
<td>Customer, Work Order, Reporting</td>
<td>Configured numbering policy</td>
<td>Production reference must be unique, stable and assigned at the controlled lifecycle point.</td>
</tr>
<tr class="even">
<td>Document snapshot</td>
<td>CRM - Commercial Offer Document Snapshot</td>
<td>Sales - Commercial Offer Owner</td>
<td>Finance and other approvers own only the fields or decisions assigned to them. The renderer consumes the approved snapshot without changing it.</td>
<td>Document renderer, Audit</td>
<td>Approved current offer revision</td>
<td>Freeze the exact lines, totals, terms, approvals, template and signatory data used for rendering.</td>
</tr>
<tr class="odd">
<td>Generated Commercial Offer artefact metadata</td>
<td>ERP Document Index - Commercial Offer</td>
<td>Sales - Commercial Offer Owner</td>
<td>IT Administration operates the repository. Document Control enforces metadata and retention rules.</td>
<td>Submission, Customer, Work Order, Audit</td>
<td>Document renderer; file stored in SharePoint/approved repository</td>
<td>Record template version, file name, external ID, hash, generated/finalised timestamps and supersession link.</td>
</tr>
<tr class="even">
<td>Submitted Commercial Offer revision</td>
<td>CRM - Submission Control</td>
<td>Sales - Commercial Offer Owner</td>
<td>Finance - Credit Control and other approvers must have completed all required decisions. Document Control protects the final artefact.</td>
<td>Customer response, Work Order, Audit</td>
<td>Finalised document artefact and submission evidence</td>
<td>Submitted revision and document artefact must be locked or tamper-evident. Revisions require a new revision and new finalised artefact.</td>
</tr>
<tr class="odd">
<td>Submission proof</td>
<td>ERP Document Index - Offer Submission</td>
<td>Sales - Commercial Offer Owner</td>
<td>Document Control maintains repository and metadata standards. The submitting user records the actual submission evidence.</td>
<td>Customer response, Audit</td>
<td>Portal, email, courier or manual evidence; file in SharePoint/approved repository</td>
<td>Capture method, date/time, recipient/reference, submitted artefact and re-submission history.</td>
</tr>
<tr class="even">
<td>Customer response / award outcome</td>
<td>CRM - Commercial Offer Management</td>
<td>Sales - Commercial Offer Owner</td>
<td>Operations consumes award details for handoff. Finance consumes customer activation and credit implications. Neither changes the customer response record.</td>
<td>Work Order, Customer activation, Reporting</td>
<td>Customer communication and award document</td>
<td>Capture accepted/awarded, rejected/lost, revision requested, clarification, hold or pending decision with evidence and date.</td>
</tr>
</tbody>
</table>

# 8. Work Order, customer activation and amendment records

<table style="width:100%;">
<colgroup>
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Record / data area</strong></th>
<th><strong>Authoritative system and module</strong></th>
<th><strong>Primary business owner<br />
(one accountable role)</strong></th>
<th><strong>Supporting / approval roles<br />
(not owners)</strong></th>
<th><strong>Main consumers</strong></th>
<th><strong>Primary source / evidence repository</strong></th>
<th><strong>Key controls and ownership rules</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Work Order handoff record</td>
<td>Work Order Management - CRM-to-Hiring Handoff</td>
<td>Sales - Commercial Offer Owner</td>
<td>Operations receives the handoff. Finance-controlled fields remain subject to Finance permissions; receiving the handoff does not transfer their ownership.</td>
<td>Hiring execution, Billing, Finance</td>
<td>Accepted Commercial Offer revision and customer Work Order document</td>
<td>Creation is explicit, not automatic. Preserve source offer, source line IDs, approval references and handoff event.</td>
</tr>
<tr class="even">
<td>Work Order</td>
<td>Work Order Management</td>
<td>Operations - Work Order Owner</td>
<td>Sales owns the accepted commercial source. Finance owns statutory and billing-control fields. Operations owns execution status and coordination.</td>
<td>Execution, Billing, Finance, Reporting</td>
<td>Customer Work Order and accepted offer</td>
<td>One Work Order may cover multiple sites; one accepted offer may create multiple Work Orders. Do not imply complete handoff without allocation evidence.</td>
</tr>
<tr class="odd">
<td>Work Order line</td>
<td>Work Order Management</td>
<td>Operations - Work Order Owner</td>
<td>Sales - Commercial Offer Owner owns source commercial terms. Finance - Customer Master Owner controls GSTN/legal billing identity. Billing owns billing-readiness processing.</td>
<td>Assignment, Log Sheet, Billing</td>
<td>Accepted Commercial Offer line and customer Work Order line</td>
<td>Preserve source-offer-line traceability. Site, GSTN, billing terms, UOM, rate and supporting documents may differ by line.</td>
</tr>
<tr class="even">
<td>Customer activation status</td>
<td>Plum Finance - Customer Master</td>
<td>Finance - Customer Master Owner</td>
<td>Sales initiates the activation request. Operations and Billing consume the approved status and cannot change it.</td>
<td>Work Order release, Invoicing, Credit</td>
<td>Finance-approved customer master</td>
<td>Customer must be active before Work Order release/posting and invoicing. CRM should consume the status through a defined contract.</td>
</tr>
<tr class="odd">
<td>GSTN and billing address</td>
<td>Plum Finance - Customer Master</td>
<td>Finance - Customer Master Owner</td>
<td>Sales or Operations may propose/select from approved values. Finance verifies, approves and controls the statutory value.</td>
<td>Work Order line, Invoice</td>
<td>Statutory customer data</td>
<td>Finance-controlled, auditable and locked after statutory events where applicable.</td>
</tr>
<tr class="even">
<td>Work Order release decision</td>
<td>Equipment Hiring - Work Order Release</td>
<td>Operations - Work Order Release Owner</td>
<td>Finance supplies customer activation. Sales supplies commercial completeness and the credit-decision reference. Operations makes the release decision.</td>
<td>Assignment, Log Sheet</td>
<td>Work Order, customer activation, credit decision reference and commercial completeness</td>
<td>Release verifies required references; it does not repeat the Commercial Offer credit approval calculation.</td>
</tr>
<tr class="odd">
<td>Work Order Amendment intake</td>
<td>Equipment Hiring - Work Order Amendment</td>
<td>Operations - Work Order Amendment Owner</td>
<td>Sales reviews commercial changes. Finance reviews statutory or billing effects. Their participation depends on amendment type.</td>
<td>Work Order, Related Commercial Offer, Audit</td>
<td>Customer amendment document and request</td>
<td>Record Administrative, Commercial or Mixed amendment without altering the Work Order.</td>
</tr>
<tr class="even">
<td>Work Order Amendment line proposal</td>
<td>Equipment Hiring - Work Order Amendment</td>
<td>Operations - Work Order Amendment Owner</td>
<td>Sales reviews commercial scope and pricing. Billing reviews future billing effects. Neither review changes the original Work Order line.</td>
<td>Future amendment application, Audit</td>
<td>Existing Work Order line or proposed new scope</td>
<td>ADD_LINE, CHANGE_LINE and CANCEL_LINE retain original snapshots and proposed values. Original Work Order lines remain unchanged.</td>
</tr>
<tr class="odd">
<td>Amendment commercial basis</td>
<td>Equipment Hiring - Work Order Amendment</td>
<td>Sales - Commercial Offer Owner</td>
<td>Operations links the amendment to the accepted related offer. Finance reviews any financial impact required by policy.</td>
<td>Amendment validation</td>
<td>Accepted Supplementary Offer or Change Quotation</td>
<td>Commercial/Mixed amendment may be received before basis is accepted but cannot be Validated without an accepted related offer.</td>
</tr>
<tr class="even">
<td>Amendment validation decision</td>
<td>Equipment Hiring - Work Order Amendment Workflow</td>
<td>Operations - Work Order Amendment Process Owner</td>
<td>Sales approves commercial interpretation. Finance approves statutory or billing effects. Authorized Management approves only where the amendment exceeds delegated authority.</td>
<td>Audit, Future application process</td>
<td>Amendment readiness and commercial basis</td>
<td>Validated means accepted for future downstream processing; it must not be described as applied.</td>
</tr>
</tbody>
</table>

# 9. Equipment, crew, mobilisation and execution records

<table style="width:100%;">
<colgroup>
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Record / data area</strong></th>
<th><strong>Authoritative system and module</strong></th>
<th><strong>Primary business owner<br />
(one accountable role)</strong></th>
<th><strong>Supporting / approval roles<br />
(not owners)</strong></th>
<th><strong>Main consumers</strong></th>
<th><strong>Primary source / evidence repository</strong></th>
<th><strong>Key controls and ownership rules</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Owned Equipment Master</td>
<td>Plum - Maintenance and Asset Management - Equipment Master</td>
<td>Fleet - Equipment Master Owner</td>
<td>Maintenance supplies technical status. Operations consumes the record for assignment.</td>
<td>Equipment assignment, Maintenance, Reporting</td>
<td>Asset registration and maintenance records</td>
<td>Hiring consumes master data; it must not duplicate or become authoritative for the master.</td>
</tr>
<tr class="even">
<td>Equipment availability and statutory status</td>
<td>Plum - Maintenance and Asset Management</td>
<td>Fleet - Equipment Availability Owner</td>
<td>Maintenance confirms technical and statutory validity. Operations consumes the result.</td>
<td>Equipment assignment</td>
<td>Maintenance, permit and statutory records</td>
<td>Assignment must use current availability and required statutory validity through a defined API contract.</td>
</tr>
<tr class="odd">
<td>Equipment assignment</td>
<td>Equipment Hiring - Assignment Management</td>
<td>Operations - Equipment Assignment Owner</td>
<td>Fleet confirms master and availability status. Maintenance confirms technical restrictions where applicable.</td>
<td>Log Sheet, Billing, Reporting</td>
<td>Released Work Order line and Equipment Master</td>
<td>Assign owned or vendor equipment to Work Order line, site, period and billing basis.</td>
</tr>
<tr class="even">
<td>Equipment assignment snapshot</td>
<td>Equipment Hiring - Assignment Management</td>
<td>Operations - Equipment Assignment Owner</td>
<td>Fleet owns the source master. The assignment snapshot is controlled by Operations and must preserve the source values used.</td>
<td>Audit, Billing, Reporting</td>
<td>Equipment Master and assignment decision</td>
<td>Preserve asset ID, registration, type/model, ownership origin, site, dates, status and relevant master values at assignment time.</td>
</tr>
<tr class="odd">
<td>Mobilisation record</td>
<td>Equipment Hiring - Mobilisation</td>
<td>Operations - Work Order Execution Owner</td>
<td>Transportation coordinates physical movement where used. Billing consumes dates and cost references.</td>
<td>Work Order, Site, Billing, Reporting</td>
<td>Assignment and transport/movement evidence</td>
<td>Preserve planned/actual dates, site, equipment, crew, transport reference and cost basis.</td>
</tr>
<tr class="even">
<td>Demobilisation record</td>
<td>Equipment Hiring - Demobilisation</td>
<td>Operations - Work Order Execution Owner</td>
<td>Transportation supports return movement. Billing reviews closure dependencies.</td>
<td>Closure, Transport, Billing</td>
<td>Site release, return and movement evidence</td>
<td>Capture return process, final readings, gate pass, fuel and billing-closure dependencies.</td>
</tr>
<tr class="odd">
<td>Equipment replacement</td>
<td>Equipment Hiring - Assignment Management</td>
<td>Operations - Equipment Assignment Owner</td>
<td>Fleet and Maintenance confirm replacement eligibility and technical restrictions.</td>
<td>Log Sheet, Billing, Reporting</td>
<td>Existing assignment and replacement equipment</td>
<td>Equipment change and crew change are separate events even when occurring together; preserve effective date and reason.</td>
</tr>
<tr class="even">
<td>Crew Master</td>
<td>Plum HR - Crew Master</td>
<td>HR - Crew Master Owner</td>
<td>Operations defines role requirements. Fleet or Maintenance may provide equipment/model competency criteria.</td>
<td>Crew assignment, Payroll/HR</td>
<td>HR employee/resource records</td>
<td>Skills, licences, certifications, restrictions, validity and equipment/model qualification are HR-controlled.</td>
</tr>
<tr class="odd">
<td>Vendor crew resource</td>
<td>Plum HR - Crew Master with vendor flag, or Equipment Hiring - Vendor Resource Register (decision pending)</td>
<td>Decision pending - see D-03</td>
<td>If stored in Plum, HR - Crew Master Owner is accountable. If stored in Hiring, Operations - Vendor Resource Register Owner is accountable. Only one model may be selected for production.</td>
<td>Vendor crew assignment</td>
<td>Vendor-submitted identity, licence and certification evidence</td>
<td>Must identify resource origin and vendor. Common statutory eligibility controls apply even if the record is thinner than an employee record.</td>
</tr>
<tr class="even">
<td>Crew assignment</td>
<td>Equipment Hiring - Crew Assignment</td>
<td>Operations - Crew Assignment Owner</td>
<td>HR supplies authoritative eligibility data. An authorized approver decides only permitted non-statutory exceptions.</td>
<td>Log Sheet, Attendance, Payroll/HR</td>
<td>Released Work Order, assignment and Crew Master</td>
<td>Validate role, skill, statutory licence, certification and equipment/model competence.</td>
</tr>
<tr class="odd">
<td>Statutory/legal licence decision</td>
<td>Equipment Hiring - Crew Eligibility</td>
<td>Operations - Crew Assignment Owner</td>
<td>HR owns licence data and validity. Operations enforces the hard block and cannot override an expired or missing statutory licence.</td>
<td>Crew assignment, Audit</td>
<td>Crew Master</td>
<td>Missing or expired statutory/legal licence must hard-block assignment.</td>
</tr>
<tr class="even">
<td>Non-statutory competency exception</td>
<td>Equipment Hiring - Approval Workflow</td>
<td>Operations - Crew Assignment Owner</td>
<td>The designated Risk Approver may approve only the mismatch categories allowed by policy. HR supplies the source competency record.</td>
<td>Crew assignment, Audit, Reporting</td>
<td>Crew Master and Work Order requirement</td>
<td>Non-statutory mismatch may permit approved override. Model-specific experience may warn or require approval according to risk policy.</td>
</tr>
</tbody>
</table>

# 10. Log sheet, fuel, Billing Worksheet and customer billing records

<table style="width:100%;">
<colgroup>
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Record / data area</strong></th>
<th><strong>Authoritative system and module</strong></th>
<th><strong>Primary business owner<br />
(one accountable role)</strong></th>
<th><strong>Supporting / approval roles<br />
(not owners)</strong></th>
<th><strong>Main consumers</strong></th>
<th><strong>Primary source / evidence repository</strong></th>
<th><strong>Key controls and ownership rules</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Log sheet</td>
<td>Equipment Hiring - Log Sheet Management</td>
<td>Operations - Site Execution Owner</td>
<td>The site user records usage. Billing reviews only approved evidence and cannot change the operational record.</td>
<td>Billing, Payroll/HR, Reporting</td>
<td>Daily site entry, approved readings and customer evidence</td>
<td>Link to Work Order line, equipment, crew, site and date/period; retain status and approval.</td>
</tr>
<tr class="even">
<td>Signed log-sheet metadata</td>
<td>ERP Document Index - Log Sheet</td>
<td>Operations - Site Execution Owner</td>
<td>Document Control enforces metadata and repository standards. Billing verifies suitability for billing.</td>
<td>Billing, Audit</td>
<td>Signed file stored in SharePoint/approved repository</td>
<td>Link file to structured log sheet and billing period; capture version, signatory, date and verification status.</td>
</tr>
<tr class="odd">
<td>Working time / usage quantities</td>
<td>Equipment Hiring - Log Sheet Management</td>
<td>Operations - Site Execution Owner</td>
<td>Billing - Billing Policy Owner defines how approved quantities are interpreted commercially.</td>
<td>Billing Worksheet</td>
<td>Approved log sheet</td>
<td>Capture normal hours, shifts, days, months, OT, idle, breakdown and availability according to Work Order terms.</td>
</tr>
<tr class="even">
<td>HMR / engine hours / odometer / KM</td>
<td>Equipment Hiring - Log Sheet Management</td>
<td>Operations - Site Execution Owner</td>
<td>Fleet validates equipment readings. Maintenance and Billing consume the approved/reconciled value.</td>
<td>Billing, Maintenance</td>
<td>Manual reading or validated GPS/IoT feed</td>
<td>Opening and closing readings must be source-linked and reconciled where required.</td>
</tr>
<tr class="odd">
<td>Breakdown record and hours</td>
<td>Equipment Hiring - Log Sheet and Breakdown Management</td>
<td>Operations - Site Execution Owner</td>
<td>Maintenance confirms the technical event. Billing applies the contractual billing or deduction rule.</td>
<td>Billing, Reporting</td>
<td>Log sheet and maintenance evidence</td>
<td>Record event, cause, start/end, responsibility and approved billable/deduction treatment.</td>
</tr>
<tr class="even">
<td>Fuel readings</td>
<td>Equipment Hiring - Log Sheet and Fuel Management</td>
<td>Operations - Site Execution Owner</td>
<td>Fleet or Fuel Management supplies source data. Billing consumes only the approved/reconciled value.</td>
<td>Billing, Reconciliation, Closure</td>
<td>Manual record, fuel system, GPS or IoT source</td>
<td>Preserve opening, issue, consumption, closing, source, tolerance and exception.</td>
</tr>
<tr class="odd">
<td>Fuel reconciliation</td>
<td>Equipment Hiring - Fuel Reconciliation</td>
<td>Operations - Site Execution Owner</td>
<td>Billing reviews the commercial effect. Fleet or Fuel Management confirms source quantities where required.</td>
<td>Closure, Billing, Reporting</td>
<td>Approved fuel readings and policy</td>
<td>Calculate expected versus actual, tolerance, variance reason and parked deduction/escalation.</td>
</tr>
<tr class="even">
<td>Billing input snapshot</td>
<td>Equipment Hiring - Billing Management</td>
<td>Billing - Billing Process Owner</td>
<td>Operations supplies approved usage evidence. Finance controls tax and invoice-handoff fields. Neither may silently alter the frozen snapshot.</td>
<td>Manual entry, Calculation engine, Audit</td>
<td>Work Order terms, approved log sheets, rates, UOM and evidence</td>
<td>Freeze the inputs used for the billing period and identify contract/rule version.</td>
</tr>
<tr class="odd">
<td>Manual billing components</td>
<td>Equipment Hiring - Billing Worksheet</td>
<td>Billing - Billing Maker</td>
<td>Billing Checker approves the worksheet. Finance reviews invoice and tax readiness.</td>
<td>Invoice handoff, Reporting</td>
<td>Billing input snapshot</td>
<td>Structured manual quantities, additions, OT, deductions, rate and remarks; retain maker-checker audit.</td>
</tr>
<tr class="even">
<td>Automated billing calculation result</td>
<td>Billing Calculation Service</td>
<td>Billing - Billing Policy Owner</td>
<td>Billing Checker reviews the result before acceptance. IT supports the service but does not own the calculation policy.</td>
<td>Billing Worksheet</td>
<td>Versioned billing input contract</td>
<td>Return component-level results, warnings, blockers, precision, rounding, rule-set version and deterministic calculation reference.</td>
</tr>
<tr class="odd">
<td>Billing Worksheet</td>
<td>Equipment Hiring - Billing Management</td>
<td>Billing - Billing Process Owner</td>
<td>Operations owns the source evidence. Finance owns invoice handoff and statutory processing. Billing owns the approved worksheet.</td>
<td>Invoice handoff, Reporting, Audit</td>
<td>Manual components or accepted automated result</td>
<td>Authoritative billable record. Record calculation mode, source snapshot, maker, checker, approval status and any override.</td>
</tr>
<tr class="even">
<td>Billing exception</td>
<td>Equipment Hiring - Billing Exception Workflow</td>
<td>Billing - Billing Process Owner</td>
<td>Operations resolves evidence or execution issues. Finance resolves invoice, tax or statutory issues. The exception record must state the responsible role.</td>
<td>Invoice readiness, Reporting</td>
<td>Missing evidence, mismatch, excess fuel, commercial discrepancy</td>
<td>Track owner, reason, status, ageing, resolution and impact. Unresolved blocker prevents invoice handoff where policy requires.</td>
</tr>
<tr class="odd">
<td>Invoice support checklist</td>
<td>Equipment Hiring - Invoice Readiness</td>
<td>Billing - Invoice Readiness Owner</td>
<td>Operations supplies operational documents. Finance supplies statutory or invoicing requirements. Each checklist item has one named responsible role.</td>
<td>Invoice handoff, Audit</td>
<td>Customer/Work Order/line requirements and document metadata</td>
<td>Checklist must be configurable by customer/Work Order/line and trace verification status.</td>
</tr>
<tr class="even">
<td>Invoice handoff package</td>
<td>Equipment Hiring - Finance Handoff</td>
<td>Billing - Invoice Handoff Owner</td>
<td>Finance receives and validates the package. Finance may reject it with reasons but does not alter the approved Billing Worksheet.</td>
<td>Plum Finance - Invoicing</td>
<td>Approved Billing Worksheet and support checklist</td>
<td>Send one versioned, idempotent package with source references, amounts, tax context and document links.</td>
</tr>
</tbody>
</table>

# 11. Vendor equipment hire, vendor crew and vendor payable records

<table style="width:100%;">
<colgroup>
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Record / data area</strong></th>
<th><strong>Authoritative system and module</strong></th>
<th><strong>Primary business owner<br />
(one accountable role)</strong></th>
<th><strong>Supporting / approval roles<br />
(not owners)</strong></th>
<th><strong>Main consumers</strong></th>
<th><strong>Primary source / evidence repository</strong></th>
<th><strong>Key controls and ownership rules</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Vendor Hire Agreement</td>
<td>Equipment Hiring - Vendor Hire Management</td>
<td>Operations - Vendor Hire Agreement Owner</td>
<td>Procurement confirms sourcing or PO requirements when applicable. Finance reviews tax and payable controls.</td>
<td>Vendor assignment, Vendor payable, Audit</td>
<td>Vendor quotation/negotiation and approved agreement</td>
<td>Capture vendor, equipment/service, site/period, rate basis, OT, deductions, taxes, validity, approvals and status.</td>
</tr>
<tr class="even">
<td>Customer-to-vendor T&amp;C pass-through</td>
<td>Equipment Hiring - Vendor Hire Management</td>
<td>Operations - Vendor Hire Agreement Owner</td>
<td>The Designated T&amp;C Policy Owner decides pass-through wording. Legal Adviser reviews legal-risk clauses. The vendor accepts or proposes deviations; Finance reviews financial terms.</td>
<td>Vendor agreement, Risk review</td>
<td>Customer Commercial Offer/Work Order T&amp;C</td>
<td>Explicitly link customer obligation, pass-through requirement, vendor clause, vendor acceptance/deviation and residual risk retained by PBL.</td>
</tr>
<tr class="odd">
<td>Vendor equipment resource</td>
<td>Equipment Hiring - Vendor Equipment Register</td>
<td>Operations - Vendor Resource Owner</td>
<td>The vendor supplies documents. Fleet or Maintenance verifies equipment identity and statutory/technical validity where required.</td>
<td>Vendor assignment, Log Sheet</td>
<td>Vendor equipment documents and inspection evidence</td>
<td>Record vendor ownership, equipment identity, type/model, statutory validity, availability and supporting documents.</td>
</tr>
<tr class="even">
<td>Vendor equipment assignment</td>
<td>Equipment Hiring - Vendor Hire Execution</td>
<td>Operations - Vendor Hire Execution Owner</td>
<td>The vendor confirms availability. The Hiring Coordinator manages the assignment and site communication.</td>
<td>Log Sheet, Vendor payable, Reporting</td>
<td>Vendor agreement, released Work Order line and vendor equipment resource</td>
<td>Link assignment to customer demand without changing the owned-equipment Work Order-line contract.</td>
</tr>
<tr class="odd">
<td>Vendor crew resource</td>
<td>Plum HR with vendor flag or Equipment Hiring - Vendor Resource Register (decision pending)</td>
<td>Decision pending - see D-03</td>
<td>If stored in Plum, HR - Crew Master Owner is accountable. If stored in Hiring, Operations - Vendor Resource Register Owner is accountable. Vendor supplies evidence; PBL verifies it.</td>
<td>Vendor crew assignment</td>
<td>Vendor documents and PBL verification</td>
<td>PBL remains responsible for required crew documentation and eligibility evidence.</td>
</tr>
<tr class="even">
<td>Vendor crew assignment</td>
<td>Equipment Hiring - Vendor Hire Execution</td>
<td>Operations - Vendor Hire Execution Owner</td>
<td>HR or the Vendor Resource Owner supplies eligibility data. The vendor confirms deployment. PBL Operations makes the assignment decision.</td>
<td>Log Sheet, Reporting</td>
<td>Vendor crew resource and vendor assignment</td>
<td>Apply statutory eligibility controls; record vendor responsibility and PBL oversight.</td>
</tr>
<tr class="odd">
<td>Vendor log sheet</td>
<td>Equipment Hiring - Log Sheet Management</td>
<td>Operations - Site Execution Owner</td>
<td>The vendor confirms the site record. Billing reviews customer-billing relevance. Accounts Payable reviews vendor-payable relevance.</td>
<td>Vendor payable, Customer billing where separately relevant</td>
<td>Site record and signed evidence</td>
<td>Same operational evidence may be referenced, but customer billing and vendor payable calculations remain independent.</td>
</tr>
<tr class="even">
<td>Vendor payable worksheet</td>
<td>Equipment Hiring - Vendor Payable Management</td>
<td>Operations - Vendor Payable Process Owner</td>
<td>The Hiring Payables Maker prepares the worksheet. Finance - Accounts Payable Checker approves the handoff. Operations confirms evidence.</td>
<td>Plum Finance - Accounts Payable</td>
<td>Vendor agreement and approved vendor log sheet</td>
<td>Calculate fixed hourly/daily/monthly base, OT, vendor-specific deductions and recoveries. Do not depend on customer payment receipt.</td>
</tr>
<tr class="odd">
<td>Vendor invoice reference</td>
<td>Equipment Hiring - Vendor Payable Management</td>
<td>Finance - Accounts Payable</td>
<td>Operations links the vendor invoice to the agreement and evidence. Finance controls the payable and dispute status.</td>
<td>Payment handoff, Audit</td>
<td>Vendor invoice/document in SharePoint/approved repository</td>
<td>Link vendor invoice to agreement, period, evidence and payable worksheet; record dispute or adjustment.</td>
</tr>
<tr class="even">
<td>Vendor payment handoff</td>
<td>Equipment Hiring - Finance Handoff</td>
<td>Finance - Accounts Payable</td>
<td>Operations supplies the approved vendor-payable worksheet. Finance owns the handoff to Plum and the resulting status.</td>
<td>Plum Finance - Accounts Payable</td>
<td>Approved vendor payable worksheet</td>
<td>Versioned, idempotent handoff with vendor, amount, taxes, deductions, supporting references and status.</td>
</tr>
</tbody>
</table>

# 12. Invoicing, accounts receivable and Finance records

<table style="width:100%;">
<colgroup>
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Record / data area</strong></th>
<th><strong>Authoritative system and module</strong></th>
<th><strong>Primary business owner<br />
(one accountable role)</strong></th>
<th><strong>Supporting / approval roles<br />
(not owners)</strong></th>
<th><strong>Main consumers</strong></th>
<th><strong>Primary source / evidence repository</strong></th>
<th><strong>Key controls and ownership rules</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Draft invoice</td>
<td>Plum Finance - Invoicing</td>
<td>Finance - Billing</td>
<td>Equipment Hiring - Invoice Handoff Owner provides the approved package. Finance creates and controls the draft invoice.</td>
<td>Customer, AR, Credit Exposure</td>
<td>Approved invoice handoff package</td>
<td>Draft invoice must trace to one approved Billing Worksheet and support checklist.</td>
</tr>
<tr class="even">
<td>Final statutory invoice</td>
<td>Plum Finance - Invoicing</td>
<td>Finance - Accounts</td>
<td>Finance - Billing prepares or reviews the invoice. Accounts owns posting, statutory reference and accounting status.</td>
<td>AR, GST, Customer, Audit</td>
<td>Posted draft invoice and statutory services</td>
<td>Authoritative invoice number, GST/e-invoice references, posting status and accounting audit trail.</td>
</tr>
<tr class="odd">
<td>Invoice submission proof metadata</td>
<td>ERP Document Index - Invoice Submission</td>
<td>Finance - Billing</td>
<td>Sales - Account Owner may support customer follow-up but does not own the submission-proof record.</td>
<td>AR, Audit, Sales follow-up</td>
<td>Portal, email, courier or manual evidence; file in SharePoint/approved repository</td>
<td>Capture submission method, date, reference, recipient, artefact and re-submission history.</td>
</tr>
<tr class="even">
<td>Invoice rejection</td>
<td>Plum Finance - Invoice Follow-up</td>
<td>Finance - Billing</td>
<td>Sales - Account Owner supports customer communication. Operations resolves service or evidence issues.</td>
<td>Credit note/reissue, Reporting</td>
<td>Customer rejection communication</td>
<td>Record reason, date, customer remarks, action owner, resolution and re-submission.</td>
</tr>
<tr class="odd">
<td>Credit note / invoice cancellation</td>
<td>Plum Finance - Invoicing and Accounting</td>
<td>Finance - Accounts</td>
<td>Finance - Billing supplies the reason and supporting data. Authorized Management approves only where policy requires.</td>
<td>AR, GST, Audit</td>
<td>Statutory/accounting process</td>
<td>Finance-controlled with approval, reason, tax impact and immutable accounting audit.</td>
</tr>
<tr class="even">
<td>Accounts receivable</td>
<td>Plum Finance - Accounts Receivable</td>
<td>Finance - Accounts Receivable</td>
<td>Sales, Credit Control and Management have view or follow-up responsibilities only.</td>
<td>Credit Exposure, Collection, Reporting</td>
<td>Final invoice and payment allocation</td>
<td>Due date, ageing, collection status and allocation to customer, PAN/legal entity, Work Order and invoice.</td>
</tr>
<tr class="odd">
<td>AR follow-up / escalation</td>
<td>Plum Finance - AR Follow-up</td>
<td>Finance - Accounts Receivable</td>
<td>The assigned Sales Account Owner supports customer follow-up according to the approved AR escalation matrix. Credit Control and Management join only at defined thresholds.</td>
<td>Management, Credit, Sales</td>
<td>AR ageing and follow-up activity</td>
<td>Use configured ageing buckets, responsible owner, escalation date, action, next-action date and management escalation.</td>
</tr>
<tr class="even">
<td>Payment receipt and bank reconciliation</td>
<td>Plum Finance - Bank Reconciliation</td>
<td>Finance - Accounts</td>
<td>Treasury or Bank Integration provides the source transaction. Finance owns allocation and reconciliation.</td>
<td>AR, Reconciliation, Audit</td>
<td>Bank feed, statement or manual receipt evidence</td>
<td>Preserve UTR, bank status, amount, allocation, reconciliation and audit trail.</td>
</tr>
<tr class="odd">
<td>Profitability source data</td>
<td>Finance and BI - Profitability Read Model</td>
<td>Finance - Management Reporting Owner</td>
<td>Operations, Sales and Billing own their source transactions. BI only consumes and presents them.</td>
<td>Management reporting</td>
<td>Invoice revenue, equipment/crew/vendor/transport and other direct costs</td>
<td>Report must drill to source records; the BI model is not authoritative for underlying transactions.</td>
</tr>
</tbody>
</table>

# 13. Document governance records

<table style="width:100%;">
<colgroup>
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Record / data area</strong></th>
<th><strong>Authoritative system and module</strong></th>
<th><strong>Primary business owner<br />
(one accountable role)</strong></th>
<th><strong>Supporting / approval roles<br />
(not owners)</strong></th>
<th><strong>Main consumers</strong></th>
<th><strong>Primary source / evidence repository</strong></th>
<th><strong>Key controls and ownership rules</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Document metadata</td>
<td>ERP Document Index</td>
<td>Primary owner of the linked business record</td>
<td>IT Administration operates the repository and access controls. Document Control enforces metadata standards.</td>
<td>All modules, Audit</td>
<td>User upload, generated artefact or integration</td>
<td>Document type, linked object, version, status, owner, hash, repository ID, access group and retention metadata.</td>
</tr>
<tr class="even">
<td>File binary</td>
<td>SharePoint or approved ERP-linked repository</td>
<td>Primary owner of the linked business record</td>
<td>IT Administration operates the storage service. The business owner approves access and retention requirements.</td>
<td>ERP document links and authorized users</td>
<td>Uploaded/generated file</td>
<td>Repository stores the binary; ERP retains authoritative business linkage and required metadata.</td>
</tr>
<tr class="odd">
<td>Document version relationship</td>
<td>ERP Document Index</td>
<td>Primary owner of the linked business record</td>
<td>Document Control enforces supersession and retention rules. IT Administration maintains the repository service.</td>
<td>Audit, Submission, Reporting</td>
<td>Prior and replacement document metadata</td>
<td>Preserve superseded-by relationship, status and reason; replacement must not overwrite a submitted/finalised artefact.</td>
</tr>
<tr class="even">
<td>Document access group</td>
<td>ERP Document Index - Repository Governance</td>
<td>IT Administration - Repository Access Owner</td>
<td>The primary owner of the linked business record approves the business need for access.</td>
<td>Security, Audit</td>
<td>ERP role matrix and repository permissions</td>
<td>Access should align with ERP role and data scope; exceptions require approval and audit.</td>
</tr>
<tr class="odd">
<td>Retention and disposal status</td>
<td>ERP Document Index - Repository Governance</td>
<td>Primary owner of the linked business record</td>
<td>IT Administration applies the retention control. Finance, Legal Adviser or Compliance supplies mandatory retention rules where relevant.</td>
<td>Audit, Compliance</td>
<td>Retention policy</td>
<td>Do not delete or alter files required for statutory, contractual, audit or dispute purposes.</td>
</tr>
<tr class="even">
<td>Document link health</td>
<td>ERP Document Index</td>
<td>Primary owner of the linked business record</td>
<td>IT Administration resolves technical repository failures. The business owner confirms whether a missing document blocks the process.</td>
<td>All consuming modules</td>
<td>Repository status and integration monitoring</td>
<td>Broken, missing or unauthorized links must be visible and assigned for resolution.</td>
</tr>
</tbody>
</table>

# 14. Integration, event, audit and security records

<table style="width:100%;">
<colgroup>
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Record / data area</strong></th>
<th><strong>Authoritative system and module</strong></th>
<th><strong>Primary business owner<br />
(one accountable role)</strong></th>
<th><strong>Supporting / approval roles<br />
(not owners)</strong></th>
<th><strong>Main consumers</strong></th>
<th><strong>Primary source / evidence repository</strong></th>
<th><strong>Key controls and ownership rules</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>API / data contract</td>
<td>Integration Governance - Contract Catalogue</td>
<td>IT - Architecture Owner</td>
<td>The primary owner of each business process approves the business meaning of the contract.</td>
<td>Modules, Plum and external systems</td>
<td>Version-controlled technical documentation</td>
<td>Versioned schemas, ownership, error model, idempotency, security and compatibility rules.</td>
</tr>
<tr class="even">
<td>Business event catalogue</td>
<td>Integration Governance - Event Catalogue</td>
<td>IT - Architecture Owner</td>
<td>The primary owner of the producing business process approves event meaning and required business context.</td>
<td>Implementation teams, Audit, Integrations</td>
<td>Domain contracts</td>
<td>Define event name, producer, owner, payload, version, correlation and audit expectations.</td>
</tr>
<tr class="odd">
<td>Business event instance</td>
<td>Producing module - Event Store</td>
<td>Primary owner of the producing business record</td>
<td>IT Administration operates the event platform and retention controls.</td>
<td>Audit, Integrations, Reporting</td>
<td>Successful business mutation</td>
<td>Record only meaningful committed actions; include actor, time, record, correlation and relevant before/after or decision context.</td>
</tr>
<tr class="even">
<td>Audit log</td>
<td>Central Audit Log</td>
<td>IT Administration - Audit Platform Owner</td>
<td>The relevant business owner defines which changes require audit. Internal Audit reviews the control design.</td>
<td>Security, Compliance, Support</td>
<td>Application events and controlled field changes</td>
<td>Searchable, tamper-evident where required, with before/after values for sensitive changes.</td>
</tr>
<tr class="odd">
<td>Integration message</td>
<td>Integration Monitoring</td>
<td>IT - Integration System Owner</td>
<td>The relevant business process owner is accountable for resolving the underlying business failure.</td>
<td>Audit, Support</td>
<td>API/event exchange</td>
<td>Correlation ID, request/response reference, status, retries, error, owner and resolution.</td>
</tr>
<tr class="even">
<td>Finance, GST or bank response</td>
<td>Plum Finance - Integration Records</td>
<td>Finance - Accounts</td>
<td>IT - Integration Support resolves technical failures. Finance decides business acceptance and reconciliation.</td>
<td>Invoice, AR, Audit</td>
<td>Statutory, bank or reconciliation service</td>
<td>Preserve original response, status, reference, timestamp and reconciliation outcome.</td>
</tr>
<tr class="odd">
<td>GPS, HMR or IoT raw data</td>
<td>Telematics or IoT Source System</td>
<td>Operations - Fleet</td>
<td>IT - Integration Support operates the connector. Billing and Maintenance consume only approved or reconciled values.</td>
<td>Log Sheet, Maintenance, Billing</td>
<td>Device or provider feed</td>
<td>Raw source is not automatically the billable value; approved/reconciled ERP value must retain source reference.</td>
</tr>
<tr class="even">
<td>Transportation handoff</td>
<td>Integration Layer - Transportation Contract</td>
<td>Operations - Transportation Process Owner</td>
<td>IT - Architecture Owner governs the contract. Hiring Operations consumes the handoff for mobilisation/demobilisation.</td>
<td>Mobilisation, Demobilisation, Reporting</td>
<td>Legacy Transportation system</td>
<td>Use defined wrappers/contracts so legacy implementation does not dictate CRM/Hiring ownership.</td>
</tr>
<tr class="odd">
<td>Messaging record</td>
<td>Messaging Integration and linked CRM/Work Order Activity</td>
<td>Primary owner of the linked business process</td>
<td>IT - Messaging System Owner operates the connector and retention controls.</td>
<td>CRM, Work Order, Audit</td>
<td>WhatsApp, email, SMS or Teams</td>
<td>Important communication should link to the business record where enabled and retain sender, recipient, date and reference.</td>
</tr>
<tr class="even">
<td>Role and permission matrix</td>
<td>Access Governance - RBAC Catalogue</td>
<td>Management - Access Policy Owner</td>
<td>Each business process owner defines permitted actions. IT Administration implements them. Management approves segregation-of-duties rules.</td>
<td>All modules, UAT, Audit</td>
<td>Approved role/action matrix</td>
<td>Freeze action permissions early; field-level and data-level scopes must be testable.</td>
</tr>
<tr class="odd">
<td>Authentication identity and claims</td>
<td>Identity Provider and Authentication Adapter</td>
<td>IT Administration - Identity Service Owner</td>
<td>Business process owners define role mapping and data scope. Management approves high-risk access.</td>
<td>All modules</td>
<td>Entra ID or temporary test identity provider</td>
<td>Authentication source may change, but internal user ID, role and scope claims must remain stable.</td>
</tr>
</tbody>
</table>

# 15. Reporting, BI and future-readiness records

<table style="width:100%;">
<colgroup>
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
<col style="width: 14%" />
</colgroup>
<thead>
<tr class="header">
<th><strong>Record / data area</strong></th>
<th><strong>Authoritative system and module</strong></th>
<th><strong>Primary business owner<br />
(one accountable role)</strong></th>
<th><strong>Supporting / approval roles<br />
(not owners)</strong></th>
<th><strong>Main consumers</strong></th>
<th><strong>Primary source / evidence repository</strong></th>
<th><strong>Key controls and ownership rules</strong></th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>Operational report</td>
<td>Reporting and BI - Read Model</td>
<td>Primary owner of the source business process</td>
<td>IT and BI support delivery; they do not own the source transaction.</td>
<td>Users, Management</td>
<td>Authoritative source transactions</td>
<td>Reports must drill to source records and must not become separately maintained totals.</td>
</tr>
<tr class="even">
<td>Credit exposure dashboard</td>
<td>Reporting and BI - CRM Credit Exposure Read Model</td>
<td>Finance - Credit Control</td>
<td>Management consumes the dashboard and approves only defined exceptions.</td>
<td>Approvers, Management</td>
<td>Firm and Potential Exposure snapshots</td>
<td>Display components and basis separately; show data cut-off and source status.</td>
</tr>
<tr class="odd">
<td>Offer pipeline reporting</td>
<td>Reporting and BI - Commercial Offer Read Model</td>
<td>Sales - Sales Process Owner</td>
<td>Sales Management reviews the pipeline but does not alter source Commercial Offer records through the report.</td>
<td>Sales management</td>
<td>Opportunity and Commercial Offer records</td>
<td>Show mode, purpose, latest revision, value, approvals, submission, status and outcome.</td>
</tr>
<tr class="even">
<td>Work Order and execution reporting</td>
<td>Reporting and BI - Work Order and Hiring Read Model</td>
<td>Operations - Work Order Execution Owner</td>
<td>Sales and Finance remain owners only of their source fields. BI displays them without changing ownership.</td>
<td>Management</td>
<td>Work Order, assignment, log sheet and exception records</td>
<td>Show site, line, equipment, crew, own/vendor status, validity and exceptions with drill-through.</td>
</tr>
<tr class="odd">
<td>Billing exception reporting</td>
<td>Reporting and BI - Billing Exception Read Model</td>
<td>Billing - Billing Process Owner</td>
<td>Finance and Operations own the resolution of the specific issue assigned to them.</td>
<td>Management</td>
<td>Billing exception records</td>
<td>Show open items, ageing, owner, reason, blocker and commercial impact.</td>
</tr>
<tr class="even">
<td>AR reporting</td>
<td>Reporting and BI - Plum AR Read Model</td>
<td>Finance - Accounts Receivable</td>
<td>Sales and Management consume the report and perform only the follow-up actions assigned by policy.</td>
<td>Sales, Management</td>
<td>Plum Accounts Receivable</td>
<td>Due, overdue, ageing, escalation, collection and allocation must trace to invoice/receipt.</td>
</tr>
<tr class="odd">
<td>Vendor payable reporting</td>
<td>Reporting and BI - Vendor Payable Read Model</td>
<td>Finance - Accounts Payable</td>
<td>Operations owns vendor-agreement and evidence source records; Finance owns payable status.</td>
<td>Management</td>
<td>Vendor payable worksheet and Plum AP status</td>
<td>Show agreement, period, base, OT, deductions, handoff and payment status.</td>
</tr>
<tr class="even">
<td>Sales commission readiness</td>
<td>Reporting and BI - Commission Readiness Read Model</td>
<td>Management - Commission Policy Owner</td>
<td>Finance supplies financial basis. Sales supplies attribution. HR supports employee linkage where required.</td>
<td>Future commission calculation</td>
<td>Account, Opportunity, Offer, Work Order, Billing and Collection records</td>
<td>Commission automation may be future scope, but attribution and basis data must be preserved.</td>
</tr>
</tbody>
</table>

# 16. Decisions to confirm before production contract freeze

| **Decision ID** | **Topic**                           | **Required decision**                                                                                                                                                                                                          | **Owner**                                                                                                          |
|-----------------|-------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| D-01            | Credit profile authority            | Confirm whether Plum already maintains controlled Credit Amount and Credit Days for the relevant legal entity/PAN. If yes, CRM consumes a GET contract. If not, CRM becomes authoritative and exposes approved values to Plum. | Accountable: Finance - Credit Control. Support: Plum implementation team.                                          |
| D-02            | Target exposure formula and cutover | Temporary basis is total active Work Order value. Target basis is unbilled Work Order value plus outstanding receivables from Plum. Confirm cutover criteria and data availability.                                            | Accountable: Finance - Credit Control.                                                                             |
| D-03            | Vendor crew master representation   | Confirm whether vendor crew are held in Plum HR/Crew Master with a vendor-resource flag. If not, use a thinner Equipment Hiring Vendor Resource Register.                                                                      | Accountable: HR - Crew Master Owner. Support: Hiring Operations and Plum implementation team.                      |
| D-04            | Vendor-hire procurement linkage     | Confirm whether a PO or Procurement approval is mandatory for all vendor-hire agreements. Do not make Procurement the authoritative record unless the operating process requires it.                                           | Accountable: Operations - Vendor Hire Owner. Support: Procurement and Finance.                                     |
| D-05            | SharePoint repository design        | Confirm site/library/folder pattern, permissions, retention, versioning, external IDs and failure/retry rules. ERP document metadata remains authoritative for business linkage.                                               | Accountable: IT Administration - Document Repository Owner. Support: owners of linked business records.            |
| D-06            | Draft invoice boundary              | Confirm whether Plum creates the first draft invoice directly from the Hiring handoff package or whether an intermediate draft exists in Hiring. Final statutory invoice remains in Plum Finance.                              | Accountable: Finance - Billing. Support: Plum implementation team and Equipment Hiring Billing.                    |
| D-07            | Work Order amendment application    | Define a future separate process for applying a Validated amendment to an effective Work Order version. The current intake record must remain non-applying until that contract is approved.                                    | Accountable: Operations - Work Order Amendment Process Owner. Support: Sales - Commercial Offer Owner and Finance. |

# 17. Implementation and UAT guidance

- Every important record and sensitive field must map to a primary owner, supporting role and explicit edit permission.

- Where one screen displays fields owned by different functions, the UI may be combined but the authorization and audit rules must remain field-specific.

- APIs and events must identify the authoritative producer and must not create duplicate masters in consuming modules.

- UAT must verify not only that values appear, but also that unauthorized functions cannot create, alter, approve or replace them.

- Submitted Commercial Offer artefacts, statutory invoices, credit decisions, billing approvals and vendor payable approvals require stronger immutability and audit checks than ordinary draft records.

- Document testing must verify both ERP metadata and repository access. A file that exists but is not correctly linked is not acceptable.

- Billing-engine tests must verify the versioned input contract and component-level result; the Billing Worksheet remains the approved billable record.

- Work Order Amendment tests must verify that Received, Under Review and Validated records do not alter the original Work Order or lines.

- Reports must drill to source transactions and show the data cut-off and calculation basis for derived measures.

- Temporary providers, fixtures and mock Plum endpoints may be used during development, but the final provider must satisfy the same frozen contract.

# 18. Summary of key ownership positions

- CRM owns Lead, Account relationship, Opportunity, Commercial Offer, T&C selection, commercial approvals, customer response and the explicit Work Order handoff.

- Finance owns customer activation, legal/statutory customer data, credit policy, final invoicing, AR, receipts, credit notes and accounting records.

- Equipment Hiring owns Work Order release, assignment, mobilisation/demobilisation, log sheets, amendment intake, Billing Worksheet and vendor-hire execution.

- HR/Crew Master owns crew identity, skills, licences, certifications and validity; Equipment Hiring owns the assignment decision.

- Equipment/Maintenance Master owns asset identity, availability and statutory status; Equipment Hiring owns the assignment snapshot and operational use.

- The Billing Worksheet is authoritative for approved billable components regardless of whether they are entered manually or produced by a calculation engine.

- Vendor payable is calculated independently from customer billing and customer payment receipt.

- The ERP Document Index owns business linkage and metadata; SharePoint or another approved repository stores file binaries.

- Derived reports and dashboards consume source records; they do not become independent systems of record.

# 19. Review and approval

| **Review area**                                 | **Reviewer** | **Decision / comments** | **Date** |
|-------------------------------------------------|--------------|-------------------------|----------|
| Business process review                         |              |                         |          |
| Finance and credit review                       |              |                         |          |
| Operations and Hiring review                    |              |                         |          |
| HR / Crew Master review                         |              |                         |          |
| IT / Integration and document-governance review |              |                         |          |
