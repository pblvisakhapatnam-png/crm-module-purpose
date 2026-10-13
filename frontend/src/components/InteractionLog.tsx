/**
 * Slice 9D - shared conversation log, embedded on the Lead, Account and Opportunity detail
 * pages (Commercial Offer and Work Order mounting is deferred to the next round, alongside the
 * Commercial Offer submission-readiness row - see docs/agent/slices/slice-9d-interaction-foundation.md).
 *
 * One component serves all linked record types so the log looks and behaves identically
 * everywhere it appears, and so a future ingestion connector's rows render through the exact
 * same UI a manually recorded conversation does.
 *
 * Content redaction is never decided here. `body_redacted` comes from the API response - the
 * backend's shared serializer is the single place that decision is made (see
 * app/modules/interactions/service.py::_serialize_interaction) - so this component only ever
 * displays what the backend already decided to send.
 */
import { FormEvent, useEffect, useState } from "react";

import { SectionCard } from "./PageLayout";
import DateInput from "./DateInput";
import { formatDateTime } from "./dateTimeDisplay";
import { enteredIndiaTimeToUtc, nowAsIndiaInput } from "./enteredDateTime";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "./signInMessages";

const INTERACTIONS_BASE_PATH = "/api/interactions";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const APP_DISPLAY_TIME_ZONE_LABEL = "IST";

// Client-side hint only, matching INTERACTION_CREATE's grant set in the authorization
// contract - never a security boundary. The backend's require_permission(INTERACTION_CREATE)
// is authoritative; a role not listed here who somehow submits the form is refused by the API,
// not silently allowed by the frontend.
const INTERACTION_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];

const CHANNEL_OPTIONS = [
  { value: "CALL", label: "Call" },
  { value: "EMAIL", label: "Email" },
  { value: "WHATSAPP", label: "WhatsApp" },
  { value: "MEETING", label: "Meeting" },
  { value: "SITE_VISIT", label: "Site Visit" },
  { value: "SMS", label: "SMS" },
  { value: "PORTAL", label: "Portal" },
  { value: "LETTER", label: "Letter" },
  { value: "NOTE", label: "Note" },
  { value: "OTHER", label: "Other" },
];

const DIRECTION_OPTIONS = [
  { value: "INBOUND", label: "Inbound (from the customer)" },
  { value: "OUTBOUND", label: "Outbound (to the customer)" },
  { value: "INTERNAL", label: "Internal" },
];

type InteractionParticipant = {
  public_id: string;
  party_role_code: string;
  display_name?: string | null;
  address_or_number?: string | null;
};

type Interaction = {
  public_id: string;
  linked_record_type: string;
  linked_record_public_id: string;
  channel_code: string;
  direction_code: string;
  occurred_at: string;
  subject?: string | null;
  body_text?: string | null;
  body_redacted: boolean;
  outcome?: string | null;
  next_follow_up_at?: string | null;
  created_at: string;
  participants: InteractionParticipant[];
  inherited_from?: { record_type: string; public_id: string; display_reference: string } | null;
};

type ValidationErrorDetail =
  | string
  | Array<{
      msg?: string;
      loc?: Array<string | number>;
    }>;

type TokenPayload = {
  role_codes?: unknown;
  exp?: unknown;
};

function decodeTokenPayload(token: string): TokenPayload | null {
  const parts = token.split(".");
  if (parts.length !== 3 || !parts[1]) return null;

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    return JSON.parse(window.atob(padded)) as TokenPayload;
  } catch {
    return null;
  }
}

function clearPrototypeSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("pbl_auth_token");
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;

  const token = window.localStorage.getItem("pbl_auth_token");
  if (!token) return null;

  const payload = decodeTokenPayload(token);
  const exp = typeof payload?.exp === "number" ? payload.exp : Number(payload?.exp ?? 0);

  if (!payload || !exp || exp * 1000 <= Date.now()) {
    clearPrototypeSession();
    return null;
  }

  return token;
}

function canCreateInteractions(): boolean {
  const token = getToken();
  if (!token) return false;

  const payload = decodeTokenPayload(token);
  const roleCodes = Array.isArray(payload?.role_codes)
    ? payload.role_codes.filter((role): role is string => typeof role === "string")
    : [];

  return roleCodes.some((role) => INTERACTION_CREATE_ROLES.includes(role));
}

function validationDetailToMessage(detail: ValidationErrorDetail | undefined): string {
  if (!detail) return "The request could not be completed. Check the form and try again.";
  if (typeof detail === "string") return detail;

  const messages = detail
    .map((item) => item.msg)
    .filter((value): value is string => Boolean(value));

  if (messages.length === 0) return "The request could not be completed. Check the form and try again.";
  return messages.join(" ");
}

async function responseErrorMessage(response: Response, fallback: string): Promise<string> {
  if (response.status === 401) return SIGN_IN_AGAIN;
  if (response.status === 403) return "You do not have permission for this action.";
  if (response.status === 404) return "Interaction not found.";
  if (response.status === 409) return "This conversation appears to already be recorded (matching external reference).";

  if (response.status === 422) {
    try {
      const body = (await response.json()) as { detail?: ValidationErrorDetail };
      return validationDetailToMessage(body.detail);
    } catch {
      return fallback;
    }
  }

  return `${fallback} HTTP ${response.status}.`;
}

type Props = {
  linkedRecordType: "lead" | "business_party" | "opportunity" | "commercial_offer" | "work_order";
  linkedRecordPublicId: string;
  /** Show a toggle for inherited history. Meaningful only for opportunity/business_party,
   * which can inherit from a source Lead - see the backend's inherited-history read model. */
  supportsInheritance?: boolean;
};

export default function InteractionLog({ linkedRecordType, linkedRecordPublicId, supportsInheritance = false }: Props) {
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [includeInherited, setIncludeInherited] = useState(supportsInheritance);

  const [showForm, setShowForm] = useState(false);
  const [channelCode, setChannelCode] = useState("CALL");
  const [directionCode, setDirectionCode] = useState("OUTBOUND");
  const [occurredAt, setOccurredAt] = useState(nowAsIndiaInput());
  const [subject, setSubject] = useState("");
  const [bodyText, setBodyText] = useState("");
  const [outcome, setOutcome] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [formMessage, setFormMessage] = useState("");

  // Editing a field clears the previous save's message, so an old confirmation or error is not
  // left beside the button. Only the user's own edits call this: the form's post-save reset uses
  // the plain setters, or it would wipe the confirmation the user needs to see.
  function clearFormFeedback() {
    setFormError("");
    setFormMessage("");
  }

  async function loadInteractions() {
    setListError("");
    const token = getToken();
    if (!token) {
      setInteractions([]);
      setListError(SIGN_IN_FIRST);
      return;
    }

    setLoading(true);
    const params = new URLSearchParams({
      linked_record_type: linkedRecordType,
      linked_record_public_id: linkedRecordPublicId,
      include_inherited: String(includeInherited),
      limit: "20",
    });

    let response: Response;
    try {
      response = await fetch(`${INTERACTIONS_BASE_PATH}?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setInteractions([]);
      setListError("Network error while loading recorded conversations.");
      setLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setInteractions([]);
      setListError(await responseErrorMessage(response, "Could not load recorded conversations."));
      setLoading(false);
      return;
    }

    const data = (await response.json()) as Interaction[];
    setInteractions(data);
    setLoading(false);
  }

  useEffect(() => {
    void loadInteractions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linkedRecordType, linkedRecordPublicId, includeInherited]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    setFormMessage("");

    const token = getToken();
    if (!token) {
      setFormError(SIGN_IN_FIRST);
      return;
    }

    const occurredIso = enteredIndiaTimeToUtc(occurredAt);
    if (!occurredIso) {
      setFormError("Enter a valid date and time for when this conversation happened.");
      return;
    }

    setSaving(true);

    let response: Response;
    try {
      response = await fetch(INTERACTIONS_BASE_PATH, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          linked_record_type: linkedRecordType,
          linked_record_public_id: linkedRecordPublicId,
          channel_code: channelCode,
          direction_code: directionCode,
          occurred_at: occurredIso,
          subject: subject.trim() || null,
          body_text: bodyText.trim() || null,
          outcome: outcome.trim() || null,
        }),
      });
    } catch {
      setFormError("Network error while recording this conversation.");
      setSaving(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setFormError(await responseErrorMessage(response, "Could not record this conversation."));
      setSaving(false);
      return;
    }

    setFormMessage("Conversation recorded.");
    setSubject("");
    setBodyText("");
    setOutcome("");
    setOccurredAt(nowAsIndiaInput());
    setSaving(false);
    void loadInteractions();
  }

  const mayCreate = canCreateInteractions();

  return (
    <SectionCard title="Conversations / Interactions">
      <p className="helper-text" style={{ marginTop: 0 }}>Times are shown in India time ({APP_DISPLAY_TIME_ZONE_LABEL}).</p>

      {supportsInheritance && (
        <label style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
          <input
            type="checkbox"
            checked={includeInherited}
            onChange={(event) => setIncludeInherited(event.target.checked)}
          />
          Show conversations recorded on the originating Lead
        </label>
      )}

      {mayCreate && (
        <div style={{ marginBottom: "12px" }}>
          <button type="button" onClick={() => setShowForm((value) => !value)}>
            {showForm ? "Cancel" : "Record a conversation"}
          </button>

          {showForm && (
            <form onSubmit={handleSubmit} style={{ marginTop: "12px", display: "grid", gap: "8px", maxWidth: "860px" }}>
              <label className="field-stack">
                Channel
                <select value={channelCode} onChange={(event) => { clearFormFeedback(); setChannelCode(event.target.value); }}>
                  {CHANNEL_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field-stack">
                Direction
                <select value={directionCode} onChange={(event) => { clearFormFeedback(); setDirectionCode(event.target.value); }}>
                  {DIRECTION_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field-stack">
                When it happened
                <DateInput
                  withTime
                  value={occurredAt}
                  onChange={(event) => { clearFormFeedback(); setOccurredAt(event.target.value); }}
                  required
                />
              </label>

              <label className="field-stack">
                Subject (optional)
                <input type="text" value={subject} onChange={(event) => { clearFormFeedback(); setSubject(event.target.value); }} />
              </label>

              <label className="field-stack">
                What was said / notes (optional)
                <textarea rows={6} value={bodyText} onChange={(event) => { clearFormFeedback(); setBodyText(event.target.value); }} />
              </label>

              <label className="field-stack">
                Outcome (optional)
                <input type="text" value={outcome} onChange={(event) => { clearFormFeedback(); setOutcome(event.target.value); }} />
              </label>

              <div>
                <button type="submit" disabled={saving}>
                  {saving ? "Saving..." : "Save conversation"}
                </button>
              </div>

              {formError && <p style={{ color: "#b91c1c" }}>{formError}</p>}
              {formMessage && <p style={{ color: "#166534" }}>{formMessage}</p>}
            </form>
          )}
        </div>
      )}

      {!mayCreate && (
        <p style={{ color: "#555" }}>Your role can view recorded conversations but cannot add new ones.</p>
      )}

      {loading && <p>Loading conversations...</p>}
      {listError && <p style={{ color: "#b91c1c" }}>{listError}</p>}

      {!loading && !listError && interactions.length === 0 && <p style={{ color: "#555" }}>No conversations recorded yet.</p>}

      {!loading && interactions.length > 0 && (
        <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: "8px" }}>
          {interactions.map((interaction) => (
            <li key={interaction.public_id} style={{ padding: "10px", border: "1px solid #eee", borderRadius: "4px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
                <strong>
                  {interaction.channel_code} - {interaction.direction_code}
                </strong>
                <span style={{ color: "#555" }}>{formatDateTime(interaction.occurred_at)}</span>
              </div>

              {interaction.inherited_from && (
                <p style={{ margin: "4px 0", fontSize: "0.85em", color: "#7c3aed" }}>
                  Recorded on the originating Lead ({interaction.inherited_from.display_reference})
                </p>
              )}

              {interaction.subject && <p style={{ margin: "4px 0" }}>{interaction.subject}</p>}

              {interaction.body_redacted ? (
                <p style={{ margin: "4px 0", fontStyle: "italic", color: "#888" }}>
                  Message content not shown for your role.
                </p>
              ) : (
                interaction.body_text && <p style={{ margin: "4px 0", whiteSpace: "pre-wrap" }}>{interaction.body_text}</p>
              )}

              {interaction.outcome && (
                <p style={{ margin: "4px 0", fontSize: "0.9em" }}>
                  <em>Outcome:</em> {interaction.outcome}
                </p>
              )}

              {interaction.next_follow_up_at && (
                <p style={{ margin: "4px 0", fontSize: "0.85em", color: "#555" }}>
                  Next follow-up: {formatDateTime(interaction.next_follow_up_at)}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
