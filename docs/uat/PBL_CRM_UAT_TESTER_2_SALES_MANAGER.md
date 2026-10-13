# Tester 2 - Sales Manager

**Sign in as `uat-manager-01`.** Read the [Tester Guide](PBL_CRM_TESTER_GUIDE.md) first. Then work through this sheet
in order, and record **Pass** or **Fail** for every step in your tab of the Feedback Log. Use only the data on this
sheet: every name starts `T2-`, and every PAN and GST number has a `2` after `ZZZZM`.

A Sales Manager does everything a Sales Executive does, and also **approves quotations** before they go to a customer.
Part A is approving for Tester 1, whenever they ask; your own work is Parts B to E. If you are doing every sheet
yourself, follow the [one-person route](PBL_CRM_UAT_ONE_PERSON_ROUTE.md) instead.

| Who | What you do for them, or they for you |
| --- | --- |
| Tester 1, Sales Executive | You approve their quotations, twice (steps 1 and 2) |
| Tester 3, Operations | Enters the market rates on your offer (step 6) |
| Tester 4, Accounts | Checks your customer's PAN (after step 4) |

---

## Part A - Approving for Tester 1

### 1. Approve Tester 1's first quotation

When Tester 1 asks, open their offer from **Commercial Offers** by its code. Tab **Submission**, card **Quotation
Document**: read the draft (**Download draft (not approved for issue)**), then press **Approve for Issue**.

**Pass if** the version reads "Approved for Issue", and *Approved by* and *Approved at* show you and the time.

**Tell us:** did you have what you needed to decide - the lines, the rates behind each line, the reason for each
line's basis rate, and its history?

### 2. Approve Tester 1's second quotation

Later Tester 1 asks again: the customer wanted a better rate, so they made **version 2** of the offer
(`CO-... v2`). Open that version and approve its quotation the same way.

**Pass if** v2's quotation (`CO-... v2/V1`) reads "Approved for Issue", and v1's quotation, on v1, is unchanged.

---

## Part B - A customer in euros

### 3. The customer

**Accounts** > **Create Account**:

| Field | Type or choose |
| --- | --- |
| Account name | `T2-Nordhavn Offshore Wind India` |
| Legal name | `T2-Nordhavn Offshore Wind India Private Limited` |
| Account status | `Qualified Prospect` |
| Qualification source | `RFQ` |
| Segment | `Key Account` |
| Industry | `Renewable Energy` |

Then **Add Address**: *Address type* `Registered Office`, *Address line 1* `Unit 4, Port User Building`, *City*
`Mundra`, *District* `Kutch`, *State* `Gujarat`, *Postal code* `370421`, *Primary address* ticked.

**Pass if** the Account opens with its address.

### 4. Its PAN and GST number

**Update PAN details**: *PAN* `ZZZZM2001Z`, *PAN verification state* `Entered - Not Verified`, *PAN legal name*
`T2-Nordhavn Offshore Wind India Private Limited`. **Save PAN Profile**.

**Add GSTIN**: *GSTIN* `24ZZZZM2001Z1ZZ`, *State code* `24`, *State name* `Gujarat`, *GSTIN verification state*
`Entered - Not Verified`, *Primary GSTIN* ticked. **Add GSTIN**.

Then **Tell Tester 4:** "T2-Nordhavn Offshore Wind India is ready for its PAN check."

**Pass if** both numbers are listed.

### 5. The enquiry and an offer in euros

**Opportunities** > **Create Opportunity**: *Opportunity name* `T2-Wind turbine component handling, Mundra`,
*Opportunity source* `RFQ`, *Source reference* `T2-RFQ-2026-118`, *Estimated value* `42000000`, *Initial status*
`New`. Link it to `T2-Nordhavn Offshore Wind India` (card **Customer (Account)**, **Link Account**).

Then **Create Commercial Offer**: *Offer title* `T2-Component handling, Mundra`, *Offer mode* `Customer format`, *Offer
type* `Firm`, **Currency `EUR - Euro`**, *Offer date* today, *Valid until* 45 days from today.

Add three lines, **currency `EUR` on each**:

| Scope / service description | Equipment / service category | Quantity | UOM | Rate amount |
| --- | --- | --- | --- | --- |
| `Hiring of 400t crawler crane for nacelle lifts, monthly` | `Crane` | `2` | `Mon` | `145000` |
| `Hiring of 100t all-terrain tailing crane, monthly` | `Crane` | `2` | `Mon` | `38000` |
| `Route survey, permits and escort vehicles` | `Logistics` | `1` | `Lot` | **leave empty** |

**Pass if** the amounts are shown in euros, never as rupees, and line 3 shows no amount.

### 6. Ask Operations for market rates

**Tell Tester 3:** "My offer `CO-...` needs two market rates in euros for line 1, the 400t crawler." You need not
wait.

Once they say so, open **Market rates for line 1** (tab **Lines & Pricing**). Choose the cheaper as the basis: type
the reason `Both vendors confirmed the dates; cheaper of the two.` in its box and press **Select as basis**. Then the
cheaper vendor withdraws: on the other rate, reason `The cheaper vendor withdrew the machine today.`, **Select as
basis**.

**Pass if** the two rates are in EUR under line 1 only, lines 2 and 3 say "No market rate is recorded for this line
yet.", the second rate now shows **Basis rate**, the first no longer shows a current reason, and **Basis history for
line 1** lists both - the second as "The basis since ...", the first as "Was the basis until ..., chosen by" you,
with its reason. Nothing about the first choice is lost.

### 7. A quotation that cannot be approved yet

Tab **Submission** > **Generate quotation document**. Open the draft: its total should say **"Not fully priced"**,
because line 3 has no rate. If it shows a sum instead, report it straight away.

Now look for **Approve for Issue** on that version.

**Pass if** there is no Approve button and the page says "Cannot be approved for issue: 1 active line has no rate. Every
active line must be priced before a quotation can be approved for issue."

### 8. Priced, but the quotation is now out of date

Tab **Lines & Pricing**: **Edit line** on line 3, *Rate amount* `9500` (EUR), **Save line**. Back on **Submission**,
look at the version you made in step 7.

**Pass if** it still cannot be approved, now because "The offer has changed since this version was generated, so this
version no longer matches it." Then **Generate quotation document** again and approve the new version: **Pass if** it
reads "Approved for Issue".

### 9. Two people saving the same offer

Two browser tabs are two people. Copy your offer's address into a second tab and open it there too.

1. **Tab 1**: **Edit Commercial Offer / Status**, change *Remarks / requirement notes* to `T2 - customer asked for
   weekend working.`, **Save Commercial Offer**. Expected under the button: "Commercial Offer updated successfully."
   Press **Edit Commercial Offer / Status** again and **Save Commercial Offer** without changing anything. Expected:
   "Nothing has been changed, so there is nothing to save."
2. **Tab 2**, not reloaded: **Edit Commercial Offer / Status**, change *Offer title* to `T2-Component handling, Mundra
   port`, **Save Commercial Offer**.
3. Reload tab 1. In both tabs open **Lines & Pricing** and press **Edit line** on line 2. In tab 1 change *Remarks* to
   `T2 - tailing crane with its own rigger.` and **Save line**; then in tab 2 change *Quantity* to `3` and **Save line**.

**Pass if** both saves in tab 2 are refused directly under their own button - "Someone else changed this Commercial
Offer after you opened it, so your change was not saved. Reload the page to see their version, then make your change
again." (and the same for "this Commercial Offer line") - and after reloading tab 2, tab 1's remarks stand, the title
and the quantity are unchanged. Make the title change again in tab 2: it saves.

The offer has changed since your quotation was approved, so **Generate quotation document** again and approve the new
version, as in step 8.

### 10. One live offer per enquiry, and a button pressed twice

An enquiry has one live offer at a time, and the system holds to that even when two people save at once. To see it
without disturbing your offer, use a second enquiry.

1. **Opportunities** > **Create Opportunity**: *Opportunity name* `T2-Spare parts lift, Mundra`, *Opportunity source*
   `RFQ`, *Estimated value* `600000`. Link it to `T2-Nordhavn Offshore Wind India`.
2. Press **Create Commercial Offer**, and copy the page's address into a second tab. In both tabs type *Offer title*
   `T2-Spare parts lift`, currency `EUR`. Press **Create Commercial Offer** in the first tab, then in the second.
3. Open the offer the first tab made. Tab **Terms & Conditions**, form **Attach header T&C clause**: choose any clause
   and **double-click** **Attach T&C clause**.

**Pass if** the second tab is refused - "An active/actionable Commercial Offer already exists for this Opportunity.
Open existing Commercial Offer CO-... instead of creating another one." - and only one offer exists for the enquiry;
and the clause is attached once, any second answer saying it is already attached, never "Internal Server Error".
Leave the spare offer as it is.

### 11. Rupees and euros are never added together

Open the **Dashboard**. Tester 1's offer is in rupees, yours in euros.

**Pass if** the amounts are shown per currency - the summary says which - and never added into one total.

---

## Part C - An order awarded in parts

### 12. Send the offer and record it

Tab **Submission**, **Submission Evidence**: *Channel* `Portal`, *Submitted date/time* now, *Submission reference*
`T2-PORTAL-UPLOAD-1`, *Submitted version / revision* `V3` - the version you approved last, in step 9. **Record submission evidence**, then **Record as Submitted /
Commercially Committed**.

**Pass if** the status is Submitted.

### 13. Accepted, in two orders

The customer awards the job, but will send two purchase orders. **Record new customer response**:

| Field | Type or choose |
| --- | --- |
| Outcome | `Accepted / awarded` |
| Response received at | now |
| Channel | `Letter of award` |
| Received from | `Procurement, Nordhavn` |
| Customer PO / WO reference | `T2-LOA-01` |
| Customer response notes | `Awarded in full. The work will be ordered on two purchase orders.` |

**Pass if** the status is Accepted.

### 14. The first Work Order, for part of the work

At the top of the offer press **Create Work Order**:

| Field | Type or choose |
| --- | --- |
| Customer WO reference | `T2-PO-001` |
| Received date | today |
| Line 1 | ticked, quantity `1` (of 2) |
| Line 2 | ticked, quantity `2` |
| Line 3 | ticked, quantity `1` |

Press **Create Work Order**. **Pass if** a green panel "Work Order created" offers **Open WO-...**, and the form now
shows line 1 with "Left: 1 Mon", lines 2 and 3 "Already on a Work Order in full".

### 15. The same order cannot make a second Work Order

On the same page, try again with *Customer WO reference* `T2-PO-001` and line 1, quantity `1`.

**Pass if** it is refused: "Customer reference T2-PO-001 is already on WO-... for this offer. One customer order makes
one Work Order ...". No second Work Order appears.

### 16. Not more than is left

Now *Customer WO reference* `T2-PO-002`, line 1 quantity `2`.

**Pass if** it is refused before or after pressing the button, saying line 1 has only 1 left.

### 17. The second Work Order

*Customer WO reference* `T2-PO-002`, line 1 quantity `1`. **Create Work Order**.

**Pass if** a second Work Order is made, and back on the offer the top no longer offers **Create another Work Order**:
everything awarded is on a Work Order.

### 18. Read both Work Orders

Open each from the offer's **Traceability** tab.

**Pass if** each shows its own customer reference, the quantity it took of each offer line, and "Awaiting release to
Ops".

---

## Part D - A change after the order

### 19. Record an amendment

On the Work Order for `T2-PO-001`, card **Work Order Amendments** > **Record Work Order Amendment**:

| Field | Type or choose |
| --- | --- |
| Amendment type | `Administrative (no commercial basis required)` |
| Customer amendment reference | `T2-AMD-01` |
| Received date | today |
| Amendment reason / summary | `Customer changed the site contact and the delivery address for the escort vehicles.` |

Press **Record amendment**. **Pass if** it is listed on the Work Order. In this version an amendment does not change the
Work Order itself.

---

## Part E - What a Sales Manager may not do

### 20. Refused

| Try | Where | Pass if |
| --- | --- | --- |
| Mark a PAN Verified | your Account, Update PAN details | `Verified` is not offered: only Accounts may |
| Read the business events | **Events** > **Load recent events** | Refused |

**Pass if** both are refused. If either works, report it straight away.

---

When you have finished, go on to [Your own data](PBL_CRM_UAT_YOUR_OWN_DATA.md).
