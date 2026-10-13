import { useEffect, useState } from "react";

import { PageHeader, SectionCard } from "../../components/PageLayout";
import { SIGN_IN_FIRST } from "../../components/signInMessages";
import { SESSION_CHANGED_EVENT, clearSession, formatDateTime, getToken, readErrorDetail, readRoleCodes } from "../resource-requirements/pageSession";
import { actInSession, createSessionGuard, readActionAnswer } from "../alerts/alertsState";
import {
  EMPTY_BAND_ROW,
  MAX_BANDS,
  MAX_STEPS,
  type AlertRole,
  type AlertSetting,
  type AlertSettingAction,
  type AlertSettings,
  type AlertSettingVersion,
  type BandRow,
  type SettingForm,
  type StepRow,
  type StepStart,
  bandText,
  formBands,
  formFromVersion,
  initialSettingsPage,
  reminderDaysText,
  sameForm,
  settingFormProblem,
  settingPayload,
  settingsPageAfter,
  settingsPageSaved,
  stepText,
} from "./alertSettingsState";
import { canManageRules, createQueryController } from "./certificatesState";
import { EquipmentNav, FeedbackLine } from "./EquipmentParts";
import type { Feedback } from "./equipmentState";

// Reminder settings (ELG-2, design section 5.6): for each kind of reminder, its schedule and its path. Everyone may
// read them; Admin changes them (ELIGIBILITY_RULE_MANAGE, Q18). A change is saved as a new version - nothing is
// edited - and applies at once, as the reminders are worked out when read.

export default function AlertSettingsPage() {
  // The settings and the forms made from them, changed through the read's updates (alertSettingsState.ts).
  const [page, setPage] = useState(initialSettingsPage);
  const settings = page.view.answer;
  const { forms } = page;
  const { loading, error } = page.view;
  const [canManage, setCanManage] = useState(false);
  const [busy, setBusy] = useState("");
  const [feedback, setFeedback] = useState<Record<string, Feedback>>({});
  // A save's answer is applied only in the session it was made in (alertsState.ts).
  const [session] = useState(() => createSessionGuard());
  // Whether the next read keeps the settings shown: only the same session reading again after a stale save.
  const [nextRead] = useState(() => ({ keepShown: false }));

  const [controller] = useState(() =>
    createQueryController<null, AlertSettings>({
      initialQuery: null,
      getToken,
      failure: "Network error: the reminder settings could not be loaded.",
      fetchAnswer: async (token) => {
        const response = await fetch("/api/eligibility/alert-settings", { headers: { Authorization: `Bearer ${token}` } });
        if (response.status === 401) clearSession();
        if (!response.ok) throw new Error(await readErrorDetail(response, "The reminder settings could not be loaded."));
        return (await response.json()) as AlertSettings;
      },
      show: (update) => {
        const keepShown = nextRead.keepShown;
        if (update.kind !== "loading") nextRead.keepShown = false;
        setPage((current) => settingsPageAfter(current, update, keepShown));
      },
    }),
  );

  function load(keepShown: boolean) {
    nextRead.keepShown = keepShown;
    setCanManage(canManageRules(readRoleCodes()));
    void controller.refresh();
  }

  useEffect(() => {
    load(false);
    // After a session change, the page is cleared at once and read again for the new person (ELG2-R4-002).
    const refresh = () => {
      session.changed();
      setBusy("");
      setFeedback({});
      load(false);
    };
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function edit(kind: string, next: SettingForm) {
    setPage((current) => ({ ...current, forms: { ...current.forms, [kind]: next } }));
    setFeedback((current) => ({ ...current, [kind]: null }));
  }

  async function save(setting: AlertSetting) {
    const kind = setting.reminder_kind_code;
    const form = forms[kind];
    const problem = settingFormProblem(form, (settings?.roles ?? []).map((role) => role.role_code));
    if (problem) {
      setFeedback((current) => ({ ...current, [kind]: { kind: "error", text: problem } }));
      return;
    }
    const token = getToken();
    if (!token) {
      setFeedback((current) => ({ ...current, [kind]: { kind: "error", text: SIGN_IN_FIRST } }));
      return;
    }
    setBusy(kind);
    // The whole answer is read, then applied only in the session the save was made in (alertsState.ts).
    await actInSession(
      session,
      async () =>
        readActionAnswer<AlertSettingAction>(
          await fetch(`/api/eligibility/alert-settings/${kind}`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify(settingPayload(form, setting.current.version_number)),
          }),
          "The setting was not saved.",
        ),
      {
        settled: () => setBusy(""),
        failed: () => setFeedback((current) => ({ ...current, [kind]: { kind: "error", text: "Network error: the setting was not saved." } })),
        apply: (answer) => {
          if (answer.status === 401) {
            clearSession();
            return;
          }
          if ("refusal" in answer) {
            // Saved by someone else meanwhile: read the settings again, keeping the message.
            if (answer.status === 409) load(true);
            setFeedback((current) => ({ ...current, [kind]: { kind: "error", text: answer.refusal } }));
            return;
          }
          const body = answer.body;
          setPage((current) => settingsPageSaved(current, body.setting));
          setFeedback((current) => ({
            ...current,
            [kind]: {
              kind: "success",
              text: body.unchanged ? "Nothing changed: this is the setting in use." : `Saved as version ${body.setting.current.version_number}. It applies from now.`,
            },
          }));
        },
      },
    );
  }

  return (
    <section>
      <PageHeader
        eyebrow="Equipment"
        title="Reminder settings"
        subtitle="For each kind of reminder - a certificate's, and PBL's holiday calendar for a year not yet complete, counted to 1 January of the year: on which days it is repeated, and whom it reaches, step by step. Each step adds people as the date comes nearer; a change applies from the moment it is saved. Reminders are shown on screen only, on the Alerts page, until email and SMS are connected."
      >
        {error ? <p className="text-danger">{error}</p> : null}
      </PageHeader>
      <EquipmentNav current="/equipment/alert-settings" />
      {loading && !settings ? <p className="helper-text">Loading the reminder settings...</p> : null}

      {settings?.settings.map((setting) => (
        <SettingSection
          key={setting.reminder_kind_code}
          setting={setting}
          roles={settings.roles}
          form={forms[setting.reminder_kind_code]}
          canManage={canManage}
          busy={busy === setting.reminder_kind_code}
          disabled={Boolean(busy) || loading}
          feedback={feedback[setting.reminder_kind_code]}
          onEdit={(next) => edit(setting.reminder_kind_code, next)}
          onSave={() => void save(setting)}
        />
      ))}
    </section>
  );
}

function versionText(version: AlertSettingVersion): string {
  const who = version.saved_by_display_name ? `saved by ${version.saved_by_display_name} on ${formatDateTime(version.saved_at)}` : "loaded with the package";
  return `Version ${version.version_number}, ${who}`;
}

function SettingSection(props: {
  setting: AlertSetting;
  roles: AlertRole[];
  form: SettingForm | undefined;
  canManage: boolean;
  busy: boolean;
  disabled: boolean;
  feedback: Feedback | undefined;
  onEdit: (next: SettingForm) => void;
  onSave: () => void;
}) {
  const { setting, roles, form, canManage, busy, disabled, feedback, onEdit, onSave } = props;
  const current = setting.current;
  const editing = canManage && form !== undefined;
  const changed = form !== undefined && !sameForm(form, formFromVersion(current));

  function band(index: number, next: Partial<BandRow>) {
    if (!form) return;
    onEdit({ ...form, bands: form.bands.map((row, at) => (at === index ? { ...row, ...next } : row)) });
  }
  function step(index: number, next: Partial<StepRow>) {
    if (!form) return;
    onEdit({ ...form, steps: form.steps.map((row, at) => (at === index ? { ...row, ...next } : row)) });
  }

  return (
    <SectionCard title={setting.reminder_kind_label}>
      <p className="helper-text">{versionText(current)}</p>
      <p>{reminderDaysText(editing && form ? formBands(form) : current.bands)}</p>

      {!editing ? (
        <>
          <ul>
            {current.bands.map((item) => (
              <li key={item.from_days_before}>{bandText(item)}</li>
            ))}
          </ul>
          <p className="helper-text">Who it reaches:</p>
          <ol>
            {current.steps.map((item) => (
              <li key={item.step_number}>
                {item.role_label}, {stepText(item)} - on screen
              </li>
            ))}
          </ol>
        </>
      ) : (
        <>
          <p className="helper-text">Repeated:</p>
          {form!.bands.map((row, index) => (
            <div className="page-actions actions-with-fields" key={`band-${index}`}>
              <label className="field-stack">
                From
                <input className="count-field" inputMode="numeric" maxLength={3} value={row.days} disabled={disabled} onChange={(event) => band(index, { days: event.target.value })} />
              </label>
              <label className="field-stack">
                days
                <select value={row.when} disabled={disabled} onChange={(event) => band(index, { when: event.target.value as BandRow["when"] })}>
                  <option value="before">before the date</option>
                  <option value="after">after the date (0: on the day)</option>
                </select>
              </label>
              <label className="field-stack">
                every
                <input className="count-field" inputMode="numeric" maxLength={3} value={row.every} disabled={disabled} onChange={(event) => band(index, { every: event.target.value })} />
              </label>
              <span className="helper-text">days</span>
              <button type="button" disabled={disabled || form!.bands.length <= 1} onClick={() => onEdit({ ...form!, bands: form!.bands.filter((_row, at) => at !== index) })}>
                Remove
              </button>
            </div>
          ))}
          <button type="button" disabled={disabled || form!.bands.length >= MAX_BANDS} onClick={() => onEdit({ ...form!, bands: [...form!.bands, EMPTY_BAND_ROW] })}>
            Add a band
          </button>

          <p className="helper-text">Who it reaches, step by step:</p>
          {form!.steps.map((row, index) => (
            <div className="page-actions actions-with-fields" key={`step-${index}`}>
              <label className="field-stack">
                Step {index + 1}
                <select value={row.roleCode} disabled={disabled} onChange={(event) => step(index, { roleCode: event.target.value })}>
                  {roles.map((role) => (
                    <option key={role.role_code} value={role.role_code}>
                      {role.role_label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-stack">
                from
                <select value={row.starts} disabled={disabled} onChange={(event) => step(index, { starts: event.target.value as StepStart, days: event.target.value === "FIRST_REMINDER" ? "" : row.days || "0" })}>
                  <option value="FIRST_REMINDER">the first reminder</option>
                  <option value="BEFORE">days before the date</option>
                  <option value="AFTER">days after the date</option>
                </select>
              </label>
              {row.starts !== "FIRST_REMINDER" ? (
                <label className="field-stack">
                  days
                  <input className="count-field" inputMode="numeric" maxLength={3} value={row.days} disabled={disabled} onChange={(event) => step(index, { days: event.target.value })} />
                </label>
              ) : null}
              <span className="helper-text">Screen (email and SMS: not yet available)</span>
              <button type="button" disabled={disabled || form!.steps.length <= 1} onClick={() => onEdit({ ...form!, steps: form!.steps.filter((_row, at) => at !== index) })}>
                Remove
              </button>
            </div>
          ))}
          <button
            type="button"
            disabled={disabled || form!.steps.length >= MAX_STEPS}
            onClick={() => onEdit({ ...form!, steps: [...form!.steps, { roleCode: roles[0]?.role_code ?? "", starts: "BEFORE", days: "7" }] })}
          >
            Add a step
          </button>

          <div className="page-actions">
            <button type="button" disabled={disabled || !changed} onClick={onSave}>
              {busy ? "Saving..." : "Save"}
            </button>
            <button type="button" disabled={disabled || !changed} onClick={() => onEdit(formFromVersion(current))}>
              Undo changes
            </button>
          </div>
          <FeedbackLine feedback={feedback} />
        </>
      )}

      {setting.earlier.length > 0 ? (
        <details>
          <summary>Earlier versions ({setting.earlier.length})</summary>
          <ul>
            {setting.earlier.map((version) => (
              <li key={version.setting_public_id}>
                {versionText(version)}: {reminderDaysText(version.bands)} {version.steps.map((item) => `${item.role_label} ${stepText(item)}`).join("; ")}.
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </SectionCard>
  );
}
