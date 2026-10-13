# Slice 2D - Lead Activities / Follow-ups Foundation

## Objective

Add a separate, repeatable Lead Activity / Follow-up record so that calls, emails, WhatsApp messages, meetings and notes are preserved as history instead of overwriting the current Lead details.

## Included

- `crm_lead_activity` table linked to `crm_lead`.
- `GET /api/leads/{public_id}/activities`.
- `POST /api/leads/{public_id}/activities`.
- Activity types: `CALL`, `EMAIL`, `WHATSAPP`, `MEETING`, `NOTE`, `OTHER`.
- Activity date/time, notes, outcome and next follow-up date/time.
- Lead detail page section for Activities / Follow-ups.
- Role-aware create action: Sales/Admin can record activities; Finance/Ops/Read-only can view.
- Business event: `LeadActivityRecorded`.

## Excluded

- Task assignment workflow.
- Reminder notifications.
- Calendar integration.
- WhatsApp/email ingestion.
- Activity edit/delete.
- Qualification decision workflow.
- Lead conversion.

## Notes

Lead Details Update remains the current Lead snapshot. Activities / Follow-ups are multiple historical records.
