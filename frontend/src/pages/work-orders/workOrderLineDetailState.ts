// Pure state rules for the Work Order line-detail section (Slice 7C), kept out of the components so
// they can be tested without a browser DOM - the frontend has no component-test capability yet.
//
// Review round 2 found three ways page state could disagree with what the server holds: a form
// editable before its detail had loaded (so a save sent no version and got a false conflict), a first
// save's result dropped because the page only replaced entries it already had, and a slow initial
// load overwriting a newer save. These functions close each one.

export type VersionedLineDetail = {
  work_order_line_public_id: string;
  detail_version?: number | null;
};

/**
 * Page state for a list loaded per Work Order (line details, billing terms): its entries and the Work
 * Order they were loaded for. Forms are editable only while `loadedFor` names the Work Order on screen.
 */
export type LoadedList<T> = { entries: T[]; loadedFor: string | null };

export const EMPTY_LOADED_LIST: LoadedList<never> = { entries: [], loadedFor: null };

/** A load has started: nothing is loaded until it succeeds, so no form is editable meanwhile. */
export function listWhileLoading<T>(state: LoadedList<T>): LoadedList<T> {
  return { entries: state.entries, loadedFor: null };
}

export function listLoaded<T>(workOrderPublicId: string, entries: T[]): LoadedList<T> {
  return { entries, loadedFor: workOrderPublicId };
}

/**
 * A load failed. Earlier entries are dropped rather than left on screen as if current, and nothing is
 * editable until a load succeeds (review round 3: a failed refresh kept stale forms editable).
 */
export function listLoadFailed<T>(): LoadedList<T> {
  return { entries: [], loadedFor: null };
}

/** Replace the entry for the saved line, or add it if the page does not have one yet. */
export function upsertLineDetail<T extends VersionedLineDetail>(current: T[], saved: T): T[] {
  const index = current.findIndex((item) => item.work_order_line_public_id === saved.work_order_line_public_id);
  if (index === -1) return [...current, saved];
  const next = current.slice();
  next[index] = saved;
  return next;
}

/**
 * A line's form may be edited only once the page holds that line's detail entry. The list route
 * returns one entry per line, with a null version until the first save, so a present entry means the
 * version the form will send is the one the server last reported.
 */
export function canEditLine(detailsLoaded: boolean, entry: VersionedLineDetail | undefined): boolean {
  return detailsLoaded && entry !== undefined;
}

/**
 * Hands out numbered tokens so only the newest piece of state wins. Starting a list load and
 * applying a save both take a new token; a list response is applied only if its token is still the
 * newest, so a load that began before a save can never overwrite that save.
 */
export function createLatestGate(): { begin: () => number; isLatest: (token: number) => boolean } {
  let latest = 0;
  return {
    begin: () => {
      latest += 1;
      return latest;
    },
    isLatest: (token: number) => token === latest,
  };
}

/**
 * Whether a line card is shown open. Until the user opens or closes it (`userOpen` null), a line
 * with missing details - or details not loaded yet - is open and a complete line is closed. After
 * that the user's choice holds, so a save that completes the line does not snap it shut.
 */
export function lineCardOpen(userOpen: boolean | null, isComplete: boolean | undefined): boolean {
  return userOpen ?? !(isComplete ?? false);
}

/**
 * A details element fires `toggle` for its own programmatic changes too. Only a change away from the
 * state the page is showing is the user's choice.
 */
export function isUserToggle(nowOpen: boolean, shownOpen: boolean): boolean {
  return nowOpen !== shownOpen;
}
