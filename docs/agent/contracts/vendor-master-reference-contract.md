# Vendor Master Reference Contract

## Contract ID and status

`VMR-001` - `APPROVED` - 12 August 2026.

## Boundary

The centralized ERP Vendor Master is authoritative for suppliers, service providers and brokers.
Market Hire and Vendor Payable retain a stable vendor reference and the small approved snapshot
needed for transaction history; they do not create a competing supplier master.

The implementation inventory must identify PBL's current Vendor Master product/module and
available interface before building the adapter. The logical ownership remains valid if the
current interface is an API, controlled export/import or another approved connector.

## Minimum vendor reference

```text
vendor_public_id / authoritative external reference
vendor code and display/legal name
PAN/GST and applicable statutory-status references
vendor type / service categories
active/blocked status
approved sites/branches or scope where applicable
payment/tax profile reference (not copied values unless required for a transaction snapshot)
master version and updated-at/as-of time
```

Bank details, KYC files, tax evidence and other sensitive vendor information remain in the
authoritative Vendor Master/Documents capability. Hiring receives only the status and references
required for its action.

## Change behavior

- An inactive/blocked vendor cannot receive a new Vendor Hire Agreement or commitment.
- Existing assignments and payable records retain the vendor reference/version used at the time.
- A master block creates an operational exception; it does not silently delete or relink history.
- External equipment identity remains in the Hiring Vendor Equipment Register. Vendor crew
  representation remains decision D-03.

## Failure behavior

Unavailable or stale Vendor Master data is visible and is never treated as an active approval.
Where an API is not ready, a controlled, versioned import may supply a read-only snapshot through
the same adapter boundary. Manual free-text supplier creation inside Market Hire is not allowed.
