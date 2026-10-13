# Feedback Form - Hiring user test

**Use the spreadsheet if you have it.** `PBL_HIRING_UAT_FEEDBACK_LOG.xlsx` has these same questions as
columns (tab **Findings**), one row per problem, with the choices already in drop-down lists, and a
tab for each tester's steps, where you record Pass or Fail for every step. It is easier to fill in
and far easier for us to read across the testers. The step results are only in the spreadsheet.

This document is the same thing in words. Use it if you would rather write than fill in a
spreadsheet, or to understand what a column is asking for. One block per problem; copy the block,
fill it in, and send it in whichever way you have been asked to.

**Before you write it up, check the User Guide's section 6 and the Tester Guide.** They list what has
deliberately been left out of this version. If what you found is on that list, you do not need to report it - but if you think it
was the wrong thing to leave out, say so: that is worth more to us than the fault.

**If in doubt, report it.** We would much rather read something already known than never hear about
something real.

---

## The block to copy

```text
1.  Your name and which login you used     :
2.  Date and roughly what time             :
3.  Which screen you were on               :
4.  Which record                           :   (for example WO-000001, RR-000003, AL-000002, EQ-000008)
    Which step of your sheet               :   (for example Tester 3, step 6; or Own data, step 5)

5.  What you were trying to do             :

6.  What you did, step by step             :
    1.
    2.
    3.

7.  What you expected to happen            :

8.  What happened instead                  :

9.  Did you try it again?                  :   yes, same thing / yes, different / no
    If different, what was different       :

10. How much did it get in your way?       :   stopped me / slowed me / annoying / just noting it

11. Screenshot attached?                   :   yes / no
```

---

## Why each line matters

Four of these are easy to leave out and hard for us to work without.

**Which login you used (1).** The same screen behaves differently for Operations and for the Fleet
Admin, on purpose. Half of "the button is missing" reports are the system working correctly. Tell
us who you were, and we will know immediately.

**Date and time (2).** The system keeps its own record of every action. If you tell us roughly when,
we can find your exact steps in it - even if you cannot remember them precisely.

**Which record (4).** The reference on the screen, like `AL-000002`. Without it we are searching for
a needle. With it we go straight to what you saw.

**Did you try it again (9).** This is the one that decides whether something gets fixed quickly. A
fault we can repeat is a fault we can fix with confidence. A fault that happened once and never
again is still worth reporting - say so, and say what was different the second time.

---

## What counts as worth reporting

All of these. Not just errors.

| | |
| --- | --- |
| It refused something it should have allowed | Report it |
| It allowed something it should have refused | Report it - this is the most serious kind |
| It refused correctly, but the message did not make sense | Report it |
| Wording that is wrong, unclear, or not how we speak | Report it |
| A number, date or name shown in a confusing way | Report it |
| A screen that made you stop and work out what to do | Report it |
| Something took far more clicks than it should | Report it |
| You could not find something you expected | Report it, and say where you looked |
| It behaved differently the second time | Report it, and say so in line 9 |
| You could do your job, but not the way you would want to | Report it - say how you would want it |

A screen that is merely ugly is worth mentioning once. A screen that is *confusing* is worth
reporting every time.

---

## If something looks badly wrong

If you think the system has lost data, shown you another customer's information when it should not
have, or let you do something that should clearly never be allowed - **stop, write it down
immediately, and tell the project owner directly** rather than only filling in a form.

Do not try to tidy it up yourself. What the system is left in is part of the evidence.

You cannot do any lasting damage: everything is invented practice data and a full backup is taken
every night.

---

## An example, filled in

```text
1.  Your name and which login you used     : A. Shah, uat-operations-01
2.  Date and roughly what time             : 13 October, about 3:40 in the afternoon
3.  Which screen you were on               : Allocate a machine (Resource Planning > the requirement)
4.  Which record                           : RR-000003
    Which step of your sheet               : Tester 3, step 9

5.  What you were trying to do             : Allocate a crane to the refinery line

6.  What you did, step by step             :
    1. Opened RR-000003 and clicked Allocate a machine to unit 1
    2. Clicked Find machines for these days
    3. Chose UAT-AC100-06 and ticked I have seen these warnings
    4. Clicked Allocate, with these warnings

7.  What you expected to happen            : The crane allocated, with its warning in plain view

8.  What happened instead                  : It was allocated, but on the allocation I had to open
                                             Eligibility to find the warning. I nearly sent the
                                             crane without the PUC being renewed.

9.  Did you try it again?                  : yes, same thing
    If different, what was different       : -

10. How much did it get in your way?       : slowed me

11. Screenshot attached?                   : yes
```

Notice what makes that example useful: it is not only "the warning was hard to see". It says what the tester
nearly did *because* of it. That is the part we could not have guessed.
