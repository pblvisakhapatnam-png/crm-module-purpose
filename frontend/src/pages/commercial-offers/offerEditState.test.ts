import { describe, expect, it } from "vitest";

import { changedFields, updateRequest } from "./offerEditState";

// CS-05a (TB-1 TB1-303): the offer page sends the version its form was opened from and only what the user changed,
// so a field nobody touched is never written back over someone else's save.

const opened = { offer_title: "Crane hire", offer_status_code: "DRAFT", remarks: "", offer_value: "1000.00" };

describe("the offer page's edit forms", () => {
  it("find only the fields the user changed", () => {
    expect(changedFields(opened, { ...opened })).toEqual([]);
    expect(changedFields(opened, { ...opened, remarks: "Customer asked for a second crane" })).toEqual(["remarks"]);
    expect(changedFields(opened, { ...opened, offer_title: "Crane hire, phase 2", offer_value: "1200.00" })).toEqual([
      "offer_title",
      "offer_value",
    ]);
  });

  it("count clearing a field as a change", () => {
    expect(changedFields(opened, { ...opened, offer_value: "" })).toEqual(["offer_value"]);
  });

  it("send the opened version and the changed fields only - never the status the form still shows", () => {
    const values = { offer_title: "Crane hire", offer_status_code: "DRAFT", remarks: "Second crane", offer_value: "1000.00" };
    expect(updateRequest(3, values, ["remarks"])).toEqual({ expected_row_version: 3, remarks: "Second crane" });
  });

  it("omit unchanged submission metadata when a preparation version header changes", () => {
    const values = {
      offer_title: "Crane hire, corrected scope",
      submitted_at: null,
      submission_reference: null,
      submission_proof_note: null,
    };
    expect(updateRequest(4, values, ["offer_title"])).toEqual({
      expected_row_version: 4,
      offer_title: "Crane hire, corrected scope",
    });
  });

  it("send a cleared field as the value given for it", () => {
    expect(updateRequest(1, { rate_amount: null, quantity: "2" }, ["rate_amount"])).toEqual({
      expected_row_version: 1,
      rate_amount: null,
    });
  });
});
