# N-06 - one way to show a business time

Status: built on branch `fix/n06-shared-time-formatter`, 12 October 2026, on PR #122's reviewed head `faf9a1ae` (the
entered-times fix, which added `readApiDateTime`), then moved onto `main` at `a19c3692`, #122's merge, whose tree is
the same as `faf9a1ae`'s. Frontend only: no backend
change, no migration, no API or contract change. Closes TB-1 register note N-06
(`docs/agent/tb-1/TB_1_DEFERRED_IMPROVEMENT_REGISTER.md`, section 5).

## Why

N-06 recorded two things. #93's guard (`components/dateTimeDisplay.test.ts`, TB1-604) failed only on a bare
`toLocaleString()`, so a page with its own reader, or its own formatter that names the zone, passed it. And nine pages
still kept their own reader (`backendDateTimeToDate`) and formatter (`formatDateTime`), in three text variants
(`docs/agent/slices/entered-times-in-india.md`, "Out of scope"). The design principles put DRY first
(`CODING_STANDARDS.md` section 1): one formatter, imported everywhere.

## What was found: eleven files, not nine

A search for every zone pattern, `timeZone`, `toLocaleString`/`toLocaleTimeString` and `Intl.DateTimeFormat` in
`frontend/src` found two more files than the note listed.

| File | Its own | Behaved like the shared formatter? | Now |
| --- | --- | --- | --- |
| `components/InteractionLog.tsx` | `backendDateTimeToDate`, `formatDateTime` | Yes (variant with blank lines; result wrapped in a template string) | imports `formatDateTime` |
| `pages/commercial-offers/CommercialOfferDetailPage.tsx` | the same | Yes (compact variant) | imports it |
| `pages/commercial-offers/CommercialOffersPage.tsx` | the same | Yes (compact) | imports it |
| `pages/leads/LeadDetailPage.tsx` | the same | Yes (blank lines) | imports it |
| `pages/opportunities/OpportunitiesPage.tsx` | the same | Yes (compact) | imports it |
| `pages/opportunities/OpportunityDetailPage.tsx` | the same | Yes (compact) | imports it |
| `pages/work-orders/WorkOrderAmendmentDetailPage.tsx` | the same | Yes (one-line `toLocaleString`) | imports it |
| `pages/work-orders/WorkOrderDetailPage.tsx` | the same | Yes (one-line) | imports it |
| `pages/work-orders/WorkOrdersPage.tsx` | the same | Yes (compact) | imports it |
| `components/DocumentsPanel.tsx` | `formatDocumentTime` (exported; also used by `pages/DocumentsPage.tsx`) | Yes | both files import `formatDateTime`; `formatDocumentTime` is gone |
| `components/OperationalReports.tsx` (the dashboard) | `formatTimestamp` | **No** - see below | imports `formatDateTime` |

Each file's `APP_DISPLAY_TIME_ZONE` constant went with its formatter; `InteractionLog.tsx` keeps
`APP_DISPLAY_TIME_ZONE_LABEL` for its "Times are shown in India time (IST)" line.

### Proof that the ten copies showed exactly what the shared formatter shows

Executed, not read (`docs/agent/technical-enablement/n06-proof-scripts/formatter-equality.mjs`, output in its
`outputs/`): each file's functions as they stood at `faf9a1ae` were cut from the source, transpiled with the image's
TypeScript and run beside `dateTimeDisplay.ts`'s `formatDateTime` on 21 inputs, in three browser zones
(`Asia/Kolkata`, `UTC`, `America/New_York`): `null`, `undefined`, `""`, `" "`, a tab, `"not a date"`, `2026-02-30T10:00:00`,
`2026-10-04 10:00:00`, a time with no zone, with microseconds, padded with spaces, 20:00 (next day in India), 31
December 19:00 (next year), `Z`, `z`, `+05:30`, `+0000`, `+00:00`, `-04:00`, microseconds with `+00:00`, and a date
alone. **The ten copies: 0 differences in 630 comparisons (10 files x 21 inputs x 3 zones).** Why it
holds: the copies answered `value || "-"` when they could not read a value, the shared one `"-"` for nothing and the
value itself otherwise - the same text for every input, blank text included (`" "` comes back as `" "` from both).

### The dashboard was the same defect as TB1-604

`formatTimestamp` read its value with `new Date(value)` and showed it with `toLocaleString("en-IN", { timeZone })`. A
time with a zone came out at the right moment, in another style ("4/10/2026, 3:30:00 pm"). A time without one was read
as the browser's own time: in India, 5 hours 30 minutes early. The dashboard gives it two times:

- *Live figures as at* - the report's `generated_at`, made by the server with its zone (`+00:00`): right moment, other
  style;
- **Recent Work Orders, Created** - `crm_work_order.created_at`, a `timestamp without time zone` (TB1-401), sent as
  `2026-10-12T01:19:54.266296` for a Work Order made at 06:49 in India. In the proof run under `Asia/Kolkata`,
  `formatTimestamp` showed the same kind of value, `2026-10-04T10:00:00` (15:30 in India), as "4/10/2026, 10:00:00 am".

P6 (TB-1) had read `formatTimestamp` as given only times with a zone; the Created column is the case it missed. Both
now show the shared style, "12 Oct 2026, 06:49 am", like every other page. One more change in what the dashboard
shows: text it cannot read now appears as it came, where `formatTimestamp` showed "-" - the server never sends such
text for these fields.

## The guard

`components/dateTimeDisplay.test.ts` keeps #93's test and adds a rule, `ownTimeHandling`, that reads the source with
TypeScript's own compiler and type checker (the frontend's `tsconfig.json`; `typescript` is already a dev dependency),
not as text. It runs over every source file but the two shared time modules - `dateTimeDisplay.ts`, and
`enteredDateTime.ts`, which turns a typed India time into UTC by adding `+05:30` and has its own guard - tests excluded.

**Reading.** However a page handles a time's zone, it can only read a time from the API's text by making a `Date`
from a string. So that is what the rule refuses, whatever came before it:

- `new Date(x)` (the constructor however reached) with one argument the type checker cannot show to be a number or a
  `Date` - a string, `any`, `unknown`;
- `Date.parse(...)`;
- a call to `readApiDateTime`: pages show times with `formatDateTime`. A page that needs an API time as a moment, to
  sort or compare, adds the function it needs to `dateTimeDisplay.ts` (as the backend's `business_time` rule does,
  `CODING_STANDARDS.md` section 2). No page needs one today.

Two string arguments are allowed, because neither is a time from the API: a date-only value read at a fixed time of
the day, written exactly `` `${value}T00:00:00` `` (any fixed `Thh:mm[:ss]`, nothing before the value) - how
`formatDateOnly` and the offer's expiry hint read a calendar date; and a string made from now itself,
`new Date(new Date().toLocaleString(...))` (`allocationState.ts`'s India today). The zone patterns and zone strings
the old copies used (`[+-]\d` in a pattern, `"Z"` or `"+00:00"` written out, `` `${value}Z` ``) are reported as well,
as early signs, but the guarantee rests on the rule above.

**Handing over.** A page could also prepare the text itself - check and add a zone its own way - and pass the result
to a shared function, never making a `Date`. So the two shared functions that take an API time, `formatDateTime` and
`enteredDateTime.ts`'s `apiDateTimeToIndiaInput`, are held to two rules wherever their name is used, however it was
imported or renamed (the type checker follows imports and re-exports, such as `pageSession.ts`'s):

- they are only called directly - `formatDateTime(...)`, `module.formatDateTime(...)`, `module["formatDateTime"](...)`,
  `(formatDateTime)(...)`. Any other use of the name is reported: `.call`, `.apply`, `.bind`, passing it as a value
  (`.map(formatDateTime)`), putting it in a variable or an object, destructuring it;
- what they are given is a record's field as the API sent it: a chain of property or element reads rooted in a
  variable (`row.created_at`, `creditReviews[0].reviewed_at`, `row?.created_at`), `null` or `undefined`, or a choice
  (`a ? b : c`, `??`, `||`) between such. Anything else - a local variable, a template, a call such as `.trim()` or
  `.replace(...)`, text joined with `+` - is reported.

Any use of `readApiDateTime` at all is reported. Every one of today's calls passes a field directly.

**Showing.** It reports a time of day shown by any of: `toLocaleString` called on anything the type checker cannot
show to be a number; `toLocaleTimeString`, `toString`, `toTimeString`, `toUTCString`, `toGMTString`, `getHours`,
`getMinutes`, `getSeconds`, `getMilliseconds` or their `getUTC` forms called on a `Date`, by name or by
`date["name"]`; or `Intl.DateTimeFormat` (however reached, `new` or not) or `toLocaleDateString` given options with
a time-of-day property - `hour`, `minute`, `second`, `fractionalSecondDigits`, `dayPeriod`, `hour12`, `hourCycle`,
`timeStyle` or `timeZoneName`. Options are read from the code where it shows them: an object literal (quoted keys and
spreads included) or a constant holding one, so `const options: Intl.DateTimeFormatOptions = { year, month, day }` is a
date. Options it cannot see - a parameter, a call's result - count as a time of day when their type allows one. A
method called on `new Date()` itself (now) is not reported. `toISOString`, `toJSON` and `getTime` are not reported:
with the reading rule a page's `Date` is now, a calendar date or a date-only value, never an API time, and the
calendar-date pages use `toISOString().slice(0, 10)` for date arithmetic.

It leaves alone numbers, whatever their options; dates without a time; India's today
(`Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date())`); calendar dates built with
`Date.UTC`; and the shared formatter.

The rule is tested on its own, through the same type checker: 32 shapes are each reported exactly as expected -
among them the pages' and the Documents panel's copy, the dashboard's call, the reviewer's examples (a zone check written as
an alternation with `.replace(/$/, "$&Z")`, both before `new Date(...)` and handed to `formatDateTime`;
`formatDateTime.call(undefined, row.created_at + "+" + "05:30")`, `.apply`, `.bind`, `.map(formatDateTime)`;
`date["toLocaleString"]`, the `getUTC` methods, quoted, spread, variable and parameter `Intl` options, a `Date` given
`{ useGrouping: false }`) - and 11 allowed shapes are not, among them `count.toLocaleString("en-IN")`, a typed
date-only options constant, and `formatDateTime` and `apiDateTimeToIndiaInput` called directly with fields, optional chains, a choice between them, or through parentheses. The scan also checks that it still finds
`dateTimeDisplay.ts`'s own reading and formatting, so a broken scan cannot pass by finding nothing. The whole scan
takes about 15 seconds: it asks the type checker what every name refers to.

**Shown to fail.** Run on `faf9a1ae`'s source with only the new test file added, the scan fails with 42 findings in
exactly the eleven files above and no other, and each of the eleven is caught by the reading rule alone ("makes a Date
from a string"); #93's test passes on that same source, which is N-06's gap. On this branch it passes.

**What it does not catch.** A `Date` turned into text without a method call (`` `${date}` ``, `String(date)`), a
`Date` made outside the frontend's source (a library), a page that shows an API time without reading it as a time at
all (printing the API's text as it is), text the page builds into a record of its own and then hands over as that
record's field, and the date part cut from an API time and read as a calendar date
(`` `${time.slice(0, 10)}T00:00:00` ``, UTC's day). None exists today; the last is date-only, which the brief left alone.

## Out of scope

- **India's today in five places** (`pages/equipment/MachineCertificates.tsx`, `MachinePage.tsx`, `PlumReportPage.tsx`,
  `pages/work-orders/workOrderContractPeriodState.ts`'s `indiaToday`, `pages/allocations/allocationState.ts`'s
  `todayIso`): dates, correct, and not an API time; a DRY move of its own if wanted.
- **`formatDateOnly`'s copies** on the offer, Opportunity and Work Order pages: date-only values read at local
  midnight and shown as that calendar day in any zone. Correct; not the same defect.
- **The offer page's expiry hint** (`CommercialOfferDetailPage.tsx`, `valid_until` at 23:59:59 against now) compares
  in the browser's zone. Right in India; date-only; not touched.
- The TB-1 evidence scripts (`docs/agent/tb-1/evidence-scripts/P6_frontend.mjs`, `P8_frontend.mjs`) name the removed
  functions; they are a dated record of the baseline and are not run by CI.

## Contracts and records changed

- No contract: the API is untouched.
- `docs/agent/tb-1/TB_1_DEFERRED_IMPROVEMENT_REGISTER.md`, N-06: closed, dated. `docs/agent/tb-1/TB_1_TEST_COVERAGE_GAPS.md`,
  row 22: a dated note.
- `docs/agent/CODING_STANDARDS.md` section 7 and `AGENTS.md` ("Date/time display rule"): show a business time with
  `formatDateTime`, never a page's own.
- `docs/agent/UI_UX_CARRY_FORWARD.md`: the "Nine pages still carry their own correct copy" line reconciled.
- Acceptance: `docs/agent/acceptance/n06-one-way-to-show-a-time-acceptance.md`. Continuity:
  `docs/continuity/N06_ONE_WAY_TO_SHOW_A_TIME.md`, `docs/continuity/NEXT_STEPS.md`.

## Authority and required reading

- TB-1 register note N-06; finding TB1-604 (`TB_1_FINDINGS_REGISTER.md`) and its fix #93; TB1-401 (the CRM tables'
  times without a zone)
- `docs/agent/slices/entered-times-in-india.md` ("Out of scope" lists the nine) and PR #122, which added
  `readApiDateTime`
- AGENTS.md, "Date/time display rule"; ADR-028 ("Timestamps"); `CODING_STANDARDS.md` sections 1 (DRY first) and 7
- `docs/agent/contracts/reports-contract.md` (the handoff report's `created_at` source column)
- `docs/agent/UI_UX_CARRY_FORWARD.md` (the shared formatter's entry)
