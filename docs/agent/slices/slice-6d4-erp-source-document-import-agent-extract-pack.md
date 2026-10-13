# Slice 6D.4 - ERP Source Document Import And Agent Extract Pack

## Status

Implemented as a documentation/source-reference slice.

## Objective

Bring the ERP-wide Functional Requirements Specification and Non-Functional Requirements baseline into the repository in a controlled, agent-readable form without changing application behavior.

## Source Documents

Source-of-truth `.docx` documents:

```text
docs/source/PBL_ERP_Functional_Requirements_Specification_2026-05-19.docx
docs/source/PBL_ERP_Non_Functional_Requirements_2026-05-19.docx
```

These source documents are PBL-specific and NDA-covered. They were registered and left unchanged.

## Created Extracts

```text
docs/source/README.md
docs/source/SOURCE_DOCUMENT_REGISTER.md
docs/reference/erp-source-extracts/ERP_FUNCTIONAL_SPEC_FULL_TEXT_EXTRACT.md
docs/reference/erp-source-extracts/ERP_NFR_FULL_TEXT_EXTRACT.md
docs/reference/erp-source-extracts/CRM_HIRING_RELEVANT_REQUIREMENTS_EXTRACT.md
docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md
docs/reference/erp-source-extracts/HIRING_BILLING_RULES_AND_EXAMPLES_EXTRACT.md
docs/reference/erp-source-extracts/FIELD_ANNEXURES_INDEX.md
docs/reference/erp-source-extracts/TOOLS_AND_ASSET_ANNEXURES_EXTRACT.md
docs/agent/fixtures/terms-and-conditions/README.md
docs/agent/fixtures/terms-and-conditions/tc-clause-library-demo.json
docs/agent/fixtures/terms-and-conditions/tc-selection-example-commercial-offer.json
```

## Extraction Method

`pandoc` was checked and was not available in the local environment. The full-text extracts were generated with a local PowerShell Open XML extraction method that reads the `.docx` package and normalizes paragraphs and tables into Markdown.

The full-text Markdown extracts are mechanical extraction aids. Table-heavy areas, embedded objects, headers, footers, comments and footnotes may not be perfect. The `.docx` files remain the source of truth.

## Scope

In scope:

- source document registration;
- full-text Markdown extraction for agent search/readability;
- curated CRM/Hiring requirements extract;
- curated T&C extract;
- curated hiring billing rules and examples extract;
- field-annexure index;
- tools/assets annexure extract;
- safe T&C fixture examples for future 6E/6F/6G slices;
- continuity and future-agent references.

Out of scope:

- no application code;
- no backend or frontend logic;
- no Docker or runtime configuration;
- no database models or migrations;
- no tests or contracts;
- no production T&C implementation;
- no billing engine implementation;
- no SharePoint or external integration implementation.

## Carry-Forward Notes

Future agents should use the extracts for discovery and planning, then verify detailed wording against the source `.docx` when implementing production behavior.

The T&C JSON files are reference examples only. Production clause text, approval behavior and legal wording require PBL review.

## Checks

Required checks:

```powershell
git diff --check
```

JSON fixtures should be validated with PowerShell `ConvertFrom-Json` or an equivalent local JSON parser.

