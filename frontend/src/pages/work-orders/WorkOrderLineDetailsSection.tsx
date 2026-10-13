import { useEffect, useState } from "react";

import { SectionCard } from "../../components/PageLayout";
import { canEditLine, isUserToggle, lineCardOpen } from "./workOrderLineDetailState";
import { lineDatesText } from "./workOrderContractPeriodState";
import DateInput from "../../components/DateInput";

// Slice 7C: site, billing GSTIN, billing address and customer line reference for each Work Order
// line. Addresses and GSTINs are picked from the Work Order's own Account (owner decision 1): a missing
// one is added on the Account first. The billing basis and contracted hours moved to the billing terms
// section in Slice 7D. The backend re-checks every choice; hiding the form from read-only roles is a
// convenience, not the control.

export type WorkOrderLineDetail = {
  work_order_line_public_id: string;
  line_number: number;
  detail_public_id?: string | null;
  detail_version?: number | null;
  site_address_public_id?: string | null;
  site_address?: { public_id: string; address_line1: string; city: string; state: string } | null;
  billing_gstin_public_id?: string | null;
  billing_gstin?: { public_id: string; gstin: string; state_code: string; verification_state_code: string } | null;
  billing_address_public_id?: string | null;
  billing_address?: { public_id: string; address_type_code: string; address_line1: string; city: string; state: string } | null;
  customer_line_reference?: string | null;
  operational_notes?: string | null;
  // Slice 7D Part 3: the line's own dates inside the Work Order's contract period. Both blank means
  // the line follows the Work Order (owner decision 13).
  line_start_date?: string | null;
  line_end_date?: string | null;
  // 8A core: whether the site is a central-government site (ELG-1 Q8); null is not answered.
  site_central_government?: boolean | null;
  is_complete: boolean;
  missing_items: string[];
  updated_by_display_name?: string | null;
  updated_at?: string | null;
};

type AccountAddress = { public_id: string; address_type_code: string; address_line1: string; city: string; state: string };
type AccountGstin = { public_id: string; gstin: string; state_code: string; gstin_verification_state_code: string };

type LineSummary = { public_id: string; line_number: number; scope_description: string; uom: string };

type FormState = {
  site_address_public_id: string;
  billing_gstin_public_id: string;
  billing_address_public_id: string;
  customer_line_reference: string;
  operational_notes: string;
  line_start_date: string;
  line_end_date: string;
  // "YES", "NO", or "" for not answered.
  site_central_government: string;
};

type Feedback = { kind: "success" | "error"; text: string } | null;

const MISSING_ITEM_LABELS: Record<string, string> = {
  SITE_ADDRESS: "site",
  BILLING_GSTIN: "billing GSTIN",
  BILLING_ADDRESS: "billing address",
};

export function missingItemsText(detail: WorkOrderLineDetail | undefined): string {
  if (!detail) return "Not loaded";
  if (detail.is_complete) return "Details complete";
  const items = detail.missing_items.map((item) => MISSING_ITEM_LABELS[item] ?? item);
  return `Missing: ${items.join(", ")}`;
}

function addressLabel(address: { address_line1: string; city: string; state: string }): string {
  return `${address.address_line1}, ${address.city}, ${address.state}`;
}

function formFromDetail(detail: WorkOrderLineDetail | undefined): FormState {
  return {
    site_address_public_id: detail?.site_address_public_id ?? "",
    billing_gstin_public_id: detail?.billing_gstin_public_id ?? "",
    billing_address_public_id: detail?.billing_address_public_id ?? "",
    customer_line_reference: detail?.customer_line_reference ?? "",
    operational_notes: detail?.operational_notes ?? "",
    line_start_date: detail?.line_start_date ?? "",
    line_end_date: detail?.line_end_date ?? "",
    site_central_government: centralAnswerCode(detail?.site_central_government),
  };
}

/** The central-government answer as the form holds it, and back: true is YES, false is NO, null not answered. */
export function centralAnswerCode(value: boolean | null | undefined): string {
  return value === true ? "YES" : value === false ? "NO" : "";
}

export function centralAnswerValue(code: string): boolean | null {
  return code === "YES" ? true : code === "NO" ? false : null;
}

export function centralAnswerText(value: boolean | null | undefined): string {
  return value === true ? "Yes" : value === false ? "No" : "Not answered";
}

function orNull(value: string): string | null {
  return value.trim().length > 0 ? value.trim() : null;
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return "Check the values entered: one of them is not accepted.";
  } catch {
    // fall through
  }
  return `The details could not be saved. HTTP ${response.status}.`;
}

// Asks every line card to open or close; `seq` changes on each click so repeating the same request
// still takes effect.
type ExpandRequest = { open: boolean; seq: number };

type Props = {
  workOrderPublicId: string;
  accountPublicId: string | null;
  accountHref: string | null;
  lines: LineSummary[];
  details: WorkOrderLineDetail[];
  detailsLoaded: boolean;
  detailsError: string;
  canEdit: boolean;
  isClosed: boolean;
  token: string | null;
  // The page-load generation this section was rendered for. Every write hands it back, so a save that
  // finishes after a newer page load has started is discarded instead of applied over it.
  loadGeneration: number;
  // Receives the saved detail from the PUT response, so the page applies the new version at once
  // rather than waiting on a background reload (review round 1).
  onSaved: (detail: WorkOrderLineDetail, loadGeneration: number) => void;
};

export default function WorkOrderLineDetailsSection(props: Props) {
  const { accountPublicId, token } = props;
  const [addresses, setAddresses] = useState<AccountAddress[]>([]);
  const [gstins, setGstins] = useState<AccountGstin[]>([]);
  const [choicesError, setChoicesError] = useState("");
  const [expandRequest, setExpandRequest] = useState<ExpandRequest>({ open: false, seq: 0 });

  useEffect(() => {
    let cancelled = false;
    if (!accountPublicId || !token || !props.canEdit) return undefined;
    const headers = { Authorization: `Bearer ${token}` };
    void (async () => {
      try {
        const [addressResponse, taxResponse] = await Promise.all([
          fetch(`/api/accounts/${encodeURIComponent(accountPublicId)}/addresses`, { headers }),
          fetch(`/api/accounts/${encodeURIComponent(accountPublicId)}/tax-profile`, { headers }),
        ]);
        if (!addressResponse.ok || !taxResponse.ok) {
          if (!cancelled) setChoicesError("The Account's addresses and GST numbers could not be loaded.");
          return;
        }
        const loadedAddresses = (await addressResponse.json()) as AccountAddress[];
        const taxBundle = (await taxResponse.json()) as { gstins?: AccountGstin[] };
        if (!cancelled) {
          setAddresses(loadedAddresses);
          setGstins(taxBundle.gstins ?? []);
          setChoicesError("");
        }
      } catch {
        if (!cancelled) setChoicesError("Network error while loading the Account's addresses and GST numbers.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [accountPublicId, token, props.canEdit]);

  const siteAddresses = addresses.filter((address) => address.address_type_code === "SITE");
  const billingAddresses = addresses.filter((address) => ["REGISTERED_OFFICE", "BILLING_DRAFT"].includes(address.address_type_code));
  const usableGstins = gstins.filter((gstin) => gstin.gstin_verification_state_code !== "REJECTED_INCORRECT");

  return (
    <SectionCard title="Site and billing details">
      <p style={{ marginTop: 0 }}>
        For each line: where the work happens, and the GST number and address the customer is billed on. Addresses and
        GST numbers are picked from the customer's Account. If one on the customer's Work Order is not
        on the Account yet, add it there first
        {props.accountHref ? (
          <>
            {" "}
            (<a href={props.accountHref} style={{ color: "#1d4ed8", fontWeight: 700 }}>go to the Account</a>)
          </>
        ) : null}
        , then pick it here. Missing details do not block anything yet; they will block releasing the Work Order to Ops.
      </p>
      {props.isClosed ? <p style={{ color: "#6b7280" }}>This Work Order is closed, so these details can no longer be changed.</p> : null}
      {props.detailsError ? <p style={{ color: "crimson" }}>{props.detailsError}</p> : null}
      {props.canEdit && !props.detailsLoaded && !props.detailsError ? <p className="helper-text">Loading the saved details...</p> : null}
      {choicesError ? <p style={{ color: "crimson" }}>{choicesError}</p> : null}
      {props.lines.length > 1 ? (
        <p style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button type="button" onClick={() => setExpandRequest((current) => ({ open: true, seq: current.seq + 1 }))}>
            Expand all lines
          </button>
          <button type="button" onClick={() => setExpandRequest((current) => ({ open: false, seq: current.seq + 1 }))}>
            Collapse all lines
          </button>
        </p>
      ) : null}
      <div style={{ display: "grid", gap: "12px" }}>
        {props.lines.map((line) => {
          const detail = props.details.find((item) => item.work_order_line_public_id === line.public_id);
          return (
            <LineDetailCard
              key={line.public_id}
              workOrderPublicId={props.workOrderPublicId}
              line={line}
              detail={detail}
              siteAddresses={siteAddresses}
              billingAddresses={billingAddresses}
              gstins={usableGstins}
              editable={props.canEdit && !props.isClosed && canEditLine(props.detailsLoaded, detail)}
              token={token}
              loadGeneration={props.loadGeneration}
              onSaved={props.onSaved}
              expandRequest={expandRequest}
            />
          );
        })}
      </div>
    </SectionCard>
  );
}

type CardProps = {
  workOrderPublicId: string;
  line: LineSummary;
  detail: WorkOrderLineDetail | undefined;
  siteAddresses: AccountAddress[];
  billingAddresses: AccountAddress[];
  gstins: AccountGstin[];
  editable: boolean;
  token: string | null;
  loadGeneration: number;
  onSaved: (detail: WorkOrderLineDetail, loadGeneration: number) => void;
  expandRequest: ExpandRequest;
};

function LineDetailCard({
  workOrderPublicId,
  line,
  detail,
  siteAddresses,
  billingAddresses,
  gstins,
  editable,
  token,
  loadGeneration,
  onSaved,
  expandRequest,
}: CardProps) {
  const [form, setForm] = useState<FormState>(() => formFromDetail(detail));
  // null until the user opens or closes the card; see lineCardOpen for what is shown meanwhile.
  const [userOpen, setUserOpen] = useState<boolean | null>(null);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);

  // Reload the form whenever a newer version of the saved detail arrives. The inputs are disabled
  // while a save is in flight, so this cannot overwrite anything typed during the save.
  useEffect(() => {
    setForm(formFromDetail(detail));
  }, [detail?.detail_version, detail?.detail_public_id]);

  function update(field: keyof FormState, value: string) {
    setFeedback(null);
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function save() {
    if (!token) {
      setFeedback({ kind: "error", text: "Your session has ended. Sign in again, then save." });
      return;
    }
    setSaving(true);
    setFeedback(null);
    try {
      const response = await fetch(
        `/api/work-orders/${encodeURIComponent(workOrderPublicId)}/lines/${encodeURIComponent(line.public_id)}/detail`,
        {
          method: "PUT",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({
            expected_detail_version: detail?.detail_version ?? null,
            site_address_public_id: orNull(form.site_address_public_id),
            billing_gstin_public_id: orNull(form.billing_gstin_public_id),
            billing_address_public_id: orNull(form.billing_address_public_id),
            customer_line_reference: orNull(form.customer_line_reference),
            operational_notes: orNull(form.operational_notes),
            line_start_date: orNull(form.line_start_date),
            line_end_date: orNull(form.line_end_date),
            site_central_government: centralAnswerValue(form.site_central_government),
          }),
        },
      );
      if (response.status === 409) {
        setFeedback({ kind: "error", text: "These details have changed since the page loaded. Reload to see the latest version." });
        return;
      }
      if (!response.ok) {
        setFeedback({ kind: "error", text: await readErrorDetail(response) });
        return;
      }
      const body = (await response.json()) as { line_detail: WorkOrderLineDetail; event: unknown };
      onSaved(body.line_detail, loadGeneration);
      setFeedback({ kind: "success", text: body.event ? "Details saved." : "Nothing changed, so nothing was saved." });
    } catch {
      setFeedback({ kind: "error", text: "Network error while saving. Try again." });
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    if (expandRequest.seq > 0) setUserOpen(expandRequest.open);
  }, [expandRequest.seq, expandRequest.open]);

  const fieldStyle = { width: "100%", maxWidth: "520px" } as const;
  const isOpen = lineCardOpen(userOpen, detail?.is_complete);
  const summaryFacts = detail?.site_address?.city ?? "";

  return (
    <details
      open={isOpen}
      onToggle={(event) => {
        // Recording the page's own change would pin a card open that should close once its details
        // load as complete.
        const nowOpen = (event.currentTarget as HTMLDetailsElement).open;
        if (isUserToggle(nowOpen, isOpen)) setUserOpen(nowOpen);
      }}
      style={{ padding: "12px", border: "1px solid #ddd", background: "#fff" }}
    >
      <summary style={{ cursor: "pointer", listStylePosition: "outside" }}>
        <span style={{ display: "inline-flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap", width: "calc(100% - 24px)" }}>
          <span>
            <strong>
              Line {line.line_number} - {line.scope_description}
            </strong>
            {summaryFacts ? <span style={{ color: "#6b7280" }}> ({summaryFacts})</span> : null}
          </span>
          <span className="status-badge">{missingItemsText(detail)}</span>
        </span>
      </summary>
      <p style={{ margin: "8px 0", color: "#6b7280" }}>Quoted unit on the offer: {line.uom}</p>

      {editable ? (
        <fieldset disabled={saving} style={{ display: "grid", gap: "12px", maxWidth: "860px", border: 0, padding: 0, margin: 0 }}>
          <label className="field-stack">
            Site
            <select value={form.site_address_public_id} onChange={(event) => update("site_address_public_id", event.target.value)} style={fieldStyle}>
              <option value="">Not chosen</option>
              {siteAddresses.map((address) => (
                <option key={address.public_id} value={address.public_id}>{addressLabel(address)}</option>
              ))}
            </select>
          </label>
          {siteAddresses.length === 0 ? <span className="helper-text">This Account has no Site address yet. Add it on the Account first.</span> : null}
          <label className="field-stack">
            Central-government site?
            <select value={form.site_central_government} onChange={(event) => update("site_central_government", event.target.value)} style={fieldStyle}>
              <option value="">Not answered</option>
              <option value="YES">Yes</option>
              <option value="NO">No</option>
            </select>
          </label>
          <span className="helper-text">
            A central public sector plant, a railway or metro, a major port, an oil field or a mine - including work there as a
            contractor. It decides which rules the machines are checked against, so a machine cannot be allocated until it is answered.
          </span>
          <label className="field-stack">
            Billing GSTIN
            <select value={form.billing_gstin_public_id} onChange={(event) => update("billing_gstin_public_id", event.target.value)} style={fieldStyle}>
              <option value="">Not chosen</option>
              {gstins.map((gstin) => (
                <option key={gstin.public_id} value={gstin.public_id}>{gstin.gstin} (state {gstin.state_code})</option>
              ))}
            </select>
          </label>
          <label className="field-stack">
            Billing address
            <select value={form.billing_address_public_id} onChange={(event) => update("billing_address_public_id", event.target.value)} style={fieldStyle}>
              <option value="">Not chosen</option>
              {billingAddresses.map((address) => (
                <option key={address.public_id} value={address.public_id}>
                  {addressLabel(address)} ({address.address_type_code === "BILLING_DRAFT" ? "Billing" : "Registered office"})
                </option>
              ))}
            </select>
          </label>
          <label className="field-stack">
            Customer's line reference
            <input value={form.customer_line_reference} onChange={(event) => update("customer_line_reference", event.target.value)} maxLength={255} style={fieldStyle} />
          </label>
          <label className="field-stack">
            This line starts on
            <DateInput value={form.line_start_date} onChange={(event) => update("line_start_date", event.target.value)} style={fieldStyle} />
          </label>
          <label className="field-stack">
            This line ends on
            <DateInput value={form.line_end_date} onChange={(event) => update("line_end_date", event.target.value)} style={fieldStyle} />
          </label>
          <p className="helper-text" style={{ margin: 0 }}>
            Leave both empty unless this line runs to different dates from the Work Order. A line left empty follows
            the Work Order's contract dates.
          </p>
          <label className="field-stack">
            Notes
            <textarea value={form.operational_notes} onChange={(event) => update("operational_notes", event.target.value)} rows={3} maxLength={4000} style={fieldStyle} />
          </label>
          <div>
            <button type="button" onClick={() => void save()} disabled={saving} style={{ padding: "8px 12px", fontWeight: 700 }}>
              {saving ? "Saving..." : "Save details"}
            </button>
            {feedback ? (
              <p style={{ color: feedback.kind === "success" ? "#065f46" : "crimson", margin: "6px 0 0 0" }}>{feedback.text}</p>
            ) : null}
          </div>
        </fieldset>
      ) : (
        <dl style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: "6px 12px", margin: 0 }}>
          <dt style={{ color: "#6b7280", fontWeight: 700 }}>Site</dt>
          <dd style={{ margin: 0 }}>{detail?.site_address ? addressLabel(detail.site_address) : "-"}</dd>
          <dt style={{ color: "#6b7280", fontWeight: 700 }}>Billing GSTIN</dt>
          <dd style={{ margin: 0 }}>{detail?.billing_gstin ? detail.billing_gstin.gstin : "-"}</dd>
          <dt style={{ color: "#6b7280", fontWeight: 700 }}>Billing address</dt>
          <dd style={{ margin: 0 }}>{detail?.billing_address ? addressLabel(detail.billing_address) : "-"}</dd>
          <dt style={{ color: "#6b7280", fontWeight: 700 }}>Customer's line reference</dt>
          <dd style={{ margin: 0 }}>{detail?.customer_line_reference || "-"}</dd>
          <dt style={{ color: "#6b7280", fontWeight: 700 }}>This line runs</dt>
          <dd style={{ margin: 0 }}>{lineDatesText(detail)}</dd>
          <dt style={{ color: "#6b7280", fontWeight: 700 }}>Notes</dt>
          <dd style={{ margin: 0 }}>{detail?.operational_notes || "-"}</dd>
        </dl>
      )}
    </details>
  );
}
