# Slice 6D.4 Acceptance - ERP Source Document Import And Agent Extract Pack

## Scope Confirmation

This is a documentation/source-reference slice only.

Expected result:

- source `.docx` files remain unchanged;
- Markdown extracts and source register are present;
- T&C JSON fixture examples are valid JSON;
- future agents can locate source-derived CRM, Hiring, T&C, billing, field and asset references;
- no application code, runtime configuration, schema, migration, contract or test files are changed.

## Acceptance Checklist

| Check | Expected Result | Status |
| --- | --- | --- |
| Source document register exists | `docs/source/SOURCE_DOCUMENT_REGISTER.md` lists both source `.docx` files | Pass |
| Functional full-text extract exists | `ERP_FUNCTIONAL_SPEC_FULL_TEXT_EXTRACT.md` exists and states extraction limitation/source-of-truth note | Pass |
| NFR full-text extract exists | `ERP_NFR_FULL_TEXT_EXTRACT.md` exists and states extraction limitation/source-of-truth note | Pass |
| CRM/Hiring curated extract exists | `CRM_HIRING_RELEVANT_REQUIREMENTS_EXTRACT.md` gives source-referenced planning summary | Pass |
| T&C extract exists | `TERMS_AND_CONDITIONS_EXTRACT.md` includes Transportation and Equipment Hiring source-derived clauses | Pass |
| Hiring billing extract exists | `HIRING_BILLING_RULES_AND_EXAMPLES_EXTRACT.md` captures billing bases and examples as source-derived planning notes | Pass |
| Field annexure index exists | `FIELD_ANNEXURES_INDEX.md` identifies relevant field annexures for later extraction | Pass |
| Tools/assets extract exists | `TOOLS_AND_ASSET_ANNEXURES_EXTRACT.md` captures tool and asset reference areas | Pass |
| T&C clause fixture validates | `tc-clause-library-demo.json` parses as JSON | Pass after local validation |
| T&C selection fixture validates | `tc-selection-example-commercial-offer.json` parses as JSON | Pass after local validation |
| Docs-only scope preserved | No app code/runtime/schema/test/contract changes | Pass |

## Validation Commands

Run:

```powershell
git diff --check
Get-Content -Raw docs\agent\fixtures\terms-and-conditions\tc-clause-library-demo.json | ConvertFrom-Json | Out-Null
Get-Content -Raw docs\agent\fixtures\terms-and-conditions\tc-selection-example-commercial-offer.json | ConvertFrom-Json | Out-Null
```

## Known Manual Gaps

- The `.docx` to Markdown full-text extract is intended for agent readability and search. It is not a legal or formatting-perfect conversion.
- Table-heavy annexures should be checked against the `.docx` source before production implementation.
- T&C clause text in JSON is normalized demo text, not final legal wording.

