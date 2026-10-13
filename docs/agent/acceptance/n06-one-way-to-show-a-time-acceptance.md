# N-06 acceptance - one way to show a business time

Slice record: `docs/agent/slices/n06-one-way-to-show-a-time.md`. Frontend only: no backend, migration, API or contract
change. Closes TB-1 register note N-06.

## Automated checks

Run on branch `fix/n06-shared-time-formatter` (built on PR #122's head `faf9a1ae`; `main` at `a19c3692`, #122's merge,
has the same tree) through the AGENTS.md frontend sequence, in a port-free Compose project (`pbl-n06`) with the working tree mounted.

| Check | Result |
| --- | --- |
| `npm run typecheck` | Clean |
| `npm test` | 33 files, 626 tests passed |
| `npm run build` | Built; one bundle of 1,061.16 kB (Vite's 500 kB warning, as before: register note N-04) |
| `components/dateTimeDisplay.test.ts` | 8 tests (5 before). `formatDateTime`: no zone read as UTC and shown in India's time; a zone kept; the next day across midnight; `null`, `undefined` and `""` give "-", unreadable and blank text come back as given. `readApiDateTime`: no zone read as UTC, an offset kept, `null` for nothing, blank or unreadable. #93's bare-`toLocaleString()` scan, unchanged. The new rule, which reads the source through TypeScript's type checker, reports each of 32 shapes exactly as expected and none of 11 allowed ones (numbers, dates without a time, India's today, calendar dates, typed date-only options, the shared functions called directly with fields). The scan over every source file but the two shared time modules finds nothing, and still finds `dateTimeDisplay.ts`'s own reading and formatting (about 15 seconds) |
| `components/enteredDateTime.test.ts` | 10 tests passed; unchanged |
| Formatter equality (`docs/agent/technical-enablement/n06-proof-scripts/formatter-equality.mjs`, output in `outputs/`) | The ten copies, run as they stood at `faf9a1ae` beside the shared formatter: 0 differences in 630 comparisons (21 inputs x 3 browser zones each). The dashboard's `formatTimestamp`: 18 of 19 inputs differ in each zone - another style everywhere, and in India a time with no zone 5 hours 30 minutes early ("4/10/2026, 10:00:00 am" for 15:30) |
| Frozen handoff contract | SHA-256 `0f16ff22...cd39080` at `main`, at `faf9a1ae` and on this branch |

**Undo proof.** `faf9a1ae`'s `frontend/src` (from `git archive`) with only the new `dateTimeDisplay.test.ts` copied in:
the scan test fails with 42 findings in exactly the eleven files the package changes and no other file - each of the
eleven caught by the reading rule ("makes a Date from a string") alone - while #93's bare-`toLocaleString()` test
passes on the same source, the gap N-06 recorded. The working tree was not touched.

## Manual check (about 5 minutes)

**Who**: any signed-in user who can see the dashboard and Work Orders (`sales1`, Sales User). **Where**: a local stack
or test site carrying this package, browser in India's time. **Data**: any Work Order (smoke-data scenario
`accepted-offer-with-work-order` makes one).

1. Note the time now in India. Open the **Dashboard**. *Live figures as at* reads like "12 Oct 2026, 06:50 am" - the
   current time in India, in the same style as every other page (before, in the style "12/10/2026, 6:50:12 am").
2. In **Recent Work Orders**, the Created time of a Work Order made just now reads the current India time (before: 5
   hours 30 minutes earlier).
3. Open **Work Orders**, then that Work Order: *Created*, *Created at*, *Last updated* and its event's time read the
   same.
4. Open the source **Commercial Offer** (*Submitted at*, *Created*, *Updated*) and its **Opportunity** (*Created*,
   *Updated*); the Opportunities and Offers lists. All read the same time.
5. On any Account or offer with an uploaded document, its documents list and the **Documents** page show the
   *Uploaded* time in the same style.

Negative path: none - nothing new is refused. Permission path: unchanged; no route or role is touched.

**Exploratory check done, 12 October 2026 (06:50 IST)**, on the lane stack (`pbl-n06`, page server on
`127.0.0.1:3101`, scenario `accepted-offer-with-work-order`, run `te1-1cb2b9fa`) in the in-app browser, browser zone
Asia/Kolkata, signed in as the local demo user. The pane was hidden, so pages were read by a page script. The API sent
the Work Order's `created_at` as `2026-10-12T01:19:54.266296` (no zone). The dashboard read "Live figures as at 12 Oct
2026, 06:50 am" and the Work Order's Created "12 Oct 2026, 06:49 am"; the Work Orders list, the Work Order page (its
Created at, Last updated and creation event), the Offers list, the offer's Submitted at, the Opportunities list and the
Opportunity's Created all read "12 Oct 2026, 06:49 am". Not opened by hand: the Lead page, the conversation log, the
Work Order Amendment page and the Documents panel and page - the scenario makes none of their records; the equality
proof holds them.

## Deferred and known gaps

- The scan does not catch a `Date` turned into text without a method call (`` `${date}` ``), a page printing the
  API's text as it is, or the date part cut from an API time and read as a calendar date (slice record, "What it does
  not catch"); none exists.
- India's today is worked out in five places, and `formatDateOnly` is copied in five pages: dates, correct, left alone
  (slice record, "Out of scope").
- No component test renders a page (`DEFERRED_REQUIREMENTS.md`, "Frontend component-test capability"): the pages'
  wiring is held by the typecheck (each import resolves), the source scan and the screen check.

## Self-review (AGENTS.md step 8)

`/code-review` at high effort on the first, text-matching guard: six findings, all on the guard - an escaped minus in a
zone pattern, `.concat("Z")`, a call inside a number's `toLocaleString` arguments (fixed then); an object key named
`hour` or `minute` failing wrongly, date-only display of an API time, and `sourceFiles` copied in two test files (left).
review rounds 1 and 2 then replaced that guard (below); the final guard answers the first five (a `Date` made from an
API string is refused whatever is shown from it), and `sourceFiles` is still copied in this test and
`enteredDateTime.test.ts`, as before this package.

## Independent review

the independent reviewer (one bounded packet per round; up to three rounds, merge only on the owner's word).

- **Round 1** (packet `6b5f8cdb...aaf7e`, commit `dcd554a8`): `CORRECTION_REQUIRED`, two material findings, both on the
  guard. N06-R1-01: it matched option names as text, so quoted options (`{ "hour": ... }`) and options it did not list
  (`second`, `fractionalSecondDigits`, `dayPeriod`) in `Intl.DateTimeFormat` passed, and the records claimed more than it
  enforced. N06-R1-02: it judged "number or date" from the option text, so `count.toLocaleString("en-IN")` failed while
  a `Date` given `{ useGrouping: false }` passed. Corrected by reading the source with TypeScript's type checker: the
  receiver's type decides `toLocaleString`, and the options' type decides a time of day (slice record, "The guard"), with
  each reported case as a test; the records now describe exactly that rule. Re-run: the test file passes; on
  `faf9a1ae`'s source the scan fails with 31 findings in the eleven files; typecheck, 626 tests and the build pass.
- **Round 2** (packet `dcf3fe6f...c5694`, commit `ee0f4298`): `CORRECTION_REQUIRED`, three material findings, all on
  the guard. N06-R2-01: `date["toLocaleString"](...)` and the UTC methods (`getUTCHours`, `toUTCString`) passed.
  N06-R2-02: a zone check written another way (`/(?:Z$|\+\d{2}:?\d{2}$|...)/` with `.replace(/$/, "$&Z")`) passed, and
  `new Date(normalized)` was not looked at. N06-R2-03: a date-only options constant typed `Intl.DateTimeFormatOptions`
  was reported, its type listing `hour` as optional. Corrected by resting the guard on what every reader must do -
  make a `Date` from a string - rather than on spellings of the zone check: `new Date(text)`, `Date.parse` and calls
  to `readApiDateTime` are refused outside the shared modules (a date-only value at a fixed time and now excepted);
  methods are found by name or `date["name"]`, the UTC ones included; options are read from the literal where the code
  shows one. Each finding's example is a test case (25 reported, 11 allowed). Re-run: the test file passes; on
  `faf9a1ae`'s source the scan fails with 42 findings in the eleven files, each caught by the reading rule alone;
  typecheck, 626 tests and the build pass.
- **Round 3** (packet `303d98e0...b42de`, commit `0d0ceb06`), the last in the owner's cap: `CORRECTION_REQUIRED`, one
  material finding. N06-R3-01: a page could check and add a zone its own way (the round 2 alternation with
  `.replace(/$/, "$&Z")`) and hand the result to the shared `formatDateTime`, making no `Date`, and the guard passed.
  Corrected: what `formatDateTime` is given must be a record's field as the API sent it - a property or element chain
  rooted in a variable, `null`, or a choice between such - so a local variable, a template or a call is reported
  (slice record, "Handing over"); the finding's example is a test case (28 reported, 11 allowed). Re-run: the test
  file passes, every one of today's calls passing a field; on `faf9a1ae`'s source the scan fails with 42 findings in
  the eleven files; typecheck, 626 tests and the build pass.
- **Round 4** (packet `ffebb9d9...a5c69`, commit `d83aea41`), run on the owner's word: `CORRECTION_REQUIRED`, one
  material finding. N06-R4-01: `formatDateTime.call(undefined, row.created_at + "+" + "05:30")` passed - the callee
  looked at was `.call` - and so would `.apply`, `.bind` and the function put in a variable. Corrected: every use of the
  names `formatDateTime` and `apiDateTimeToIndiaInput`, as the type checker resolves them through imports and
  re-exports, must be a direct call given a record's field; any other use is reported, as is any use of
  `readApiDateTime` (slice record, "Handing over"). The finding's example and those variants are test cases (32
  reported, 11 allowed). Re-run: the test file passes; on `faf9a1ae`'s source the scan fails with 42 findings in the
  eleven files; typecheck, 626 tests and the build pass. **This correction has not been reviewed**: a fifth round needs
  the owner's word.
