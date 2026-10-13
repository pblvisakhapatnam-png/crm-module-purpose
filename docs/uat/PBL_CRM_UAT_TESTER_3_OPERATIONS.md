# Tester 3 - Operations

**Sign in as `uat-operations-01`.** Read the [Tester Guide](PBL_CRM_TESTER_GUIDE.md) first. Then work through this
sheet, and record **Pass** or **Fail** for every step in your tab of the Feedback Log.

In the CRM, Operations does two jobs: it **enters the market rates** collected from vendors, so Sales can price an
offer, and it **makes the Work Order** once the customer has accepted. You cannot make a Lead, a customer, an enquiry
or an offer - that is Sales work, and half of this sheet checks that the system stops you clearly.

Your work comes from the Sales testers. **Start with Part A**, which needs nobody. When Tester 1 or Tester 2 sends you
an offer's code, do the part it belongs to, then come back. If you are doing every sheet yourself, follow the
[one-person route](PBL_CRM_UAT_ONE_PERSON_ROUTE.md) instead.

| Who | What you do for them |
| --- | --- |
| Tester 1, Sales Executive | Three market rates on their offer (Part B), then their Work Order (Part D) |
| Tester 2, Sales Manager | Two market rates in euros on their offer (Part B) |

---

## Part A - Things Operations may not do

### 1. Making records that are Sales work

Try each. Write down **how** you were stopped.

| Try | Where | Pass if |
| --- | --- | --- |
| Create a Lead | **Leads** | No **Create Lead**, or refused |
| Create a customer | **Accounts** | No **Create Account**, or refused |
| Create an enquiry | **Opportunities** | No **Create Opportunity**, or refused |
| Create an offer | **Commercial Offers** | No **Create Commercial Offer**, or refused |
| Read the business events | **Events** > **Load recent events** | Refused |

**Pass if** every one is refused or not offered. If any works, report it straight away.

**Tell us** for each: a clear "you may not" message, or a button that is simply missing? Which would you rather have?

---

## Part B - Market rates

### 2. Three rates for Tester 1's offer

When Tester 1 sends you their offer's code, open it (**Commercial Offers**, find the code). Tab **Lines & Pricing**:
each line has its own **Market rates for line N**. Under **line 1** (`Hiring of 250mt crane on call basis`), form
**Add a rate for line 1** - once for each row:

| Field | Rate 1 | Rate 2 | Rate 3 |
| --- | --- | --- | --- |
| Rate type | `Market rate` | `Market rate` | `Market rate` |
| Rate amount | `133400` | `139200` | `150800` |
| Currency | `INR` | `INR` | `INR` |
| Rate basis | `per_day` | `per_day` | `per_day` |
| Equipment / service description | `250t crane, operator included, no fuel` | `250t crane, operator and fuel` | `250t crane, operator included, no fuel` |
| Source / vendor | `T3-Sagar Equipment Hire` | `T3-Konaseema Cranes & Logistics` | `T3-Deccan Heavy Lift Services` |
| Vendor contact | `+91-90000-11001` | `+91-90000-11002` | `+91-90000-11003` |
| Collected by | `B. Srinivas (Ops)` | `P. Lakshmi (Ops)` | `M. Anand (Ops)` |
| Collected at | today, 10:00 | today, 11:30 | today, 12:15 |
| Comparison notes | `Could not confirm a machine for the full period.` | `Confirmed availability in writing.` | `Machine available from next week.` |

Leave **Choose this rate as the line's basis now** unticked. Press **Save rate** each time.

The broker sent one quote for both cranes. On the `T3-Konaseema Cranes & Logistics` rate press **Attach the quote**:
any small file of your own stands for the broker's WhatsApp screenshot, email or PDF; *Document type* `Vendor quote`;
**Upload**.

Then under **line 3** (`Hiring of 200mt crane on continuous basis`), **Add a rate for line 3** from the same quote:
*Rate amount* `2790000`, *Rate basis* `per_month`, *Source / vendor* `T3-Konaseema Cranes & Logistics`, *Collected by*
`P. Lakshmi (Ops)`, and in **Quote copy attached to another rate** choose "Line 1: T3-Konaseema Cranes & Logistics
...". **Save rate**.

**Pass if** the three rates are listed under line 1 only, each saved with "Rate saved on line 1." under the button;
each shows the time you typed - "Collected by B. Srinivas (Ops) on <today>, 10:00 am", then 11:30 am and 12:15 pm; the
Konaseema rate shows "Quote copy: ..." with **Download**; and line 3's rate shows the same file with "(Attached to line
1's rate)" - the quote is attached once. Then **tell Tester 1** the rates are in. Choosing which rate each line is
priced on is their decision.

**Tell us:** could you say what each rate did and did not include? Would a person reading this next week understand
what you were quoted?

### 3. Two rates in euros for Tester 2's offer

When Tester 2 sends you their offer's code, add two rates the same way under **line 1** (the 400t crawler),
**currency `EUR`**:

| Field | Rate 1 | Rate 2 |
| --- | --- | --- |
| Rate amount | `141000` | `148500` |
| Rate basis | `per_month` | `per_month` |
| Equipment / service description | `400t crawler crane, operator included` | `400t crawler crane, operator and rigging crew` |
| Source / vendor | `T3-Baltic Lift Partners` | `T3-Westcoast Crawler Hire` |
| Collected by | `P. Lakshmi (Ops)` | `P. Lakshmi (Ops)` |

**Pass if** both are listed in euros under line 1. Then tell Tester 2.

### 4. Choosing the basis yourself

On Tester 1's offer, under line 1, press **Select as basis** on a rate that is not the basis, leaving its reason box
empty.

**Pass if** the system offered you the choice and refused it beside the button ("Give the reason for choosing this
rate."), with nothing changed. If Tester 1 has already sent the offer (status Submitted), its market rates are settled
and no **Select as basis** shows - that is correct: say so in the notes, and pass. Today entering a rate and
choosing the basis are one permission, so Operations can do both. **Tell us whether it should**: should Operations be
stopped from choosing the basis, or is it useful when Sales are away?

### 5. Changing an offer is not Operations' job

On Tester 1's offer, try each:

| Try | Pass if |
| --- | --- |
| **Edit Commercial Offer / Status** | Not offered to you |
| **Edit line** on a line, or add a line | Refused or not offered |
| **Generate quotation document** | Refused or not offered |
| **Approve for Issue** | Not offered |
| **Record customer response** | Refused or not offered |

**Pass if** each is refused or not offered. If any works, report it straight away.

---

## Part C - A file

### 6. A file on the offer

A vendor's quote belongs on its rate (step 2). A file about the whole offer goes on the offer: on Tester 1's offer, tab
**Overview**, **Documents**: choose any small file of your own, *Document type* `Commercial`, *Remarks* `T3 - route
survey for the 250t crane.` Press **Upload**.

**Pass if** it says "File added: ..." and **Download** gives it back. Operations may upload to an offer, not to a
customer.

---

## Part D - Making the Work Order

### 7. Tester 1's Work Order

When Tester 1 tells you their offer is accepted and gives you the customer's order reference `T1-PO-4471`, open the
accepted version - `CO-... v2`; v1 reads "Replaced by v2" - and press **Create Work Order** (at the top of the offer):

| Field | Type or choose |
| --- | --- |
| Customer WO reference | `T1-PO-4471` |
| Received date | today |
| Remarks | `T3 - received from Tester 1 by phone.` |
| Lines | all ticked, each with all of its quantity |

Press **Create Work Order**.

**Pass if** the green panel "Work Order created" shows **Open WO-...** and "Lines copied: 5".

### 8. Nothing left to order

On the same page, try once more with *Customer WO reference* `T3-RETRY-01`.

**Pass if** it is refused - every line is already on a Work Order in full - and no second Work Order appears.

### 9. Read the Work Order as the person who receives it

Open the Work Order.

**Pass if** it shows the customer's reference, which offer it came from, and for each line the offer line it came
from, with the status "Awaiting release to Ops".

**Tell us:** does it tell you what you need to plan the job? What would you ring Sales about?

---

## Part E - What you would actually need

### 10. In your own words

- Is the market-rate form the right shape for the way you collect vendor quotes? Is entering a rate on each line,
  and attaching a quote once for several lines, the way you work?
- What is missing from the Work Order when it reaches you?
- Is there anything on these screens you would never use?

**Pass if** you wrote your answers in the Feedback Log's notes for this step.

---

When you have finished, go on to [Your own data](PBL_CRM_UAT_YOUR_OWN_DATA.md).
