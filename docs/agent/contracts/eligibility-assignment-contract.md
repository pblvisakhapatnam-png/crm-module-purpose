# Eligibility to Resource Assignment Contract

## Contract ID and status

`ELA-001` - `APPROVED` - 12 August 2026.

## Boundary

Compliance/Eligibility owns the decision about whether a resource/crew combination satisfies a
requirement. Assignment owns the commitment and must preserve the exact decision/rule versions
used.

## Evaluation input

```text
requirement public ID/version
resource public ID/type
crew/operator public references
site and planned period
required licence/skill/certification references
correlation metadata
```

## Evaluation result

```text
eligibility decision public ID/version
overall decision: ELIGIBLE / BLOCKED / OVERRIDE_REQUIRED / WARNING
rule results with rule/evidence versions
expired/missing statutory licence hard-blocks
  non-statutory mismatch override requirement where policy permits
model-specific experience warning/override result
valid-until / evaluated-at
approved override reference and conditions where applicable
```

Assignment cannot convert `BLOCKED` into an allow decision. An override must come from the
configured approval policy and remain linked to the assignment.

Risk Approver identity/scope is resolved through `ORA-001`; the eligibility or assignment client
cannot assert it.

## Settled baseline and configurable values

- A missing, expired or invalid statutory/legal licence or mandatory statutory document always
  blocks assignment and cannot be overridden by Operations.
- Policy may allow an authorized Risk Approver to accept named non-statutory skill, experience or
  model-competency gaps. Allowed categories, approver and expiry are configuration; no broad
  override exists by default.
- Eligibility is checked when assigning or replacing a resource and again before the planned
  start when relevant evidence, master status or validity has changed or expired.
- External-source unavailability does not convert unknown evidence into valid evidence. A
  still-valid previously verified result may be used only within its recorded validity/policy;
  otherwise the assignment remains blocked or requires the permitted non-statutory exception.

## Continuous validity monitoring

Eligibility is not a one-time pre-start check. When an approved assignment extends beyond an
evidence/rule validity date:

1. Eligibility records the earliest applicable `valid_until` and submits a versioned recheck job
   through the Background Jobs capability.
2. Notifications sends the accepted statutory-document alerts at 60, 30 and 15 days before expiry
   to the employee and HR manager, plus the operational owner where assignment is affected.
3. A master/evidence status-change event or the scheduled expiry job re-evaluates every affected
   current/future assignment.
4. If a mandatory statutory/legal requirement lapses, Eligibility emits `EligibilityLapsed` with
   assignment/resource/evidence/rule references and effective time.
5. Resource Assignment consumes that event idempotently, marks the assignment's compliance state
   `COMPLIANCE_BLOCKED`, prevents further operational Log Sheets/extension under that assignment,
   and requires Operations to release or replace the affected resource/crew. Existing history and
   evidence remain unchanged.
6. `EligibilityRestored` may clear the compliance block only after new authoritative evidence is
   verified and a fresh eligible decision is linked. It does not backdate validity over the gap.

The job runner performs an overdue-validity recovery scan after downtime so a missed timer cannot
leave an expired assignment apparently valid. Statutory lapse has no override. Non-statutory
expiry follows its configured warning/override policy.

## Events

Logical facts include `EligibilityEvaluated`, `EligibilityRecheckScheduled`,
`EligibilityExpiring`, `EligibilityLapsed` and `EligibilityRestored`.
