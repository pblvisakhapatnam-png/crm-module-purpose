# UI / UX Carry-Forward Notes

These items are not blockers for thin foundation slices, but future UI agents should address them before production hardening.

## Navigation

```text
- Standardize page-level Back / return navigation placement.
- Continue refining origin-aware returns from linked Account, Opportunity, Commercial Offer and Work Order pages after the Slice 6A foundation.
- Slice 6A shows linked Work Order(s) on the originating Commercial Offer profile after a WO shell is created.
- Slice 6A adds clear CO -> WO and WO -> CO navigation.
- Avoid trapping users on detail pages that only return to lists when they came from a related record.
```

## Forms and validation

```text
- Improve inline validation and field-level highlighting.
- Place success/error messages close to the action that triggered them.
- Use separate message state for separate actions in long profile pages.
- Clear stale success/error messages when the related input changes.
- Make blocked/read-only states explanatory, not merely hidden.
```

## Server refusals (TB-1 TB1-801, October 2026)

```text
- Read a refusal through components/errorDetail.ts (readErrorDetail), never by putting the response's
  `detail` on screen as it came: FastAPI answers a refused field with a list of objects, and React
  replaces the whole page with its error screen when given one. components/errorDetail.test.ts fails
  on a page that passes `detail` on unread.
- Check a typed amount with components/amounts.ts (amountProblem) before sending, so the message names
  the field ("Offer value must be a number.") instead of "Check the values entered".
- Still to do, page by page as each is next changed (TB-1's TB1-603 path): 36 older helpers each read
  errors their own way and reduce the list to "... HTTP 422." without naming the field; the shared
  reader could name it for all of them at once. No route has an error element, so any other render
  failure still shows React Router's "Unexpected Application Error!" in place of the application.
```

## Profile pages

```text
- Review long profile pages for section order and scroll burden.
- Standardize linked-record cards.
- Standardize loading, empty and error states.
- Keep deferred-boundary panels visible but concise.
```

## Date/time display

```text
- Display business timestamps in Asia/Kolkata for PBL users.
- Avoid repeated IST labels on every field when the page context is clear.
- Use shared display helpers instead of per-page ad-hoc formatting.
```

## Visited-link/session behaviour

```text
- Browser visited-link colour can survive logout/login.
- Where business meaning depends on viewed-this-session state, control it explicitly in app state.
- Clear session-specific viewed state on logout/login where required.
```

## Page decomposition

Recorded 8 September 2026 (Slice 9B).

```text
- frontend/src/pages/commercial-offers/CommercialOfferDetailPage.tsx is about 5,700 lines (6,150 on
  11 September 2026, after the UI cleanup reskin regrouped its sections without splitting it) and
  holds the Overview, Lines & Pricing, Terms & Conditions, Submission and Traceability tabs, every
  lifecycle action and all of their local feedback state in one component.
- Three separate Slice 9B review findings landed in this one file, and each correction had to be
  reasoned about across the whole component rather than a single section.
- Split it by tab or by action group, preserving the Slice 6I.1 tab structure, the UI
  action-feedback rule and the existing role-aware behaviour. Do it together with the frontend
  component-test capability recorded in docs/agent/DEFERRED_REQUIREMENTS.md, not before it: a
  decomposition of this size should not be the first change made without any behavioural test.
```

## Interaction log (Slice 9D)

Recorded 8 September 2026 from the Slice 9D independent review. Full list, including the
non-UI items, in `docs/agent/DEFERRED_REQUIREMENTS.md`.

```text
- InteractionLog shows the newest 20 records with no pagination, and surfaces only the
  inherited-history toggle. The API already accepts channel_code, direction_code, occurred_from,
  occurred_to, limit and offset; the UI should surface them.
- DONE 11 September 2026 (UI cleanup package): stale form feedback is now cleared when the user
  edits a field. Only the user's own edits clear it; the form's post-save reset does not, so the
  "Conversation recorded." confirmation survives the reset.
- DONE 11 September 2026 (UI cleanup package): timestamps no longer repeat the IST label on every
  row; one note at the top of the log states that times are in India time.
- The component has no component-level test, because the frontend has no component-test
  capability yet (see DEFERRED_REQUIREMENTS.md). Add tests with that capability, not before it.
```

## UI cleanup reskin (September 2026)

Owner decision, 10 September 2026, taken with the seeded pilot screens in front of them: a
**reskin, not a restructure**, before the UAT pilot, so testers are not sidetracked by the UI.

Done:

```text
- Shared building blocks in frontend/src/components/PageLayout.tsx, styled in globals.css:
  PageHeader (Back link, record type, title, status badges, actions), SectionGroup (labelled,
  coloured band holding related sections), SectionCard (bordered section), SectionIndex (sticky
  "Jump to" row), StatusBadge (colour by status code, label from the page's own formatter) and
  ReferenceText (a UUID kept visible but secondary).
- The six detail pages - Commercial Offer, Account, Lead, Opportunity, Work Order, Work Order
  Amendment - use them: related sections grouped and boxed, a Jump-to row on long pages, and a
  consistent Back placement in the header. This closes the "common page-header/action component"
  first asked for in Slices 3C and 4B, for detail pages.
- Developer wording removed from the pages' own text ("Slice N", "foundation", "future agents",
  role codes, event names); out-of-date claims corrected. Text the backend supplies - business-event
  reasons and a few validation messages - is unchanged and still says "Slice N" in places.
- Owners and creators shown by name instead of user UUID. On the Commercial Offer, Work Order and
  Work Order Amendment pages the linked Account and Opportunity are shown by name, with the
  reference number kept small beside it; the Lead and Opportunity pages still show linked records
  as "Open Account" / "Open Opportunity" / "Open Lead" with the reference.
- The Approve-for-issue button is shown only while the backend reports no reason the version cannot
  be approved; otherwise the reason is shown in its place. The server re-checks on approval.
```

Not done, deliberately:

```text
- Pages are not shorter. Grouping and the Jump-to row make long pages easier to navigate, not
  smaller: the Commercial Offer Submission tab measured 7.2 screens before and 7.5 after at
  1440x900. Shortening them is the restructure, sequenced after the pilot so user feedback shapes it.
- List pages and "new" pages were only cleared of developer wording; they do not use PageHeader.
- Inline validation and field-level highlighting, visited-link session state, shared date/time
  helpers and InteractionLog pagination/filters are unchanged.
- No component tests: the frontend still has no component-test capability (DEFERRED_REQUIREMENTS.md).
- DONE 11 September 2026: the owner's language pass, as its own package
  (docs/agent/slices/ui-language-pass.md). What it left is listed below.
```

## Language pass (September 2026)

Recorded 11 September 2026. The language pass removed developer wording from page text and from
the backend messages users see (`docs/agent/slices/ui-language-pass.md`). Still to consider:

```text
- Network errors end "Check that the backend and frontend services are running." A pilot tester
  cannot act on that; say what to try instead.
- ~~"Login first..." messages remain in about eighty places, in several wordings. Make them one.~~ Done 28
  September 2026: see "Sign in and Sign out, one wording".
- The Work Order Amendment pages still say "intake" and "intake/review record only".
- The Account document storage option "Future SharePoint reference".
- The button "Record as Submitted / Commercially Committed" is accurate but long.
- List pages other than the dashboard still show raw status codes such as QUOTE_PENDING.
- Credit review messages on the Submission tab show the raw review code, for example "...review
  is WITHIN_LIMIT_AS_PER_MANUAL_REVIEW", and some still say "remain future work". Showing a
  label needs a small code change, so it was left out of a wording-only package.
- The Work Order page has two rows labelled "Created at", one in the summary and one under
  "How this Work Order was created".
- DONE (document upload package, September 2026): the Documents page was a developer test page
  whose upload box always filed to one fixed sample Account as KYC, and no screen let a user
  upload a file against a chosen customer or offer. Files are now uploaded, listed and downloaded
  on the Account and Commercial Offer pages, and the Documents page lists recent files with
  downloads (docs/agent/slices/document-upload-on-record-pages.md).
```

## Document upload (September 2026)

Recorded 13 September 2026, from the upload package's own gap list, which until now lived only in
that package's records.

```text
- There is no upload control on the Lead, Opportunity or Work Order pages. The server rules for
  those record types are already in place, so this is a missing screen rather than a missing
  permission - a user who needs to attach a file to a Lead has nowhere to do it.
- Deleting and viewing an uploaded file are both absent; see docs/agent/DEFERRED_REQUIREMENTS.md,
  "Document deletion and in-browser viewing", and Q-12 in docs/continuity/OPEN_QUESTIONS.md.
```

## Mobile layout (September 2026)

Recorded 13 September 2026, from the project owner using the deployed pilot on a phone.

```text
- The application works on a phone: pages load, sign-in works, records can be read and edited.
- It is not laid out for a small screen, so it is awkward - the owner's word. Long detail pages,
  wide tables and the side-by-side groupings added by the UI cleanup all assume a desktop width.
- Accepted for the pilot and to be addressed afterwards. Worth doing together with the page
  decomposition already recorded above, rather than as a separate responsive pass: both are about
  the same long pages, and fixing the structure first makes the small-screen work smaller.
- 26 September 2026: the menu that stacked a screen above every page can be hidden, and starts
  hidden at 900px and below (see "App shell" below). The pages themselves are unchanged.
```

## Pilot screen review (September 2026)

Recorded 12 September 2026, from the project owner's walk through the screens on localhost before
the VPS pilot. Four items were fixed in the same package; the rest are recorded elsewhere.

Fixed:

```text
- The conversation form (InteractionLog) used no field class at all, so its labels sat inline and
  every control fell back to the browser's default width - the notes box was about twenty
  characters wide. It now uses the shared `field-stack` class like every other form, the form's
  max width matches the app's section-form convention (860px, was 480px), and the notes box is six
  rows instead of three.
- SectionIndex had a "Jump to" row but no way back. It now ends with "Back to top", pushed to the
  far end of the same sticky row, scrolling in place rather than putting a bare "#" in the address
  bar - the same reasoning the section links already used.
- The Work Order line table showed the source Commercial Offer line as a bare UUID. It now reads
  "CO-000013 line 2", with the UUID kept below it as secondary reference text. This needed one
  additive read-only API field, `source_offer_line_number`, from a join the query already had.
- The Account Classification tab's owner field is a text box holding a raw user UUID. It now names
  the current owner above the box ("Currently: Sales User 1") and says plainly that the value is an
  internal ID rather than a name.
```

Not fixed, deliberately:

```text
- The owner field still requires a UUID to be typed to CHANGE the owner. A real user picker is the
  fix; it remains the Slice 1K "Owner user picker" exclusion in the Account contract. Naming the
  current owner removes the confusion of reading the screen, not the awkwardness of editing it.
- Deleting and viewing an uploaded document: see docs/agent/DEFERRED_REQUIREMENTS.md, "Document
  deletion and in-browser viewing", and Q-12 in docs/continuity/OPEN_QUESTIONS.md.
- Whether a conversation note should be mandatory: Q-11, deliberately left to the pilot to answer.
- Still no component tests, so none of the above is covered behaviourally (DEFERRED_REQUIREMENTS.md).
```

## Work Order billing terms (Slice 7D.1)

Recorded 15 September 2026, from the owner's look at the merged billing terms form.

```text
- DONE: the terms no longer flow as identical grey boxes. They sit in three chapters coloured with the
  shared tones (The rate, Working time, Extra charges); each group is a card with a one-line description
  and an Answered / Still needed tag; fields share rows. Classes: terms-* in globals.css.
- A reusable shape for any long operational form: chapters of tagged cards over a fixed-width field
  grid. The Site and billing details section above it (7C) still uses the plain layout.
- DONE: each billing terms period opens and closes; the latest starts open, earlier complete ones start
  closed, and a period the user opened, closed or edited keeps that state.
- The tags describe the period as last saved, so they hide while the form's basis differs from the
  saved one. They do not follow unsaved edits within the same basis; the Save message is the signal.
- Still no component tests; how the cards look is covered by the owner's screen check only.
- **"Remove this period" is in the wrong place** (owner's screen check, 23 September 2026). It sits at
  the foot of the period's open form, directly below **Save terms** - a destructive action one line
  under the safe one - and immediately above "Apply these terms to other lines" and "Add a later
  period", which act on the whole line, not on this period. Reaching it means scrolling the entire
  term set. The fix when the form is taken up: move it into the period card's own header row, beside
  the period's dates and its Answered/Still needed tag, where it plainly belongs to that period, and
  keep it visually apart from Save. Recorded rather than corrected, on the owner's own 7D.1 ruling
  below and because the file is already on the decomposition list
  (`docs/agent/DEFERRED_REQUIREMENTS.md`, "Code structure in the Work Orders module").
- **Owner's verdict, 16 September 2026: every check passed, and the form is still unwieldy.** The
  layout stays exactly as built; the owner chose to put functionality first because making this form
  genuinely easy to use is likely to take a while. Do not re-open it as a small polish job. When it is
  taken up, treat it as its own package together with the page decomposition recorded above, and start
  from what makes a long operational form usable - fewer things on screen at once - rather than from
  more colour or more tags.
```

## Work Order contract period (Slice 7D Part 3)

Recorded 17 September 2026, alongside the layout note above.

```text
- The Contract period section sits under the Work Order snapshot, in the same blue group, because the
  dates are the Work Order's own fact rather than a line's. It reuses the plain field layout, not the
  chapters-of-cards shape 7D.1 gave the billing terms: it is four fields, not forty.
- The Jump-to row is unchanged - the section lives inside "The Work Order", which it already names.
- "Apply these terms to other lines" is a collapsed button inside each line's billing-terms card,
  beside "Add a later period", because both are actions on the line as a whole rather than on one
  period. It opens to a tick list, and the button says how many lines it will change.
- The replace confirmation uses window.confirm. It is the one place in this module that does, and it
  is deliberate: it is the only action that replaces something already recorded, and a native dialog
  cannot be missed. If the app later gains its own dialog component, this is a natural first user.
- The owner's verdict on the 7D.1 form stands and is not re-opened here: when the long operational
  form is taken up again, the contract period section should be considered part of that package
  rather than polished on its own.
- Still no component tests, so everything above is covered by the owner's screen check only.
```

From the owner's screen check, 22 September 2026:

```text
- Once an extension exists, "Contract ends on" is shown, not offered, with a line saying the extensions
  set it. The start date and notes stay fields. Before this the form kept offering the end date, and
  a save silently undid the extensions.
- The latest extension has a Remove button, in its own table column; earlier rows have none. It asks
  with window.confirm, naming the move and where the end goes back to - the second deliberate
  window.confirm in this module, for the same reason as the first: it removes something recorded.
  Its message sits below the table, not in it, so it survives removing the last extension, which
  removes the table. The first version put it inside and lost it; caught on screen.
- "Received on" is now "Extension order received on", and the column "Order received on".
- An order dated more than 15 days before today shows an amber warning under the field. It never
  disables the button: the owner asked for a warning, not a refusal.
- Every date field on the Work Order page stops at a four-digit year. Since 28 September 2026 every date
  field in the application does, through the shared `DateInput` (see "Sign in and Sign out, one wording").
- The sidebar now names who is signed in and their roles, on every page. Before, it said only "Signed
  in". If the name cannot be fetched it falls back to that, rather than showing a stale name - and a
  name is shown only for the session it was fetched for, so a change of user never shows the previous
  person while the new name is on its way (review round 5, F-01).
- "The extension starts on" is filled in with the day after the current end and shown only when there
  is a fixed end to follow. A later date shows an amber line naming the days it leaves outside, and
  Record asks to confirm with window.confirm - the third deliberate use in this module, for the same
  reason as the others: it records something with consequences the user should see first.
- Gaps are listed in amber under the extension history, one line each.
```

## Resource requirements (WRR-001, September 2026)

Built minimally, in Foundation Slice Mode:

- **Resources needed** on the Work Order page is its own component and loads itself, again on each new
  page-load generation. It lists every line, with its requirements or "No requirement recorded for this
  line.", and **Add a requirement** for Operations and Admin.
- The new-requirement page and the requirement page share one set of form fields. The line's facts -
  quantity in billing units, contract, line dates, the Work Order's crew - are shown beside the fields
  they bear on, not in a separate panel. Messages sit beneath the Save and Cancel buttons.
- Moving **Needed from** reads the Work Order again for that date: the billing basis and crew shown beside
  the fields become that date's, and crew numbers not yet typed are refilled from it - each number on its
  own, so typing the operators leaves the helpers following the date. Save is disabled ("Reading the Work
  Order for that date...") until that answer is in; if the read fails, it stays disabled, the reason is
  shown beside it, and **Read the Work Order again** retries, clearing any earlier message. Typed crew
  numbers are never overwritten. The same holds on the change form of a saved requirement.
- Refresh on a requirement discards anything half done on the page - a change, a typed cancellation
  reason, a confirmation - because it was made against the version Refresh replaces.
- Cancelling asks for a reason, then a second click ("Yes, cancel it") - an in-page confirmation rather
  than window.confirm, because the reason is typed on the page anyway.
- The pages use a shared session helper (`pages/resource-requirements/pageSession.ts`) instead of their
  own copies of the token, role and return-link helpers every older page carries. A later pass could
  move the older pages onto it.
- Date and time: one shared formatter, `components/dateTimeDisplay.ts` (`formatDateTime`, re-exported by
  `pageSession.ts`), shows a business time in India's time whatever the browser's zone. Added 4 October 2026 when
  four CRM pages were found showing times 5 hours 30 minutes early (TB-1's TB1-604;
  `docs/continuity/TB1_604_CRM_TIMES_IN_INDIA.md`). Nine pages still carry their own correct copy; move each to the
  shared one when the page is next worked on. `dateTimeDisplay.test.ts` fails on any bare `toLocaleString()`.
  *12 October 2026 (TB-1 note N-06):* all moved - the nine, the Documents panel's and the dashboard's, which showed the
  Recent Work Orders' Created time 5 hours 30 minutes early - and the dashboard's two times now read like every other
  page's ("12 Oct 2026, 06:49 am"). `dateTimeDisplay.test.ts` now fails when any file but the two shared time modules
  reads a time from text (a `Date` made from a string) or shows a time of day itself (`docs/agent/slices/n06-one-way-to-show-a-time.md`).
- The planning list empties the moment a new filter, page or refresh is asked for, and shows "Loading"
  until the answer: it never lists one filter's requirements under another's controls.
- The form's fields sit at the top of their row, and every hint sits beneath its box, so a hint under one
  field never pushes its neighbours down (the owner's screen check found the **Type** box out of line).
- Deferred at the owner's word (screen check, 25 September 2026): keep a requirement's title and status
  badge visible while its page scrolls. Do it with the wider UI pass rather than on this page alone.
- Not done: the planning list has no search, no grouping by site or date, and no calendar view; a
  requirement cannot be printed or exported. All wait for Operations to use the list.

## App shell (September 2026)

- Requirement (the project owner, 26 September 2026): the left menu panel can be hidden and shown again,
  as in many desktop apps, leaving the page the full width. To be built with the move of the older
  pages onto the shared stylesheet classes (next section), as one app-wide UI package rather than inside a
  business slice: both touch every page, so one screen check covers them. It is small - a toggle in
  `layout/AppShell.tsx`, one class on `.app-shell` in `globals.css`, the choice remembered in the browser -
  and it helps the small-screen use recorded under "Mobile layout".
- DONE 26 September 2026 (`docs/agent/slices/ui-menu-and-shared-styles.md`): a three-line button beside
  "PBL CRM", named "Menu", with `aria-expanded`; hidden, only the button is left at the top left and the
  page takes the width (still centred at its 1180px reading width); `.app-shell--menu-hidden`; the choice
  in `localStorage` (`pbl_menu_shown`), read and written in `try`/`catch`. Until the user chooses, the
  menu is shown on a desktop and hidden at 900px and below, where it would stack a screen above the page.
- Still as before: the menu scrolls away with a long page rather than staying in view, so showing it
  from the foot of a page shows it at the top. Making the panel stay put is a separate, small change.

## After signing in (owner, 27 September 2026)

- Requirement, to be built at the earliest opportunity: straight after a successful sign-in, instead of
  "Login successful.", the page says **"You are logged in as <name>. Click here to view the Dashboard."**, with
  "here" a link to the Dashboard (`/`) - or words to that effect.
- Where: `frontend/src/pages/LoginPage.tsx` sets the message (`setMessage("Login successful.")`) and shows a
  "Signed in user" box beneath it; the new line takes the user's `display_name` from the login answer, and
  the box may then go or shrink. Link to the Dashboard as the menu does (`layout/AppShell.tsx`, a plain
  `<a href>`).
- **Every E2E test signs in through it:** `e2e/tests/fixtures/auth.ts` waits for the text "Login
  successful.", so the fixture changes with the message - wait for the new line, or for the Dashboard link.
  Run the full E2E suite, not one spec.
- The page still styles inline; move it onto `globals.css` classes in the same change. (This said
  "CODING_STANDARDS.md, section 7: a page that is worked on moves whole", which section 7 does not say.
  Reconciled 7 October 2026, TB-1 TB1-608: section 7 has a page that still styles inline moved in its own
  package, never inside an unrelated slice; this package was about the login page, so moving it here was
  that package's own work.)
- Kept out of ERT-2 (the owner's note came at its screen check): it touches the login page and every E2E
  test's sign-in, not equipment.
- DONE 27 September 2026 (branch `ui/sign-in-message`): beneath the **Sign in** button the page says "You are
  logged in as **<name>**. Click here to view the Dashboard.", "here" a plain `<a href="/">`; the name is the
  login answer's `display_name`, falling back to the username. The "Signed in user" box is gone - the menu's
  Session panel already shows the name and roles. "Signing in..." and "Login failed..." sit in the same place.
  The page styles through `globals.css`: `.form-card` with a new `.form-card-narrow` (360px), `.field-stack`
  labels, `.form-actions`, `.action-feedback` (no margin inside a `.form-card`, whose gap spaces it),
  `.helper-text` / `.text-danger`, and `.content-card` for the test users; no inline styles are left on it.
  The E2E fixture waits for "You are logged in as" and checks that "here" goes to `/`. Checks: frontend
  typecheck, 352 tests and build; full E2E 23 passed / 9 skipped / 0 failed. The owner's screen check
  passed the same day.

## Equipment (ERT-1, September 2026)

- The Equipment pages style through `globals.css`, not inline (owner, 26 September 2026: "follow
  stylesheets etc. so that we don't have to make changes at multiple places"): `.data-table-padded` for
  table cells, `.text-danger` / `.text-success` / `.text-warning` for outcome words, `.facts-list` for a
  record's label-value facts, `.form-actions` inside a `.form-grid` for a form's buttons (level with the
  boxes, with any message beneath them), `.actions-with-fields`, `.section-form`, `.compact-list`,
  `.divided-item`. They are for every page.
- DONE 26 September 2026 (`docs/agent/slices/ui-menu-and-shared-styles.md`): every table's cells are
  padded, ruled and aligned by `.data-table` itself, and `.data-table-padded` is gone; the fourteen older
  files whose table cells were styled inline (thirteen found by the owner's grep, and the Account page,
  whose cells used style constants) colour their messages with the `.text-*` classes. A moved
  message is coloured text, as here, where the older pages drew a pink or green box around it - a rule
  that matches the inline colour, kept for the pages not yet moved. Whether the box should come back, as
  one rule on the classes for every page, was the owner's to say: at the screen check on 26 September 2026
  the owner confirmed the plain coloured text, so the box does not return and this is settled, not open.
- Still inline, for a later pass: 1,071 `style={{...}}` attributes in 33 files (1,252 before), 445 of them
  on the Commercial Offer page; message colours on the 15 pages and sections that have no table (the
  new-record pages, the Commercial Offer page, the Work Order line sections); muted grey text, about 130
  places, which is `.helper-text`; label-value grids, which are `.facts-list`; nine table wrappers' top
  margins inside section cards. Move a page whole, in a package of its own, rather than one property
  across every page.
- *Reconciled 7 October 2026 (TB-1 TB1-608).* The line above said "move a page whole when it is next worked
  on", where `CODING_STANDARDS.md` section 7 - the owner's rule of 26 September 2026 - says a page that still
  styles inline is "moved in [its] own package". The owner's rule stands: such a page moves whole in a package
  of its own (or one whose subject is that page, as the sign-in message package was for the login page), never
  as scope creep inside an unrelated slice; new code adds no inline style. Lines holding `style={{` in
  `frontend/src` on `main` at `4ff3966`: 1,047 in 31 files (counted as TB-1 counted them, `git grep -c`),
  445 of them on the Commercial Offer page; no file gained one since the rule.
- Found in that package's screenshots, and older than it: in a narrow table column inside a section card,
  words and buttons break mid-word ("Remo ve", "Li ne", "INR 25,00 0"). `.section-card` sets
  `overflow-wrap: anywhere` for everything inside it, table cells included. A cell rule setting it back to
  `normal` for words and buttons, with long references keeping their own class, is the likely fix; it
  changes how every card's tables size their columns, so it wants its own screen check.
- The owner's screen check (26 September 2026) found the details form's buttons out of line with its
  boxes (now the `.form-actions` rule), the preview's line numbers starting at 3 unexplained (now "Line in
  file", with a note that lines 1 and 2 are the report's title and headings), and **Refresh** hard to find
  after mapping a name (now a **Refresh the preview** prompt at the top of the page as well).
- Deferred at the owner's word: after a refresh, say what changed - highlight the rows whose outcome or
  flags the mapping or reading changed. The row is correct, but nothing points to it.

## Future UX agent scope

The UX agent may improve consistency and discoverability, but must not weaken backend permission checks, status rules or business-event recording.

## Sign in and Sign out, one wording (owner, 27 September 2026)

- Found at ELG-1's screen check: after signing in, the login page still offers **Sign in**, and the application
  mixes two wordings - the page's "Login" heading and "You are logged in as", the sidebar's "Signed in as" with
  a **Logout** button, "Please log in first." on the older Account pages, "Sign in first." on the newer ones.
- **Decided: "Sign in" and "Sign out" everywhere** ("Signed in as", "Sign in first.", "Not signed in"). Nothing
  says log in, login, log out or logout on screen.
- **When already signed in, the login page says "You are signed in as <name>", links to the Dashboard and offers
  Sign out** instead of the form; after signing out, the form is back. Signing in as someone else is sign out,
  then sign in.
- **Its own small package, straight after ELG-1** (owner's decision): it touches the shared sign-in screen, the
  sidebar's Session panel, about a dozen pages' messages and `e2e/tests/fixtures/auth.ts`, which every E2E test
  signs in through (it waits for "You are logged in as"; a spec signing in twice would meet a page with no
  form). Run the full E2E suite. The "Login first..." item above is the same work.
- DONE 28 September 2026 (branch `ui/sign-in-out-and-dates`):
  - The sign-in page is headed **Sign in**. Signed in, it says "You are signed in as <name>. Click here to view
    the Dashboard." with **Sign out** in place of the form; signed out, the form is back. The menu's Session
    panel says **Sign out** and, when nobody is signed in, **Sign in**. Failing: "Sign-in failed. Check the
    username and password."
  - The session - whether one is in use and whose - moved from the Session panel into one hook,
    `components/useSession.ts`, which the panel and the sign-in page share.
  - The two messages repeated across the pages are one each, in `components/signInMessages.ts`:
    `SIGN_IN_FIRST` ("Sign in first. No active session was found.") and `SIGN_IN_AGAIN` ("Sign in first, or sign
    in again if your session has ended."). The rest say "Sign in ..." where they said "Login ..." and keep their
    own guidance ("Sign in as a Sales or Admin user to create Accounts."). Nothing on screen says log in, login,
    log out or logout; API paths, event names and code names are unchanged. The backend had no such message.
  - `e2e/tests/fixtures/auth.ts` waits for "You are signed in as" and, where someone is already signed in,
    signs out on the sign-in page first. `e2e/tests/sign-in.spec.ts` checks the page's Sign out, the form's
    return and signing in as someone else.
  - Also done in the same package, from the owner's screen check of ELG-1 (28 September 2026): the Certificate
    rules table's "In effect" column is wider (`.col-state-actions`, 13rem) so its date and **End this rule**
    each stay on one line, and Source is held to 14rem (`.col-long-text`) so "The rule" keeps its width - at
    1440 px the table is about 400 px shorter and its tallest row 251 px rather than 305; and every date box stops at a four-digit year - one
    shared `components/DateInput.tsx` (`max` 9999-12-31, or 9999-12-31T23:59 with a time), used by all 47
    date and date-and-time boxes in 18 files, with a test (`components/dateInputs.test.ts`) that fails when a
    page adds a plain date box.

## Allocations (8A core, owner's screen check, 29 September 2026)

- **Deferred (the owner: "can be deferred or even left alone, most probably will be highlighted by UATs").** On an
  allocation's page, an action's message stays after the next action: "Trip (Own Load) added." is still shown
  beside its button when "Listed." appears beside another. Each message sits beside its own button, as the rule
  asks; clearing the others when a new action starts would leave only the latest (`AllocationPage.tsx`, `say`).

