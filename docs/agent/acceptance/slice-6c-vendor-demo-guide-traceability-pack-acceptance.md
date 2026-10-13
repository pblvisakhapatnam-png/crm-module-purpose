# Slice 6C Acceptance - Vendor Demo Guide and Prototype Traceability Pack

## Automated checks

Run from repository root:

```powershell
git diff --check
```

Backend and frontend tests are not required if this slice remains documentation-only.

If any application code changes, run the relevant tests and record the reason for the code change.

## Documentation review checklist

Reviewer:

```text
Project owner, vendor reviewer or Slice Test Agent.
```

Starting files:

```text
docs/demo/01_VENDOR_DEMO_GUIDE.md
docs/demo/02_VENDOR_IMPLEMENTATION_HANDOFF_NOTES.md
docs/demo/03_PROTOTYPE_TRACEABILITY_WALKTHROUGH.md
docs/demo/04_PROTOTYPE_SCOPE_AND_DEFERRED_FUNCTIONALITY.md
```

Positive path:

```text
1. Open 01_VENDOR_DEMO_GUIDE.md.
2. Confirm the documented flow is Lead -> Account -> Opportunity -> Commercial Offer -> Commercial Offer lines -> Commercial Offer closure -> Work Order shell.
3. Confirm each step includes purpose, what to demonstrate, key control, event/audit expectation and not-yet-implemented items.
4. Open 03_PROTOTYPE_TRACEABILITY_WALKTHROUGH.md.
5. Confirm it explains Lead to Account, Account to Opportunity, Opportunity to Commercial Offer and Commercial Offer to Work Order shell links.
6. Confirm it covers Account repair / traceability guard and Commercial Offer active/actionable guard.
7. Open 04_PROTOTYPE_SCOPE_AND_DEFERRED_FUNCTIONALITY.md.
8. Confirm deferred functionality is clearly marked.
9. Open 02_VENDOR_IMPLEMENTATION_HANDOFF_NOTES.md.
10. Confirm vendor implementation guidance is stack-flexible and preserves controls rather than copying screens blindly.
```

Expected result:

```text
The demo pack is readable by a vendor or business reviewer without relying on chat history.
```

## Terminology check

```text
- UI/business-facing language uses Account.
- business_party appears only in implementation notes where needed.
- Customer Master activation is clearly separate from Account creation.
- Commercial Offer credit/exposure gate wording is precise and not described as the initial credit assessment.
- Work Order shell is clearly not an operational Work Order.
```

## Deferred functionality check

Confirm these are marked deferred:

```text
Customer Master activation
Finance approval for Customer Master
Work Order release/posting
equipment assignment
crew assignment
log sheets
billing
invoicing
full approval workflow
credit exposure calculation engine
Commercial Offer revisions/versioning
T&C / clause library
production integrations
```

## Permission / security check

Because this is a documentation slice, no live permission behavior changes.

Review the handoff notes and confirm they state:

```text
- Backend authorization remains authoritative.
- Frontend role-awareness is only UX.
- Production must preserve role checks and audit/event behavior.
```

## Manual demo review

Optional but recommended before vendor demo:

```text
1. Login as sales1 / password.
2. Walk through one existing or newly created Lead -> Account -> Opportunity -> Commercial Offer -> Work Order shell path.
3. Use 01_VENDOR_DEMO_GUIDE.md as the presenter guide.
4. Note any places where screen labels or current demo data make the guide confusing.
```

Known manual gaps:

```text
- This slice does not add repeatable demo seed data.
- This slice does not add browser automation.
- This slice does not verify every screen with screenshots.
```

## Acceptance status

```text
Pending human documentation review.
```
