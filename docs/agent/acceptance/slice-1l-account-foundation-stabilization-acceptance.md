# Slice 1L Acceptance - Account Foundation Stabilization + Agent Instructions

This is a documentation/control slice. It does not add runtime functionality.

## Required checks

- `AGENTS.md` includes Foundation Slice Mode.
- `AGENTS.md` includes the minimum foundation-slice testing gate.
- `AGENTS.md` includes backend rebuild/recreate guidance for backend route/schema/service changes.
- `AGENTS.md` includes frontend `.next` cleanup and build/restart guidance.
- `AGENTS.md` includes the UI action-feedback placement rule.
- `AGENTS.md` includes future agent role patterns.
- PBL's internal working instructions references `AGENTS.md` and the Account / `business_party` contract.
- Account contract no longer contradicts the Slice 1I PAN/GST hardening decision.
- Account contract includes stabilization carry-forward rules.
- `docs/continuity/NEXT_STEPS.md` points to Slice 2A Lead Foundation.
- No Alembic migration is added.
- No backend or frontend code is changed.

## Automated checks

For this documentation-only slice:

```powershell
git diff --check
```

Backend and frontend runtime tests are not required unless code files were changed.

## Manual review

- Read `AGENTS.md` and confirm the new working mode matches the agreed faster slice approach.
- Read `docs/continuity/NEXT_STEPS.md` and confirm the next slice is Lead foundation.
- Confirm only documentation files are staged for commit.

## Deferred work

- UX consistency pass for moving existing long-page action messages below their relevant buttons.
- Larger QA/hardening agent for detailed validation cases.
- Lead / Opportunity contracts and routes.

## TB-1 fix TB1-604 (4 October 2026): times shown in India's time

Test user: `sales1` / `password` (SALES_USER). Starting URL: `http://localhost:3000/accounts/new`.

1. Note the time on your clock (India). Create an Account; the confirmation's **Created** shows today's date and that
   time, to the minute, in the form "04 Oct 2026, 03:30 pm".
2. Open **Accounts**: the new Account's **Created** shows the same time. Open it: **Created** and **Last updated** show
   it too.
3. Add a contact; its **Created** column shows the time you added it.
4. Open **Leads**: a Lead created now shows the current time in **Created**.

Negative path: before this fix each of these showed the time 5 hours 30 minutes earlier ("10/4/2026, 10:00:00 AM" for
03:30 pm). `frontend/src/components/dateTimeDisplay.test.ts` fails if a page formats a time with a bare
`toLocaleString()` again.
