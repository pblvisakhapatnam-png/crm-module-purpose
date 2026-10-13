# Field Annexures Index

## Purpose

This index points future agents to ERP source annexures and field tables that are relevant for CRM, Hiring, HR, Maintenance, Tools, Asset and Billing work.

Source:

```text
docs/source/current/requirements/PBL_ERP_Functional_Requirements_Specification_2026-05-19.docx
```

The source `.docx` remains the source of truth. Automated table extraction may be imperfect.

See also:

```text
docs/source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md
docs/reference/erp-source-extracts/README.md
```

## Authority and use of this extract

This file is a derived, machine-readable curated reference (a navigation index) based on the identified source document.

The source document is authoritative for the wording and content that existed in that source when it was prepared. This does not mean the source document automatically overrides a later explicit PBL decision, approved business rule, frozen contract, accepted architecture decision or current implementation instruction. Where a later approved decision changes or refines a source position, the source wording is retained as historical input elsewhere and the current reconciliation is stated separately.

This extract must not be treated as a final database schema, screen design, service boundary or technical prescription. See `docs/source/README.md` for the full authority hierarchy.

The annexure fields indexed below are candidates for field catalogues, controlled vocabularies, fixtures and validation review. They do not automatically become mandatory production fields. Statutory, sensitive and personally identifiable fields (for example, employee/licence data under Annexure-8/Annexure-17) require data classification and access review before implementation.

## Annexure Index

| Annexure / field table | Source section | Relevance | Likely future module | Recommended extraction format |
| --- | --- | --- | --- | --- |
| Leads | Annexure-1 - Leads | Lead capture fields, statuses, source metadata and lead lifecycle fields | CRM Lead | Structured JSON schema draft plus field catalog Markdown |
| Opportunities | Annexure-2 - Opportunities | Opportunity fields, RFQ/quote status, quote date, T&C JSON field, validation notes | CRM Opportunity / Commercial Offer | Structured JSON schema draft plus field catalog Markdown |
| Terms and Conditions | Annexure-3 T&C | Transportation and Hiring clause library seed | T&C Master / Commercial Offer | Clause records with stable IDs and applicability flags |
| Equipment Types | Annexure-21 Type of Equipment | Equipment categories such as cranes, manlifts, trailers and prime movers | Asset Registry / Hiring Quote Lines | Controlled vocabulary / lookup table |

Annexures 8 to 20 and 22 to 26 are not part of this copy. They cover Equipment Hiring, HR, maintenance, tyres and finance, which the CRM does not need. PBL keeps the full specification.

## Notes For Future Agents

```text
- Do not infer final database schema directly from annexure tables.
- Use annexures to create field catalogs, fixture examples and validation candidates.
- Classify statutory/personal fields before implementation.
- Preserve Account as UI term and business_party only as internal/domain/database wording.
- Preserve Work Order and source Commercial Offer line traceability for Hiring fields.
```
