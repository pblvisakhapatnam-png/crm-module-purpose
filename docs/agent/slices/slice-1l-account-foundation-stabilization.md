# Slice 1L - Account Foundation Stabilization + Agent Instructions

## Objective

Stabilize the Account / `business_party` foundation before moving to Lead and Opportunity work.

This is a control slice, not a feature slice.

## Included

- Update `AGENTS.md` with Foundation Slice Mode.
- Update PBL's internal working instructions to reference the current Account contract and Foundation Slice Mode.
- Define the lighter foundation-slice testing gate.
- Define backend rebuild/recreate rule for route/schema/service changes.
- Define frontend safe build/restart rule.
- Define reusable UI action-feedback placement rule.
- Define future agent role patterns.
- Update Account contract notes for stabilization and PAN/GST role clarity.
- Update `NEXT_STEPS.md` to move from Account foundation to Lead foundation.

## Excluded

- New Account business functionality.
- New database migration.
- New backend route.
- New frontend UI feature.
- Deep validation hardening.
- Full QA automation expansion.

## Account foundation status after Slice 1L

Account foundation has these guardrail slices in place:

- Slice 1A: `business_party` data model.
- Slice 1B: Account create/list/get backend API.
- Slice 1C: Account list UI.
- Slice 1D: Account create UI.
- Slice 1E: Account detail/profile shell.
- Slice 1F: Account list pagination and session-viewed links.
- Slice 1G: Account Contacts foundation.
- Slice 1H: Account Addresses foundation.
- Slice 1I: Account PAN/GST foundation.
- Slice 1J: Account Documents linkage.
- Slice 1K: Account Ownership / Classification foundation.
- Slice 1L: stabilization and agent instructions.

## Carry-forward rules

- Use Foundation Slice Mode for Lead foundation.
- Keep slices narrow.
- Use one backend route family per sub-domain.
- Keep backend permissions authoritative.
- Create business events for meaningful create/update actions.
- Do not over-test every UX edge case during guardrail creation.
- Record deferred hardening in acceptance docs.
- Use local action messages near the relevant action button.
- Rebuild/recreate backend when route/schema/service files change.
- Use safe frontend build/restart sequence when frontend code changes.

## Result

After this slice, move to:

```text
Slice 2A - Lead Foundation
```
