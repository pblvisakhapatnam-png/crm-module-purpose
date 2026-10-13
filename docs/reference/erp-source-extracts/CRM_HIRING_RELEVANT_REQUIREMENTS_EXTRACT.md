# CRM Hiring Relevant Requirements Extract

## Purpose

This is a curated extract and summary of CRM + Equipment Hiring relevant requirements from the ERP Functional Requirements Specification.

Source of truth:

```text
docs/source/current/requirements/PBL_ERP_Functional_Requirements_Specification_2026-05-19.docx
```

Supporting full extract:

```text
docs/reference/erp-source-extracts/ERP_FUNCTIONAL_SPEC_FULL_TEXT_EXTRACT.md
```

If this curated extract conflicts with the source Word document, the Word document controls for what the source actually said. See "Authority and use of this extract" below for how that relates to current approved decisions.

## Authority and use of this extract

This file is a derived, machine-readable curated reference based on the identified source document.

The source document is authoritative for the wording and content that existed in that source when it was prepared. This does not mean the source document automatically overrides a later explicit PBL decision, approved business rule, frozen contract, accepted architecture decision or current implementation instruction.

Where a later approved decision changes or refines the source position, the source wording is retained as historical input below and the current reconciliation is stated separately in "Current Design Reconciliations".

This extract must not be treated as a final database schema, screen design, service boundary or technical prescription. See `docs/source/README.md` for the full authority hierarchy and `docs/agent/ARCHITECTURE_DECISIONS.md` (ADR-013) for the directional-guidance rule.

## Extraction Notes

This file is summarized from source sections and preserves source section references where practical. It does not redefine the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract.

## Transportation CRM / Quotation / Work Order Points

Source references:

```text
1 Functional Requirements: Transportation Sales & Operations Module
1.1 CRM: Lead Ingestion & Opportunity Management
1.3 Quotation & PBL T&C Master
1.4 Work Order, Addressing & GST Complexity
1.7 Billing & Profitability analysis
```

Relevant requirements:

```text
- Leads may be automatically ingested from external sources such as Tender Tiger, Projects Today and mail campaigns.
- A Lead converts to Opportunity only after formal enquiry such as RFQ, tender document or recorded verbal confirmation.
- Opportunity must be marked Ready to Quote by an authorized user before operational rate discovery.
- Vendor negotiations and rate revisions must be linked to Opportunity and auditable.
- PBL T&C master library is required, with clauses categorized by risk type and business line.
- Quote preparation must allow contextual T&C selection and protect mandatory clauses from omission without secondary approval.
- Quote versioning must archive previous versions and require reason for revision.
- Work Order line-level billing and shipping addresses are required.
- Work Order line-level T&C overrides are required.
- GST must be determined at invoice line level based on billing GSTIN, shipping state and place of supply.
- Risk and penalty clauses such as LD, EMD/security deposit refunds and submission deadlines must be tracked.
- Invoicing must respect T&C compliance checks before final posting.
- Profitability reporting is expected at Work Order line, Customer, Branch and Equipment levels.
```

Prototype implication:

```text
The current prototype preserves Lead -> Account -> Opportunity -> Commercial Offer -> Work Order shell traceability only. It does not implement full Transportation billing, GST, quote versioning or T&C approval.
```

## Equipment Hire Lead / Opportunity

Source references:

```text
2 Functional Requirements: Equipment Hire Module
2.1 CRM: Lead & Opportunity Management
Annexure-1 - Leads
Annexure-2 - Opportunities
```

Relevant requirements:

```text
- Leads may be ingested from Probe42, Projects Today and Tender Tiger.
- Marketing or Sales users must be able to manually create leads from walk-ins, phone calls, references and events.
- Every lead should capture source metadata, original communication documents and timestamps.
- Lead communications should be recorded as user-stamped chronological logs.
- Lead lifecycle includes New, Contacted, Under Nurturing, Qualified and Lost/Not Interested.
- Lost/Not Interested requires user remarks and reason codes.
- Tasks and reminders may be sent by SMS or WhatsApp.
- Lead converts to Opportunity only after formal RFQ or enquiry.
- Opportunity can include site surveys, route surveys, technical feasibility notes and risk assessments before quoting.
```

Prototype implication:

```text
Current Lead and Opportunity foundations cover a subset. AI/external ingestion, task reminders and full survey/risk document workflows remain deferred.
```

## Quotation / Commercial Rule Engine

Source references:

```text
2.2 Quotation & Commercial Rule Engine
Annexure-3 Terms and Conditions
7.1 CRM & Sales Governance
```

Relevant requirements:

```text
- Quotations must support multiple equipment items in one quote.
- PBL T&C master library must support clause selection and customization.
- Users should cross-check historical rates for similar equipment.
- Quoted margins should be evaluated against thresholds; deviations trigger approvals.
- Only approved quotations may be shared with customers.
- Quote revisions require versioning and audit trail.
- Quote margin should be greater than or equal to least margin per Annexure-2 validation note.
```

Prototype implication:

```text
Current Commercial Offer lines, pricing evidence and selected basis-rate foundation support future quote engine work. Structured Commercial Offer revision, resubmission, revision reason, lineage and revision-history foundations are now implemented (Slices 6J, 6K, 6L, 6M, 6M.1) - see "Current Design Reconciliations" -> "K1. Commercial Offer revision status" below for the accurate current status. Complete production approval orchestration, margin threshold calculation/approval, production document rendering, production numbering, submitted-document finalization/immutability/tamper evidence, and complete T&C deviation/new-clause governance remain future work.
```

## Work Order Structure And Governance

Source references:

```text
2.3 Work Order (Contract) Structure & Governance
7.2 Hiring Contract & Hierarchy Rules
Slice 6D.1 frozen handoff contract
```

Relevant requirements:

```text
- Work Order line-level shipping addresses and billing GSTNs are required.
- Line-level T&C customization is required, with header defaults available.
- Work Orders should specify documents to be submitted with invoices.
- Available documents in other modules should be mapped/attached to invoices before billing due date.
- Customer master should be PAN-based with GSTN billing addresses as children.
- Billing address must lock once an E-Invoice is generated.
- Contract valid-from and valid-to dates are mandatory.
- Log sheet generation and billing must be blocked beyond validity unless approved extension exists.
- Contract expiry alerts should trigger 30 days before expiry.
- Contract renewal may be same terms or revised terms with approval.
- Credit limit gating should validate active contracts and outstanding receivables before Work Order confirmation.
```

Prototype implication:

```text
Current Work Order is a shell only. Customer Master activation, release/posting, line-level GST/site/billing terms, document checklist, validity gates and credit/readiness gates remain later production work.
```

## Billing Basis And OT Logic

Source references:

```text
2.4 Billing Basis & Overtime Logic
Annexure-10 - Log Sheet
7.4 Billing & Financial Logic
```

Relevant requirements:

```text
- Billing UOMs include Hour, Shift, Day and Month.
- Hour-based billing uses actual working hours and does not apply OT or breakdown logic.
- Shift/day billing uses per shift/day and applies OT and breakdown deductions based on contractual hours.
- Month-based billing includes OT Normal Hours and OT Engine Hours modes.
- Contracted hours must be completed before OT can be claimed in month-based billing.
- Different rates may apply for normal hours, OT, breakdown, second shift and holidays.
- Monthly pro-rated hourly rates may vary by month length.
- OT rates may be percent of normal rate or separate rates.
- Customer ERP restrictions may cause holiday/weekly-off hours to be billed as normal-day OT.
- Idle hours caused by customer-side issues are billable if customer-signed and treated as working hours.
- Breakdown deductions and same-day OT offsetting may be configurable.
```

Prototype implication:

```text
The current prototype does not implement billing. Future Billing slices should use the Annexure-10 examples and preserve Work Order line traceability.
```

## Log Sheet Management

Source references:

```text
2.5 Site Execution & Log Sheet Management
Annexure-10 - Log Sheet
```

Relevant requirements:

```text
- Daily log sheets should be generated for each active equipment line.
- Log sheets capture start/end times, breakdown periods, HMR and odometer readings.
- Customer-supplied fuel can require expected-vs-actual fuel variance calculation.
- Excess fuel consumption creates parked deductions for billing review.
- Equipment replacement/transshipment stops old log sheets and starts new sheets while preserving audit trail.
- Extra KM and additional crew charges should be calculated where contract terms define them.
- Unsigned log sheets should be flagged as non-billable in later governance.
```

## Fleet / Crew Operations

Source references:

```text
2.6 Fleet & Crew Operations
5.1 Employee & Operator Master Data
Annexure-8 - Employee Master
Annexure-17 - License Data
```

Relevant requirements:

```text
- Equipment assignment history must track every asset assigned to a Work Order.
- Hired equipment vendor log sheets require a posted Vendor Purchase Order before posting.
- Crew assignment from Employee Master is mandatory per shift for PBL-owned equipment.
- Crew changes should stop old crew attendance and start new crew attendance on transshipment.
- Employee master must capture operator/driver identity, statutory documents and driving licence data.
- Driving/operator licence expiries require alerts.
```

Prototype implication:

```text
Equipment assignment, crew eligibility and log sheet foundations are later slices. They must preserve Work Order line and source Commercial Offer line identity.
```

## Compliance / Logistics Controls

Source references:

```text
2.7 Compliance & Logistics Control
7.5 Compliance & Statutory Controls
```

Relevant requirements:

```text
- Work Order posting may generate mobilization Transportation order under PBL Own Loads.
- Demobilization may generate Transportation order when contract completes and conditions apply.
- HR compliance documents such as PF/ESI challans, wage register and bank transfer proof must block Ready for Submission until uploaded/verified.
- Work Order closure is blocked until equipment and personnel gate passes are returned.
- Closing fuel reconciliation can block contract closure.
- Surepass or similar verification is expected for new vendors/drivers where integrated.
- E-Invoice and E-Way Bill integration is expected later.
```

Prototype implication:

```text
These are production controls. The prototype Work Order shell does not post, mobilize, demobilize, bill or close operationally.
```

## Invoicing / Financial Governance

Source references:

```text
2.8 Invoicing & Financial Governance
6 Accounts & Finance
7.4 Billing & Financial Logic
```

Relevant requirements:

```text
- Approved log sheets convert to draft invoices based on billing frequency.
- Invoice submission mode and courier proof should be tracked.
- Customer escalations can be suggested by overdue day bands.
- Invoice rejection within 24 hours can allow cancellation/reupload.
- Invoice rejection after 24 hours requires credit note handling.
- Corrections should release locks where legally allowed and reverse accounting entries where applicable.
- Duplicate invoice prevention and purchase three-way match are hard controls in finance governance.
```

## Hard Gates Relevant To CRM/Hiring

Source references:

```text
7 Business Rules
```

Hard gates:

```text
- Lead conversion requires formal enquiry/RFQ.
- Quote revision requires version and reason.
- Mandatory T&C omission requires secondary approval.
- Work Order confirmation/release must respect credit readiness.
- Work Order line billing GSTN/address locks after E-Invoice.
- Invoice readiness depends on required HR/customer documents where applicable.
- Work Order closure depends on gate pass return and fuel reconciliation where applicable.
- Backend authorization and auditability are required by the NFR baseline.
```

## Current Design Reconciliations

This section preserves each original source requirement summary above and states, separately, how the current preferred design relates to it. Where a reconciliation below differs from the source suggestion, the reconciliation is the current working direction; the source summary above remains as historical input. See `docs/source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md` for the full directional design these reconciliations are drawn from, and the unresolved decisions in its Section 16 (D-02 onward; D-01 is resolved by ADR-015).

### K1. Commercial Offer revision status

The source implies full quote versioning is a single future block. That is now out of date. Accurately:

```text
- Structured Commercial Offer revision, resubmission, revision reason, lineage and revision-history foundations have been implemented (Slice 6K revisions, Slice 6L customer response/award outcome, Slice 6M lifecycle guidance, Slice 6M.1 terminal-status guard).
- Complete production approval orchestration remains future work (see 6G.1, 6H.1).
- Margin threshold calculation and approval remain future work.
- Production document rendering (quote/PDF generation) remains future work.
- Production Commercial Offer numbering remains future work; the prototype `CO-000001` style is identity-derived only.
- Submitted-document finalization, immutability or tamper evidence remain future work.
- Complete T&C deviation and new-clause governance remain future work (see 6G.1).
```

Do not claim that production quote document generation is complete; it is not.

### K2. Credit gate

The source proposes a Work Order-stage credit block. Preserved as the original requirement; current reconciliation:

```text
- Substantive credit and exposure assessment occurs before Commercial Offer submission (the Commercial Offer credit/exposure gate; deferred in the prototype to Slice 6I.3, manual foundation in 6I.2).
- An over-limit Commercial Offer is held until authorized exception approval, not silently blocked or silently allowed.
- Work Order release verifies customer activation, commercial completeness and the applicable Commercial Offer credit-decision reference; it does not perform an unrelated second approval by default.
- Later policy may require re-evaluation when material exposure or commercial facts change.
```

### K3. Explicit Work Order creation

The source references automatic same-term extension in places. Current reconciliation:

```text
- No silent automatic Work Order creation.
- An accepted Commercial Offer, an accepted Supplementary Offer or Change Quotation, or a validated Work Order Amendment may make an action eligible.
- Actual Work Order creation or amendment application remains an explicit, controlled and auditable action (see the frozen Slice 6D.1 handoff contract and the Slice 6O.2 amendment-intake boundary).
- Any future automation requires separate approval and must preserve authorization and source-line traceability.
```

### K4. Vendor Purchase Order gate

The source states a hard PO gate for hired-equipment vendor log sheets ("Hired equipment vendor log sheets require a posted Vendor Purchase Order before posting"). Preserved as the original requirement; current reconciliation:

```text
- Current design uses a Vendor Hire Agreement as the proposed primary commercial/operational record (System-of-Record Matrix Section 11).
- Whether every vendor hire must also have an approved or posted Purchase Order is unresolved decision D-04 in that matrix.
- Agents must not silently implement a universal PO hard block.
- Agents must not omit Procurement/PO traceability.
- The design should permit a procurement or PO reference on the Vendor Hire Agreement.
- Hiring Operations, Procurement and Finance must confirm the final production gate before this is treated as settled.
```

### K5. Mobilisation Transportation integration

The source states Work Order posting "may generate mobilization Transportation order" automatically. Current reconciliation:

```text
- Current preferred direction is a controlled Transportation handoff or interface (System-of-Record Matrix "Transportation handoff" record), not silent automatic order generation.
- The exact trigger and automatic-versus-confirmed behaviour remain detailed-design decisions.
- Do not tightly couple Work Order posting to the existing internal Transportation implementation.
- Use an approved contract with idempotency, retry, failure visibility and audit, consistent with the Integration Governance rules in the matrix.
```

### K6. Billing Worksheet and draft invoice

The source states approved log sheets "convert to draft invoices" directly. Current reconciliation:

```text
- The current preferred design introduces an authoritative Billing Worksheet between operational evidence (log sheets) and Finance invoicing.
- Structured manual entry and automated calculation engines are parallel producers of the same controlled Billing Worksheet.
- Maker-checker approval and the support-document/invoice checklist apply before Finance handoff.
- The final boundary for first draft invoice creation (whether Plum creates it directly from the Hiring handoff package, or an intermediate draft exists in Hiring) remains decision D-06 in the System-of-Record Matrix.
- Do not directly generate a final invoice merely because a log sheet is approved.
```

### K7. Work Order-line T&C changes

The source requires line-specific T&C (line-level shipping/billing address, line-level T&C overrides). Preserved as the original requirement; current reconciliation:

```text
- Line-specific terms normally originate from the accepted Commercial Offer line or approved header defaults.
- A material post-award change must not be an uncontrolled direct Work Order edit.
- Use the appropriate Supplementary Offer or Change Quotation (Slice 6O.1) and Work Order Amendment (Slice 6O.2) path for a material change.
- A controlled administrative correction may be designed where it does not change the commercial agreement and is authorized and audited (see the `ADMINISTRATIVE` amendment type in the Work Order Amendment contract).
```

### K8. External integrations

The source names direct integrations (Tender Tiger, Projects Today, Probe42, Surepass and similar). Current reconciliation:

```text
- Named direct integrations remain target capabilities unless removed by an approved decision.
- Phase 1 must not depend on a named provider unless feasibility, licensing and delivery timing are confirmed.
- Reviewed manual input, upload, a mock provider or an adapter-backed data source may be used initially.
- The provider interface must remain replaceable and loosely coupled, consistent with the Integration Governance rules in the System-of-Record Matrix.
```

Updated 11 August 2026: the second bullet's condition is now **satisfied for SurePass specifically**, because SurePass is already in use at PBL. It continues to apply unchanged to Tender Tiger, Projects Today, Probe42 and other named providers. See K10.

### K9. Signed log-sheet evidence

Not explicitly a single source statement but implied throughout the Log Sheet and billing sections above. Current reconciliation:

```text
- Where customer sign-off is contractually required, the verified customer-signed log sheet is the primary billing evidence.
- GPS, IoT, HMR and telematics data support validation and reconciliation.
- Those feeds do not automatically replace signed evidence.
- Unsigned or unverified log sheets are non-billable unless an authorized and traceable exception is approved.
```

### K10. SurePass legal identity validation at Account onboarding

Added 11 August 2026. The source mandates SurePass validation of PAN, GSTN and bank-account ownership during **vendor** onboarding, and Aadhaar/PAN/bank validation during **employee** onboarding, and requires Surepass verification of new vendors and drivers. It does not separately state the customer/Account case. Current reconciliation, per `ADR-015`:

```text
- The same pattern applies to Account / Qualified Prospect onboarding: PAN and GSTIN are passed
  to SurePass for validation, and the validated response is used to obtain/confirm authoritative
  legal-entity information where the service supports it.
- A routine manual Accounts/Finance approval is not required to reconfirm a fact SurePass has
  already validated successfully. Human review is exception-driven only (mismatch, validation
  failure, incomplete/ambiguous response, policy exception, or prolonged provider unavailability
  requiring the authorized manual route). A temporary outage alone is non-blocking.
- SurePass validates facts. It does not grant business approval. Do not describe it as approving
  an Account, a customer, or a credit decision.
- Legal identity validation, credit assessment/approval and financial exposure remain three
  separate concerns. SALES_MANAGER performs the credit assessment; the CRM Account Master is
  authoritative for approved Credit Amount and Credit Days; and the configured Department Head
  or Managing Director approves. Finance/Accounts consumes the validated legal master and
  monitors exposure.
- The provider interface must still remain replaceable and loosely coupled (K8, bullet 4). A
  temporary SurePass outage must not prevent an Account from existing or hard-block operational
  work. Keep verification pending, retry and audit; use an authorized manual route for prolonged
  unavailability. Failed validation and returned mismatches remain exceptions.
- Accounts owns the exception queue by default, with configurable authorized Sales assignment.
  SurePass-returned identity values are authoritative, while source values/mismatches remain as
  evidence. Retention and periodic re-verification values are deferred policy parameters.
```

> **Clarification, 13 August 2026 (PBL decision).** The 11 August reconciliation above is
> preserved unchanged. Its wording `SALES_MANAGER performs the credit assessment` records the
> position at that date and the initial/default mapping, but it is no longer the authorization
> rule. Credit assessment now requires an authenticated user holding a current, active, scoped
> `CREDIT_ASSESSOR` authority assignment, resolved through `ORA-001`; authorized administrators may
> reassign that authority without a code change. Preparing a credit proposal remains a Sales
> activity and is not the assessment. Credit approval is unchanged and remains a separate
> `CREDIT_APPROVER` assignment under the configured Department Head / Managing Director policy.
> See `ADR-015` (amended), `ACP-001`, `ORA-001` and `OPEN_QUESTIONS.md` Q-07.

See `docs/agent/ARCHITECTURE_DECISIONS.md` (ADR-014, ADR-015) and `docs/continuity/ACCOUNT_IDENTITY_VALIDATION_CORRECTION_2026-08-11.md`. This reconciliation does not alter the preserved source wording elsewhere in this extract.

## Relationship To Slice 6D.1

This extract does not change the frozen handoff:

```text
Accepted Commercial Offer -> Work Order shell
```

Slice 6D.1 still controls the prototype-to-production handoff contract. ERP source requirements inform later production slices after the shell.
