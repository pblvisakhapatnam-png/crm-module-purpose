# Historical Source Documents

## Purpose

This folder is reserved for superseded source documents, vendor papers, earlier requirement drafts and prior versions of governance documents such as the System-of-Record Matrix.

No historical documents are currently stored here. This README exists so the folder is trackable in Git and so future agents understand its purpose before adding anything to it.

## Rules for this folder

- Superseded source documents may be stored here when a current document replaces them.
- A historical document remains evidence of a prior requirement, design or decision. It is not automatically current authority; see the authority hierarchy in `docs/source/README.md`.
- Do not edit a historical document merely to make it agree with current design. If a historical document turns out to be wrong or outdated, that is expected — it is a record of what was believed or decided at an earlier point, not a live specification.
- Do not invent or back-fill historical documents that are not actually available. This folder should only ever contain documents that genuinely existed and were genuinely superseded.
- When a current document under `docs/source/current/` is superseded and moved here, record the supersession and replacement in `docs/source/SOURCE_DOCUMENT_REGISTER.md` (superseded-by link, date and reason). Do not silently move a file without updating the register.

## Relationship to continuity records

`docs/continuity/` records project decisions and slice history over time. This folder is specifically for the source *documents themselves* (the artefacts), not for narrative continuity notes. Do not duplicate continuity narrative here; link to the relevant `docs/continuity/` note instead where useful.
