# Tester 1 - Sales Executive

**Sign in as `uat-sales-01`.** Read the [Tester Guide](PBL_CRM_TESTER_GUIDE.md) first. Then work through this sheet
in order, and record **Pass** or **Fail** for every step in your tab of the Feedback Log. Use only the data on this
sheet: every name starts `T1-`, and every PAN and GST number has a `1` after `ZZZZM`, so nothing you type clashes with
another tester.

You work with three other testers. When a step says **Tell Tester 2** or **Tell Tester 3**, send them the offer's
code (`CO-...`, at the top of the offer page) and carry on with the next step that does not need them. If you are
doing every sheet yourself, follow the [one-person route](PBL_CRM_UAT_ONE_PERSON_ROUTE.md) instead.

| Who | What they do for you |
| --- | --- |
| Tester 2, Sales Manager | Approves your quotations (steps 17 and 23) |
| Tester 3, Operations | Enters the market rates on your offer (step 13) and makes the Work Order (step 26) |
| Tester 4, Accounts | Checks your customer's PAN and GST numbers (after step 10) |

---

## Part A - An enquiry comes in

### 1. Create a Lead

**Leads** > **Create Lead**.

| Field | Type or choose |
| --- | --- |
| Lead source | `Email` |
| Source reference | `T1 enquiry email` |
| Company name | `T1-Trident Marine Works Private Limited` |
| Contact name | `T1-R. Satyanarayana` |
| Contact phone | `+91-98480-11223` |
| Contact email | `satya@trident-marine.invalid` |
| Requirement summary | `Crane support for breakwater block placement at a fishing harbour. Blocks about 40 t. Duration not confirmed.` |
| Lead status | `New` |

Press **Create Lead**. **Pass if** it says "Lead created successfully." and the Lead opens from the list.

### 2. Record a follow-up call

On the Lead, card **Follow-up activities**:

| Field | Type or choose |
| --- | --- |
| Activity type | `Call` |
| Activity date/time | now |
| Notes | `First call. Breakwater blocks around 40 t, placed from the shore.` |
| Outcome | `Asked us to suggest a crane and a rate.` |
| Next follow-up date/time | tomorrow, 11:00 |

Press **Record Lead Activity**. **Pass if** it is listed with the follow-up date.

### 3. Record a conversation

On the same Lead, card **Conversations / Interactions** > **Record a conversation**:

| Field | Type or choose |
| --- | --- |
| Channel | `Site Visit` |
| Direction | `Outbound (to the customer)` |
| When it happened | today, 15:00 |
| Subject | `Site visit with Operations` |
| What was said / notes | `Access road can take the crane. Tide allows about 8 working hours a day.` |
| Outcome | `Customer asked for a formal quotation.` |

Press **Save conversation**. **Pass if** it says "Conversation recorded." and the visit is listed at the time you
typed: today, 03:00 pm.

**Tell us:** the Lead has two places to record contact with the customer. Was it clear which to use?

### 4. Qualify the Lead and convert it

Card **Qualification decision**: *Decision* `Qualified`, *Decision notes* `Real requirement, budget confirmed on the call.` Press **Save Qualification Decision**.

Then card **Convert to Account and Opportunity**: *Conversion notes* `Converted after the site visit.` Press
**Convert Lead**.

**Pass if** it says "Lead converted to Account and Opportunity." and links an Account `T1-Trident Marine Works Private Limited` and an Opportunity, both of which open.

### 5. A Lead we will not take

Create a second Lead, as in step 1:

| Field | Type or choose |
| --- | --- |
| Lead source | `Phone` |
| Company name | `T1-Ravindra Builders` |
| Contact name | `T1-K. Ravindra` |
| Contact phone | `+91-99490-55667` |
| Contact email | `ravindra@ravindra-builders.invalid` |
| Requirement summary | `Crane for a two-day slab lift at a residential site in the town centre.` |

Then **Qualification decision**: *Decision* `Unqualified`. Press **Save Qualification Decision** with the *Reason*
empty first. **Pass if** it is refused: "Reason is required when a Lead is unqualified or closed." Then type the
reason `Site access cannot take our smallest crane safely. Customer advised to use a local hydra operator.` and save.

**Pass if** no **Convert Lead** is offered for this Lead, and no Account `T1-Ravindra Builders` appears under
**Accounts**.

---

## Part B - A large customer, typed in by hand

### 6. Create the Account

**Accounts** > **Create Account**.

| Field | Type or choose |
| --- | --- |
| Account name | `T1-Kakinada Steel & Ferro Alloys` |
| Legal name | the long name below, on one line |
| Account status | `Qualified Prospect` |
| Qualification source | `Enquiry` |
| Segment | `Key Account` |
| Industry | `Iron and Steel` |

Legal name: `T1-Kakinada Steel and Ferro Alloys Corporation of India Limited - Visakhapatnam Integrated Works and Coastal Logistics Division (A Government of India Enterprise under the administrative control of the Ministry of Steel)`

Press **Create Account**. **Pass if** the Account opens and the long legal name is shown in full, without breaking
the page.

### 7. Its address and contact

On the Account, **Add Address**:

| Field | Type or choose |
| --- | --- |
| Address type | `Registered Office` |
| Address line 1 | `Administrative Building, Steel Plant Complex` |
| City | `Visakhapatnam` |
| District | `Visakhapatnam` |
| State | `Andhra Pradesh` |
| Postal code | `530031` |
| Primary address | tick |

Then **Add Contact**: *Contact name* `T1-M. Ramesh`, *Designation* `Deputy General Manager (Projects)`, *Department*
`Projects`, *Phone* `+91-89120-44556`, *Email* `ramesh@kakinada-steel.invalid`, *Primary contact* ticked.

**Pass if** both are listed on the Account.

### 8. Its PAN

Card **Update PAN details**:

| Field | Type or choose |
| --- | --- |
| PAN | `ZZZZM1001Z` |
| PAN verification state | `Entered - Not Verified` |
| PAN legal name | `T1-Kakinada Steel and Ferro Alloys Corporation of India Limited` |

Press **Save PAN Profile**. Before saving, open *PAN verification state*: **Pass if** `Verified` and
`Rejected / Incorrect` are **not** offered to you - only Accounts may choose them.

### 9. Its four GST numbers

The company works in four states. Card **Add GSTIN**, once for each row:

| GSTIN | State code | State name | GSTIN verification state | Primary GSTIN |
| --- | --- | --- | --- | --- |
| `37ZZZZM1001Z1ZZ` | `37` | `Andhra Pradesh` | `Entered - Not Verified` | tick |
| `36ZZZZM1001Z1ZZ` | `36` | `Telangana` | `Entered - Not Verified` | |
| `21ZZZZM1001Z1ZZ` | `21` | `Odisha` | `Entered - Not Verified` | |
| `24ZZZZM1001Z1ZZ` | `24` | `Gujarat` | `Entered - Not Verified` | |

The numbers are invented, in the right shape. **Pass if** all four are listed, each with its state.

### 10. Hand the customer to Accounts

**Tell Tester 4:** "T1-Kakinada Steel & Ferro Alloys is ready for its PAN and GST checks." Then carry on.

**Pass if** you could find everything on the Account you would want to know about a customer. Write down what was
missing.

---

## Part C - The enquiry and the offer

### 11. The Opportunity, linked to the customer

**Opportunities** > **Create Opportunity**:

| Field | Type or choose |
| --- | --- |
| Opportunity name | `T1-Crane hire for structures and erection works, Vizag` |
| Opportunity source | `Manual` |
| Customer requirement summary | `Cranes of various capacity for structures and erection works. Some on call, some continuous. Overtime billed separately.` |
| Estimated value | `8500000` |
| Expected close date | the last day of next month |
| Initial status | `New` |

Press **Create Opportunity**. On the Opportunity, card **Customer (Account)**: *Link existing Account*
`T1-Kakinada Steel & Ferro Alloys`, **Link Account**.

**Pass if** the card now shows the Account with **Open Account**.

### 12. The Commercial Offer and its lines

On the Opportunity press **Create Commercial Offer**:

| Field | Type or choose |
| --- | --- |
| Offer title | `T1-Crane hire, Vizag works` |
| Offer mode | `Plum-generated quote` |
| Offer type | `Firm` |
| Currency | `INR - Indian rupee` |
| Offer date | today |
| Valid until | 30 days from today |

Press **Create Commercial Offer**. Write down its code (`CO-...`).

Then tab **Lines & Pricing** > **Add Commercial Offer line**, once for each row, currency `INR` each time:

| Scope / service description | Equipment / service category | Quantity | UOM | Rate amount |
| --- | --- | --- | --- | --- |
| `Hiring of 250mt crane on call basis` | `Crane` | `8` | `Days` | `145000` |
| `Overtime hours for 250mt crane` | `Crane` | `8` | `Hrs` | `18500` |
| `Hiring of 200mt crane on continuous basis` | `Crane` | `3` | `Mon` | `2850000` |
| `Overtime hours for 200mt crane` | `Crane` | `60` | `Hrs` | `14500` |
| `Mobilisation and demobilisation` | `Mobilisation` | `1` | `Lot` | `375000` |

**Pass if** the five lines are listed with their amounts, and the offer's value adds up.

### 13. Ask Operations for market rates

**Tell Tester 3:** "My offer `CO-...` needs market rates for line 1, the 250mt crane on call, and line 3, the 200mt
crane." Carry on with step 14 and come back to step 15 when they say the rates are in.

**Pass if** Tester 3 found your offer from its code alone.

### 14. Terms and conditions

Tab **Terms & Conditions**: *Recommendation basis* `Equipment Hiring`, **Attach recommended clauses**. Then open one
clause with **View clause detail**.

**Pass if** the clauses are attached and you can read one. The wording is sample wording, not PBL's final terms.

### 15. Choose the rate each line is priced on

Tab **Lines & Pricing**. Each line has its own **Market rates for line N**. Under line 1 Tester 3 has entered three
rates. First press **Select as basis** on one of them with its reason box empty. Then, on
**`T3-Konaseema Cranes & Logistics`** - the middle one, not the cheapest - type the reason and press **Select as
basis**:

`Not the lowest quote. The lowest vendor could not confirm a machine for the whole period and has had two breakdowns on our sites this year. This vendor confirmed availability in writing.`

Under line 3 Tester 3 has entered one rate from the same quote. Choose it as line 3's basis, reason `Only quote for the
200mt crane, from the same vendor.`

Then tab **Submission**, card **Submission Readiness**: find **Market rates and basis rate on each line**.

**Pass if** the empty reason is refused beside the button ("Give the reason for choosing this rate."); line 1's
Konaseema rate shows **Basis rate** and "The basis since ..., chosen by" you, with your reason; line 3's rate shows the
quote file with "(Attached to line 1's rate)"; and the checklist warns "No market rate on line(s) 2, 4, 5." and says
it does not block anything.

### 16. Make the quotation

Tab **Submission** > **Generate quotation document**.

**Pass if** it says the quotation was "generated as Draft", and there is **no Approve for Issue** button for you: only a
Sales Manager or Admin approves. Open the draft with **Download draft (not approved for issue)** and read it as the
customer would.

### 17. Ask for approval

**Tell Tester 2:** "Please approve the quotation on `CO-...`." Wait for them, then press **Refresh**.

**Pass if** the version now reads "Approved for Issue", and *Approved by* names Tester 2 (Pilot Sales Manager) with the time.

### 18. Send it, and record that it was sent

Tab **Submission**, card **Submission Evidence**:

| Field | Type or choose |
| --- | --- |
| Channel | `Email` |
| Submitted date/time | now |
| Submission reference | `T1-QTN-EMAIL-1` |
| Submitted version / revision | `V1` |
| Recipient summary | `T1-M. Ramesh, Projects` |

Press **Record submission evidence**, then **Record as Submitted / Commercially Committed**.

**Pass if** the offer's status is Submitted.

### 19. A submitted offer is settled

The offer has gone to the customer, so it is settled. Open tab **Lines & Pricing**, then **Terms & Conditions**, then
**Submission**.

**Pass if** there is no **Add Commercial Offer line** form and no **Edit line** button, and where they were the page
says: "This offer is Submitted, so its lines, prices, T&C, credit reviews and submission evidence can no longer change on this version. Make a new version on the Submission tab." The same note stands in place of the market-rate, T&C,
credit-review and submission-evidence forms. The offer's code reads `CO-... v1`: what the customer received stays
exactly as sent.

---

## Part D - Negotiation, a new version, and the order

### 20. Log the negotiation

Open the Opportunity `T1-Crane hire for structures and erection works, Vizag`. **Record a conversation** four times:

| Channel | Direction | What was said / notes |
| --- | --- | --- |
| `Email` | `Outbound (to the customer)` | `Sent the approved quotation with rate breakup and mobilisation terms.` |
| `Call` | `Inbound (from the customer)` | `Customer says the monthly rate is above budget. Asked if it improves for a three-month commitment.` |
| `Note` | `Internal` | `Operations confirmed the machine can be committed for three months.` |
| `Email` | `Outbound (to the customer)` | `Offered a lower monthly rate against a three-month commitment.` |

**Pass if** all four are listed, with your name and the time.

### 21. The customer asks for a revision

On the offer, tab **Submission**, card **Customer Response / Award Outcome**: *Outcome* `Revision requested`,
*Response received at* now, *Channel* `Phone / verbal`, *Customer response notes* `Asked for the three-month rate in writing.` Press **Record customer response**.

Then, on the same tab, card **Offer versions** > **Make a new version**: *Reason* `Rate correction`, *Note* `Monthly rate for a three-month commitment.` Press **Make a new version**.

**Pass if** it says "CO-... v2 made as an editable Draft. Lines, prices, T&C and the current credit review were copied;
submission evidence and quotation documents were not." and offers **Open the new version**, and **Offer versions** lists
v1, still Submitted, and v2, a Draft.

### 22. Change the rate on version 2

Press **Open the new version**. The code is the same, now `CO-... v2`. Tab **Lines & Pricing**: the five lines are
there, and lines 1 and 3 have their market rates and basis rates, copied - each basis marked "(carried over from
version 1)", and the quote file "(Attached to line 1's rate on version 1)". **Edit line** on line 3, *Rate amount*
`2750000`, **Save line**.

**Pass if** it saves and the line's amount changes on v2, while v1 - open it from **Offer versions** - still shows the
old rate and cannot be changed.

### 23. Version 2's quotation, approved and sent

On v2, tab **Submission**: **Generate quotation document**. Its reference carries the version: `CO-... v2/V1`. **Tell
Tester 2** to approve it (they open `CO-... v2`). When they have, record **Submission Evidence** for v2 (`Email`,
reference `T1-QTN-EMAIL-2`, version `V2`) - v1's evidence was not copied - and press **Record as Submitted /
Commercially Committed**.

**Pass if** v2 is Submitted, and v1 now reads "Replaced by v2" and stays read-only history, its own quotation and who
approved it unchanged.

### 24. The customer says yes

Three days later the customer telephones and confirms. On **v2** - the version they accepted - **Record new customer
response**:

| Field | Type or choose |
| --- | --- |
| Outcome | `Accepted / awarded` |
| Response received at | now |
| Channel | `Phone / verbal` |
| Received from | `T1-M. Ramesh` |
| Customer PO / WO reference | `T1-PO-4471` |
| Customer response notes | `Confirmed on the telephone by their project manager. Written order to follow.` |

**Pass if** v2's status is Accepted and *Ready to create the Work Order* reads **Yes**. On v1 the same action is not
offered: a reply goes on the latest version only.

### 25. An accepted offer cannot be undone by editing

Press **Edit Commercial Offer / Status** and try to set *Offer status* back to `Draft`, then save.

**Pass if** it is refused, and the message tells you why.

### 26. Hand it to Operations

**Do not make the Work Order yourself.** **Tell Tester 3:** "`CO-... v2` is accepted; the customer's order reference
is `T1-PO-4471`." When they say it is made, open it from v2's **Traceability** tab.

**Pass if** the Work Order shows the customer's reference `T1-PO-4471`, every line with the offer line it came from,
and the status "Awaiting release to Ops". That is where the CRM stops (Tester Guide).

---

## Part E - A file, and what you may not do

### 27. Attach a file to the offer

Tab **Overview**, **Documents**: choose any small file of your own (a text file will do), *Document type*
`Commercial`, *Remarks* `T1 - copy of the customer's order email.` Press **Upload**.

**Pass if** it says "File added: ..." and **Download** gives the file back.

### 28. What a Sales Executive may not do

| Try | Where | Pass if |
| --- | --- | --- |
| Approve a quotation | any offer's Submission tab | No **Approve for Issue** button |
| Mark a PAN Verified | your Account, Update PAN details | `Verified` is not offered |
| Read the business events | **Events** > **Load recent events** | Refused: "Your role may not have permission to view business events." |

**Pass if** each is refused or not offered. If any of them works, report it straight away.

---

When you have finished, go on to [Your own data](PBL_CRM_UAT_YOUR_OWN_DATA.md).
