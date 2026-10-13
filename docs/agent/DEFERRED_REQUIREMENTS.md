# Deferred Requirements - Agent Backlog

This file lists important requirements that are intentionally not fully implemented in the foundation prototype. They remain real requirements. Future agents must implement them through scoped slices.

## Account legal identity validation

Recorded 11 August 2026 as `ADR-015`. Not implemented. See
`docs/continuity/ACCOUNT_IDENTITY_VALIDATION_CORRECTION_2026-08-11.md` and the "Production
direction: integration-driven legal identity validation" section of
`docs/agent/contracts/account-business-party-contract.md`.

The prototype captures PAN/GST manually with human-set verification states (Slice 1I). The
target design validates PAN and GSTIN through PBL's existing SurePass integration instead, with
human review only on exception.

Deferred work:

- SurePass provider adapter behind a replaceable, loosely coupled interface.
- Use of the validated response to obtain/confirm legal name, PAN details, GST registration
  details/status and registered/legal address where the service supports it.
- Explicit verification state on the Account, reconciled with the existing Slice 1I states.
- Verification evidence/metadata persistence under data minimisation: status, timestamp,
  provider, external reference/request ID, validated identifiers, returned details, mismatch or
  exception reason.
- Exception routing (mismatch, failure, ambiguous/incomplete response, policy exception, or
  prolonged provider unavailability requiring the manual route) to Accounts by default, with
  configurable assignment to authorized Sales personnel.
- Business events for validation success, failure and exception.
- Non-blocking outage/retry behaviour and an authorized, audited manual fallback for prolonged or
  permanent provider unavailability.
- SurePass-authoritative field precedence with preserved source/mismatch evidence and corrected
  Work Order handling.
- Parameterized evidence-retention and re-verification policy; parameter values remain deferred.

Do **not** implement a routine manual Accounts/Finance approval step to reconfirm a fact SurePass
has already validated, and do not describe SurePass as granting business approval.

### The route: relay through Plum first, our own connector later (owner decision, 13 September 2026)

**Parked, with the route chosen.** Rather than integrating SurePass directly, the first
implementation sends the PAN or GSTIN to **Plum**, which already integrates with SurePass, and
consumes Plum's relayed response. A direct SurePass connector comes later.

This needs no architecture change. ADR-022 already defines identity validation as a
provider-independent capability owning *provider adapters*, so a Plum relay is simply one adapter
and a later direct connector is another. Accounts neither knows nor cares which answered, and
switching routes is a change at one seam rather than in any business module.

What the decision rests on, as confirmed by the project owner:

- **Plum will build whatever API is asked for**, so the usual question - does the interface exist
  or only a screen? - does not apply here. The dependency shifts from capability to vendor
  delivery time.
- **What is relayed is SurePass's own output**, not Plum's customer master record. That keeps
  ADR-015's rule intact: SurePass-returned legal identity values stay authoritative over
  user-entered or customer-document values, because they still originate from SurePass. A response
  carrying Plum's own master instead would be a different thing entirely, with ownership
  implications touching `D-01` and Customer Master activation.
- **The response can carry SurePass's own reference id and timestamp alongside Plum's**, which is
  what ADR-015's evidence requirement needs.

What is deliberately left to implementation time, and must not be lost:

**The two timestamps do not mean the same thing.** Plum's response is likely to be a cached result,
so SurePass's timestamp records when the identity was actually verified, while Plum's records when
Plum handed the record over. If Plum re-serves a two-year-old cache entry, Plum's timestamp is
today and the verification is two years old - so judging currency on Plum's timestamp can make a
stale verification look fresh. ADR-015's required "verification timestamp" means the first one.
Record both; decide which governs currency when the slice is built.

This is bound to `OPEN_QUESTIONS.md` **Q-04**, the deferred re-verification interval: an interval
cannot be set without settling which timestamp it is measured from. Decide the two together.

One trade-off to recognise rather than discover: ADR-030's direction moves capability progressively
**out** of Plum, and this routes a new capability **through** it. Contained at the adapter, so the
cost of reversing it is small - but it is a deliberate choice, not a free win.

Policy decisions and deliberately deferred parameter values: `docs/continuity/OPEN_QUESTIONS.md`,
Q-01 to Q-04.

## Credit and exposure

### Initial prospect/account credit assessment

This happens earlier at Account/PAN level. It assigns approved credit amount and approved payment days. It should not be implemented as a late Commercial Offer-only step.

Ownership (`ADR-015`, amended 13 August 2026): the assessment requires a current, active
`CREDIT_ASSESSOR` authority assignment for the relevant scope, resolved through `ORA-001`.
`SALES_MANAGER` is the initial/default mapping, not a permanent hard-coded role check. The CRM
Account Master's legal-entity/PAN-level credit profile is authoritative for approved Credit Amount
and Credit Days, resolving matrix decision D-01. Sales may prepare a proposal, which is not the
assessment. The applicable Department Head or Managing Director makes the authenticated decision
under `CREDIT_APPROVER`; the Account Credit Profile service activates approved values from that
decision. Named assessors, approvers, delegated thresholds and any future maker/checker rule are
configurable by authorized personnel rather than hard-coded, and `ADMIN` is not an implicit
assessor. Consumption and monitoring of actual exposure remains a separate Finance/Accounts
concern.

Deferred work:

- PAN-level prospect credit profile.
- `CREDIT_ASSESSOR`-authorized assessment capture, storing the authenticated assessor identity and
  the authority assignment/version relied on.
- Credit amount and payment-days approval with authenticated approver identity, authority,
  timestamp, reference and conditions; never store passwords or reusable credentials.
- Review date and periodic review reminders.
- Market feedback, financial strength and payment behaviour notes.
- Configurable delegated-authority and maker/checker policy if PBL enables it later.

### Commercial Offer credit/exposure gate

This happens later, especially before customer-facing quote submission, customer-format offer submission or tender bid commitment.

Deferred work:

- Calculate Potential Exposure from submitted offers and tender bids.
- Compare proposed submission against already-approved credit amount and payment days.
- Block or route over-limit/exhausted-credit cases for approval.
- Preserve approval reference and conditions for Work Order release.

## Terms and conditions

Deferred work:

- T&C master / clause library.
- Offer-level T&C selection.
- Offer-line-level T&C selection.
- Copy selected clause text into the specific offer/line.
- Clause customization per offer and per line.
- New clause proposal into master.
- Approval for new clauses or material deviations.
- Full audit trail of selected, modified, approved, rejected and removed clauses.

Do not implement T&C as unstructured notes hidden inside Commercial Offer remarks.

## Commercial Offer approvals and submission

Deferred work:

- Commercial approval workflow.
- Credit/exposure approval workflow.
- Margin/authority/terms approval rules.
- Submission proof requirements.
- Submitted document locking. **Resolved by Slice 9F, 10 October 2026.** The intermediate CS-05c rule allowed
  submitted content to change in place while a revision was OPEN. The owner's later 9F decision supersedes that
  mechanism: every submitted version is immutable commercial history, including its header, lines, prices, T&C,
  credit reviews and submission evidence. A change is made on a copied Draft/Ready version with new child identities;
  abandoning it leaves the submitted predecessor untouched. Only withdrawal/closure and outcome notes remain legal on
  the submitted row. See `commercial-offer-contract.md`, "Slice 9F".
- Potential Exposure event integration.
- Tender/customer-format BOQ upload and structured capture.

### Markup over the basis rate is not modelled at all (recorded 9 September 2026)

Raised by the project owner while reviewing the UAT practice data, and confirmed by inspection:
**there is no markup or margin concept anywhere in the application.** The only matches for
`margin` in `backend/app/modules/` are CSS declarations in the quotation stylesheet.

What exists today: Slice 4D records the market rates Operations collected and which one was
selected as the basis, with a mandatory `selection_reason`. Slice 4E records the rate we quote on
each offer line. Nothing connects the two.

What is therefore absent:

- no field records the markup applied over the basis rate, as a percentage or an amount;
- nothing calculates or displays it, so a reviewer cannot see that a line was quoted at, say, 18%
  over the rate it was based on;
- there is no markup rule (minimum, standard, by equipment type, by customer segment or by
  duration), so nothing can be complied with or breached;
- consequently there is no deviation workflow, no approval for quoting below a floor, and no
  record of who permitted one.

This is broader than the "Margin/authority/terms approval rules" line already in the section
below, which concerns approval. The gap here starts earlier: the markup cannot be **recorded**,
so there is nothing for an approval rule to act on. Any future package must add the concept
before it can add a control over it.

Deferred rather than built now because the rules themselves are a genuine PBL business decision -
what the standard markup is, whether it varies by equipment or customer, who may go below it and
by how much - and none of that has been stated. Margin-threshold **approval** additionally depends
on `APR-001`, as Slice 9E already records.

**The CRM pilot cannot test markup handling.** That is stated plainly in the testers' guide,
`docs/uat/PBL_CRM_TESTER_GUIDE.md` ("Not in the system yet"), so testers do not look for it and do
not report its absence as a defect. *(Reconciled 9 October 2026: the pilot's data sheet that said so,
`docs/uat-source/PBL_CRM_UAT_DATA_SHEET.md`, was replaced by the restart's tester sheets.)*

### Blocking generation of an unpriced or partly priced quotation (deferred, 9 September 2026)

**STATUS: SUPERSEDED by owner decision on 9 September 2026, and replaced by a different control
implemented in the UI cleanup package on 11 September 2026. Do not implement what this entry
describes.** Both its trigger and its implementation are wrong as current guidance: it says to
block *generation*, after the pilot findings are actioned.

What replaced it: incomplete pricing is gated at **approval for issue**, not at generation, and
before the pilot rather than after it. `approve_commercial_offer_quote_document` refuses while any
active line has no amount, and - owner decision of 11 September 2026 - also refuses a version the
offer has changed since. The two together guarantee that the approved document itself is fully
priced; a check of current lines alone would let a version frozen as "Not fully priced" be
approved once the missing rate was filled in. Generation stays open so Sales can still produce
rough drafts, which is part of what the pilot exists to observe.

Why: the commercial risk lands at issue, not at generation - independent review's own wording was
"a document called a quotation can be downloaded and later approved for issue". Gating approval
closes that risk without obstructing exploratory data entry, which blocking generation would
have done. The authoritative description is the "Slice 9E" section of
`docs/agent/contracts/commercial-offer-contract.md`, under the approval preconditions.

The original entry is preserved unchanged below, per ADR-013, as the record of what was planned
on 9 September 2026.

Slice 9E generates a quotation document even when some or all active lines carry no rate. The
document does not lie about it - the total reads "Not priced" when nothing is priced and "Not
fully priced" when only some lines are, never a numeric total that is really a partial sum - but
generation itself is not refused.

Independent review recommended blocking it outright. The owner decided to allow it during the
CRM pilot and block it afterwards, because the pilot exists partly to watch PBL users enter data
themselves and refusing to generate until every rate is filled would obstruct exactly that.

**Trigger: before the CRM pilot's findings are actioned, and in any case before any real
customer data enters the system.**

The work when it is taken: a precondition in `generate_commercial_offer_quote_document` returning
`422`, exactly as the existing "no active lines" check does, plus a test. The renderer's
"Not fully priced" handling stays as defence in depth so a future code path cannot reintroduce a
false total. No migration and no data-shape change, so nothing about this gets harder by waiting;
the only consequence is that partly-priced versions generated during the pilot stay frozen as
they are, which is harmless because the pilot is synthetic-only.

**Customer-facing quote document generation is implemented by Slice 9E** (8 September 2026):
a frozen, versioned HTML quotation with a one-step Draft -> Approved for Issue gate. What
remains deferred from this list: server-side PDF rendering (the stored/frozen artifact is
HTML; a customer's PDF is produced by the browser's own Print dialog, outside the system);
margin-threshold evaluation and approval (needs `APR-001`); and full maker-checker (a Sales
Manager may currently both prepare and approve their own quote). See
`docs/agent/slices/slice-9e-quotation-generation.md`.

## Commercial Offer versions and legacy revisions

Slice 9F implements immutable Commercial Offer rows and retires new Slice 6K in-place revision cycles. Existing legacy
revision records remain listable/closable for compatibility. Resolved in 9F:

- Formal revision/version control through `offer_code` plus immutable `version_number` rows.
- Prior submitted version lock/tamper evidence: a sent row and its children are no longer editable; replacement and
  abandonment preserve the earlier row exactly.
- Commercial Offer cloning and immutable version snapshots for the header, active lines, pricing evidence/selected
  basis, active T&C and current credit review.
- `9F-R5-A1` - The first hosted Playwright run exposed the exact contract/UI mismatch described by this Round 5
  advisory: the backend permits outcome-date/remarks-only corrections on the current `ACCEPTED`, `REJECTED`,
  `WITHDRAWN` or `CLOSED` row, but the Slice 9F UI had disabled the whole form. The 11 October correction preserves
  that established backend path, keeps status and commercial content locked, enables only those two outcome fields,
  and adds targeted terminal-status and withdrawn-version browser coverage. `REVISED` and `ABANDONED` remain fully
  immutable.
- `9F-R8-A1` - Reconciled on the same 11 October correction touch: lifecycle guidance now names **Offer versions**,
  `NEXT_STEPS.md` calls the corrected checklist item the acceptance happy-path step, and the retained Slice 9F design
  names the shipped additive response fields.

Still deferred:

- Revised-value and line comparison.
- Structured corrigendum/amendment content beyond the Slice 6K reason metadata.
- Carry-forward of submission evidence and quote documents is not automatic by owner decision; each version is sent
  afresh. Any future assisted carry-forward needs its own business decision and audit design.
- Downstream Work Order and report screens that show only `offer_code` do not yet add the version label (`vN`). Their
  stored public-ID and source-line traceability remains correct, and the frozen handoff payload is unchanged. Add the
  label when those screens are enhanced without changing the handoff contract. *12 October 2026:* the Work Order half
  is done - the Work Order output carries `commercial_offer_version_number` by the frozen handoff contract's second
  amendment, and the Work Order pages and the Create Work Order page show "CO-000123 v2". Still open: the dashboard's
  reports, and the amendment pages' related-offer codes.
- Server-side PDF generation and legal/version approval controls beyond Slice 9E's simple
  Draft -> Approved for Issue gate (see the "Commercial Offer approvals and submission" section
  above).
- `9F-R5-A2` - Reconcile stale non-functional comments/docstrings left after 9F: the 6M.1 same-status update comment,
  the quotation approval/generation status comments and the lifecycle-guidance docstring still describe the older
  status or Slice 6K-revision model. This is maintenance wording only; the tested runtime sets are correct.
- `9F-R5-A3` - Make the generic content-lock guidance accurately version- and status-aware. For `REVISED` and
  `ABANDONED`, `offerStatus.ts::contentLockedNote` gives post-award wording ending **otherwise raise a new offer**,
  although these rows are inactive history and the useful direction is to open the latest live version. In
  `services/common.py::_lock_offer_for_content_change`, every non-Draft/Ready status is told **Use Make a new
  version**, including `ACCEPTED`, `WITHDRAWN`, `CLOSED` and `REJECTED`, where version creation is refused. Keep
  **Make a new version** for `SUBMITTED`; direct `REVISED`/`ABANDONED` users to the latest live version; keep
  appropriate post-award/concluded guidance for `ACCEPTED`/`WITHDRAWN`/`CLOSED`/`REJECTED`. The dedicated
  version-history guidance is already correct; this is a message-consistency hardening item.
- `9F-R5-A4` - Simplify `CommercialOfferDetailPage.tsx::handleAbandonVersion`: on a failed abandon request, the
  placeholder **See the validation message below.** is set and then immediately replaced by the detail from
  `versionErrorMessage`. Remove the placeholder `setVersionActionErrors` call when that handler is next touched. It
  has no visible wrong outcome.
- `9F-CI-R1-A1` - Future-proof terminal edit eligibility against a later constant-alignment change. The current
  frontend terminal-status constant intentionally contains only `ACCEPTED`, `REJECTED`, `WITHDRAWN` and `CLOSED`, so
  `REVISED`/`ABANDONED` cannot open the edit form. If that constant is ever aligned with the broader backend
  cannot-leave tuple, explicitly exclude both history statuses and add a browser assertion that the replaced row's
  **Edit Commercial Offer / Status** button remains disabled, or move the rule into a tested `offerStatus.ts` helper.
  Without that safeguard, the Edit button, outcome fields and Save would misleadingly enable, the inline
  **REVISED/ABANDONED history never reaches this form** comment would become false, and every save would end in the
  backend's authoritative read-only-history `422`; no data could change.
- `9F-CI-R1-A2` - When the Commercial Offer edit/status rules are next hardened, extract the inline form-eligibility
  decision into a pure frontend helper and add a Vitest table covering full edit (`DRAFT`, `READY_FOR_REVIEW`),
  status/outcome edit (`SUBMITTED`), outcome-only edit (`ACCEPTED`, `REJECTED`, `WITHDRAWN`, `CLOSED`) and no form
  (`REVISED`, `ABANDONED`). This pairs naturally with `9F-R5-A3`/`9F-R5-A4`. Current behavior has targeted Chromium
  coverage and no wrong outcome.
- `9F-CI-R3-A1` - Strengthen the Slice 9B status-writer lock-order tripwire for version submission. Its generic AST
  check currently recognizes `lock_commercial_offer_row`; the v2 submit path instead uses
  `lock_commercial_offer_version_submission_rows` to lock predecessor and successor in ID order, while the v1 branch
  contains the single-row lock text that lets the generic source-order check pass. Runtime locking is correct: the
  pre-lock version-context read uses immutable lineage and status is re-read after both rows are locked. When this
  tripwire is next touched, recognize the two-row lock explicitly and add a focused assertion or concurrency test that
  the predecessor-retiring write occurs only after both rows are locked.

## Commercial Offer lifecycle reactivation (CLOSED, 7 September 2026)

**STATUS: RESOLVED by Slice 9B.** PBL decided that a Rejected Commercial Offer is final: no
further customer response of any outcome may be recorded against it, and a later award must be
recorded against the replacement offer instead. `REJECTED` was removed from
`COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES`, closing the `REJECTED -> ACCEPTED` path.
`COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` is deliberately unchanged, so preparing a
replacement offer for the same Opportunity remains permitted - that was never the defect. See
`docs/agent/slices/slice-9b-crm-pilot-hardening.md`.

The original gap description is preserved below as the historical record of what was found and
how, per ADR-013.

Recorded 17 August 2026. This gap was independently surfaced twice by an unrelated
independent-review exercise (PBL's internal records, not part of this copy), not by ordinary CRM slice work.
That benchmark used a historical Commercial Offer candidate commit as its review subject; this
entry is written from an independent check of the **current `main`** codebase, not from the
benchmark's own historical candidate, because a benchmark result on an old commit is not by itself
evidence about current behaviour.

**Verified current-main behaviour, checked directly against the files named below:**

1. `COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` in
   `backend/app/modules/commercial_offers/contract.py` (around line 109) includes
   `REJECTED`. A `REJECTED` Base Offer therefore counts as inactive for the Slice 6B.1
   one-active-Base-Offer-per-Opportunity creation guard, so a new Base Offer may be created for the
   same Opportunity while the rejected one still exists.
2. `COMMERCIAL_OFFER_CUSTOMER_RESPONSE_ALLOWED_STATUSES` in the same file (around line 266) also
   includes `REJECTED`. The Slice 6L Customer Response action
   (`create_commercial_offer_customer_response` in
   `backend/app/modules/commercial_offers/service.py`, around line 1658) therefore accepts a new
   customer response against an offer that is currently `REJECTED`.
3. In that same function (around lines 1711-1719), `target_status` is set to `ACCEPTED` whenever the
   response outcome is `ACCEPTED_AWARDED`, unconditionally relative to the offer's current status.
   There is no guard preventing this when the current status is `REJECTED`.

**The complete reachable scenario this establishes:** a Commercial Offer (Offer A) reaches
`REJECTED` through a customer response. Because `REJECTED` is treated as inactive for the
one-active-offer guard, a replacement Base Offer (Offer B) is created for the same Opportunity and
proceeds through its own lifecycle. A later, delayed customer response is then recorded against
Offer A with outcome `ACCEPTED_AWARDED`; nothing in the current code rejects this, and it moves
Offer A back to `ACCEPTED`. Offer A and Offer B can then both be simultaneously actionable
(`ACCEPTED` and, depending on Offer B's own progress, active/actionable) for the same Opportunity,
which the Slice 6B.1 one-active-offer rule was intended to prevent.

**This is recorded as a known gap, not fixed here.** No Commercial Offer runtime code, contract, API
shape, migration or business rule is changed by this documentation entry. A future corrective
package should decide, as a genuine business/product question rather than a default engineering
choice: whether a `REJECTED` offer should remain eligible to receive a later customer response at
all; whether `REJECTED` should instead be excluded (or only conditionally included, e.g. only while
no replacement offer yet exists) from
`COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES`; and whether reaching `ACCEPTED` from `REJECTED`
through the Customer Response action should require an explicit additional confirmation given the
possibility of a second, already-created replacement offer. This is exactly the class of question
the workflow/lifecycle overlay in `BOUNDED_INDEPENDENT_REVIEW_METHOD.md` section H.2 is designed to
surface for a future implementation package to resolve, not to answer automatically.

## Database-level uniqueness for the one-active-Base-Offer rule

**STATUS: RESOLVED by CS-05c (10 October 2026).** The owner decided on 9 October 2026 that the database enforces the
rule, "for consistency". Migration `20260908_0053` adds exactly the index described below,
`ux_crm_commercial_offer_one_active_base_per_opportunity`; the upgrade stops, naming the offers, on any Opportunity
that already has two active Base Offers; creation answers the index with its own refusal. See the offer contract's
CS-05c section. The original entry is kept below as the record.

Recorded 7 September 2026 (Slice 9B). The Slice 6B.1 rule - at most one active/actionable Base
Offer per Opportunity - is currently enforced by application logic plus a row lock on the parent
`crm_opportunity`, taken before the eligibility read in
`commercial_offers.service._normalize_create_payload`. That serializes concurrent creations and
also blocks a concurrent Opportunity status change, so the rule holds under concurrency today.

**It is not enforced at the database level.** A partial unique index over
`crm_commercial_offer (opportunity_id) WHERE offer_purpose = 'BASE' AND offer_status_code NOT IN
('WITHDRAWN','REJECTED','CLOSED')` would make the invariant structural rather than procedural,
and would survive a future code path that forgets the lock.

Deferred because it needs an Alembic migration, and Slice 9B deliberately did not take the
migration head - the Hiring lane (`7C`) owns it. Natural home: alongside the `7C` migration, or
its own small package.

*Updated 7 October 2026 (TB-1):* the `7C` migration came and went without it. Its home is now TB-1's
corrective package CS-05 (concurrency safeguards), whose objective names this partial unique index.

*Reconciliation, 8 October 2026 (TB-1 CS-11):* since the service split, `_normalize_create_payload` is in
`backend/app/modules/commercial_offers/services/offers.py`.

## Frontend component-test capability (blocks two Slice 9B acceptance items)

Recorded 8 September 2026 (Slice 9B, twelfth correction pass). The frontend has **no component-test
capability**. `frontend/package.json` carries Vitest, but neither `@testing-library/react` nor
`jsdom`, and the only frontend test file (`frontend/src/routes.test.ts`) exercises React Router's
matcher against the route table - it renders nothing.

Two Slice 9B acceptance items are blocked on this and on nothing else:

- **The success-confirmation check.** Recording a `REJECTED_LOST` customer response replaces the
  form with the finality panel; the green confirmation must survive that. The fix is verified
  structurally (the message is a sibling of the conditional, and is now set before any refresh
  runs), but never behaviourally.
- **The reviewer-requested regression test**: a successful `REJECTED_LOST` whose secondary refresh
  fails, asserting that the finality panel *and* the confirmation both still appear.

The browser-driver route was attempted twice and failed twice for the same cause: the driver
populates the date-time input's DOM value without dispatching React's synthetic change event, so
the field is still reported as required on submit. This is a limitation of the driver, not evidence
about the application.

Deferred because it is a frontend-tooling package - two dev dependencies plus a jsdom test
environment and a first component test - not a correction to a CRM slice. Natural home: alongside
the `CommercialOfferDetailPage.tsx` decomposition recorded in `docs/agent/UI_UX_CARRY_FORWARD.md`,
or its own small
package before the CRM pilot starts. Until it exists, no frontend behaviour in this application is
covered by an automated test.

*Reconciled 8 October 2026 (TB-1 REP-1, TB1-903):* "the only frontend test file" is no longer true -
`npm test` runs 28 Vitest files (33 on 12 October 2026), testing the pages' state modules and the shared components' helpers
as well as the route table. None renders a component, so the gap above stands, and with it the two
blocked Slice 9B items. TB-1 schedules the capability with corrective package CS-10 (TB1-700).

## Interactions (Slice 9D) - recorded parkable items

Recorded 8 September 2026, from the Slice 9D independent review; classifications corrected in
correction pass 2. Each was accepted as parkable rather than fixed in 9D, and recorded here so a
later package does not have to rediscover them.

**These are not all merely "future work".** An earlier version of this preamble claimed none was
a defect in delivered behaviour, which was inaccurate: the list mixes accepted defects, delivered
limitations, hardening work, an undecided policy and a compatibility nonconformance. Each item
below is labelled with what it actually is, because "parked" and "harmless" are different claims
and only the first one is true of all of them.

Nine items are recorded here. Two further distinct UI items - stale form feedback, and per-row
timezone labels - are in `docs/agent/UI_UX_CARRY_FORWARD.md` under "Interaction log (Slice 9D)",
which also repeats the two items below that are primarily UI-facing. Eleven distinct items in
total across the two documents.

**Reads and pagination**

- **[Delivered limitation]** Replace the 500-row inherited-history ceiling with database pagination. When
  `include_inherited=true`, `interactions.service.list_interactions_for_record` fetches up to
  `_INHERITED_MERGE_FETCH_CAP` rows per side and paginates the merged list in Python, because
  direct and inherited rows come from two different `linked_record_type` values. Correct for a
  pilot's volume; it is not correct at scale, and the cap silently truncates rather than
  erroring. A UNION-based query paginated in the database is the real fix.
- **[Incomplete delivery]** Frontend pagination and the filters the API already supports. The component shows the
  newest 20 records with no paging, and exposes only the inherited-history toggle. The API
  already accepts `channel_code`, `direction_code`, `occurred_from`, `occurred_to`, `limit` and
  `offset`; the UI does not yet surface them.

**Audit and semantics**

- **[Accepted defect]** Deletion reason, update old/new values, and no-op updates. `InteractionUpdated` records
  that a change happened but not what it was; `InteractionDeleted` carries no reason. A `PUT`
  that changes nothing currently emits an event that looks like an edit.
- **[Undecided policy]** Future/naive timestamp and follow-up ordering policy. `occurred_at` accepts a future
  datetime and a naive one; no policy defines whether either is meaningful, and there is no rule
  ordering `next_follow_up_at` relative to `occurred_at`. Decide before production hardening.
- **[Accepted defect]** An empty interaction is labelled "content redacted". When a caller lacks
  `INTERACTION_CONTENT_READ`, `body_redacted` is `true` even for a record that never had a body,
  implying hidden content where none exists. Distinguish "withheld" from "never present" -
  `body_stored` already carries the fact needed to do it.

**Guard hardening**

- **[Hardening]** The event-payload static guard can be bypassed through an alias. It matches
  `record_business_event(...)` by bare name or attribute; a module-level alias
  (`_emit = record_business_event`) would not be seen. Runtime payloads are safe today and a
  separate runtime test proves it, so this is a hardening item, not a hole - but the guard should
  resolve aliases, per the Slice 9B lesson that a detector's search shape decides its findings.

**Testing**

- **[Test-coverage gap]** Component tests for `InteractionLog`. Blocked on the same missing frontend component-test
  capability already recorded above ("Frontend component-test capability"); the current frontend
  tests cover the route table, not this component.

**Policy, before production activation**

- **[Policy decision, required before production]** Interaction retention and read-access auditing. Retention is an unset parameter under the
  ADR-015 precedent, and no audit records who read a message body. Both must be resolved before
  interactions carrying real customer correspondence go into production use. See
  `docs/agent/contracts/interaction-contract.md`, "Data classification". **Extended by Slice 9C
  (8 September 2026):** the same open question covers documents. Slice 9C added
  `document_metadata.retention_due_at` as shape only - never set, nothing purges against it,
  same ADR-015 precedent as above - and no audit records who downloaded a document's bytes
  through `GET /api/documents/{public_id}/content`. This is one policy question, not two: a
  document attached to an interaction and the interaction's own message body carry the same
  retention/audit gap, and should be resolved together rather than separately per module. See
  `docs/agent/slices/slice-9c-document-storage-foundation.md`. **Extended by Slice 9E
  (8 September 2026):** a generated quotation document (`document_type = 'QUOTATION'`) is a
  `document_metadata` row like any other, so it carries the identical unset
  `retention_due_at` and the identical absence of download-audit evidence. This remains one
  policy question, not three - do not split it further. Not triggered by the current CRM pilot:
  the pilot uses synthetic data only (owner decision 5, 8 September 2026), so this item becomes
  a blocking prerequisite only if the pilot's data basis changes to real customer data. See
  `docs/agent/slices/slice-9e-quotation-generation.md`.
- **[Compatibility nonconformance, owned and time-bounded]** The MCF-001 structured-error-envelope exception. `INT-001` returns `{"detail": ...}` like
  every other module; the exception is owned by and retires with the PF-1B error-envelope
  retrofit. Recorded in the contract, repeated here so the retrofit package finds it.

## Roles and what each person sees (accepted for the hosted pilot, 11 September 2026)

Recorded by TE-5 while setting up the pilot's accounts. PBL's real jobs, as the owner described
them: Sales Executives work from Lead through Commercial Offer and negotiation; the Operations
Executive collects market rates for vehicles and equipment; the Manager sees the whole pipeline and
each Sales Executive's performance; Finance sees billing-relevant data only. Three gaps against the
application as it stands, confirmed against the permission table
(`backend/app/modules/authorization/contract.py`):

- **Everyone reads every record.** `SALES_USER` can list and open every Lead, Account, Opportunity,
  Commercial Offer and Work Order, not only their own. There is no record-level data scope at all.
- **No per-person view.** The reports (Slice 9A) group only by status, never by owner or creator,
  so a manager cannot see one Sales Executive's pipeline or results.
- **Finance sees more than billing.** `FINANCE_USER` reads every CRM record and can capture and
  verify PAN/GST details and upload documents. Nothing billing-related exists yet to limit it to.

Owner decision, 11 September 2026: **accepted as known limitations for the pilot**, which runs on
invented data, so cross-visibility harms nothing there. Testers are told in the tester guide, and
what they say is the input for designing these properly.

Before real customer data, decide: what "own records" means for each record type (the owner field
exists on Account, Lead and Opportunity, but a Commercial Offer or Work Order records only who
created it); which measures make up a performance view; and Finance's real scope. Narrowing any
role tightens routes PF-1A-E1 recorded, so it goes through `POST_BASELINE_TIGHTENED_ROUTES` rather
than editing the frozen baseline.

## What the committed-credential check does not cover

Recorded 13 September 2026, after a near miss: a draft of the `--password-stdin` tests used two of
the pilot's **real** passwords as fixtures. `scripts/check_tracked_secrets.py` did not flag them.
They were caught by eye and replaced before the commit, so nothing real ever reached the
repository - but the gap is worth stating, because a green check is easily read as "no credential
here" when it means something narrower.

**What it does detect:** a credential-*named* variable assigned a concrete-looking literal
(SEC-004: `password = "..."`, `"apiKey": "..."`, `db_password = ...`), a connection URL with an
inline credential (SEC-005), known issued-token formats (SEC-003), PEM private-key blocks
(SEC-002), and credential-bearing file paths (SEC-001).

**What it cannot detect:** a real password used as a bare argument or an unnamed literal -
`_login(username, "S@l3suser123_1")`, `io.StringIO("0wn3r!@#$")`. There is no name next to the
value to key on, and the value itself is just a string. Flagging every credential-shaped literal
across ~930 files would produce false positives at a rate that gets the check ignored, which is
worse than the gap.

**So this is a limit of the approach, not a bug to fix**, and it is deliberately not on a to-do
list as though a patch were pending. What would genuinely help, if this ever recurs:

- a narrow rule for *test* files only, where the false-positive cost is lower and the habit of
  pasting a real value is most likely - for example flagging a literal that also appears in a
  known credentials-file format elsewhere in the tree;
- or a pre-commit reminder rather than a gate.

Neither is scheduled. **The control that actually works is the human one: never paste a real
credential into a test, use an obviously fictional value.** That is why the pilot's tests use
`Ex@mpl3pass123_1` and `Sampl3!@#$`, which resemble the real ones in shape and are not them.
(7 October 2026: the second became `Sampl3!@#$-chosen` when TB-1 TB1-204 part a's 12-character
minimum came in; the sign-in hardening tests use `Fictional#Tester-2026`.)

## Sign-in: what TB-1 TB1-204 part a left (7 October 2026)

TB1-204 part a stopped repeated wrong passwords, made a password reset, disabling and retiring end
every earlier sign-in, set password rules and raised the hashing cost
(`docs/continuity/TB1_204A_SIGN_IN_HARDENING.md`). Left, by the owner's decisions of that day:

- **Where the browser keeps the sign-in.** It stays in `localStorage` (`pbl_auth_token`), where a
  script injected into a page could read it. Moving it to a secure, HttpOnly cookie - with the
  protection against cross-site requests a cookie needs - is scheduled with CS-10's shared session and
  fetch helper, which first gathers the 29 files that read the token into one, so the move then
  touches that one. **Due before production** (TB-1 corrective register row 12).
- **Sign out on the server, one device at a time.** Sign out clears the browser only; the server
  accepts that sign-in until it expires (at most 8 hours) unless the password is reset or the account
  tool's `end-sign-ins` is run, which end every device's. Ending one device's needs a record per
  sign-in, which belongs with the cookie move above.
- **Keeping someone out on purpose.** Counting is per typed username, so anyone who can reach the
  sign-in page and knows a username can keep that person stopped, 15 minutes at a time; the hosted
  pilots' site login and rate limit stand in front of that. Counting per network address as well
  needs a client address the backend can trust, which nginx does not pass on today.
- **Users setting their own passwords** under the rules, and the NFR's SSO, MFA for privileged users,
  configurable session timeout and device controls.
- **An older stored password** keeps its 260,000-iteration hash until that person next signs in; until
  then a wrong password for that account is answered after the same work as any other, but the
  stored hash is the weaker one.
- **Raising the work factor** (8 October 2026). 600,000 is both the count outside development and CI
  and the most any setting or stored hash may have (`STANDARD_PASSWORD_HASH_ITERATIONS`), so no change
  of setting locks anyone out. Raising it - when OWASP's figure rises - is a change to that number in
  code; older hashes are upgraded at each person's next sign-in. Lowering the number in code would make
  hashes above it unusable.
- **The route guard's unused allowance.** `backend/tests/test_authorization_route_migration_guard.py`
  allows `.role_codes` in `identity/routes.py::login` only as the success event's payload. Since round 7
  that payload is built in the identity service and the route reads no role codes, so the allowance,
  and the guard's comments calling it a real usage, are unused. Retire them with the next change to
  that guard; until then they permit nothing the route does.

## Entering a market rate and choosing the basis rate are one permission

Recorded 13 September 2026, from the project owner's description of how the two roles actually
work, while the pilot sheets were being written.

**The business process.** The Operations Executive goes to the market, obtains rates from vendors
against an enquiry line, and enters them. The **Sales Executive then chooses** which of those rates
the offer is priced on - and it need not be the lowest, which is why `selection_reason` is
mandatory. Finding out what the market costs and deciding what PBL quotes are two different jobs
held by two different people.

**What the system does.** Both actions are guarded by the same permission,
`COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE` (`ADMIN`, `SALES_USER`, `SALES_MANAGER`,
`OPERATIONS_USER`): `POST .../pricing-evidence` and
`POST .../pricing-evidence/{id}/select-basis` in `commercial_offers/routes.py`. So Operations can
choose the basis rate, and Sales can enter rates. Neither is prevented.

Sales being able to enter a rate is reasonable - somebody has to when Operations is unavailable.
Operations being able to make the pricing decision is the part worth a second look, because the
choice of a dearer rate is exactly the kind of commercial judgement an approval trail is usually
built around.

**Not changed now**, for the same reason the document-upload permission split was not: separating
them needs a new permission and a seed migration, and the next migration slot is reserved for the
Hiring lane. It is also the wrong moment to decide - **the pilot is asked the question directly**.
The Operations sheet has the tester choose a basis rate, tells them the system allows it, and asks
whether it should. Their answer should settle it before the permission is split.

The owner's current position (13 September 2026) is that the two Operations jobs - market rates by
an executive, and receiving a confirmed Work Order, probably by a manager - are rolled into one
role for the pilot and may be separated afterwards. If they are, this permission split belongs in
the same package.

**Decided, 13 October 2026 (the owner):** only Sales chooses a line's basis rate; Operations and Sales enter market
rates. The split is part of the vendor package (`docs/vendor/03_REMAINING_AND_DEFERRED_SCOPE.md`, group A). Splitting
attaching a file to an offer from recording pricing evidence stays optional tidy-up (group D).

## Creating a Work Order and deciding its amendments are one permission

Recorded 7 October 2026 (TB-1 TB1-108, TB1-206), beside the pricing-evidence coupling above, which
is the same kind of case.

**What the system does.** One permission, `WORK_ORDER_CREATE` (`ADMIN`, `SALES_USER`,
`SALES_MANAGER`, `OPERATIONS_USER`), guards four capabilities: creating a Work Order from an
accepted offer (`POST /api/work-orders/from-commercial-offer`); recording and editing an amendment
and its lines; **deciding** an amendment (`POST .../amendments/{amendment_public_id}/decision`);
and attaching a document to a Work Order (`DOCUMENT_LINK_WRITE_PERMISSION["work_order"]` in
`documents/contract.py`). Narrowing who may decide amendments, or who may attach Work Order
documents, would therefore also narrow who may create Work Orders, and the other way round.
`work-order-amendment-contract.md` documents the shared role set; until now nothing recorded what
sharing it means.

**Why it is harmless today.** Deciding an amendment changes nothing on the Work Order: applying a
validated amendment is the open decision `D-07` (`docs/continuity/OPEN_QUESTIONS.md`), and the
approvals the System-of-Record matrix describes need `APR-001`, which is not built.

**A departure from directional guidance, now recorded.** The matrix suggests Operations owns the
amendment validation decision, with Sales, Finance and Management approving their parts; Slice 6O.2
gave the decision to the four roles that record amendments, with no second approver. The guidance
is directional, so departing from it is allowed (ADR-013) - but not silently: the 6O.2 slice record
now carries the deviation note. Whether PBL wants deciding separated from recording is a business
question for `D-07` or `APR-001`; nothing here settles it.

**When.** Split the decision, and the right to attach Work Order documents, into their own
permission codes in whichever comes first: the package that builds amendment application (`D-07`), or
the one that activates governed authority configuration so that grants can change without a code
release (PF-1A beyond E3, stopped since 7 September 2026 until `APR-001` or Work Order release needs
it). A split changes the route pins and `test_document_upload_rights.py`.

## Document upload - gaps carried from the upload package

Recorded 13 September 2026, discharging a commitment made in
`docs/continuity/DOCUMENT_UPLOAD_ON_RECORD_PAGES_COMPLETION.md`: that package's own "Known gaps"
list existed only in its slice and acceptance records, with nothing here or in
`UI_UX_CARRY_FORWARD.md` pointing at any of it, and the note said the entries would land in the
records update following the TE-5 VPS dry run. This is that update.

**Permissions**

- Commercial Offer uploads reuse `COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE`, so changing who may
  record pricing evidence silently also changes who may attach files to an offer. A dedicated
  permission needs a seed migration, and the next migration slot is reserved for the Hiring lane -
  which is why it was not done, not because the coupling is right.
- The permission catalogue's descriptions of `DOCUMENT_UPLOAD` and
  `COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE` are unchanged and now understate what those grants
  actually govern. A reader deciding who to give them to would be misled.

**Upload behaviour**

- The linked record's existence is not checked on upload: a well-formed public id for a record that
  does not exist is accepted.
- Uploads carry no idempotency key, so a retry after an unconfirmed upload can store a second copy.
  The form reloads the list so the user can see it happened. A key needs a schema change.
- A caller without rights can still make the server receive one whole request, up to the 26 MiB
  cap, before the `403`.
- The content check confirms how a file is *built*, not that the document inside is complete, valid
  or uncorrupted - a damaged or hand-assembled file built as a Word, Excel or PDF file is accepted
  (owner decision after review round 5). It is not a malware scan and no text is interpreted. The
  tests use files the owner saved from one installation of Word and Excel; they do not cover every
  program that writes those formats.

**Test coverage**

- The shared authorization guard pins the exact permission of every protected route but nine, and
  flags a new ungated route. *Corrected 7 October 2026 (TB-1 TB1-201): this line said "every protected
  route".* The nine: the four Reports routes, pinned instead by `test_reports_api.py`'s own map; and
  the five Interactions routes, which the guard only checks carry some permission, so a swapped
  permission on one would pass every test - adding them to `POST_BASELINE_NEW_ROUTES` is TB-1's
  corrective package CS-19. The guard also bounds the total route count by a `>= 70` floor rather than an exact number,
  and does not detect a *removed* ungated route. This is a pre-existing PF-1A-E1 limitation that
  the upload package inherited rather than introduced; that package's own routes are pinned exactly
  by `test_document_upload_rights.py`.
- A second, different hazard on the same fixture, now that two lanes run at once: the file
  records which permission guards which route, so a **bad merge there does not fail - it records
  the wrong rule.** The other files two lanes share conflict loudly; this one does not. See
  `AGENTS.md`, "Parallel lanes and worktrees".

## Document deletion and in-browser viewing

Recorded 12 September 2026, from the project owner's own walk through the screens before the CRM
pilot. Neither gap had been recorded anywhere; both are real.

**A document cannot be deleted.** `backend/app/modules/documents/routes.py` has no `DELETE` route
at all, so a file uploaded against the wrong customer, or uploaded in error, cannot be withdrawn by
anyone - including an administrator. On a pilot of synthetic data that is untidy; with real
customer documents it would be a genuine problem, because the wrong customer's file would sit on
another customer's record permanently.

The owner has decided the core of the behaviour (Q-12 in `docs/continuity/OPEN_QUESTIONS.md`):
**deleting removes the file from storage**, the audit trail may keep the record of the document and
of its deletion, and no "reason for deletion" capture is to be built now. The work that implies:

- a `DELETE /api/documents/{public_id}` route behind its own permission, not folded into
  `DOCUMENT_UPLOAD`;
- removal of the stored object through the Slice 9C storage abstraction, not a direct file unlink,
  so a future non-local provider behaves the same;
- a `DocumentDeleted` business event carrying who deleted what and when - the audit record the
  owner's decision relies on - and never the content;
- a decision, at build time, on what the `document_metadata` row itself does: a deleted-marker that
  keeps the row readable for audit is the shape most consistent with this repository's existing
  "avoid hard deletes for business records" standard, but the owner's decision speaks only to the
  stored file;
- the three still-open points in Q-12: whether a reason later becomes required, who beyond the
  uploader and an administrator may delete, and whether a document cited by an approved-for-issue
  quotation version is protected from deletion.

**A document cannot be viewed without downloading it.** `GET /api/documents/{public_id}/content`
serves every file as `Content-Disposition: attachment`, so even a PDF is saved to disk rather than
opened. Serving a safe subset inline would fix it, but the allowlist matters more than the
convenience: an uploaded HTML or SVG served inline from the application's own origin is a
stored-XSS hole, so only PDF, common image types and plain text should ever be inline, with
everything else left as an attachment. Worth pairing with the deletion work, since both touch the
same route family.

Neither is triggered by the current pilot, which uses synthetic data only.

## Documents on a Work Order's extensions and amendments (owner, 8 October 2026)

When a customer extends a Work Order or amends it, the papers that come with it - the extension order, the amendment
letter, revised rates - must be attachable to that extension or amendment, not only to the Work Order as a whole.

What exists today: a document can be linked to a Work Order (`work_order` in `documents/contract.py`), but not to a
contract extension (Slice 7D Part 3) or to a Work Order amendment (Slice 6O.2). A user can attach an extension's order
to the Work Order, but nothing says which extension it belongs to.

Suggested when it is built:

- Attach, list and download documents on a contract extension and on an amendment, where each is shown on the Work
  Order page.
- Reading such a document needs what reading its Work Order needs (`WORK_ORDER_READ`); attaching one needs what
  recording the extension (`WORK_ORDER_CONTRACT_EXTENSION_WRITE`) or the amendment (`WORK_ORDER_CREATE`) needs. Each
  attachment is a business event on the extension or amendment, as other document links are.
- Removing the latest extension (allowed since 22 September 2026) keeps its documents visible in the audit trail;
  nothing is deleted with it.

Open for the owner when it is built: whether an extension may be recorded without its order attached (a rule, or only
a reminder); whether the documents of a rejected amendment stay visible.

## Rate discovery and pricing

Current pricing evidence is only a foundation. Deferred work:

- Rate master.
- Advanced benchmarking by equipment, customer, segment, site/region, date range and billing UOM.
- Automated Plum historical-rate extraction.
- Role-controlled visibility for sensitive margin/cost data.
- Link selected benchmark/reference to approval and submission.

## Work Order and Customer Master

Current Work Order is only a handoff shell. Deferred work:

- Customer Master creation/activation request at first Work Order.
- Finance approval before WO release/posting.
- WO release/posting gate.
- Customer WO document metadata and required document checklist.
- Partial award and multiple WO handling from one Commercial Offer - **the duplicate half done by CS-04 part 1 (8
  October 2026)**: several Work Orders per offer, an offer line's quantity onto them once, whole or in parts, never past
  its total (refused, and held by the database); a Supplementary Offer may make its own Work Order, a Change Quotation
  may not; one customer Work Order reference per Work Order of an offer, so a repeated request is refused (the owner,
  after review round 3). Still deferred: the request key that would answer a repeated request with the Work Order it
  made rather than a refusal (CS-04 part 2, with CS-06 - its behaviour agreed by the owner on 12 October 2026 and
  written into the frozen handoff contract's second amendment, to be built with PF-1B; that amendment also put the
  offer's version and the lines handed off into the handoff's output and events); recording the unawarded
  balance of a line (CEX-001's worked example, step 4); cancelling a Work Order, which would let its quantity be handed
  off again and let the offer be recorded lost; and splitting by number of machines when a line is counted in time.
  **Splitting one line across Work Orders by period** (the owner, 8 October 2026: rare, but a customer may order the
  same 4 cranes on one Work Order for one period and on another for the next) is deferred as a future feature: the
  handoff would carry a period per part, the database rule would allow the line's quantity once per period rather than
  once in all (a loosening, so production data already meets it), and a part's amount would follow the period - which
  needs the offer line to say how its quantity relates to duration. Best added before billing and credit exposure read
  Work Order lines. Until then: a line counted in time splits by quantity (3 of 6 months each); one counted in machines
  is quoted as two lines, or the second order comes as a Supplementary Offer.
- Customer Master / Finance integration.

## Work Order lines

Current WO lines copy selected offer lines. Deferred work:

- ~~Site per WO line.~~ Done by Slice 7C (14 September 2026).
- ~~GSTN per WO line.~~ Done by Slice 7C, with the billing address.
- Billing terms per WO line - **done by Slice 7D**: Part 1 (14 September 2026) recorded the billing
  basis and contracted hours (moved from 7C), working days, the Work Order rate, off days and off-day
  work, overtime and how monthly overtime is counted, breakdown and same-day offsetting, idle time and
  standby, minimum guarantee, part-month charging, and effective-dated periods; **Part 2 (15 September
  2026) added night/second shift, mobilisation, demobilisation and fuel**. What remains of `WBT-001` is
  listed below.
- ~~Customer line/reference mapping.~~ Done by Slice 7C.
- ~~Mobilization/demobilization terms.~~ Done by Slice 7D Part 2, recorded once for the line, on its
  first period. How the credit-back and waiver months are counted is the billing slices' (decision 9).
- Fuel, crew and extra charge terms - ~~fuel~~ done by Slice 7D Part 2 (supplied and included, supplied
  and charged at an agreed rate per litre or at actual cost, or customer-supplied at agreed litres per
  working and travel hour). Measuring the excess use belongs to log sheets and billing (decision 12).
  Crew comes with assignment; ~~extra kilometre and extra crew charges are not yet placed in a slice~~
  **extra kilometres, and the crew numbers with their extra-crew charge, are recorded by Slice 7D Part 4**
  (owner's answers 22 and 23 of 17-18 September 2026; implemented 24 September 2026, migration
  `20260908_0040`). What remains open is calculating those charges (8D) and assigning the crew (8B). The
  numbers are what the customer is charged for, never what the crew are paid - see "Operators' pay"
  below.
- ~~Contract start and end dates, per Work Order and per line.~~ Done by Slice 7D Part 3
  (17 September 2026), with extensions kept as history.
- ~~The crew's food and accommodation (left out by Slice 7D Part 2), and hours per shift and shifts per day as a Work
  Order states them.~~ Recorded by **Slice 7D Part 5** (owner's answers of 9 October 2026, migration `20260908_0052`):
  food, accommodation, travel to and from the job and daily travel, for operators and helpers, provided by the
  customer or at a cost it deducts or bills separately; and the shift pattern, which replaced Part 2's night shift.
  What remains open is calculating them (8D) and the assumptions A1 to A15 awaiting the owner's screen check. Four bear
  on money and 8D may not calculate with them until the owner confirms them: A9 (how one rate or a rate per later shift
  is counted), A10 (which hours the rate buys with several shifts), A12's whole-month part and A15 (a later shift's
  percentage of the Work Order rate)
  (`slice-7d-part-5-crew-upkeep-and-shifts.md`).
- Document checklist per line.

### Line-detail locks and a dependency, recorded by Slice 7C

Owner decisions of 14 September 2026 that later slices must implement; see
`docs/agent/slices/slice-7c-work-order-line-operational-detail.md`, decision 3.

- **When mobilisation starts**, `PUT /api/work-orders/{id}/lines/{line}/detail` must refuse changes
  to site, billing basis, contracted hours and customer line reference; changes go through a Work
  Order Amendment. Today only a Closed Work Order refuses.
- **When the e-invoice is generated**, the billing GSTIN and billing address lock - not at
  mobilisation, because a wrong GSTIN found after mobilisation must still be correctable.
- **Work Order release (7B)** must refuse while any line's `is_complete` is false, **or while any
  line's billing terms are incomplete** (`terms_complete` false, Slice 7D), **or while the Work Order's
  holiday list is incomplete** (`is_complete` false on `GET .../holidays`, Slice 7D Part 4).
- **Whether the holiday list locks at mobilisation with the billing terms** (Slice 7D Part 4). Decision
  6 locks every billing term at mobilisation, and the holidays decide which days take a line's off-day
  rate; but the list is the Work Order's, not a period's, and no decision covers it. Nothing locks it
  today but a Closed Work Order. Decide when mobilisation is built.
- **All billing terms lock at mobilisation too** (Slice 7D owner decision 6): after mobilisation,
  `POST`/`PUT`/`DELETE` on `.../billing-terms` must refuse, and a change goes through a Work Order
  Amendment that starts a new period. Once billing exists, a period already billed must never be
  rewritten (`WBT-001`).
- **The contract start locks at mobilisation** (Slice 7D Part 3 owner decision 19): `PUT
  .../contract-period` must then refuse a change to `contract_start_date`. A line's own dates lock with
  the rest of its detail. Not enforced, because mobilisation does not exist yet. The decision's other
  half - the end date moving only through an extension - **is enforced now, and from the first
  extension rather than from mobilisation** (owner's screen check, 22 September 2026). Mobilisation
  must also decide whether removing the latest extension stays allowed once equipment is on site.
- **Every lock must release again.** When an invoice is cancelled inside the statutory window, or a
  full credit note is issued against it, all billing and transaction locks are released so the source
  data can be corrected and a revised invoice raised (FRS 2.3.6.3). That applies to the mobilisation
  lock and the e-invoice lock above, and it reconciles with `WBT-001`'s rule that a billed period is
  never rewritten: a cancelled or fully credited period is no longer a billed one. Build the locks so
  they can be lifted by that path, rather than as one-way doors.
- **Dependency on the Account module (CRM lane).** A GSTIN's verification state is fixed when it is
  created; nothing can later mark an existing GSTIN rejected. The owner's process is that a
  SurePass rejection alerts the Sales Executive, who enters the correct GSTIN on the Account and
  re-picks it on each affected line. 7C already reports a rejected GSTIN as missing on every line
  that uses it, but that check cannot fire on a real rejection until SurePass lands or the Account
  module gains the audited manual route ADR-015 permits.

### The contract period, recorded by Slice 7D Part 3

Recorded 17 September 2026; see `docs/agent/slices/slice-7d-part-3-contract-period.md`.

- **A copied period is not checked against the receiving line's own dates.** "Apply these terms to
  other lines" checks every copied period against the *contract*, and deliberately not against the
  dates the receiving line carries for itself, so a line running 1 January to 31 March can receive a
  period starting 1 June. Enforcing it would block the case owner decision 20d describes - a line
  takes the terms and is then edited where its own charge differs - and no decision asks for it. If a
  real Work Order makes it a problem, the rule to add is the existing
  `classify_date_against_contract` called with the line's own bounds.
- **Nothing consumes the dates yet.** `contract_period_rules.py` is the tested rule that log sheets
  (FRS 2.5.1, daily sheets from the contract start), Work Order release (7B), closure (8E), the
  mobilisation credit-back period (FRS 2.7.2), demobilisation eligibility (FRS 2.7.4) and `WRR-001`'s
  scheduling window will each call. None of them exist.
- **No expiry alert and no approval of an extension.** Alerts need `NTF-001` and a notice period that
  is a setting nobody has chosen (Slice 8F). Approval needs `APR-001`; the screen says "Approval step
  not yet added" so a reader knows the system does not ask for one yet.
- ~~**An extension recorded in error is corrected by recording another**, not cancelled - the
  owner's decision of 17 September 2026.~~ **Superseded on 22 September 2026:** the latest extension
  can now be removed, putting the end back, and an extension must move the end later. The removal is
  kept in the audit log as `WorkOrderContractExtensionRemoved`.
- ~~**Whether an extension order may be dated in the future.**~~ **Answered the same day:** the owner
  explained the order date is not the thing to test. An order may arrive after the contract has ended
  and is recorded normally; what needs confirmation is an extension that *starts* later than the day
  after the end it follows, which leaves days outside the contract. Built in Part 3.
- **Days in a gap before an extension are outside the contract** (owner, 22 September 2026). Log
  sheets must not be created for them, and nothing may be billed on them; `contract_period_rules.py`
  answers `IN_GAP`, one of `CONTRACT_DATE_OUTSIDE_OUTCOMES`, for the slices that will ask.

### Read consistency and number messages on the Work Order page (found by analogy, Slice 7D Part 4)

Independent review of Slice 7D Part 4 found two defects in its new work (round 2, findings F-05 and F-06),
both corrected there. Each has an older relative, in work already merged, that the review did not
examine and that Part 4 deliberately leaves alone:

- **The contract period is read in two statements** (Part 3): `get_work_order_contract_period` reads the
  period, then its extensions. An extension committing between the two could return one version's end
  date beside the next version's extension list. The fix is Part 4's: read both in one statement.
- **Part 1 and Part 2 numbers get a generic refusal.** A rate, an hour count or a percentage typed as 0,
  negative or with three decimal places is sent, and the server's refusal reaches the screen only as
  "Check the values entered: one of them is not accepted." Part 4's `amountProblem` is the check to reuse,
  one field at a time, with each field's own limits. (An invalid entry in a browser number field reads as
  blank and is reported missing, which is a separate, milder oddity.)

Neither is urgent - the version guards prevent any wrong write, and the server refuses every bad
number - but both can confuse a user. Natural home: the long-form rework of the billing-terms page
(`UI_UX_CARRY_FORWARD.md`, Slice 7D.1), or its own small package.

### Billing terms deferred by Slice 7D

Recorded 14 September 2026 for Part 1 and extended 15 September 2026 for Part 2; see
`docs/agent/slices/slice-7d-work-order-line-billing-terms.md`.

- **From `WBT-001`'s minimum term set, deliberately not built yet:** taxable-value adjustment terms and
  approved exception/variation references (both belong with billing and approvals), and decimal
  precision and rounding settings (a Finance setting before billing goes live).
- **Invoice presentation:** the single-line average-rate bill, and showing off-day hours as normal-day
  overtime for a customer whose ERP requires it (Annexure-10 notes 1 and 4).
- **Different working times on different weekdays** (FRS 2.4).
- **Not in the source, so not guessed:** holiday premiums on hourly lines, and engine-hours overtime on
  shift or day lines. Add when a real Work Order needs them (owner decision 7).
- **Approval of a Work Order rate that differs from the quote** needs `APR-001` (owner decision 3).
- **Creating a period from a validated Work Order Amendment** waits for `D-07`. Mobilisation and
  demobilisation are recorded once for the line, so an amendment that changes them is part of the same
  `D-07` work rather than a new period (Part 2, decision 8).
- **Part 2's own deferrals:** how the mobilisation credit-back and demobilisation waiver months are
  counted, and from which date (decision 9); how customer-supplied fuel excess is measured, which belongs
  with log sheets and the billing team's review of a parked deduction (decision 12); separate overtime or
  breakdown rules for a night shift, which no Work Order has yet asked for (decision 10) - since Part 5, for any
  later shift; and any fuel charge form other than an agreed rate per litre or actual cost (decision 11).
- **Part 5's own deferrals** (9-10 October 2026): any check of the contracted hours against the shift hours (both are
  recorded as the Work Order states them; Billing UAT reconciles them); different shifts on different weekdays; a
  shift the Work Order states but does not charge; and an upkeep cost on a basis other than those recorded (per person
  per day, month or trip; per trip or per day whatever the number of people). Add each when a real Work Order needs it
  (decision 7).
- **What the owner's Part 4 answers send elsewhere** (17-18 September 2026; see
  `docs/agent/slices/slice-7d-part-4-remaining-billing-terms.md`):
  - **billing frequency** belongs to the equipment, not the Work Order or the line - one line can carry
    several machines and several cycles - so it is recorded with equipment assignment (8A) and used by
    invoicing (8G), not by 7D (answer 21);
  - **a monthly shortfall is deducted pro rata, with no minimum**, for every monthly line; there is no
    term to record, and billing (8D) applies it (answer 26). The monthly minimum-guarantee refusal's old
    wording, "the monthly rate already covers the contracted month", contradicted this and is corrected
    by Part 4;
  - **weekly-off and holiday work are not given separate rates** (answer 24, the recommendation
    withdrawn): Part 1's single off-day choice covers weekly off days and every listed holiday alike.

### PBL's default holiday calendar (owner, 2 October 2026)

**Built by HOL-1 (2 October 2026)**: `docs/agent/slices/hol-1-holiday-calendar.md`, with the owner's answers - a calendar
per year kept by Admin with a "complete" mark; each Work Order's changes to it, a holiday added or a calendar holiday made
a working day at the normal or the overtime rate (Q4); the holidays that apply to each state's lines; a reminder on the
Alerts for a year not set up (Q2). What it leaves is listed under "What HOL-1 leaves", after this section, which is kept
as the decision's record.

**There are holidays whether or not a Work Order names them.** PBL sets up a default holiday calendar
every year, and the system must provide the facility to do so. **Every Work Order inherits the
default calendar, and its own terms change it for that Work Order** - adding a holiday the calendar
does not have, or taking off a calendar holiday the Work Order works through. So there is one default
and, where a Work Order calls for it, that Work Order's variations to it. Raised by the owner while
preparing the Hiring user test (TE-7), when "The Work Order names no holidays" was shown to mean no
holiday dates at all. (Recorded first, the same day, as a Work Order's list replacing the calendar;
the owner corrected that: a Work Order can name some holidays and leave the rest to the calendar.)

- **What it supersedes.** Answer 25 of Slice 7D Part 4 said national and festival dates are stated in
  the Work Order "not taken from a company calendar". They now come from the calendar, and the Work
  Order states only how it differs.
- **What it changes in 7D Part 4, when the calendar is built** - nothing before then: the routes and
  screens stay as they are until the calendar exists to vary.
  - The Work Order's holiday list becomes its **variations to the calendar**: a holiday **added**
    (date, kind, description, as today) or a calendar holiday **removed** (the date, and why). Today it
    can only add. A holiday moved to another day is one removal and one addition.
  - The dates already listed carry over as additions; one that is already in the calendar for the
    site's state adds nothing and does no harm.
  - "The Work Order names no holidays" becomes "follows PBL's calendar unchanged", and is still an
    answer that must be given before release (7B), as now.
  - The variations stay one list for every line of the Work Order (decision 27); each line applies
    them to the calendar for its own site's state.
- **The calendar decides which days are holidays, never what they are charged.** Work on any holiday,
  default or named, is charged by the line's single off-day choice (answer 24), a Work Order term; a
  line whose choice is "not in the Work Order" charges nothing extra for it. So the default does not
  guess a term (`WBT-001`: missing terms are not guessed).
- **The facility, as recommended:** a calendar for each year, kept by an authorized role (Admin until
  a position is mapped under `ORA-001`): each date with its kind (national or festival), a description,
  and where it applies - all of India, or named states, since festivals differ by state. A line takes
  the dates for its site's state.
- **Left for the package that builds it:** what happens when a Work Order runs into a year whose
  calendar is not set up yet (at least a reminder before the year starts, as ELG-2 reminds about
  certificates); and how a change to a year already used is handled - approved log sheets are
  corrected by versioning (`LBE-001`), never rewritten. It is built before or with log sheets (8C),
  which mark the holidays; see `docs/agent/FUTURE_SLICES.md`. **Answered by HOL-1** (Q2, Q3): a reminder on
  the Alerts for this year and next until each is marked complete, holding nothing; any year may be changed at any
  time, every change kept, with a warning for a day already passed.
- **Refined by the owner's answer to HOL-1's Q4** (2 October 2026): a calendar holiday is not "removed with why" but
  made a **working day**, charged at the normal rate or - every hour of it - at the line's overtime rate, with an
  optional note. No Work Order works through every festival, so a single "national holidays only" choice is not wanted.

### What HOL-1 leaves (2 October 2026)

- **Found by analogy at HOL-1's review, not fixed there** (round 1, HOL1-R1-001): ELG-2's
  `alerts.save_setting` reads the setting it returns after its commit has released the module's lock, so a second save
  committing in that instant could be shown as the first one's version. The calendar's save builds its answer before it
  commits; the reminder settings' save should do the same. Harmless meanwhile beyond the message shown - the version
  guard prevents any wrong write - and the settings are saved by Admin alone. Natural home: ELG-2's next package, or
  its own small one.

- **Marking a log-sheet day as a holiday or a working day** (8C), through `work_orders/holiday_rules.py`, and correcting
  an approved log sheet after the calendar changes a day it used - by versioning (`LBE-001`), never rewriting. HOL-1 lets
  any year change at any time because nothing is billed yet.
- **Charging** (8D): a holiday by each line's off-day term; a working day at the normal rate, or every hour at the
  line's overtime rate. A working day at the overtime rate on a line recording no overtime rate is shown on the Work
  Order page and blocks nothing; billing must refuse to guess the rate (`WBT-001`). Whether such a day's hours count
  towards a monthly line's contracted hours is billing's question.
- **Whether release (7B) refuses** while a year the contract runs into is not complete. HOL-1 holds nothing; the Work
  Order page and the Alerts say so.
- **Whether the Work Order's changes lock at mobilisation** - still open, as recorded under the Slice 7C locks.
- **Changes for some lines only** ("only these lines"), if a Work Order ever needs them (decision 27): nothing entered
  changes.
- **Copying last year's calendar, or loading holidays automatically**: Admin enters each year; later, if Admin asks.
- **Email and SMS for the calendar reminder**: with the notification service (`NTF-001`).
- **The Hiring user test pack** (`docs/uat-hiring/`) still describes Slice 7D Part 4's holiday list ("names no
  holidays" / "names these holidays"). By the owner's answer to Q1 the test runs on TE-7's version; the guide and the
  Sales and Accounts sheets are updated after the test, with what the testers say about holidays.

### Operators' pay: a standing rule (owner, 17-18 September 2026)

**An operator's pay never derives from the customer's billed overtime.** PBL sets its operators'
hours. An operator contracted for 10 hours works 10 on a Work Order specifying 8: the customer is
charged 2 hours of overtime; the operator gets no overtime pay. Crew attendance and pay take their
hours from PBL's own HR terms, through the HR reference of ADR-032 - never from a Work Order, its
billing terms, or the crew numbers Slice 7D Part 4 records. Applies to crew assignment and attendance
(8B) and to anything that later computes pay; recorded against 8B in `docs/agent/FUTURE_SLICES.md`.

### Contracts are independent of each other: a standing rule (owner, 17-18 September 2026)

**Contracts with customers, vendors and employees are independent of each other.** Where one depends
on another, it is created while *viewing* the other, and nothing is inherited automatically. Slice 7D
Part 3's "Apply these terms to other lines" is the pattern: it copies once, at the user's hand, and
the copies then stand on their own. Where it applies:

- **Market Hire** (`MHA-001`): a vendor's hire terms for a hired machine are written while looking at
  the customer's Work Order line, never derived from its rates, and a later change to the customer's
  terms never changes the vendor's;
- **Crew** (8B): an operator's hours and pay come from PBL's HR terms, whatever the customer's Work
  Order says - the operators'-pay rule above is one case of this one;
- **Amendments**: a customer's Work Order amendment does not reach into a vendor's contract or an
  employee's terms.

The owner decided on 24 September 2026 that this is recorded here rather than as an ADR (Slice 7D
Part 4, decision 31). It is a rule for every slice that links two of these contracts, not work waiting
to be built, so it is not struck through when any one of those slices is done.

### FRS 2.3 to 2.8 gap check (16 September 2026)

The project owner asked whether anything built or planned would fall short of FRS sections 2.3 to
2.8 (multi-site lines, billing basis and overtime, log sheets, fleet and crew, compliance and
logistics, invoicing). All 45 requirements were checked against the code and the records. **Nothing
built so far rules any of them out.** What the check found:

**Six items needed attention rather than recording.** They were not lost, but each had no home:

1. **Contract dates.** A Work Order has no contract start date, end date or validity anywhere -
   confirmed against `backend/app/modules/work_orders/`. It was noted only as out of scope in 7C.
   Needed by validity control (2.3.7), expiry alerts (2.3.8), renewal (2.3.9), automatic daily log
   sheets (2.5.1), the mobilisation credit-back period (2.7.2), demobilisation eligibility (2.7.4)
   and `WRR-001`'s scheduling window. **Going into Slice 7D Part 3.**
2. **Entering the same terms on several lines (2.3.2).** Terms exist per line only, with no way to
   copy them between lines. **Going into Slice 7D Part 3** at the owner's direction of 17 September
   2026, as "apply these terms to other lines" with tick boxes, pushed from whichever line is open -
   not as terms inherited from a Work Order header. Both directions were weighed: pushing chooses
   its source just as freely, and settles a ten-line Work Order in one action.
3. **Terms that cannot yet be recorded:** billing frequency (2.8.1), extra-kilometre allowance and
   rate and extra-crew allocation and rate (2.5.6), and separate rates for weekly-off work and
   holiday work (2.4.5), which today share one choice and one rate. **Going into Slice 7D Part 4.**
   **Answered 17-18 September 2026** (recorded in
   `docs/agent/slices/slice-7d-part-4-remaining-billing-terms.md`): extra kilometres go into Part 4 as
   recommended; crew goes in as numbers of operators and helpers per billing unit of the line; **billing
   frequency leaves Part 4** for the equipment (8A, 8G); and **separate weekly-off and holiday rates are
   withdrawn** - Part 1's single choice records both, so no migration. The holiday dates themselves
   join Part 4 as a list the Work Order states.
4. **A monthly line refuses a minimum guarantee** and says the monthly rate already covers the
   contracted month, while 2.4.4.2.1 bills hours below the contracted hours pro rata. **A question
   for the owner in Slice 7D Part 4**: is a monthly contract ever billed in full, or to a minimum,
   whatever the hours worked? **Answered 17-18 September 2026:** neither - a monthly shortfall is
   deducted pro rata, with no minimum, and there is no new term. Only the refusal's wording was wrong;
   Part 4 corrects it, and the pro-rata rule is recorded for billing (8D).
5. **The PAN hierarchy is not enforced (2.3.4).** See the CRM entry in
   `docs/agent/FUTURE_SLICES.md`: the same PAN may sit on two Accounts, and a GSTIN is not checked
   against its Account's PAN.
6. **Locks must be releasable (2.3.6.3).** Recorded above, under the Slice 7C lock decisions.

**Everything else was already recorded, or is now recorded in the slice that will build it.** The
additions are in `docs/agent/FUTURE_SLICES.md`, against 7B, 8A, 8B, 8C, 8D, 9A and the credit gate,
plus four new entries - 8E closure and demobilisation, 8F contract expiry and renewal, 8G invoice
preparation and submission, 8H collections and escalation. Each carries its FRS reference.

**One thing the source itself gets wrong:** the requirement for additional usage and crew charges
carries the RefID of the holiday reclassification requirement (2.4.9) and repeats its title. It is
recorded here by what it asks for, not by that number.

**One decision this text may settle.** `D-04` asks whether vendor hire needs a purchase order.
FRS 2.6.2 answers it for log-sheet posting: a posted vendor Purchase Order must exist before a hired
equipment vendor log sheet may be posted. Whether assignment also requires one is still open. The
owner is confirming.

### Carried to Slice 7D Part 2 (owner decision, 14 September 2026)

**STATUS, 15 September 2026: BOTH items are CLOSED.** The owner's screen check of Part 2 passed,
covering P2-9 and P2-10 (the page-load generation) and P2-11 (Part 1's stale-message fix, steps 11c and
11d). The first item is CLOSED by Slice 7D Part 2's code. The Work Order detail page
now has one page-load generation: every load takes the next number, every result and every save carries
the number it started in, and a result from any other generation is ignored. Applying a save no longer
starts a new generation, which was the defect. The rules live in
`frontend/src/pages/work-orders/workOrderPageState.ts` with pure-rule tests replaying both sequences
(`workOrderPageState.test.ts`); the frontend still has no component-test capability, so the page's own
wiring is covered by the diff, the existing Playwright specs and the owner's screen check (acceptance
steps P2-9 and P2-10). The original entry is preserved below as the record of what was found.

The second item, the owner's re-check of Part 1's stale-message fix, was acceptance step P2-11 and passed
at the same screen check.

- **First item of Part 2's slice document - Work Order detail page load generation.** Independent
  review round 5 of Part 1 found, and the owner chose to fix in Part 2 rather than hold Part 1: the Work Order detail page has no single load generation. The main Work Order and lines requests have
no generation check (since Slice 5A), and a finished save restarts the line-detail or billing-terms load
gate unconditionally (the Slice 7C pattern, copied by 7D). Navigating to another Work Order while one is
still loading, or pressing Refresh while a save is in flight, can therefore let an older response show
under the newer Work Order, or leave the billing terms read-only until the next reload. The server's
revision checks mean no stale screen can save a wrong value. Correction: one page-load generation (or
AbortController) covering the Work Order, lines, line-detail and billing-term loads and every save
callback; results apply only while their generation and Work Order are current, and a save started
before a newer load never invalidates it. Test it with component or integration tests for out-of-order
navigation and refresh during an in-flight save - the frontend has no component-test capability yet.
  See the "Round 5" entry in `docs/agent/slices/slice-7d-work-order-line-billing-terms.md`.
- **Owner re-check of Part 1's stale-message fix at Part 2's screen check.** After Part 1's screen check
  the owner asked for a fix (an error under "Add a later period" stayed after later saves). It was made
  and tested but not re-checked on screen: the owner will check it together with Part 2 (acceptance
  checklist steps 11c and 11d of `docs/agent/acceptance/slice-7d-work-order-line-billing-terms-acceptance.md`).

### A full test of the Hiring lane before UAT (owner, 14 September 2026)

Before the Hiring work goes to UAT - possibly as or before Slice 7E - the owner expects a full test pass
to iron out remaining wrinkles across 7C, 7D and what follows. Inputs it must not lose:

- ~~the Part 2 carry-over (page load generation)~~ - closed by Part 2 on 15 September 2026, and its
  screen check (acceptance steps P2-9 and P2-10) passed the same day;
- the frontend component-test capability recorded under "Frontend component-test capability", without
  which the Work Order page's request ordering cannot be tested directly;
- the owner's screen checks of 7C and 7D, and any wrinkles they raise;
- the Slice 7C GSTIN-rejection dependency (above), which needs SurePass or the Account module's manual
  route before the "billing GSTIN missing (rejected)" check can fire on a real rejection;
- the Billing/Finance UAT `WBT-001` requires: every implemented formula compared with Annexure-10 and
  real Work Orders before billing goes live (7D records terms only; nothing is calculated yet);
- one unexplained intermittent frontend failure seen during 7D ("periodLabel > names period 1 ...",
  once, then 9 clean runs); watch for it recurring;
- one E2E sign-in stall seen during 7D on a worktree stack: the first test's login never reached the
  backend and timed out, and an immediate rerun passed; watch for it recurring in CI.
  **Recurred 22 September 2026** on the Slice 7D Part 3 worktree stack, straight after a 24-minute
  backend regression. The first test's sign-in again never reached the backend. In a later test, the
  amendment page's three requests all completed at the same instant about 11 seconds after sign-in,
  past the test's 10-second wait, with no backend error. The run took 2.4 minutes; an immediate rerun
  passed in 54.7 seconds. Twice now, both on worktree stacks: requests appear to queue in front of the
  backend, and the frontend's `vite preview` proxy is the likeliest place. Worth diagnosing before CI
  sees it rather than after. Later the same day a run passed, but again took 2.5 minutes straight after
  a backend regression - so the slowness follows the regression even when nothing fails.
  **Cause found, 22 September 2026: the developer machine's memory, not the application.** The laptop
  has 11.9 GB; WSL 2 with no `.wslconfig` takes up to half of it for Docker's VM and never hands any
  back, so Windows sat at 96-97% used with 24 GB committed and paged the VM out to disk. Inside the VM
  that shows as raised IO-stall figures and requests arriving at the backend ten seconds late, with no
  error anywhere - sign-in timing out, or a page whose requests all complete at once. Two consecutive
  runs failed 3 and then 5 tests, each in 3.2-3.4 minutes. With a `%USERPROFILE%\.wslconfig` of
  `[wsl2] memory=4GB, processors=4, swap=2GB, autoMemoryReclaim=gradual`, a `wsl --shutdown` and a
  restart, host use fell to 87% and the same suite passed 17/9/0 in 1.0 minute. **Not an application
  defect and nothing to fix in this repository**; recorded because the symptom looks exactly like one,
  and because it will recur on any machine that runs this stack with memory that tight. The E2E suite
  itself runs one browser at a time (`workers: 1`), so it is not the memory that is at fault either.

## Code structure in the Work Orders module (measured 23 September 2026)

Recorded at the project owner's direction after Slice 7D Part 3, as a note rather than a scheduled
package. Nothing here is a defect: the module follows the layout `CODING_STANDARDS.md` asks for, the
SQL is PostgreSQL-only and statically guarded, every action records a business event, and Part 3 added
a pattern worth copying - `contract_period_rules.py` is pure logic with no database, clock or I/O, so
it can be tested exhaustively and reused by log sheets, release and billing.

What was measured:

```text
backend/app/modules/work_orders/service.py      3,529 lines, 84 functions, 18 over 60 lines
  largest: copy_work_order_line_billing_terms 191, _normalize_billing_terms 152,
           create_work_order_contract_extension 133, create_work_order_from_commercial_offer 131
  five concerns in one file: handoff (Slices 5A/6A/6O), amendments (6O.2), line detail (7C),
  billing terms (7D Parts 1 and 2), contract period and copying (7D Part 3, about a quarter)
backend/app/modules/work_orders/repository.py   1,646 lines, one function over 60
backend/app/modules/work_orders/routes.py         653 lines, nothing over 22
frontend WorkOrderBillingTermsSection.tsx       1,282 lines; WorkOrderAmendmentDetailPage 920;
                                                WorkOrderDetailPage 834
```

**This is not Part 3's doing, and not only this module.** `commercial_offers/service.py` is 3,712
lines, and `CommercialOfferDetailPage.tsx` about 6,150 (already recorded in
`UI_UX_CARRY_FORWARD.md`). Whatever convention is chosen for splitting a large service should be
decided once and applied to both, rather than per slice.

**TE-6 decided it.** The convention is `CODING_STANDARDS.md`, "When a service outgrows one file". When
`commercial_offers/service.py` is split, start from TE-6's proof scripts in
`docs/agent/technical-enablement/te-6-proof-scripts/`, which generated that split and proved it moved
nothing. Also retarget `_status_writing_function_sources` in
`backend/tests/test_slice_9b_pilot_hardening.py` to walk the new package, as TE-6 did for the amendment
scan. It keeps only functions whose `__module__` is the service module itself, so after a split it
would find none and fail.

*Added 7 October 2026 (TB-1 TB1-601).* Three tests in
`backend/tests/test_slice_9e_quotation_generation.py` also patch names on the service module itself
(`monkeypatch.setattr(offers_service_module, ...)`: `insert_commercial_offer_quote_document`, twice,
and `list_commercial_offer_tc_clauses_for_offer`). After a split the moved code looks those names up
in its new concern module, so the patches would reach nothing - and the tests would pass while
proving nothing, not fail. Move each patch to the concern module, and show each test failing with its
patch removed, before and after the split (corrective package CS-11).

*Reconciliation, 8 October 2026 (TB-1 CS-11):* done. `commercial_offers/service.py` is split into thirteen concern
modules and `common`, and re-exports its 54 public names
(`docs/agent/technical-enablement/CS_11_COMMERCIAL_OFFERS_SERVICE_SPLIT.md`). The three 9E patches are on
`services/quote_documents.py`, each test shown failing with its patch removed on the base and on the split; the 9B scan
walks the package; and two more tests the scan of every caller found, which called private helpers through the
service, follow the code too. Unchanged, the 9E tests fail against the split rather than pass: `monkeypatch.setattr`
refuses a name the thin module does not hold. They would have passed while proving nothing only had the service kept
re-exporting the repository names, which TE-6's rule forbids.

What to do, in order, with the risk of each:

1. ~~**Split `service.py` into a package by concern** - handoff, amendments, line detail, billing terms,
   contract period - keeping a thin `service.py` that re-exports, so no caller changes. Mechanical, no
   behaviour change, low risk.~~ **Done by TE-6** (23 September 2026), with copying terms placed beside
   billing terms rather than the contract period.
2. ~~**Break up the three longest functions.** Copying terms (191 lines) has a real sequence and can be
   split into verify-targets, read-source, write-each-line. Normalising billing terms (152) and listing
   missing terms (112) are field-by-field chains: a table of field rules would shorten both and make
   Part 4's extra terms cheap to add. Low to medium risk; both are well covered by tests.~~ **Done by
   TE-6**, split along the parts the terms arrived in rather than into a table.
3. ~~**A context manager for the write preamble.** Fifteen functions open with the same lock, row read and
   version check and close with the same commit/rollback. Medium risk; do it with item 1, not before.~~
   **Done by TE-6 for the close only.** The fifteen share `except Exception: db.rollback(); raise`
   exactly, not their opening: seven lock and validate outside the `try`, so a common opening would
   have changed when they roll back. See `TE_6_WORK_ORDERS_SERVICE_SPLIT.md`, "As built".
4. **Move test cases down a level where they do not need the API.** 351 tests take about 6.5 minutes
   because each builds a full Lead-to-Work-Order chain; the pure-rule tests run in seconds. (Those 351
   are Part 3's two files, the route guard and the harness; the ten files testing Work Orders are 725,
   and took 18 minutes on a host with 1 GB free, 23 September 2026.) Low risk,
   slow to do, and worth it only when the suite's time starts to hurt.
5. **Split the frontend sections.** Same problem as the Commercial Offer page. **Do not start before the
   frontend has a component-test capability** (see "Frontend component-test capability" above); that
   ordering is already recorded and applies here for the same reason.

**The work package for items 1 to 3 is written**, at the owner's direction on 23 September 2026:
`docs/agent/technical-enablement/TE_6_WORK_ORDERS_SERVICE_SPLIT.md`. It carries the scope, the shared-
helper question that decides whether the split is easy, the mechanical equivalence proof the review
packet must contain, and what to watch for - seven importers, a test that introspects the module by
name, and the BOM.

**When.** Items 1 to 3 are one small package with no behaviour change, best taken after Slice 7D Part 3
merges and **before Part 4**, which will otherwise add more terms to exactly those long functions.
Item 4 when the suite's run time becomes a nuisance. Item 5 after the component-test gap is closed.

Deliberately not on this list: the rules module, the migrations and the contract files, which are in
good order; and any change driven by line count alone.

## Resource requirements and the Equipment Reference (WRR-001, 24 September 2026)

Built: what a Work Order line needs on site, and version 1 of the platform's equipment structure
(ADR-037). See `docs/agent/slices/wrr-001-resource-requirement-foundation.md`, section 17 and the
implementation record. Deliberately not built, each with where it goes:

- **The Plum transformer** and the **Model** and **Machine** records it fills (design section 6) -
  **built by ERT-1 (25 September 2026)**: `docs/agent/slices/ert-1-plum-machines-into-the-equipment-reference.md`
  and "Plum's machines: what ERT-1 left out" below; the kit is ERT-2.
- **Asking Plum for its improvements** (ADR-037 route A): a type field or the platform's type code, a
  model key, capabilities in the platform's units, the Annexure-20 validity dates, and a link between a
  crane's superstructure and carrier. The owner is also obtaining a sample of Plum's vehicle type master;
  if it holds a level version 1 cannot take in, that comes back to the owner (design section 20).
- **The part classes of the component hierarchy** (boom section, hook block, counterweight, tool), with
  the machine records - see "Asset component hierarchy" below. The additive change is made: structure
  version 2 (ERT-1) added `class_kind_code`, `equipment_part_fit` and the first part class, Crane
  carrier; the kit's classes come with ERT-2.
- **A maintenance screen for the structure**, for Fleet's Equipment Master owner (Q14), with a write
  permission of its own. Until then the structure changes only by migration, each change a new version.
- **Combinations of machines** (prime mover plus bed) are Transportation's (Q15). The tables hold items
  under a requirement; this slice allows exactly one (`ck_rr_item_single_item_this_slice`). A rule such
  as "one prime mover takes at most one bed" attaches to the items when Transportation adopts them.
- **A "how many of this item per unit" field**: not added, because with one item it is always 1; it can
  be added later with a default of 1 without touching existing rows.
- **Structured licence and skill requirements** - `crew_notes` is free text; structured checks and their
  evidence belong to Eligibility (`ELA-001`).
- **Availability, reservation, assignment and fulfilment counts** (`RPA-001`, 8A). The statuses
  `PARTLY_FULFILLED`, `FULFILLED` and `COMPLETED` are reserved and not accepted by the database yet;
  "remaining" will be `units_required` minus what Assignment records. `WRR-001`'s rule that cancellation
  releases uncommitted reservations applies once reservations exist.
- **Whether Work Order release (7B) refuses a machine line with no requirement** - 7B's question (Q1).
- **Work Order and line versions** in the requirement (`WRR-001`'s minimum list): a Work Order has no
  versions until amendments are applied (`D-07`).
- **Market Hire and own-versus-hired** - `MHA-001` is `PROPOSED`.
- **Automatic requirements, a split action, and alerts** - not wanted now (Q1, Q7).
- **Requirement dates re-checked when the contract changes**: a contract change is not blocked by a
  requirement; the requirement shows `OUTSIDE_CONTRACT` instead (owner, Q8).

## Plum's machines: what ERT-1 left out (25 September 2026)

Built: Plum's vehicle report brought into models and machines through a preview Admin confirms, with the
Fleet Admin's value rules and corrections (`docs/agent/slices/ert-1-plum-machines-into-the-equipment-reference.md`,
section 20). Deliberately not built, each with where it goes:

- **Owning company codes.** The owning company is kept as Plum gives it, trimmed, and corrected like any
  other Plum value. A confirmed list of company codes (the design's `equipment_owner_company`, Q8) waits
  for the first module that needs a code - Finance or Fixed Assets - and needs its own screen.
- **The detachable kit and the depth setting** - ERT-2, **built 26 September 2026**; see "Detachable kit:
  what ERT-2 left out" below.
- **Statutory validity dates and every eligibility check** - the Eligibility foundation (Q9, Q12).
- **Prime mover and bed pairing** - Transportation's (Q7). Plum's `BedNo` is kept with the prime mover's
  last report values only.
- **A maintenance screen for the category rules** (design section 6) and for the structure: both change
  by migration until then. The rules are shown read-only on the Plum report page.
- **Creating a machine Plum does not hold**, and any feed back into Plum - Phase 2 and Phase 3 of
  ADR-037.
- **Machine location** - 8A. **Equipment documents** - see "Equipment documents" below.
- **A Fleet Admin role** - Admin holds `EQUIPMENT_REFERENCE_MANAGE` until one exists; the role is given it
  by a grant.
- **Who else sees engine and chassis numbers.** Admin only for now (owner, 25 September 2026). The owner
  is not yet sure whether Operations should, and Finance may need them during audits. Either is a grant of
  `EQUIPMENT_IDENTITY_READ`, with no code change, when the owner decides.
- **Closing value rules automatically**: an export may be partial, so a rule stays open until the Fleet
  Admin closes it; the list to send to Plum shows how many rows of the latest report still carry it.

## Equipment Hiring execution

Deferred work:

- Equipment assignment.
- Own/hired equipment treatment.
- Vendor hiring and procurement linkage.
- Crew/operator assignment. Crew hours and pay come from PBL's HR terms, never from the customer's
  billed overtime - see "Operators' pay: a standing rule" above.
- Each machine's billing cycle, weekly or monthly, recorded with its assignment (owner, answer 21 of
  Slice 7D Part 4).
- Skill, licence and certification eligibility checks - the **Eligibility foundation**, before 8B
  (`FUTURE_SLICES.md`; owner, 25 September 2026).
- Equipment replacement, demobilization and closure.
- What each line needs is recorded since WRR-001; assignment will fulfil those requirements - see
  "Resource requirements and the Equipment Reference" above.

**8A core (28 September 2026) built** own machines allocated to the requirements' units, held before release, with
the eligibility decision, replacement and history, each machine's billing cycle and the kit going to site per trip
(`docs/agent/slices/8a-core-equipment-allocation.md`, sections 12 and 17). What it left out, each with where it
goes:

- **Hired machines and vendors** - the own/hired flag, the vendor placeholder, the Purchase Order gate: 8A after
  the user test, once `D-03` and `D-04` are decided and `MHA-001` is approved.
- **Firm allocation**: 7B, which turns holds into allocations after a fresh check. The owner leans to releasing a
  line at a time rather than the whole Work Order (28 September 2026); decided with 7B.
- **Dispatch and arrival**: the mobilisation transport order; fire extinguishers and first-aid boxes checked
  before a machine leaves (ELG-1 Q1); the load test after erection on a construction site (BOCW); delivery
  challans and e-way bills (HSN and declared value, with Finance and the tax adviser); over-size permits; mats
  and timber. With dispatch, after release.
- **Trips (Own Load)** (owner, 29 September 2026). A crane may go to site in several loads, broken down into its
  parts; 8A core records as many Trips (Own Load) as needed, each saying in the planner's words what it carries
  and listing its kit. Deferred:
  - **Moving or removing a Trip (Own Load).** Once added, a trip keeps its day, so a change of dates that would
    leave it outside the allocation is refused (freeing or replacing still ends an allocation early). The owner:
    "Defer it".
  - **Each crane model's standard loads**: how many loads the model travels in, what goes on each, and each
    load's weight and size, from the manufacturer's transport plan - held on the Equipment Reference as kit is,
    so an allocation's trips fill in from the model instead of being typed. The weights and sizes are what an
    over-size permit needs.
  - **The crane's major parts as records** - base, carbody, crawlers, upper works, boom butt - so each load names
    them and demobilisation checks them back (8E). These are the fitted parts ERT-2 left until Hiring needs them.
  - **Each Trip (Own Load) linked to Transportation's "PBL Own Loads" order** (FRS 2.7.1). Transportation owns the
    order and the vehicles; Hiring raises it (`FUTURE_SLICES.md`, 7B).
  - **Loads leaving before the allocation's first day.** A trip goes on a day of its allocation, so today the
    planner starts the allocation on the first dispatch day.
- **Gate passes**: 8A after the user test; the closure check is 8E.
- **General tools** issued from inventory: the inventory integration.
- **Kit coming back, and a completed job** (`COMPLETED`): 8E.
- **Carrying the kit over to a replacement machine** in one step: later, if the screen check asks for it.
- **Crew**: 8B.
- **Reminders and escalation** for certificates running out before or during a job: ELG-2, reading the
  allocations.
- **`EligibilityLapsed` and `EligibilityRestored` as events**, and a recheck job: the job runner (ADR-019). Until
  then an allocation's answer is worked out when read, and **Check again** stores one.
- **Approving "needs approval"**: the approval capability (`APR-001`, `ORA-001`). Until then such a machine
  cannot be allocated.
- **A time limit on holds**: a setting, when wanted (`RPA-001`). Holds do not expire.
- **HSN and asset value in the history** (FRS 2.6.1): no source holds them; with Finance, when the challans need
  them.
- **Where a machine is when not allocated**: a location source; Plum's report has none.
- **Maintenance restrictions on availability**: Plum Maintenance, when integrated.
- **An availability calendar across machines**: later.
- **Site states the platform cannot match**: an address whose state is not one of the 36 states and union
  territories, by name or code, is refused with a message asking for the address to be corrected. A small list
  of other spellings would be the owner's to approve, if the user test finds many.

## Asset component hierarchy (recorded 24 September 2026)

Source: FRS 3.1, "Parent-Child Asset Relationship"; the equipment business rule "Asset Hierarchy";
Annexure-11(A), which splits a Manitowoc M 2250 into its parts with each part's share of value; and
Annexure-11(B), tools with issue quantities. Nothing is built yet.

Owner decisions, 24 September 2026:

- A machine can have child parts, and a part its own children, down to a **depth that is a setting,
  default 3** - crane, carrier, tyre; crane, tool box, spanner. Annexure-11(A)'s percentage groups
  ("Boom and Jib", "Counter Weight") are categories of parts, not a level of their own.
- **Build only what Hiring needs.** The rest waits for the modules that own it.

What Hiring needs, built with the Equipment Reference's machine records (the package after WRR-001):

- a parent-child link, dated from fitting to removal, so replacing a part keeps its history;
- two kinds of child: a part tracked on its own (hook block, numbered counterweight, fire
  extinguisher) and a counted accessory specific to the machine;
- **fitted parts and detachable kit**, both recorded as the machine's children. Fitted parts are
  always part of the machine: carrier, upperworks module. Detachable kit belongs to the machine but
  goes to site only when a job needs it: boom inserts, counterweights, hook blocks, tackles and
  lifting accessories;
- the part classes these need, in the Equipment Reference, and what each may be fitted to;
- Plum's superstructure and carrier pairs, through the transformer (ERT-1).

**Tools and where the kit comes from (owner, 25 September 2026).** An earlier line here expected
"Plum's per-vehicle tools list". There is none:

> I do not understand what you mean by Tools Report. Anything that is of the nature of a fixed asset
> associated with and specific to an equipment is in the equipment list I shared. There will be other
> tools such as spanners, screw drivers etc. which are not specific to an equipment are in the inventory
> system and we will have to associate them from that system. We probably can add that piece later
> because when a tool is assigned to an equipment to be deployed / mobilized, then it impacts the
> inventory system

- Equipment-specific fixed assets are rows of Plum's equipment list and come in through the
  transformer. The report of 24 September holds none apart from crane halves, so the detachable kit is
  recorded on the platform by the Fleet Admin (ERT-2; the ADR-037 refinement in the ERT-1 design).
- General tools - spanners, screwdrivers, socket sets, the tools of Annexure-11(B) with their issue
  quantities - are not the machine's children. They are inventory items, associated with a machine
  when issued to it for a mobilisation, which moves stock: later, with the inventory integration.

**Kit is shared by crane model (owner, 26 September 2026; ERT-2 design).** Asked whether kit belongs to
one crane or is shared, the owner answered that kit is interchangeable among units of the same model and
can be associated with a model. Research then showed that sharing also crosses models (Grove, Liebherr,
Manitowoc) and can stop at a model version (SANY). The owner made the research authoritative over the
inputs. Kit is therefore held for **the exact crane models it fits**, not as a crane's children, and the
earlier lines "both recorded as the machine's children" and "an insert left at the yard still belongs to
its crane" are superseded for kit. Fitted parts stay a machine's dated children. When a crane is sold, the
buyer usually takes a set of kit, which the Fleet Admin retires. See
`docs/agent/slices/ert-2-detachable-kit.md`, sections 1, 2 and 5.

Used later by Hiring:

- **The mobilisation BOM** is picked from the machine's detachable kit, and from general tools issued
  out of the inventory system, per trip; Work Orders need not list these items (8A). It records what
  went to this site, and is never stored in the hierarchy, so an insert left at the yard still belongs
  to its crane. The inventory part waits for the inventory integration.
- Demobilisation checks the BOM's returnable items back - the kit to its machine, general tools to
  inventory (8E; FRS 3.1).
- Eligibility checks certificates on the machine and on the parts that carry them: load test on a
  hook block, slings and shackles, fire extinguisher, first-aid box (FRS, "Maintenance Compliance &
  Statutory Gating"; `ELA-001`).

Left to the modules that own them, not designed now: maintenance planning by part, cost booked on
parts and totalled up the tree, each part's share of the machine's value (Annexure-11(A)), tyre life
from receipt through rotation and retreading to scrap, and the battery register - Maintenance, Fixed
Assets and Inventory.

## Equipment documents (owner, 25 September 2026)

Recorded with the ERT-1 design (its section 1, comment 4). Not built; to be set up when appropriate.

> Finally, there needs to be a provision to attach links to Equipment documentation - load charts and
> the like - to the assigned equipment.

- **Where they attach.** To a **Model**, for what applies to every machine of it - load charts,
  operator's and service manuals, specification sheets - and to a **Machine**, for what is its own - its
  configuration's load chart, name plate image, certificates. Both come from ERT-1. A machine assigned to
  a job (8A) shows its own documents and its model's.
- **Links or files.** A link to where the document already lives (a manufacturer's site, the ERP
  SharePoint site of ADR-036), or a file stored through Slice 9C's document foundation.
- **What it takes.** Slice 9C's documents attach to a record by type, fail-closed per type
  (`documents/contract.py`, `DOCUMENT_LINK_READ_PERMISSION` and `DOCUMENT_LINK_WRITE_PERMISSION`): two
  new types - equipment model and equipment asset - read with `EQUIPMENT_REFERENCE_READ` and attached
  with `EQUIPMENT_REFERENCE_MANAGE`. A link, as distinct from a file, needs a small addition to that
  foundation.
- Certificates with validity dates are the Eligibility foundation's; this item is the reference
  documents.

## Detachable kit: what ERT-2 left out (26 September 2026)

Built: kit held for the crane models it fits, shared by their cranes; four kinds (boom and jib sections,
counterweight, hook blocks, the cranes' own lifting tackle); counterweight counted, the rest one by one;
retirement with the day and the reason; the depth setting of 3 for fitted parts
(`docs/agent/slices/ert-2-detachable-kit.md`, section 18). Deliberately not built, each with where it goes:

- **The mobilisation BOM** - which pieces went to site with which crane, per trip - and checking them back:
  8A and 8E. Which pieces a configuration needs, and which go on every job (the boom foot and head, by their
  types), is 8A's. (8A core, 28 September 2026, built the list per trip; which pieces a configuration needs is
  still to come - see "Equipment Hiring execution".)
- **Mats, timber and cribbing**, and store-held slings and shackles: 8A and the inventory integration.
- **Fitted parts other than Plum's carriers** - upperworks, carbody, crawlers: when Hiring or Maintenance
  needs them; ERT-1's links carry them within the depth setting.
- **Kit for machines other than cranes**, and a removable auxiliary hoist as a kind: a later structure
  version, when needed.
- **A maintenance screen** for the structure and the depth setting: still by migration.
- **Bringing back a retired piece**: re-record it, or a route if needed.
- **A spreadsheet upload of kit**: not needed at PBL's size (about 28 crane models carry kit).
- **Plum listing kit**: binding such rows to pieces already recorded, and which source then wins, comes back
  to the owner (ADR-037 refinement, point 1).
- **Feet and US tons**: ratings are stored in metres and tonnes; an entry helper on the model form if
  converting Manitowoc's figures proves error-prone.

## Fixed Assets: what the Equipment Reference keeps for it (owner, 26 September 2026)

> Build it in a way that it can be part of the fixed asset module too, either with links or any other
> appropriate way, when we get to that, which won't be any time soon. Equipment as well as kits.

Not built: there is no Fixed Assets module yet. When it comes, it owns value, capitalisation, depreciation
and disposal, and links its own records to machines, parts and pieces of kit by their public id. What the
Equipment Reference already guarantees for that (ERT-2 design, section 17):

- a public id and `EQ-` reference that never change and are never reused, and no deletion;
- an event for every change of state, with its day and, on retirement, its reason;
- each "add kit" recorded as one lot;
- a counted set that shrinks only by a retirement saying how many left, when and why.

Fixed Assets will keep, in its own records: acquisition values and dates (Plum holds purchase and invoice
data, which ERT-1 did not take), which kit was capitalised with which crane, each part's share of a
machine's value (Annexure-11(A)), and whether a piece came with the machine or was bought separately (FRS
3.1 tags tools "OEM or General").

## Trailer beds and prime movers (owner, 26 September 2026)

> Also, think about how beds attached to trailers will be treated.

Decided in outline, not built - Transportation's (WRR-001, Q15; ERT-1, Q7). A bed is **its own machine**,
never a part or kit of the prime mover: it has its own registration and statutory documents, and Plum lists
beds as separate machines. Attaching one is a dated **coupling between two machines**:

- a new link kind, `COUPLED`, in the dated link table beside `FITTED`, with history kept;
- one bed per prime mover, and one prime mover per bed, at a time; retiring either ends the coupling;
- Plum's `BedNo` on each prime mover, kept in its source binding since ERT-1, lets the Plum import propose
  couplings for the Fleet Admin to confirm, as it proposes carrier pairs.

Modular hydraulic axles combined into one trailer, and their accessories (spacer beams, bolsters, stands,
beams - shared across makes and counted), are Transportation's too; the same records can carry them.

## Statutory requirements found with ERT-2 (26 September 2026)

Researched at the owner's request while designing ERT-2. The findings and their sources are in
`docs/agent/slices/ert-2-detachable-kit.md`, section 2, E and H. They are not legal advice. Each item names
the package it belongs to.

**Corrected by the research of 27 September 2026** (ELG-1 design, `docs/agent/slices/elg-1-machine-eligibility.md`,
section 2, E; research treated as more authoritative than the earlier record, per the owner's direction for
that package):

- **The central rules say nothing about lifting.** The OSH (Central) Rules 2026 hold no provisions for
  examining lifting machines, and the standards under the Code's section 18 have not been published. So at
  the central government's own sites - central public sector plants, railways and metros, major ports, oil
  fields and mines, with their contractors - no lifting rule applies since 8 May 2026 (docks keep the Dock
  Workers Regulations 1990). Gujarat's final rules hold none either, and the factories' 12-month interval was
  in the repealed section 29 itself. ERT-2's "the same substance survives in every regime found" was wrong.
- **A test every 5 years** is the BOCW and dock rules' only, not the factories'. BOCW also requires a test
  **after erection on a construction site** - 8A's, at mobilisation.
- **Slings every 6 months** is IS 12735:1994, clause 5.3, and customers' contracts - not the law, whose
  interval is 12 months.
- **Gujarat's Forms 37 and 38** are in the **draft** amendment of 13 December 2025; the notified rules end at
  Form 36. Nothing is built on them.
- **The CEV emission stage** is a type-approval fact about the engine, not a certificate that lapses: not
  needed for eligibility.
- **The 60, 30 and 15-day alerts** of `ELA-001` are PBL's policy; no law requires advance notice.

Under the owner's conservative principle (27 September 2026) the stricter reading is built: PBL's own rule
where the law is silent - a thorough examination every 12 months and a load test every 5 years, blocking, for
cranes, man lifts, forklifts, hook blocks and tackle, and slings every 6 months (Q2).

**Built by ELG-1** (migration `20260908_0044`): the certificates of machines, fitted parts and pieces of kit;
the examination rules as dated data per jurisdiction (`IN` and each state and union territory); the road
papers, with fitness and permits only for a vehicle registered as transport; "not applicable" only where the
law is unclear; the `ELA-001` decision; Certificates due. What is still not built stays below, under its
package.

**The law is changing now.** The OSH Code 2020 came into force on 21 November 2025 and repealed the
Factories Act 1948, the BOCW Act 1996, the Dock Workers Act 1986 and the Mines Act 1952.

- The OSH (Central) Rules 2026 (8 May 2026) supersede the BOCW Central Rules 1998 and the Dock Workers
  Rules 1990 where the central government is the authority.
- Gujarat's OSH Rules 2025 are in force. Maharashtra has drafts only, so its old rules probably
  continue.

References elsewhere to Factories Act section 29, Form 10 or the BOCW rules are therefore historical
where a newer rule applies.

- **Eligibility foundation** (the machine half built as ELG-1; what it left is named):
  - **An examination register for cranes, kit and tackle** - built by ELG-1 as the thorough examination and
    load test certificates of each crane, hook block and piece of tackle, with the piece's own number or its
    stencilled `EQ-` reference as its mark, the competent person in "issued by", the certificate's number,
    the next due date worked out from the rule, and nothing ever deleted. Chains monthly, wire rope every 3
    months and pre-use checks are checks by a responsible person, not certificates: log sheets (8C) and
    Maintenance. A test after repair or alteration waits for Maintenance; until then the Fleet Admin records
    the new test:
    - each item's identification mark and safe working load;
    - tests before first use, after repair or alteration and every 5 years;
    - a thorough examination every 12 months, chains monthly, and wire rope every 3 months;
    - the competent person and their recognition by the state;
    - the form and certificate number, and the next due date;
    - records kept at least 5 years.

    **The rules - intervals, forms, who may examine - must be data for each jurisdiction** (central, each
    state, ports, mines), because they are changing now.
  - **A crane's road-vehicle documents:** registration, insurance, pollution-under-control certificate
    and road tax. A fitness certificate and a permit only if the crane is registered as a transport
    vehicle - built by ELG-1, the transport question read from the registration certificate. The CEV
    emission stage is not needed (above).
  - **Operators** (the people half, with 8B): aged at least 18, trained for the appliance, medically examined (and annually from 40
    under the OSH Central Rules); their driving-licence class, which is unsettled for cranes; a
    signaller where the regime asks for one.
  - **The automatic safe load indicator** on cranes whose safe load varies with radius, and its weekly
    test (IS 13367-1) - a check, not a certificate: log sheets (8C) and Maintenance.
  - **Reminders and escalation** for certificates running out, and running out before or during a job -
    ELG-2, after 8A's core (`FUTURE_SLICES.md`).
- **8A (mobilisation):**
  - **A delivery challan for every trip, going and returning** (CGST rule 55), and an e-way bill for
    each consignment over ₹50,000. They need each item's description, HSN code, quantity and value.
  - **Permission for over-size or over-weight loads** (MoRTH on national highways, states on their own
    roads), recording each load's size and weight and the load per axle.
  - **Mats and timber**, which are site or job equipment.
- **Transportation:** the trucks and trailers that carry kit are goods vehicles, with their own permits,
  fitness certificates and axle limits.
- **Finance and PBL's tax adviser:**
  - which value to declare on a challan (no circular exists; practice is book value);
  - whether a crane driven on the road needs an e-way bill;
  - the HSN codes for hook blocks, shackles and counterweight;
  - whether keeping cranes at another state's sites, or moving them to a branch registered in another
    state, has GST consequences (Maharashtra advance ruling, Sanghvi Movers, 2018).
- **Inventory integration:**
  - store-held slings and shackles are identified and examined one by one, like the cranes' own
    tackle;
  - replacement wire rope to IS 2266 must carry the ISI mark (Quality Control Order 2024, S.O.
    2581(E)), since the BIS Act forbids hiring or storing notified goods without it.
- **At customer sites:** customers' own standards apply on top - NTPC's material-handling standard,
  OISD-GDN-192 and the other OISD hoisting standards, the Central Electricity Authority's line
  clearances. They reach PBL through contracts, and their texts were not read.

## Certificate reminders: what ELG-2 leaves out (1 October 2026)

ELG-2 (`docs/agent/slices/elg-2-certificate-reminders.md`) reminds about certificates running out, on screen, with
configurable schedules and escalation paths. Left out:

- **A note with "seen" - a deferred design, needing PBL's confirmation before it is taken up** (owner, 1 October
  2026, answering ELG-2's Q20: "Put note as a deferred design requiring PBL confirmation before taking up"). The
  design as put: when someone marks a reminder as seen, they may add an optional one-line note for the others it
  has reached - for example "Renewal applied for at the RTO, expected on 10 October" - shown to everyone the
  reminder has reached. Until PBL confirms it, the Alerts page shows only who has seen each reminder, and when.
  Engineering note for whoever takes it up: ELG-1 withholds free text that may repeat a certificate number - a
  withdrawal reason, a mark's reason - from those without `EQUIPMENT_IDENTITY_READ`; a note shown to Operations and
  Management would need PBL to accept that it is not withheld, or a rule for what it may contain.
- **Email, SMS and messaging.** The screen is the only channel. Each step of a path already names its channels, which
  today can only be `SCREEN`; when the notification service (`NTF-001`) is built with a provider, Admin adds a channel
  to a step and a job sends each reminder day to that step's audience once.
- **A job raising reminders**, and the events `EligibilityExpiring`, `EligibilityRecheckScheduled`,
  `EligibilityLapsed` and `EligibilityRestored`: the job runner (ADR-019). Until then the reminders are worked out
  each time they are read, and a read records nothing.
- **Reaching people by position, region or site** ("the Operations head for the site's region"): `ORA-001`, once
  positions are live. Paths name roles now, as data.
- **The people half's reminders** - crew licences and operators' certificates: 8B, reusing these reminders with
  their own kinds.
- **Reminding ahead of a rule that starts on a later day**, for a machine not on a job. A machine on a job is
  reminded already: its check takes the rule in effect when the job starts.
- **Snoozing a reminder, or giving it to one person to deal with**, and **reminders on the Dashboard**: later, if the
  testers ask.
- **The platform's other reminders** (contract expiry, offer review, credit profile review - `NTF-001`'s list): their
  own modules. The Alerts page can gather them; its count then adds them up.
- **Stopping the reminders of a closed Work Order's allocations**: when closing a Work Order is built.
- **The count in the menu** is worked out with the whole list, read at most every five minutes. Measured at the
  size of Plum's report (the acceptance record); if a real fleet makes it slow, the reminders would be stored by a
  daily job instead - a different design, back to the owner.

## Currencies other than INR: what TB1-600 leaves out (4 October 2026)

The owner's decision of 4 October 2026 (Q-08's refinement; the Commercial Offer contract's TB1-600 section) lets an
offer or an amendment be recorded in USD, GBP or EUR. Only entry and reporting were built. Still to decide or build,
when work in another currency is real (the owner expects none soon):

- **Conversion.** Nothing converts and no exchange rate is held. A total across currencies, in any report or check,
  needs a rate source, a date rule and an owner.
- **Credit exposure.** `CEX-001` and the Account credit profile are in INR. An offer in another currency cannot yet be
  counted against approved credit; the exposure gate, when built, must refuse or convert it, never add it as rupees.
- **Work Order lines and billing terms.** Handoff copies each offer line's currency onto the Work Order line, while
  billing terms are INR by construction (`WORK_ORDER_LINE_BILLING_TERM_CURRENCY`). A Work Order from an offer in
  another currency would carry lines in one currency and terms in another; billing (`WBT-001`, `LBE-001`) must settle
  this before it reads either.
- **One offer, one currency.** An offer line may still be in a different currency from its offer, as before; whether
  they must match is not decided. Since 12 October 2026 the quotation totals each currency separately instead of
  adding them (the Commercial Offer contract, "Quotation totals per currency"); the offer's own `offer_value`, which
  reports total, is still one figure in the offer's currency, typed by hand.
- **The database.** The columns still take any three characters; only the application checks the list. A `CHECK`
  constraint, or a lookup table if the list starts to change often (`CODING_STANDARDS.md` section 5), can come with a
  later migration. Rows saved before the fix keep their code until next edited.

## Log sheet, billing and invoice support

Deferred work:

- Log sheet templates and customer sign-off.
- Usage, extra hours, extra KM, breakdowns and deductions.
- Fuel variance and reconciliation.
- Billing calculation from WO/log sheet terms.
- Draft invoice support document checklist.
- Invoice/AR integration and collection follow-up.

## Documents and integrations

Deferred work:

- SharePoint or document repository integration.
- Document versioning and locking for submitted/approved documents.
- Probe42, D&B, Tender Tiger, Projects Today or similar integrations where feasible.
- WhatsApp/email/communication ingestion.
- OpenAPI export and integration monitoring.

## Reverse auctions through customer portals (raised by the owner, 13 October 2026)

**The need.** Some customers buy through reverse auctions on their procurement portals: suppliers lower their prices
in real time and the lowest acceptable bid wins. PBL wants to take part through this system rather than by hand on each
portal. There may be many such customers.

**What PBL described:**

1. **Pull the enquiries.** Read reverse-auction enquiries from each customer's portal through its interface (API), at a
   frequency PBL sets. Pull only the header fields needed to decide whether to look closer.
2. **Choose, then pull the detail.** PBL picks from the header list the enquiries it wants to examine; the system then
   pulls their detail - items, quantities, dates, terms.
3. **Quote the usual way.** If PBL decides to quote, the ordinary Commercial Offer process follows: Opportunity, offer
   lines, market rates and the basis rate, approvals.
4. **Send the rates.** Once the rates are decided, the system sends them to the auction portal through the same
   interface.
5. **A target or maximum price per line.** An auction sets a ceiling price for each item, and a bid must be equal to or
   lower than it. An offer line has no such field today. It is needed, and a line's rate above it must be refused.

**How reverse auctions usually work.** From public Indian procurement rules and auction guidelines (General Financial
Rules 2017, rule 149; GeM; public-sector auction rules); each portal's own bid document governs:

- often a technical qualification first, then the auction among the bidders who qualified;
- the buyer sets a start or ceiling price - its estimate, or the lowest sealed bid - and a minimum step (decrement);
  each new bid must undercut the standing lowest bid ("L1") by the step or a multiple of it, sometimes with a cap on
  how far one bid may go;
- bidders see their rank, and sometimes the lowest price, but not who the other bidders are;
- a bid in the last minutes that becomes the lowest extends the auction automatically;
- the lowest is judged item by item, by group, or on the total value; on the total, line prices are reduced in
  proportion afterwards;
- the buyer may negotiate with the lowest bidder, and is not obliged to award.

**To settle before it is built:**

- **Which customers and portals**, and whether each offers suppliers an interface to read auctions and submit bids.
  Many portals let suppliers bid only through their web pages; where there is no interface, the fallback is the offer
  export below and entry by hand.
- **Signing in to each portal**: PBL's credentials, kept in a secret store; each portal's rules on automated access.
- **How often to pull, and which fields**; matching each portal's items and units to offer lines.
- **The lowest price PBL will go to.** Bidding is live and fast, so approvals cannot wait for each bid. A floor price per
  line, approved in advance (markup approval applies to the floor), below which no bid goes without a new approval;
  and who may place bids during an auction.
- **What is recorded during an auction** - each round's rate per line, the final rate, the rank - and what happens when
  it closes: award, loss, or negotiation with the lowest bidder.

**Until then** (PBL, 13 October 2026): an export of an offer in JSON or XML, or a similar format, serves customer
templates, portal uploads and entering auction rates by hand. It is part of the vendor package
(`docs/vendor/03_REMAINING_AND_DEFERRED_SCOPE.md`, group A).

## Messages about a record, and a to-do list (owner, 8 October 2026)

A user looking at any record - an offer, a Work Order, a document - should be able to send a message about it to a
person, for example the salesperson responsible, without leaving the page. The message lands in that person's to-do
list and they are notified.

What is wanted:

- A **Message** button on every page, always in the same place, that captures what the user is looking at: the kind of
  record, its reference and a link back to it. The user picks the person and writes the message.
- The message becomes a task in the recipient's to-do list, with the link to the record, and the recipient is
  notified.

Suggested when it is built:

- The person defaults to the record's responsible salesperson, where the record has one.
- A **My tasks** list: the recipient marks a task done, and the sender sees whether it is done.
- Notification through `NTF-001` (in the application first; email or SMS later, as `NTF-001` allows).
- Permissions stay with the record: the link opens only for someone who may already read the record, and the message
  shows the record's reference, never its contents.
- Sending, reading and completing are business events.

What exists today: nothing like it. `NTF-001` is the delivery boundary only; Interactions (`INT-001`) are conversations
with customers; ELG-2's Alerts are certificate reminders about machines.

Open for the owner when it is built: who may message whom (anyone, or within a team or reporting line); whether a task
can carry a due date, and what happens when it passes (a reminder, escalation to the manager); whether the recipient
can reply in the thread or only mark it done; and that these internal messages stay separate from the customer
conversation log.

## UI/UX and UAT hardening

Recorded 22 September 2026, from the owner's screen check of Slice 7D Part 3:

- ~~**Date fields elsewhere accept a five- or six-digit year.**~~ Done 28 September 2026: every date and
  date-and-time box is the shared `frontend/src/components/DateInput.tsx`, and a test fails when a page adds a
  plain one. The record as it stood: Chrome lets a date input's year run on
  unless the input has a maximum. The Work Order page's eight date fields now carry
  `max="9999-12-31"` (`DATE_INPUT_MAX`); fourteen date fields in seven other files do not -
  Commercial Offer detail, new Commercial Offer, new related offer, new Opportunity, Opportunity
  detail, new Work Order Amendment and new Work Order - nor do the nine date-and-time fields. The
  server remains the control, so nothing wrong is saved without a refusal; this is the browser
  offering a date nobody means. A shared date-input component is the natural fix.
- **Backspace should walk back through a date field** (owner's screen check, 23 September 2026). With
  the cursor in the year, pressing Backspace should clear that segment and carry on into the month and
  then the day, ending at the start of the field - the mirror of typing forward, which moves on from
  day to month to year by itself. The browser's own date control does not do this: Backspace clears
  only the segment the cursor is in and stops there, so correcting a date means clicking back a
  segment at a time. It needs the key handled in a shared date-input component - the same component
  the four-digit-year cap above wants, so do the two together rather than patching field by field.
  Still open: the shared component now exists (`DateInput`), but a native date box does not let a page move
  the cursor between its segments, so this needs a date box of the application's own - its own package.
- ~~**The application does not show who is signed in.**~~ Done in Slice 7D Part 3 at the owner's
  word: the sidebar names the signed-in user and their roles, asked of `/api/auth/me` whenever the
  session changes.

Deferred work:

- Consistent Back/return navigation.
- Origin-aware linked-record navigation.
- Inline validation and field-level highlighting.
- Consistent success/error message placement.
- Reduced scroll burden on long pages.
- Browser-session visited-link consistency.
- ~~Repeatable demo seed data.~~ Built: the TE-1 smoke-data harness and Slice 6P's `vendor-demo-bundle`
  (reconciled 7 October 2026, TB-1 TB1-904).
- ~~Playwright/browser regression tests.~~ Built: TE-1's `e2e/` suite, run in CI since TE-2CI (reconciled
  7 October 2026, TB-1 TB1-904).
