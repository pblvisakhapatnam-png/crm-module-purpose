# Acceptance - Slice 2C Lead Details Update Foundation

## Scope check

- [ ] `PUT /api/leads/{public_id}` exists.
- [ ] Lead details status seed migration exists.
- [ ] No Account, Opportunity or conversion record is created.
- [ ] Lead detail page contains editable early Lead details form for allowed roles.
- [ ] Finance/Ops/Read-only users can view Lead detail but cannot update Lead details.

## Backend checks

- [ ] Backend route changes are visible after backend rebuild/recreate.
- [ ] Alembic head/current is `20260704_0012`.
- [ ] Backend pytest passes.
- [ ] Sales/Admin can update Lead source, contact snapshot, requirement summary, status and assignment field.
- [ ] Finance user cannot update Lead.
- [ ] Invalid early Lead details status is rejected.
- [ ] Invalid email-like value is rejected.
- [ ] Missing Lead update returns 404.

## Frontend checks

- [ ] Frontend production build passes.
- [ ] Frontend test script passes, if present.
- [ ] `/leads/[leadId]` loads Lead detail.
- [ ] Allowed Sales/Admin user can save Lead details update.
- [ ] Success/error message appears below the Save Lead Details button.
- [ ] View-only user does not see the update form.
- [ ] Existing list/detail navigation still works.

## Deferred checks

- Qualification decision validation.
- Conversion to Qualified Prospect / Account.
- Opportunity creation.
- Duplicate Lead / Account matching.
- Sales assignment queues and reassignment approval.
- Lead task/activity timeline.



## View-only role clarification

- [ ] Finance, Ops and Read-only users can view Lead details on the Lead profile page.
- [ ] Finance, Ops and Read-only users cannot update Lead details.
- [ ] The Lead Details section must not look blank or hidden for view-only users.
