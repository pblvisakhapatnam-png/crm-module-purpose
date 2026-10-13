import { FormEvent, useEffect, useState } from "react";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";

const ACCOUNT_CREATE_PATH = "/api/accounts";
const ACCOUNT_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];

const STATUS_OPTIONS = [
  { value: "DRAFT", label: "Draft" },
  { value: "QUALIFIED_PROSPECT", label: "Qualified Prospect" },
];

const QUALIFICATION_SOURCE_OPTIONS = [
  { value: "manual", label: "Manual" },
  { value: "enquiry", label: "Enquiry" },
  { value: "rfq", label: "RFQ" },
  { value: "tender", label: "Tender" },
  { value: "registration", label: "Registration" },
  { value: "external_intelligence", label: "Reviewed external intelligence" },
];

type CreatedAccount = {
  public_id: string;
  account_name: string;
  legal_name?: string | null;
  account_status_code: string;
  qualification_source?: string | null;
  segment?: string | null;
  industry?: string | null;
  account_owner_user_public_id?: string | null;
  account_owner_display_name?: string | null;
  created_at: string;
};

type CreateResponse = {
  account: CreatedAccount;
  event: {
    public_id: string;
    event_name: string;
    record_type: string;
    record_public_id: string;
  };
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

type AccountCreateAccessStatus = "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token";

type AccountCreateAccess = {
  status: AccountCreateAccessStatus;
  roleCodes: string[];
};

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("pbl_auth_token");
}

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

function getAccountCreateAccess(): AccountCreateAccess {
  const token = getToken();
  if (!token) return { status: "no_token", roleCodes: [] };

  const payload = decodeTokenPayload(token);
  if (!payload) return { status: "invalid_token", roleCodes: [] };

  const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp ?? 0);
  if (exp > 0 && exp * 1000 < Date.now()) {
    return { status: "expired", roleCodes: [] };
  }

  const roleCodes = Array.isArray(payload.role_codes)
    ? payload.role_codes.filter((role): role is string => typeof role === "string")
    : [];

  const allowed = roleCodes.some((role) => ACCOUNT_CREATE_ROLES.includes(role));
  return { status: allowed ? "allowed" : "denied", roleCodes };
}

function accountCreateAccessMessage(status: AccountCreateAccessStatus): string {
  if (status === "no_token") return "Sign in first as a Sales or Admin user to create Accounts.";
  if (status === "expired") return "Sign in again to create Accounts because the current session has expired.";
  if (status === "invalid_token") return "Sign in again to create Accounts because the current session is invalid.";
  if (status === "denied") return "Your role can view Accounts but cannot create new Accounts.";
  return "";
}

function normalizeOptional(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "-";
}

function optionLabel(options: { value: string; label: string }[], value: string | null | undefined): string {
  if (!value) return "-";
  return options.find((option) => option.value === value)?.label ?? value;
}

function validationDetailToMessage(detail: ValidationErrorDetail | undefined): string {
  if (!detail) return "The Account could not be created. Check the form and try again.";

  if (typeof detail === "string") return detail;

  const messages = detail
    .map((item) => item.msg)
    .filter((value): value is string => Boolean(value));

  if (messages.length === 0) return "The Account could not be created. Check the form and try again.";

  return messages.join(" ");
}

async function createErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) {
    return SIGN_IN_AGAIN;
  }

  if (response.status === 403) {
    return "You do not have permission to create Accounts.";
  }

  if (response.status === 404) return "Account creation is not available right now. Ask an administrator to check the service.";

  if (response.status === 422) {
    try {
      const body = (await response.json()) as { detail?: ValidationErrorDetail };
      return validationDetailToMessage(body.detail);
    } catch {
      return "The Account could not be created because the form contains invalid values.";
    }
  }

  return "The Account could not be created. Please try again.";
}

export default function NewAccountPage() {
  const [accountName, setAccountName] = useState("");
  const [legalName, setLegalName] = useState("");
  const [accountStatusCode, setAccountStatusCode] = useState("DRAFT");
  const [qualificationSource, setQualificationSource] = useState("manual");
  const [segment, setSegment] = useState("");
  const [industry, setIndustry] = useState("");
  const [sourceRemarks, setSourceRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [created, setCreated] = useState<CreateResponse | null>(null);
  const [createAccess, setCreateAccess] = useState<AccountCreateAccess>({ status: "checking", roleCodes: [] });

  useEffect(() => {
    setCreateAccess(getAccountCreateAccess());
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setError("");
    setCreated(null);

    const access = getAccountCreateAccess();
    setCreateAccess(access);
    if (access.status !== "allowed") {
      setError(accountCreateAccessMessage(access.status));
      return;
    }

    if (accountName.trim().length === 0) {
      setError("Account name is required.");
      return;
    }

    const token = getToken();
    if (!token) {
      setError(SIGN_IN_FIRST);
      return;
    }

    setSubmitting(true);

    const payload = {
      party_type: "organization",
      account_name: accountName.trim(),
      legal_name: normalizeOptional(legalName),
      account_status_code: accountStatusCode,
      qualification_source: qualificationSource,
      segment: normalizeOptional(segment),
      industry: normalizeOptional(industry),
      source_remarks: normalizeOptional(sourceRemarks),
    };

    let response: Response;
    try {
      response = await fetch(ACCOUNT_CREATE_PATH, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setError("Could not reach the server, so the Account was not created. Please try again shortly.");
      setSubmitting(false);
      return;
    }

    if (!response.ok) {
      setError(await createErrorMessage(response));
      setSubmitting(false);
      return;
    }

    const data = (await response.json()) as CreateResponse;
    setCreated(data);
    setMessage("Account created successfully.");
    setAccountName("");
    setLegalName("");
    setAccountStatusCode("DRAFT");
    setQualificationSource("manual");
    setSegment("");
    setIndustry("");
    setSourceRemarks("");
    setSubmitting(false);
  }

  return (
    <section>
      <h2>Create Account</h2>
      <p>
        Create a Draft Account or a Qualified Prospect. Add PAN / GST, contacts and addresses on the
        Account page after it is created. Duplicate Accounts are not checked yet, so look in the
        Account list first.
      </p>

      <div className="page-actions">
        <a className="button-link-secondary" href="/accounts">Back to Accounts</a>
      </div>

      {createAccess.status === "checking" ? (
        <p style={{ marginTop: "24px" }}>Checking Account create access...</p>
      ) : createAccess.status !== "allowed" ? (
        <div className="content-card">
          <h3>Account creation not available</h3>
          <p style={{ color: "crimson" }}>{accountCreateAccessMessage(createAccess.status)}</p>
          <p>
            Only Admin, Sales User and Sales Manager roles can create Accounts.
          </p>
          <p>
            <a href="/login">Go to Sign in</a>
          </p>
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
          className="form-card"
        >
          <label className="field-stack">
            Account name <span style={{ color: "crimson" }}>*</span>
            <input
              value={accountName}
              onChange={(event) => setAccountName(event.target.value)}
              maxLength={255}
              required
            />
          </label>

          <label className="field-stack">
            Legal name
            <input
              value={legalName}
              onChange={(event) => setLegalName(event.target.value)}
              maxLength={255}
            />
          </label>

          <label className="field-stack">
            Account status
            <select
              value={accountStatusCode}
              onChange={(event) => setAccountStatusCode(event.target.value)}
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field-stack">
            Qualification source
            <select
              value={qualificationSource}
              onChange={(event) => setQualificationSource(event.target.value)}
            >
              {QUALIFICATION_SOURCE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field-stack">
            Segment
            <input
              value={segment}
              onChange={(event) => setSegment(event.target.value)}
              maxLength={100}
            />
          </label>

          <label className="field-stack">
            Industry
            <input
              value={industry}
              onChange={(event) => setIndustry(event.target.value)}
              maxLength={100}
            />
          </label>

          <label className="field-stack">
            Source remarks
            <textarea
              value={sourceRemarks}
              onChange={(event) => setSourceRemarks(event.target.value)}
              maxLength={4000}
              rows={4}
            />
          </label>

          <div>
            <button type="submit" disabled={submitting}>
              {submitting ? "Creating Account..." : "Create Account"}
            </button>
            {message && <p className="action-feedback" style={{ color: "green" }}>{message}</p>}
            {error && <p className="action-feedback" style={{ color: "crimson" }}>{error}</p>}
          </div>
        </form>
      )}

      {created ? (
        <div className="content-card">
          <h3>Created Account</h3>
          <p>
            <strong>Account:</strong> {created.account.account_name}
          </p>
          <p>
            <strong>Legal name:</strong> {displayValue(created.account.legal_name)}
          </p>
          <p>
            <strong>Reference:</strong> {created.account.public_id}
          </p>
          <p>
            <strong>Status:</strong> {optionLabel(STATUS_OPTIONS, created.account.account_status_code)}
          </p>
          <p>
            <strong>Qualification source:</strong> {optionLabel(QUALIFICATION_SOURCE_OPTIONS, created.account.qualification_source)}
          </p>
          <p>
            <strong>Segment / industry:</strong> {displayValue(created.account.segment)} / {displayValue(created.account.industry)}
          </p>
          <p>
            <strong>Owner:</strong> {displayValue(created.account.account_owner_display_name ?? created.account.account_owner_user_public_id)}
          </p>
          <p>
            <strong>Created:</strong> {formatDateTime(created.account.created_at)}
          </p>
          <div style={{ marginTop: "16px" }}>
            <a href="/accounts">Go to Account list</a>
          </div>
        </div>
      ) : null}
    </section>
  );
}
