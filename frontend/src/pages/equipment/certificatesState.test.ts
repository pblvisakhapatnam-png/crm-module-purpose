import { describe, expect, it } from "vitest";

import {
  type QueryUpdate,
  type QueryView,
  createQueryController,
  initialQueryView,
  queryView,
  queryViewKeeping,
  ANSWER_LABELS,
  EMPTY_CERTIFICATE_FORM,
  EMPTY_MARK_FORM,
  EMPTY_RULE_FORM,
  type AssetCertificates,
  type Certificate,
  type CertificateKind,
  type MarkableKind,
  canManageRules,
  certificateFormProblem,
  certificatePayload,
  certificateText,
  checkFormProblem,
  checkQuery,
  daysBetween,
  otherCertificateText,
  otherMarkText,
  otherRecords,
  dueQuery,
  dueText,
  formatDay,
  markFormProblem,
  markPayload,
  needsPieceMark,
  pieceMarkText,
  resultText,
  ruleFormProblem,
  fitRuleToKind,
  ruleJurisdictionChoices,
  rulePayload,
  ruleText,
  siteStates,
  statusText,
} from "./certificatesState";

const TODAY = "2026-09-27";

const kind = (code: string, flags: Partial<CertificateKind> = {}): CertificateKind => ({
  kind_code: code,
  kind_label: code === "INSURANCE" ? "Insurance" : code === "PERMIT" ? "Permit" : code === "REGISTRATION" ? "Registration" : "Thorough examination",
  end_date_optional: false,
  valid_in_required: false,
  is_examination: false,
  states_registration: false,
  ...flags,
});

const certificate = (changes: Partial<Certificate> = {}): Certificate => ({
  certificate_public_id: "c1",
  asset_public_id: "a1",
  asset_reference: "EQ-000001",
  kind_code: "INSURANCE",
  kind_label: "Insurance",
  number: "POL-1",
  number_withheld: false,
  issued_by: "Invented Insurer",
  issued_on: "2026-01-01",
  valid_from: "2026-01-01",
  valid_until: "2026-12-31",
  valid_in_code: null,
  valid_in_label: null,
  registered_as_code: null,
  certificate_status_code: "RECORDED",
  has_copy: true,
  in_force: true,
  recorded_by_display_name: "Admin",
  recorded_at: "2026-01-01T00:00:00Z",
  withdrawn_reason: null,
  withdrawn_by_display_name: null,
  withdrawn_at: null,
  ...changes,
});

describe("words", () => {
  it("shows a whole date as the screens do and counts days between two", () => {
    expect(formatDay("2027-03-12")).toBe("12 March 2027");
    expect(formatDay(null)).toBe("-");
    expect(daysBetween("2026-09-27", "2026-10-09")).toBe(12);
  });

  it("says where each certificate stands on a machine's page", () => {
    const base = { mark: null, certificate: null };
    expect(statusText({ ...base, outcome_code: "VALID", cover_ends_on: "2027-03-12" }, TODAY)).toBe("valid until 12 March 2027");
    expect(statusText({ ...base, outcome_code: "VALID", cover_ends_on: null }, TODAY)).toBe("valid, with no end date");
    expect(statusText({ ...base, outcome_code: "RUNS_OUT_SOON", cover_ends_on: "2026-10-09" }, TODAY)).toBe("runs out in 12 days");
    expect(statusText({ ...base, outcome_code: "RUNS_OUT_SOON", cover_ends_on: "2026-09-28" }, TODAY)).toBe("runs out in 1 day");
    expect(statusText({ ...base, outcome_code: "RUN_OUT", cover_ends_on: "2026-09-03" }, TODAY)).toBe("ran out on 3 September 2026");
    expect(statusText({ ...base, outcome_code: "MISSING", cover_ends_on: null }, TODAY)).toBe("missing");
    expect(statusText({ ...base, outcome_code: "COPY_MISSING", cover_ends_on: null }, TODAY)).toBe("copy missing");
    const mark = { reason: "Tracked crane.", until_date: null } as AssetCertificates["marks"][number];
    expect(statusText({ ...base, mark, outcome_code: "NOT_APPLICABLE", cover_ends_on: null }, TODAY)).toBe("not applicable: Tracked crane.");
    // Withheld with the numbers (round 6).
    const withheld = { reason: null, until_date: null } as AssetCertificates["marks"][number];
    expect(statusText({ ...base, mark: withheld, outcome_code: "NOT_APPLICABLE", cover_ends_on: null }, TODAY)).toBe("not applicable (reason shown to Admin only)");
    const ending = { reason: "First year.", until_date: "2026-10-05" } as AssetCertificates["marks"][number];
    expect(statusText({ ...base, mark: ending, outcome_code: "RUNS_OUT_SOON", cover_ends_on: "2026-10-05" }, TODAY)).toBe(
      "not applicable: First year. (until 5 October 2026); ends in 8 days",
    );
    expect(statusText({ ...base, outcome_code: null, cover_ends_on: null }, TODAY)).toBe("no certificate in force");
  });

  it("says what each result of a check means, in the words of Q4", () => {
    expect(resultText({ outcome_code: "RUNS_OUT_BEFORE_START", cover_ends_on: "2026-10-05", mark_public_id: null })).toBe("runs out on 5 October 2026, before the job starts - renew it");
    expect(resultText({ outcome_code: "RUNS_OUT_IN_PERIOD", cover_ends_on: "2026-10-20", mark_public_id: null })).toBe("runs out on 20 October 2026, during the period - renew it");
    expect(resultText({ outcome_code: "COPY_MISSING", cover_ends_on: null, mark_public_id: null })).toBe("its copy is missing");
    expect(resultText({ outcome_code: "RETIRED", cover_ends_on: null, mark_public_id: null })).toBe("retired");
    // A mark ending before or during the job (round 3, ELG1-R3-001).
    expect(resultText({ outcome_code: "RUNS_OUT_BEFORE_START", cover_ends_on: "2026-09-30", mark_public_id: "m" })).toBe(
      "not applicable until 30 September 2026, before the job starts - the certificate is needed after that",
    );
    expect(resultText({ outcome_code: "NOT_APPLICABLE", cover_ends_on: null, mark_public_id: "m" })).toBe("not applicable");
    expect(ANSWER_LABELS.WARNING).toBe("Can be allocated, with a warning");
  });

  it("writes a certificate's facts, keeping its number from those who may not see it", () => {
    expect(certificateText(certificate())).toBe("No. POL-1, by Invented Insurer; 1 January 2026 to 31 December 2026");
    expect(certificateText(certificate({ number: null, number_withheld: true, kind_code: "REGISTRATION", registered_as_code: "TRANSPORT" }))).toBe(
      "number shown to Admin only, by Invented Insurer; 1 January 2026 to 31 December 2026; registered as a transport vehicle",
    );
    expect(certificateText(certificate({ valid_until: null, valid_in_code: "IN", valid_in_label: "Central government sites" }))).toContain("valid in all India");
  });

  it("names how a piece of tackle is matched to its certificate", () => {
    expect(pieceMarkText({ serial_number: "SL-7", asset_reference: "EQ-000512" })).toBe("its own number SL-7");
    expect(pieceMarkText({ serial_number: null, asset_reference: "EQ-000512" })).toBe("stencil EQ-000512 on it");
    expect(needsPieceMark({ origin_code: "PLATFORM", class_code: "LIFTING_TACKLE" })).toBe(true);
    expect(needsPieceMark({ origin_code: "PLATFORM", class_code: "COUNTERWEIGHT" })).toBe(false);
    expect(needsPieceMark({ origin_code: "PLUM", class_code: "CRANE" })).toBe(false);
  });

  it("sums a rule up", () => {
    expect(ruleText({ renew_every_months: 6, lapse_code: "BLOCK", basis_code: "PBL_RULE", not_applicable_code: "NOT_ALLOWED", not_applicable_max_months: null })).toBe(
      "every 6 months; a lapse stops the machine; PBL's own rule",
    );
    expect(ruleText({ renew_every_months: null, lapse_code: "BLOCK", basis_code: "STATUTORY", not_applicable_code: "ALLOWED", not_applicable_max_months: 12 })).toBe(
      "a lapse stops the machine; the law; may be marked not applicable for at most 12 months",
    );
  });

  it("offers rules only to Admin", () => {
    expect(canManageRules(["ADMIN"])).toBe(true);
    expect(canManageRules(["OPERATIONS_USER", "SALES_MANAGER"])).toBe(false);
  });
});

describe("recording a certificate", () => {
  const complete = { ...EMPTY_CERTIFICATE_FORM, kindCode: "INSURANCE", number: " POL-1 ", issuedBy: "Insurer", issuedOn: "2026-09-01", validFrom: "2026-09-01", validUntil: "2027-08-31" };

  it("refuses what the server would refuse", () => {
    expect(certificateFormProblem(complete, undefined, TODAY)).toBe("Choose the kind of certificate.");
    expect(certificateFormProblem({ ...complete, number: " " }, kind("INSURANCE"), TODAY)).toContain("number");
    expect(certificateFormProblem({ ...complete, issuedOn: "2026-09-28" }, kind("INSURANCE"), TODAY)).toContain("future");
    expect(certificateFormProblem({ ...complete, validUntil: "2026-08-31" }, kind("INSURANCE"), TODAY)).toContain("before it starts");
    expect(certificateFormProblem({ ...complete, validUntil: "" }, kind("INSURANCE"), TODAY)).toContain("runs until");
    expect(certificateFormProblem({ ...complete, validUntil: "" }, kind("THOROUGH_EXAMINATION", { end_date_optional: true, is_examination: true }), TODAY)).toBeNull();
    expect(certificateFormProblem(complete, kind("PERMIT", { valid_in_required: true }), TODAY)).toContain("where the permit");
    expect(certificateFormProblem(complete, kind("REGISTRATION", { states_registration: true }), TODAY)).toContain("transport");
    expect(certificateFormProblem(complete, kind("INSURANCE"), TODAY)).toBeNull();
  });

  it("sends only what the kind takes", () => {
    const body = certificatePayload({ ...complete, validIn: "IN-GJ", registeredAs: "TRANSPORT" }, kind("INSURANCE"), "key-1");
    expect(body).toMatchObject({ create_request_key: "key-1", kind_code: "INSURANCE", number: "POL-1", valid_in_code: null, registered_as_code: null });
    expect(certificatePayload({ ...complete, validIn: "IN-GJ" }, kind("PERMIT", { valid_in_required: true }), "k").valid_in_code).toBe("IN-GJ");
    expect(certificatePayload({ ...complete, validUntil: "" }, kind("ROAD_TAX", { end_date_optional: true }), "k").valid_until).toBeNull();
  });
});

describe("marking not applicable", () => {
  const markable = (latest: string | null): MarkableKind => ({
    kind_code: "POLLUTION_UNDER_CONTROL",
    kind_label: "Pollution certificate (PUC)",
    latest_until: latest,
    rule: { rule_public_id: "r", jurisdiction_code: null, basis_code: "STATUTORY", lapse_code: "BLOCK", renew_every_months: null, not_applicable_code: "ALLOWED", not_applicable_max_months: latest ? 12 : null, source: "s", note: null },
  });

  it("asks for a reason, and an end within the rule's limit where it has one", () => {
    const form = { ...EMPTY_MARK_FORM, kindCode: "POLLUTION_UNDER_CONTROL", reason: "First year after registration." };
    expect(markFormProblem(form, undefined, TODAY)).toContain("rules allow");
    expect(markFormProblem({ ...form, reason: " " }, markable(null), TODAY)).toContain("reason");
    expect(markFormProblem(form, markable(null), TODAY)).toBeNull();
    expect(markFormProblem(form, markable("2027-09-26"), TODAY)).toContain("no later than 26 September 2027");
    expect(markFormProblem({ ...form, until: "2027-09-27" }, markable("2027-09-26"), TODAY)).toContain("at most 12 months");
    expect(markFormProblem({ ...form, until: "2026-09-26" }, markable("2027-09-26"), TODAY)).toContain("past");
    expect(markFormProblem({ ...form, until: "2027-09-26" }, markable("2027-09-26"), TODAY)).toBeNull();
    expect(markPayload({ ...form, until: "" }, "k")).toEqual({ create_request_key: "k", kind_code: "POLLUTION_UNDER_CONTROL", reason: "First year after registration.", until: null });
  });
});

describe("the check", () => {
  it("needs a state and a start, and a period that does not end before it starts", () => {
    const form = { stateCode: "IN-GJ", central: false, from: "2026-10-01", to: "2026-10-31" };
    expect(checkFormProblem({ ...form, stateCode: "" })).toContain("state");
    expect(checkFormProblem({ ...form, from: "" })).toContain("starts");
    expect(checkFormProblem({ ...form, to: "2026-09-30" })).toContain("before it starts");
    expect(checkFormProblem({ ...form, to: "" })).toBeNull();
    expect(checkQuery(form)).toBe("state_code=IN-GJ&period_from=2026-10-01&central_government_site=false&period_to=2026-10-31");
    expect(checkQuery({ ...form, to: "", central: true })).toBe("state_code=IN-GJ&period_from=2026-10-01&central_government_site=true");
  });

  it("offers states and territories, not the central government's own sites", () => {
    const listed = siteStates([
      { jurisdiction_code: "IN", jurisdiction_label: "Central government sites", jurisdiction_kind_code: "CENTRAL", gst_state_code: null },
      { jurisdiction_code: "IN-GJ", jurisdiction_label: "Gujarat", jurisdiction_kind_code: "STATE", gst_state_code: "24" },
    ]);
    expect(listed.map((item) => item.jurisdiction_code)).toEqual(["IN-GJ"]);
  });
});

describe("certificates due", () => {
  it("asks for only the filters chosen", () => {
    expect(dueQuery({ band: "", classCode: "", kindCode: "", search: " " }, 0, 50)).toBe("limit=50&offset=0");
    expect(dueQuery({ band: "RUN_OUT", classCode: "CRANE", kindCode: "INSURANCE", search: "EQ-1" }, 50, 50)).toBe(
      "limit=50&offset=50&band=RUN_OUT&class_code=CRANE&kind_code=INSURANCE&search=EQ-1",
    );
  });

  it("says what is due", () => {
    expect(dueText({ band_code: "MISSING", cover_ends_on: null, mark_public_id: null })).toBe("missing");
    expect(dueText({ band_code: "RUN_OUT", cover_ends_on: "2026-09-03", mark_public_id: null })).toBe("ran out on 3 September 2026");
    expect(dueText({ band_code: "WITHIN_15", cover_ends_on: "2026-10-05", mark_public_id: null })).toBe("runs out on 5 October 2026");
    expect(dueText({ band_code: "WITHIN_30", cover_ends_on: "2026-10-20", mark_public_id: "m" })).toBe('"not applicable" ends on 20 October 2026');
  });
});

describe("rules", () => {
  const complete = { ...EMPTY_RULE_FORM, kindCode: "THOROUGH_EXAMINATION", classCode: "CRANE", effectiveFrom: "2026-10-01", renewEvery: "6", basis: "PBL_RULE", source: "Test rule." };
  const examination = kind("THOROUGH_EXAMINATION", { end_date_optional: true, is_examination: true });

  it("refuses what the server would refuse", () => {
    expect(ruleFormProblem(complete, undefined)).toContain("certificate");
    expect(ruleFormProblem({ ...complete, basis: "STATUTORY", lapse: "WARN" }, examination)).toContain("law always stops");
    expect(ruleFormProblem({ ...complete, renewEvery: "" }, examination)).toContain("how often");
    expect(ruleFormProblem({ ...complete, renewEvery: "12" }, kind("INSURANCE"))).toContain("states its own end");
    expect(ruleFormProblem({ ...complete, lapse: "NOT_REQUIRED", renewEvery: "", notApplicable: "ALLOWED" }, examination)).toContain("Nothing is required");
    expect(ruleFormProblem({ ...complete, maxMonths: "6" }, examination)).toContain("needs 'not applicable'");
    expect(ruleFormProblem({ ...complete, source: " " }, examination)).toContain("source");
    // The server's bounds: an interval of 1 to 240 months, a mark's limit of 1 to 120.
    expect(ruleFormProblem({ ...complete, renewEvery: "0" }, examination)).toContain("1 to 240");
    expect(ruleFormProblem({ ...complete, renewEvery: "241" }, examination)).toContain("1 to 240");
    expect(ruleFormProblem({ ...complete, renewEvery: "240" }, examination)).toBeNull();
    const allowed = { ...complete, notApplicable: "ALLOWED" };
    expect(ruleFormProblem({ ...allowed, maxMonths: "0" }, examination)).toContain("1 to 120");
    expect(ruleFormProblem({ ...allowed, maxMonths: "121" }, examination)).toContain("1 to 120");
    expect(ruleFormProblem({ ...allowed, maxMonths: "120" }, examination)).toBeNull();
    expect(ruleFormProblem(complete, examination)).toBeNull();
    // Round 5: the registration decides transport, and only the examinations have central-site rules.
    const registration = kind("REGISTRATION", { states_registration: true });
    const roadPaper = { ...complete, kindCode: "REGISTRATION", renewEvery: "" };
    expect(ruleFormProblem({ ...roadPaper, appliesWhen: "TRANSPORT_ONLY" }, registration)).toContain("applies always");
    expect(ruleFormProblem({ ...roadPaper, jurisdictionCode: "IN" }, registration)).toContain("only the examinations");
    expect(ruleFormProblem({ ...roadPaper, jurisdictionCode: "IN-GJ" }, registration)).toBeNull();
    expect(ruleFormProblem({ ...complete, jurisdictionCode: "IN" }, examination)).toBeNull();
  });

  it("drops what a newly chosen certificate cannot have, and offers only the places its rules can apply", () => {
    const registration = kind("REGISTRATION", { states_registration: true });
    const filled = { ...complete, appliesWhen: "TRANSPORT_ONLY", jurisdictionCode: "IN" };
    expect(fitRuleToKind({ ...filled, kindCode: "REGISTRATION" }, registration)).toMatchObject({ renewEvery: "", appliesWhen: "ALWAYS", jurisdictionCode: "" });
    expect(fitRuleToKind({ ...filled, kindCode: "INSURANCE" }, kind("INSURANCE"))).toMatchObject({ renewEvery: "", appliesWhen: "TRANSPORT_ONLY", jurisdictionCode: "" });
    expect(fitRuleToKind(filled, examination)).toEqual(filled);
    expect(fitRuleToKind({ ...complete, jurisdictionCode: "IN-GJ" }, kind("INSURANCE")).jurisdictionCode).toBe("IN-GJ");
    const places = [
      { jurisdiction_code: "IN", jurisdiction_label: "Central government sites", jurisdiction_kind_code: "CENTRAL", gst_state_code: null },
      { jurisdiction_code: "IN-GJ", jurisdiction_label: "Gujarat", jurisdiction_kind_code: "STATE", gst_state_code: "24" },
    ];
    expect(ruleJurisdictionChoices(places, examination).map((item) => item.jurisdiction_code)).toEqual(["IN", "IN-GJ"]);
    expect(ruleJurisdictionChoices(places, registration).map((item) => item.jurisdiction_code)).toEqual(["IN-GJ"]);
  });

  it("sends empty choices as none", () => {
    expect(rulePayload(complete, "k")).toMatchObject({ type_code: null, jurisdiction_code: null, renew_every_months: 6, not_applicable_max_months: null, note: null });
    expect(rulePayload({ ...complete, jurisdictionCode: "IN-GJ", typeCode: "CRAWLER" }, "k")).toMatchObject({ type_code: "CRAWLER", jurisdiction_code: "IN-GJ" });
  });
});

describe("records outside the status rows", () => {
  const mark = (id: string, status: string, until: string | null = null) =>
    ({ mark_public_id: id, mark_status_code: status, until_date: until }) as AssetCertificates["marks"][number];

  it("lists every certificate and mark once, those still live with their Withdraw", () => {
    const inRow = certificate({ certificate_public_id: "in-row" });
    const later = certificate({ certificate_public_id: "later", in_force: false, valid_from: "2027-01-01" });
    const withdrawn = certificate({ certificate_public_id: "gone", in_force: false, certificate_status_code: "WITHDRAWN" });
    const counted = mark("counted", "IN_FORCE");
    const ended = mark("ended", "IN_FORCE", "2026-09-01");
    const old = mark("old", "WITHDRAWN");
    const status = { kind_code: "INSURANCE", certificate: inRow, mark: null } as unknown as AssetCertificates["statuses"][number];
    const marked = { kind_code: "ROAD_TAX", certificate: null, mark: counted } as unknown as AssetCertificates["statuses"][number];
    const records = otherRecords({ statuses: [status, marked], certificates: [inRow, later, withdrawn], marks: [counted, ended, old] });
    expect(records.liveCertificates.map((item) => item.certificate_public_id)).toEqual(["later"]);
    expect(records.historyCertificates.map((item) => item.certificate_public_id)).toEqual(["gone"]);
    expect(records.liveMarks.map((item) => item.mark_public_id)).toEqual(["ended"]);
    expect(records.historyMarks.map((item) => item.mark_public_id)).toEqual(["old"]);
    expect(otherCertificateText(later, TODAY)).toBe("takes over on 1 January 2027");
    expect(otherCertificateText(certificate({ in_force: true }), TODAY)).toBe("in force, not required of it today");
    expect(otherCertificateText(certificate({ in_force: false, valid_from: "2026-01-01" }), TODAY)).toBe("replaced by a later one");
    expect(otherMarkText(ended, TODAY)).toBe("ended on 1 September 2026; withdraw it before marking again");
    expect(otherMarkText(mark("x", "IN_FORCE"), TODAY)).toBe("not counted by the rule in force here");
    // A registration in force wins over the registration's mark (owner, 28 September 2026).
    const registrationMark = { ...mark("r", "IN_FORCE"), kind_code: "REGISTRATION" };
    expect(otherMarkText(registrationMark, TODAY, true)).toBe("not counted while a registration is in force");
    expect(otherMarkText(registrationMark, TODAY, false)).toBe("not counted by the rule in force here");
    expect(otherMarkText({ ...mark("i", "IN_FORCE"), kind_code: "INSURANCE" }, TODAY, true)).toBe("not counted by the rule in force here");
  });
});

describe("loading one answer", () => {
  type Deferred = { resolve: (value: string) => void; reject: (error: Error) => void };

  function harness() {
    const pending: Record<string, Deferred[]> = {};
    let view: QueryView<string> = initialQueryView<string>();
    const controller = createQueryController<string, string>({
      initialQuery: "A",
      getToken: () => "token",
      fetchAnswer: (_token, query) =>
        new Promise<string>((resolve, reject) => {
          (pending[query] ??= []).push({ resolve, reject });
        }),
      show: (update) => {
        view = queryView(view, update);
      },
      failure: "failed",
    });
    return { controller, pending, view: () => view };
  }

  it("clears the old answer the moment another query starts, and never shows an older answer after a newer request", async () => {
    const { controller, pending, view } = harness();
    const first = controller.refresh();
    pending.A[0].resolve("answer for A");
    await first;
    expect(view().answer).toBe("answer for A");
    // The controls move to B: A's answer goes at once, before B answers.
    const toB = controller.setQuery("B");
    expect(view()).toEqual({ answer: null, loading: true, error: "" });
    // Back to A, whose answer comes before B's slow one: B's arrives last and is dropped.
    const backToA = controller.setQuery("A");
    pending.A[1].resolve("A again");
    await backToA;
    pending.B[0].resolve("late answer for B");
    await toB;
    expect(view().answer).toBe("A again");
  });

  it("reloads the query the controls show, and a save made under another query reloads nothing", async () => {
    const { controller, pending, view } = harness();
    void controller.setQuery("B");
    const reload = controller.refresh();
    expect(pending.B).toHaveLength(2);
    expect(pending.A).toBeUndefined();
    pending.B[1].resolve("fresh B");
    await reload;
    expect(view().answer).toBe("fresh B");
    // A save sent while the page showed A returns after it moved to B: nothing is reloaded or shown.
    expect(controller.isCurrent("A")).toBe(false);
    expect(controller.refreshIf("A")).toBeNull();
    expect(pending.A).toBeUndefined();
    expect(view().answer).toBe("fresh B");
    const same = controller.refreshIf("B");
    expect(same).not.toBeNull();
    pending.B[2].resolve("B after the save");
    await same;
    expect(view().answer).toBe("B after the save");
  });

  it("shows an answer already in hand, and a read still in flight cannot replace it (8A-FB-007)", async () => {
    const { controller, pending, view } = harness();
    const reading = controller.refresh();
    // A write's response arrives, carrying the record as it now stands, while an older read is in flight.
    controller.answered("from the write");
    expect(view()).toEqual({ answer: "from the write", loading: false, error: "" });
    pending.A[0].resolve("older read");
    await reading;
    expect(view().answer).toBe("from the write");
  });

  it("a failure shows no answer, and only the latest request's failure is shown", async () => {
    const { controller, pending, view } = harness();
    const older = controller.refresh();
    const newer = controller.setQuery("B");
    pending.A[0].reject(new Error("A failed"));
    await older;
    expect(view().error).toBe("");
    pending.B[0].reject(new Error("B failed"));
    await newer;
    expect(view()).toEqual({ answer: null, loading: false, error: "B failed" });
  });

  it("asks for nothing when signed out", async () => {
    const shown: QueryUpdate<string>[] = [];
    const controller = createQueryController<string, string>({
      initialQuery: "A",
      getToken: () => null,
      fetchAnswer: () => Promise.reject(new Error("not asked")),
      show: (update) => shown.push(update),
      failure: "failed",
    });
    await controller.refresh();
    expect(shown).toEqual([{ kind: "signed-out" }]);
  });
});

describe("reading the shown answer again", () => {
  const shown = { answer: "A1", loading: false, error: "" };
  const isA = (answer: string) => answer.startsWith("A");

  it("keeps the answer on screen while the same query is read again, so the page does not empty", () => {
    expect(queryViewKeeping(shown, { kind: "loading" }, isA)).toEqual({ answer: "A1", loading: true, error: "" });
    expect(queryViewKeeping({ ...shown, loading: true }, { kind: "answer", answer: "A2" }, isA)).toEqual({ answer: "A2", loading: false, error: "" });
  });

  it("clears it for another query, and on a failure or signing out, as queryView does", () => {
    expect(queryViewKeeping(shown, { kind: "loading" }, (answer) => answer.startsWith("B")).answer).toBeNull();
    expect(queryViewKeeping(shown, { kind: "failed", message: "No" }, isA)).toEqual({ answer: null, loading: false, error: "No" });
    expect(queryViewKeeping(shown, { kind: "signed-out" }, isA).answer).toBeNull();
  });
});
