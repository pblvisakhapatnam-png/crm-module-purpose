import { describe, expect, it } from "vitest";

import {
  COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS,
  contentLockedNote,
  offerContentLocked,
  statusUpdateOptions,
} from "./offerStatus";

describe("statusUpdateOptions", () => {
  it("offers every editable status before submission", () => {
    expect(statusUpdateOptions("DRAFT")).toEqual(COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS);
    expect(statusUpdateOptions("READY_FOR_REVIEW")).toEqual(COMMERCIAL_OFFER_STATUS_UPDATE_OPTIONS);
  });

  it("never offers Draft or Ready for Review for a submitted offer, only withdrawing or closing it", () => {
    expect(statusUpdateOptions("SUBMITTED")).toEqual(["WITHDRAWN", "CLOSED"]);
  });

  it("keeps a later preparation version in Draft or Ready for Review until it is sent or abandoned", () => {
    expect(statusUpdateOptions("DRAFT", true)).toEqual(["DRAFT", "READY_FOR_REVIEW"]);
    expect(statusUpdateOptions("READY_FOR_REVIEW", true)).toEqual(["DRAFT", "READY_FOR_REVIEW"]);
  });

  it("never offers Accepted, Rejected or Submitted, which have their own actions", () => {
    for (const status of ["DRAFT", "READY_FOR_REVIEW", "SUBMITTED"]) {
      for (const ownAction of ["ACCEPTED", "REJECTED", "SUBMITTED"]) {
        expect(statusUpdateOptions(status)).not.toContain(ownAction);
      }
    }
  });
});

describe("offerContentLocked", () => {
  it("locks every sent, final, replaced or abandoned version", () => {
    for (const status of ["SUBMITTED", "ACCEPTED", "REJECTED", "WITHDRAWN", "CLOSED", "REVISED", "ABANDONED"]) {
      expect(offerContentLocked(status)).toBe(true);
    }
  });

  it("leaves an offer's content open before it is submitted", () => {
    for (const status of ["DRAFT", "READY_FOR_REVIEW"]) {
      expect(offerContentLocked(status)).toBe(false);
    }
  });

  it("locks a status it does not know after submission, as the server does", () => {
    expect(offerContentLocked("UNKNOWN")).toBe(true);
  });

  it("says why, with the status in words, as the server does", () => {
    expect(contentLockedNote("ACCEPTED")).toContain("This offer is Accepted, so its lines, prices, T&C");
    expect(contentLockedNote("WITHDRAWN")).toContain("This offer is Withdrawn");
    expect(contentLockedNote("ACCEPTED")).toContain("can no longer change");
  });

  it("tells a submitted offer's user how to make a change", () => {
    const note = contentLockedNote("SUBMITTED");
    expect(note).toContain("This offer is Submitted, so its lines, prices, T&C, credit reviews and submission evidence");
    expect(note).toContain("can no longer change on this version");
    expect(note).toContain("Make a new version on the Submission tab");
  });
});
