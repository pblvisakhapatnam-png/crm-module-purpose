# PF-1A-E3 - Governed Authority Configuration, Publication and Self-Escalation Prevention

## Status

Implemented. Backend only. Predecessor: PF-1A-E2-B (`20260904_0031`). Migration: `20260906_0032`.
Governing decisions: ADR-033 (parameter-driven authority configuration), ADR-032 (HR reference
source), `ORA-001`.

## Objective

The smallest coherent governed lifecycle that can change published Business Authority
configuration safely, on top of the read-only PF-1A-E2-B store, implementing ADR-033's
preventive self-escalation invariant.

## Model

One governed **Configuration Change** record spans all four configurable object families
(`BUSINESS_AUTHORITY`, `BUSINESS_AUTHORITY_ROLE`, `BUSINESS_AUTHORITY_RULE`,
`BUSINESS_AUTHORITY_ASSIGNMENT`) and all three change types (`CREATE`, `UPDATE`, `DEACTIVATE`).
Four ad-hoc per-family workflows is exactly the defect ADR-033 correction C2-2 removes. An
append-only evaluation record captures every recomputation, at every stage.

Lifecycle: `PENDING -> ACTIVE` or `PENDING -> REJECTED`, both terminal. A `REJECTED` change is
retained forever as an audit record; it is never deleted and can never activate.

## The invariant

**No stored risk boolean is ever read as final.** The `proposal_time_*` columns are
preliminary/audit evidence of what was believed when the change was raised. Authorization
recomputes risk against current state. Activation recomputes it again, inside the same
transaction that publishes. A change that was ordinary when raised and ordinary when authorized
does not activate as ordinary once it has become self-affecting or protected.

Independence (`authorized_by != initiated_by`) is mandatory for a self-affecting privilege
increase and for every protected-meta-authority-affecting change. Ordinary, unrelated,
non-protected administration remains single-person, deliberately: ADR-033 warns explicitly
against turning every configuration edit into a two-person process.

**A successful authorization is one bound fact, not a combination.** The authorizer's identity
and the identity of the exact successful `AUTHORIZATION` evaluation that established it
(`authorized_evaluation_id`) are written together, in one statement, or not at all. Activation
loads *that* evaluation and no other, and verifies its stage, its outcome, its
`authorization_satisfied` verdict and its acting identities before it counts as an
authorization; anything unverifiable refuses with `AUTHORIZATION_EVIDENCE_UNVERIFIABLE`.

Reading "the most recent `AUTHORIZATION` evaluation" instead would be unsafe, and not
theoretically: a later **refused** attempt legitimately records its own evaluation against its
own freshly recomputed context, so activation could otherwise pair an approver from one context
with a dependency fingerprint and risk verdict from another - an authorization that never
happened, assembled from two halves that separately did. A refusal therefore never overwrites,
refreshes or re-points the authorizer fields. A later *successful* authorization replaces all of
them together, which is the ordinary re-authorization path a drifted change must take.

## Conservatism, in three named directions

- **Protection is over-inclusive.** Any non-retracted version asserting
  `is_protected_meta_authority`, or a proposal payload asserting it, makes the object
  protected - so *clearing* the flag is itself a protected change.
- **Privilege increase is assumed unless proven otherwise.** Only a `DEACTIVATE`, and an
  `UPDATE` whose published content is byte-identical **and** whose declared temporal scope is
  unchanged or strictly narrowed, are provably non-increasing. Scope and threshold semantics
  belong to the PF-1A-E2-A kernel and are not re-derived here.
- **Temporal scope is part of what a publication grants.** An otherwise-identical `UPDATE` that
  moves `effective_from` earlier, moves `declared_effective_to` later, or replaces a finite
  declared end with no end at all, grants the same authority over time it did not previously
  cover. All three are privilege increases, and the finite-to-unbounded case is the largest and
  the easiest to mistake for housekeeping, because not one payload field changes. Only a
  formally proven narrowing - later-or-equal start **and** earlier-or-equal end, payload and
  active semantics otherwise unchanged - is non-increasing; anything incomparable (an absent
  published start, a non-timestamp value, a naive/aware mixture) fails closed as broadening,
  because an unprovable narrowing is not a narrowing.
- **Linkage uses the state the PF-1A-E2-A kernel says is current, not "ever" and not "most
  recently written."** An assignment that has been deactivated must stop making its former holder
  self-affected, or ordinary administration would become permanently two-person for anyone who
  ever held anything - but a version that is genuinely **effective now** must never be erased by a
  later-published successor that is future-dated, inactive or reassigned. See "The authority
  graph" below.

**None of these is a publication-validity rule, and none may be read as one.** They decide *how
many people must agree*. Whether the resulting immutable lineage may be written at all is a
separate question with a separate answer, asked of the unchanged kernel immediately before
publication - see "Prospective lineage validation" below. A proven narrowing is legitimately
single-person **and** can legitimately be unpublishable.

## The authority graph

**The graph is derived by the unchanged PF-1A-E2-A kernel. PF-1A-E3 does not rank rows itself.**

An earlier revision of this package carried the store's physical append order on each row and
treated *the latest non-retracted row* as the object's current state. That is a second, quieter
notion of currency, and it disagrees with the kernel's in both directions. The disagreement is
exploitable rather than academic:

- publish a **future-effective inactive** successor to your own assignment, and a
  publication-order view concludes you hold nothing today - so your own privilege increase stops
  being self-affecting and becomes a **single-person** change;
- publish a **future-effective** successor to a rule, and the same view concludes the role it
  grants from carries no protected meta-authority today - so editing that role stops being a
  protected change.

`configuration_policy.derive_effective_state` therefore assembles **complete** lineage material -
every version and every retraction assertion, unfiltered - and hands it to
`material.check_material_well_formed` and then `lineage.evaluate_lineage`:

```text
validate retraction / correction / provenance assertions   kernel
derive the CURRENT ASSERTED lineage                        kernel
derive asserted intervals / closure                        kernel
select the SINGLE version effective at as_of               kernel
then apply active_flag / grant eligibility                 PF-1A-E3
```

Two different answers come back, and conflating them is what the correction removes:

- **the effective version** - the single one effective at `as_of` - answers *what does this object
  mean right now*, and is what every linkage, reference and grant question uses;
- **the authoritative predecessor** - the temporally last version of the same validated current
  asserted lineage - answers *what would an `UPDATE` or `DEACTIVATE` supersede*, and is what the
  expected-predecessor check and the privilege-increase comparison use.

They coincide most of the time. Where they do not - a lapsed interval has a predecessor and no
effective version; a future-effective successor is the predecessor while an earlier version is
still effective - a reference asserted by **either** counts, because losing either one
under-computes risk.

**Anything the kernel cannot establish fails the whole governed action closed.** A contradictory
lineage, an ambiguous version at `as_of`, invalid provenance or ill-formed material puts the
object in `AuthorityContext.unresolved`, and every stage then refuses with
`AUTHORITY_CONTEXT_UNAVAILABLE`. It is never read as "this object has nothing", which is the
reading that would silently under-compute risk.

## Eligibility

Eligibility goes through the **unchanged PF-1A-E2-A kernel**. The service resolves each
protected candidate authority code for the acting actor, then dereferences the exact authority
version the kernel cited and reads the data-driven `is_protected_meta_authority` flag off it.
The candidate-code list is a deliberately over-inclusive read that decides nothing; the strict
answer comes from the cited version.

A kernel `FAIL_CLOSED`, an unresolvable actor-person link, an undereferenceable cited version,
or an unresolvable position incumbency makes the whole governed action fail closed with
`AUTHORITY_CONTEXT_UNAVAILABLE`. It never degrades to "not eligible, carry on".

There is no literal administration-code constant anywhere in the production package; a test
asserts its absence, and a decoy authority carrying that code with the flag *false* proves the
classification is data-driven.

## Publication

### The governance-wide serialization boundary

Activation takes **one non-blocking, transaction-scoped governance-wide advisory lock first,
before any read**. Every read the transaction performs - the Configuration Change row, the
published store, the protected candidate codes, the kernel's own reads, the expected-predecessor
lookup, the duplicate check and the bound authorization evidence - happens after it, and it is
held through publication until the same commit or rollback that decides whether anything was
published.

Governance-wide, not merely per-object, because **a per-object lock cannot see the pair that
matters**. Two activations of two *different* stable objects can be mutually risk-dependent -
two assignments that would duplicate each other, a rule and the authority it grants from - and
they take two different lock keys, so under `READ COMMITTED` each could validate against a
snapshot taken before the other published, and both would publish. Governed configuration
administration is a rare, deliberate, low-frequency path, so serializing it whole costs nothing
worth protecting. The `FOR UPDATE` row lock and the per-object advisory lock are retained as
secondary defence and for the precise contention evidence they give.

**What this boundary does not do:** it serializes governed activation against *this
application's database*. It does not serialize any external HR/organisation or actor-person
system, whose state this package only reads through the authoritative providers. That remains
handled by failing closed - the production composition refuses to compose while those providers
are absent, and an unresolvable dependency refuses the governed action outright.

### The published version

Activation recomputes risk, checks the expected predecessor against the kernel-derived
authoritative predecessor, re-checks references and duplication, checks that its own recorded
publication time does not precede the allocation anchor's, **asks the unchanged kernel whether the
resulting lineage would still be valid** (next section), then inserts exactly one immutable
version into the existing PF-1A-E2-B store with
`publication_reference_type = CONFIGURATION_CHANGE` and `publication_reference_id` = the
Configuration Change id. `corrects_object_version` is always NULL: PF-1A-E3 implements
publication and deactivation, not correction or retraction. Failure before commit leaves no
partial publication and no false `ACTIVE`.

The row that is validated and the row that is written are **one object**. Activation constructs
the exact `PublishedRow` it would append - identity, interval, active flag, payload, provenance and
recorded instant - and hands that same object to the prospective evaluation and then to the store's
writer, which takes the whole row rather than reassembling it from loose arguments. Two
constructions that merely agree today can diverge later and publish something no kernel approved.
The writer still refuses structurally, rather than silently rewriting, if a caller ever presents a
correction assertion or a provenance other than `CONFIGURATION_CHANGE`.

### Prospective lineage validation: an append that would be defective is never written

**PF-1A-E3's `UPDATE` appends; it does not retract and republish.** A predecessor carrying a finite
`declared_effective_to` therefore stays asserted beside the new version, and where the new version
starts *before* that declared end, PF-1A-E2-A 11.4 reads the pair as an **explicit overlap** and
fails the whole object's resolution closed. A strictly narrower interval is the reachable case, and
it is exactly the shape the privilege rule correctly permits as non-increasing.

Two questions are involved and neither answers the other:

```text
does this change GRANT MORE than what it supersedes?   classify_risk        -> how many people
could the RESULTING LINEAGE be published at all?       prospective check    -> whether anything
                                                                                may be written
```

A narrowing legitimately answers *no* to the first and can still be refused by the second. The
correct response is to refuse the publication, **not** to reclassify every narrowing as a privilege
increase - that would demand a second person to *reduce* someone's own authority, which is
conservative in the useless direction ADR-033 warns about, and would still not stop the defective
append.

So, inside the same governance-wide boundary, after the predecessor, the allocation anchor and the
recorded instant have established the **exact** immutable version to be appended, and **before**
that version is inserted or the Configuration Change moves to `ACTIVE`,
`configuration_policy.prospective_publication_defects` assembles the object's **complete
prospective material** - every existing published version, every existing retraction assertion, and
the proposed version exactly as it would be written - and hands it to the unchanged
`material.check_material_well_formed` and `lineage.evaluate_lineage`. Any defect at all refuses with
`PUBLICATION_LINEAGE_INVALID`: no version row, no `ACTIVE`, prior lineage untouched, and the refusal
recorded as ordinary governance evidence on the `PENDING` change.

**There is deliberately no local "do these intervals overlap?" rule.** The security goal is broader
than the one observed shape: a partial local copy would pass every defect class it did not
anticipate - duplicate starts, invalid provenance, a recorded time that decreases across the version
order, an unretracted correction target, material that is not a published-version record at all -
and would be a second copy of semantics this package has already been corrected once for owning.

The check applies identically to `CREATE`, `UPDATE` and `DEACTIVATE`. A single-version `CREATE`
ordinarily validates; a `DEACTIVATE` is provably non-increasing and would be an easy exemption to
make, and is deliberately not one, because the append it writes can leave exactly the same
overlapping lineage. `PUBLICATION_TIMESTAMP_NOT_MONOTONIC` is retained and is still asserted
*first*, even though the prospective evaluation would also detect that failure: the specific check
names its cause precisely, and a reader of a refused evaluation is better served by "the recorded
clock cannot be published behind" than by a general "the resulting lineage would be defective".

Why this matters more than a failed resolution: because the authority graph is
whole-configuration, an object whose lineage the kernel cannot establish blocks **every** governed
action, not only actions about that object - and **PF-1A-E3 has no correction or retraction path**,
so a defective lineage it published could not be repaired by anything this package offers.

### `object_version`: opaque **and** lexicographically ordered

Two PF-1A-E2 invariants apply at once, and satisfying only one of them is a real regression.

- **It is opaque.** A version published before PF-1A-E3 existed, or by any other authorized
  mechanism, legitimately reads `v1`, a UUID, or anything else. **PF-1A-E3 parses no version
  identifier, anywhere.** Any numeric reading would make every legitimately non-numeric
  predecessor permanently unmanageable, because no `UPDATE` could ever state a matching expected
  predecessor.
- **It is lexicographically ordered.** `lineage.py` states in terms that `object_version` is
  compared lexicographically and that *a publisher must use a lexicographically ordered version
  identity*; the kernel requires `published_at` to be non-decreasing in that order (11.8.3) and
  uses the same ordering as a sort key (15.5). A merely unique, unordered identifier is **not
  sufficient**: a later publication that happened to sort before an earlier one is read by the
  unchanged kernel as contradictory provenance, and an otherwise clean `DENY` becomes
  `DENY + FAIL_CLOSED`.

### The predecessor and the allocation anchor are two different values

They were previously one, and that was wrong in both directions.

**The expected predecessor** (`previous_object_version_expected`, required for `UPDATE` and
`DEACTIVATE`) is compared against the **authoritative predecessor derived above** - the temporally
last version of the *validated current asserted lineage*. A **retracted** version is not an answer
to that question however great its spelling: a valid retraction removes its target from the
current asserted lineage, so an `UPDATE` naming it is refused with `LINEAGE_PRECONDITION_FAILED`
even while it remains the object's lexicographic maximum. If the predecessor is unresolved,
dangling, contradictory or temporally ambiguous under E2 semantics, the activation fails closed.

**The allocation anchor** is the object's **all-time lexicographic maximum, retracted versions
included**, read separately by `configuration_repository.allocation_anchor`. It has to span
retracted rows because the kernel validates provenance across *every* published version, so a new
identity must sort after all of them. Anchoring the allocation on the predecessor instead would,
whenever the maximum has been retracted, mint an identity that sorts **before** a stored row -
publishing exactly the contradictory provenance the ordering rule exists to prevent.

The maximum is taken in Python with `max()`, the same comparison the kernel uses, never by a SQL
`ORDER BY` over the text column, because that would apply the database collation and the store
could then believe a different identity was greatest from the one the kernel does.

**The new identity** is allocated by `allocate_object_version(allocation_anchor, change_id)` as

```text
new = anchor + non-empty suffix        (suffix = "e3" + 16 hex chars, from the change id)
```

so the anchor is a **proper prefix** of the result. Lexicographic comparison places a proper
prefix strictly before its extension, so `new > anchor` for *any* anchor whatever its syntax,
and since `anchor >= v` for every existing version and the ordering is total, `new > v` for all
of them. **The proof uses concatenation only** - not one character of the anchor is inspected,
classified or interpreted - so both invariants hold simultaneously.

Uniqueness comes from two independent directions: allocation happens inside the governance-wide
publication boundary, so no concurrent governed allocator can observe the same anchor, and the
suffix derives from the unique Configuration Change identity. The store's own
`(object_id, object_version)` key is the structural backstop.

### `published_at` must not go backwards either

Ordering `object_version` is only half of PF-1A-E2-A 11.8.3: the other half is that `published_at`
is **non-decreasing in that order**. Because a newly minted identity always sorts *after* the
all-time anchor, recording it with an **earlier** `published_at` than the anchor's would publish
provenance the unchanged kernel reads as contradictory - turning a later, otherwise clean
resolution `FAIL_CLOSED`. A clock rollback, a restored backup or a mis-set container clock
produces exactly that, with every other rule still satisfied.

Activation therefore compares its own captured instant against the anchor's recorded
`published_at`, **inside the same governance-wide boundary that read the anchor**, and refuses
with `PUBLICATION_TIMESTAMP_NOT_MONOTONIC` before writing the version row or moving the change to
`ACTIVE`. Equality passes, because the rule is non-decreasing rather than strictly increasing. An
absent or non-UTC-normalized anchor timestamp refuses too. **The clock is never advanced,
substituted or re-read to get past the check** - doing so would manufacture the very conformance
being verified. The floor follows the all-time anchor even when that anchor has been retracted,
because the kernel validates provenance across retracted versions as well.

**Replay is prevented by the governed lifecycle, not by the allocator.** An allocator anchored on
the current maximum would, on a second run, allocate a different longer identity rather than
colliding, so the control is the `PENDING -> ACTIVE` transition taken under the change row's own
lock inside the publishing transaction; a second activation is refused with
`LIFECYCLE_STATE_INVALID`.

Identifiers grow by the suffix width per publication. That is accepted deliberately: governed
configuration change is a rare administrative act, the column is `Text`, and **no fixed-width
scheme can be proven greater than an arbitrary opaque predecessor** - a predecessor of `~~~~~~~~`
defeats any bounded alphabet without reading its syntax, which is precisely what the opacity
invariant forbids.

**None of this is an effectiveness rule.** Ordering serves lineage validity and the
expected-predecessor check; whether a version grants anything at a given instant remains the
PF-1A-E2-A kernel's question.

## Downgrade

`20260906_0032`'s downgrade refuses once any governed Configuration Change, evaluation record or
`CONFIGURATION_CHANGE`-provenance published version exists. It sits above `20260904_0031`, so
`downgrade base` cannot reach the destructive authority-store downgrade beneath it. An empty
development database still downgrades intentionally.

**The locks come before the count, and that order is the whole point.** The guard first acquires
`ACCESS EXCLUSIVE` on every table a governed activation can write - the four PF-1A-E2-B published
version tables, then the two PF-1A-E3 lifecycle tables, in that fixed documented order so two
concurrent downgrades cannot deadlock each other - and PostgreSQL holds those locks until the
migration transaction ends. Counting first and locking later would leave a window in which a
concurrent activation commits after it was counted and before `DROP` acquired its lock, so a
downgrade could certify "no governed state" and then destroy some. The lock set is deliberately
wider than the tables this revision drops, because one governed activation writes to both halves
in one transaction.

## Known residual risk, recorded rather than hidden

**A published lineage the kernel cannot establish now blocks every governed action, not only
actions about that object.** That is the fail-closed direction and is deliberate: the authority
graph is whole-configuration, so an object whose currency cannot be determined leaves the graph
undetermined, and guessing would be the under-computation this correction removes. The
operational consequence is real, though: one contradictory object stops all governed
configuration administration until it is corrected.

**PF-1A-E3 cannot itself correct such a lineage**, because it implements publication and
deactivation only - not correction or retraction. Repair requires another authorized mechanism,
which does not exist yet.

**PF-1A-E3 can no longer publish a lineage the unchanged kernel would immediately classify as
defective**, in that shape or any other: see "Prospective lineage validation" above. An earlier
revision of this package recorded that behaviour as an accepted residual risk, on the grounds that
it failed closed rather than open. That reasoning was wrong in one important respect, and the
correction is recorded here rather than the earlier wording being quietly deleted: the append is
*permanent*, PF-1A-E3 offers no correction or retraction path to undo it, and because the authority
graph is whole-configuration the resulting object blocks **all** governed administration - so the
"fails closed" property describes an outage the package itself could not clear, not a contained
failure.

**What remains genuinely open is repair, not prevention.** The narrowing that the privilege rule
permits is still not *expressible* as a single governed publication where the predecessor declares
a finite end: the activation is refused, and the administrator has no PF-1A-E3 action that closes
the predecessor explicitly. An `UPDATE` model that supersedes by retract-then-republish, or a
correction/retraction authorization path, would make that case expressible. Both are design
decisions beyond this package's scope, and neither is half-attempted here. Refusing is the safe
half of the problem and is what this package owes; expressing the change is the other half and is
deferred explicitly.

## Out of scope

No HTTP route, request/response schema or admin UI. No production actor-person provider and no
production HR/organisation provider - the governed production seam therefore **refuses to
compose**, so PF-1A-E3 delivers no production-callable governed configuration service. No seed,
default or fixture that could become a production bootstrap. **Q-10 (who first holds the
protected meta-authority) remains open and is not answered here.**

**The frontend half, which activation must not leave behind** (added 7 October 2026, TB-1 TB1-804).
The pages decide which buttons and forms to offer from 47 role lists copied from the backend's
grants, and `/api/auth/me` returns role codes, not permission codes. That holds only while a grant
changes with a code release. Before any grant is changed through governed configuration - PF-1A
activation - `/api/auth/me` must return the user's permission codes and the pages must ask by
permission, or they will offer actions the server refuses and hide ones it allows. The backend stays
authoritative either way. TB-1's corrective package CS-10 (part c) holds the work.
