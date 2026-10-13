# Terms And Conditions Extract

## Purpose

This extract turns Annexure-3 T&C source text into stable, source-derived prototype clause records for later T&C Master work.

These are not final legal-approved clauses. They are source-derived prototype clause records for Slice 6E planning and implementation.

Source:

```text
docs/source/current/requirements/PBL_ERP_Functional_Requirements_Specification_2026-05-19.docx
Annexure-3 T&C (Transportation)
Annexure-3 T&C (Hiring)
```

If this extract conflicts with the source `.docx`, the source `.docx` controls for what the source actually said.

## Authority and use of this extract

This file is a derived, machine-readable curated reference based on the identified source document.

The source document is authoritative for the wording and content that existed in that source when it was prepared. This does not mean the source document automatically overrides a later explicit PBL decision, approved business rule, frozen contract, accepted architecture decision or current implementation instruction.

Where a later approved decision changes or refines the source position, the source wording is retained as historical input and the current reconciliation is stated separately below ("T&C Governance Reconciliation").

This extract must not be treated as a final database schema, screen design, service boundary or technical prescription. See `docs/source/README.md` for the full authority hierarchy.

## Extraction Notes

The Transportation T&C source appears as a dense numbered paragraph in the automated extract. It has been normalized into one record per source clause number.

The Hiring T&C source appears as separate clause lines. It has been normalized into one record per source clause theme.

## Transportation T&C Clauses

| Clause ID | Business line | Source clause | Theme | Clause text | Prototype default | Notes for 6E |
| --- | --- | --- | --- | --- | --- | --- |
| TRANS-TC-001 | Transportation | 1 | Transportation charges and GST | Transportation charges are fixed and applicable GST will be 18% charged extra on the service amount. | Mandatory | Tax wording should become configurable by tax setup, not hard-coded forever. |
| TRANS-TC-002 | Transportation | 2 | Loading and unloading scope | Loading and unloading shall be arranged by the customer at customer cost. | Mandatory | Useful as scope/responsibility clause. |
| TRANS-TC-003 | Transportation | 3 | Transit insurance | Transit insurance shall be arranged by the customer at customer cost. | Mandatory | Risk/insurance category. |
| TRANS-TC-004 | Transportation | 4 | Transit documents | All mandatory transit documents for movement of cargo will be provided by the customer. | Mandatory | Document responsibility clause. |
| TRANS-TC-005 | Transportation | 5 | Free time | PBL will allow free time at loading and unloading points as mentioned in the quote/contract. | Optional/contextual | Needs free-time field link in future quote line/WO line. |
| TRANS-TC-006 | Transportation | 6 | Detention charges | After free time, detention charges will be charged per day or part of a day at the rates mentioned in the quote/contract. | Optional/contextual | Needs detention rate fields. |
| TRANS-TC-007 | Transportation | 7 | Payment settlement | Payments should be made within 30 days on submission of bills. | Mandatory by default | Payment-days should link to credit/payment terms. |
| TRANS-TC-008 | Transportation | 8 | En-route/RTO charges | Customer should reimburse RTO charges, penalties or similar expenses incurred, upon submission of receipts. | Optional/contextual | Reimbursable expense clause. |
| TRANS-TC-009 | Transportation | 9 | Billing address | PBL will raise invoice at the address mentioned in the Work Order; if not provided, invoice will be raised as per place-of-supply GST rules. | Mandatory | Strong link to Work Order billing address/GST controls. |
| TRANS-TC-010 | Transportation | 10 | Account statement | Customer shall submit account statement at end of contract or financial year, whichever is earlier. | Optional/contextual | Finance/account reconciliation clause. |
| TRANS-TC-011 | Transportation | 11 | Consignor/consignee information | Customer shall provide consignor and consignee address, contact person name, email ID and cell number for smooth execution and stage-wise SMS/email alerts. | Mandatory where applicable | Contains personal-contact fields; production must apply data governance. |
| TRANS-TC-012 | Transportation | 12 | Quote validity | Quote is valid up to 3 days from date of submission. | Mandatory by default | Quote validity should map to offer validity date. |
| TRANS-TC-013 | Transportation | 13 | Other terms | Other terms include RTA challans as applicable in the source text. | Optional/contextual | Source line appears incomplete; verify against `.docx` before production use. |
| TRANS-TC-014 | Transportation | 14 | Tolerance percentage | Customer shall allow 0.50% tolerance on gross weight of loaded quantity; deduction accepted beyond 0.5% tolerance limit only. | Optional/contextual | Needs weight/tolerance fields in future Transportation quote/WO. |

Transportation notes from source:

```text
- In case of deviation in dimensions, weight, loading point or unloading point, price will be renegotiated accordingly.
- PBL will issue digitally signed invoices; physical invoices may be charged additionally.
- For service issues, the source gives a PBL support email.
- The source states that terms and conditions are dynamic and will be updated at quote time.
```

## Hiring T&C Clauses

| Clause ID | Business line | Source clause | Theme | Clause text | Prototype default | Notes for 6E |
| --- | --- | --- | --- | --- | --- | --- |
| HIRE-TC-001 | Equipment Hire | Equipment Hire charges | Hire charges | Hire charges for the equipment shall be captured in the quote/contract. Source example refers to 100 MT Crawler Crane at Rs.xxxxx. | Mandatory | Amount/equipment should come from offer line, not hard-coded clause text. |
| HIRE-TC-002 | Equipment Hire | Mobilization Charges | Mobilization | Mobilization is customer scope and may be charged as specified in quote/contract. | Optional/contextual | Should attach at header or line depending contract. |
| HIRE-TC-003 | Equipment Hire | Demobilization Charges | Demobilization | If equipment works beyond a stated number of months, no demobilization charges may be levied; otherwise specified demobilization charges apply at de-mobilization. | Optional/contextual | Needs minimum contract months and demobilization rule fields. |
| HIRE-TC-004 | Equipment Hire | GST | GST | Applicable GST on tax invoice shall be charged as per GST rules. | Mandatory | Tax should be controlled by tax setup/GST fields. |
| HIRE-TC-005 | Equipment Hire | Working hours | Working hours and breakdown deduction | Monthly charges are for normal working days excluding Sundays and holidays, with stipulated hours per day and lunch break. Breakdown hours are deducted pro-rata. | Mandatory where monthly/shift/day billing applies | Connect to billing UOM, contracted hours and breakdown logic. |
| HIRE-TC-006 | Equipment Hire | OT Charges | Overtime charges | Beyond stipulated work hours, extra overtime charges apply at the rate specified in quote/contract. | Optional/contextual | Connect to OT mode/rate fields. |
| HIRE-TC-007 | Equipment Hire | Food & Accommodation | Crew food/accommodation | PBL will provide food and accommodation to crew at PBL cost. | Optional/contextual | Crew scope clause. |
| HIRE-TC-008 | Equipment Hire | Diesel | Fuel/diesel | Diesel will be supplied by customer on free basis at specified litres/hour and marching rate; excess consumption may be charged by customer as debit note. | Optional/contextual | Needs fuel scope, agreed average and variance rules. |
| HIRE-TC-009 | Equipment Hire | Advance | Advance payment | Customer has to pay an advance after commissioning of the crane at site as specified in quote/contract. | Optional/contextual | Finance/payment milestone clause. |

## T&C Governance Reconciliation

The clause tables above are preserved exactly as extracted from the source. The following states the current preferred ownership and governance direction alongside them, drawn from `docs/source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md` Section 7.

1. The **Prototype default** column in the clause tables above is a proposed seed classification for prototype/test purposes. It is not final commercial or legal policy.

2. The current ownership working model is:

   ```text
   - Sales - Commercial Offer Owner selects clauses for a specific offer.
   - The Sales - Commercial Offer Owner cannot approve a deviation or a new clause merely because they prepare the offer.
   - One Designated T&C Policy Owner owns the clause catalogue and deviation policy.
   - The working assumption is Commercial Head, unless PBL nominates another named role (unresolved until PBL confirms).
   - Finance reviews clauses with financial impact.
   - Legal Adviser reviews legal-risk wording.
   - Authorized Management approves items above delegated authority.
   ```

3. The clauses in this file are not legal-approved final wording. Legal and commercial review remains required before production use.

4. Each production clause must retain a stable identity and version so a later change can be traced and compared.

5. Standard, Approved Alternative, Deviation and Proposed New Clause must be distinguishable per clause selection, per the System-of-Record Matrix "T&C selection" record.

6. Current System-of-Record and approval governance controls (T&C deviation / new-clause decision, Commercial approval case) apply to any clause selection that departs from a Standard clause; see the matrix Section 6 and Section 7 for the full control detail. Deviation and new-clause approval workflow remain deferred in the current prototype (Slice 6G.1).

Do not rewrite the source clause wording above to make it appear legally approved; it is not.

## 6E Implementation Notes

For T&C Master foundation:

```text
- Store stable clause ID.
- Store source business line.
- Store clause category/risk category.
- Store source clause number/theme.
- Store default mandatory/optional treatment.
- Support header and line applicability.
- Require approval when mandatory clauses are omitted.
- Require approval when clause text is materially modified.
- Do not treat this extract as final legal approval.
```
