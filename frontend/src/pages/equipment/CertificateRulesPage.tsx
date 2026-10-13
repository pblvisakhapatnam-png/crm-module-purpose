import { useEffect, useState } from "react";

import { PageHeader, SectionCard, StatusBadge } from "../../components/PageLayout";
import { SESSION_CHANGED_EVENT, clearSession, getToken, readErrorDetail, readRoleCodes } from "../resource-requirements/pageSession";
import { EquipmentNav, FeedbackLine } from "./EquipmentParts";
import {
  EMPTY_RULE_FORM,
  RULE_STATE_LABELS,
  type CertificateKind,
  type EligibilityRule,
  type Jurisdiction,
  type RuleForm,
  canManageRules,
  createQueryController,
  formatDay,
  initialQueryView,
  queryView,
  fitRuleToKind,
  ruleFormProblem,
  ruleJurisdictionChoices,
  rulePayload,
  ruleText,
} from "./certificatesState";
import { type Feedback, type Structure, findClass, newRequestKey } from "./equipmentState";
import DateInput from "../../components/DateInput";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

// Certificate rules (ELG-1, Q7): which certificates each kind of machine needs, where and how often, as dated
// data per jurisdiction - the law, or PBL's own rule where the law is silent. Nothing is edited or deleted: a rule
// is ended on a date and another added, so every past answer can still be explained. Admin adds and ends them.

const BASELINE = "BASELINE";

export default function CertificateRulesPage() {
  const [view, setView] = useState(initialQueryView<EligibilityRule[]>());
  const rules = view.answer ?? [];
  const error = view.error;
  const [jurisdictionFilter, setJurisdictionFilter] = useState("");
  const [showEnded, setShowEnded] = useState(false);
  const [kinds, setKinds] = useState<CertificateKind[]>([]);
  const [jurisdictions, setJurisdictions] = useState<Jurisdiction[]>([]);
  const [structure, setStructure] = useState<Structure | null>(null);
  const [canManage, setCanManage] = useState(false);
  const [adding, setAdding] = useState(false);
  const [ending, setEnding] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Record<string, Feedback>>({});
  // The list's loading: its query is the place the control shows - after a session change or a save too - and an
  // answer is shown only for the latest request (certificatesState.ts, createQueryController).
  const [controller] = useState(() =>
    createQueryController<string, EligibilityRule[]>({
      initialQuery: "",
      getToken,
      failure: "Network error: the rules could not be loaded.",
      fetchAnswer: async (token, jurisdiction) => {
        const query = jurisdiction ? `?jurisdiction_code=${encodeURIComponent(jurisdiction)}` : "";
        const response = await fetch(`/api/eligibility/rules${query}`, { headers: { Authorization: `Bearer ${token}` } });
        if (response.status === 401) clearSession();
        if (!response.ok) throw new Error(await readErrorDetail(response, "The rules could not be loaded."));
        return (await response.json()) as EligibilityRule[];
      },
      show: (update) => setView((current) => queryView(current, update)),
    }),
  );

  /** Who may add and end rules follows the session: a change closes the forms of one who may no longer. */
  function readRights() {
    const allowed = canManageRules(readRoleCodes());
    setCanManage(allowed);
    if (!allowed) {
      setAdding(false);
      setEnding(null);
    }
  }

  useEffect(() => {
    readRights();
    void controller.refresh();
    const token = getToken();
    if (token) {
      void (async () => {
        try {
          const headers = { Authorization: `Bearer ${token}` };
          const [kindsResponse, jurisdictionsResponse, structureResponse] = await Promise.all([
            fetch("/api/eligibility/certificate-kinds", { headers }),
            fetch("/api/eligibility/jurisdictions", { headers }),
            fetch("/api/equipment-reference/structure", { headers }),
          ]);
          if (kindsResponse.ok) setKinds((await kindsResponse.json()) as CertificateKind[]);
          if (jurisdictionsResponse.ok) setJurisdictions((await jurisdictionsResponse.json()) as Jurisdiction[]);
          if (structureResponse.ok) setStructure((await structureResponse.json()) as Structure);
        } catch {
          // Labels and choices only.
        }
      })();
    }
    const refresh = () => {
      readRights();
      void controller.refresh();
    };
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function post(key: string, path: string, body: Record<string, unknown>, success: string): Promise<boolean> {
    const token = getToken();
    if (!token) {
      setFeedback({ [key]: { kind: "error", text: SIGN_IN_FIRST } });
      return false;
    }
    try {
      const response = await fetch(path, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (response.status === 401) clearSession();
      if (!response.ok) {
        setFeedback({ [key]: { kind: "error", text: await readErrorDetail(response, "Nothing was saved.") } });
        return false;
      }
      const result = (await response.json()) as { replayed: boolean };
      setFeedback({ [key]: { kind: "success", text: result.replayed ? "Already saved: nothing more was recorded." : success } });
      void controller.refresh();
      return true;
    } catch {
      setFeedback({ [key]: { kind: "error", text: "Network error: the change may not have been saved. Reload to see." } });
      return false;
    }
  }

  const shown = rules.filter((rule) => showEnded || rule.state_code !== "ENDED");

  return (
    <section>
      <PageHeader
        eyebrow="Equipment"
        title="Certificate rules"
        subtitle="Which certificates each kind of machine needs, where and how often. A site's state's rule is used before the rule for all of India; at a central government site, its own rules for the examinations. A rule is never changed: it is ended and a new one added."
      >
        {error ? <p className="text-danger">{error}</p> : null}
      </PageHeader>
      <EquipmentNav current="/equipment/certificate-rules" />

      <div className="page-actions actions-with-fields">
        <label className="field-stack">
          Where
          <select
            value={jurisdictionFilter}
            onChange={(event) => {
              setJurisdictionFilter(event.target.value);
              void controller.setQuery(event.target.value);
            }}
          >
            <option value="">Everywhere</option>
            <option value={BASELINE}>All of India (the baseline)</option>
            {jurisdictions.map((item) => (
              <option key={item.jurisdiction_code} value={item.jurisdiction_code}>
                {item.jurisdiction_label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <input type="checkbox" checked={showEnded} onChange={(event) => setShowEnded(event.target.checked)} /> Show ended rules
        </label>
        {canManage && !adding ? (
          <button type="button" onClick={() => setAdding(true)}>
            Add a rule
          </button>
        ) : null}
      </div>
      <FeedbackLine feedback={adding ? undefined : feedback.add} />

      {canManage && adding ? (
        <SectionCard title="Add a rule">
          <AddRuleForm
            kinds={kinds}
            jurisdictions={jurisdictions}
            structure={structure}
            onCancel={() => setAdding(false)}
            onSave={async (body) => {
              if (await post("add", "/api/eligibility/rules", body, "Rule added.")) setAdding(false);
            }}
          />
          <FeedbackLine feedback={feedback.add} />
        </SectionCard>
      ) : null}

      <div className="data-table-wrap">
        <table className="data-table data-table-wide">
          <thead>
            <tr>
              <th>Where</th>
              <th>Certificate</th>
              <th>Required of</th>
              <th>The rule</th>
              <th className="col-long-text">Source</th>
              <th className="col-state-actions">In effect</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((rule) => (
              <tr key={rule.rule_public_id}>
                <td>{rule.jurisdiction_label ?? "All of India"}</td>
                <td>{rule.kind_label}</td>
                <td>
                  {rule.type_label ? `${rule.type_label} ${rule.class_label.toLowerCase()}` : `Every ${rule.class_label.toLowerCase()}`}
                  {rule.applies_when_code === "TRANSPORT_ONLY" ? <div className="helper-text">when registered as a transport vehicle</div> : null}
                </td>
                <td>
                  {ruleText(rule)}
                  {rule.note ? <div className="helper-text">{rule.note}</div> : null}
                </td>
                <td className="text-break-anywhere">{rule.source}</td>
                <td>
                  <StatusBadge code={rule.state_code} tone={rule.state_code === "IN_EFFECT" ? "success" : "muted"} label={RULE_STATE_LABELS[rule.state_code] ?? rule.state_code} />
                  <div className="helper-text">
                    from {formatDay(rule.effective_from)}
                    {rule.effective_to ? ` to ${formatDay(rule.effective_to)}` : ""}
                    {rule.end_reason ? `; ended: ${rule.end_reason}` : ""}
                  </div>
                  {canManage && !rule.effective_to ? (
                    ending === rule.rule_public_id ? (
                      <EndRuleForm
                        onCancel={() => setEnding(null)}
                        onEnd={async (body) => {
                          if (await post(`end-${rule.rule_public_id}`, `/api/eligibility/rules/${rule.rule_public_id}/end`, body, "Rule ended.")) setEnding(null);
                        }}
                      />
                    ) : (
                      <button type="button" onClick={() => setEnding(rule.rule_public_id)}>
                        End this rule
                      </button>
                    )
                  ) : null}
                  <FeedbackLine feedback={feedback[`end-${rule.rule_public_id}`]} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {shown.length === 0 && !error ? <div className="empty-state">No rule here.</div> : null}
    </section>
  );
}

function EndRuleForm({ onEnd, onCancel }: { onEnd: (body: Record<string, unknown>) => void; onCancel: () => void }) {
  const [lastDay, setLastDay] = useState("");
  const [reason, setReason] = useState("");
  return (
    <div className="form-grid section-form">
      <label className="field-stack">
        Last day in effect
        <DateInput value={lastDay} onChange={(event) => setLastDay(event.target.value)} />
      </label>
      <label className="field-stack">
        Why
        <input value={reason} onChange={(event) => setReason(event.target.value)} maxLength={1000} />
      </label>
      <div className="form-actions">
        <button type="button" disabled={!lastDay || !reason.trim()} onClick={() => onEnd({ effective_to: lastDay, reason: reason.trim() })}>
          End rule
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function AddRuleForm({
  kinds,
  jurisdictions,
  structure,
  onSave,
  onCancel,
}: {
  kinds: CertificateKind[];
  jurisdictions: Jurisdiction[];
  structure: Structure | null;
  onSave: (body: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<RuleForm>(EMPTY_RULE_FORM);
  const [requestKey] = useState(newRequestKey);
  const kind = kinds.find((item) => item.kind_code === form.kindCode);
  const equipmentClass = findClass(structure, form.classCode || null);
  const problem = ruleFormProblem(form, kind);
  const edit = (next: Partial<RuleForm>) => setForm({ ...form, ...next });
  return (
    <div className="form-grid">
      <label className="field-stack">
        Certificate
        <select
          value={form.kindCode}
          onChange={(event) => edit(fitRuleToKind({ ...form, kindCode: event.target.value }, kinds.find((item) => item.kind_code === event.target.value)))}
        >
          <option value="">Choose a certificate</option>
          {kinds.map((item) => (
            <option key={item.kind_code} value={item.kind_code}>
              {item.kind_label}
            </option>
          ))}
        </select>
      </label>
      <label className="field-stack">
        Required of
        <select value={form.classCode} onChange={(event) => edit({ classCode: event.target.value, typeCode: "" })}>
          <option value="">Choose a kind of machine, part or kit</option>
          {(structure?.classes ?? [])
            .filter((item) => item.is_active)
            .map((item) => (
              <option key={item.class_code} value={item.class_code}>
                {item.class_label}
              </option>
            ))}
        </select>
      </label>
      <label className="field-stack">
        Type
        <select value={form.typeCode} onChange={(event) => edit({ typeCode: event.target.value })}>
          <option value="">Every type</option>
          {(equipmentClass?.types ?? [])
            .filter((item) => item.is_active)
            .map((item) => (
              <option key={item.type_code} value={item.type_code}>
                {item.type_label}
              </option>
            ))}
        </select>
      </label>
      <label className="field-stack">
        Where
        <select value={form.jurisdictionCode} onChange={(event) => edit({ jurisdictionCode: event.target.value })}>
          <option value="">All of India (the baseline)</option>
          {ruleJurisdictionChoices(jurisdictions, kind).map((item) => (
            <option key={item.jurisdiction_code} value={item.jurisdiction_code}>
              {item.jurisdiction_label}
            </option>
          ))}
        </select>
      </label>
      <label className="field-stack">
        Applies
        <select value={form.appliesWhen} onChange={(event) => edit({ appliesWhen: event.target.value })}>
          <option value="ALWAYS">Always</option>
          {kind?.states_registration ? null : <option value="TRANSPORT_ONLY">Only when registered as a transport vehicle</option>}
        </select>
      </label>
      <label className="field-stack">
        In effect from
        <DateInput value={form.effectiveFrom} onChange={(event) => edit({ effectiveFrom: event.target.value })} />
      </label>
      {kind?.is_examination ? (
        <label className="field-stack">
          Renew every (months)
          <input value={form.renewEvery} onChange={(event) => edit({ renewEvery: event.target.value })} inputMode="numeric" maxLength={3} />
        </label>
      ) : null}
      <label className="field-stack">
        Basis
        <select value={form.basis} onChange={(event) => edit({ basis: event.target.value })}>
          <option value="STATUTORY">The law</option>
          <option value="PBL_RULE">PBL's own rule</option>
        </select>
      </label>
      <label className="field-stack">
        A lapse
        <select value={form.lapse} onChange={(event) => edit({ lapse: event.target.value })}>
          <option value="BLOCK">Stops the machine</option>
          <option value="NOT_REQUIRED">Not required here</option>
          <option value="OVERRIDE">Needs approval (PBL's rule only)</option>
          <option value="WARN">Warns only (PBL's rule only)</option>
        </select>
      </label>
      <label className="field-stack">
        "Not applicable"
        <select value={form.notApplicable} onChange={(event) => edit({ notApplicable: event.target.value, maxMonths: event.target.value === "ALLOWED" ? form.maxMonths : "" })}>
          <option value="NOT_ALLOWED">Never: the law is clear</option>
          <option value="ALLOWED">May be claimed: the law is unclear</option>
        </select>
      </label>
      {form.notApplicable === "ALLOWED" ? (
        <label className="field-stack">
          For at most (months, optional)
          <input value={form.maxMonths} onChange={(event) => edit({ maxMonths: event.target.value })} inputMode="numeric" maxLength={3} />
        </label>
      ) : null}
      <label className="field-stack">
        Source: the Act, rule, form and notification, or PBL's decision and its date
        <input value={form.source} onChange={(event) => edit({ source: event.target.value })} maxLength={1000} />
      </label>
      <label className="field-stack">
        Note (optional)
        <input value={form.note} onChange={(event) => edit({ note: event.target.value })} maxLength={1000} />
      </label>
      <div className="form-actions">
        <button type="button" disabled={Boolean(problem)} onClick={() => onSave(rulePayload(form, requestKey))}>
          Add rule
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
        {form.kindCode && problem ? <p className="helper-text">{problem}</p> : null}
      </div>
    </div>
  );
}
