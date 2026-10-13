# Your own data, and trying to break it

**Do this last, after your own tester sheet is finished.** No script: you invent the work, and you try to make the
system fail. It is the most valuable part of the test - a script only finds the faults somebody already thought of.

Two to three hours, spread over several days if you like. Stop when you stop finding things.

## The rules

**Every name you type starts `OWN-` and your tester number**, for example `OWN-T1-Narmada Cement`. That is how we tell
your own data from the sheets'. Never add to, or change, a record from the sheets in this part.

**PAN and GST numbers:** Sales uses PAN `ZZZZQ1nnnZ` (replace `nnn` with any three digits) and GST numbers made from it
- a state code, the PAN, `1Z`, then a letter, for example `24ZZZZQ1001Z1ZK`. A GST number can exist only once in the
system.

**The fleet is shared.** A machine you allocate is not free for anyone else on those days. Allocate on your own `OWN-`
Work Orders only, and free what you allocated when you are done. The Fleet Admin may record papers on any machine, but
tells the others before withdrawing a paper on a machine allocated on Tester 1's Work Orders.

| You are | Your own work |
| --- | --- |
| Tester 1, Sales | `OWN-T1-` customers, offers and Work Orders, their sites, terms and holidays |
| Tester 2, Fleet Admin | Papers, kit and rules on the fleet; a year of the holiday calendar far ahead (2030); never the current year's |
| Tester 3, Operations | Requirements and allocations on Tester 1's `OWN-T1-` Work Orders, by agreement - or ask Tester 1 for one |
| Tester 4, Accounts | Read anything; try the things you should not be able to do |

Record each step below in the **Own data** tab of the Feedback Log, and every problem on its own row of **Findings**.

---

### 1. A real job, your way

Invent the kind of work you actually deal with: an awkward site, an odd crane, a job that runs over a holiday, a
machine whose papers run out half-way. Take it as far as your login lets you.

**Pass if** you could do your actual job with this. Write down every place where the answer was no, "not quite", or
"only if I worked around it".

### 2. Wrong numbers in a requirement

A requirement for **0** machines, or a capacity of `abc`; one ending before it starts, or outside the contract.
**Pass if** each is refused, naming the field, or clearly flagged.

### 3. Wrong certificates

A certificate issued **in the future**, or valid until **before** it was issued; a permit with no state; "Not
applicable" with no reason. **Pass if** each is refused, with the reason.

### 4. Copies

A copy that is not really a PDF (a renamed file); a very large copy. **Pass if** the first is refused because its
contents do not match its name, and the second names the limit.

### 5. Kit

More counterweights on a trip than the set has free; a piece that travels with another crane on those days. **Pass
if** each is refused, saying how many are free or where the piece is.

### 6. Holidays and terms

A holiday outside the contract period; a working day with no rate chosen; a billing rate of `-5`, or with many decimal
places. **Pass if** each is refused or clearly handled - never silently rounded.

### 7. A button pressed twice

Press **Allocate**, **Save terms** or **Create Work Order** twice quickly. **Pass if** one record is made, not two, and
any message makes sense.

### 8. The browser's Back button in the middle of a form

**Pass if** nothing is lost without warning.

### 9. Things out of order

Allocate on a line with no site, or with "Central-government site?" unanswered; allocate a machine already allocated
elsewhere on the same days; replace a machine with one that cannot be allocated; free a machine already freed; change
a Work Order's site after a machine is allocated - what happens to the allocation's answer? **Pass if** each is refused
or clearly handled, and the reason makes sense to you as a business person.

### 10. Repeat anything that failed

For every fault you found: write down what you did, start again from a clean screen, and do exactly the same again.
**Pass if** you recorded, for each fault, whether it happened the second time - both answers matter.

---

When you report a fault, give the record's code (`WO-000002`, `RR-000003`, `AL-000004`, `EQ-000021`), the login, and
roughly what time it was: the system keeps its own record of every action, and those three let us find yours.
