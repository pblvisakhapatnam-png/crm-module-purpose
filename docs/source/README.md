# Source Documents

## Purpose

This folder stores the source-of-truth ERP-wide documents and current directional governance documents for the PBL ERP programme.

These documents cover more than the current CRM + Equipment Hiring prototype. They include ERP-wide functional and non-functional requirements across CRM, Transportation, Equipment Hire, Maintenance, Purchase, Inventory, HR, Payroll, Finance, Accounts, controls, annexures and reporting, plus the current CRM/Hiring System-of-Record governance direction.

## Folder structure

```text
docs/source/
├── README.md                       This file.
├── SOURCE_DOCUMENT_REGISTER.md      Full register of source documents and derived extracts.
├── current/
│   ├── requirements/                Formal current requirements sources.
│   │   ├── PBL_ERP_Functional_Requirements_Specification_2026-05-19.docx
│   │   └── PBL_ERP_Non_Functional_Requirements_2026-05-19.docx
│   └── governance/                  Current governance and directional-design documents.
│       ├── 03_PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.docx
│       └── PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md
└── historical/                      Superseded or historical source documents retained for traceability.
```

`docs/source/current/requirements/` holds the formal ERP-wide functional and non-functional requirements specifications. They describe business intent and requirement detail as understood when each document was prepared.

`docs/source/current/governance/` holds the current CRM + Equipment Hiring System-of-Record Matrix: a directional working design for system-of-record ownership, business accountability and control boundaries. It is current guidance, not a frozen contract; see the intentional DOCX/Markdown difference below and the authority hierarchy in this file.

`docs/source/historical/` holds superseded or historical source documents kept only as traceability evidence. See `docs/source/historical/README.md`.

A related but separate folder, `docs/reference/erp-source-extracts/`, holds derived machine-readable extracts. These are not formal source documents; see `docs/reference/erp-source-extracts/README.md`.

Keep the `.docx` files in the repo as source-of-truth references. Do not modify the binaries during normal agent work.

## Authority hierarchy

When a source document, extract, matrix or other reference appears to conflict with something else in the repository, resolve the conflict using this order, highest first:

```text
1. Current explicit human instruction or approved decision
2. Frozen contracts and approved architecture decisions
3. Accepted requirements and active slice acceptance criteria
4. Current module contracts and active implementation documentation
5. Current source and reference documents (this folder and docs/reference/erp-source-extracts/)
6. Historical continuity records and superseded drafts
```

An original source document is authoritative for what that source document said when it was prepared. That does not mean it automatically overrides a later explicit PBL decision, an approved business rule, a frozen contract, an accepted architecture decision or a current implementation instruction. The latest approved decision controls where it intentionally refines an earlier source. The older source wording must remain preserved as historical input; it must not be silently erased. A difference between an older source position and a later approved decision must be reconciled and recorded, not hidden.

## Binding versus directional guidance

Source documents, matrices, vendor papers, requirement notes and earlier design documents describe business intent, current understanding and preferred direction at the time they were prepared.

Unless a provision is explicitly classified as a frozen contract, approved architecture decision, mandatory control, accepted requirement or current approved business rule, its proposed workflow, ownership arrangement, module boundary, field treatment or implementation approach is **directional guidance**, not a binding technical prescription. During detailed design or implementation, an agent or developer may adopt a different, better solution where it is demonstrably clearer, safer, simpler, more maintainable, more extensible or more appropriate to the actual business requirement, subject to the material-deviation workflow below.

See `docs/agent/ARCHITECTURE_DECISIONS.md` (ADR-013) and `AGENTS.md` for the full governance rule and the properties a substitute solution must preserve.

## Material-deviation workflow

A different solution than the one a source document suggests is acceptable only where it preserves or improves the intended business outcome, authorization and segregation of duties, auditability and traceability, statutory and mandatory controls, NFR compliance, cross-module compatibility, frozen API/event contracts and the agreed API-first modular direction.

Material deviations must not be made silently. The implementation record (slice note, contract update or continuity note) must identify: the original suggestion; whether it was directional or binding; the proposed alternative; why the alternative is better; affected contracts, modules, data, migrations, events, security and tests; and any limitation, risk or deferred work.

A frozen contract, explicit current human instruction, approved business rule or accepted architecture decision may not be changed without human approval.

## Intentional System-of-Record Matrix DOCX/Markdown difference

`docs/source/current/governance/03_PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.docx` is the formal, human-readable System-of-Record Matrix. `docs/source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md` is the agent-readable companion. The Markdown file is **not** a verbatim conversion of the DOCX: it carries the same matrix content plus an additional directional-guidance caution at the top explaining that the matrix records current preferred ownership/control direction rather than a binding technical prescription, and that a documented deviation is permitted where it is demonstrably better. This difference is deliberate and both files should be kept, not reconciled to be byte-for-byte or word-for-word identical. See `docs/source/SOURCE_DOCUMENT_REGISTER.md` for the full registration of both files.

As of 11 August 2026 the Markdown companion carries a second addition the DOCX does not: an "Entries superseded by a later approved decision" notice listing the matrix entries superseded by `ADR-014` / `ADR-015` (integration-driven Account legal identity validation, separation of identity validation, credit assessment/approval and financial exposure, and resolution of D-01 in favor of the CRM Account Master). The superseded matrix rows and original D-01 question remain preserved verbatim; only the notice was added. This is the reconciliation mechanism this README requires, not a rewrite of the source position. See `docs/continuity/ACCOUNT_IDENTITY_VALIDATION_CORRECTION_2026-08-11.md`.

## Agent-Readable Extracts

Agent-readable Markdown extracts of the formal requirements specifications live under:

```text
docs/reference/erp-source-extracts/
```

These extracts are meant to help coding agents search, summarize and plan work without repeatedly opening the Word files. See `docs/reference/erp-source-extracts/README.md` for how each extract is classified and used.

Full-text extracts preserve source wording as-is; if a full-text extract conflicts with the source Word document, the source Word document controls for what the source actually said. Curated extracts may add an explicit current-design reconciliation section; where present, that reconciliation reflects the current approved/preferred direction and should be read alongside the preserved source summary, not in place of the authority hierarchy above.

## Confidentiality

These documents are PBL-specific and intended for NDA-covered project use. Do not publish, upload or copy them outside approved project channels.

## Extraction Limitations

The initial extracts were generated with a local PowerShell Open XML text/table extractor because `pandoc` was not available in the local shell.

Table-heavy, embedded-object, image, header/footer, footnote or complex formatting areas may be imperfect. The source `.docx` remains the source of truth for exact wording and layout.
