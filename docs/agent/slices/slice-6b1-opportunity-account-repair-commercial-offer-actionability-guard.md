# Slice 6B.1 - Opportunity Account Repair and Commercial Offer Actionability Guard

## Purpose

Close the gap left after Slice 6A.1: Commercial Offer submit/accept and Work Order shell creation correctly require Account traceability, but a manually created Opportunity with no Account had no controlled repair path.

UI term is Account. Internal/domain/database term is `business_party`. Account does not mean Customer Master.

## In scope

```text
- Add controlled Opportunity Account repair endpoint.
- Link an existing Account / business_party to an unlinked Opportunity.
- Create a minimal/provisional Account / Qualified Prospect and link it to an unlinked Opportunity.
- Reject unauthorized repair attempts.
- Reject silent relinking when the Opportunity already has an Account.
- Record OpportunityAccountRepaired for successful repair.
- Record AccountCreated when repair creates a minimal Account.
- Update Opportunity detail UI to show linked Account or repair panel.
- Add Commercial Offer create guard for one active/actionable Commercial Offer per Opportunity.
- Update Commercial Offer create UI to route/link to an existing actionable offer.
- Preserve Slice 6A/6A.1 linked navigation and Account traceability guard behavior.
```

## Out of scope

```text
- No Customer Master activation.
- No Finance approval.
- No Work Order release/posting.
- No equipment assignment.
- No crew assignment.
- No log sheets.
- No billing.
- No full approval workflow.
- No Opportunity lines.
- No formal Commercial Offer revision/versioning.
- No production Commercial Offer numbering.
```

## Backend behavior

New route:

```text
POST /api/opportunities/{public_id}/account-repair
```

Allowed roles:

```text
ADMIN
SALES_USER
SALES_MANAGER
```

Repair request must provide exactly one of:

```text
account_public_id
create_account
```

`create_account` creates a minimal Account / `business_party` as `QUALIFIED_PROSPECT` and links it to the Opportunity. This is not Customer Master activation.

Already-linked Opportunities return 422 and are not silently relinked.

Commercial Offer create now blocks a second active/actionable Commercial Offer for the same Opportunity.

Active/actionable is defined conservatively as any existing Commercial Offer whose status is not:

```text
WITHDRAWN
REJECTED
CLOSED
```

## Frontend behavior

Opportunity detail:

```text
- Shows linked Account when present.
- If Account is missing, shows an Account repair panel for Sales/Admin roles.
- Repair panel can link a recent existing Account or create a minimal Account / Qualified Prospect.
- Repair success/error messages appear near the action button that triggered them.
```

Commercial Offer create:

```text
- Checks existing Commercial Offers when an Opportunity is selected or prefilled.
- Shows a link when an active/actionable offer already exists.
- The normal create action opens the existing offer instead of creating another unrelated offer.
```

## Notes

Commercial Offer codes remain the existing identity-derived `CO-000001` style and are documented as prototype-only. Production numbering and formal revision numbering are deferred.

No database migration is required because `crm_opportunity.business_party_id` and `business_party` already exist.

The originally attempted obvious filenames `slice-6a-linked-record-navigation-traceability.md` and `slice-6a-1-commercial-offer-account-link-guard.md` do not exist; the actual prior slice files are `slice-6a-linked-record-navigation-traceability-stabilization.md` and `slice-6a1-commercial-offer-account-link-guard-repair-path.md`.
