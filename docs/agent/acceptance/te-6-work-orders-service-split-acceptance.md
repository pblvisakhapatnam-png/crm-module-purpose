# TE-6 Acceptance - Splitting the Work Orders service

Technical-enablement package. No behaviour, API, route, permission, business event, schema, migration
or frontend screen changed; the frozen Accepted Offer to Work Order handoff contract is unchanged. A
screen check is not required - nothing a user can see changed - and was not done.

Changed: `backend/app/modules/work_orders/service.py` (now a re-export), the new package
`backend/app/modules/work_orders/services/`, four test files (monkeypatch targets and one
introspection scan; no assertion), one new test file pinning the module's public names, and
documentation. Detail, reasons and departures from the brief:
`docs/agent/technical-enablement/TE_6_WORK_ORDERS_SERVICE_SPLIT.md`, "As built".

**Status: committed as `79f8342` and merged through PR #66 as `dc0d119`, 23 September 2026. Review
rounds 1 to 4 corrected (round 4 authorized beyond the cap); the owner chose to commit without a fifth
round, so there is no ACCEPTED verdict.** The proof scripts, their outputs and the review verdicts are
kept in `docs/agent/technical-enablement/te-6-proof-scripts/`.

## Automated checks

| Check | Command | Baseline (`1d7515f`) | Candidate |
| --- | --- | --- | --- |
| Full backend regression | `docker compose exec backend pytest -q` | 2015 passed | **2019 passed, 0 failed** (the 2015 plus the 4 below) |
| Public names of `service` | `pytest tests/test_te6_work_orders_service_surface.py` | - | **4 passed** (new) |
| Work Order test files (ten) | `pytest` on the ten files | 725 | **725 passed** (after the split) |
| Part 3 rules / routes | `pytest tests/test_slice_7d_part_3_contract_{rules,period}.py` | 47 / 128 | 47 / 128 |
| Frontend | `npm run typecheck`, `npm test`, `npm run build` | - | clean / **188 passed** / built |
| E2E | `pwsh -NoProfile -File scripts/run-e2e.ps1` | - | **17 passed, 9 skipped, 0 failed**; cleanup succeeded |
| Repository checks | `check_tracked_secrets.py`, `validate_contract_fixtures.py`, `unittest discover -s scripts/tests`, `git diff --check` | - | all clean |
| Frozen handoff contract | `sha256sum` | `70debad7...0cb0b86a` | unchanged |
| Alembic head | - | `20260908_0039` | unchanged; no migration |

## Equivalence

| Proof | What it shows | Result |
| --- | --- | --- |
| Text comparison | Every one of the 104 original definitions exists once under `services/`, byte-identical unless declared | 87 identical, 14 rollback-helper, 3 rewritten, 10 new, all declared |
| Rollback helper | Each write's AST equals the original's with only its outer `try/except Exception: db.rollback(); raise` made `with _rollback_on_error(db):` | 14 of 14 (15 of 15 before the copy was split) |
| Pure rewrites | `_normalize_billing_terms` and `_period_missing_items` against the originals on generated inputs | 300,000 each, all identical; 48 of 49 refusal messages and 16 of 16 missing codes reached |
| Copy | The original and new copy against the same recording fakes | 21 scenarios, identical traces and results |
| Harnesses can fail | Six deliberately broken versions | 6 of 6 reported |
| Import bindings (static) | Every name a new module imports is imported as the original imported it, or is a moved or declared definition from `common` | 318 of 318; no decorator, dynamic lookup, non-constant default or dunder attribute; 7 declared `getattr`/`hasattr` sites, each on a payload or event parameter, and any other fails; a same-named import from another module, a planted decorator, a `__globals__` lookup and a `getattr` on a function are each reported |
| Global lookups (runtime) | Every global every new function loads resolves to the original's object, its moved definition, its new definition, or an unshadowed builtin; module constants equal | 665 lookups in 96 functions; 9 constants; 5 of 5 deliberate rebinds reported |
| Generator = candidate | The package regenerated from the base commit's `service.py` | all 8 files byte-identical |
| Exported surface | Every name any other file takes from `service` - through the service or any package on its path, by any import form including relative ones, at any scope - is exported; anything unresolvable (a dunder other than `__all__`/`__name__`/`__file__`/`__doc__`, the module as a value, a computed `import_module`...) fails unless declared at its exact site; `__all__` = the 40 names the original defined | 37 taken, 40 exported; dynamic importers (`importlib`, `sys.modules`, `builtins`, `pkgutil`, `runpy`) tracked by what they are, `eval`/`exec`/`compile`/`globals()` and path fragments in strings refused; 16 declared sites, each with its reason, and a stale one fails; 49 of 49 planted forms reported |
| Surface against the original | `vars(original)` compared with the new module | 261 public before = 40 defined + 221 imported; all 40 present as their moved definitions, nothing else exposed; the 221 not re-exported by the owner's decision |

The one refusal message not reached is a defensive check in `_check_part_2_terms`, which this package
did not change and which earlier checks make unreachable, as its own comment says.

## Non-vacuity of the test changes

Each changed test was run in its original form against the split.

| Test | Original target | Observed failure |
| --- | --- | --- |
| 7C: concurrent save; failure building the response | patch on `service` | `AttributeError`: `service` no longer holds `list_work_order_line_detail_rows` |
| 7D: failure building the response; concurrent update | patch on `service` | `AttributeError`: `service` no longer holds `list_work_order_billing_term_rows` |
| Part 3: one line that cannot be written | string patch `...service.insert_billing_term` | `AttributeError` from `monkeypatch` |
| 9B: amendment accessor inventory (four tests) | `vars(service)` filtered on its own name | `assert 0 >= 8`; inventory drift naming eight functions; two `KeyError`s |

## Independent review

| Round | Result | Findings |
| --- | --- | --- |
| 1 | CORRECTION_REQUIRED | 4 material: public names dropped from `service` (F-01); the importer scan claimed a check it did not make (F-02); the text proof did not show moved code resolves the same globals (F-03); NEXT_STEPS listed three departures of six (F-04). All four corrected. |
| 2 | CORRECTION_REQUIRED | 3 material: the 221 names the original only imported were no longer reachable (R2-F01) - **the owner approved the narrower surface, 23 September 2026**, now recorded; reflective access to globals was not rejected (R2-F02) - now fails closed; the importer scan missed some import forms (R2-F03) - now fails closed, 14 forms tested. |
| 3 | CORRECTION_REQUIRED | 1 material: the importer scan still passed `service.__dict__[...]`, the full dotted path used as a value, and relative imports (R3-F01). Rebuilt to track every package on the service's path and resolve relative imports; only four harmless dunders pass; unresolvable sites fail unless declared at their exact site; 28 forms tested. |
| 4 (authorized beyond the cap) | CORRECTION_REQUIRED | 1 material: an aliased `import_module` on a path assembled from string pieces passed the scan (R4-F01). Dynamic importing is now tracked by what it is rather than what it is called; `eval`/`exec`/`compile`/`globals()` and path fragments in strings are refused; 49 forms tested. The reviewer's residual called the rest of the evidence strong. |

## Deferred and not checked

- Independent review: no ACCEPTED verdict. Round 4's finding is corrected but was not re-reviewed; the
  owner chose to commit without a fifth round (23 September 2026). The scan's stated limit - a path
  assembled from pieces that never contain `app.modules` or `work_orders.service` - stands.
- The owner's decision to merge.
- The commercial offers service (3,712 lines) has the same shape; the convention for splitting it is
  in `docs/agent/CODING_STANDARDS.md`, "When a service outgrows one file". Not started.
