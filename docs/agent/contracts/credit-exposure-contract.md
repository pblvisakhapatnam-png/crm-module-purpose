# Credit Exposure Decision Contract

## Contract ID and status

`CEX-001` - `APPROVED` - 12 August 2026.

## Purpose and ownership

Credit Exposure owns the reproducible calculation of approved-credit utilization and the policy
decision returned to Commercial Offer or Work Order. It does not own approved Credit Amount/Days,
offers, Work Orders or the receivables ledger.

## Evaluation request

```text
evaluation_public_id / idempotency key
Account public ID and PAN/legal-entity reference
source record type/public ID/version
commitment type (offer submission, tender bid, Work Order release, other approved type)
proposed amount/currency and payment days
evaluation timestamp
correlation and actor metadata
```

## Evaluation result

```text
evaluation_public_id
credit-profile version/reference
approved amount/days used
Potential Exposure components/reference
Firm Exposure components/reference
Finance/receivables input reference and as-of time where available
proposed incremental exposure
available amount before/after
decision code and policy version
approval-required flag/reference
calculation breakdown
staleness/incomplete-data indicators
overdue commercial-commitment review references/hold indicator
evaluated_at
```

The consuming module enforces the returned decision according to its approved action contract.
It must preserve the evaluation/approval reference through later Work Order readiness.

## Failure behavior

Missing/stale inputs are not silently treated as zero. The result must distinguish unavailable,
incomplete and policy-rejected conditions. Retry behavior depends on the missing source.

## Exposure state machine

Exposure is calculated by value allocation, not by treating an entire offer and every derived
Work Order as separate full-value commitments.

| Commercial/Work Order state | Potential Exposure | Firm Exposure |
| --- | --- | --- |
| Draft offer/revision | Zero | Zero |
| Latest submitted revision of an active offer/tender series | Submitted live amount not already transferred | Zero unless a related Work Order allocation already exists |
| Submitted offer/tender with overdue commitment review and no recorded outcome | Retain the untransferred amount conservatively; do not silently remove it | No change; return `REVIEW_REQUIRED`/hold for new exposure decisions on the Account until Sales resolves the overdue review |
| Superseded submitted revision | Zero | No change to existing Work Order allocations |
| Accepted/awarded, before Work Order shell creation | Awarded/live amount awaiting handoff; if the awarded amount is not yet quantified, retain the full latest submitted amount conservatively | Zero |
| Work Order shell created from selected offer lines | Only the still-live, not-handed-off remainder | Exact selected-line amount allocated to the Work Order shell |
| Additional shell for a later partial handoff | Reduce Potential by the additional selected-line allocation | Add that allocation; never add the full offer again |
| Work Order released/executing | No change for the same allocation | The allocation remains Firm; release does not transfer it a second time |
| Submitted Change/Supplementary Offer or unapplied amendment | Live proposed increase is Potential; a decrease does not reduce Firm until effective | Existing effective Work Order amount remains Firm |
| Approved change applied to effective Work Order | Remove the applied change amount from Potential | Increase/decrease Firm by the effective Work Order change |
| Offer/line Withdrawn, Rejected/Lost, Closed, expired or explicitly not awarded | Remove the affected untransferred amount from Potential | No change to valid Work Order allocations |
| Work Order allocation cancelled/reversed | Return the amount to Potential only if the commercial commitment remains live and awaits a replacement handoff; otherwise remove it | Remove/reverse the cancelled allocation with an audit reference |
| Work Order billed under target formula | No change | Unbilled component reduces while outstanding receivable increases; payment reduces the receivable component |

`ACCEPTED` is therefore not a blanket exclusion: an accepted amount remains Potential only until
the corresponding amount is handed off. The transfer trigger is successful creation of a Work
Order shell from specific selected offer lines, recorded by the existing
`CommercialOfferConvertedToWorkOrder`/equivalent event. Operational release is a later control and
does not create a second exposure transfer.

Every transfer records offer series/revision/line, Work Order/line, allocated amount, transfer or
reversal event, and calculation version. The sum of untransferred live allocation plus Work Order
allocation must reconcile to the applicable live/awarded commercial amount.

## Commitment liveness and offers without an expiry date

Potential Exposure must not accumulate silently because a submitted offer/tender has no
`valid_until` date or customer response.

- At controlled submission, Commercial Offer must have either an explicit `valid_until` date or
  a system-calculated `next_exposure_review_due_at`. When `valid_until` is absent, the review date
  is mandatory and is calculated from a configured maximum review interval for that offer/tender
  category; the user does not bypass it by leaving a field blank.
- For submitted/unawarded value with an explicit `valid_until`, the expiry job removes the
  untransferred amount from Potential at the end of that business date unless an authorized
  extension/resubmission is already effective. An accepted/awarded commitment is not cancelled
  merely because the earlier offer-validity date passes; its award/handoff state governs it.
- The originating Commercial Offer module owns this review state and customer/outcome action.
  Credit Exposure consumes the current status; it does not edit the offer.
- Background Jobs schedules explicit expiry and reminders before/on a no-expiry review date.
  Notifications sends review reminders to the responsible Sales owner and escalates an overdue
  item to the Sales Manager under policy.
- On the due date, Sales must either confirm that the commitment remains live and set the next
  review date, or record the applicable expired, withdrawn, rejected/lost, closed or not-awarded
  outcome. Confirmation records actor, time, reason/evidence and the next due date.
- An overdue unresolved amount remains Potential to avoid understating exposure. The exposure
  result is `REVIEW_REQUIRED` and holds new exposure-dependent submission/exception decisions for
  that Account until the review is resolved. It is never silently treated as zero.
- Recording a final/not-awarded outcome removes only the affected untransferred amount. Confirming
  it live retains that amount and starts the next review period.
- Existing submitted offers are migrated/backfilled with a review date derived from their latest
  submission date and the approved interval. Already-overdue records enter the review queue; the
  migration does not silently remove their exposure.

Logical facts include `CommercialCommitmentReviewScheduled`, `CommercialCommitmentReviewDue`,
`CommercialCommitmentConfirmedLive` and the existing recorded outcome/closure fact. Jobs and
events are idempotent for the offer/revision/review occurrence.

## Firm Exposure basis

The temporary Firm basis is allocated value of active Work Order shells/Work Orders. It must use
the allocation state above and must not sum an offer again. The target basis is unbilled effective
Work Order value plus outstanding receivables from Plum.

## Worked example: partial award and amendment

```text
1. Latest submitted offer = INR 100.
   Potential = 100; Firm = 0.

2. Customer awards INR 60, but the accepted outcome has not yet recorded the unawarded balance.
   Conservative state before handoff: Potential = 100; Firm = 0.

3. A Work Order shell is created for selected lines worth INR 60.
   Transfer 60 once: Potential = 40; Firm = 60.

4. Sales records that the remaining INR 40 was not awarded.
   Potential = 0; Firm = 60.

5. A submitted Change Offer proposes an additional INR 15.
   Potential = 15; Firm = 60.

6. The change is approved and applied to a new effective Work Order version.
   Transfer 15 once: Potential = 0; Firm = 75.

7. Under the target formula, INR 30 is billed but unpaid.
   Unbilled Work Order = 45; outstanding receivable = 30; Firm remains 75.

8. Customer pays INR 10.
   Unbilled Work Order = 45; outstanding receivable = 20; Firm = 65.
```

If step 2 records the exact partial award immediately, the unawarded INR 40 leaves Potential at
that point; step 3 then changes Potential 60 -> 0 and Firm 0 -> 60. Both paths reconcile to the
same result without understatement or double counting.

## Settled decision rules

- Current calculations use INR, so no currency conversion is required in CRM/Hiring.
- Within-limit actions proceed. Over-limit or exhausted-credit Commercial Offers are held until
  an authorized exception is approved. The decision and approval reference remain visible to
  Work Order handoff/release.
- Missing, stale or unavailable inputs are identified explicitly and are not treated as zero.
- The maximum no-expiry review interval, reminder offsets and escalation time are configurable
  operating parameters that must be set before the production exposure gate is enabled.

System-of-Record Matrix decision D-02 now concerns only when the available Plum and Work Order
data are reliable enough to activate the target Firm Exposure formula. Until then, the temporary
basis is used and labelled with its basis and as-of time. A permissible data-age threshold is a
configurable Finance integration parameter to set before the live receivables gate is enabled.
