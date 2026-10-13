// Whether the left menu is shown (the project owner, 26 September 2026: the menu can be hidden and shown
// again, as in many desktop apps, the page then using the full width). The choice is remembered per
// browser. Kept apart from AppShell so it can be tested without a browser DOM.

export const MENU_SHOWN_KEY = "pbl_menu_shown";

/** At this width and below the menu stops being a side panel and stacks above the page (globals.css). */
export const STACKED_MENU_QUERY = "(max-width: 900px)";

type ChoiceStore = Pick<Storage, "getItem" | "setItem">;

/**
 * The remembered choice. With none - or when the browser refuses its storage - the menu is shown beside
 * the page on a desktop, and hidden where it would stack above the page and push it a screen down.
 * The store is passed as a function because merely reaching `window.localStorage` can throw.
 */
export function readMenuShown(store: () => ChoiceStore, stacked: boolean): boolean {
  try {
    const saved = store().getItem(MENU_SHOWN_KEY);
    if (saved === "true") return true;
    if (saved === "false") return false;
  } catch {
    // Storage refused: fall through to the default.
  }
  return !stacked;
}

/** Remember the choice. If the browser refuses, the menu still opens and closes; it is only not remembered. */
export function writeMenuShown(store: () => ChoiceStore, shown: boolean): void {
  try {
    store().setItem(MENU_SHOWN_KEY, String(shown));
  } catch {
    // Storage refused: nothing to remember it in.
  }
}
