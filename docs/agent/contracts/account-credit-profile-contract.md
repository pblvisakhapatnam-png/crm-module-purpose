# Account Credit Profile Contract

## Contract ID and status

`ACP-001` - `APPROVED` - 12 August 2026. Amended 13 August 2026 by explicit PBL decision:
assessment authorization is expressed through the configurable `CREDIT_ASSESSOR` authority
resolved via `ORA-001`, not through a fixed `SALES_MANAGER` role check. Status remains `APPROVED`;
no other semantics changed.

## Ownership

The CRM Account Master's Account Credit Profile component is authoritative at legal-entity/PAN
level for approved Credit Amount and Credit Days. It is an independently implementable component
inside the Account Master boundary, not a separate customer/account master. It remains logically
separate from identity validation and calculated exposure.

```text
CREDIT_ASSESSOR authority        performs the credit assessment
                                 (initial/default mapping: SALES_MANAGER)
Authorized Sales roles           prepare/propose changes against the Account
                                 (SALES_USER, SALES_MANAGER, and ADMIN where the Account
                                 contract permits it); a proposal is not an assessment
CREDIT_APPROVER authority        approves under policy; currently the configured
                                 Department Head or Managing Director
Finance/Accounts                 consumes approved profile and exposure information
```

Authorization for the assessment is the current, active `CREDIT_ASSESSOR` authority assignment for
the relevant organizational/data scope, resolved by the backend through `ORA-001`. `SALES_MANAGER`
is the initial/default mapping, which preserves the agreed current operating arrangement and
migration compatibility. Once ORA authority assignments are active, authorized administrators may
assign, suspend, revoke or reassign `CREDIT_ASSESSOR` to an eligible employee or position without
a code change; the application role alone must not remain the permanent authorization rule.

Business authority is not implied by administrative access. Maintaining authority assignments and
exercising `CREDIT_ASSESSOR` are separate capabilities, and `ADMIN` is not an implicit assessor.

## Minimum approved profile

```text
credit_profile_public_id
Account public ID
legal-entity/PAN reference
approved_credit_amount
currency
approved_credit_days
effective_from / effective_to (nullable)
status
assessment reference, authenticated assessor identity and the CREDIT_ASSESSOR
  authority assignment/version relied on
approval decision public ID/reference
authenticated approver identity and authority snapshot
approval policy and authority-assignment versions
approval timestamp and conditions
review date (nullable)
version
created/updated audit metadata
```

Passwords, tokens and reusable credentials are never approval evidence.

## Interfaces and approval integrity

- Record/update the credit assessment: an authenticated user holding a current, active
  `CREDIT_ASSESSOR` assignment for the relevant scope, resolved through `ORA-001`. The backend
  checks the authority assignment, not a fixed role name.
- Propose a credit-profile change: authorized Sales role; a proposal is neither an assessment nor
  an approved limit.
- Decide the proposal: the authenticated approver acts through `APR-001`; backend authority is
  resolved through `ORA-001` for the applicable Department Head/Managing Director assignment.
- Activate approved values: a narrow Account Credit Profile application service consumes the
  valid approval decision and writes the effective profile. Sales cannot assert or transcribe an
  approver identity to activate its own proposal.
- Query effective approved profile: authorized consuming modules.
- Supersede/suspend profile: policy-authorized command with event and reason.

The proposal actor, decision actor and system/application actor that activates the profile are
recorded separately. An out-of-band approval cannot be represented as an authenticated in-system
decision. If PBL later permits imported historical/manual approval evidence, that requires an
explicit import mode, source document, authenticated transcriber, separately authorized verifier
and a visible `IMPORTED_OUT_OF_BAND` classification; it is not the production default here.

## Events

Logical facts include `CreditAssessmentRecorded`, `CreditProfileApproved`,
`CreditProfileSuperseded` and `CreditProfileSuspended`.

## Boundaries

- This contract does not calculate Potential/Firm Exposure.
- It does not decide a Commercial Offer or Work Order action.
- It relies on `APR-001`/`ORA-001` for assessor and approver authority resolution, authentication
  and any configured maker/checker independence; it does not let the proposing Sales user
  self-certify the assessment or the approval, and it does not maintain its own authority table.

## Settled baseline and configurable values

- Current credit profiles use INR. Multi-currency is deferred until overseas customer business
  enters scope.
- An approval becomes effective at its recorded effective date, which normally cannot precede
  the approval. A genuine authorized correction may record an earlier effective date with reason
  and audit; it must not silently rewrite the earlier profile.
- The supporting assessment and senior-management approval reference are mandatory. Additional
  document requirements and review reminders are policy configuration for the implementation
  slice.
- Suspension or urgent reduction uses the configured approval authority. The current eligible
  authority is the applicable Department Head or Managing Director; named people and thresholds
  are not hard-coded.
