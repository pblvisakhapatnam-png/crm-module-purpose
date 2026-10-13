# Tester 4 - Accounts

**Sign in as `uat-finance-01`.** Read the [Tester Guide](PBL_CRM_TESTER_GUIDE.md) first. Then work through this
sheet, and record **Pass** or **Fail** for every step in your tab of the Feedback Log. The numbers you type have a `4`
after `ZZZZM`, so they clash with nobody's.

In the CRM, Accounts does a small job that **nobody else can do**: it marks a customer's PAN **Verified** or
**Rejected / Incorrect**, and can choose those states for a GST number **when it adds one**. Sales can only enter them as
not yet checked. A GST number already added cannot be changed today, by anyone. Accounts can also attach documents to a
customer. It reads everything else and changes nothing else.

Your customers come from the Sales testers. **Start with Part A**, which needs nobody. If you are doing every sheet
yourself, follow the [one-person route](PBL_CRM_UAT_ONE_PERSON_ROUTE.md) instead.

| Who | What you do for them |
| --- | --- |
| Tester 1, Sales Executive | Check `T1-Kakinada Steel & Ferro Alloys` and `T1-Trident Marine Works Private Limited` (Parts B and D) |
| Tester 2, Sales Manager | Check `T2-Nordhavn Offshore Wind India` (Part C) |

---

## Part A - What Accounts may not do

### 1. Refused

| Try | Where | Pass if |
| --- | --- | --- |
| Create a Lead | **Leads** | No **Create Lead**, or refused |
| Create a customer | **Accounts** | No **Create Account**, or refused |
| Create an enquiry | **Opportunities** | No **Create Opportunity**, or refused |
| Create an offer | **Commercial Offers** | No **Create Commercial Offer**, or refused |
| Read the business events | **Events** > **Load recent events** | Refused |

**Pass if** every one is refused or not offered. If any works, report it straight away.

---

## Part B - Checking a customer's numbers

### 2. What is waiting

When Tester 1 says `T1-Kakinada Steel & Ferro Alloys` is ready, open it from **Accounts**, section **Tax identity**.

**Pass if** you can see the PAN and the four GST numbers, each "Entered - Not Verified".

**Tell us:** if forty customers were waiting, could you find them and work through them from these screens? What
would you need?

### 3. The PAN is correct: verify it

Treat the PAN as checked against the PAN card. **Update PAN details**: keep the PAN as it is, *PAN verification state*
`Verified`, *Remarks* `T4 - checked against the PAN card copy.` **Save PAN Profile**.

**Pass if** the PAN now shows Verified. **Tell us:** can you see who checked it, and when?

### 4. A GST number entered by Sales

Try to mark `37ZZZZM1001Z1ZZ` (Andhra Pradesh) as Verified.

**Pass if** you find out how, or find that it cannot be done. Today a GST number cannot be changed once it is added,
so a number Sales entered stays "Entered - Not Verified". **Tell us how this should work**: the gap is known and recorded
for later (it waits for SurePass or an audited manual route), and your answer helps shape it.

### 5. Attach the PAN card copy

On `T1-Kakinada Steel & Ferro Alloys`, **Documents**: choose any small file of your own, *Document type* `PAN`,
*Remarks* `T4 - PAN card copy (practice file).` **Upload**.

**Pass if** it says "File added: ..." and **Download** gives it back. **Tell us:** nothing removes a wrong file today.
How often would that matter?

---

## Part C - A number that is wrong

### 6. Reject a PAN

When Tester 2 says `T2-Nordhavn Offshore Wind India` is ready, open it. Treat its PAN as wrong: the name on the PAN
card is a different company. **Update PAN details**: *PAN verification state* `Rejected / Incorrect`, *Remarks* `T4 - name on the PAN card does not match the customer.` **Save PAN Profile**.

**Pass if** the PAN shows Rejected / Incorrect with your remarks.

**Tell us:** is it obvious to Sales that this number is wrong? Tester 2's offer for this customer carries on - nothing
stops it today. What should happen?

---

## Part D - A customer with no numbers yet

### 7. Add the numbers yourself

Open `T1-Trident Marine Works Private Limited` - Tester 1's customer made from a Lead. It has no PAN yet.

**Update PAN details**: *PAN* `ZZZZM4001Z`, *PAN verification state* `Verified`, *PAN legal name*
`T1-Trident Marine Works Private Limited`. **Save PAN Profile**.

**Add GSTIN**: *GSTIN* `37ZZZZM4001Z1ZZ`, *State code* `37`, *State name* `Andhra Pradesh`, *GSTIN verification
state* `Verified`, *Primary GSTIN* ticked. **Add GSTIN**.

**Pass if** both are saved as Verified.

**Tell us:** how would you have known this customer was waiting for its numbers, without being told?

### 8. A GST number already in the system

On the same customer, **Add GSTIN** `37ZZZZM1001Z1ZZ` - the number already on `T1-Kakinada Steel & Ferro Alloys` -
state code `37`.

**Pass if** it is refused: "GSTIN already exists in the Account GSTIN register."

### 9. Numbers of the wrong shape

On the same customer, try each in **Add GSTIN** or **Update PAN details**, one at a time:

| Try | Pass if |
| --- | --- |
| GSTIN `37ZZZZM4001Z` (too short) | Refused, saying what is wrong |
| GSTIN `24ZZZZM4002Z1ZZ` with *State code* `37` | Refused: the state code must match the first two digits |
| PAN `ZZZZ4001Z` | Refused, saying what is wrong |

**Pass if** each is refused with a message you understand. Do not leave a wrong number saved: if one is accepted,
report it.

---

## Part E - What Accounts may not change

### 10. Read, but not change

On Tester 1's offer (ask them for its code):

| Try | Pass if |
| --- | --- |
| Change a line or a rate | Not offered |
| Add a market rate to a line, choose a line's basis rate, or attach a vendor quote | Not offered; you can read the rates, each line's basis history and download the quotes |
| Generate or approve a quotation | Not offered |
| Record the customer's reply | Not offered |
| Create a Work Order from an accepted offer | Not offered |

**Pass if** each is refused or not offered. If any works, report it straight away.

### 11. What you would actually need

- Before marking a number Verified, what would you want to see?
- What should happen to an offer, a quotation or a Work Order for a customer whose PAN is rejected?
- Is there anything on these screens you would never use?

**Pass if** you wrote your answers in the Feedback Log's notes for this step.

---

When you have finished, go on to [Your own data](PBL_CRM_UAT_YOUR_OWN_DATA.md).
