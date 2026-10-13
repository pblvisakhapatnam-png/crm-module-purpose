# 01 - Current state and scope

## The flow, end to end

```text
Lead                      an enquiry, from any source
  -> Account              the customer company, with its PAN and GST numbers
  -> Opportunity          a piece of business we are pursuing with that customer
  -> Commercial Offer     what we offer: lines, quantities, rates, terms; sent as a quotation
  -> Accepted offer       the customer awards all or part of it
  -> Work Order handoff   the awarded lines become a Work Order           <- the CRM ends here
  -> Equipment Hiring     site, billing terms, machines, papers; later crew, log sheets, billing
```

The CRM owns everything up to and including the handoff. Equipment Hiring owns the Work Order after it.

## What the CRM owns

- **Leads**: recording and updating them, follow-up activities, the qualify-or-close decision, and converting a
  qualified Lead into an Account and an Opportunity.
- **Accounts** (called `business_party` inside the code, because the same company may later also be a vendor or a
  transporter): contacts, addresses, PAN and GST numbers with Finance's verification, classification, documents and,
  later, the approved credit amount and credit days.
- **Opportunities**: the pursuit, its stage and its offers.
- **Commercial Offers**: three kinds (a Base Offer, a Supplementary Offer for extra work, a Change Quotation for a
  change to work already ordered); lines with quantities and rates; the market rates collected for each
  line and the one chosen as its basis; terms and conditions; checks before submission; versions (a sent offer is never
  edited - a change is a new version); the quotation document and its approval for issue; and the customer's response.
- **Documents, the conversation log and reports** for the records above.
- **The handoff** of an awarded offer to a Work Order, under a frozen agreement with Hiring (doc 05), and recording a
  customer's later amendment to a Work Order.

## What Equipment Hiring owns

The Work Order after the handoff: each line's site and billing GST number; billing terms and the contract period;
shifts and crew upkeep; the holiday calendar; what kind of machine each line needs; PBL's own machines, their kit and
their statutory papers; and allocating machines to the work. Still to come on that side: releasing the Work Order,
crew, hired-in machines, daily log sheets and billing. None of it is in this package.

## Shared foundations

Sign-in, roles and permissions, the record of every business event, statuses, document storage, the HR reference that
will tell the system who holds which position, and the application's frame and menus. Both sides use them. A change
here can break the other side, which is why we ask you to tell us before changing them (`VENDOR_START_HERE.md`).

## Where things stand

- **The CRM has been tested by PBL's staff** on a hosted test site since September 2026, with invented data. A second
  round of user testing started on 12 October 2026. What testers report feeds the remaining work.
- **The CRM's main flow works end to end**, from a Lead to a Work Order, with the controls a real business needs:
  every business action checks the user's permission on the server; a sent offer cannot be changed, only replaced by
  a new version; each awarded quantity is handed off once and never twice; amounts in different currencies are never
  added together. Doc 02 goes capability by capability.
- **It is not yet ready for real customers.** Several capabilities are partly built, some wait on a PBL decision or
  an outside system, and production hosting does not exist yet. Doc 03 sorts what remains.
- **Size**: about 3,500 automatic server-side tests, about 600 screen-logic tests and about 25 browser walk-throughs,
  all run on every proposed change.

We deliberately do not put a percentage on how complete the CRM is. Doc 02 says what works and what does not, which is
more useful.

## This package

**The present work is the CRM only.** Hiring is visible for context and for its tests, and is out of scope. The
handoff between them may be read and tested, and changed only with PBL's written approval.

What the package includes, what is a separately priced option and what comes later is set out in doc 03. Where it
runs, how many people use it and what it must achieve is in doc 10.
