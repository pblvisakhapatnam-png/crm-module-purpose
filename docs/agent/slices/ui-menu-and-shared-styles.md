# App-wide UI - Hideable Menu and Shared Styles

An app-wide UI package, not a business slice: both parts touch every page, so one screen check covers
them (`docs/agent/UI_UX_CARRY_FORWARD.md`, "App shell (September 2026)" and "Equipment (ERT-1,
September 2026)"). Foundation Slice Mode.

## Status

Implemented 26 September 2026 on a feature branch, from `main` at `67786d2`
(ERT-1 merged, PR #72). Frontend only: no backend change, no migration (Alembic head unchanged at
`20260908_0042`), no new route, no permission or event change. The frozen Accepted Offer -> Work Order
handoff contract is byte-for-byte unchanged (SHA-256 `70debad7...b0e86a`, before and after). No visible
text changed except the new button's name and tooltip.

## Authority and required reading

- The owner's standing rule, 26 September 2026: `docs/agent/CODING_STANDARDS.md` sections 1 (DRY first,
  then KISS, YAGNI and SOLID) and 7 (style through `globals.css` classes and `--app-*` tokens, never
  inline `style={{...}}`).
- `docs/agent/UI_UX_CARRY_FORWARD.md`: "App shell (September 2026)", "Equipment (ERT-1, September 2026)",
  "Mobile layout (September 2026)", "Page decomposition".
- `docs/agent/UI_UAT_GUIDELINES.md`; `docs/agent/TESTING_STRATEGY.md` sections 7 and 11.
- `docs/agent/DEFERRED_REQUIREMENTS.md`: the frontend still has no component-test capability.
- No module contract applies: no API, event or data changed.

## Part 1 - The menu can be hidden

The owner's requirement (26 September 2026): the left menu can be hidden and shown again, as in many
desktop apps, the page then using the full width.

- **One button**, beside "PBL CRM" at the top of the menu, three lines on it. Its accessible name is
  "Menu"; `aria-expanded` says whether the menu is open and `aria-controls` names it; the tooltip says
  "Hide the menu" or "Show the menu".
- **Hidden**, the menu, the brand and the session panel go; only the button is left, at the top left on
  the page's own background, and the page takes the rest of the width. On a desktop that is a 60px
  strip; below 900px, where the menu has always stacked above the page, it is a row of its own above
  the page. The page keeps its reading width of at most 1180px, centred, as when the menu is shown.
- **One class**, `app-shell--menu-hidden` on `.app-shell`, in `globals.css`. The button is the only
  new element; the menu's contents are wrapped in one `div` (`#app-menu`) so the button can name it.
- **Remembered per browser** in `localStorage` (`pbl_menu_shown`), read and written in `try`/`catch`:
  a browser that refuses its storage still opens and closes the menu, and only forgets the choice.
  `frontend/src/layout/menuPreference.ts` holds the rule, apart from `AppShell` so it is tested
  without a browser DOM (`menuPreference.test.ts`, 4 tests).
- **Default, until the user chooses**: shown on a desktop, as the owner asked; hidden at 900px and
  below, where an open menu stacks above every page and pushes it a screen down (the owner's phone
  use, "Mobile layout"). The default is read once, when the application loads. **Confirmed by the
  owner at the screen check, 26 September 2026** (step 13); showing it by default on a phone too would
  be a one-line change if that is ever wanted.
- Works with the existing `@media` rules: 1100px is untouched, 900px stacks the menu as before or
  leaves the button row, 520px is untouched.

## Part 2 - The older pages on the shared classes

What ERT-1 added to `globals.css` for the Equipment pages, now used by the pages that still coloured
and padded inline.

**Table cells.** Every table in the frontend already carried `.data-table`, so the cell rule is now
`.data-table`'s own and `.data-table-padded` is gone:

```css
.data-table th, .data-table td {
  padding: 8px;
  border-bottom: 1px solid var(--app-border);
  text-align: left;
  vertical-align: top;
}
```

- **Which files, exactly** (corrected after review round 1, R1-F01). The owner named seven files and
  gave a grep, `grep -rn '<t[hd] style={{' frontend/src --include=*.tsx`. The two do not describe the
  same set, and neither is the whole of it:

  ```text
  The owner's grep finds 13 files (on main, 67786d2):
    named by the owner   WorkOrderDetailPage, WorkOrderAmendmentDetailPage, WorkOrderContractPeriodSection,
                         ResourceRequirementsPage, AccountsPage
    not named            LeadsPage, LeadDetailPage, OpportunitiesPage, OpportunityDetailPage,
                         CommercialOffersPage, TermsAndConditionsPage, DocumentsPage,
                         components/DocumentsPanel
                         (DocumentsPage and DocumentsPanel match only through their file-name cell,
                         written style={{ ...CELL_STYLE, ... }}; their other cells use the constants)
  Inline cell styles removed: 184, in 14 files - those 13, and AccountDetailPage (named by the owner),
    whose cells took their style from two constants the grep cannot see
  Changed nothing, takes the new rule: components/OperationalReports (named by the owner; its cells were bare)
  Dropped .data-table-padded: the five Equipment pages - ImportPreviewPage, MachinePage, MachinesPage,
    ModelsPage, PlumReportPage
  ```

  All 14 are moved because the rule can belong to `.data-table` only once every table follows it. The
  six cell-style constants, a header and a cell constant in each of `DocumentsPanel`, `DocumentsPage`
  and `AccountDetailPage`, are gone, and `grep -rnE '<t[hd][^>]*style=' frontend/src` now finds nothing.
  (The first version of this record said four constants; there were six.)
- The operational reports on the dashboard had bare cells, unpadded and with centred headings; they
  now take the rule, which is the visible gain of this part.
- Where the older tables differed, the rule takes the most common form: the row rule most list pages
  drew (in the theme's border colour, `#d8e0e8`, where they used `#eee` and `#ddd`) and the top
  alignment the Accounts, Documents and Equipment tables used. Work Order, Resource Planning and
  Equipment tables gain the row rule; Leads, Opportunities, Commercial Offers and the T&C library
  align to the top rather than the middle.
- Two cells kept a behaviour of their own and got a class for it: a file name breaks anywhere rather
  than widening its column (`.text-break-anywhere`), and remarks keep the lines they were typed on
  (`.text-pre-wrap`). A per-cell `overflowWrap: "anywhere"` inside a section card was dropped:
  `.section-card` already sets it for everything inside.
- The planning list's warnings list inside a cell is `.compact-list`, as ERT-1 made it for this.

**Message colours** in those 13 files and `AccountDetailPage` (the operational reports have none) are
on `.text-danger`, `.text-success` and `.text-warning`: 71 places - 64 messages, the warnings, the two
required-field asterisks on the Opportunity page and the amendment's "Proposed cancellation". `crimson`, `green` and
`#065f46` become the theme's red and green; `#92400e` and `#b91c1c` were already the theme's. Where a
message also set its margin, the margin stays inline: it is layout this package did not take on.

**The one visible difference to decide on.** A stylesheet rule has drawn a pink or green box around a
`<p>` whose inline style says `crimson` or `green`. A message moved onto the classes no longer matches
it, so on the moved pages an error or confirmation is now coloured text, as on the Equipment pages,
rather than a box. The rule stays for the pages not yet moved, with a comment saying so. If the owner
prefers the box, it becomes one rule on the classes, for every page, Equipment included.

## Not in scope, and recorded

In `docs/agent/UI_UX_CARRY_FORWARD.md`:

- 1,071 inline `style={{...}}` attributes remain (1,252 before), in 33 files; 445 are on the Commercial
  Offer page. Message colours remain in 15 files that have no table (the new-record pages, the Commercial Offer page, the
  Work Order line sections). The largest remaining groups have a class already: muted grey text
  (`#6b7280`, about 130) is `.helper-text`; the label-value grids are `.facts-list`.
- Nine table wrappers still set their top margin inline (0 or 12px, inside a section card).
- Found in the screenshots, older than this package: inside a section card, words and buttons in a
  narrow table column break mid-word ("Remo ve", "Li ne", "25,00 0"), because `.section-card` sets
  `overflow-wrap: anywhere` for everything inside, table cells included.

## Files

```text
frontend/src/layout/AppShell.tsx               the button, the class, the #app-menu wrapper
frontend/src/layout/menuPreference.ts          the remembered choice and its default (new)
frontend/src/layout/menuPreference.test.ts     4 tests (new)
frontend/src/styles/globals.css                the menu rules; the cell rule folded into .data-table;
                                               .text-break-anywhere, .text-pre-wrap
frontend/src/components/DocumentsPanel.tsx      cells and messages moved
frontend/src/components/OperationalReports.tsx  unchanged: its bare cells take the new rule
frontend/src/pages/  AccountsPage, AccountDetailPage, CommercialOffersPage, DocumentsPage, LeadsPage,
                     LeadDetailPage, OpportunitiesPage, OpportunityDetailPage, ResourceRequirementsPage,
                     TermsAndConditionsPage, WorkOrderDetailPage, WorkOrderAmendmentDetailPage,
                     WorkOrderContractPeriodSection, and the five Equipment pages (modifier removed)
```
