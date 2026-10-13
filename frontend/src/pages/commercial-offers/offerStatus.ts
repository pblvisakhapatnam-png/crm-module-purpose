// The statuses the Commercial Offer edit form may set. Accepted and Rejected come only from the Customer Response
// action and Submitted only from Record as Submitted (Slice 6M.1). A submitted offer may be withdrawn or closed but
// not moved back to Draft or Ready for Review (TB-1 finding TB1-301, 4 October 2026), as the server's general update
// enforces.
export const COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS = ["DRAFT", "READY_FOR_REVIEW", "WITHDRAWN", "CLOSED"] as const;
const AFTER_SUBMISSION_OPTIONS = ["WITHDRAWN", "CLOSED"] as const;
const PREPARATION_VERSION_OPTIONS = ["DRAFT", "READY_FOR_REVIEW"] as const;

/** The statuses the edit form offers for an offer currently in `currentStatus`. */
export function statusUpdateOptions(currentStatus: string, isPreparationVersion = false): readonly string[] {
  if (isPreparationVersion) return PREPARATION_VERSION_OPTIONS;
  return currentStatus === "SUBMITTED" ? AFTER_SUBMISSION_OPTIONS : COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS;
}

// Slice 9F: one Commercial Offer row is one immutable version once sent. Only Draft and Ready for Review versions
// accept commercial-content changes. The server is authoritative; this hides forms that would only be refused.
const PRE_SUBMISSION_STATUSES: readonly string[] = ["DRAFT", "READY_FOR_REVIEW"];

/**
 * True when an offer in `status` does not take changes to its lines, prices, T&C, credit reviews or evidence.
 */
export function offerContentLocked(status: string): boolean {
  return !PRE_SUBMISSION_STATUSES.includes(status);
}

/** What the page shows in place of a content form the offer does not take now, in the server's words. */
export function contentLockedNote(status: string): string {
  const label = status.charAt(0) + status.slice(1).toLowerCase().replace(/_/g, " ");
  if (["ACCEPTED", "REJECTED", "WITHDRAWN", "CLOSED", "REVISED", "ABANDONED"].includes(status)) {
    return (
      `This offer is ${label}, so its lines, prices, T&C, credit reviews and submission evidence can no longer change. ` +
      "A change after the award goes on a Work Order amendment; otherwise raise a new offer."
    );
  }
  return `This offer is ${label}, so its lines, prices, T&C, credit reviews and submission evidence can no longer change on this version. Make a new version on the Submission tab.`;
}
