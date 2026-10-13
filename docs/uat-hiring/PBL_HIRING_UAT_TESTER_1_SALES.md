# Tester 1 - Sales: from an accepted offer to Work Orders ready for Operations

**Sign in as `uat-sales-01`.** Read the [User Guide](PBL_HIRING_USER_GUIDE.md) and the
[Tester Guide](PBL_HIRING_TESTER_GUIDE.md) first. Work through this sheet in order, and record **Pass** or **Fail**
for every step in your tab of the Feedback Log. Use only the data on this sheet: every name starts `T1-`.

The Hiring site starts with only PBL's machines and its holiday calendar. **Everything the others plan on comes from
you**: the customer, the accepted offer, and two Work Orders with their sites, terms and holidays. Tester 3
(Operations) waits for your Work Orders, so do Parts A and B first. If you are doing every sheet yourself, follow the
[one-person route](PBL_HIRING_UAT_ONE_PERSON_ROUTE.md) instead.

| Who | What they do with your work |
| --- | --- |
| Tester 3, Operations | Plans machines on both your Work Orders (after steps 12 and 13) |
| Tester 2, Fleet Admin | Adds a holiday to PBL's calendar, which your first Work Order then shows (after step 8) |
| Tester 4, Accounts | Reads your terms and holidays as the person who will bill from them |

"Day 0" below is the date the person running the test gives you: the day PBL's machines were loaded. Every sheet
counts from it, so Operations' dates match yours.

---

## Part A - The customer, the offer, and the customer's yes

This part is the CRM's, done briefly: the CRM test covers it in depth.

### 1. The customer and its sites

**Accounts** > **Create Account**: *Account name* `T1-Saurashtra Port Infra`, *Legal name* `T1-Saurashtra Port Infra Private Limited`, *Account status* `Qualified Prospect`, *Segment* `Infrastructure`, *Industry* `Marine and Port Construction`. **Create Account**.

Then **Add Address** four times:

| Address type | Address line 1 | City | District | State | Postal code | Primary address |
| --- | --- | --- | --- | --- | --- | --- |
| `Registered Office` | `Port House, Ashram Road` | `Ahmedabad` | `Ahmedabad` | `Gujarat` | `380009` | tick |
| `Site` | `Jetty 3 and tank farm, Dahej Port (not a major port)` | `Dahej` | `Bharuch` | `Gujarat` | `392130` | |
| `Site` | `Private container freight station, yard extension` | `Uran` | `Raigad` | `Maharashtra` | `400702` | |
| `Site` | `Contractor work, central PSU refinery shutdown` | `Vadodara` | `Vadodara` | `Gujarat` | `391320` | |

**Pass if** the four addresses are listed.

### 2. Its PAN and GST numbers

**Update PAN details**: *PAN* `ZZZZH1001Z`, *PAN verification state* `Entered - Not Verified`. **Save PAN Profile**.

**Add GSTIN** twice: `24ZZZZH1001Z1ZZ` (state code `24`, `Gujarat`, *Primary GSTIN* ticked) and `27ZZZZH1001Z1ZZ`
(state code `27`, `Maharashtra`).

**Pass if** both GST numbers are listed with their states. The Work Order bills each line from one of them.

### 3. The enquiry and the offer

**Opportunities** > **Create Opportunity**: *Opportunity name* `T1-Cranes for jetty, yard and refinery shutdown`,
*Opportunity source* `RFQ`, *Estimated value* `9000000`. Link it to `T1-Saurashtra Port Infra` (card **Customer
(Account)**, **Link Account**).

**Create Commercial Offer**: *Offer title* `T1-Crane hire, Dahej, Uran and Vadodara`, *Offer type* `Firm`, *Currency*
`INR - Indian rupee`. Then three lines, currency `INR`:

| Scope / service description | Equipment / service category | Quantity | UOM | Rate amount |
| --- | --- | --- | --- | --- |
| `Hiring of 250t crawler crane for jetty piling, monthly basis` | `Crane` | `2` | `Mon` | `1200000` |
| `Hiring of 100t all-terrain crane at the container yard, shift basis` | `Crane` | `40` | `Shift` | `14000` |
| `Hiring of 100t all-terrain crane for the refinery shutdown, day basis` | `Crane` | `20` | `Days` | `52000` |

**Pass if** the offer has the three lines. Write down its code (`CO-...`).

### 4. Sent, and accepted

Tab **Submission**: **Submission Evidence** - *Channel* `Email`, *Submitted date/time* now, *Submission reference*
`T1-QTN-1` - **Record submission evidence**, then **Record as Submitted / Commercially Committed**.

Then **Record new customer response**: *Outcome* `Accepted / awarded`, *Response received at* now, *Channel* `Letter of award`, *Customer PO / WO reference* `T1-LOA-01`, *Customer response notes* `Awarded in full. Jetty and yard on one order, the refinery shutdown on another.` **Record customer response**.

**Pass if** the status is Accepted and **Create Work Order** shows at the top of the offer.

### 5. The first Work Order: jetty and yard

Press **Create Work Order**: *Customer WO reference* `T1-PO-001`, *Received date* today. Lines 1 and 2 ticked with all
their quantity; **untick line 3** - the refinery shutdown is ordered separately. **Create Work Order**.

**Pass if** "Work Order created" offers **Open WO-...**, and line 3 still shows all 20 days left. Write down the Work
Order's code: this is **your first Work Order**.

### 6. The second Work Order: the refinery shutdown

Back on the offer, **Create another Work Order**: *Customer WO reference* `T1-PO-002`, only line 3, all of it. Before
pressing the button, try `T1-PO-001` as the reference once.

**Pass if** `T1-PO-001` is refused ("Customer reference T1-PO-001 is already on WO-... for this offer ..."), and with
`T1-PO-002` a second Work Order is made. Write its code down: **your second Work Order**. The offer no longer offers
**Create another Work Order**.

---

## Part B - The first Work Order, ready for Operations

Open your first Work Order (`T1-PO-001`).

### 7. Each line's site and billing details

Card **Site and billing details**, each line:

| | Line 1 (crawler, monthly) | Line 2 (all-terrain, shifts) |
| --- | --- | --- |
| Site | `Jetty 3 and tank farm, Dahej Port (not a major port)` | `Private container freight station, yard extension` |
| Central-government site? | `No` | `No` |
| Billing GSTIN | `24ZZZZH1001Z1ZZ` | `27ZZZZH1001Z1ZZ` |
| Billing address | the Registered Office | the Registered Office |

**Save details** on each. **Pass if** each line says its details are saved. Read the hint beside
*Central-government site?*: why is Dahej **No**? (User Guide, 4.5.)

### 8. The contract period

Card **Contract period**: *Contract starts on* **5 days after day 0**, *Contract ends* `On a fixed date`, *Contract ends
on* **8 months after that**. **Save contract dates**.

**Pass if** the dates are saved. Then **tell Tester 2**: "My first Work Order's contract is in; it runs into next year."

### 9. Billing terms, line 1

Card **Billing terms**, line 1 > **Start billing terms**. The customer's order says (step 10 enters the rest):

| Term | The order says |
| --- | --- |
| Billing basis and rate | **Month**, INR **12,00,000** per month |
| Contracted time | **260 hours** a month, **26 working days** |
| Weekly off | **Sunday**. Work on an off day or a holiday is charged at the **overtime rate** |
| Overtime | **125%** of the normal rate, on the hours the machine was available, counted over the whole month after the contracted hours |
| Breakdown | reduces the billed hours pro rata |
| Idle time caused by the customer | paid as working hours; a part month divided by the calendar days in it |
| Fuel | supplied by the customer, at an agreed **14 litres per working hour**; fuel while travelling not in the order |
| Extra kilometres | not in the order |
| Crew | **1 operator and 1 helper**; extra crew not in the order |
| Mobilisation | INR **1,50,000**, credited back if the crane stays more than **3 months** |
| Demobilisation | INR **1,50,000** |

**Save terms**. **Pass if** it says "Terms saved." and line 1 lists as missing only the **shifts** and the **crew food,
accommodation and travel** - the two things step 10 enters. If it lists anything else, the table above did not answer
it: say which.

### 10. The shifts and the crew's upkeep, line 1

The order also says the crane works **two shifts of 10 hours** a day at the one monthly rate, and that the customer
provides the crew's food and accommodation on site and pays their trip to and from the job.

In the same period, chapter **Working time**, card **Shifts**: *Shifts a day* `Two shifts`, *Shift 1 hours* `10`,
*Shift 2 hours* `10`, *The shifts are charged* `The same rate for every shift`. In **Overtime**, *On these shifts,
overtime is counted* `Per shift, beyond each shift's hours`.

Chapter **Extra charges**, card **Crew food, accommodation and travel** - for the **Operators**:

| Item | Choose | At a cost |
| --- | --- | --- |
| Food | `Provided by the customer` | |
| Accommodation | `Provided by the customer` | |
| Travel to and from the job | `Provided by the customer at a cost` | *Cost (INR)* `2500`, *The cost is* `per person per trip`, *The customer recovers it* `Deducted from PBL's invoice` |
| Daily travel to site | `Not in the Work Order` | |

Then press **Same as for operators**: the helpers take the same answers. **Save terms**.

**Pass if** line 1 now reads "Terms complete", and the helpers' travel shows the same cost as the operators'.
**Tell us:** is this how a real order states the crew's upkeep and shifts?

### 11. Billing terms, line 2

Line 2 > **Start billing terms**: **Shift** basis, INR **14,000** a shift, **8 hours** a shift, weekly off **Sunday**
(charged at the overtime rate), overtime INR **1,800 an hour**, breakdown pro rata, idle time paid as working hours, no
minimum guarantee, *Shifts a day* `One shift` of **8 hours**, fuel supplied by PBL and included in the rate, no extra
kilometres, crew **1 operator** and no helper, extra crew not in the order, no mobilisation or demobilisation charge.
The operator's **food is provided by the customer at a cost** of INR **150 per person per day**, deducted from PBL's
invoice; accommodation, travel to and from the job and daily travel are not in the order. **Save terms**.

**Pass if** line 2 reads "Terms complete", and the crew card asks only about operators - the order states no helper.

### 12. The holidays

Card **Holidays: PBL's calendar and this Work Order's changes**. Choose **The Work Order changes PBL's calendar as
listed**. In **PBL's calendar holidays inside the contract**, set **Diwali** to `Working day, overtime rate`, note
`Jetty works continue through Diwali.` Then **Add a holiday**: a date **20 days after the contract starts**, *Kind*
`Festival holiday`, *Description* `T1-Site festival, port users' holiday`. **Save holidays**.

**Pass if** it says "Holidays saved." and **Holidays that apply** shows two groups - "Line 1 - Gujarat" with Gujarat
Day on 1 May, "Line 2 - Maharashtra" with Maharashtra Day - Diwali as "Working day, every hour at the line's overtime
rate", and your festival as "added by this Work Order".

Then **tell Tester 3**: "My first Work Order (`WO-...`) is ready to plan."

---

## Part C - The second Work Order, at a central-government site

Open your second Work Order (`T1-PO-002`).

### 13. Site, contract, terms and holidays

- **Site and billing details**, line 1: *Site* `Contractor work, central PSU refinery shutdown`, *Central-government
  site?* `Yes`, billing GSTIN `24ZZZZH1001Z1ZZ`, the Registered Office. **Save details**.
- **Contract period**: from **10 days after day 0** to **40 days after day 0**, on a fixed date. **Save contract dates**.
- **Billing terms**: **Day** basis, INR **52,000** a day, **12 hours** a day, no weekly off - tick *The Work Order
  states the weekly off days* and leave every day unticked - work on a holiday at the overtime rate, overtime
  INR **4,500 an hour**, breakdown pro rata, idle time paid as working hours, no minimum guarantee, *Shifts a day*
  `One shift` of **12 hours**, fuel supplied by PBL and included in the rate, no extra kilometres, crew **1 operator
  and 1 helper**, extra crew not in the order, mobilisation and demobilisation INR **75,000** each. Crew food and
  accommodation **provided by the customer**; both kinds of travel not in the order - for the helper too (**Same as for
  operators**). **Save terms**.
- **Holidays**: **The Work Order follows PBL's calendar unchanged**. **Save holidays**.

**Pass if** the line reads "Terms complete" and **Holidays that apply** shows "Line 1 - Gujarat". Why is this site
**Yes**? (User Guide, 4.5.) Then **tell Tester 3**: "My second Work Order (`WO-...`) is ready."

---

## Part D - After Operations has planned

### 14. How often a machine is invoiced

When Tester 3 has allocated a crane on your first Work Order, open the allocation from the Work Order's **Machines
allocated**. *How often this machine is invoiced* `Monthly`, **Save the billing cycle**.

**Pass if** it is saved. Sales may do this (User Guide, section 5). **Tell us:** should Sales decide it?

### 15. Read what Operations planned

On both Work Orders, read **Resources needed** and **Machines allocated**.

**Pass if** you can tell, from the Work Order alone, which machine goes where, from when to when, and what is still
open. On your second Work Order one machine was **replaced** before the job: is the history clear?

---

## Part E - Things Sales may not do

### 16. Refused

| Try | Where | Pass if |
| --- | --- | --- |
| Add a requirement | a Work Order > *Resources needed* | No **Add a requirement** |
| Allocate, replace or free a machine | a requirement, or an allocation | "Your role can see the machines. Operations and Admin allocate them." |
| Upload Plum's report, record a certificate, add a rule | **Equipment** | Refused or not offered |
| Change PBL's holiday calendar | **Holiday Calendar** | Read only |
| See your reminders | **Alerts** | Empty: Sales is on no reminder path, by design |
| See business events | **Events** | Refused |

**Pass if** each is refused or not offered. If any works, report it straight away.

### 17. What you would actually need

- From an accepted offer to a Work Order Operations can plan: what slowed you down?
- Is anything on a real customer order missing from the billing terms?
- Would you want the sites and terms copied from the offer, rather than entered again?

**Pass if** you wrote your answers in the Feedback Log's notes for this step.

---

When you have finished, go on to [Your own data](PBL_HIRING_UAT_YOUR_OWN_DATA.md).
