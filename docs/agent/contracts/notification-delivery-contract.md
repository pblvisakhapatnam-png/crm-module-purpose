# Notification Delivery Contract

## Contract ID and status

`NTF-001` - `APPROVED` - 12 August 2026.

## Boundary

The originating business module owns why a notification is required, its business record,
audience rule and due time. Notifications owns template rendering, channel delivery, retry,
delivery status and safe failure visibility. A notification is not approval, workflow state or
proof that the recipient acted.

## Notification request

```text
notification_request_public_id / idempotency key
notification_type and template version
source module / record type / public ID / version
audience authority, role or resolved recipient references
scheduled_at and business timezone
safe template data or authoritative data references
priority / escalation reference where applicable
correlation and causation references
```

Sensitive fields and evidence files are linked through authorized application routes; they are
not copied into email/SMS/push content unless the owning policy explicitly permits it.

## Delivery result

```text
channel and provider reference
recipient reference (protected as required)
status: SCHEDULED / SENT / DELIVERED / FAILED / CANCELLED
attempt count and last attempt time
safe failure code / retryable flag
delivered_at where known
```

Repeated jobs or events do not send the same notification twice for the same type, source version,
recipient and scheduled occurrence.

## Initial required notification triggers

- Employee/driver/operator statutory-document expiry alerts at 60, 30 and 15 days to the employee
  and HR manager, as required by the accepted FRS.
- Contract/Work Order expiry alert at 30 days to Sales and Fleet/Operations.
- Identity-validation exception assignment/escalation.
- Credit-profile review reminders when configured.
- Submitted Commercial Offer/tender commitment-review reminders and Sales Manager escalation when
  an offer without a customer outcome reaches its exposure review date.
- Authority suspension/revocation and pending-approval reassignment alerts to the affected user,
  responsible manager and authority administrator as permitted by HR/security policy.
- Background job/integration failures requiring an operational owner.

## Delivery failure

A failed notification remains visible and retryable. It does not silently change or relax the
underlying deadline, statutory block, approval or business state. Critical alerts have an owned
escalation/fallback channel defined by the implementing slice.

## Events

Technical delivery events may include `NotificationSent` and `NotificationDeliveryFailed`.
Business modules continue to own the event that caused the notification.
