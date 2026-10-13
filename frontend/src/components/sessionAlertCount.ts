// The menu's alert count is kept per session in sessionStorage for up to five minutes (ELG-2). TB-1 finding TB1-802
// (5 October 2026): the copy kept the whole sign-in token beside the count, and Sign out did not remove it, so a working
// token stayed in the tab after signing out. The copy now keeps a fingerprint of the token instead
// (pages/alerts/alertsState.ts), and Sign out and an ended session remove it.

/** The sessionStorage key the menu keeps its count under. */
export const ALERT_COUNT_KEY = "pbl_alert_count";

/** Remove the kept count; a store that refuses (private browsing, blocked storage) holds nothing to remove. */
export function forgetAlertCount(store: () => Pick<Storage, "removeItem">): void {
  try {
    store().removeItem(ALERT_COUNT_KEY);
  } catch {
    // Storage refused: nothing was kept there.
  }
}
