# PBL CRM test - Guide for Testers

What the CRM does, in plain words, and how this test runs. Read it before your sheet, and keep it open while you test.

## What the test is

- It tests the **CRM part** of PBL's new system: from a first enquiry to the customer's order.
- The site is **the CRM test site**. It starts **empty**: you type in everything yourself, from your
  sheet.
- **All the data is invented.** Never type a real customer, rate, PAN or GST number.
- Use it the way you would do your daily work. Tell us what is confusing, slow, missing or wrong.

## Signing in

You sign in twice:

1. A **shared site login** (a box the browser shows). It keeps the test site private.
2. **Your own username and password.** What you can see and do depends on your job.

Both are given to you separately. Do not share them. The same username and password also work on the Hiring test site.
Five wrong passwords in 15 minutes stop your username for 15 minutes; the sign-in page says so.

## Who does what

Up to four testers, each with **one job and one set of data**:

| Tester | Job | Sign in as | Your sheet | Your names start |
| --- | --- | --- | --- | --- |
| 1 | Sales Executive | `uat-sales-01` | [Tester 1 - Sales Executive](PBL_CRM_UAT_TESTER_1_SALES.md) | `T1-` |
| 2 | Sales Manager | `uat-manager-01` | [Tester 2 - Sales Manager](PBL_CRM_UAT_TESTER_2_SALES_MANAGER.md) | `T2-` |
| 3 | Operations | `uat-operations-01` | [Tester 3 - Operations](PBL_CRM_UAT_TESTER_3_OPERATIONS.md) | `T3-` |
| 4 | Accounts | `uat-finance-01` | [Tester 4 - Accounts](PBL_CRM_UAT_TESTER_4_ACCOUNTS.md) | `T4-` |

When one person does all four, they follow the [one-person route](PBL_CRM_UAT_ONE_PERSON_ROUTE.md): which login, in
which order, with which data.

## How the test runs

| | What you do |
| --- | --- |
| **First** | Read this guide |
| **Your sheet** | Work through it in order, with its data, exactly as written. Some steps hand work to another tester: the sheet says whom, and what to do meanwhile |
| **Your own data** | Only when your sheet is finished: [Your own data](PBL_CRM_UAT_YOUR_OWN_DATA.md). Invent your own work and try to break the system. Every name starts `OWN-` |
| **Throughout** | The **Feedback Log**: **Pass** or **Fail** for every step of your sheet, in your own tab, and one row in **Findings** for every problem, at the time |

## Rules of the test

- **Use only your own sheet's data**, typed exactly as written: do not shorten it, correct it or use your own names
  instead. The long names and odd addresses are there on purpose.
- **Never mix your own data into a sheet.** Your own data comes last, and every name in it starts `OWN-`.
- **Look at anything; change only your own records**, unless your sheet tells you to work on another tester's.
- **Never edit one customer, Lead, enquiry, Work Order amendment or conversation in two tabs at once.** A Commercial
  Offer and its lines refuse a save from a tab opened before someone else's (Tester 2 checks it); those records do not
  yet, so the later save would quietly overwrite the earlier one.
- **Your job is to find faults.** If a step does not do what the sheet says, it has **failed**: write down what
  happened, then carry on with the next step. If something goes wrong, do it again: a fault we can repeat is a fault
  we can fix.
- **Everyone can see every record** in this test, including other testers' customers. That is known, and is being
  recorded for later; tell us who should see what.

## How work moves through the CRM

```text
Lead       ->  Account + Opportunity  ->  Commercial Offer  ->  Quotation  ->  Customer reply  ->  Work Order
(enquiry)      (customer + enquiry)       (what we offer)       (document)     (won, lost ...)      (handed over)
```

1. **Lead** - a new enquiry. You call, email and meet, and note what happened. If it is worth pursuing, you qualify it
   and **convert** it.
2. **Converting** creates an **Account** (the customer company) and an **Opportunity** (this particular enquiry).
   An Account can also be typed in by hand, and an Opportunity created and then linked to its Account.
3. **Commercial Offer** - what we offer for that enquiry: the lines, the market rates behind them, and the terms.
4. **Quotation** - the document made from the offer. A Sales Manager approves it before it is sent.
5. **Customer reply** - accepted, lost, wants a revision, on hold, and so on.
6. **Work Order** - when the customer accepts, Sales or Operations makes the Work Order from the offer, with the
   customer's own order reference. This hands the order over.

## Jobs

| Job | What it does in the CRM |
| --- | --- |
| Sales Executive | Works enquiries from Lead to Commercial Offer, **chooses which market rate the offer is priced on**, makes quotations and records the customer's reply |
| Sales Manager | Everything a Sales Executive does, and **approves** a quotation before it goes to the customer |
| Operations | **Enters the market rates** collected from vendors against an offer, and **makes the Work Order** once the customer accepts. Cannot make Leads, customers, enquiries or offers |
| Accounts | Reads everything; **marks a PAN Verified or Rejected** - nobody else can - adds PAN and GST numbers, choosing Verified or Rejected when adding a GST number, and attaches documents. A GST number already added cannot be changed, by anyone |

If a button you expect is missing, check which login you are using: some buttons show only to some jobs, on purpose.

## The menu

| Menu item | What it is for |
| --- | --- |
| Dashboard | The pipeline at a glance: offers by stage, offers waiting for a reply, accepted offers waiting for a Work Order, Work Orders made |
| Accounts | Customer companies: contacts, addresses, PAN, GST numbers, documents and conversations |
| Leads | New enquiries, and the calls, emails, meetings and notes about them |
| Opportunities | One for each enquiry, RFQ or tender from an Account |
| Commercial Offers | What we offer and quote. See below |
| T&C Library | Standard terms and conditions you can attach to an offer. The wording is sample wording, not legally final |
| Work Orders | Orders made from accepted offers |
| Documents | The most recent files across the system, including generated quotations |
| Events | The history of who did what, and when. Only Admin and Management see it |

The menu also lists the Hiring part's pages (Holiday Calendar, Resource Planning, Allocations, Equipment, Alerts).
They belong to the Hiring test, on its own site; ignore them here. The **Menu** button at the top hides and shows the
menu.

**Codes.** An offer has a code such as `CO-000012`, and a Work Order `WO-000003`: use them when you report a problem.
Leads, Accounts and Opportunities have no code of their own; give their name. Long grey codes under a name are the
record's internal reference - ignore them.

All times are India time.

## Two places to note a contact on a Lead

A Lead has **Follow-up activities** - a call, email, meeting or note with an outcome and the **next follow-up date** -
and **Conversations / Interactions**, the conversation log that Accounts and Opportunities have too. Tell us whether
both are needed.

## Files

An Account and a Commercial Offer each have a **Documents** section: the files attached to that record, and a form to
upload another. PDF, Word, Excel, PNG, JPG, text and CSV files up to 25 MB are accepted. The system checks that a file
is the kind its name says - a file named `.pdf` must be a PDF. Who may upload: to an Account, Admin, Sales, the Sales
Manager and Accounts; to an offer, Admin, Sales, the Sales Manager and Operations.

## The Commercial Offer page

It has five tabs. Two have a **Jump to** row.

- **Overview** - the offer's customer, enquiry, status, value and dates, and its documents.
- **Lines & Pricing** - the lines we quote (description, quantity, unit, rate, currency, amount). Under each line,
  its own **market rates** that Operations collected, with the vendor's quote attached. Sales chooses one rate per
  line as its **basis**, with a reason; it need not be the cheapest. Changing the basis needs a reason too, and the
  line's **basis history** keeps every earlier choice: "Was the basis until ..., chosen by ...". When one quote covers
  several lines, it is attached to one line's rate and the other lines' rates point to it.
- **Terms & Conditions** - the standard clauses attached to this offer.
- **Submission** - from preparing the offer to the customer's reply: where it stands; a readiness checklist (it
  advises, it does not stop you) and the credit review; the quotation and its submission; the customer's response and
  the offer's versions.
- **Traceability** - links to the enquiry, the customer, the Work Orders made from this offer, and related offers.

**A sent offer is settled, and a change is a new version.** Once an offer is recorded as submitted, that version is
frozen: what the customer received stays exactly as sent. To change it, on the Submission tab, card **Offer versions**,
press **Make a new version**: it copies the offer, its lines, each line's market rates and basis rate, T&C and
current credit review into an
editable Draft - the same code, `CO-000012 v2`. Make the change, generate and approve a quotation, record how it was
sent, and record it as submitted: the old version then reads "Replaced by v2" and stays as history. A version being
prepared can be abandoned (**Abandon this version**); the sent one is unchanged. The customer's reply and the Work Order
go on the latest version. An enquiry has only one live offer at a time.

**Currency.** An offer is in Indian rupees unless you choose otherwise: an offer, each line and each market rate may be
in **INR, USD, GBP or EUR**. Nothing is converted, and amounts in different currencies are never added together -
reports show each currency separately.

### What the status labels mean

| Label | Means |
| --- | --- |
| Commercially active | **Yes** while the offer is live, including after the customer accepts it. **No** once it is lost, withdrawn or closed |
| Can make a new version | **Yes** on the latest Submitted version - sent, with no win or loss recorded - when no later version is being prepared |
| Can record a customer response | **Yes** once the offer has been submitted, including after the customer accepts it. A **lost** offer is final |
| Ready to create the Work Order | **Yes** once the customer has accepted, the offer is linked to an Account and has an active line; **Yes, for what is not on a Work Order yet** when part is already on one; **Already created** when everything is |

### Quotations

- **Generate quotation document** makes a quotation from the offer's current lines and terms. Each time you generate,
  you get a new **version** (`/V1`, `/V2`); old versions are kept and marked superseded. A new version of the offer
  (above) starts its own quotations again at `/V1`: `CO-000012 v2/V1`.
- A new version starts as **Draft**. Only a Sales Manager (or Admin) can **Approve for Issue**.
- A version cannot be approved if a line has **no rate**, or if the offer **changed after** the version was made. The
  page says why. Generate a new version and approve that.
- The quotation is a web page. To make a PDF, open it and use your browser's **Print**, then **Save as PDF**.

## The Work Order, and why the CRM makes it

When the customer accepts, the offer page shows **Create Work Order** at the top. The Work Order is the hand-over from
Sales to the people who do the work.

- It asks for the **customer's own order reference** - their purchase order, or a Letter of Intent's number. It is
  required. **One customer order makes one Work Order**: a reference already used on that offer is refused.
- Every accepted line is ticked, with all of its quantity. **A customer may award the work in parts**: untick a line,
  or lower its quantity, and a later Work Order - for the next customer order, with its own reference - takes only
  what is left. Nobody can put more on Work Orders than the offer holds.
- Each Work Order line stays linked to the offer line it came from, so what is later billed can be traced to what was
  quoted.
- It stops at **"Awaiting release to Ops"**. Setting the customer up in Finance, the working terms of each line,
  releasing it to Operations, machines, crew, log sheets and billing come after it - most of them in the Hiring part,
  tested on its own site.

**After the order.** A **Work Order Amendment** records a change the customer asks for after ordering; validating one
does not yet change the Work Order. A **Supplementary offer** (extra lines or quantity) and a **Change quotation** (a
revised price for work already ordered) are new offers linked to the original.

## Not in the system yet - please do not report these

| Thing | Position |
| --- | --- |
| Markup rules over the basis rate | Not built. Being recorded for later |
| Credit limit checks | Not built. The credit review is a manual record only |
| GST calculation on the quotation | Not built |
| Sending the quotation by email from the system | Not built. Download it and send it yourself |
| A PDF quotation made by the system | Print the web page from your browser |
| Releasing a Work Order, machines, crew, log sheets and billing | Not in the CRM. A Work Order stops at "Awaiting release to Ops" |
| Deleting a file uploaded by mistake | Not built. Tell us, and we remove it |
| Changing a GST number once added | Not built. Tell us how it should work |
| Seeing only your own customers | Not built. Every job sees every record in this test |
| A report of each person's own work | Not built. Reports group by status only |
| Choosing a customer's owner from a list of names | Not built. The owner field takes an internal ID |

If you think something on this list should not have been left out, say so. That is worth more to us than a fault.

## Reporting

The **Feedback Log** is a spreadsheet with a tab for each tester's steps, one for your own data, and **Findings**:

- In **your tab**, give every step a result: **Pass**, **Fail**, **Could not try** (an earlier step failed, or another
  tester has not got there), or **Not done**. For a Fail, write the Findings row number beside it.
- In **Findings**, one row per problem, at the time. It asks for four things that are easy to leave out and hard for
  us to work without: **which login** you used, **roughly what time** it was, **the record's code** (or name), and
  **whether it happened again**.

If you are not sure whether something is a fault, report it. A screenshot helps a lot. If you think the system has lost
data, shown you something it should not have, or let you do something your job should not allow, tell the person
running the test straight away, and leave the screen as it is.
