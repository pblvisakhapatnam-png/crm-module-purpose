# Annex B - Glossary of reference IDs

The records and code comments refer to work by short IDs. This annex says what each kind of ID means, where it is
explained, and which documents the records mention that are not in this copy.

## Words

| Word | Meaning |
| --- | --- |
| Account | A customer company. Inside the code it is `business_party`, because the same company may later also be a vendor or transporter |
| Base Offer, Supplementary Offer, Change Quotation | The three kinds of Commercial Offer: the main offer; an offer for extra work; an offer for a change to work already ordered |
| Basis rate | The market rate chosen as the basis for an offer line's price |
| Existing ERP system | PBL's current ERP system, which holds finance, HR and fleet records today. The records and the code call it Plum |
| Handoff | Turning an awarded offer into a Work Order (doc 05) |
| Reverse auction | A customer's online auction in which suppliers lower their prices in real time, below a ceiling price per item; the lowest acceptable bid wins. A later package (doc 03, group E) |
| Work Order shell | A Work Order just made by the handoff, not yet released |
| Potential and firm exposure | Credit exposure from offers still open, and from awarded work |
| Slice | One numbered step of delivered work, small enough for a person to try in 10 to 20 minutes |
| Contract | The written agreement between two modules (or a module and its users) about what it takes, does and records |
| Frozen | A contract others build on; changed only by a dated, approved amendment |
| Migration | A step that changes the database's structure; there is one chain of them |

## Families of IDs

| ID | Example | What it is | Explained in |
| --- | --- | --- | --- |
| ADR-nnn | ADR-028 | An architecture decision, with its reasons | `docs/agent/ARCHITECTURE_DECISIONS.md`. ADR-011, 012, 029 and 034 are short notes in this copy; ADR-035 is withdrawn; ADR-006 is replaced by ADR-028 |
| Contract IDs | CEX-001, ORA-001 | A production contract between modules | `docs/agent/architecture/CONTRACT_REGISTRY.md` lists each with its file and status; the texts are in `docs/agent/contracts/` |
| Slice numbers | Slice 4G, 6O.2, 7D Part 5 | A step of delivered work. 0 platform, 1 Accounts, 2 Leads, 3 Opportunities, 4 Commercial Offers, 5 the Work Order shell, 6 CRM hardening and the handoff, 7 Work Order detail (Hiring), 8 execution (Hiring), 9 the CRM pilot. ".n" is a follow-up; "Part n" an instalment | Built: `docs/agent/slices/` and `docs/agent/acceptance/`. Not yet built (for example 7A, 7B, 8B to 8H, 6G.1, 6H.1, 6I.3): `docs/agent/FUTURE_SLICES.md` |
| TE-n | TE-1, TE-2B | Technical work: test tools, the move to React and PostgreSQL, the automatic checks, user-test packs | `docs/agent/technical-enablement/`. TE-5, PBL's test-site deployment, is not in this copy |
| PF-1x | PF-1A, PF-1B | Production foundation work: A authority, B shared request rules, C background jobs, D notifications, E documents and targets, F outside systems (F-HR the HR reference). "E1", "E2" are its instalments | `docs/agent/architecture/MODULE_DEPENDENCY_AND_DELIVERY_WAVES.md`; `docs/agent/pf-1a/`, `docs/agent/pf-1f-hr/`. PF-1B to PF-1E are not built |
| PAF-1 | | The production architecture foundation: documents and contracts, no code | `docs/agent/slices/paf-1-production-architecture-foundation.md`, `docs/agent/architecture/` |
| TB-1 | | The full technical review of the code, October 2026: 79 findings | Not in this copy; what is still open is in annex A |
| TB1-nnn | TB1-103 | One finding of that review; a letter (TB1-204 a) is a part of it. The hundreds roughly give the area: 1 boundaries, 2 security, 3 business rules, 4 database, 5 events and logs, 6 shared code, 7 tests, 8 screens, 9 documents | Annex A for the open ones; code comments usually explain the finding where they cite it; two notes in `docs/continuity/` |
| CS-nn | CS-04, CS-05a | A correction package from that review | Annex A. CS-04: the handoff's dated amendments; CS-05a, CS-05c: `docs/agent/slices/`; CS-11: `docs/agent/technical-enablement/` |
| N-nn | N-06 | A smaller observation from that review | Annex A; N-06 is `docs/agent/slices/n06-one-way-to-show-a-time.md` |
| G-103, REP-1, HOF-2 | | A group of review findings; a records package; a decision on repeated handoffs | Not in this copy; HOF-2's outcome is the handoff contract's first amendment |
| WRR-001, ERT-n, ELG-n, HOL-1, 8A core | ERT-1 | Equipment Hiring packages: resource requirements, the equipment reference and kit, machine eligibility and reminders, the holiday calendar, allocating machines | Their files in `docs/agent/slices/` and contracts in `docs/agent/contracts/` |
| D-nn | D-02 | A decision carried from the system-of-record matrix | `docs/continuity/OPEN_QUESTIONS.md` |
| Q-nn | Q-13 | A question put to PBL, and its answer | `docs/continuity/OPEN_QUESTIONS.md` |
| G1 to G7 | G5 | The seven shared module rules (stable identity and version, the acting user from the server, a tracking id, retry safety, structured errors, events, writing only one's own tables) | `docs/agent/architecture/MCF_ADOPTION_RECORD.md` |
| W1-W3, R1-R9, D1-D5 | W1 | Recorded writes, reads and database rules across module boundaries. D1-D5 are not D-01 to D-07 | `docs/agent/architecture/BOUNDARY_EXCEPTION_REGISTER.md`; annex A |
| CF-n, Wave n | CF-2A | Lanes of the contract-freeze plan; delivery waves | `docs/agent/architecture/CONTRACT_FIXTURE_AND_FREEZE_PLAN.md`, `docs/agent/architecture/MODULE_DEPENDENCY_AND_DELIVERY_WAVES.md` |
| HOF-001, FIX-000, SEC-001 | | Rule numbers of the contract-fixture check and the committed-credential check | `scripts/validate_contract_fixtures.py`, `scripts/check_tracked_secrets.py`; `docs/agent/technical-enablement/TE_2CI_GITHUB_ACTIONS_VALIDATION_FOUNDATION.md` |
| DEV-ORCH | | PBL's internal development tooling | Not in this copy; not needed to build or run the system |

## Labels that mean something only inside one record

Review findings such as `ELG1-R1-005` or `9F-R5-A2` (package, review round, item), and labels such as `F-3`, `C1-6`,
`P1`, `NS-PR-01` or `V-04`, are numbered within the record that uses them - a slice, a package or a contract - and are
explained there. The review papers themselves are not in this copy; each record says what was found and what was
done about it.

## Business references and test data

| Pattern | Meaning |
| --- | --- |
| CO-, WO-, RR-, EQ-, AL- followed by digits | A Commercial Offer, Work Order, resource requirement, machine or allocation, as people see it |
| `20260908_0055` | A migration's name; the head of the chain |
| UAT-..., REG-, CHS-, ENG-, OWN-, HU-, T1- | Invented test data: machines, registration and engine numbers made up for tests, testers' own records, the user-test customers |
| PR numbers and commit hashes | Points in PBL's internal history; not in this copy, which has a single commit |

## The slices, by area

### CRM

| Slice | What it built | Record in `docs/agent/slices/` |
| --- | --- | --- |
| 1, 1A-1L | Accounts: the record, list, create, profile, contacts, addresses, PAN and GST, documents, owner and classification, stabilisation | `slice-1-account-foundation.md` and `slice-1a-...` to `slice-1l-...` |
| 2A-2E | Leads: the record, profile, sorting, follow-up activities, the qualify-or-close decision | `slice-2a-...` to `slice-2e-...` |
| 3A-3D | Opportunities: the record, profile, stage; converting a Lead into an Account and an Opportunity | `slice-3a-...` to `slice-3d-...` |
| 4A-4F | Commercial Offers: the offer, profile, status, pricing evidence and the basis rate, lines, closing the lifecycle | `slice-4a-...` to `slice-4f-...` |
| 4G | Market rates per offer line | `slice-4g-market-rates-per-offer-line.md` |
| 5A | The Work Order shell made by the handoff | `slice-5a-work-order-handoff-shell.md` |
| 6A, 6A.1, 6B.1 | Links between records; guards and repairs for missing Account links | `slice-6a-...`, `slice-6a1-...`, `slice-6b1-...` |
| 6D.1, 6D.3 | Freezing the handoff; its example data | `slice-6d1-...`, `slice-6d3-...` |
| 6E-6G | Terms and conditions: the clause library and attaching clauses to offers | `slice-6e-...` to `slice-6g-...` |
| 6H-6J | Before sending: the checklist, evidence, the credit note, commitment | `slice-6h-...` to `slice-6j-...` |
| 6K-6M.1 | Revisions (replaced by 9F), the customer's response, tidying the statuses after it | `slice-6k-...` to `slice-6m1-...` |
| 6O, 6O.1, 6O.2 | The Work Order shell page; Supplementary Offers and Change Quotations; recording a Work Order amendment | `slice-6o-...`, `slice-6o1-...`, `slice-6o2-...` |
| 9A, 9B, 9D, 9E, 9F | Reports; pilot hardening; the conversation log; quotations; offer versions | `slice-9a-...` to `slice-9f-...` |
| CS-05a, CS-05c | An out-of-date save cannot overwrite an offer; a sent offer changes only by a new version | `cs-05a-...`, `cs-05c-...` |
| Upload, language pass | Uploading documents on record pages; plain wording on screens | `document-upload-on-record-pages.md`, `ui-language-pass.md` |

### Shared foundations

| Slice | What it built | Record |
| --- | --- | --- |
| 0, 0A-0G | The platform: database, sign-in, business events, statuses, document records | `docs/agent/slices/slice-0-...` to `slice-0g-...` |
| 9C | Document storage | `docs/agent/slices/slice-9c-document-storage-foundation.md` |
| N-06, entered times | One way to show a time; a typed time comes back as typed | `docs/agent/slices/n06-...`, `docs/agent/slices/entered-times-in-india.md` |
| UI reskin, UI menu | The screens' look; the menu that can be hidden; the shared stylesheet | `docs/agent/slices/ui-cleanup-pilot-reskin.md`, `docs/agent/slices/ui-menu-and-shared-styles.md` |
| PF-1A-E1 to E3 | Permissions on every route; the authority engine (switched off) | `docs/agent/pf-1a/` |
| PF-1F-HR | The HR reference design | `docs/agent/pf-1f-hr/` |
| TE-1 to TE-4, TE-8 | Test data and browser tests; the move to React, PostgreSQL and GitHub Actions; user-test packs | `docs/agent/technical-enablement/` |
| 5B, 6B, 6B.2, 6C, 6D, 6D.2, 6D.4, 6E.2, 6P | Earlier preparation and demonstration work, kept as history | `docs/agent/slices/` |

### Equipment Hiring (not this package)

7C, 7D Parts 1 to 5, WRR-001, ERT-1, ERT-2, ELG-1, ELG-2, 8A core, HOL-1, TE-6 and TE-7, each with its record in
`docs/agent/slices/` or `docs/agent/technical-enablement/`.

## Mentioned but not in this copy

| The records mention | What it was | Use instead |
| --- | --- | --- |
| `docs/agent/tb-1/` | The technical review's working papers | Annex A |
| `docs/continuity/` notes other than the four kept | PBL's running notes on each package | The package's own slice and acceptance records; doc 01 for the current picture |
| `docs/continuity/NEXT_STEPS.md` dated "Update" entries | PBL's running log | The new `docs/continuity/NEXT_STEPS.md` |
| `docs/agent/PLAN.md`, `docs/agent/AGENT_HANDOFF.md`, `docs/agent/AGENT_WORKFLOW.md`, `docs/agent/SKILLS_AND_TOOLS.md`, PBL's internal working instructions | PBL's internal planning and working notes | `VENDOR_START_HERE.md`, docs 01 and 07, `AGENTS.md` |
| `docs/agent/architecture/INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md`, `BOUNDED_INDEPENDENT_REVIEW_METHOD.md`, `PLATFORM_PRINCIPLES_IMPLEMENTATION_REVIEW.md`, `PBL_BUSINESS_REVIEW_GUIDE.md` | PBL's internal review procedures | Doc 08; `AGENTS.md`, "PBL review and approval language" |
| `docs/deployment/`, `deploy/uat/`, `TE_5_UAT_DEPLOYMENT.md` | Hosting files and runbooks for PBL's test sites | Doc 07, "Running it somewhere other than a laptop"; doc 10 |
| `docs/demo/`, most of `docs/planning/` | Earlier demonstration notes and plans, superseded | The vendor documents |
| Proof-script and evidence folders under `docs/agent/technical-enablement/` | Material used to check earlier work | The package records describe what was checked |
| `docs/uat-source/`, the tester PDFs | PBL's user-test working files | The Markdown sheets in `docs/uat/` and `docs/uat-hiring/` |
| `tools/devorch/`, `tools/review/` | PBL's internal development tooling | Not needed |
| Annexures 8 to 20 and 22 to 26 of the functional specification, `HIRING_BILLING_RULES_AND_EXAMPLES_EXTRACT.md`, `TOOLS_AND_ASSET_ANNEXURES_EXTRACT.md` | Equipment Hiring, HR, maintenance, tyre and finance detail, and the extracts made from it | Not needed for the CRM; PBL keeps them |
| `backend/tests/fixtures/plum_vehicle_report_dummified_2026-09-24.csv`, `backend/tests/test_ert1_plum_report.py` | PBL's fleet list, and the Hiring test that read it | Not needed for the CRM |
| `ACCOUNT_IDENTITY_VALIDATION_CORRECTION_2026-08-11.md` | A note on identity validation | `docs/agent/contracts/account-identity-validation-contract.md`; `docs/continuity/OPEN_QUESTIONS.md`, Q-01 to Q-04 |
