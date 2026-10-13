# Slice 9D Acceptance - Interaction Foundation

Written so a later tester can perform regression/UAT without this session's chat history.

## Preconditions

**This package is based on the authorization post-baseline catalogue** - see
`docs/continuity/AUTHORIZATION_POST_BASELINE_CATALOGUE.md`. That prerequisite carries the
frozen/post-baseline permission split and no migration; 9D adds the first five post-baseline
permissions on top of it. Review and integrate the prerequisite first.

Stack running, Alembic at `20260908_0033 (head)`. This slice adds a migration; after merging,
rebuild the backend image before testing - `alembic/` is baked into the image, so a merged
migration is invisible until `docker compose up -d --build --force-recreate backend` runs:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| Interactions API | `docker compose exec backend pytest tests/test_interactions_api.py -q` | 38 passed |
| Event-payload guard | `docker compose exec backend pytest tests/test_slice_9d_interaction_event_payloads.py -q` | 11 passed |
| Interaction permissions and migration seeding | `docker compose exec backend pytest tests/test_slice_9d_interaction_foundation.py -q` | 19 passed |
| Post-baseline catalogue (from the prerequisite package) | `docker compose exec backend pytest tests/test_authorization_post_baseline_catalogue.py -q` | 11 passed |
| Route migration guard (no new `.role_codes` exception needed) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py -q` | 99 passed |
| Full backend regression | `docker compose exec backend pytest -q` | 1190 passed, 0 failed |
| **Committed-credential check** | `python scripts/check_tracked_secrets.py` | no findings |
| **Repository script tests** | `python -m unittest discover -s scripts/tests` | 58 passed |
| **Contract fixtures** | `python scripts/validate_contract_fixtures.py` | all rules passed |
| Alembic head | `docker compose exec backend alembic current` | `20260908_0033 (head)` |
| Migration reversible | `docker compose exec backend alembic downgrade -1` then `alembic upgrade head` | interaction tables/permissions/grants removed then restored; baseline stays at 31/110 throughout |
| **Empty-database chain** | full chain into a fresh database | the whole chain (32 revisions, numbered 0001-0033 with 0004/0005 unused) applies to head; the three coordinate CHECK constraints exist and a direct insert of latitude 999 is rejected there; downgrade removes both tables and re-upgrade returns to head |
| Frontend typecheck | `docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run typecheck` | clean |
| Frontend tests | same, `npm test` | 54 passed (unchanged - no new public URL was added) |
| Frontend build | same, `npm run build` | clean |

## Manual happy path

Test user `sales1` / `password` (SALES_USER).

1. Open an existing Lead (or create one from `/leads/new`).
2. Scroll to the **Conversations / Interactions** section.
3. Click **Record a conversation**.
4. Fill in: Channel = Call, Direction = Outbound, a recent date/time, a subject, and some notes
   in "What was said / notes".
5. Save. Confirm the conversation appears in the list immediately below, with the subject and
   notes visible.
6. Convert the Lead to an Account + Opportunity (`/leads/{id}` -> Convert action, or via the
   qualification-decision + convert flow if not already qualified).
7. Open the new Opportunity. Confirm the **Conversations / Interactions** section shows the
   "Show conversations recorded on the originating Lead" checkbox, **already ticked** - inherited
   history is on by default wherever a record can inherit, so the salesperson sees the customer's
   history without having to know to ask for it.
8. Confirm the conversation recorded in step 5 is listed, labelled "Recorded on the originating
   Lead (...)".
9. **Untick** the checkbox. Confirm the list becomes empty - nothing has been recorded directly
   against the Opportunity, which is the point: the row was never copied.
10. Re-tick it and confirm the conversation returns.
11. Open the linked Account. Repeat steps 7-10 there - the same single inherited conversation
    should appear, again ticked by default.

Expected result: one conversation, recorded once against the Lead, visible on all three pages
under an explicit "inherited" label, never duplicated.

## Manual permission path

Test users: `sales1` / `password` (SALES_USER) and `finance1` / `password` (FINANCE_USER).

1. As `sales1`, record a conversation on any Lead/Account/Opportunity with a subject **and**
   body text filled in (e.g. subject "RFQ", body "Please quote for 2 cranes").
2. Log out, log in as `finance1`.
3. Open the same record. Confirm the conversation is listed, its subject is visible, but the
   body area shows **"Message content not shown for your role."** instead of the actual text.
4. Confirm `finance1` does **not** see a "Record a conversation" button (Finance holds
   `INTERACTION_READ` but not `INTERACTION_CREATE`).
5. Log in as `readonly1` / `password` (MANAGEMENT_READ_ONLY). Confirm the conversation body
   **is** visible (Management Read Only holds `INTERACTION_CONTENT_READ`), but no "Record a
   conversation" button appears.

Expected result: Finance sees that a conversation happened and its subject/outcome, never the
customer's actual words. Every role that can view a record can view its conversation list.

## Manual validation path

1. Attempt to record a conversation with `linked_record_type` set to something invalid via a
   direct API call (the UI does not expose this, since it only ever sends one of the five valid
   types) - `POST /api/interactions` with `"linked_record_type": "not_a_real_type"` - expect
   `422`.
2. Attempt to record a conversation against a well-formed but nonexistent Lead public id -
   expect `422` with a message naming that no such record exists.
3. Record a conversation with an outcome and a follow-up date. Confirm you can later find a way
   to correct the outcome (via `PUT /api/interactions/{id}` - no dedicated edit button exists in
   the UI for this pilot round; this is a known, deliberate scope trim, not a defect).

## Correction pass 1 - what to re-verify

Added 8 September 2026 after the first independent review. Each item below is covered by an
automated test; the API checks are listed so a reviewer can exercise them directly.

| Behaviour | How to check | Expected |
| --- | --- | --- |
| Partial update preserves the untouched field | `PUT /api/interactions/{id}` with `{"outcome": "x"}` on a record that has a `next_follow_up_at` | 200; `next_follow_up_at` unchanged. Sending `{"next_follow_up_at": null}` explicitly still clears it. |
| External references redact with the body | As `finance1`, `GET` the detail **and** the list for an interaction created with `external_reference_url` and `external_message_id` | Both `null`, `body_redacted: true`. `external_system` still visible. As `sales1`, both present. |
| Coordinates paired and in range | `POST` with only `geo_latitude`; then with `geo_latitude: 91` | `422` in both cases |
| Participant references resolve | `POST` with a participant carrying a random `contact_public_id`; then one carrying only `party_role_code` | `422` in both cases. A participant with only `display_name` is accepted (external person). |
| Idempotent replay | `POST` the same payload twice with the same `idempotency_key` | Both `201`. Second carries `replayed: true` and the **same** `public_id`. One row, one `InteractionRecorded` event. |
| Correlation | `POST` with `X-Correlation-Id: <value>` | Response `correlation_id` echoes it, and the `business_event` row carries it. Omitting the header still yields a generated one. |
| Contract/schema version | Any create or update response | `contract_version` present; the emitted event payload carries `schema_version`. |

**Gate note.** The two SEC-004 findings that made `Required validation` red are fixed by renaming
misleading test variables (`secret_*` to `marker_*`); `check_tracked_secrets.py` and
`scripts/tests` both pass. This was a naming fix, not an exclusion - the scanner's finding was
acted on, not suppressed.

## Correction pass 2 - what to re-verify

| Behaviour | How to check | Expected |
| --- | --- | --- |
| Immutable fields are refused, not ignored | `PUT /api/interactions/{id}` with `{"body_text": "x"}`; then `{"outcome": "ok", "body_text": "x"}` | `422` both times. The row is unchanged - including `outcome` from the mixed request, which must not be partially applied. **No `InteractionUpdated` event is emitted.** A `PUT {"outcome": "ok"}` alone still returns `200` and emits exactly one. |
| Unknown fields are refused | `POST` or `PUT` carrying `not_a_field_at_all` | `422`. All three request schemas forbid extras. |
| Key reuse with a different payload | `POST` twice with the same `idempotency_key`, changing `subject` the second time | First `201`; second **`409`**, message "already been used for a different command". The original is *not* returned. An identical retry still replays with `replayed: true`. |
| Key reuse against a different record | Same key, different `linked_record_public_id` | `409` - the linked record is part of command identity |
| Replay after deletion | Create with a key, `DELETE` it, then retry the identical create | `409`, message "has since been deleted". Nothing resurrected, no duplicate row, and the deleted body does **not** appear in the response |
| Coordinates rejected by the database | Direct SQL `INSERT INTO interaction (...) VALUES (..., 999, -999)` | Rejected by `ck_interaction_geo_latitude_range`. Also test latitude without longitude, and 91 / -91 / 181 / -181. A valid pair still inserts. |
| Participant may not be both | `POST` with a participant carrying both `contact_public_id` and `app_user_public_id` | `422`. Either alone is accepted; the two people together are two participant rows. |

**Empty-database evidence.** The migration changed in this pass, so the chain was re-run into a
fresh database: the whole chain applied to head - 32 revisions, since the numbering runs
0001-0033 but skips 0004 and 0005, so the sequence number and the file count differ - the three
CHECK constraints were present there,
the direct insert of latitude 999 was rejected, and downgrade/re-upgrade returned to head. The
scratch database was dropped afterwards.

## Deferred / not covered by this round

- Commercial Offer and Work Order pages do not yet show the Conversations section (backend
  supports both `linked_record_type` values already; only the frontend mount is deferred).
- No participant-management UI (participants can only be set at creation time via the API).
- No delete button in the UI (the API supports it; `ADMIN`/`SALES_MANAGER` only).
- No Commercial Offer submission-readiness row for "has a conversation been logged" - deferred to
  the next round per the owner's explicit decision to keep 9D from touching any existing module.
- No access audit of who read a message body - deferred to the retention-policy package.
