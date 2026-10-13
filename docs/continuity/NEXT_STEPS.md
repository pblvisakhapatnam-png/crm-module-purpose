# Next steps

The current status of this copy, and the record of the frozen handoff contract's fingerprint. PBL's running log of
earlier work is not part of this copy; where the records mention "the latest update" or a dated entry here, this page
replaces it.

## Where things stand

| Item | Position |
| --- | --- |
| This copy | Made from PBL's internal repository at commit `f8bba7ce` (13 October 2026); `docs/vendor/VENDOR_BASELINE_MANIFEST.md` says what was left out or changed |
| Database | One chain of migrations; its head is `20260908_0055` |
| CRM | The main flow works end to end, from a Lead to a Work Order; PBL's staff are testing it with invented data. What is left: `docs/vendor/02_CRM_CAPABILITY_MATRIX.md` and `docs/vendor/03_REMAINING_AND_DEFERRED_SCOPE.md` |
| Equipment Hiring | Built up to allocating PBL's own machines and the holiday calendar; the Work Order is not yet released. Not part of this package |
| The handoff | Frozen, amended twice with PBL's approval (8 and 12 October 2026); `docs/vendor/05_CRM_TO_HIRING_HANDOFF.md` |
| Next | Phase 0, the kickstart (`docs/vendor/09_PHASE_0_KICKSTART.md`) |

## The frozen handoff contract's fingerprint

`docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` changes only by a dated amendment added at its
end with PBL's approval. A file cannot hold its own fingerprint, so each amendment's "before" and "after" SHA-256 is
recorded here. Check the current value before and after any work near the handoff:

```powershell
Get-FileHash docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
```

| Event | SHA-256 before | SHA-256 after |
| --- | --- | --- |
| Frozen by Slice 6D.1 | - | `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a` |
| Amendment of 8 October 2026 (CS-04 part 1: each offer line's quantity handed off once; no Work Order from a Change Quotation; the latest response must be the award; no "lost" after a handoff; the customer's order reference required and unique per offer) | `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a` | `0f16ff221e897f6199c352204a0ecced6f9a67f0c6695ad97c08c9dc2cd39080` |
| Amendment of 12 October 2026 (CS-04 part 2, items c and d: the offer's version on the Work Order and its events; the handed-off lines in `CommercialOfferConvertedToWorkOrder`; a request key and a tracking id agreed for later) | `0f16ff221e897f6199c352204a0ecced6f9a67f0c6695ad97c08c9dc2cd39080` | `7954b4558a12578cc98bcb851b48a302ce7a155b249969d2b4b817af4bd10130` |

**Current value: `7954b4558a12578cc98bcb851b48a302ce7a155b249969d2b4b817af4bd10130`.** Everything above each amendment
is unchanged: the file up to the start of an amendment still has that amendment's "before" value.
