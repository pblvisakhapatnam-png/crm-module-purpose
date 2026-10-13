# Terms And Conditions Fixture Pack

## Purpose

This folder contains safe demo/reference examples for the future T&C Master / Clause Library foundation.

The examples are derived from the ERP Functional Requirements Specification source document and normalized for agent-readable planning. They are not seed data, not runtime fixtures and not legally approved final contract wording.

## Source Documents

Primary source:

```text
docs/source/current/requirements/PBL_ERP_Functional_Requirements_Specification_2026-05-19.docx
```

Agent-readable extracts:

```text
docs/source/SOURCE_DOCUMENT_REGISTER.md
docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md
docs/reference/erp-source-extracts/ERP_FUNCTIONAL_SPEC_FULL_TEXT_EXTRACT.md
```

The `.docx` source remains the source of truth. The Markdown extract and JSON files are reference aids for future implementation agents.

## Files

```text
tc-clause-library-demo.json
tc-selection-example-commercial-offer.json
```

## Use In Future Slices

Use these examples when planning or testing:

- Slice 6E - T&C Master / Clause Library Foundation.
- Slice 6F - Commercial Offer Header T&C Attachment Foundation.
- Slice 6G - Commercial Offer T&C Readiness And Recommended Clause Foundation.
- Slice 6G.1 - T&C Deviation and New-Clause Approval Foundation.

Do not load these files into production as-is. Production T&C content must be reviewed and approved by PBL before use.
