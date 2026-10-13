# Handoff Fixture Validation Checklist

## Purpose

Use this checklist whenever the Accepted Commercial Offer -> Work Order shell fixture pack is created or changed.

The fixtures are contract examples only. They are not runtime fixtures and are not seed data.

## JSON Validity Check

```text
[ ] Every `.json` file parses successfully.
[ ] JSON is pretty formatted and readable.
[ ] No comments are present inside JSON.
```

Recommended command:

```powershell
python -m json.tool docs/agent/fixtures/accepted-offer-work-order/accepted-commercial-offer-handoff-example.json
```

Run the same check for each JSON fixture.

## Identity Continuity Check

```text
[ ] Commercial Offer public ID is stable across handoff and output examples.
[ ] Commercial Offer number/reference is stable.
[ ] Opportunity public ID is stable.
[ ] Account public ID is present in valid examples.
[ ] Account display name is safe demo text.
[ ] Correlation ID appears where expected.
```

## Account Traceability Check

```text
[ ] Valid handoff examples include `account_public_id`.
[ ] Negative missing-Account example has null/missing Account traceability.
[ ] Negative missing-Account example expects rejection.
[ ] Negative missing-Account example does not create a Work Order shell.
```

## Commercial Offer Line Identity Check

```text
[ ] Every valid handoff line has `commercial_offer_line_public_id`.
[ ] Line sequence is stable.
[ ] Line status is explicit.
[ ] Partial-award fixture identifies selected and excluded lines.
[ ] Excluded lines do not appear in Work Order output lines.
```

## Work Order Source-Line Identity Check

```text
[ ] Every Work Order line includes source Commercial Offer line public ID.
[ ] Source line IDs match selected/awarded Commercial Offer lines.
[ ] No Work Order line is created from invalid or cancelled source lines.
```

## Status Check

```text
[ ] Production fixture Work Order shell status is HANDOFF_RECEIVED.
[ ] Fixture notes mention the current prototype maps to HANDOFF_CREATED.
[ ] No fixture implies release, posting, execution, assignment, billing or invoicing is complete.
[ ] PENDING_CUSTOMER_MASTER is not treated as the default initial shell status.
```

## Document Metadata Check

```text
[ ] Document references are metadata only.
[ ] No real document links are used.
[ ] No local app-server file path is used as production document storage.
[ ] Placeholder links use safe fake URLs such as `https://example.invalid/...`.
```

## Credit / Reference Timing Check

```text
[ ] Handoff carries the latest available Commercial Offer credit/exposure reference where applicable.
[ ] Fixture explains that this does not replace the future Work Order release credit/readiness gate.
[ ] No fixture claims full credit exposure calculation is implemented.
```

## Negative-Path Checks

```text
[ ] Missing Account traceability expects rejection.
[ ] Invalid selected line expects rejection.
[ ] No partial silent success is shown for invalid selected lines.
[ ] Negative examples do not create Work Order shells.
[ ] Negative examples do not create success business events.
```

## No Real Data / No Secrets Check

```text
[ ] No real customer/vendor/PBL confidential data.
[ ] No real PAN.
[ ] No real GSTN.
[ ] No real addresses.
[ ] No real personal names, phone numbers or emails.
[ ] No passwords.
[ ] No tokens.
[ ] No secrets.
```

## Contract Alignment Check

```text
[ ] Fixtures do not redefine Slice 6D.1.
[ ] Fixtures do not change frozen payload fields.
[ ] Fixtures preserve Account as UI term.
[ ] business_party appears only as internal/domain/database terminology if needed.
[ ] Backend authorization remains authoritative.
[ ] Frontend role-awareness remains UX only.
```
