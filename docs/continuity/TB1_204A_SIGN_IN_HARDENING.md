# Sign-in hardening: wrong-password stops, ended sign-ins, password rules (7 October 2026)

TB-1 correction package 3: the last Critical correction in the corrective-slice register's "Recommended correction
sequence", row 3 (CS-08) - TB1-204 part a. Branch `fix/tb1-204a-sign-in-hardening`, built on `main` at `4ff3966`.
Alembic revision `20260908_0048`. The TB-1 records under `docs/agent/tb-1/` are pinned by SHA-256 and are not edited;
this note, `NEXT_STEPS.md`, the two contracts below and dated reconciliation notes in the records that said otherwise
carry the corrections. Parts b and c of TB1-204 (diagnostics and CORS; `nosniff`) are register row 12, not this
package.

## What was wrong

TB1-204 part a, as P2 recorded it (items a to f):

- **(a)** `POST /api/auth/login` answered every attempt; nothing counted wrong passwords. Only the hosted pilots'
  Traefik rate limit and site login stood in front of guessing - about a day and a half for a 25-bit pilot password,
  by TE-5's own estimate.
- **(b)** A sign-in stayed valid for its 480 minutes whatever happened to the account's password. The package prompt
  said a disabled account's earlier sign-ins kept working too; the code showed otherwise - every request re-reads the
  account and its roles, so disabling, retiring and a role change already applied at once. But **disabling and then
  enabling again within 8 hours brought the old sign-ins back**, which nobody had recorded.
- **(c)** No password rule beyond 1 to 200 characters.
- **(d)** PBKDF2-SHA256 at 260,000 iterations; OWASP's current figure is 600,000.
- **(e)** An unknown username was refused before any hashing, so the answer's speed showed which usernames exist.
- **(f)** A token holding a non-ASCII character raised `UnicodeEncodeError`, not a `TokenError`: 500 instead of 401.

And the token sat in `localStorage`, readable by any script on the page.

Found while building it, in the same code: a failed sign-in recorded **what was typed as the username** in its event.
That is sometimes the person's password, typed in the wrong box, and the event log keeps it for good; and because
the log then refused any payload holding "password", "token" or "secret" (until CS-02, TB1-500), a typed name such as
`mypassword` made the sign-in answer **500**. Probing the same route found three more 500s, all before this package: a username holding a NUL
character (PostgreSQL takes none), and a lone surrogate in either field - JSON allows one, UTF-8 cannot carry it, and
FastAPI's 422 answer, which repeats the refused input, then failed to be written, **on any route**.

## The decisions

The owner, 7 October 2026, at the start of this package (each the recommendation put to them):

1. **Wrong passwords.** Five failed sign-ins for one username within any 15 minutes, with no successful sign-in among
   them, stop that username for 15 minutes. Counted per typed username, not per network address: on the pilots every
   request reaches the backend from nginx, which forwards no client address, so counting by address would stop
   everyone together. Counted whether or not an account has the name, so being stopped shows nothing about which
   usernames exist. An admin lifts it early with the account tool's `unlock`. The sign-in page says so next to the
   button. Accepted consequences: a tester who stops themselves waits 15 minutes or asks the owner; anyone past the
   site login who knows a username can keep that person stopped, 15 minutes at a time.
2. **Ending sign-ins.** A password reset, disabling and retiring end every earlier sign-in at once; enabling again
   does not bring them back. A role change needs nothing. A new tool command, `end-sign-ins`, ends them without
   changing the password. **Sign out stays a browser action**: with this design a server-side Sign out would sign the
   person out on every device at once; one device's belongs with the cookie move (4).
3. **Password rules**, wherever a password is set: at least 12 characters; not containing the username; not containing
   an obvious word or run (`password`, `qwerty`, `admin`, `pbl`, `123456` and the like); not one character repeated.
   No capital/digit/symbol rule. Passwords already set are not checked (only their hash is kept) and keep working;
   the pilots' form passes; the development seed's `password` is exempt.
4. **Token storage.** Stays in `localStorage` for now, recorded; the move to a secure cookie is scheduled with CS-10's
   shared helper, before production (register row 12).

Built without asking, as ordinary safeguards (ADR-023): 600,000 iterations with each stored hash upgraded at that
user's next successful sign-in; every wrong-credentials refusal (401) costs the same hashing wherever the count is
600,000, which is everywhere but development and CI ("What changed", the work factor) - a stopped name's 429
checks no password at all; a malformed token is a 401. And the corrections
above: the failed sign-in's event records the account's own username when the typed name reaches one, and only that
the name reaches none otherwise - never what was typed; a sign-in holding a NUL character is refused as malformed
(422), before anything is counted; and the 422 answer is written with non-ASCII escaped, so a lone surrogate gets a 422
on every route.

## What changed

Backend:

- `backend/alembic/versions/20260908_0048_sign_in_hardening.py`: `app_user.token_version` (integer, not null, default
  0, never negative) - accounts already disabled or retired start at 1, so a token from before the change (which
  counts as 0) does not come back when such an account is enabled (round 1) - and two tables (round 3; one row per
  username with arrays of its attempts before): `sign_in_attempt`, one row per recent attempt, numbered by its
  sequence, which never reuses a number, with its time; and `sign_in_stop`, one row per stopped username with until
  when. Both key the SHA-256 of the typed name's lower-cased form (PostgreSQL's `lower()`, the one the sign-in lookup
  uses); no typed text is stored. The attempts of the last 15 minutes are the count, so the window rolls (round 1; it
  was a count from a window's start, which a boundary reset). Downgrade drops all three.
- `backend/app/modules/identity/throttle.py` (new): an attempt is **counted before its password is checked**, in a
  transaction the service commits at once. Everything that reads or writes one name's rows first takes that name's
  advisory lock (`pg_advisory_xact_lock(hashtextextended(...))`, the codebase's idiom) and touches no other name's
  rows (round 3), so one name's attempts are taken one at a time and two names' never wait for each other - no
  deadlock. A burst of parallel guesses therefore gets no more than five checked, and no lock is held while a
  password is hashed. The attempt that reaches the limit stops the name at once, and **the stop's event is written in
  that same transaction** (round 1), so a stop never exists without its `UserSignInLocked`. A successful sign-in
  removes only its own attempt and those numbered before it - attempts that came after it, still being checked or
  already failed, keep counting (round 2), and since numbers are never reused, not even after pruning (round 3) - and
  lifts a stop in force when fewer than five attempts remain in the window, recording `UserSignInUnlocked` ("Lifted
  by a successful sign-in: too few attempts came after it to keep the stop."). A stop is never shorter than the window
  (round 3; since round 9 asserted over the fixed `ATTEMPT_WINDOW` and `STOP_LENGTH` constants), so when one runs out the attempts that made it have left the window and counting starts
  again. Old attempts and stops are pruned at the start of each sign-in, in a transaction of their own that skips any
  row another holds (`SKIP LOCKED`) and so never waits, each attempt by its own time and only a minute past the
  window or stop, so pruning never removes a row a concurrent sign-in still counts (rounds 2 and 3). `unlock` lifts
  only a stop in force, with its name's attempts; a name not stopped keeps its count (round 1).
- `backend/app/modules/identity/service.py`: the sign-in prunes old rows (committed on their own), counts the attempt,
  refuses a stopped name without checking
  its password, always checks the password (against a stand-in when there is no usable hash, so an unknown, disabled
  or password-less account costs the same - development and CI aside, below), clears the count on success, upgrades an older hash, and issues a token
  carrying the account's `token_version`. It looks the account up first, so the stop's event, written with the
  count, can name it.
- `backend/app/modules/identity/routes.py`: `429` with "Too many failed sign-ins for this username. Try again in N
  minutes." and `Retry-After` for a stopped name and for the attempt that stops it; `401` otherwise as before. Event:
  `UserLoginFailed` (reason distinguishes a stopped name); payload `{"username": <the account's own>}` or
  `{"username_known": false}`, the rule every sign-in event follows.
- `backend/app/modules/identity/dependencies.py`: a token whose `ver` is not the account's is refused, 401 "This
  sign-in has ended. Sign in again." A token issued before this change has no `ver`, read as 0 - the start of every
  account active when the migration runs - so deploying it signs no active account out; an account already disabled or
  retired starts at 1, so its older tokens stay ended (round 1; this sentence corrected in round 2).
- `backend/app/core/security.py`: the count in force, 600,000 outside development and CI; `verify_password` always
  spends at least that (a stand-in for no
  hash, a top-up for an older hash - whether or not it matches, round 1: a disabled account's right password on an
  older hash was answered faster); `password_hash_needs_upgrade`; tokens carry `ver`
  (`create_access_token` now requires it, so nothing can issue a token without the account's number); a non-ASCII
  token, a payload that is not an object, an expiry or version that is not a whole number are `TokenError`s. A stored
  hash claiming more than 600,000 rounds is unusable, refused after the stand-in's work (round 7: up to ten times the
  count was accepted, so refusing such an account cost more than refusing any other; round 8 set the bound at
  600,000, the most any setting can write, rather than the current setting).
- The count is a setting, `PASSWORD_HASH_ITERATIONS` in `backend/app/core/config.py`, default 600,000
  (`STANDARD_PASSWORD_HASH_ITERATIONS`), never more in any environment, and exactly that outside development and CI,
  which may set fewer - elsewhere the settings refuse fewer, so the backend does not start (option A, the owner, 8
  October 2026: at 600,000 the test suite took CI's backend job past its 45-minute limit).
  `.github/workflows/te-2ci-validation.yml` sets 10,000 for the backend job only; its run took 11 minutes. As no
  setting writes a hash above 600,000 and every hash up to that is usable, changing the setting - a rollback, or an
  old backend still running beside a tool on a new count - never locks anyone out (round 8; round 7's bound at the
  current setting would have). Where development or CI set fewer, a hash with more than the setting is checked at
  its own count, so a refusal there can cost more, and so show that the account exists: only those two can be in
  that state, and they hold only test accounts. The owner accepted that as a stated limit (8 October 2026, review
  round 9) rather than refusing such hashes there (round 7's rule, which locks test accounts out when the count is
  lowered) or making every refusal cost the highest count stored (a query per sign-in). Raising the work factor is a
  change to the number in code; older hashes are then upgraded at each person's next sign-in. A demo user's hash is
  upgraded the same way - at its next sign-in, not when the backend starts, since the seed replaces only a hash that
  no longer accepts the demo password (round 8 corrected this note, which said otherwise).
- Round 8 bounded the sign-in window and the stop at a day as settings; round 9 found the attempt limit still
  unbounded, so a configuration could switch the stop off. The three numbers are now constants in `throttle.py`
  (`ATTEMPT_LIMIT`, `ATTEMPT_WINDOW`, `STOP_LENGTH` - the owner's 5, 15 and 15 minutes), not settings: nothing sets
  them, no test needs to, and no configuration can weaken the stop. A stale `SIGN_IN_*` variable is ignored.
- `backend/app/modules/identity/repository.py`: `token_version` read with the account; `replace_password_hash` swaps
  the hash only if it is still the one read, so an upgrade never overwrites a reset made meanwhile, and leaves
  `updated_at` and `token_version` alone (not a password change).
- `backend/app/modules/identity/schemas.py`: the sign-in request refuses a NUL character or text that is not UTF-8 in
  either field (422).
- `backend/app/core/errors.py`, `backend/app/main.py`: the application's handler for FastAPI's 422 - the same body,
  written with every non-ASCII character escaped, so it can always be sent, and a number JSON cannot hold - Python's
  decoder reads 1e400 as infinity, and accepts NaN - repeated as its text (review round 12: such a body answered 500);
  any other input it cannot repeat - raw bytes that are not UTF-8, a value nested too deeply to write - is left out,
  each error keeping its type, location and message (review round 13).
- A stop is never shorter than the window (round 3; since round 9 asserted on the throttle's constants).
- `backend/app/modules/events/repository.py`: `payload_is_storable(payload)` - whether the event log's guard would take a
  payload - re-exported by `events/service.py`. `identity.service.storable_event_payload` uses it: an event's payload
  names an account by its username, or, when the log would refuse that username, by the fixed
  `{"username_withheld": true}` - and the event's `record_public_id` names the account either way - so such an account's
  sign-ins answer 200, 401 or 429 rather than failing (round 4; round 6 replaced the first stand-in, the public id in
  the payload, which is only a 36-character text). Round 7: the whole payload is checked, not only the username - a
  success event lists the account's role codes and a role change both sets, so a refused role code made a correct
  sign-in fail after its attempt was counted, and made that role impossible to remove. `storable_event_payload`
  withholds the whole payload when any part of it would be refused; `signed_in_event_payload` builds the success
  event's payload in the identity service, so the sign-in route reads no role codes, as
  `test_authorization_route_migration_guard.py` requires of route modules (its allowance for the old statement is now
  unused; `DEFERRED_REQUIREMENTS.md`). **What the log refuses changed when CS-02 (TB1-500, #105) merged first, on 8
  October:** until then the words "password", "token" and "secret" anywhere; since then text shaped like a credential
  (a JSON Web Token, a private key, a password hash, an address with a password in it, Basic credentials). This package
  was reconciled with it at the merge: `payload_is_storable` now asks CS-02's own check, so the withholding follows
  whatever the guard refuses, and the words are ordinary text again.
- `backend/app/modules/identity/password_rules.py` (new; it also refuses what the sign-in would refuse, a NUL
  character or non-UTF-8 text). (`backend/app/core/config.py` held the stop's three numbers as settings until round
  9, which made them constants in `throttle.py`.)
- `backend/app/modules/identity/models.py`, `backend/app/models_metadata.py`: the column, `SignInAttempt` and
  `SignInStop` (round 3).
- `backend/tooling/user_admin/`: `reset-password`, `disable` and `retire-demo-users` raise `token_version`; new
  `end-sign-ins` (event `UserSignInsEnded`) and `unlock` (event `UserSignInUnlocked`, for an account); the tool's
  events name an account by the sign-in events' rule, so its commands work on an account whose username the event
  log would refuse; `create` refuses a username or display name the event log would refuse, asked directly rather
  than left to the event's failure (round 7) - since CS-02, text shaped like a credential, so "Under Secretary" is
  created, and the message says so instead of naming the three old words (CS-02's note left that wording for this
  package); an exit 3 for
  `end-sign-ins` or `unlock` says to run it again, since `list` shows neither (round 5); `create` and
  `reset-password` refuse a chosen password that breaks a rule at exit 2 before anything changes, naming the rule and
  never the password, and draw a generated one again in the rare case it contains a short username. The reset's note
  now says every earlier sign-in has ended.
- `backend/tooling/smoke_data/auth_tokens.py`: its test token carries the account's number.

Frontend:

- `frontend/src/components/signInMessages.ts`: `signInRefusal` - the server's words for a 429, "Sign-in failed. Check
  the username and password." for anything else.
- `frontend/src/pages/LoginPage.tsx`: shows that message beside the Sign in button, where the failure already was.

Tests:

- `backend/tests/test_tb1_204a_sign_in_hardening.py` (new, 91 tests): the fifth wrong password stops the name and then
  even the right one is refused, with one `UserSignInLocked`; a stop runs out, and counting starts again after it; a
  success clears the count (here on the attempt that reaches the limit, so the stop is recorded and then lifted);
  failures older than the window stop counting, and the window rolls - one attempt, three at 14:59, four from 15:01
  give five checked and then the stop (round 1); an unknown username is stopped the same way
  and nothing typed reaches the events or the table; a password typed as the username is a clean 401 and is not
  recorded, including one shaped like a credential, which since CS-02 would have answered 422; an account whose
  username holds text the event log refuses (since CS-02 an address with a password in it; inserted directly - the tool
  refuses such names) signs in, fails and is stopped with defined answers, its events withheld whole and naming it by
  record id (rounds 4, 6 and 11; until CS-02 the test also gave the account a public id holding a refused word, which
  since CS-02 is ordinary text - the public id is an ordinary UUID now), and
  the tool lifts its stop and ends its sign-ins - unlock, end-sign-ins, a reset, disabling - instead of rolling back
  (round 5); a lost confirmation tells the operator to run end-sign-ins or unlock again, and what a second run also
  does, not to check `list` (rounds 5 and 6); a stored hash this module could not have written - a non-ASCII or short
  key, an empty or non-hex salt, iterations out of bounds, another algorithm - is refused after the stand-in's work,
  at sign-in and in the tool's password check, never an error (round 6), including one claiming one round more than
  the count, or ten times it (round 7); an account holding a role whose code holds refused text signs in (200, nothing
  counted) and the tool removes that role, both events withheld whole (round 7); the tool refuses a new account whose
  display name holds refused text, and creates "Under Secretary" (round 7, after CS-02); the default count is 600,000, and production settings refuse fewer
  (option A); no setting may hash more than 600,000 times, in any environment; a hash written at 600,000 stays usable, and is not downgraded, when the setting is lowered; the seed
  keeps a demo user's valid older hash, which that user's next sign-in upgrades (round 8);
  every spelling of a name shares its count; twelve parallel attempts get exactly five checked; one name's
  stop does not touch another; pruning never waits on a row another transaction holds, removes each attempt by its
  own time whatever order they were numbered in, and keeps one within a minute of the window (round 3); one name's
  counting, stop and clearing never wait for another name's rows, all held elsewhere, and twelve sign-ins for four
  names at once all count (round 3); a success paused past the window clears nothing that came after it (round 3); a
  stop is never shorter than the window, and no environment variable changes the stop's numbers (rounds 3 and 9); a
  stop is never without
  its event when the password check, or the attempt's own event, fails after it, and nothing of the attempt is kept
  when the stop's event cannot be written (round 1); `unlock` lifts a stop and says when there was none, and changes
  nothing before the limit (round 1); accounts already disabled when the change is deployed start at 1, by the
  migration's own statement, so enabling one does not bring back a pre-change sign-in (round 1); a reset, disabling (and enabling
  again), retiring and `end-sign-ins` each end earlier sign-ins; a role change keeps the sign-in with the new roles; a
  token from before the change works until the account's number is raised; new hashes use 600,000; an older hash is
  upgraded at the next successful sign-in only, leaving `updated_at` and the number alone; an upgrade never overwrites
  a reset; every wrong-credentials refusal - unknown name, wrong password, older hash, disabled account on a current or
  (round 1) an older hash, no password - spends exactly
  the count in force, 600,000 outside development and CI (counted, not timed, so the test cannot be flaky); seven malformed tokens are 401s; a sign-in
  holding a NUL character or a lone surrogate is a 422 that counts and records nothing; the 422 keeps FastAPI's shape
  and is written for a lone surrogate, and for 1e400, -Infinity and NaN, on another route too (round 12), and leaves
  out an input it cannot repeat - bytes that are not UTF-8, sent as octet-stream or text, an array 3,000 deep (round 13); the password rules, case by case; every password the generator can make meets them; and the tool refuses weak chosen passwords
  on `create` and `reset-password`, saving nothing and ending nothing.
- `backend/tests/test_user_admin_tooling.py`: the disable test now expects an earlier sign-in to stay ended after
  enabling (the owner's decision 2); a chosen-password case was lengthened to 12 characters for the rules; the two
  settings it builds outside development pin the count, as `test_slice_9b_pilot_hardening.py`'s helper now does,
  since CI sets fewer for the whole job (option A).
- `backend/tests/conftest.py`: the session removes the `sign_in_attempt` and `sign_in_stop` rows it created, as it does
  its events.
- `frontend/src/components/signInMessages.test.ts` (new, 3 tests).

Records: this note; `NEXT_STEPS.md`; `docs/agent/contracts/platform-foundation.md` (the sign-in's 429, the token's
`ver`, the 401 for an ended sign-in) and `docs/agent/contracts/workflow-and-events.md` (the failed sign-in's payload
and three new events); `docs/deployment/CRM_UAT_VPS_RUNBOOK.md` ("Accounts": the rules, `end-sign-ins`, `unlock`, how a
stop works, the known limitations); dated reconciliation notes in `TE_5_UAT_DEPLOYMENT.md` (no password rules; a reset
leaving sign-ins valid; "Deliberately not done: token revocation"); `docs/agent/DEFERRED_REQUIREMENTS.md` (a new section
on what this package leaves, including where the token is kept, and a dated note on the test password lengthened);
the account tool's package docstring; for option A, the runbook's "Accounts" (leave the setting unset) and
`DEFERRED_REQUIREMENTS.md`'s section (raising the work factor; the guard's unused allowance).

## What testers are told

At the next deploy of each pilot, tell its testers, in these words or near them:

> If you type a wrong password five times within 15 minutes, the sign-in page says "Too many failed sign-ins for this
> username. Try again in N minutes." and will not let you in for 15 minutes, even with the right password. Wait, or
> ask the owner to unlock you. Your password and the way you sign in are otherwise unchanged, and the update does not
> sign you out.

Nothing else changes for them. For the owner: the deploy carries a migration, so take the backup first and undo it, if
ever, by restoring that backup rather than by a downgrade (TB1-405, register row 6); and each account's stored
password hash changes at its first sign-in after the deploy, though its password does not - so the 30 September
check that compared hashes between backups to see whether a password changed no longer works across that point. And run no account command while deploying it (the runbook, "Deploy a release"): the tool runs in a container of its
own, which a deploy does not stop, so a reset or a disable started with the previous release's tool and finished
after this release's migration would not end earlier sign-ins (review round 11; the owner chose this written rule, 8
October 2026, over a database trigger or a deploy-time check).

## Checks

| Check (7 October 2026, on this branch) | Result |
| --- | --- |
| Frozen handoff contract SHA-256 before | `70debad7...0b86a`, unchanged |
| Worktree stack started on a fresh volume, then rebuilt with the migration | migrations to `20260908_0048`; "The 6 demo users were already in place."; `admin1` signs in (200) and its hash goes from 260,000 to 600,000; `Bearer é.a.b` -> 401; five wrong passwords for an unknown name -> four 401s, then 429 "Try again in 15 minutes." |
| The new file (at first, before the three additions below) | 46 passed |
| The whole of every file whose control or fixture the change touches: the new file, `test_user_admin_tooling.py`, `test_auth.py`, `test_events.py`, `test_postgresql_dialect_regression.py`, `test_smoke_data_auth_tokens.py`, `test_smoke_data_audit_events.py`, `test_slice_9b_pilot_hardening.py`, `test_business_authority_store_schema.py`, `test_business_authority_security_boundary.py`, `test_business_authority_store_wiring.py` | 345 passed |
| Undo: no stop is ever set | 8 failed - every stop, window, spelling, burst and unlock test |
| Undo: the token's number not checked | 6 failed - reset, disable/enable, retire, end-sign-ins, the pre-change token, and the tool's disable test |
| Undo: disabling does not raise the number | 2 failed - the disable/enable test here and the tool's |
| Undo: chosen passwords not checked against the rules | 4 failed - three weak creates and the weak reset |
| Undo: 260,000 iterations | 2 failed - the new-hash and the upgrade tests |
| Undo: refusals without the stand-in or the top-up | 1 failed - the equal-work test |
| Undo: no ASCII check on the token | 1 failed - the non-ASCII token (500) |
| Undo: the typed username recorded, as before | 2 failed - the unknown-name and the password-as-username tests |
| Undo: the attempt row read without its lock | the burst test failed, 3 runs of 3 |
| Undo: the hash swapped without comparing it | 1 failed - the reset-meanwhile test |
| Undo: a success does not clear the count | 2 failed - the clear and the run-out tests |
| Undo: the page's 429 message removed | 2 of the 3 frontend tests failed |
| Probing the sign-in with malformed bodies (after the above) | a NUL character in the username, and a lone surrogate in either field, each answered 500 - corrected: the three additions below |
| The new file, with the three additions | 53 passed |
| Undo: the sign-in request's NUL check removed | 1 failed - the NUL username (500, from the throttle's digest) |
| Undo: the 422 handler not registered | 3 failed - both surrogate cases and the 422-shape test |
| Undo: pruning without `SKIP LOCKED` | 1 failed - the held-row test (lock timeout) |
| The same malformed bodies over HTTP, after a backend restart | 422, 422, 422 |
| The whole of every touched control's file again, with `test_tb1_503_database_errors_carry_no_values.py` (the error handler's) | 359 passed |
| Undo proofs left the tree as it was | the tree's diff and new files hashed identical before and after each |
| Empty-database migrations, scratch database on the worktree stack | upgrade from empty to `20260908_0048`: the column (integer, default 0, not null), its check, the table, its two checks and key; 0 users; downgrade -1 to `20260908_0047`: table gone, column gone; upgrade to head again; one head |
| Frontend typecheck, tests, build (AGENTS.md sequence, worktree source) | clean; 28 files, 570 tests passed; built |
| Committed-credential and contract-fixture checks | no findings (2093 files); all rules passed |
| Full backend regression, alone, of the round-1 commit `9582ef1` (the owner agreed) | 3064 passed, 1 skipped, 0 failed (1 h 49 min 54 s - package 2's took 53 min: every sign-in in the suite now hashes 600,000 times, and the host had under 1 GB free) |
| Playwright, full suite (`run-e2e.ps1` under pwsh, worktree stack; every sign-in is a start-seeded demo user, now on a 600,000 hash after its first sign-in) | 37 passed, 9 skipped, 0 failed (2.0 min); cleanup succeeded - before the three additions, which touch no page and no sign-in a spec makes |
| Sign-in page by hand (worktree stack, the browser pane hidden, so driven by a page script filling the form and submitting it) | an unknown name with a wrong password: four times "Sign-in failed. Check the username and password.", then "Too many failed sign-ins for this username. Try again in 15 minutes." on the fifth and sixth, each directly below the Sign in button; `unlock` on that name: "may sign in again.", exit 0, and again: "was not stopped from signing in; nothing changed.", exit 0 |
| Independent review (the independent reviewer), round 1 (commit `9582ef1`, packet `2737d0a0...`) | CORRECTION_REQUIRED, five material findings: (1) the count was a fixed window, which a boundary reset, so up to eight passwords could be checked within a few seconds across it; (2) accounts already disabled when the migration ran started at 0, so enabling one revived a pre-change token; (3) a disabled account's right password on an older hash was answered faster, and the records overstated "every refusal"; (4) `unlock` before the limit erased the count and said nothing changed; (5) the stop was committed before its event, so a failure in between left a stop with no record. All corrected - see "What changed" (marked round 1) and the rows below |
| After round 1's corrections: the new file | 59 passed |
| Undo: the count as a fixed window again | 1 failed - the rolling-window test |
| Undo: the migration's statement touching no account | 1 failed - the deploy test |
| Undo: the migration not running the statement | 1 failed - the deploy test (its source check) |
| Undo: an older hash topped up only when it does not match | 1 failed - the equal-work test (the disabled account on an older hash) |
| Undo: `unlock` removing a row that is not stopped | 1 failed - the unlock-before-the-limit test |
| Undo: the attempt committed before the stop's event | 3 failed - the three fault tests |
| After round 1's corrections: the whole of every touched control's file (as before) | 365 passed |
| A populated database, scratch database on the worktree stack: upgrade to `20260908_0047`, one active and one disabled account, then to head | active 0, disabled 1; the table's columns, its check and key; downgrade -1 drops both, upgrade restores 0 and 1; one head |
| Committed-credential check after round 1's corrections | 7 findings (SEC-004), all in this package's test file: request bodies giving the `password` key a literal - the three new fault tests, and the malformed-body tests added before round 1, so the round-1 commit would have failed CI's check too (it was last run before those tests were written). Corrected: the bodies use a named constant, the malformed ones built with `json.dumps`; then no findings (2094 files) |
| The new file after that, and the NUL and 422-handler undo proofs again | 59 passed; the undos fail 1 and 3, as before |
| Playwright after round 1's corrections | 37 passed, 9 skipped, 0 failed (2.1 min); cleanup succeeded |
| Independent review, round 2 (commit `b100054`, packet `b23180e1...`) | CORRECTION_REQUIRED, three material findings: (1) a successful sign-in cleared every counted attempt, including wrong ones that registered after it while it was being checked, so those failures were forgotten; (2) times are taken before the row's lock, so they can be stored out of order, and pruning looked only at the last one - a row with a recent attempt could go; (3) records still said a missing `ver` was every account's start and the deploy signed nobody out, which round 1's start at 1 for inactive accounts made untrue. All corrected (marked round 2 above) |
| After round 2's corrections: the new file | 61 passed |
| Undo: a success clearing every attempt, as before | 1 failed - the success-first test |
| Undo: pruning by the last stored time | 1 failed - the out-of-order test |
| After round 2's corrections: the whole of every touched control's file; the credential check | 367 passed; no findings |
| After round 2's corrections: Playwright | 37 passed, 9 skipped, 0 failed (1.8 min); cleanup succeeded |
| After round 2's corrections: a populated database, scratch database, as before | active 0, disabled 1; columns `last_attempt_number`, `attempt_numbers`, `attempt_times`, `locked_until`; the paired-arrays and digest checks and the key; downgrade -1 and upgrade restore 0 and 1; one head |
| CI on the round-2 commit `b100054` (pull request #102) | five jobs passed; the backend regression was still running when the round-3 commit superseded it |
| Independent review, round 3 (commit `e8f8e8a`, packet `96a436d4...`) | CORRECTION_REQUIRED, three material findings: (1) a registration's transaction pruned other names' rows (skipping locked ones) and then upserted its own, so two sign-ins for two names could each delete the other's row and deadlock on re-inserting it - one answering 500; (2) attempt numbers restarted when a pruned row was recreated, so a success paused past the window could clear a later failure that reused its number; (3) the events contract still said `UserSignInUnlocked` meant the limit-reaching attempt had the right password. Corrected by rebuilding the counter - two tables, a sequence, a per-name advisory lock, pruning in its own never-waiting transaction, a stop never shorter than the window - and the contract (marked round 3 above) |
| After round 3's corrections: the new file | 65 passed |
| Undo: a registration also deleting other names' stale rows | 1 failed - the other-names test (lock timeout). Its first version seeded the other names through the code under test, which under this undo had already deleted the stale rows, so the undo passed; the setup now writes them directly |
| Undo: a success clearing every attempt of its name | 2 failed - the success-first and paused-success tests |
| Undo: no rule that a stop covers its window | 1 failed - the settings test |
| Undo: pruning with no margin | 1 failed - the by-its-own-time test |
| After round 3's corrections: the whole of every touched control's file; the credential check | 371 passed; no findings |
| After round 3's corrections: Playwright | 37 passed, 9 skipped, 0 failed (1.8 min); cleanup succeeded |
| After round 3's corrections: a populated database, scratch database, as before | active 0, disabled 1; `sign_in_attempt` (id bigint, digest, time) and `sign_in_stop` (digest, until), their digest checks, keys and the two indexes; downgrade -1 drops both tables, upgrade restores 0 and 1; one head |
| CI on the round-3 commit `e8f8e8a` | five jobs passed; the backend regression was still running when the round-4 commit superseded it |
| Independent review, round 4 (commit `9ed6468`, packet `c90830c7...`) | CORRECTION_REQUIRED, two material findings: (1) an existing account whose username holds "password", "token" or "secret" (the tool refuses such names; a database may still hold one) made every sign-in answer 500, because the event log refuses those words anywhere and the sign-in events named the account; (2) this note still named the removed `SignInThrottle`, and TE-5's command lists lacked `end-sign-ins` and `unlock`. Both corrected (marked round 4 above) |
| After round 4's corrections: the new file | 68 passed |
| Undo: the sign-in events always naming the account by username | 3 failed - the account test, for each word (500) |
| Main merged into the branch (`f78d25a`: PRs #101 TB1-405 and #103 CS-18, documentation and `deploy.sh`) | one conflict, `NEXT_STEPS.md`: all three 7 October entries kept, this package's last, its next step now row 5 (row 6 is #101) |
| After round 4's corrections: the whole of the 12 touched control files, the three that assert the event guard's message (`test_ert1_equipment_import_api.py`, `test_slice_7d_part_2_billing_terms.py`, `test_slice_7d_part_4_billing_terms.py`) and the two event-payload files (`test_tb1_202_account_event_payloads.py`, `test_slice_9d_interaction_event_payloads.py`); the credential check | 625 passed; no findings |
| After round 4's corrections: Playwright | 37 passed, 9 skipped, 0 failed (1.7 min); cleanup succeeded |
| Independent review, round 5 (commit `ee3d6fb`, packet `63e9af80...`), the last the owner allowed | CORRECTION_REQUIRED, three material findings: (1) the account tool's own events still named the account by username, so on an account whose username holds a refused word unlock, end-sign-ins, a reset and disabling rolled back; (2) an exit 3 for end-sign-ins or unlock said to check `list`, which shows neither - and TE-5 said the same; (3) the events contract did not state the public-id rule. All corrected (marked round 5 above); **a sixth round, and the merge, wait for the owner** |
| After round 5's corrections: the new file | 73 passed |
| Undo: the tool naming the account by username | 3 failed - the tool test, for each word |
| Undo: the `list` advice for end-sign-ins and unlock | 2 failed - the lost-confirmation test, both commands |
| After round 5's corrections: the whole of the 12 touched control files; the credential check | 379 passed; no findings |
| After round 5's corrections: Playwright | 37 passed, 9 skipped, 0 failed (1.7 min); cleanup succeeded |
| Independent review, round 6 (commit `ff74f56`, packet `74330c36...`), the owner's extra round | CORRECTION_REQUIRED, three material findings: (1) round 4's stand-in, the public id, is only a 36-character text and could hold a refused word too; (2) the advice that running end-sign-ins or unlock again is harmless was untrue - a second run also ends a sign-in, or lifts a stop, made since; (3) a stored hash with a non-ASCII key made the comparison raise (500). All corrected (marked round 6 above); **a seventh round, and the merge, wait for the owner** |
| After round 6's corrections (the stack rebuilt fresh once the overnight run had finished): the new file | 82 passed |
| Undo: the public id in the payload, as in round 4 | 3 failed - the sign-in account test, for each word (500) |
| Undo: the round-5 "harmless" advice | 2 failed - the lost-confirmation test, both commands |
| Undo: the stored key compared as text, unchecked | 1 failed - the non-ASCII key (500) |
| After round 6's corrections: the whole of the 12 touched control files; Playwright; the credential check | 388 passed; 37 passed, 9 skipped, 0 failed (1.8 min), cleanup succeeded; no findings |
| Frozen handoff contract SHA-256 after (the round-5 candidate) | `70debad7...0b86a`, unchanged |
| Independent review, round 7 (commit `00f4640`, packet `c563e2ca...`, the owner's second extra round) | CORRECTION_REQUIRED, two material findings: (1) a stored hash claiming up to ten times the count was accepted and worked through, so refusing such an account cost up to ten times more; (2) only the username was checked against the event log's words, so a role code holding one made a correct sign-in answer 500, after its attempt was counted, and the role impossible to remove. Both corrected (`3d02191`); the owner then chose one more round, with the trust boundary stated |
| CI on `3d02191`: the backend regression at 600,000 rounds ran past its 45-minute limit, twice | the owner chose option A (8 October): the count a setting, CI's backend job at 10,000; corrected in `3d02191` and `75489de` |
| Main merged into the branch (`6bb5f6c`: PR #104, CS-12 TB1-605) | one conflict, `NEXT_STEPS.md`: both entries kept, this package's last |
| CI on `6bb5f6c`, the first run at 10,000 (11 min 15 s) | 3094 passed, 12 failed: nine tests building settings outside development read CI's 10,000 and were refused; the default-count test read it too; the tool's `create` let a display name with a word through (round 7's whole-payload rule); the route guard refused round 7's wrapped success payload in `identity/routes.py`, a file not in the touched list since round 7. All corrected: the settings pinned, the default read from the field, `create`'s refusal asked directly, the payload built in the service; the guard's file joins the touched list |
| After those corrections, the backend at 10,000 (as CI): the new file; the whole of the 13 touched control files (the 12 and the route guard's) | 90 passed; 495 passed |
| Undo: the cap at ten times the count, as before round 7 | 2 failed - one round over the count, and ten times it |
| Undo: only the username checked, as before round 7 | 3 failed - the role-code test, for each word |
| Undo: `create`'s refusal not asked | 3 failed - the new-account test, for each word |
| Undo: the route reading the role codes, as in `3d02191` | 1 failed - the route guard's scan |
| Undo: no floor outside development and CI | 1 failed - the default-count test |
| Undo proofs left the tree as it was | hashed identical before and after each |
| The backend back at 600,000: the whole of the 13 touched control files; Playwright; the credential check | 495 passed; 37 passed, 9 skipped, 0 failed (2.3 min), cleanup succeeded; no findings (2100 files) |
| Frozen handoff contract SHA-256 after (the round-8 candidate) | `70debad7...0b86a`, unchanged |
| Independent review, round 8 (commit `60569a9`, packet `e4c9ec82...`), the owner's third extra round, with the trust boundary stated | CORRECTION_REQUIRED, three material findings, all on option A's setting: (1) a hash stored with more rounds than the current setting was unusable, so a lowered setting - a configuration rollback, or a tool on a raised count beside a backend still on the old one - locked out accounts the application itself had hashed; (2) the new numeric settings had no upper bound, so a huge count hung every sign-in and a huge window or stop overflowed; (3) this note said demo users are re-seeded at a new count when the backend starts, which the seed does not do for a valid older hash. Corrected: the count bounded at 600,000 in every environment and every hash up to that usable; the window and stop bounded at a day; the records corrected |
| After round 8's corrections: the new file at 600,000; the whole of the 13 touched control files at 10,000, on a stack whose demo users hold 600,000-round hashes (before the correction, the 422 test's `admin1` sign-in failed there) | 93 passed; 498 passed |
| Undo: the bound at the current setting, as in round 7 | 1 failed - the lowered-setting test |
| Undo: no upper bound on the count | 1 failed - the bounds test |
| Undo: no upper bound on the window and the stop | 1 failed - the bounds test |
| Undo: the seed replacing a valid older demo hash | 1 failed - the seed test |
| Undo proofs left the tree as it was | hashed identical before and after each |
| CI on `60569a9` (pull request #102), at 10,000 rounds | all seven checks passed: backend regression (10 min 46 s), Compose build, health and E2E, migrations, frontend, fixtures, secrets; Required validation succeeded |
| After round 8's corrections, at 600,000: the whole of the 13 touched control files; Playwright; the credential check | 498 passed; 37 passed, 9 skipped, 0 failed (1.7 min), cleanup succeeded - but against a backend last started before round 8's changes, which it does not reload, so it proved the pages, not round 8's code (rerun below, after round 9); no findings |
| Frozen handoff contract SHA-256 after (the round-9 candidate) | `70debad7...0b86a`, unchanged |
| Independent review, round 9 (commit `73a3696`, packet `e93c9ee0...`), approved by the owner | CORRECTION_REQUIRED, three material findings: (1) the attempt limit was still an unbounded setting, so a configuration could switch the stop off; (2) in development and CI with a lowered count, a hash written at 600,000 makes a refusal cost more than an unknown name's, showing the account exists; (3) TE-5's tooling record said the application's engine keeps SQL parameters (untrue since TB1-503) and every tool event carries the username and roles. Corrected: (1) the stop's three numbers are constants, not settings; (2) the owner accepted it as a stated limit of development and CI, and the records that claimed equal cost everywhere are qualified; (3) dated reconciliations in TE-5 |
| CI on `73a3696` | all seven checks passed (backend regression 14 min 44 s); Required validation succeeded |
| After round 9's corrections: the new file at 600,000; the whole of the 13 touched control files at 10,000 | 93 passed; 498 passed |
| Undo: the attempt limit a setting again | 1 failed - the constants test |
| The backend restarted on round 9's code: Playwright; by hand over HTTP; the credential check | 37 passed, 9 skipped, 0 failed (1.9 min), cleanup succeeded; an unknown name's six wrong passwords answered 401 four times, then 429 "Try again in 15 minutes." twice, and `admin1` signed in (200); no findings |
| Frozen handoff contract SHA-256 after (the round-10 candidate) | `70debad7...0b86a`, unchanged |
| Independent review, round 10 (commit `0fe1284`, packet `82f5ffb9...`), approved by the owner | CORRECTION_REQUIRED, one material finding: this note still called the stop-covers-window rule "a settings rule" after round 9 made the numbers constants. Corrected |
| Main merged into the branch (CS-02, TB1-500, #105, `61c7d24`), which made pull request #102 conflicting | conflicts in `events/repository.py` (main's guard taken whole; `payload_is_storable` rebuilt on its check), `main.py` (both exception handlers kept) and `NEXT_STEPS.md` (both entries, this package's last); the tests that used the three words now use a credential-shaped value, and `create`'s refusal and message follow CS-02's rule |
| After the merge: the whole of the 14 touched control files (the 13 and CS-02's `test_tb1_500_event_payload_guard.py`) at 10,000 | 703 passed |
| Undo: `payload_is_storable` always true | 4 failed - the account, tool, create and role-code tests |
| Undo: the success payload not withheld whole (round 7's undo, after the merge) | 1 failed - the role-code test |
| Undo: `create`'s refusal not asked (after the merge) | 1 failed - the create test |
| After the merge, at 600,000: the whole of the 14 touched control files; the backend restarted on the merged code: Playwright, by hand over HTTP, the credential check | 703 passed; 37 passed, 9 skipped, 0 failed (1.9 min), cleanup succeeded; five wrong passwords for an unknown name: 401 four times, then 429; no findings |
| Frozen handoff contract SHA-256 after (the round-11 candidate) | `70debad7...0b86a`, unchanged |
| Independent review, round 11 (commit `cf27a35`, packet `d1fcb6c6...`), approved by the owner | CORRECTION_REQUIRED, two material findings and one advisory: (1) the account tool runs in a container of its own, which a deploy does not stop, so a reset or a disable started with the previous release's tool and finished after this migration would not end earlier sign-ins; (2) this note still said 93 tests and described a public-id case the tests no longer build after the merge; (3, advisory) for an account whose stored username is credential-shaped, the success and tool events withheld only the username, keeping the role codes. Handled: (1) the owner's written rule in the runbook - no account command during a deploy; (2) corrected, 85 tests; (3) every payload is now composed with the real username and withheld once, whole |
| CI on `cf27a35` | all seven checks passed (backend regression 10 min 54 s); Required validation succeeded |
| After round 11's corrections, at 10,000: the new file and the account tool's | 162 passed |
| Independent review, round 12 (commit `eb4c11e`, packet `2f174904...`), approved by the owner | CORRECTION_REQUIRED, one material finding and one advisory: (1) a body such as `{"username": 1e400, ...}` answered 500 - Python's decoder reads it as infinity, which FastAPI's 422 repeats and JSON cannot hold; (2, advisory) the stop's event for a credential-shaped stored username kept `locked_until` beside the withheld marker. Both corrected: the 422 handler repeats a non-finite number as its text; the stop's payload is composed with the real username and withheld once, and `account_event_payload` is gone |
| Undo: the 422 handler without the non-finite step | 3 failed - 1e400, -Infinity and NaN |
| Undo: the stop's payload withheld only in part | 1 failed - the account test |
| After round 12's corrections, at 10,000: the whole of the 14 touched control files; the backend restarted: by hand, Playwright, the credential check | 706 passed; `{"username":1e400,...}` answered 422; 37 passed, 9 skipped, 0 failed (4.5 min), cleanup succeeded; no findings |
| Frozen handoff contract SHA-256 after (the round-13 candidate) | `70debad7...0b86a`, unchanged |
| Independent review, round 13 (commit `0b16097`, packet `8f832ca8...`), approved by the owner | CORRECTION_REQUIRED, one material finding: a body of bytes that are not UTF-8, sent as anything but JSON, answered 500 - FastAPI's error repeats the bytes, which its encoder could not decode. Probing the same handler found a second: a username 3,000 arrays deep (writing it ran out of recursion). Corrected for the whole class: when the input cannot be repeated, for any reason, each error keeps its type, location and message and the inputs are left out |
| Undo: no fallback in the 422 handler | 3 failed - octet-stream, text and the deep array |
| Malformed bodies by hand on the restarted backend | invalid UTF-8 as octet-stream, as text and as a multipart field: 422; a 3,000-deep username: 422; invalid UTF-8 inside JSON, JSON 100,000 deep, a 5,000-digit number: FastAPI's own 400; none a 500 |
| After round 13's correction, at 10,000: the whole of the 14 touched control files; Playwright on the restarted backend; the credential check | 709 passed; 37 passed, 9 skipped, 0 failed (2.0 min), cleanup succeeded; no findings |
| Frozen handoff contract SHA-256 after (the round-14 candidate) | `70debad7...0b86a`, unchanged |

## What is not changed

- Where the browser keeps the sign-in (`localStorage`), and Sign out clearing only the browser: decision 4, scheduled
  with CS-10 before production (`DEFERRED_REQUIREMENTS.md`, "Sign-in: what TB-1 TB1-204 part a left").
- TB1-204 parts b and c - unauthenticated diagnostics, the development CORS origin, `nosniff` - are register row 12.
- SSO, MFA for privileged users, configurable session timeout and device controls remain the NFR's target.
- `UserLoginFailed` events already stored keep the typed username they were written with (pilot data).
- The 25-bit pilot password form stays until real data, as TE-5 records; it meets the new rules.
- No new route and no permission change: `unlock` and `end-sign-ins` are the server account tool's, run by whoever
  holds the server.
