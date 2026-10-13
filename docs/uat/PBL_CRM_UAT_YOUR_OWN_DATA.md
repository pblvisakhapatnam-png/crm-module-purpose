# Your own data, and trying to break it

**Do this last, after your own tester sheet is finished.** It has no script: you invent the work, and you try to make
the system fail. It is the most valuable part of the test - a script only finds the faults somebody already thought of.

Two to three hours, spread over several days if you like. Stop when you stop finding things.

## Two rules

**Every name you type starts `OWN-` and your tester number**, for example `OWN-T1-Sunrise Cement`. That is how we
tell your own data from the sheets' data. Never add to, or change, a record from the sheets in this part.

**Use PAN and GST numbers nobody else is using.** A GST number can exist only once in the whole system, so the second
person to type one is refused - correctly. Use your own block:

| Tester | Your PANs | Your GST numbers |
| --- | --- | --- |
| 1 | `ZZZZP1nnnZ` | a state code, your PAN, then `1Z` and a letter: `24ZZZZP1001Z1ZA` |
| 2 | `ZZZZP2nnnZ` | `27ZZZZP2001Z1ZA`, and so on |
| 3 | `ZZZZP3nnnZ` | (Operations cannot add numbers; keep it for Part B) |
| 4 | `ZZZZP4nnnZ` | `33ZZZZP4001Z1ZA`, and so on |

Replace `nnn` with any three digits - `001`, `002` and so on.

**What your login can do decides what you can invent.** Sales and the Sales Manager can take an enquiry all the way to
a Work Order. Operations and Accounts cannot make customers or offers: do Part A with the records you made `OWN-` names
on - market rates on an offer's lines, Work Orders, PAN and GST checks on a Sales tester's `OWN-` customer, with their permission - and
spend longer on Parts B and C.

Record each step below in the **Own data** tab of the Feedback Log, and every problem on its own row of **Findings**.

---

### 1. A real job, your way

Invent a customer and an enquiry of the kind you actually deal with: an awkward customer, an unusual machine, a job
with a strange duration or a difficult site. Take it as far as your login lets you.

**Pass if** you could do your actual job with this. Write down every place where the answer was no, "not quite", or
"only if I worked around it".

### 2. A required field left empty

Leave a required field empty and save. **Pass if** it is refused and names the field.

### 3. A PAN or GST number of the wrong shape

`ABC`, `12345`, a GST number one character short. **Pass if** each is refused and says what the right shape is.

### 4. A GST number already in the system

**Pass if** it is refused and says so.

### 5. A GST number that is not this customer's PAN

A GST number in the right shape whose middle ten characters are a different PAN. **Tell us** what happened, and
whether it should be refused.

### 6. Odd quantities and rates

A quantity of `0`, `-5` or `abc`; a rate with many decimal places. **Pass if** each is refused or clearly handled -
never silently rounded without telling you.

### 7. Dates far in the past or the future

An offer valid until a date ten years ahead; a Work Order received last year. **Pass if** what happens makes sense to
you.

### 8. A very long name, other languages and special characters

Paste a whole paragraph into a name; type notes in Hindi, Telugu or Gujarati, with `& < > " '`. **Pass if** it is
refused, or stored and shown back correctly without breaking the page.

### 9. Files

A file renamed to `.pdf` that is not really a PDF; a file over 25 MB. **Pass if** the first is refused because its
contents do not match its name, and the second is refused naming the limit.

### 10. A button pressed twice

Press **Save**, **Create** or **Record** twice quickly. **Pass if** one record is made, not two, and any message makes
sense.

### 11. The browser's Back button in the middle of a form

**Pass if** nothing strange happens and nothing is lost without warning.

### 12. Things out of order

Approve a quotation for an offer with no prices; record a customer's reply before the offer is sent; create a Work
Order from an offer the customer has not accepted; change an offer that is finished; record the same reply twice.
**Pass if** each is refused, and the refusal makes sense to you as a business person.

### 13. Repeat anything that failed

For every fault you found: write down what you did, start again from a clean screen, and do exactly the same again.
**Pass if** you recorded, for each fault, whether it happened the second time - both answers matter.

---

When you report a fault, give the record's code where it has one (`CO-000012`, `WO-000003`), the login, and roughly
what time it was: the system keeps its own record of every action, and those three let us find yours.
