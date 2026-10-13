# App-wide UI - Hideable Menu and Shared Styles - Acceptance

Package record: `docs/agent/slices/ui-menu-and-shared-styles.md`. Frontend only.

## Commands

Run in the cloud session's Docker Compose stack, per `AGENTS.md`:

```text
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run typecheck
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm test
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run build
pwsh -NoProfile -File scripts/run-e2e.ps1
python scripts/check_tracked_secrets.py
python scripts/validate_contract_fixtures.py
python -m unittest discover -s scripts/tests
```

No backend file changed, so the full backend regression was not run.

## Results - first candidate, 26 September 2026

| Check | Result |
| --- | --- |
| Frontend typecheck | clean |
| Frontend tests | 334 passed in 13 files (330 on `main`; +4 in `layout/menuPreference.test.ts`) |
| Frontend build | built |
| Full E2E suite (`pwsh`, retries 0) | 21 passed, 9 skipped, 0 failed; cleanup succeeded - the same counts as ERT-1 |
| Committed-credential check, contract fixtures, script unit tests | clean; all rules passed; 100 passed |
| Frozen handoff contract | SHA-256 `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a` before and after |
| Inline cell styles (`grep -rnE '<t[hd][^>]*style=' frontend/src`) | none (184 before) |
| Inline `style={{` attributes in `frontend/src` | 1,069 (1,252 on `main`) |

## Independent review, round 1

the independent reviewer, one bounded packet, reasoning effort high, read-only and without tools. Packet
SHA-256 `857742e42889a628ea716fe074fdfc2b272d949ea78a4a9943e389e50382d48d`; candidate commit `eddf1d3`,
tree `3afc09e9`; the evidence in it was rerun on that exact commit, E2E included (21 passed, 9 skipped,
0 failed, on a fresh database). Result: `CORRECTION_REQUIRED`.

| Finding | Severity | What it said | Disposition |
| --- | --- | --- | --- |
| R1-F01 | material | The records' 13-file scope did not match the diff: 14 files lost inline cell styles, OperationalReports changed nothing, and "the literal grep matches only 11 files". | Corrected. Checked against `main`: the owner's literal grep finds 13 files, not 11 - `DocumentsPage` and `DocumentsPanel` match through their file-name cell, `style={{ ...CELL_STYLE, ... }}`. The rest of the finding stands: the package record and the continuity note now carry one explicit inventory (13 found by the grep; 14 with inline cell styles removed, the Account page's through constants; OperationalReports unchanged; five Equipment pages dropped the modifier), and `UI_UX_CARRY_FORWARD.md` and `NEXT_STEPS.md` say "the fourteen older files" to match. While correcting it, the package record's "four cell-style constants" was found wrong too - there were six, two in each of three files - and is corrected. |
| R1-F02 | advisory | The storage test reached `localStorage` or failed on `setItem`, but never had `getItem` itself throw. | Corrected, not carried forward: the storage-refused test now also reads through a store whose `getItem` throws, and expects the desktop and stacked defaults. Mutation check: moving `getItem` outside the `try` (with the store reached safely) passes the round-1 test and fails the corrected one. Test count unchanged at 334: the assertions are in the existing test. |

The reviewer's residual uncertainty was the rendered appearance, which a text packet cannot carry. The
before and after screenshots (56 each, 1400px and 390px, same data) are with the owner, as
`<a PBL folder outside the repository>`, outside the repository; the owner's screen check settles it.

## Results - after the round-1 corrections

| Check | Result |
| --- | --- |
| Frontend typecheck / tests / build | clean / 334 passed in 13 files / built |
| R1-F02 mutation check (`getItem` outside the `try`) | fails the corrected test; passes the round-1 test |
| Committed-credential check, contract fixtures, script unit tests | clean; all rules passed; 100 passed |
| Runtime code changed by the corrections | none: one test file and the records, so the E2E result on `eddf1d3` stands |

## Independent review, round 2

the independent reviewer, one bounded packet, reasoning effort high, read-only and without tools. Packet
SHA-256 `8ac7e2f67ca8f5c598be0a2d91d7ab2a5d6fef65324c63abbb8b724cf8c3b459`; candidate commit `2fd25fc`,
tree `21a6690b`, which included the three uncommitted records carrying the owner's screen-check outcome.
The packet carried a `-U20` diff plus the whole current text of all 28 changed files except
`NEXT_STEPS.md`, so no finding could arise from a hunk cutting a handler in half. Result:
`CORRECTION_REQUIRED`.

| Finding | Severity | What it said | Disposition |
| --- | --- | --- | --- |
| R2-F01 | material | The package record says that where a converted message also set a margin, the margin stays inline because layout was not taken on. `AccountsPage`'s two list-result messages instead went from `color` plus `marginTop: "16px"` to the class alone, dropping the margin without recording the exception - the records-versus-diff class again. | Corrected in the code, not the record: the two paragraphs are now `<p className="text-success" style={{ marginTop: "16px" }}>` and the `text-danger` equivalent. Verified first: the finding is real and exactly two lines wide (`git diff main -- frontend/src` has no other removed line carrying both a colour and a `marginTop`), `.text-success`/`.text-danger` set only `color`, and 21 converted messages in four other files already keep their margin inline in precisely this idiom - so the record was true everywhere except here, and the fix makes it true. It also restores consistency with the `loading` paragraph two lines below, which kept its inline `16px`. Rendered spacing was in fact unchanged even before the fix (`body` and `.list-card` set no `font-size`, so the UA default `1em` resolved to the same 16px), but that equivalence held only by coincidence of the base font size; it is now explicit again. |
| R2-F02 | advisory | The invalid-stored-value test exercised only the desktop width, where the correct default is itself `true`, so an implementation accepting any non-`"false"` value would pass. | Corrected within the round, not carried forward: the test now also asserts that `"maybe"` with `stacked: true` reads `false`. Mutation check: with `if (saved === "true")` replaced by `if (saved !== null && saved !== "false")`, the suite fails at exactly the new assertion (1 failed, 3 passed) while the pre-existing desktop assertion still passes - so the gap was real and is now closed. The implementation was restored byte-identical to `HEAD` afterwards and verified with `git diff --quiet`. Test count unchanged at 334: the assertion went into the existing test. |

The reviewer's residual uncertainty was that the screenshots themselves are not in the packet, so
rendered appearance rests on the reported Playwright comparison and the owner's screen check rather
than its own inspection. That is inherent to a text packet and is answered by the screen check above.

## Results - after the round-2 corrections

| Check | Result |
| --- | --- |
| Frontend typecheck / tests / build | clean / 334 passed in 13 files / built |
| R2-F02 mutation check | fails at the new assertion only; the previous assertion passes |
| `menuPreference.ts` after the mutation check | byte-identical to `HEAD` (`git diff --quiet`) |
| Runtime code changed by the corrections | two inline `marginTop` values in `AccountsPage.tsx`; nothing else |
| Full E2E suite (`pwsh`, retries 0), re-run on the corrected candidate | 21 passed, 9 skipped, 0 failed in 1.6 min; manifest cleanup succeeded; 21 login events cleaned above boundary 857557 |
| Inline `style={{` attributes in `frontend/src`, current | 1,071 in 33 files (1,069 at round 2; R2-F01 restored two by design) |

## Independent review, round 3

the independent reviewer, one bounded packet, reasoning effort high, read-only and without tools. Packet
SHA-256 `933feab5b9df31e6dae0ba3f221c4eb9cd317ec23a0d98ca834680b188b25fc5`; candidate tree `89c8ffaa`.
The E2E evidence in it was re-run on that candidate rather than cited from `eddf1d3`, because R2-F01's
correction changed a runtime file. Result: `CORRECTION_REQUIRED`, one material finding, and explicitly
"no runtime defect is evident from the supplied code".

| Finding | Severity | What it said | Disposition |
| --- | --- | --- | --- |
| R3-F01 | material | Four record-versus-candidate drifts, all of them introduced by the earlier corrections themselves: the slice and carry-forward records still said 1,069 inline `style={{` when the candidate has 1,071; the carry-forward still called the message-box decision the owner's to make at the screen check, and the slice still called the narrow-width default awaiting confirmation, though the recorded screen check settled both; and `NEXT_STEPS.md` still named round 2 as the next review stage. | Corrected, all four. `1,069` became `1,071` in `docs/agent/slices/ui-menu-and-shared-styles.md` and `docs/agent/UI_UX_CARRY_FORWARD.md` (the `1,069` in the first-candidate results table above is left as it stands: it is dated history, and is the figure that was true then). The carry-forward now records that the owner confirmed the plain coloured text, so the box does not return and the question is settled rather than open. The slice record now says the 900px default was confirmed at the screen check. `NEXT_STEPS.md` now carries the round-2 dispositions and the re-run E2E result, and names round 3 as the current stage and the last inside the cap of three. Checked while correcting: the neighbouring `445` figure is right - it is `CommercialOfferDetailPage.tsx` alone, "the Commercial Offer page" singular, not the directory's 472 - and the file count is still 33. |

These corrections are documentation only; no code changed, so the typecheck, test, build and E2E
results above stand unchanged for the corrected tree.

## Screenshots

Taken with Playwright against the running stack at 1400px and 390px wide, of the new build and of
`main` built beside it on the same data, and looked at: the menu shown, hidden and at its default at
each width; the dashboard's reports; the Work Order lines, contract extensions and amendment lines;
Resource Planning; the Accounts list and an Account's contacts (with the missing-name error),
classification (with the saved message), addresses, GSTINs and documents; the Documents, Leads,
Opportunities, Commercial Offers and T&C lists; a Lead's activities and an Opportunity's offers; and
the five Equipment pages. Every table is as it was, with the row rule and top alignment described in
the package record; the dashboard's reports are padded and left-aligned where they were bare. The
moved messages are coloured text without the box. Nothing overlapped or was cut off at either width.

## Screen check - the owner's

Local stack, seeded with `core-regression-bundle`, `work-order-resource-requirements` and
`uat-pilot-seeded`; signed in as `admin1`. The steps as given to the owner are in the chat that handed
the package over; the outcome is recorded here.

**Outcome: Pass. Every step was in order, 26 September 2026, candidate commit `2fd25fc`.**

Two steps needed a word back, neither of them a defect:

- **Step 6, the centred headings.** The owner could not see them at first. They were in the *old*
  build, on the dashboard's report tables; the new build shows those headings left-aligned, which is
  what the package intends. The step read as if the centred headings should still be findable in the
  new build, which is the step's wording, not the build's behaviour. A later screen check of this area
  should ask the reader to confirm the headings are left-aligned rather than to find centred ones.
- **Step 13, the two confirmations.** Both answered yes: the menu starts hidden at 900px and below,
  and the moved messages are plain coloured text with the old pink and green boxes gone.

That settles the reviewer's residual uncertainty from round 1, which a text packet could not carry:
the rendered appearance is confirmed by the person who set the requirement. It also confirms two of
the three decisions the package made for the owner to settle - the menu's 900px default and the
message form. The third, one form for every table's cell (a light rule between rows, text at the top),
was accepted as part of "all steps OK" across the table steps.

## What still needs checking

Recorded at the owner's direction, 26 September 2026, when the package went to a pull request after
three review rounds without any round ending `ACCEPTED`. Nothing here is a known defect; each is
something this package did not establish, written down so the next person does not have to rediscover
it. The first item is the reason the others matter.

1. **No round ended `ACCEPTED`, and R3-F01's corrections are themselves unreviewed.** Rounds 1, 2 and 3
   returned 2, 2 and 1 findings, all corrected. Round 3 was the last inside the owner's cap of three, so
   the four documentation corrections made for R3-F01 went in without an independent pass over them -
   and each of the three rounds found something in the previous round's corrections. The pattern was
   converging (one runtime finding in total, R2-F01; everything after it was records catching up with
   code), which is why the owner chose the pull request over a fourth round. A reviewer of this PR should
   read the four R3-F01 corrections as unreviewed text: the `1,071` figure, the two
   settled-not-open decisions, and the review stage in `NEXT_STEPS.md`.

   To be exact about the review-to-commit binding, which this package does not satisfy: the last tree
   any reviewer saw is `89c8ffaa` (round 3, packet `933feab5`). Everything added after it is unreviewed -
   the four R3-F01 corrections, the `SKILLS_AND_TOOLS.md` note on the Windows script-test failures, this
   section itself, and the two continuity paragraphs recording the owner's decision. No code is among
   them: `git diff 89c8ffaa` over the committed tree touches documentation only, which is the reason the
   typecheck, test, build and E2E evidence above still applies to what was committed.
2. **Rendered appearance rests on the screenshots and the owner's screen check, not on an independent
   look.** Every round said so as its residual uncertainty: a text packet cannot carry an image. The
   owner's screen check passed and settled it for the pages and widths it covered (see above), but no
   automated check would catch a purely visual regression on a page the screen check did not open. The
   56 before-and-after screenshots at 1400px and 390px are with the owner as
   `<a PBL folder outside the repository>`, outside the repository, and were taken on `eddf1d3` - so
   they predate R2-F01's two restored margins, which are invisible at the same 16px anyway.
3. **No component test covers the menu button, the shared classes or the page styles.** The frontend has
   no component-test capability (`DEFERRED_REQUIREMENTS.md`). `menuPreference.test.ts` covers the
   remembered choice and the width default, and the mutation checks in rounds 1 and 2 prove those
   assertions can fail; the button and the CSS itself are covered by the screen check alone.
4. **`.data-table` is now one rule for every table in the application.** That is the point of the
   package, and it is also its standing risk: a later change to `.data-table` cells changes every table
   at once, including the five Equipment pages that dropped `.data-table-padded`. The same is true of
   `.text-success` and `.text-danger`, which set only `color` - a margin added there would move messages
   on every page that uses them, which is exactly why R2-F01 was fixed in the page and not in the class.
5. **Script validator unit tests: know where the figure came from.** The "100 passed" above was measured
   on Linux. On a Windows host four TE-5 deploy-script tests fail for environmental reasons unrelated to
   this package; see `docs/agent/SKILLS_AND_TOOLS.md` under "Validator unit tests" for the mechanism and
   the proof they are pre-existing.
6. **Deferred UI items this package deliberately left.** The 1,071 remaining inline `style={{}}`
   attributes, and the mid-word breaks in narrow table columns inside section cards (older than this
   package, found in its screenshots), are both in `docs/agent/UI_UX_CARRY_FORWARD.md` with the
   suggested fix. Move a page whole when it is next worked on, rather than one property across every
   page.

## Known gaps

- No component test: the button, the class and the page styles are covered by the screenshots and the
  owner's screen check only (the frontend has no component-test capability, `DEFERRED_REQUIREMENTS.md`).
- The remaining inline styles, and the mid-word breaks in narrow table columns inside section cards,
  are recorded in `docs/agent/UI_UX_CARRY_FORWARD.md`.
