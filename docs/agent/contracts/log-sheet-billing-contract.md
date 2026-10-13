# Log Sheet to Billing Engine Contract

## Contract ID and status

`LBE-001` - `APPROVED` - 12 August 2026.

## Boundary

Log Sheet certifies operational evidence. Billing Engine interprets approved evidence under Work
Order commercial terms. Billing must not alter Log Sheets, and Log Sheet must not calculate
commercial charges.

## Minimum approved evidence

```text
log_sheet_public_id and version
Work Order / line / equipment and/or crew/service assignment public IDs and versions
site and service date/period
approved working quantity/hours
approved normal/overtime/standby quantities
approved breakdown/downtime quantities
opening/closing meter readings where applicable
fuel evidence where contractually required
customer certification status/reference
approval status, timestamp and approver identity
evidence/document references
correction/supersession reference
unit/timezone conventions
```

## Consumption rules

- Only an approved, non-superseded version is billable unless an authorized exception contract
  explicitly permits otherwise.
- Billing records the exact Log Sheet and Work Order term versions used.
- A correction after calculation creates a recalculation/adjustment path; it does not mutate a
  previously approved billing result silently.
- Unsigned/unverified evidence remains non-billable unless an authorized traceable exception is
  approved under current governance.

## Events

Logical facts include `LogSheetApproved`, `LogSheetSuperseded` and `BillingRecalculationRequired`.

## Settled baseline

- Evidence records the units required by the Work Order billing basis: Hour, Shift, Day or Month,
  plus HMR/engine hours, odometer/KM, fuel and other readings where applicable.
- Where the contract requires customer sign-off, the verified customer-signed Log Sheet is the
  primary billing evidence. GPS/IoT/HMR data may support reconciliation but does not silently
  replace required signed evidence.
- Unsigned or unverified evidence is non-billable unless the configured authorized Billing
  approver records a reasoned, traceable exception.
- A correction creates a new Log Sheet/evidence version and triggers recalculation. It never
  changes an approved prior version or closed billing result silently; later correction uses an
  adjustment path.
- Billing calculations follow `WBT-001`; units, minimums and rounding are not invented in the Log
  Sheet module.
