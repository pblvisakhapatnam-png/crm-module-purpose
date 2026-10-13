# Slice 4B - Commercial Offer Detail / Profile Shell

## Objective

Refine the Commercial Offer / Quote profile page into a clearer read-only shell without changing the foundation backend contract.

## Scope

In scope:

```text
- Replace the basic Slice 4A Commercial Offer detail page with a structured profile shell.
- Show read-only sections for offer snapshot, Opportunity context, Account context, commercial summary, remarks, workflow position, deferred boundaries and audit/traceability.
- Keep Commercial Offer navigation consistent with the current page-level action pattern.
- Remove the stray create-page prefill logic from the Commercial Offer detail page.
- Preserve Admin/Management Read Only event shortcut behavior without weakening backend event permissions.
```

Out of scope:

```text
- Backend API changes.
- Commercial Offer update or submission workflow.
- Quote line items.
- Rate master.
- Revision handling.
- Approval workflow.
- Credit checks and exposure consumption.
- Award capture.
- Work Order handoff.
- Billing, OT, breakdown and invoice logic.
```

## Minimum gate

```text
1. Frontend build passes.
2. Frontend test script passes.
3. Backend pytest is recommended as a regression check but no backend code changed.
4. Manual happy path: open an existing Commercial Offer and confirm all profile shell sections display.
5. Manual navigation path: Back to Commercial Offers, Open Opportunity, Open Account where present, and View recent business events where permitted.
6. Manual permission path: Finance can view the read-only profile and cannot see event access if not authorized.
7. Docs and NEXT_STEPS updated.
```

## Implementation notes

Commercial Offer profile remains read-only in Slice 4B.

The profile displays Account context only when the linked Opportunity has Account context available through the Commercial Offer read API. A Commercial Offer linked to an Opportunity without an Account correctly shows that no Account is linked yet.

The profile uses page-level actions at the top and action links in the audit/traceability section. A later UI cleanup can introduce a shared page-header/action component across operational pages.
