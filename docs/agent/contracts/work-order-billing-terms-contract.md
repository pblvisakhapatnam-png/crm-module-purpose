# Work Order Billing Terms Contract

## Contract ID and status

`WBT-001` - `APPROVED` - 12 August 2026.

## Boundary

Work Order owns accepted contractual billing terms and their effective versions. Billing Engine
consumes those terms and does not infer commercial rules from UI text, Log Sheets or offer notes.

## Minimum term set

```text
Work Order and line public IDs/versions
term-set public ID/version/effective period
currency
billing UOM and quantity basis
normal rate and period basis
normal-hours/shift definition
overtime rate/rule
standby rate/rule
breakdown/downtime treatment
minimum guarantee and pro-rating rule
mobilisation/demobilisation terms
fuel treatment where applicable
taxable-value adjustment terms
approved exception/variation references
source Commercial Offer/line/term references
```

Only explicitly present, approved terms may be calculated. Missing required terms produce a
non-billable/incomplete result, not an invented default.

## Version behavior

Every billing result records the term-set version used. Work Order amendments create a new
effective version or approved adjustment path; they do not rewrite terms already used for a
closed period.

## Settled baseline and UAT requirement

- The supported billing bases are Hour, Shift, Day and Month.
- Hour-based billing uses actual working hours without OT or breakdown logic. Shift/day billing
  applies contractual hours, OT and breakdown treatment. Month billing supports OT Normal Hours
  and OT Engine Hours, including the contracted-hours gate and contract-specific pro-rating.
- Normal, OT, breakdown, second-shift, holiday, idle/customer-caused delay, mobilisation,
  demobilisation, minimum guarantee and fuel treatment are applied only when the approved Work
  Order terms define them. Missing terms are not guessed.
- Current terms and rates use INR.
- An approved amendment has an explicit effective date and creates a new term version. Closed or
  already-billed periods are not rewritten; an authorized retrospective change creates a visible
  adjustment.
- Accepted Commercial Offer header/line term references and the values used to create the Work
  Order are retained for history.

Exact decimal precision and rounding are engineering/Finance calculation settings. Before billing
goes live, Billing/Finance UAT must compare every implemented formula with the source Annexure-10
examples and representative real Work Orders because customer contracts can select different
methods and rates. This validates the implementation; it does not reopen the billing bases above.
