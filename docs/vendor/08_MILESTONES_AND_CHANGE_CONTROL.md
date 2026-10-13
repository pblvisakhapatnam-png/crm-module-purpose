# 08 - Milestones, acceptance and changes

## Milestones are what we pay for

You will plan your work in sprints, or however suits you best. Sprints are your way of working; **milestones are what
PBL pays for**. A milestone is a business result PBL can see and check, at a fixed price.

Each milestone in your proposal states:

| Item | What it says |
| --- | --- |
| Business result | What PBL can do at the end that it could not do before, in plain words |
| Starting point | The version of the code it builds on |
| Included | The capabilities it delivers, by name from docs 02 and 03 |
| Not included | Anything a reader might assume is included but is not |
| What you need from PBL | Decisions, information, access, interfaces from outside systems - and by when |
| What it changes | The contracts and the database structure it touches |
| How it is accepted | The checks, written so that anyone can follow them: what should work, what should be refused, and what each role may and may not do |
| Automatic tests | The tests it adds, and that the full checks still pass |
| User testing | What PBL's staff will try, and how long it takes them |
| Documents and handover | The records it updates (contract, slice, acceptance) and any guide it adds |
| Finished means | The state it is left in: merged into `main`, deployed where agreed, records updated |
| Payment | Due when PBL accepts the milestone against the checks above |

Keep each piece of work small enough that a person can try it in 10 to 20 minutes. A milestone can contain several
such pieces.

## How a change reaches the main line

PBL owns the `main` branch. A change reaches it when:

1. it is in a pull request, up to date with `main`;
2. the combined automatic check, `Required validation`, has succeeded on exactly that version;
3. PBL's technical reviewer has accepted it;
4. PBL's staff have tried it, where it changes what a user sees; and
5. PBL has confirmed the merge.

Raise a pull request when the work is ready to be accepted, not before: every push to an open pull request runs the
full checks again (`AGENTS.md`, "Pull requests and CI cost").

## When something changes

Discovery is part of the work. You will find things we did not write down. This is how we will treat what you find:

| What you find | How we treat it |
| --- | --- |
| **Something you could reasonably have found in Phase 0**, inside the agreed scope | Part of the fixed price |
| **A necessary refactor** to deliver what was agreed | Part of the fixed price. If it is large, tell us early and we will look at it together |
| **An existing defect unrelated to the agreed work** | Tell us. We decide whether to fix it now; if we ask you to, it is priced on its own |
| **A new requirement from PBL** | A change request: you tell us what it does to price and dates; nothing starts until PBL agrees in writing |
| **A change you would prefer** - a different structure, library or style | Only with PBL's agreement, and at your cost, unless it is one of the reasons in `VENDOR_START_HERE.md`, "Ground rules" and we agree it is needed |

Please do not label ordinary discovery inside the agreed scope as a change request because it turned out to be
harder than expected. Equally, if we add to the scope, we expect to pay for it.

A change request is written in plain language: what changes, why, what it costs, how long it takes, and what else it
affects. PBL answers in writing.

## When something waits on PBL

Some work depends on a PBL decision or on an outside system (doc 03, groups H and I). Tell us as soon as you see that
a milestone will wait on one; we will agree together what it does to the dates. Until we decide, use the default doc
03 states.

## Your proposal

We will compare proposals line by line, so please price:

- each milestone of groups A and B;
- the two items doc 03 asks for on their own lines: credit exposure (group A) and the CRM side of PAN and GST
  validation (group I);
- each separately priced option in group C, on its own;
- any optional tidy-up from group D you recommend, on its own, with your reason;
- setting up hosting and handing it over;
- monthly support after go-live;

and state the warranty you offer after each milestone is accepted, your assumptions, and anything you have left out.
