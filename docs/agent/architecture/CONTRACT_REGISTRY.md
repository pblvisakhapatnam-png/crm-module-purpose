# Production Contract Registry

## Purpose

This registry is the control point for module contracts. PBL's reviewer updates maturity; an implementer
must not promote or change a contract silently.

## Maturity rules

| Status | Meaning | Parallel implementation allowed? |
| --- | --- | --- |
| `PROPOSED` | Logical draft awaiting review | Owners may refine; consumers may review only |
| `APPROVED` | Semantics accepted, exact implementation may proceed | One owner may implement; consumers may build fixtures |
| `FROZEN` | Change-controlled compatibility boundary | Yes, for named consumers |
| `IMPLEMENTED` | Runtime behavior and tests exist | Yes, subject to its compatibility status |
| `SUPERSEDED` | Historical only; replacement named | No |

## Production foundation contracts

| ID | Contract | Owner -> consumer | Status | Current business position |
| --- | --- | --- | --- | --- |
| `MCF-001` | `shared-module-contract-foundation.md` | Platform -> all modules | `APPROVED` | Required production safeguards; no PBL decision pending |
| `ORA-001` | `organization-authority-authorization-contract.md` | Employee Master -> Authorization/Org Authority -> all approval/business modules | `APPROVED` | Employee Master owns positions/status; ORA owns application authority mappings and suspends/re-evaluates them on HR changes. See ADR-032 (interim SharePoint-backed HR reference source, `docs/agent/pf-1f-hr/`) and ADR-033 (general parameter-driven authority configuration model, `docs/agent/pf-1f-hr/PF_1A_AUTHORITY_CONFIGURATION_MODEL.md`); this contract's text is unchanged |
| `NTF-001` | `notification-delivery-contract.md` | Notifications -> business modules | `APPROVED` | Delivery boundary settled; provider/channel discovery remains implementation work |
| `AIV-001` | `account-identity-validation-contract.md` | Identity Validation -> Account Master | `APPROVED` | ADR-015 and Q-01 to Q-04 settle authority, mismatch and outage behavior; parameter values may be set later |
| `ACP-001` | `account-credit-profile-contract.md` | Account Master Credit Profile -> Exposure | `APPROVED` | INR; CRM Account Master authority; configured Department Head/MD approval |
| `CEX-001` | `credit-exposure-contract.md` | Credit Exposure -> Commercial Offer/Work Order | `APPROVED` | Allocation formulas, no-expiry commitment review and over-limit/overdue holds are settled; only D-02 target-formula cutover remains |
| `WRR-001` | `work-order-resource-requirement-contract.md` | Work Order -> Resource Requirement | `APPROVED` | Planning may begin from a valid shell; commitment/execution requires release; splitting is supported. Its foundation is built by the WRR-001 package (`resource-requirement-api-contract.md`); the required category/type comes from the platform's Equipment Reference (ADR-037). Maturity is PBL's reviewer's to change; this text records only what exists |
| `RMR-001` | `resource-master-reference-contract.md` | Equipment/Employee Masters -> Resource/Authorization consumers | `APPROVED` | Plum Equipment Master is authoritative for owned resources' identity, status and statutory documents; since ADR-037 (24 September 2026) the equipment structure - classes, types, capabilities - is the platform's Equipment Reference, which Plum's data enters through a transformer. For employees and organization positions, the Employee Master **logical capability** is authoritative; Plum contributes the basic employee facts it actually maintains, and (per ADR-032, since PBL has confirmed Plum holds no structured Organisation Unit/Position/Incumbency record) the structured reference data comes in Phase 1 from a governed SharePoint-backed interim source composed behind the HR-reference adapter (`docs/agent/pf-1f-hr/`), with a future `NEW_SHARED_PLATFORM` master as the eventual canonical implementation. This contract's text/semantics are unchanged; only the current-source wording above is refined |
| `VMR-001` | `vendor-master-reference-contract.md` | ERP Vendor Master -> Market Hire/Vendor Payable | `APPROVED` | One centralized vendor identity; current product/interface must be inventoried |
| `RPA-001` | `resource-planning-assignment-contract.md` | Requirement/Availability -> Assignment | `APPROVED` | Temporary reservations supported; first valid atomic commitment wins; partial fulfilment supported. Its owned-machine half is built by 8A core (`resource-assignment-api-contract.md`): machines held for a requirement's units, eligibility decided on each, replacement and history; hired machines wait for `MHA-001`, crew for 8B, and commitment at release for 7B. Maturity is PBL's reviewer's to change; this text records only what exists |
| `ELA-001` | `eligibility-assignment-contract.md` | Eligibility -> Resource Assignment | `APPROVED` | Statutory failures hard-block; configured non-statutory exceptions remain traceable. Its machine half is built by ELG-1 (`eligibility-api-contract.md`): machines' certificates, the rules per jurisdiction, and the decision, which 8A core stores when it allocates; the 60/30/15-day alerts are reminded on screen by ELG-2 (`eligibility-api-contract.md`, "Reminders and escalation"), with configurable schedules and escalation paths by role - email and SMS wait for `NTF-001`, audiences by position for `ORA-001`, `EligibilityExpiring` and the recheck job for ADR-019; the people half comes with 8B. Maturity is PBL's reviewer's to change; this text records only what exists |
| `MHA-001` | `market-hire-assignment-contract.md` | Market Hire -> Resource Assignment | `PROPOSED` | D-03 vendor crew ownership and D-04 universal PO gate remain genuine PBL decisions |
| `RAL-001` | `resource-assignment-log-sheet-contract.md` | Resource Assignment -> Log Sheet | `APPROVED` | Daily evidence per execution-ready billable assignment/line, including equipment and crew/service-only work |
| `WBT-001` | `work-order-billing-terms-contract.md` | Work Order -> Billing Engine | `APPROVED` | Hour/Shift/Day/Month and recorded contract rules; calculation examples require Billing UAT |
| `LBE-001` | `log-sheet-billing-contract.md` | Log Sheet -> Billing Engine | `APPROVED` | Approved evidence only; unsigned evidence needs a traceable exception; corrections are versioned |
| `BIP-001` | `billing-invoice-preparation-contract.md` | Billing Engine -> Invoice Preparation | `PROPOSED` | D-06 must decide whether Plum or Hiring creates the first draft invoice |
| `CMA-001` | `customer-master-activation-contract.md` | Work Order/Account -> Finance activation | `APPROVED` | Sales starts at first Work Order; Finance approves before release; existing Plum customer is reused |
| `APR-001` | `approval-policy-contract.md` | Approval Policy -> business modules | `APPROVED` | Configurable authorities/delegation; maker-checker applies only where the owning policy requires it. Until the HR feed exists, approval rights are set by an administrator (ADR-038, 13 October 2026) |
| `INT-001` | `interaction-contract.md` | Interactions -> CRM record surfaces, future ingestion adapters | `APPROVED` | Shared conversation log (Slice 9D), contract version `2.0` since 11 October 2026 (a date and time with no zone is refused; `1.0` before), implemented. Meets every MCF-001 guarantee except the structured error envelope, which carries a recorded exception owned by and retiring with the PF-1B retrofit |

## Existing contract position

| Contract | Position |
| --- | --- |
| `accepted-offer-to-work-order-handoff-contract.md` | `FROZEN` and implemented as the current Work Order shell handoff; unchanged by PAF-1. Amended twice, each time by a dated section the owner approved at its end: 8 October 2026 (CS-04 part 1: an offer line's quantity handed off once, whole or in parts; no Change Quotation; the latest response must be the acceptance; no "lost" after a handoff) and 12 October 2026 (CS-04 part 2 items c and d: the offer's version on the Work Order and its events, and the lines handed off in `CommercialOfferConvertedToWorkOrder`; a request key and a correlation id agreed for later). Its status is unchanged; the hashes before and after each are in `docs/continuity/NEXT_STEPS.md` |
| Existing Account, Lead, Opportunity, Commercial Offer, Work Order and T&C contracts | Current implementation contracts; retain until a scoped production slice supersedes or freezes a boundary |
| `platform-foundation.md` | Prototype platform contract (Slice 0). Its stack, services and environment variables are historical: a dated note at its top (7 October 2026, TB-1 TB1-904) reconciles them with ADR-016 and ADR-028. Since 8 October 2026 (TB1-107) it also names `GET /api/auth/roles` and `GET /api/platform/config-summary` |
| `reports-contract.md` | Current implementation contract, written 8 October 2026 (TB-1 TB1-107) for Slice 9A's four dashboard reports: a read model over other modules' tables, with its sources and owners. No maturity status; records what exists |
| `workflow-and-events.md` and `documents.md` | Implemented foundations; production hardening and MCF retrofit remain required |

## What the status words mean for PBL

```text
PROPOSED  Draft for discussion. Coding must not depend on it yet.
APPROVED  PBL agrees with the business meaning. The owning team may start coding it.
FROZEN    Other modules may safely build against it. Later changes need a recorded review.
```

## Before PBL accepts a draft

PBL only needs to confirm these business points:

- Is the correct module responsible for the information or action?
- Is the information passed between modules sufficient for the real work?
- Is it clear who may perform, approve or view the action?
- Is it clear what should happen when information is missing, wrong or unavailable?
- Are all unresolved business questions plainly listed?

This review is not required for ordinary production safeguards or a business rule already settled
by a current instruction, approved ADR, frozen contract or accepted requirement. ADR-023 requires
those to be applied directly, citing the source, rather than asking PBL again.

The detailed technical review is performed by engineering. PBL is not expected to approve
technical field names, API terminology, database changes or test design without a plain-language
explanation of their business effect.

`CONTRACT_REGISTRY.md` is the single authority for maturity definitions and current status. Other
architecture records link here rather than redefining the state machine.

## Engineering checks before status changes

After PBL accepts the business meaning, engineering confirms:

- owner and consumers agree the business outcome and ownership;
- authorization and segregation-of-duties effects are explicit;
- identifiers, commands/queries/events and failure behavior are explicit;
- source guidance has been reconciled under ADR-013;
- open policy questions are listed and do not block the approved semantics;
- API, event, data, migration, security and test impacts are reviewed.

A contract becomes `FROZEN` only after PBL agrees that other modules may rely on it and
engineering provides examples and a safe change process. Frozen does not mean it can never
change; it means later changes are checked and recorded.
