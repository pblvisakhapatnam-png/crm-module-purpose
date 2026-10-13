// What the offer page's two edit forms - the offer's details and one offer line - send (CS-05a, TB-1 finding
// TB1-303). Each save carries the version of the record the form was opened from, and only the fields the user
// changed: the server refuses a save from a form opened before someone else's (409), and a field the user did not
// touch is never written back over a value someone else has since saved.

/** The form's fields whose value differs from the form as it was opened, in the form's own order. */
export function changedFields<F extends Record<string, string>>(opened: F, edited: F): Array<keyof F & string> {
  return (Object.keys(edited) as Array<keyof F & string>).filter((key) => edited[key] !== opened[key]);
}

/** The request body for a save: the version the form was opened at, and each changed field's value from `values`,
 * which holds every field ready to send. */
export function updateRequest<V extends Record<string, unknown>>(
  expectedRowVersion: number,
  values: V,
  changed: ReadonlyArray<keyof V & string>,
): Record<string, unknown> {
  const request: Record<string, unknown> = { expected_row_version: expectedRowVersion };
  for (const key of changed) request[key] = values[key];
  return request;
}

/** Shown beside the Save button when the form is saved as it was opened. */
export const NOTHING_CHANGED_MESSAGE = "Nothing has been changed, so there is nothing to save.";
