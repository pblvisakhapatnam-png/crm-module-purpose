import { describe, expect, it } from "vitest";

import {
  type AlertSettings,
  type AlertSettingVersion,
  type SettingForm,
  type SettingsPage,
  bandText,
  formBands,
  formFromVersion,
  initialSettingsPage,
  reminderDaysText,
  settingFormProblem,
  settingPayload,
  settingsPageAfter,
  settingsPageSaved,
  stepText,
} from "./alertSettingsState";
import { createQueryController } from "./certificatesState";

const ROLES = ["ADMIN", "OPERATIONS_USER", "MANAGEMENT_READ_ONLY", "SALES_USER"];

function version(bands: [number, number][], steps: [string, string, number | null][]): AlertSettingVersion {
  return {
    setting_public_id: "s",
    reminder_kind_code: "CERTIFICATE_RUNNING_OUT",
    version_number: 1,
    saved_by: null,
    saved_by_display_name: null,
    saved_at: "2026-10-01T00:00:00Z",
    bands: bands.map(([from_days_before, every_days]) => ({ from_days_before, every_days })),
    steps: steps.map(([role_code, starts_code, from_days_before], index) => ({
      step_number: index + 1,
      role_code,
      role_label: role_code,
      starts_code,
      from_days_before,
      channel_codes: ["SCREEN"],
    })),
  };
}

const STANDARD = version(
  [[60, 30], [15, 7], [7, 1], [0, 1]],
  [["ADMIN", "FIRST_REMINDER", null], ["OPERATIONS_USER", "DAYS_BEFORE", 15], ["MANAGEMENT_READ_ONLY", "DAYS_BEFORE", 7]],
);
const NOT_YET = version([[0, 1]], [["ADMIN", "FIRST_REMINDER", null], ["OPERATIONS_USER", "DAYS_BEFORE", -7], ["MANAGEMENT_READ_ONLY", "DAYS_BEFORE", -14]]);

describe("the reminder days, in words", () => {
  it("as the server reckons them", () => {
    expect(reminderDaysText(STANDARD.bands)).toBe("Reminders 60, 30, 15, 8, 7, 6, 5, 4, 3, 2 and 1 day before; on the day, and every day after that.");
    expect(reminderDaysText(NOT_YET.bands)).toBe("Reminders on the day, and every day after that.");
    expect(reminderDaysText([{ from_days_before: 30, every_days: 10 }, { from_days_before: 0, every_days: 7 }])).toBe(
      "Reminders 30, 20 and 10 days before; on the day, and every 7 days after that.",
    );
    expect(reminderDaysText([{ from_days_before: 10, every_days: 5 }, { from_days_before: -5, every_days: 1 }])).toBe(
      "Reminders 10 and 5 days before; on the day; 5 days after, and every day after that.",
    );
  });

  it("says each band and step", () => {
    expect(bandText({ from_days_before: 60, every_days: 30 })).toBe("From 60 days before the date, every 30 days");
    expect(bandText({ from_days_before: 0, every_days: 1 })).toBe("From the day itself, every day");
    expect(bandText({ from_days_before: -3, every_days: 2 })).toBe("From 3 days after the date, every 2 days");
    expect(stepText(STANDARD.steps[0])).toBe("from the first reminder");
    expect(stepText(STANDARD.steps[1])).toBe("from 15 days before the date");
    expect(stepText(NOT_YET.steps[1])).toBe("from 7 days after the date");
  });
});

describe("the form", () => {
  it("reads a version and sends it back as it was", () => {
    for (const item of [STANDARD, NOT_YET]) {
      const payload = settingPayload(formFromVersion(item), 4) as { expected_version: number; bands: unknown; steps: unknown };
      expect(payload.expected_version).toBe(4);
      expect(JSON.parse(JSON.stringify(payload.bands))).toEqual(item.bands);
      expect(payload.steps).toEqual(
        item.steps.map((step) => ({ role_code: step.role_code, starts_code: step.starts_code, from_days_before: step.from_days_before, channel_codes: ["SCREEN"] })),
      );
      expect(settingFormProblem(formFromVersion(item), ROLES)).toBeNull();
    }
  });

  it("refuses beside Save what the server refuses, in its words", () => {
    const base = formFromVersion(STANDARD);
    const cases: [SettingForm, string][] = [
      [{ ...base, bands: [] }, "at least one band"],
      [{ ...base, bands: Array.from({ length: 11 }, (_row, index) => ({ days: String(index), when: "after" as const, every: "1" })) }, "no more than 10"],
      [{ ...base, bands: [{ days: "x", when: "before", every: "1" }] }, "whole numbers"],
      [{ ...base, bands: [{ days: "366", when: "before", every: "1" }, { days: "0", when: "after", every: "1" }] }, "between 365 days before"],
      [{ ...base, bands: [{ days: "0", when: "after", every: "0" }] }, "every 1 to 365 days"],
      [{ ...base, bands: [{ days: "10", when: "before", every: "1" }, { days: "10", when: "before", every: "2" }, { days: "0", when: "after", every: "1" }] }, "same day"],
      [{ ...base, bands: [{ days: "60", when: "before", every: "30" }, { days: "7", when: "before", every: "1" }] }, "never left without reminders"],
      [{ ...base, steps: [] }, "at least one step"],
      [{ ...base, steps: [{ roleCode: "NOBODY", starts: "FIRST_REMINDER", days: "" }] }, "role from the list"],
      [{ ...base, steps: [{ roleCode: "ADMIN", starts: "FIRST_REMINDER", days: "" }, { roleCode: "ADMIN", starts: "BEFORE", days: "7" }] }, "one step only"],
      [{ ...base, steps: [{ roleCode: "ADMIN", starts: "BEFORE", days: "7" }] }, "first step must start at the first reminder"],
      [{ ...base, steps: [{ roleCode: "ADMIN", starts: "FIRST_REMINDER", days: "" }, { roleCode: "SALES_USER", starts: "BEFORE", days: "" }] }, "Give the days"],
      [{ ...base, steps: [{ roleCode: "ADMIN", starts: "FIRST_REMINDER", days: "" }, { roleCode: "SALES_USER", starts: "BEFORE", days: "61" }] }, "before the first reminder"],
      [{ ...base, steps: [{ roleCode: "ADMIN", starts: "FIRST_REMINDER", days: "" }, { roleCode: "SALES_USER", starts: "AFTER", days: "366" }] }, "no more than 365 days after"],
    ];
    for (const [form, words] of cases) {
      expect(settingFormProblem(form, ROLES), words).toContain(words);
    }
  });

  it("previews only the bands that are whole numbers", () => {
    const form = formFromVersion(STANDARD);
    expect(formBands({ ...form, bands: [...form.bands, { days: "", when: "before", every: "1" }] })).toEqual(formBands(form));
    expect(formBands(form).map((band) => band.every_days)).toEqual([30, 7, 1, 1]);
  });
});

describe("what the Reminder settings page shows across sessions", () => {
  function settingsOf(versionNumber: number): AlertSettings {
    const current = { ...version([[0, 1]], [["ADMIN", "FIRST_REMINDER", null]]), version_number: versionNumber };
    return {
      settings: [{ reminder_kind_code: "CERTIFICATE_RUNNING_OUT", reminder_kind_label: "A certificate running out", current, earlier: [] }],
      roles: [{ role_code: "ADMIN", role_label: "Admin" }],
      channel_codes: ["SCREEN"],
    } as unknown as AlertSettings;
  }

  function deferred<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((yes) => {
      resolve = yes;
    });
    return { promise, resolve };
  }

  // The page as the component keeps it (AlertSettingsPage.tsx): one state, changed only through the controller's
  // updates, and a read that keeps the settings shown only when asked to.
  function harness() {
    let page: SettingsPage = initialSettingsPage();
    const nextRead = { keepShown: false };
    const reads: { token: string; answer: ReturnType<typeof deferred<AlertSettings>> }[] = [];
    let token = "admin";
    const controller = createQueryController<null, AlertSettings>({
      initialQuery: null,
      getToken: () => token,
      failure: "Network error.",
      fetchAnswer: (readWith) => {
        const answer = deferred<AlertSettings>();
        reads.push({ token: readWith, answer });
        return answer.promise;
      },
      show: (update) => {
        const keepShown = nextRead.keepShown;
        if (update.kind !== "loading") nextRead.keepShown = false;
        page = settingsPageAfter(page, update, keepShown);
      },
    });
    return {
      reads,
      page: () => page,
      load: (keepShown: boolean) => {
        nextRead.keepShown = keepShown;
        return controller.refresh();
      },
      edit: (form: SettingForm) => {
        page = { ...page, forms: { ...page.forms, CERTIFICATE_RUNNING_OUT: form } };
      },
      signInAs: (next: string) => {
        token = next;
      },
    };
  }

  it("clears one session's settings and unsaved edits the moment another session reads, and keeps its late answer out", async () => {
    const h = harness();
    const opened = h.load(false);
    h.reads[0].answer.resolve(settingsOf(1));
    await opened;
    const edited = { ...formFromVersion(settingsOf(1).settings[0].current), bands: [] };
    h.edit(edited);

    // Admin's save is refused as stale: the settings are read again, kept on screen meanwhile.
    const adminRead = h.load(true);
    expect(h.page().view.answer?.settings[0].current.version_number).toBe(1);
    expect(h.page().forms.CERTIFICATE_RUNNING_OUT).toEqual(edited);

    // Before that read answers, someone else signs in: the page is cleared at once and read again for them.
    h.signInAs("operations");
    const operationsRead = h.load(false);
    expect(h.page().view.answer).toBeNull();
    expect(h.page().forms).toEqual({});
    expect(h.page().view.loading).toBe(true);

    // Admin's read answering late is not shown; the new session's answer is.
    h.reads[1].answer.resolve(settingsOf(7));
    await adminRead;
    expect(h.page().view.answer).toBeNull();
    expect(h.page().forms).toEqual({});
    h.reads[2].answer.resolve(settingsOf(2));
    await operationsRead;
    expect(h.reads.map((read) => read.token)).toEqual(["admin", "admin", "operations"]);
    expect(h.page().view.answer?.settings[0].current.version_number).toBe(2);
    expect(h.page().forms.CERTIFICATE_RUNNING_OUT).toEqual(formFromVersion(settingsOf(2).settings[0].current));
  });

  it("signed out: nothing of the earlier session is shown, and it is not left loading", () => {
    const shown = settingsPageAfter(settingsPageAfter(initialSettingsPage(), { kind: "answer", answer: settingsOf(1) }), { kind: "signed-out" });
    expect(shown.view.answer).toBeNull();
    expect(shown.view.loading).toBe(false);
    expect(shown.forms).toEqual({});
  });

  it("keeps the settings shown while the same session reads again after a stale save, then replaces them", () => {
    const shown = settingsPageAfter(initialSettingsPage(), { kind: "answer", answer: settingsOf(1) });
    const reading = settingsPageAfter(shown, { kind: "loading" }, true);
    expect(reading.view.answer).toEqual(settingsOf(1));
    expect(reading.view.loading).toBe(true);
    const answered = settingsPageAfter(reading, { kind: "answer", answer: settingsOf(3) });
    expect(answered.view.answer?.settings[0].current.version_number).toBe(3);
  });

  it("a saved setting replaces that setting and its form only", () => {
    const shown = settingsPageAfter(initialSettingsPage(), { kind: "answer", answer: settingsOf(1) });
    const saved = settingsPageSaved(shown, settingsOf(4).settings[0]);
    expect(saved.view.answer?.settings[0].current.version_number).toBe(4);
    expect(saved.view.answer?.roles).toEqual(shown.view.answer?.roles);
    expect(settingsPageSaved(initialSettingsPage(), settingsOf(4).settings[0])).toEqual(initialSettingsPage());
  });
});
