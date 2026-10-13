# ERP Source Extracts

## Purpose

The files in this folder are machine-readable extracts or curated references derived from the formal ERP source documents registered in `docs/source/SOURCE_DOCUMENT_REGISTER.md`. They exist to improve search and agent access to large `.docx` source material without requiring an agent to repeatedly open the Word files.

These files are **not** independent requirements. They do not automatically override current approved decisions, frozen contracts, accepted architecture decisions or current implementation instructions. See the authority hierarchy in `docs/source/README.md` and `docs/agent/ARCHITECTURE_DECISIONS.md` (ADR-013).

Two different kinds of extract exist here, and they are deliberately not treated the same way:

- **Full-text extracts** preserve the source document's wording as extracted. They are not rewritten, modernized or reconciled with current design; where the extracted body differs from current preferred direction, the difference is real and should be resolved by reading the current design documents alongside the extract, not by editing the extracted text.
- **Curated extracts** summarize relevant source sections and, where useful, add an explicit **Current Design Reconciliation** or **Authority and use of this extract** section stating how the current preferred direction relates to the original source suggestion. The original source summary is preserved; the reconciliation is added alongside it, not in place of it.

Conversion from the source `.docx` files may be imperfect, particularly for tables, embedded objects, images, headers, footers, footnotes and complex formatting. The source `.docx` under `docs/source/current/requirements/` remains the source of truth for exact wording and layout. Agents must inspect the formal source document (or the current System-of-Record Matrix / relevant contract for design questions) before making a material decision based only on an extract.

## Classification of files in this folder

| File | Status |
| --- | --- |
| `ERP_FUNCTIONAL_SPEC_FULL_TEXT_EXTRACT.md` | Faithful source extract; not current design authority. |
| `ERP_NFR_FULL_TEXT_EXTRACT.md` | Faithful source extract; applicability governed by the register and current decisions. |
| `CRM_HIRING_RELEVANT_REQUIREMENTS_EXTRACT.md` | Curated requirements reference with current-design reconciliation. |
| `TERMS_AND_CONDITIONS_EXTRACT.md` | Directional clause-seed reference; not legal approval. |
| `FIELD_ANNEXURES_INDEX.md` | Navigation and extraction-planning reference only. |

Annexures 8 to 20 and 22 to 26 are not part of this copy. They cover Equipment Hiring, HR, maintenance, tyres and finance, which the CRM does not need. PBL keeps the full specification. The two curated extracts made from them (billing rules and examples; tools and assets) are withheld with them.

## How to use these files

1. Use a curated extract or the full-text extract to quickly locate a relevant source section and understand its general content.
2. Before relying on an extract for a material implementation or business decision, inspect the formal source `.docx` (`docs/source/current/requirements/`) for exact wording, and inspect `docs/source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md` and the relevant `docs/agent/contracts/` file for current design authority.
3. Where a curated extract's **Current Design Reconciliation** section states a current preferred direction, treat that reconciliation — not the older source suggestion alone — as the current working assumption, subject to the authority hierarchy in `docs/source/README.md`.
4. Where a decision is recorded as unresolved (for example, the remaining System-of-Record Matrix Section 16 decisions D-02 onward), treat it as genuinely unresolved. Do not guess at a resolution on an extract's behalf. D-01 was resolved by PBL on 11 August 2026; see ADR-015 and the matrix reconciliation notice.

## Related documents

```text
docs/source/README.md
docs/source/SOURCE_DOCUMENT_REGISTER.md
docs/source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md
docs/agent/ARCHITECTURE_DECISIONS.md
```
