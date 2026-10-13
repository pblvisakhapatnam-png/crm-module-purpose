# TE-3 — UAT Synthetic Data Pack

Technical-enablement work package, not a numbered CRM business slice. Extends the TE-1 harness
(`backend/tooling/smoke_data`) rather than introducing a second seeding mechanism, following the
precedent TE-1 set and Slices 6O.1, 6O.2 and 6P each reused.

**No application behaviour, API contract, database schema, migration, permission rule, business
event or frontend screen changes.** Both frozen contracts are untouched.

## Superseded in part by TE-4 (10 September 2026)

Two statements below were accurate when written and are no longer current. They stand as written,
per ADR-013: this document records what was true at TE-3, and a later correction is a
reconciliation rather than a rewrite.

- *"`status` does not certify that a targeted cleanup left nothing behind."* **Still true.** TE-4
  built a mechanism to close this and then removed it; see the TE-4 package document.
- The generic Opportunity -> Account edge removed by TE-3's third review did not distinguish an
  Account the repair flow *created* from one it merely *linked*. TE-4 draws that from the repair's
  own business event.

See `docs/agent/technical-enablement/TE_4_CLEANUP_PROVENANCE.md`.

## Objective

Practice data for the PBL CRM pilot, in two halves: a seeded dataset for browser testing and a
blank system plus a printed data sheet for manual entry. Both carry deliberately awkward-but-real
shapes, because a tidy dataset flatters the UI and hides the problems a pilot exists to find.

## Why the pilot data is synthetic — and why that had consequences

Owner decision, 8 September 2026: the pilot runs on synthetic data. Recorded here in full because
a later reader will otherwise wonder how an item marked *required before production* did not block
a pilot.

`docs/agent/DEFERRED_REQUIREMENTS.md` records one open policy question covering interactions
(9D), documents (9C) and generated quotations (9E): nothing purges records at the end of a
retention period, and no audit records who downloaded a document. That question is genuinely
required before production. It does **not** gate this pilot, because the pilot handles no real
customer data — and that argument holds **only while the data is both invented and removable**.

Removable turned out not to be free. See "The cleanup defect" below.

## The cleanup defect this package had to fix first

The TE-1 cleanup routine predates Slices 9C, 9D and 9E and had never created an account address,
GSTIN or tax profile. Two distinct failure modes, found by writing the tests first:

**Loud.** `business_party_address`, `business_party_gstin`, `business_party_tax_profile` and
`business_party_contact` all reference `business_party` with no `ondelete`, so the bare
`DELETE FROM business_party` raises `ForeignKeyViolation` and aborts the whole cleanup the moment
a dataset attaches any of them — which the UAT pack must, since the awkward-shape requirement is
precisely a long legal name, a multi-line site address and several GSTINs.

**Silent, and worse.** Slice 9E's `crm_commercial_offer_quote_document.commercial_offer_id` is
application-enforced with **no declared foreign key** (a documented convention in that module), and
Slice 9C documents and Slice 9D interactions are linked by `linked_record_public_id`. Deleting the
parent therefore does not fail. It succeeds, and the child survives pointing at a record that no
longer exists. Reproduced before fixing: **2 orphaned quote documents and 2 orphaned
`document_metadata` rows, with cleanup reporting success both times.**

The silent mode is the dangerous one for a pilot whose entire justification is removability: a
reset would appear to work while quotations, stored files and whatever users typed into the
conversation log remained.

Both were fixed by extending the ownership-discovery pattern TE-1 already established for
live-created Work Orders — discover from what the run owns, not from what the manifest happens to
list. That first fix was itself incomplete; see "Second review" below, where discovery is replaced
by a closure.

**Two claims in the first fix were wrong and are corrected further down; they are kept here as the
record of what was tried.** It deleted stored bytes *before* their metadata row, reasoning that
the reverse would strand the file — the later review showed the real hazard runs the other way,
because a rollback restores rows but never files. And it argued the resulting risk was recoverable
by a later sweep; no such sweep exists. Byte deletion now happens **after the commit**, and a
failure raises with the orphaned keys named.

`status` was corrected in the same pass, its docstring having justified checking only anchor
records on the grounds that "if an anchor record is gone, its subordinates are gone too
(FK-enforced)" — the very assumption disproved above. That correction was also incomplete: the
check it added joined through the parent it was meant to detect the absence of. See below.

## What was added

**`backend/tooling/smoke_data/cleanup.py`** — delete steps for quote documents, documents (with
their stored bytes), interactions and interaction participants, plus the four account sub-tables;
account sub-record and document public ids folded into the business-event cleanup.

**`backend/tooling/smoke_data/status.py`** — a `residue` block, `residue_clear` and `all_absent`.

**`backend/tooling/smoke_data/builders.py`** — `add_account_address`, `add_account_gstin`,
`set_account_tax_profile`, `log_interaction`, `generate_quote_document`, `approve_quote_document`.
`create_account`, `create_account_linked_opportunity`, `create_offer_no_line` and `add_offer_line`
gained optional overrides, all defaulting to their original values so no existing scenario changes.

`add_offer_line` uses an explicit `UNSET` sentinel rather than `None` defaulting, because an
ACTIVE line with **no rate** is a reachable application state the dataset must produce, and
`None`-as-default would have silently priced it.

**`backend/tooling/smoke_data/scenarios.py`** — the `uat-pilot-seeded` scenario: three leads at
three stages of their life, then ten customers across every offer status, with full statutory
identity and real BOQ line shapes. Also `add_market_rate`, `select_basis_rate`,
`create_lead_detailed`, `add_lead_activity_detailed` and `upload_customer_document` in
`builders.py` for the sales-journey coverage described below.

**`docs/uat/`** — the runbook and the manual data sheet.

## Where the data came from

Customers, equipment and work are modelled on PBL's own published project pages and on the BOQ
structure of a real equipment-hiring RFQ held in the tender corpus. Names are altered to be
recognisably fictional, per the owner's rule of 9 September 2026: *"Vizag Steel Plant can become
Kakinada Steel, Larsen & Toubro can become Carson & Two Bros. It gives a familiar ring and at the
same time fictional."* **No real customer name appears anywhere in the dataset.** Crane models are
PBL's own fleet and are used unaltered — a model number identifies equipment, not a customer.

The single most useful shape came from the real RFQ and would not have been invented: **every
crane-hire line is paired with its own overtime line**, at its own rate, with units of `Days`,
`Hrs` and `Mon`. That doubles the line count a screen must hold and matches the Hour/Shift/Day/
Month basis `WBT-001` defines.

## PAN and GSTIN

Owner decision, 9 September 2026: format-valid but impossible. SurePass validation is deferred
(ADR-015), so nothing checks these against the real registry — an invented-but-plausible PAN could
silently coincide with a real business's statutory number.

A PAN's **fourth character encodes entity type** (C/P/H/F/A/T/B/L/J/G). `Z` is not among them, so
`ZZZZ<index><digits>Z` satisfies `^[A-Z]{5}[0-9]{4}[A-Z]$` while naming no entity that could have
been issued one. GSTINs are the state code plus that PAN, which is also why several GSTINs for one
customer correctly **share** a PAN.

The **fifth** character is reserved: seeded customers use `A`–`J`, the manual data sheet uses `M`.
The GST register rejects duplicates globally, so without that separation a pilot user keying in
the data sheet could hit a collision that looks to them like a defect.

## The sales journey, added after owner review

The first version of the dataset started every customer as an Account with an Opportunity already
attached. The owner asked whether the data covered leads being nurtured with calls and notes,
leads closed as not worth pursuing, several market rates collected by Operations with one chosen,
negotiation, and revision. It did not — it began in the middle of the story and skipped most of
what a sales executive actually does. Added:

**Three leads**, each worked through a sequence of calls, emails, meetings and notes rather than a
single activity: one qualified and converted through the real Slice 3D action (producing its own
Account, Opportunity and quotation), one closed as `UNQUALIFIED` with the reason recorded and
correctly producing no Account, and one deliberately left open for a tester to work themselves.

**Three market rates per offer, from three named Operations Executives**, with one selected as the
basis and a mandatory reason. The choice alternates across the dataset: roughly half take the
lowest rate, the rest take the second-lowest with a reason about vendor availability and breakdown
history. Only a dataset containing both shows what `selection_reason` is for — the Commercial
Offer contract states plainly that the selected rate need not be the lowest, and that is invisible
if every offer is quoted on the cheapest.

`collected_by_name` is free text and records who went and got the rate; the authenticated
`created_by` separately records who keyed it in. Multiple Operations Executives entering rates
against one offer is therefore properly attributed, and the pilot can exercise it live.

**A negotiation trail and a real revision.** Four messages over the course of a price discussion,
then an opened revision, resubmission evidence, a second quotation version approved for issue, and
the revision marked resubmitted — with version 1 retained and marked superseded. Previously the
dataset had only a "revision requested" customer response and no revision record at all.

**Uploaded customer documents.** Three offers carry a file uploaded through the real Slice 9C
upload path, storage provider and all. The generated quotation exercises document *generation*;
upload is a different route with different code behind it, and is what a user does far more often.

## What the pilot cannot test, and why it is recorded rather than hidden

**Markup over the basis rate does not exist in the application.** Confirmed by inspection: the
only matches for `margin` in `backend/app/modules/` are CSS. There is no field recording the
markup applied, no calculation, no rule (standard, minimum, by equipment or customer), and
therefore no deviation workflow or approval. The system records the rates collected and which was
chosen, and separately records what was quoted, but nothing connects the two.

This is broader than the "Margin/authority/terms approval rules" line already in
`DEFERRED_REQUIREMENTS.md`, which concerns approval: the gap starts earlier, because the markup
cannot be recorded at all, so there is nothing for an approval rule to act on. Recorded as its own
entry, and stated in the tester-facing data sheet so its absence is not reported as a defect.

## A known limitation found while building this

**A seed that fails partway leaves its records behind with no run id to clean up with**, because
the run id is only returned on success. This was hit twice during development and left 33 accounts
and 10 leads in the database, invisible to any manifest-driven cleanup. The recovery — find them by
the `UAT-` prefix — is documented in the runbook. The proper fix is to save the manifest as records
are created rather than only at the end; it is recorded rather than silently endured.

## Third review: the closure went too wide, and other corrections

A third review returned eight findings, three P1. The closure fixed under-deletion and introduced
over-deletion, which is the trade a wider net always risks.

**The worst: reachability was treated as ownership.** The closure followed Opportunity -> Account
for *every* owned Opportunity. Review reproduced one run deleting another run's pre-existing
Account, simply because its own Opportunity had been repaired onto it. An Account is a **parent**
several runs may point at, not a child of our Opportunity.

The previous, narrower code had this right - it followed that edge only for Opportunities derived
from our own Leads. Generalising it into the closure lost a constraint that already existed. The
edge is now sourced from the Lead and joined through `source_lead_id`, restricting it to the
conversion case where the Account genuinely was created by us.

Owner decision, 10 September 2026, on the direction that remains wide: **cascade downward without
asking.** "If the enquiry is being deleted, why even ask - they can be deleted." So anything
hanging off a record we own goes with it, including an Opportunity someone repaired onto an
Account we own. A confirmation route is added only if that ever causes a problem.

**And the pilot no longer depends on any of this.** The pilot gets its own stack and database, so
a reset there is a rebuild, not a surgical deletion - no ownership question arises at all.
Targeted cleanup remains for the automated test suite, which shares a database and cannot rebuild.

### The other corrections

- **The storage pre-check re-hid the defect it was meant to fix.** Round 2 established that the
  local provider returns False from `exists()` for a key it refuses. Round 2's fix then used
  `exists()` as a pre-check and read False as "nothing here to leak" - so a real file behind an
  invalid key was skipped, survived, and was counted as deleted. `delete` is now always called
  (it raises where `exists` hides). An `exists()` call remains, but only to record whether there
  was an object to remove so the count reflects real deletions; it gates nothing. This note
  previously said there was "no pre-check at all", which was untrue of the code it described.

  **Still trusted, and unverified:** `exists()` answering truthfully. A provider returning False
  both before and after a deletion that did nothing yields a clean result with the file intact.
  That violates the storage contract, but nothing here tests provider conformance.
- **`documents_storage_deleted` counted things it had not deleted** - metadata-only rows and keys
  that held nothing - while the CLI prints every count as something removed. It now counts only
  objects actually removed.
- **A global orphan poisoned every run's verdict.** One unattributable orphaned quote document
  made every subsequent reset report residue. It is now surfaced separately and excluded from
  `residue_clear`, because a warning that fires every time is one an operator learns to ignore.
- **`status` compared unequal sets.** `found` was counted before the closure expanded the ids and
  `expected` after, so a run with one live-created offer reported `all_present=False` with both
  offers present. The closure now runs before anything is counted.
- **A damaged manifest was partly acted on.** A manifest with one good anchor and one malformed
  entry cleaned up its readable half and exited successfully. Malformed records are now refused;
  legitimately sparse ones (a closed Lead has no Account) are still fine.
- **The E2E failure message advised a recovery that cannot work** - re-running cleanup to find
  keys whose rows are already gone. Corrected to say the keys exist only in that output.
- **Four helper functions the closure replaced were left behind as dead code**, referenced only in
  each other's docstrings. Removed: in a deletion path, a plausible-looking unused function is a
  trap for whoever reads it next.

### One item accepted, and one habit named

The READ COMMITTED discovery/delete race is still not addressed, for the reasons recorded above,
and matters less now the pilot rebuilds rather than deletes.

The stale-comment finding was the **fourth instance in this package** of prose outliving the
behaviour it described. It is named here rather than quietly corrected each time, because the
pattern is the problem, not the individual comments.

## Second review: the discovery approach was wrong, not just incomplete

A second independent review of `cleanup.py` and `status.py` returned six findings, five of them
P1, and failed four of six categories. The findings mattered less than what they had in common.

**Every defect across both reviews had the same shape: a relationship followed one level and no
further.** Leads found their converted Opportunities, but those Opportunities did not find their
own offers. Offers found their related offers, but an Opportunity did not find an ordinary offer
raised on it later. Offers found their quote documents, but interactions did not find their
attached documents. Ten findings over two rounds, each fix leaving another level behind it.

That is not a series of oversights, it is a wrong approach: `cleanup.py` was reimplementing
referential integrity by hand, one special case at a time, over a graph the database does not
enforce. **Discovery is therefore rewritten as a closure** - `_OWNERSHIP_EDGES` declares each
relationship once, and `_expand_ownership_closure` follows all of them repeatedly until the owned
set stops growing. Adding a relationship is now one entry in a table rather than a new special
case in the middle of a delete sequence, and the whole defect class is answered rather than its
current instances.

The trade-off is stated at the definition: a wider closure reaches records a pilot user attached
to seeded data - an Opportunity repaired onto a seeded Account, an offer raised on a seeded
Opportunity. Those should be removed; they exist only because the practice data existed, and not
reaching them either orphaned them or aborted the reset on a foreign key. The boundary is that
nothing is reached except through an actual relationship to something the run owns, which
`test_ownership_closure_settles_and_does_not_reach_unrelated_records` holds in place.

### `status` could certify a failed reset as clean

The worst single finding, and self-defeating. The residue check added in the first correction pass
joined through `crm_commercial_offer` to find quote documents — so once the offer was deleted the
join matched nothing, and an **orphaned** quote document, the only case worth detecting, was
invisible to the check written to detect it. Its document and interaction checks used manifest ids
only, so anything hanging off a record discovered during cleanup was never examined.

Both were addressed the same way: `status` runs the **same closure** cleanup runs, so the two
consider identical record sets by construction rather than by two lists kept in step by hand, and
asks about global quote-document orphans directly. It also reports lead activities and audit-row
residue.

**That fix is incomplete, and an earlier version of this paragraph claimed otherwise.** The
closure recomputes from surviving relationships. Once cleanup has deleted a record the manifest
never named — a derived offer, say — its id cannot be rediscovered afterwards, so anything still
attached to it is invisible to `status`. Round 4 fault-injected exactly that: a surviving
`document_metadata` row on such an offer, with `status` returning `all_absent=True` and
`residue_clear=True`.

So **`status` does not certify that a targeted cleanup left nothing behind**, and must not be
described as doing so. What it does is check the records it can still identify, and report
database-wide quote-document orphans. Certifying the rest would need the expanded ids persisted
before deletion, or an orphan signal for each record type that does not depend on the parent
surviving. Neither is done here.

On the pilot this does not arise: that database is rebuilt rather than cleaned, so nothing needs
certifying. For the automated test suite it means residue can accumulate unnoticed in a shared
development database — untidy, not dangerous.

### The storage recovery claim was false

The first correction pass moved byte deletion after the commit and justified it in a comment
saying the residual risk became recoverable because "a later sweep can still find them from the
storage provider". **There is no such sweep.** After the commit the keys exist only in memory, the
provider interface cannot list objects, and a second cleanup finds no rows to work from.

This is the third time in two packages that a claim was asserted in prose that the code did not
support - after Slice 9E's "approval is recorded" footer and its compensating-commit comment. A
storage failure now **raises**, carrying the orphaned keys in the message, because by the time it
is known the rows are committed away and that message is the only surviving record of them. The
existence check is taken before and after the delete, because `exists()` returning false on its
own proves nothing: the local provider reports false for a key it refused as invalid, so a
rejected deletion and a successful one look identical from the after-check alone.

The CLI printed `documents_storage_failed: 1` as **"1 deleted"** and exited 0. Failures are no
longer a count in that report at all.

### The type-blind matching argument was rebutted, and conceded

The first pass declined to filter on `linked_record_type`, arguing that enumerating types risks a
future link type escaping cleanup. Review's counter: adding a new **owned** type already requires
updating discovery, so the enumeration is the same maintenance rather than extra - while id-only
matching in a shared database promises exact deletion on `uuid4` luck across tables sharing no
constraint. Documents and interactions are now matched on `(linked_record_type, public_id)` pairs,
with both Account spellings included because the two modules genuinely disagree on that vocabulary.

### Accepted and not fixed

The READ COMMITTED discovery/delete race is real: ids are selected, then matching rows deleted,
and a concurrent commit in between can slip through. It is not addressed here. A pilot reset is a
single operator action against a database nobody else is writing to, and the alternatives -
`SERIALIZABLE`, or advisory locks across polymorphic public-id relationships that have no foreign
keys - are disproportionate to a test-data tool. Recorded as a known limitation rather than
silently accepted.

## Corrections from the deletion-path review

The cleanup change was reviewed adversarially before hand-off, on the grounds that it deletes from
a real database. Four defects were found, all on the under-deletion side plus one dangerous
side-effect ordering. Recorded because each is the same shape as the defect this package exists to
fix, one level further down — which is the reason the review was worth commissioning.

**Bytes were deleted before the commit.** The original ordering deleted each stored file, then
continued through eight more DELETEs before the single `db.commit()`. Any failure in between —
including the accounts DELETE this file's own comment describes as the one that fails loudly —
rolls the transaction back and restores every row, but nothing restores a file. That leaves live
`document_metadata` rows whose `storage_key` points at nothing and whose downloads fail: cleanup
destroying data it was not asked to touch. `delete_stored_document_object`'s own docstring
describes it as compensation for a transaction that did **not** commit, so this inverted its
intended use. Byte deletion now runs after the commit returns, which turns the residual risk into
the recoverable direction (rows gone, some bytes remaining) rather than the unrecoverable one.

**A document attached to an interaction was never found, while the interaction was deleted.**
`interaction` is a first-class document link type with its own extra content permission, so a
pilot user attaching a file to a logged call is ordinary use. Its document hangs off the
interaction's public id, which the discovery set did not contain. Fixed by selecting the owned
interaction ids first and folding them into the document scope.

**Audit rows for interactions and quote documents survived.** Both write their `business_event`
keyed by their **own** public id, not the linked record's. The quote-document case was worse: the
rows were deleted without first capturing their ids, so the orphaned events could never have been
found from the database afterwards. Both id sets are now collected before anything is deleted.

**Byte deletion could not fail loudly.** `delete_stored_document_object` swallows exceptions by
design — correct for its original use, wrong as a primary deletion path, where a storage provider
that is down would produce a clean "cleanup succeeded" with every file still present. Existence is
now checked afterwards and failures reported as `documents_storage_failed`.

One recommendation was **declined**: adding `AND linked_record_type IN (...)` to the document and
interaction deletes as defence in depth. Every public id involved is a `uuid4`, so a cross-type
collision is not reachable, and enumerating the permitted types would mean a link type added later
silently escapes cleanup — reintroducing exactly this package's defect class in the name of
hardening. The reasoning is recorded at the call site.

## Verification

- `backend/tests/test_smoke_data_harness.py` — **61 passed** (38 pre-existing, 23 new).
- Full backend regression — **1304 passed, 0 failed** (1281 at the Slice 9E baseline, plus 23).
- The harness suite is self-cleaning: 0 database residue and 0 files in the document store after
  a full run, verified after the storage tests were corrected to remove files whose rows they had
  deliberately committed away.
- The interaction-attachment correction was proven non-vacuous by reverting the fix and watching
  the test fail, then restoring it.
- The three cleanup regression tests each **failed first**, in the two distinct modes above, and
  passed only after the fix.
- The seeded dataset was verified for substance, not just row counts: a **217-character legal
  name** rendered into a generated quotation; a site address using its second line with a district
  differing from its city; **four GSTINs sharing one PAN** across four states; version 1 superseded
  by version 2 with each keeping its own status; and the unpriced-line quotation reading **"Not
  fully priced"** in its total row while still showing the priced line's own amount.
- Cleanup of the full dataset removed 10 accounts, 12 offers, 27 lines, 10 quotations, 10
  documents, 10 interactions, 18 GSTINs, 11 addresses, 3 Work Orders and 216 business events,
  leaving **zero files on disk** in the document store.
- Every command printed in the runbook was executed as written.

## Deliberately not done

No Playwright coverage of the UAT dataset. The pilot is a human exercise; adding browser
automation over practice data would cost more than it protects, and the existing E2E suite already
covers the flows. No dedicated PowerShell wrapper (`uat-data.ps1`) — `scripts/smoke-data.ps1`
already exposes seed/status/cleanup for any scenario, and a second wrapper would be maintenance
without capability. No changes to the UI, the pricing gate, or anything else queued for the UI
cleanup package.
