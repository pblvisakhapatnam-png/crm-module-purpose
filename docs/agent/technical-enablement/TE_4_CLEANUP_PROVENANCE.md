# TE-4 — Cleanup Correctness for the TE-1 Harness

Technical-enablement package, successor to TE-3. Extends the TE-1 harness
(`backend/tooling/smoke_data`).

No application behaviour, API contract, schema, migration, permission rule, business event or
frontend screen changes. Both frozen contracts untouched. Alembic head unchanged
(`20260908_0035`).

**Changed:** `backend/tooling/smoke_data/{cleanup,status,cli,manifest}.py`,
`backend/tests/{conftest,test_smoke_data_harness}.py`, `scripts/vendor-demo.ps1`, documentation.
`store.py` is byte-identical to `main` — everything added to it was removed again with the scope.

## What the harness cleanup does

It deletes a seed run's records from a database that also holds unrelated ones. Ownership follows
a **mixed rule**, and the two halves must not be confused:

*Parents* are claimed by **provenance** — the manifest names them, or a business event records that
the run created them. That distinction is load-bearing: following Opportunity → Account for any
owned Opportunity deletes another run's Account, while not following it leaves an Account the
repair flow created, and no adjustment to how *far* discovery reaches separates the two. The
Opportunity Account repair writes its own `repair_mode`, so `created_minimal_account` is ours and
`existing_account` is not.

*Descendants* are then claimed by **downward containment** — once a parent is owned, the closure
takes what hangs off it, including records another run or a user created there afterwards. That is
reachability, deliberately, and it is the cascade the owner approved on 10 September 2026: "if the
enquiry is being deleted, why even ask."

## What this package changed

- **The provenance edge** for an Account the Opportunity repair flow created, bounded so an Account
  it merely *linked* is untouched. Two tests hold that boundary; neither means anything alone.
- **Manifest validation and collection are one pass** over one pair of mappings, so a record shape
  cannot be validated without being collected or collected without being validated. Two
  hand-maintained lists is how the collections came to be validated nowhere.
- **Audit rows are deleted on `(record_type, public_id)` pairs.** A public id is not unique across
  record types, and matching on the id alone deleted unrelated events. Each account sub-record type
  keeps its own id group for the same reason — pooling them and pairing every id with all four
  types reproduces the defect inside its own fix. `status` counts residue on the same pairs, from
  one shared builder.
- **`exists()` is a counter, not a gate.** It sits outside the delete's `try`, so a provider that
  cannot answer the probe still has its object deleted.
- **Storage-provider conformance is tested**, not assumed: stored objects are reported present,
  `delete` removes them, deleting what is absent is a no-op, and an escaping key raises.
- **`status` gained** the empty-manifest guard `cleanup` already had, residue checks for all four
  account sub-tables, and correct classification of a malformed manifest (previously "a database
  error").
- **`--require-present`**, because `status` exited 0 both when the data was all there and when it
  had all been removed. Both `vendor-demo.ps1` call sites pass it.
- **Tests write to an isolated runs directory** (`backend/tests/conftest.py`), so the real one is
  never touched. In conftest rather than the harness test module, because other modules use the
  harness too.

## What `status` can and cannot tell you

It reports whether a run's anchor records are present, and whether anything is still attached to
records **that still exist**. It **cannot certify that a targeted cleanup left nothing behind**:
once a record the manifest never named has been deleted, nothing attached to it can be rediscovered.

That limitation is TE-3's, and it is unchanged. A mechanism to close it — a durable record of every
id a cleanup deleted — was built here and then **removed**; see below.

## The recorded cleanup scope: built, then deleted

Three review rounds produced a versioned on-disk record of every id a cleanup was about to delete,
so `status` could check residue by each record's own primary key. It worked. It also produced a P1
in **every** review round after it was introduced, the last being the fourth repair to the single
function arbitrating between its two sources.

Owner decision, 10 September 2026: **leave `status` where TE-3 had it.** The mechanism served the
lowest-value need in the package — the CRM pilot resets by rebuilding its database, CI gets a fresh
one, and the only consumer was a developer's shared local database where undetected residue costs
untidiness. Removing it closed every outstanding finding against it at once.

The lesson is recorded because it cost five rounds to learn: **when a fix keeps generating findings,
ask whether the fix should exist before repairing it again.** Two findings in the round before
removal were closed by deletion alone, with no code written.

## Known limitations

- `status` cannot certify a targeted cleanup, as above.
- The READ COMMITTED discovery/delete race is not addressed. A reset is one operator action, and
  `SERIALIZABLE` or advisory locks over FK-less polymorphic relationships are disproportionate here.
- A seed that fails partway leaves records with no run id to clean up with.
- A storage-deletion failure names its keys in `CleanupStorageError` and nowhere else; they are
  removed by hand, which is what the E2E and runbook instructions say.
- No index on `business_event.record_public_id`, which the repair edge scans once per closure pass.

## Stakes

The CRM pilot does not depend on this — it has its own stack and resets by rebuilding. Targeted
cleanup serves the automated test suite, which shares a developer's local database and cannot
rebuild. A residual defect costs untidiness. That bounds what is proportionate, and this package
learned the hard way that it bounds what should be *built*, not just how carefully it is checked.

See `docs/agent/acceptance/te-4-cleanup-provenance-acceptance.md` for verification.

## Later extension: machine eligibility (ELG-1, 27 September 2026)

ELG-1's certificates, "not applicable" marks and stored eligibility decisions are **descendants** of the
run's assets, claimed by downward containment like everything else under an owned parent: each is about one
asset and never moves to another, so it is the run's by the asset it is on, whoever recorded it - the harness,
a tester, or a Playwright test on the screen. The assets themselves are the run's by provenance, as before
(the import that brought them in, or the kit model a piece was added as). A certificate's copies go with it,
through the same (linked record type, public id) pairs the other documents use, their stored files included;
audit rows go on the typed pairs `eligibility_certificate`, `eligibility_not_applicable` and
`eligibility_decision`. The certificate rules are the platform's, not a run's, and are never deleted.

Cleanup refuses, deleting nothing, when a stored decision about an asset the run did **not** bring in has a
result naming one of the run's assets - a part fitted to that machine when it was judged - or naming a
certificate or mark on one of them, such as the run's carrier whose papers met that machine's rule. Deleting the run's
asset, or the certificate the decision names, would break that decision's record. Code:
`_refuse_eligibility_entanglement` and `_delete_eligibility` in `backend/tooling/smoke_data/cleanup.py`;
tests: `backend/tests/test_elg1_smoke_data.py`.

