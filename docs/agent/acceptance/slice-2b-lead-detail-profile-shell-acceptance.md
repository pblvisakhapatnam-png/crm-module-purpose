# Acceptance - Slice 2B Lead Detail / Profile Shell

## Scope check

- [ ] No new backend route is added.
- [ ] No Alembic migration is added.
- [ ] `/leads/[leadId]` page exists.
- [ ] `/leads` company names link to `/leads/{public_id}`.
- [ ] Lead detail uses `GET /api/leads/{public_id}`.
- [ ] Lead detail is read-only.
- [ ] Qualification, conversion, duplicate matching and tasks are not implemented.

## Frontend checks

- [ ] Frontend production build passes.
- [ ] Frontend test script passes, if present.
- [ ] Lead list loads.
- [ ] Lead company link opens the Lead profile page.
- [ ] Lead links do not rely on native browser visited-link colour for session state.
- [ ] Lead profile shows summary, contact snapshot, requirement summary and audit snapshot.
- [ ] Back to Leads link works.
- [ ] Missing/invalid Lead ID shows a friendly not-found/error message.

## Permission check

- [ ] Sales/Admin user can open Lead profile.
- [ ] Finance/Ops/Read-only user can open Lead profile.
- [ ] Sales/Admin placeholder message does not imply qualification/conversion is available now.
- [ ] View-only role placeholder message does not show unavailable workflow actions.

## Deferred checks

- Lead edit validation.
- Lead qualification workflow.
- Lead conversion workflow.
- Lead assignment workflow.
- Lead activity/task timeline.
- Viewed-this-session marker for Lead list, if required later.


