# Accepted Offer To Work Order Fixture Examples

## Purpose

This directory contains safe, non-confidential example payloads for the frozen Accepted Commercial Offer -> Work Order shell handoff.

These files are contract examples only. They are not seed data, not runtime fixtures and not database schema.

## Files

```text
accepted-commercial-offer-handoff-example.json
work-order-shell-output-example.json
partial-award-selected-lines-example.json
negative-missing-account-traceability-example.json
negative-invalid-line-selection-example.json
```

## Safety

All values are fake demo values.

Do not replace placeholders with real customer data, real PAN, real GSTN, real addresses, real document links, real personal data, secrets, passwords or tokens.

PAN/GSTN values use:

```text
PLACEHOLDER_NOT_REAL
```

Document links use:

```text
https://example.invalid/...
```

## Contract Reference

These examples follow:

```text
docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
docs/planning/ACCEPTED_OFFER_TO_WORK_ORDER_PAYLOAD_SPEC.md
```

Production MVP Work Order shell examples use:

```text
HANDOFF_RECEIVED
```

The current prototype maps shell creation to:

```text
HANDOFF_CREATED
```

Do not infer that the shell is released, posted, executable, assigned, billable or invoiced.
