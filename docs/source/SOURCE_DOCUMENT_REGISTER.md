# Source Document Register

## Purpose

This register records the ERP-wide source documents and current governance documents imported into the repo, and the agent-readable extracts derived from them. See `docs/source/README.md` for the folder structure and the authority hierarchy that governs how these documents relate to current approved decisions.

## Register: Formal requirements

| # | Source document | Repo path | Date/version | ERP scope covered | Key CRM/Hiring sections | Key annexures | Derived extracts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | PBL ERP Functional Requirements Specification | `docs/source/current/requirements/PBL_ERP_Functional_Requirements_Specification_2026-05-19.docx` | 2026-05-19, from filename/source copy timestamp | Transportation Sales & Operations, Equipment Hire, Equipment Maintenance, Purchase & Inventory, HR & Payroll, Accounts & Finance, Business Rules, Reporting, Annexures | 1 Transportation Sales & Operations; 1.1 CRM; 1.3 Quotation & PBL T&C Master; 1.4 Work Order; 2 Equipment Hire; 2.1 CRM; 2.2 Quotation & Commercial Rule Engine; 2.3 Work Order; 2.4 Billing; 2.5 Log Sheet; 2.6 Fleet & Crew; 2.7 Compliance; 2.8 Invoicing; 7 Business Rules | Annexure-1 Leads; Annexure-2 Opportunities; Annexure-3 T&C; Annexure-21 Equipment Types (the others are not in this copy) | `ERP_FUNCTIONAL_SPEC_FULL_TEXT_EXTRACT.md`; `CRM_HIRING_RELEVANT_REQUIREMENTS_EXTRACT.md`; `TERMS_AND_CONDITIONS_EXTRACT.md`; `FIELD_ANNEXURES_INDEX.md`; T&C JSON fixtures |
| 2 | PBL ERP Non-Functional Requirements | `docs/source/current/requirements/PBL_ERP_Non_Functional_Requirements_2026-05-19.docx` | 2026-05-19, from filename/source copy timestamp | ERP-wide usability, security, auditability, rules engine, integration, performance, availability, data governance, mobile, AI readiness, records management, monitoring, implementation, migration, training and support | Security and access control; auditability and traceability; business rules framework; API-first integrations; performance and availability; mobile and field readiness; records management; monitoring; migration and support | Not annexure-heavy in extract; NFR sections are direct requirement headings | `ERP_NFR_FULL_TEXT_EXTRACT.md` |

Status: current formal requirements sources. These documents describe ERP-wide business intent and requirement detail as understood when each was prepared. Per the authority hierarchy in `docs/source/README.md`, they remain authoritative for what they said at that time, but do not automatically override a later explicit PBL decision, frozen contract, approved architecture decision or accepted requirement recorded in `docs/agent/contracts/`.

**This copy (13 October 2026).** Documents 1 and 2 here are clean copies. In document 1, every tracked change
is accepted and the internal review comments are removed; in both, the author fields read "PBL". The text is
the text the full-text extracts below already read. PBL keeps the reviewed originals.

Document 1 here also holds only the annexures the CRM needs: 1 (Leads), 2 (Opportunities), 3 (terms and
conditions) and 21 (types of equipment). Annexures 8 to 20 and 22 to 26 - Equipment Hiring, HR, maintenance,
tyres and finance - and the spreadsheets embedded in them are not part of this copy; nor are the extracts made
from them, and the full-text extract stops at the same annexures.

## Register: Current governance

| # | Document | Repo path | Status | Purpose |
| --- | --- | --- | --- | --- |
| 3 | Clarified System-of-Record Matrix (DOCX) | `docs/source/current/governance/03_PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.docx` | Current directional governance document | Formal, human-readable matrix of system-of-record ownership, business accountability and control boundaries for CRM + Equipment Hiring. |
| 4 | Clarified System-of-Record Matrix (Markdown) | `docs/source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md` | Current agent-readable governance companion | Same matrix content plus an additional directional-guidance caution explaining that the matrix is directional rather than technically prescriptive, and how a demonstrably better implementation approach may depart from it. **Note:** this is not a verbatim conversion of the DOCX; the additional caution is intentional and both files are kept as separate, deliberately different artefacts. See `docs/source/README.md` for the full explanation of this intentional difference. |

Both documents record the current preferred direction for CRM/Hiring system-of-record ownership. Neither is a frozen contract; where either conflicts with a frozen contract (for example `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md`) or an approved architecture decision, the frozen contract or architecture decision controls. Unresolved decisions are tracked explicitly in the matrix's own Section 16 and must be treated as unresolved, not guessed at. D-01 was resolved by PBL on 11 August 2026 in ADR-015; the remaining decisions D-02 onward remain open unless a later approved record resolves them.

## Register: Derived extracts

All extracts below live under `docs/reference/erp-source-extracts/` and are derived references, not independent requirements. See `docs/reference/erp-source-extracts/README.md` for the full classification and usage rules.

| Extract | Derived from | Kind | Status |
| --- | --- | --- | --- |
| `ERP_FUNCTIONAL_SPEC_FULL_TEXT_EXTRACT.md` | Document 1 | Full-text | Faithful source extract; not current design authority. |
| `ERP_NFR_FULL_TEXT_EXTRACT.md` | Document 2 | Full-text | Faithful source extract; applicability governed by this register and current decisions. |
| `CRM_HIRING_RELEVANT_REQUIREMENTS_EXTRACT.md` | Document 1 | Curated | Curated requirements reference with current-design reconciliation. |
| `TERMS_AND_CONDITIONS_EXTRACT.md` | Document 1, Annexure-3 | Curated | Directional clause-seed reference; not legal approval. |
| `FIELD_ANNEXURES_INDEX.md` | Document 1, all annexures | Curated (navigation) | Navigation and extraction-planning reference only. |
| T&C JSON fixtures (`docs/agent/fixtures/terms-and-conditions/`) | Document 1, Annexure-3 | Curated (fixture) | Safe demo/reference examples for the T&C Master foundation; not seed data, not legally approved wording. |

## Source-Of-Truth Rule

The Word documents under `docs/source/current/requirements/` are the source of truth for exact requirement wording. The System-of-Record Matrix DOCX is the source of truth for the formal governance document; its Markdown companion is the agent-readable version and is intentionally not identical (see above).

Markdown and JSON extracts are agent-readable working copies. If a table, clause or field looks incomplete in an extract, inspect the source `.docx`. If an extract's stated current-design reconciliation appears to conflict with a frozen contract or approved architecture decision, the frozen contract or architecture decision controls; treat the conflict as something to reconcile in documentation, not to resolve by guessing.

## Authority and reconciliation notes

- Original source text in the full-text extracts and in each curated extract's preserved source summary is kept intact; it is not rewritten when a later decision changes direction.
- Current reconciliations (where an extract states one) are maintained in a separate, clearly labeled section of that extract, not blended into the source summary.
- Later approved decisions — frozen contracts, approved architecture decisions, accepted requirements and current module contracts — control over older conflicting source suggestions, per the authority hierarchy in `docs/source/README.md`.
- Unresolved design items (for example, the System-of-Record Matrix's remaining D-02 onward decisions) remain working assumptions until PBL or the project owner confirms them. Do not treat a working assumption as settled. D-01 is no longer unresolved; see ADR-015 and the matrix reconciliation notice.

## Historical documents

No documents are currently held under `docs/source/historical/`. See `docs/source/historical/README.md` for the rules that apply if a current document is later superseded and moved there.

## Extraction Method

Initial extracts were generated with a local PowerShell Open XML text/table extractor because `pandoc` was not available.

Known limitations:

```text
- complex tables may lose layout;
- embedded objects and images are not extracted;
- headers, footers and footnotes may not be represented;
- source table boundaries may be approximated.
```
