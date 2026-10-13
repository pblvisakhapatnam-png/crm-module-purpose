# UI Cleanup - Pilot Reskin

Step 4 of the road to the UAT pilot (`docs/continuity/NEXT_STEPS.md`, "The road to the UAT
pilot"). Foundation Slice Mode.

## Status

Implemented 11 September 2026 on branch `ui-cleanup`, base commit `40f6ff0` (PR #33 merge).
Accepted after four independent review rounds and merged to `main` through PR #34 as `8b7b5ff`
on 11 September 2026.

No migration: Alembic head unchanged at `20260908_0035`. No new route and no permission change.
The frozen Accepted Offer -> Work Order handoff contract and its output are unchanged.

## Owner decisions

| Date | Decision |
| --- | --- |
| 9 Sep 2026 | Gate incomplete pricing at **approval for issue**, not at generation, and do it in this package rather than after the pilot. Supersedes Slice 9E decision 7. |
| 10 Sep 2026 | With the seeded pilot screens in front of them: a **reskin, not a restructure**. Bar: clarity; related sections grouped and clearly demarcated with bounding boxes; appropriate colours; a good look and feel. Restructuring happens after the pilot. |
| 11 Sep 2026 | Approval for issue also refuses a version the offer has **changed since** (stale). |
| 11 Sep 2026 | Scope confirmed as one pull request: quotation approval, reskin including names instead of IDs, records. |
| 11 Sep 2026 | The reskinned Commercial Offer page approved as the look for every detail page. A final language pass will be done by the owner at the end. |

The reskin decision was taken knowing what it cannot do. It groups, boxes and colours sections,
adds a jump-to-section row and uses plain wording; it does not make pages shorter. At 1440x900 the
Commercial Offer Submission tab measured 7.2 screens before and 7.5 after.

## Part A - Quotation approval

### The rule

`approve_commercial_offer_quote_document` now refuses, in this order: a concluded offer
(existing); a superseded version (existing); a version already approved (existing); **any active
line on the offer without an amount**; and **a version whose stored `source_fingerprint` no
longer matches the offer**.

The last two only work as a pair. If a version still matches its offer and every active line on the
offer is priced, then every line in the frozen document is priced. Checking current lines alone
would leave a hole: a version frozen reading "Not fully priced" would become approvable the moment
the missing rate was filled in. Generation still accepts an incompletely priced offer, so Sales can
still produce rough drafts.

The staleness match is taken at one instant: approval reads the whole snapshot in one read-only
`REPEATABLE READ` transaction opened after it holds its locks. Line, T&C clause and Account writers
do not take the offer lock, so a change committing after that instant makes the version stale a
moment later, just as a change a minute after approval does; both are flagged, and the approved
document is fully priced either way. Independent review round 2 showed that the first version,
which read the snapshot part by part, could combine parts from different moments and approve a
version the offer matched at no instant; generation and the listing now read their snapshots the
same single-instant way. Serializing every snapshot writer against approval (round 1) was judged
not worth its cost; the reasoning is in the Commercial Offer contract.

What counts as priced is defined once, in `quote_render.count_unpriced_lines`, which the document's
"Not priced" / "Not fully priced" wording also uses, so the gate and the document cannot disagree.

### One source for the reason, on the server

`quote_document_approval_blocked_reason` produces every refusal message. The approve path raises
it; the serializer exposes it on every returned quotation version as `approval_blocked_reason`:
`null` when, in the state that response was read from, an approval would succeed for a caller
holding `COMMERCIAL_OFFER_QUOTE_APPROVE`. The listing reads that state at one instant. The field
deliberately ignores the caller's role, which remains the route permission's job.

The Commercial Offer page shows the Approve button only when the field is `null`, and shows the
reason in its place otherwise. That is the fix for the Approve button appearing on a version that
could not be approved when the page loaded - a Draft version of a won or lost offer, for example.
The field is advisory: if the offer changes between loading the page and clicking Approve, the
server re-checks under its locks and refuses. The frontend re-derives nothing.

One ordering consequence: the concluded-offer check now runs after the quotation row is looked up,
so approving a quotation id that does not exist on a concluded offer returns `404` rather than
`422`. The lock order - offer, then quotation - is unchanged.

## Part B - Reskin

### Shared building blocks

`frontend/src/components/PageLayout.tsx`, styled in the "Shared page layout" block of
`frontend/src/styles/globals.css`: `PageHeader`, `SectionGroup`, `SectionCard`, `SectionIndex`,
`StatusBadge` and `ReferenceText`. Presentation only: no data loading, no permission logic.

### Pages

The six detail pages use them: Commercial Offer, Account, Lead, Opportunity, Work Order and Work
Order Amendment. Each has a header with a Back link, record type, title, status badges and actions;
related sections are grouped in labelled, coloured, boxed groups; long pages have a sticky Jump-to
row. Whole sections were moved only to put related items together; no handler, fetch, permission
check or display condition changed. The Commercial Offer Submission tab now reads in working order:
"Where this offer stands", "Prepare", "Quotation and submission", "Customer response".

Developer wording was removed from the pages' own text across 20+ pages: "Slice N", "foundation",
"future agents", role codes and raw event names. Several claims that had become false were corrected
rather than merely reworded - for example that Work Order Amendment intake, quotation generation or
offer lines were "deferred".

**Text supplied by the backend was not changed.** About twenty backend strings still say "Slice N":
the reasons stored with business events (shown on the Events page, and in the Work Order's handoff
history for Admin and Management roles), and a few validation messages the normal screens do not
trigger. That wording belongs to the owner's language pass at the end, not to this reskin.

The conversation log (`InteractionLog`) now uses the shared card, shows one "India time" note
instead of an IST label on every row, and clears a stale confirmation or error when the user edits a
field. Only the user's own edits clear it; the post-save form reset does not, so the confirmation
survives - the Slice 9B lesson.

### Names instead of user IDs

Display-name fields were added beside existing user IDs, resolved from `app_user.display_name`
through a LEFT JOIN in the same query (the Slice 9E `QUOTE_DOCUMENT_ACTOR_JOINS` precedent), `null`
when the ID is null or matches no user:

```text
Account                  account_owner_display_name, created_by_display_name
Account classification   account_owner_display_name
Lead                     assigned_to_display_name, created_by_display_name
Opportunity              owner_display_name, created_by_display_name
Commercial Offer         created_by_display_name
Work Order (read routes) created_by_display_name     - on WorkOrderReadResponse only
Work Order Amendment     created_by_display_name
```

**The frozen handoff output is deliberately unchanged.** `POST /api/work-orders/from-commercial-offer`
returns `WorkOrderResponse`, which belongs to the frozen Slice 6D.1 contract. The display name lives
on `WorkOrderReadResponse`, a subclass used only by the list and detail routes; Pydantic serializes
a field by its declared type, so the handoff response carries exactly its previous fields. A test
asserts both halves.

Linked Account and Opportunity are shown by name on the Commercial Offer, Work Order and Amendment
pages, fetched through their existing read routes, with the reference number kept small beside it.

### Playwright

Five assertions changed because headings or link text changed, each kept at the same strength:
three "(Slice 6O.x)" heading texts became exact heading-role checks, and the Amendment page's
Opportunity and Account links are now located by destination rather than by their former UUID text.

## Part C - Records

- `docs/agent/DEFERRED_REQUIREMENTS.md`: status block superseding "Blocking generation of an
  unpriced or partly priced quotation"; the original entry preserved beneath it (ADR-013).
- `docs/agent/slices/slice-9e-quotation-generation.md`: dated supersession note under decision 7.
- `docs/agent/contracts/commercial-offer-contract.md`: approval preconditions and
  `approval_blocked_reason`; a dangling "Deferred pricing precondition" reference repaired; display
  names.
- Account, Lead, Opportunity, Work Order and Work Order Amendment contracts: display names.
- `docs/agent/UI_UX_CARRY_FORWARD.md`: what the reskin did and did not do.
- `docs/uat/PBL_CRM_UAT_RUNBOOK.md` and `PBL_CRM_UAT_DATA_SHEET.md`: the Approve-button known issue
  removed; Step 9 now checks the pricing gate and the stale-version refusal.
- `docs/continuity/NEXT_STEPS.md`: decisions and status.

## Not in scope

Shortening pages (the restructure, after the pilot). Splitting `CommercialOfferDetailPage.tsx`.
Frontend component tests. InteractionLog pagination and filters (post-pilot, `NEXT_STEPS.md`
batch (b)). Inline validation and field highlighting. Resolving `qualification_decided_by`,
amendment `decided_by` and subordinate-record `created_by` to names. The owner's final language
pass.

## Recorded for the owner

- The Accounts and Leads list/detail queries were rewritten with table aliases so the new
  `app_user` join could not make `id`, `created_at` or `updated_at` ambiguous. Existing tests pass
  unchanged; it is still the largest backend change in the package.
- The Account profile summary shows the PAN and GSTIN stored on the Account record itself, which
  can differ from the Tax identity section. Pre-existing; worth a look in the language pass.
- The Account page formats times in the browser's local time zone rather than India time.
  Pre-existing; not changed here.
- On the Lead and Opportunity pages, linked records (the converted Account and Opportunity, the
  Opportunity's Account, the source Lead) read "Open Account", "Open Opportunity" or "Open Lead"
  with the reference beside them, because those responses carry no names. The Lead's "Decided by"
  still shows a user ID for the same reason.
- The Opportunity edit form's errors still appear in the page header rather than beside Save.
  Pre-existing; moving them would have meant changing rendering conditions, which this reskin did
  not do.
- The Lead page no longer repeats a read-only listing of the Lead's details for roles that cannot
  edit; every field in it is already shown in the Summary, Contact and Requirement cards.
