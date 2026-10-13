import { FormEvent, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useParams } from "react-router-dom";

import DocumentsPanel from "../../components/DocumentsPanel";
import InteractionLog from "../../components/InteractionLog";
import { PageHeader, ReferenceText, SectionCard, SectionGroup, SectionIndex, StatusBadge } from "../../components/PageLayout";
import { formatDateTime } from "../../components/dateTimeDisplay";
import { readSafeReturnTarget, type ReturnTarget } from "../../components/returnTarget";
import { SIGN_IN_AGAIN, SIGN_IN_FIRST } from "../../components/signInMessages";

const ACCOUNT_DETAIL_BASE_PATH = "/api/accounts";
const VIEWED_ACCOUNT_IDS_KEY = "pbl_viewed_account_ids_this_session";
const ACCOUNT_VIEWED_EVENT = "pbl-account-viewed";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const ACCOUNT_CREATE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];
const ACCOUNT_TAX_CAPTURE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER", "FINANCE_USER"];
const ACCOUNT_TAX_VERIFICATION_ROLES = ["FINANCE_USER"];
const ACCOUNT_DOCUMENT_CAPTURE_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER", "FINANCE_USER"];
const ACCOUNT_CLASSIFICATION_MAINTAIN_ROLES = ["ADMIN", "SALES_USER", "SALES_MANAGER"];

const DOCUMENT_TYPE_OPTIONS = [
  { value: "PAN", label: "PAN" },
  { value: "GST", label: "GST" },
  { value: "KYC", label: "KYC" },
  { value: "RFQ", label: "RFQ" },
  { value: "COMMERCIAL", label: "Commercial" },
  { value: "OTHER", label: "Other" },
];

const DOCUMENT_STORAGE_MODE_OPTIONS = [
  { value: "external_link", label: "External link / reference" },
  { value: "future_sharepoint", label: "Future SharePoint reference" },
];

const DOCUMENT_STATUS_OPTIONS = [
  { value: "Linked", label: "Linked" },
  { value: "Draft", label: "Draft" },
];

const ADDRESS_TYPE_OPTIONS = [
  { value: "REGISTERED_OFFICE", label: "Registered Office" },
  { value: "COMMUNICATION", label: "Communication" },
  { value: "SITE", label: "Site" },
  { value: "BILLING_DRAFT", label: "Billing Draft" },
  { value: "OTHER", label: "Other" },
];

const TAX_VERIFICATION_STATE_OPTIONS = [
  { value: "NOT_AVAILABLE", label: "Not Available" },
  { value: "ENTERED_NOT_VERIFIED", label: "Entered - Not Verified" },
  { value: "VERIFICATION_PENDING", label: "Verification Pending" },
  { value: "VERIFIED", label: "Verified" },
  { value: "REJECTED_INCORRECT", label: "Rejected / Incorrect" },
  { value: "NOT_REQUIRED_YET", label: "Not Required Yet" },
];

const GSTIN_PATTERN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;

function normalizeTaxCode(value: string): string {
  return value.trim().toUpperCase().replace(/\s+/g, "");
}
const TAX_CAPTURE_VERIFICATION_STATE_OPTIONS = TAX_VERIFICATION_STATE_OPTIONS.filter(
  (option) => option.value !== "VERIFIED" && option.value !== "REJECTED_INCORRECT",
);

// Display labels for the qualification source codes, matching the Create Account form.
const QUALIFICATION_SOURCE_OPTIONS = [
  { value: "manual", label: "Manual" },
  { value: "enquiry", label: "Enquiry" },
  { value: "rfq", label: "RFQ" },
  { value: "tender", label: "Tender" },
  { value: "registration", label: "Registration" },
  { value: "external_intelligence", label: "Reviewed external intelligence" },
];

const DETAIL_GRID_STYLE = {
  display: "grid",
  gridTemplateColumns: "200px 1fr",
  gap: "8px 12px",
  margin: 0,
} as const;

const COMPACT_DETAIL_GRID_STYLE = {
  display: "grid",
  gridTemplateColumns: "130px 1fr",
  gap: "8px 12px",
  margin: 0,
} as const;

const SECTION_FORM_STYLE = {
  display: "grid",
  gap: "12px",
  maxWidth: "860px",
  marginTop: "20px",
  paddingTop: "16px",
  borderTop: "1px solid #e5e7eb",
} as const;

const FORM_HEADING_STYLE = { margin: 0, fontSize: "15px" } as const;

type Account = {
  public_id: string;
  party_type: string;
  account_name: string;
  legal_name?: string | null;
  pan?: string | null;
  gstin?: string | null;
  account_status_code: string;
  qualification_source?: string | null;
  account_owner_user_public_id?: string | null;
  account_owner_display_name?: string | null;
  segment?: string | null;
  industry?: string | null;
  source_remarks?: string | null;
  is_strategic_account?: boolean;
  classification_notes?: string | null;
  created_by?: string | null;
  created_by_display_name?: string | null;
  created_at: string;
  updated_at: string;
};

type AccountClassification = {
  account_public_id: string;
  account_owner_user_public_id?: string | null;
  account_owner_display_name?: string | null;
  segment?: string | null;
  industry?: string | null;
  is_strategic_account: boolean;
  classification_notes?: string | null;
  updated_at: string;
};


type AccountContact = {
  public_id: string;
  account_public_id: string;
  contact_name: string;
  designation?: string | null;
  department?: string | null;
  phone?: string | null;
  email?: string | null;
  is_primary: boolean;
  is_active: boolean;
  remarks?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

type AccountAddress = {
  public_id: string;
  account_public_id: string;
  address_type_code: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  district?: string | null;
  state: string;
  postal_code?: string | null;
  country_code: string;
  is_primary: boolean;
  is_active: boolean;
  remarks?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

type AccountTaxProfile = {
  public_id: string;
  account_public_id: string;
  pan?: string | null;
  pan_verification_state_code: string;
  pan_legal_name?: string | null;
  remarks?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

type AccountGstin = {
  public_id: string;
  account_public_id: string;
  gstin: string;
  gstin_verification_state_code: string;
  state_code: string;
  state_name?: string | null;
  legal_name?: string | null;
  trade_name?: string | null;
  is_primary: boolean;
  is_active: boolean;
  remarks?: string | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
};

type TokenPayload = {
  role_codes?: unknown;
  exp?: unknown;
};

type CreateAccessStatus = "checking" | "allowed" | "no_token" | "expired" | "denied" | "invalid_token";

type CreateAccess = {
  status: CreateAccessStatus;
  roleCodes: string[];
};

function clearPrototypeSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("pbl_auth_token");
  window.sessionStorage.removeItem(VIEWED_ACCOUNT_IDS_KEY);
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
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

function hasAnyRole(roleCodes: string[], allowedRoles: string[]): boolean {
  return roleCodes.some((role) => allowedRoles.includes(role));
}

function canSetTaxVerificationState(roleCodes: string[]): boolean {
  return hasAnyRole(roleCodes, ACCOUNT_TAX_VERIFICATION_ROLES);
}

function readRoleAccess(allowedRoles: string[]): CreateAccess {
  if (typeof window === "undefined") return { status: "checking", roleCodes: [] };

  const token = window.localStorage.getItem("pbl_auth_token");
  if (!token) return { status: "no_token", roleCodes: [] };

  const payload = decodeTokenPayload(token);
  if (!payload) return { status: "invalid_token", roleCodes: [] };

  const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp ?? 0);
  if (!exp || exp * 1000 <= Date.now()) {
    clearPrototypeSession();
    return { status: "expired", roleCodes: [] };
  }

  const roleCodes = Array.isArray(payload.role_codes)
    ? payload.role_codes.filter((role): role is string => typeof role === "string")
    : [];

  const allowed = hasAnyRole(roleCodes, allowedRoles);
  return { status: allowed ? "allowed" : "denied", roleCodes };
}

function readCreateAccess(): CreateAccess {
  return readRoleAccess(ACCOUNT_CREATE_ROLES);
}

function readTaxAccess(): CreateAccess {
  return readRoleAccess(ACCOUNT_TAX_CAPTURE_ROLES);
}

function readDocumentAccess(): CreateAccess {
  return readRoleAccess(ACCOUNT_DOCUMENT_CAPTURE_ROLES);
}

function readClassificationAccess(): CreateAccess {
  return readRoleAccess(ACCOUNT_CLASSIFICATION_MAINTAIN_ROLES);
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

function readViewedAccountIds(): string[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.sessionStorage.getItem(VIEWED_ACCOUNT_IDS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : [];
  } catch {
    return [];
  }
}

function markAccountViewed(publicId: string) {
  if (typeof window === "undefined") return;

  const viewed = new Set(readViewedAccountIds());
  viewed.add(publicId);
  window.sessionStorage.setItem(VIEWED_ACCOUNT_IDS_KEY, JSON.stringify(Array.from(viewed)));
  window.dispatchEvent(new Event(ACCOUNT_VIEWED_EVENT));
}

function displayValue(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "-";
}

function accountDetailErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to view this Account.";
  if (status === 404) return "Account not found. It may have been removed, or the link may be incorrect.";
  if (status === 422) return "The Account link is invalid. Open the Account again from the Account list.";
  return `Could not load the Account (error ${status}). Please try again shortly.`;
}

// These messages are used both when a section loads and when it saves, so the fallback wording
// does not claim which of the two failed.
function contactErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to add Account Contacts.";
  if (status === 404) return "Account not found. Open the Account again from the Account list.";
  if (status === 422) return "Check the Contact details. Contact name is required and email must be valid if provided.";
  return `Something went wrong with Contacts (error ${status}). Please try again.`;
}

function addressErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to add Account Addresses.";
  if (status === 404) return "Account not found. Open the Account again from the Account list.";
  if (status === 422) return "Check the Address details. Type, address line 1, city and state are required.";
  return `Something went wrong with Addresses (error ${status}). Please try again.`;
}

function documentErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to record Account Documents.";
  if (status === 404) return "Account not found. Open the Account again from the Account list.";
  if (status === 422) return "Check the Document details. Document type and file/reference name are required.";
  return `Something went wrong with Documents (error ${status}). Please try again.`;
}

function classificationErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to update Account ownership / classification.";
  if (status === 404) return "Account not found. Open the Account again from the Account list.";
  if (status === 422) return "Check the details. The owner must be a valid user ID, or left blank.";
  return `Something went wrong with ownership and classification (error ${status}). Please try again.`;
}

function taxProfileErrorMessage(status: number): string {
  if (status === 401) return SIGN_IN_AGAIN;
  if (status === 403) return "You do not have permission to save PAN / GST details.";
  if (status === 404) return "Account not found. Open the Account again from the Account list.";
  if (status === 422) return "Check the PAN / GST details. PAN and GSTIN must match the expected Indian formats.";
  return `Something went wrong with PAN / GST details (error ${status}). Please try again.`;
}

async function responseDetailOrFallback(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.clone().json()) as { detail?: unknown };
    const detail = body.detail;

    if (typeof detail === "string" && detail.trim().length > 0) {
      return detail;
    }

    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: unknown };
      if (typeof first.msg === "string" && first.msg.trim().length > 0) {
        return `${fallback} ${first.msg}`;
      }
    }
  } catch {
    // Use the fallback message below.
  }

  return fallback;
}

function formatStatusLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function optionLabel(options: { value: string; label: string }[], value: string | null | undefined): string {
  if (!value) return "-";
  return options.find((option) => option.value === value)?.label ?? value;
}

type OwnerFields = {
  account_owner_user_public_id?: string | null;
  account_owner_display_name?: string | null;
};

// The owner's name, falling back to the user id when no name is known. A name is shown only beside
// the id it belongs to: after a classification save the Account record's owner id is refreshed but
// its name is not, so a record with no owner id must show no owner rather than a stale name.
function ownerLabel(record: OwnerFields | null): string {
  if (!record?.account_owner_user_public_id) return "-";
  return displayValue(record.account_owner_display_name ?? record.account_owner_user_public_id);
}

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt style={{ color: "#6b7280", fontWeight: 700 }}>{label}</dt>
      <dd style={{ margin: 0, minWidth: 0, overflowWrap: "anywhere" }}>{children}</dd>
    </>
  );
}

export default function AccountDetailPage() {
  // The route table declares `/accounts/:accountId` with no splat segment, so React Router always
  // yields a single string here. The previous array form could only come from a catch-all route,
  // which this application has never served.
  const params = useParams<{ accountId: string }>();
  const accountId = params?.accountId;

  const [account, setAccount] = useState<Account | null>(null);
  const [contacts, setContacts] = useState<AccountContact[]>([]);
  const [addresses, setAddresses] = useState<AccountAddress[]>([]);
  const [taxProfile, setTaxProfile] = useState<AccountTaxProfile | null>(null);
  const [gstins, setGstins] = useState<AccountGstin[]>([]);
  // Changing this makes the Documents panel load its list again, after the older "record a link" form saves.
  const [documentsRefreshKey, setDocumentsRefreshKey] = useState(0);
  const [classification, setClassification] = useState<AccountClassification | null>(null);
  const [loading, setLoading] = useState(false);
  const [contactsLoading, setContactsLoading] = useState(false);
  const [addressesLoading, setAddressesLoading] = useState(false);
  const [taxLoading, setTaxLoading] = useState(false);
  const [classificationLoading, setClassificationLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [contactMessage, setContactMessage] = useState("");
  const [contactError, setContactError] = useState("");
  const [addressMessage, setAddressMessage] = useState("");
  const [addressError, setAddressError] = useState("");
  const [taxMessage, setTaxMessage] = useState("");
  const [taxError, setTaxError] = useState("");
  const [taxActionSource, setTaxActionSource] = useState<"" | "pan" | "gstin">("");
  const [documentMessage, setDocumentMessage] = useState("");
  const [documentError, setDocumentError] = useState("");
  const [classificationMessage, setClassificationMessage] = useState("");
  const [classificationError, setClassificationError] = useState("");
  const [createAccess, setCreateAccess] = useState<CreateAccess>({ status: "checking", roleCodes: [] });
  const [taxAccess, setTaxAccess] = useState<CreateAccess>({ status: "checking", roleCodes: [] });
  const [documentAccess, setDocumentAccess] = useState<CreateAccess>({ status: "checking", roleCodes: [] });
  const [classificationAccess, setClassificationAccess] = useState<CreateAccess>({ status: "checking", roleCodes: [] });
  const [returnTarget, setReturnTarget] = useState<ReturnTarget>({
    href: "/accounts",
    label: "Back to Accounts",
  });

  const [contactName, setContactName] = useState("");
  const [designation, setDesignation] = useState("");
  const [department, setDepartment] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [isPrimary, setIsPrimary] = useState(false);
  const [remarks, setRemarks] = useState("");

  const [addressTypeCode, setAddressTypeCode] = useState("COMMUNICATION");
  const [addressLine1, setAddressLine1] = useState("");
  const [addressLine2, setAddressLine2] = useState("");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [stateName, setStateName] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [countryCode, setCountryCode] = useState("IN");
  const [isPrimaryAddress, setIsPrimaryAddress] = useState(false);
  const [addressRemarks, setAddressRemarks] = useState("");

  const [pan, setPan] = useState("");
  const [panVerificationStateCode, setPanVerificationStateCode] = useState("NOT_AVAILABLE");
  const [panLegalName, setPanLegalName] = useState("");
  const [taxRemarks, setTaxRemarks] = useState("");

  const [gstin, setGstin] = useState("");
  const [gstinVerificationStateCode, setGstinVerificationStateCode] = useState("ENTERED_NOT_VERIFIED");
  const [gstinStateCode, setGstinStateCode] = useState("");
  const [gstinStateName, setGstinStateName] = useState("");
  const [gstinLegalName, setGstinLegalName] = useState("");
  const [gstinTradeName, setGstinTradeName] = useState("");
  const [isPrimaryGstin, setIsPrimaryGstin] = useState(false);
  const [gstinRemarks, setGstinRemarks] = useState("");

  const [documentType, setDocumentType] = useState("KYC");
  const [documentFileName, setDocumentFileName] = useState("");
  const [documentOriginalFileName, setDocumentOriginalFileName] = useState("");
  const [documentStorageMode, setDocumentStorageMode] = useState("external_link");
  const [documentStoragePathOrUrl, setDocumentStoragePathOrUrl] = useState("");
  const [documentVersionNo, setDocumentVersionNo] = useState("1");
  const [documentStatus, setDocumentStatus] = useState("Linked");
  const [documentRemarks, setDocumentRemarks] = useState("");

  const [accountOwnerUserPublicId, setAccountOwnerUserPublicId] = useState("");
  const [classificationSegment, setClassificationSegment] = useState("");
  const [classificationIndustry, setClassificationIndustry] = useState("");
  const [isStrategicAccount, setIsStrategicAccount] = useState(false);
  const [classificationNotes, setClassificationNotes] = useState("");

  const taxVerificationStateOptions = canSetTaxVerificationState(taxAccess.roleCodes)
    ? TAX_VERIFICATION_STATE_OPTIONS
    : TAX_CAPTURE_VERIFICATION_STATE_OPTIONS;

  async function loadContacts(accountPublicId: string, token: string) {
    setContactsLoading(true);
    setContactError("");

    let response: Response;
    try {
      response = await fetch(`${ACCOUNT_DETAIL_BASE_PATH}/${accountPublicId}/contacts`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setContactError("Could not reach the server while loading Contacts. Please try again shortly.");
      setContactsLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setContactError(contactErrorMessage(response.status));
      setContactsLoading(false);
      return;
    }

    const data = (await response.json()) as AccountContact[];
    setContacts(data);
    setContactsLoading(false);
  }

  async function loadAddresses(accountPublicId: string, token: string) {
    setAddressesLoading(true);
    setAddressError("");

    let response: Response;
    try {
      response = await fetch(`${ACCOUNT_DETAIL_BASE_PATH}/${accountPublicId}/addresses`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setAddressError("Could not reach the server while loading Addresses. Please try again shortly.");
      setAddressesLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setAddressError(addressErrorMessage(response.status));
      setAddressesLoading(false);
      return;
    }

    const data = (await response.json()) as AccountAddress[];
    setAddresses(data);
    setAddressesLoading(false);
  }

  async function loadTaxProfile(accountPublicId: string, token: string) {
    setTaxLoading(true);
    setTaxError("");

    let response: Response;
    try {
      response = await fetch(`${ACCOUNT_DETAIL_BASE_PATH}/${accountPublicId}/tax-profile`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setTaxError("Could not reach the server while loading PAN / GST details. Please try again shortly.");
      setTaxLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setTaxError(await responseDetailOrFallback(response, taxProfileErrorMessage(response.status)));
      setTaxLoading(false);
      return;
    }

    const data = (await response.json()) as { tax_profile: AccountTaxProfile | null; gstins: AccountGstin[] };
    setTaxProfile(data.tax_profile);
    setGstins(data.gstins);
    if (data.tax_profile) {
      setPan(data.tax_profile.pan ?? "");
      setPanVerificationStateCode(data.tax_profile.pan_verification_state_code);
      setPanLegalName(data.tax_profile.pan_legal_name ?? "");
      setTaxRemarks(data.tax_profile.remarks ?? "");
    } else {
      setPan("");
      setPanVerificationStateCode("NOT_AVAILABLE");
      setPanLegalName("");
      setTaxRemarks("");
    }
    setTaxLoading(false);
  }


  async function loadClassification(accountPublicId: string, token: string) {
    setClassificationLoading(true);
    setClassificationError("");

    let response: Response;
    try {
      response = await fetch(`${ACCOUNT_DETAIL_BASE_PATH}/${accountPublicId}/classification`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setClassificationError("Could not reach the server while loading ownership and classification. Please try again shortly.");
      setClassificationLoading(false);
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setClassificationError(await responseDetailOrFallback(response, classificationErrorMessage(response.status)));
      setClassificationLoading(false);
      return;
    }

    const data = (await response.json()) as AccountClassification;
    setClassification(data);
    setAccountOwnerUserPublicId(data.account_owner_user_public_id ?? "");
    setClassificationSegment(data.segment ?? "");
    setClassificationIndustry(data.industry ?? "");
    setIsStrategicAccount(data.is_strategic_account);
    setClassificationNotes(data.classification_notes ?? "");
    setClassificationLoading(false);
  }

  useEffect(() => {
    setReturnTarget(readSafeReturnTarget("/accounts", "Back to Accounts"));
    setCreateAccess(readCreateAccess());
    setTaxAccess(readTaxAccess());
    setDocumentAccess(readDocumentAccess());
    setClassificationAccess(readClassificationAccess());

    async function loadAccount() {
      setAccount(null);
      setContacts([]);
      setAddresses([]);
      setTaxProfile(null);
      setGstins([]);
      setClassification(null);
      setMessage("");
      setError("");
      setContactMessage("");
      setContactError("");
      setAddressMessage("");
      setAddressError("");
      setTaxMessage("");
      setTaxError("");
      setTaxActionSource("");
      setDocumentMessage("");
      setDocumentError("");
      setClassificationMessage("");
      setClassificationError("");

      if (!accountId) {
        setError("The Account link is invalid. Open the Account again from the Account list.");
        return;
      }

      const token = getToken();
      if (!token) {
        setError(SIGN_IN_FIRST);
        return;
      }

      setLoading(true);

      let response: Response;
      try {
        response = await fetch(`${ACCOUNT_DETAIL_BASE_PATH}/${accountId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        setError("Could not reach the server while loading the Account. Please try again shortly.");
        setLoading(false);
        return;
      }

      if (!response.ok) {
        if (response.status === 401) clearPrototypeSession();
        setError(accountDetailErrorMessage(response.status));
        setLoading(false);
        return;
      }

      const data = (await response.json()) as Account;
      setAccount(data);
      markAccountViewed(data.public_id);
      setMessage("Account loaded.");
      setLoading(false);
      await loadContacts(data.public_id, token);
      await loadAddresses(data.public_id, token);
      await loadTaxProfile(data.public_id, token);
      await loadClassification(data.public_id, token);
    }

    loadAccount();
  }, [accountId]);

  async function handleCreateContact(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setContactMessage("");
    setContactError("");

    if (!account) {
      setContactError("Load the Account before adding Contacts.");
      return;
    }

    if (createAccess.status !== "allowed") {
      setContactError("You do not have permission to add Account Contacts.");
      return;
    }

    if (!contactName.trim()) {
      setContactError("Contact name is required.");
      return;
    }

    const token = getToken();
    if (!token) {
      setContactError(SIGN_IN_FIRST);
      return;
    }

    const payload = {
      contact_name: contactName.trim(),
      designation: designation.trim() || null,
      department: department.trim() || null,
      phone: phone.trim() || null,
      email: email.trim() || null,
      is_primary: isPrimary,
      remarks: remarks.trim() || null,
    };

    let response: Response;
    try {
      response = await fetch(`${ACCOUNT_DETAIL_BASE_PATH}/${account.public_id}/contacts`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setContactError("Could not reach the server. The Contact was not saved. Please try again.");
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setContactError(contactErrorMessage(response.status));
      return;
    }

    const data = (await response.json()) as { contact: AccountContact };
    setContacts((current) => [data.contact, ...current]);
    setContactName("");
    setDesignation("");
    setDepartment("");
    setPhone("");
    setEmail("");
    setIsPrimary(false);
    setRemarks("");
    setContactMessage("Contact added.");
  }

  async function handleCreateAddress(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAddressMessage("");
    setAddressError("");

    if (!account) {
      setAddressError("Load the Account before adding Addresses.");
      return;
    }

    if (createAccess.status !== "allowed") {
      setAddressError("You do not have permission to add Account Addresses.");
      return;
    }

    if (!addressLine1.trim() || !city.trim() || !stateName.trim()) {
      setAddressError("Address line 1, city and state are required.");
      return;
    }

    const token = getToken();
    if (!token) {
      setAddressError(SIGN_IN_FIRST);
      return;
    }

    const payload = {
      address_type_code: addressTypeCode,
      address_line1: addressLine1.trim(),
      address_line2: addressLine2.trim() || null,
      city: city.trim(),
      district: district.trim() || null,
      state: stateName.trim(),
      postal_code: postalCode.trim() || null,
      country_code: (countryCode.trim() || "IN").toUpperCase(),
      is_primary: isPrimaryAddress,
      remarks: addressRemarks.trim() || null,
    };

    let response: Response;
    try {
      response = await fetch(`${ACCOUNT_DETAIL_BASE_PATH}/${account.public_id}/addresses`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setAddressError("Could not reach the server. The Address was not saved. Please try again.");
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setAddressError(addressErrorMessage(response.status));
      return;
    }

    const data = (await response.json()) as { address: AccountAddress };
    setAddresses((current) => [data.address, ...current]);
    setAddressTypeCode("COMMUNICATION");
    setAddressLine1("");
    setAddressLine2("");
    setCity("");
    setDistrict("");
    setStateName("");
    setPostalCode("");
    setCountryCode("IN");
    setIsPrimaryAddress(false);
    setAddressRemarks("");
    setAddressMessage("Address added.");
  }

  async function handleSaveTaxProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTaxMessage("");
    setTaxError("");
    setTaxActionSource("pan");

    if (!account) {
      setTaxError("Load the Account before saving PAN / GST details.");
      return;
    }

    if (taxAccess.status !== "allowed") {
      setTaxError("You do not have permission to save PAN / GST details.");
      return;
    }

    const token = getToken();
    if (!token) {
      setTaxError(SIGN_IN_FIRST);
      return;
    }

    const payload = {
      pan: pan.trim().toUpperCase() || null,
      pan_verification_state_code: panVerificationStateCode,
      pan_legal_name: panLegalName.trim() || null,
      remarks: taxRemarks.trim() || null,
    };

    let response: Response;
    try {
      response = await fetch(`${ACCOUNT_DETAIL_BASE_PATH}/${account.public_id}/tax-profile`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setTaxError("Could not reach the server. The PAN details were not saved. Please try again.");
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setTaxError(await responseDetailOrFallback(response, taxProfileErrorMessage(response.status)));
      return;
    }

    const data = (await response.json()) as { tax_profile: AccountTaxProfile };
    setTaxProfile(data.tax_profile);
    setPan(data.tax_profile.pan ?? "");
    setPanVerificationStateCode(data.tax_profile.pan_verification_state_code);
    setPanLegalName(data.tax_profile.pan_legal_name ?? "");
    setTaxRemarks(data.tax_profile.remarks ?? "");
    setTaxMessage("PAN profile saved.");
  }

  async function handleCreateGstin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTaxMessage("");
    setTaxError("");
    setTaxActionSource("gstin");

    if (!account) {
      setTaxError("Load the Account before adding GSTIN details.");
      return;
    }

    // The same access the GSTIN form is shown by: the tax-capture roles, Finance among them (TB-1 finding TB1-800).
    if (taxAccess.status !== "allowed") {
      setTaxError("You do not have permission to add GSTIN details.");
      return;
    }

    const normalizedGstin = normalizeTaxCode(gstin);
    setGstin(normalizedGstin);

    if (!normalizedGstin) {
      setTaxError("GSTIN is required.");
      return;
    }

    if (!GSTIN_PATTERN.test(normalizedGstin)) {
      setTaxError("GSTIN must be a valid 15-character Indian GSTIN, for example 29ABCDE1234F1Z5.");
      return;
    }

    if (gstins.some((existing) => normalizeTaxCode(existing.gstin) === normalizedGstin)) {
      setTaxError("This GSTIN is already recorded for this Account.");
      return;
    }

    const token = getToken();
    if (!token) {
      setTaxError(SIGN_IN_FIRST);
      return;
    }

    const payload = {
      gstin: normalizedGstin,
      gstin_verification_state_code: gstinVerificationStateCode,
      state_code: normalizeTaxCode(gstinStateCode) || normalizedGstin.slice(0, 2),
      state_name: gstinStateName.trim() || null,
      legal_name: gstinLegalName.trim() || null,
      trade_name: gstinTradeName.trim() || null,
      is_primary: isPrimaryGstin,
      remarks: gstinRemarks.trim() || null,
    };

    let response: Response;
    try {
      response = await fetch(`${ACCOUNT_DETAIL_BASE_PATH}/${account.public_id}/gstins`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setTaxError("Could not reach the server. The GSTIN was not saved. Please try again.");
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setTaxError(await responseDetailOrFallback(response, taxProfileErrorMessage(response.status)));
      return;
    }

    const data = (await response.json()) as { gstin: AccountGstin };
    setGstins((current) => [data.gstin, ...current]);
    setGstin("");
    setGstinVerificationStateCode("ENTERED_NOT_VERIFIED");
    setGstinStateCode("");
    setGstinStateName("");
    setGstinLegalName("");
    setGstinTradeName("");
    setIsPrimaryGstin(false);
    setGstinRemarks("");
    setTaxMessage("GSTIN added.");
  }

  async function handleCreateDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDocumentMessage("");
    setDocumentError("");

    if (!account) {
      setDocumentError("Load the Account before recording Documents.");
      return;
    }

    if (documentAccess.status !== "allowed") {
      setDocumentError("You do not have permission to record Account Documents.");
      return;
    }

    if (!documentFileName.trim()) {
      setDocumentError("Document file/reference name is required.");
      return;
    }

    const parsedVersionNo = Number(documentVersionNo);
    if (!Number.isInteger(parsedVersionNo) || parsedVersionNo < 1) {
      setDocumentError("Version number must be a positive whole number.");
      return;
    }

    const token = getToken();
    if (!token) {
      setDocumentError(SIGN_IN_FIRST);
      return;
    }

    const payload = {
      document_type: documentType,
      file_name: documentFileName.trim(),
      original_file_name: documentOriginalFileName.trim() || null,
      storage_mode: documentStorageMode,
      storage_path_or_url: documentStoragePathOrUrl.trim() || null,
      version_no: parsedVersionNo,
      status: documentStatus,
      remarks: documentRemarks.trim() || null,
    };

    let response: Response;
    try {
      response = await fetch(`${ACCOUNT_DETAIL_BASE_PATH}/${account.public_id}/documents`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setDocumentError("Could not reach the server. The document was not recorded. Please try again.");
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setDocumentError(await responseDetailOrFallback(response, documentErrorMessage(response.status)));
      return;
    }

    setDocumentsRefreshKey((key) => key + 1);
    setDocumentType("KYC");
    setDocumentFileName("");
    setDocumentOriginalFileName("");
    setDocumentStorageMode("external_link");
    setDocumentStoragePathOrUrl("");
    setDocumentVersionNo("1");
    setDocumentStatus("Linked");
    setDocumentRemarks("");
    setDocumentMessage("Document recorded.");
  }

  async function handleSaveClassification(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClassificationMessage("");
    setClassificationError("");

    if (!account) {
      setClassificationError("Load the Account before saving Classification details.");
      return;
    }

    if (classificationAccess.status !== "allowed") {
      setClassificationError("You do not have permission to update Account ownership / classification.");
      return;
    }

    const token = getToken();
    if (!token) {
      setClassificationError(SIGN_IN_FIRST);
      return;
    }

    const payload = {
      account_owner_user_public_id: accountOwnerUserPublicId.trim() || null,
      segment: classificationSegment.trim() || null,
      industry: classificationIndustry.trim() || null,
      is_strategic_account: isStrategicAccount,
      classification_notes: classificationNotes.trim() || null,
    };

    let response: Response;
    try {
      response = await fetch(`${ACCOUNT_DETAIL_BASE_PATH}/${account.public_id}/classification`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
    } catch {
      setClassificationError("Could not reach the server. The ownership and classification were not saved. Please try again.");
      return;
    }

    if (!response.ok) {
      if (response.status === 401) clearPrototypeSession();
      setClassificationError(await responseDetailOrFallback(response, classificationErrorMessage(response.status)));
      return;
    }

    const data = (await response.json()) as { classification: AccountClassification };
    setClassification(data.classification);
    setAccountOwnerUserPublicId(data.classification.account_owner_user_public_id ?? "");
    setClassificationSegment(data.classification.segment ?? "");
    setClassificationIndustry(data.classification.industry ?? "");
    setIsStrategicAccount(data.classification.is_strategic_account);
    setClassificationNotes(data.classification.classification_notes ?? "");
    setAccount((current) => current ? {
      ...current,
      account_owner_user_public_id: data.classification.account_owner_user_public_id ?? null,
      segment: data.classification.segment ?? null,
      industry: data.classification.industry ?? null,
      is_strategic_account: data.classification.is_strategic_account,
      classification_notes: data.classification.classification_notes ?? null,
      updated_at: data.classification.updated_at,
    } : current);
    setClassificationMessage("Ownership and classification saved.");
  }

  const accessChecked = createAccess.status !== "checking";
  const canChangeAnything = [createAccess, taxAccess, documentAccess, classificationAccess].some(
    (access) => access.status === "allowed",
  );
  // Once loaded, the classification response is authoritative for the owner: both its GET and its
  // save response carry the owner id and name together. The Account record is used only until it
  // loads. Testing the classification's owner id instead would fall back to the Account record
  // after the owner is cleared, whose name the save does not refresh (independent review, round 1).
  const ownerRecord: OwnerFields | null = classification ?? account;

  return (
    <section>
      <PageHeader
        eyebrow="Account"
        title={account ? account.account_name : "Account"}
        badges={
          account ? (
            <StatusBadge code={account.account_status_code} label={formatStatusLabel(account.account_status_code)} />
          ) : null
        }
        back={{ href: returnTarget.href, label: returnTarget.label }}
        actions={
          account && createAccess.status === "allowed" ? (
            <a className="button-link-secondary" href="/accounts/new">
              Create another Account
            </a>
          ) : null
        }
      >
        {account && accessChecked && !canChangeAnything ? (
          <p className="helper-text">You can view this Account. Your role cannot change it.</p>
        ) : null}
        {loading ? <p>Loading Account...</p> : null}
        {message && !loading ? <p className="text-success">{message}</p> : null}
        {error ? <p className="text-danger">{error}</p> : null}
      </PageHeader>

      {account ? (
        <div style={{ maxWidth: "1120px" }}>
          <SectionIndex
            items={[
              { id: "account-profile", label: "Profile" },
              { id: "account-people", label: "People and places" },
              { id: "account-tax", label: "Tax identity" },
              { id: "account-documents", label: "Documents and conversations" },
              { id: "account-record", label: "Record details" },
            ]}
          />

          <SectionGroup
            id="account-profile"
            title="Profile"
            tone="blue"
            description="Who this Account is, who looks after it and how it is classified."
          >
            <SectionCard title="Profile summary">
              <dl style={DETAIL_GRID_STYLE}>
                <DetailRow label="Account name">{account.account_name}</DetailRow>
                <DetailRow label="Legal name">{displayValue(account.legal_name)}</DetailRow>
                <DetailRow label="Status">
                  <StatusBadge code={account.account_status_code} label={formatStatusLabel(account.account_status_code)} />
                </DetailRow>
                <DetailRow label="Party type">{formatStatusLabel(account.party_type)}</DetailRow>
                <DetailRow label="Qualification source">
                  {optionLabel(QUALIFICATION_SOURCE_OPTIONS, account.qualification_source)}
                </DetailRow>
                <DetailRow label="PAN">{displayValue(account.pan)}</DetailRow>
                <DetailRow label="GSTIN">{displayValue(account.gstin)}</DetailRow>
                <DetailRow label="Source remarks">
                  <span style={{ whiteSpace: "pre-wrap" }}>{displayValue(account.source_remarks)}</span>
                </DetailRow>
              </dl>
            </SectionCard>

            <SectionCard title="Ownership and classification">
              <p className="helper-text">
                Who looks after this Account and how it is classified. Sales keeps these details up to date.
              </p>
              {classificationLoading ? <p>Loading ownership and classification...</p> : null}

              <dl style={DETAIL_GRID_STYLE}>
                <DetailRow label="Owner">{ownerLabel(ownerRecord)}</DetailRow>
                <DetailRow label="Segment">{displayValue(classification?.segment ?? account.segment)}</DetailRow>
                <DetailRow label="Industry">{displayValue(classification?.industry ?? account.industry)}</DetailRow>
                <DetailRow label="Strategic account">
                  {(classification?.is_strategic_account ?? account.is_strategic_account) ? "Yes" : "No"}
                </DetailRow>
                <DetailRow label="Classification notes">
                  <span style={{ whiteSpace: "pre-wrap" }}>
                    {displayValue(classification?.classification_notes ?? account.classification_notes)}
                  </span>
                </DetailRow>
              </dl>

              {classificationAccess.status === "allowed" ? (
                <form onSubmit={handleSaveClassification} style={SECTION_FORM_STYLE}>
                  <h5 style={FORM_HEADING_STYLE}>Update ownership and classification</h5>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Owner's user ID
                    <input value={accountOwnerUserPublicId} onChange={(event) => setAccountOwnerUserPublicId(event.target.value)} style={{ padding: "8px" }} />
                    <span className="helper-text" style={{ fontSize: "13px" }}>
                      {classification?.account_owner_user_public_id ? (
                        <>
                          Currently:{" "}
                          <strong>
                            {classification.account_owner_display_name ?? "a user who no longer exists"}
                          </strong>
                          .{" "}
                        </>
                      ) : null}
                      This is the internal ID of the sales person who owns the Account, not a name.
                      Leave blank for no owner. Choosing the owner from a list of users is not available yet.
                    </span>
                  </label>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Segment
                      <input value={classificationSegment} onChange={(event) => setClassificationSegment(event.target.value)} style={{ padding: "8px" }} />
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Industry
                      <input value={classificationIndustry} onChange={(event) => setClassificationIndustry(event.target.value)} style={{ padding: "8px" }} />
                    </label>
                  </div>

                  <label style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <input type="checkbox" checked={isStrategicAccount} onChange={(event) => setIsStrategicAccount(event.target.checked)} />
                    Strategic account
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Classification notes
                    <textarea value={classificationNotes} onChange={(event) => setClassificationNotes(event.target.value)} rows={3} style={{ padding: "8px" }} />
                  </label>

                  <button type="submit" style={{ padding: "10px", cursor: "pointer", maxWidth: "220px" }}>
                    Save Classification
                  </button>
                </form>
              ) : (
                <p className="helper-text" style={{ marginTop: "16px" }}>
                  Your role can view ownership and classification, but cannot change them.
                </p>
              )}
              {classificationMessage ? <p className="action-feedback text-success">{classificationMessage}</p> : null}
              {classificationError ? <p className="action-feedback text-danger">{classificationError}</p> : null}
            </SectionCard>
          </SectionGroup>

          <SectionGroup
            id="account-people"
            title="People and places"
            tone="teal"
            description="The people you deal with at this Account, and its addresses."
          >
            <SectionCard title="Contacts">
              <p className="helper-text">You can add contacts here. Editing or removing a contact is not available yet.</p>
              {contactsLoading ? <p>Loading Contacts...</p> : null}

              {contacts.length === 0 && !contactsLoading ? <p>No Contacts recorded for this Account yet.</p> : null}

              {contacts.length > 0 ? (
                <div className="data-table-wrap" style={{ marginTop: "12px" }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Contact</th>
                        <th>Designation / Department</th>
                        <th>Phone</th>
                        <th>Email</th>
                        <th>Primary</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {contacts.map((contact) => (
                        <tr key={contact.public_id}>
                          <td>
                            <strong>{contact.contact_name}</strong>
                            <div style={{ marginTop: "4px" }}>
                              <ReferenceText>{contact.public_id}</ReferenceText>
                            </div>
                          </td>
                          <td>
                            {displayValue(contact.designation)} / {displayValue(contact.department)}
                          </td>
                          <td>{displayValue(contact.phone)}</td>
                          <td>{displayValue(contact.email)}</td>
                          <td>{contact.is_primary ? "Yes" : "No"}</td>
                          <td>{formatDateTime(contact.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}

              {createAccess.status === "allowed" ? (
                <form onSubmit={handleCreateContact} style={SECTION_FORM_STYLE}>
                  <h5 style={FORM_HEADING_STYLE}>Add Contact</h5>
                  <label style={{ display: "grid", gap: "4px" }}>
                    Contact name *
                    <input value={contactName} onChange={(event) => setContactName(event.target.value)} style={{ padding: "8px" }} />
                  </label>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Designation
                      <input value={designation} onChange={(event) => setDesignation(event.target.value)} style={{ padding: "8px" }} />
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Department
                      <input value={department} onChange={(event) => setDepartment(event.target.value)} style={{ padding: "8px" }} />
                    </label>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Phone
                      <input value={phone} onChange={(event) => setPhone(event.target.value)} style={{ padding: "8px" }} />
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Email
                      <input value={email} onChange={(event) => setEmail(event.target.value)} style={{ padding: "8px" }} />
                    </label>
                  </div>

                  <label style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <input type="checkbox" checked={isPrimary} onChange={(event) => setIsPrimary(event.target.checked)} />
                    Primary contact
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Remarks
                    <textarea value={remarks} onChange={(event) => setRemarks(event.target.value)} rows={3} style={{ padding: "8px" }} />
                  </label>

                  <button type="submit" style={{ padding: "10px", cursor: "pointer", maxWidth: "180px" }}>
                    Add Contact
                  </button>
                </form>
              ) : (
                <p className="helper-text" style={{ marginTop: "16px" }}>
                  Your role can view Contacts, but cannot add them.
                </p>
              )}
              {contactMessage ? <p className="action-feedback text-success">{contactMessage}</p> : null}
              {contactError ? <p className="action-feedback text-danger">{contactError}</p> : null}
            </SectionCard>

            <SectionCard title="Addresses">
              <p className="helper-text">
                You can add addresses here. Editing or removing an address is not available yet. A Billing Draft address
                is not a Finance-approved billing address.
              </p>
              {addressesLoading ? <p>Loading Addresses...</p> : null}

              {addresses.length === 0 && !addressesLoading ? <p>No Addresses recorded for this Account yet.</p> : null}

              {addresses.length > 0 ? (
                <div className="data-table-wrap" style={{ marginTop: "12px" }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Address</th>
                        <th>City / State</th>
                        <th>Primary</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {addresses.map((address) => (
                        <tr key={address.public_id}>
                          <td>{optionLabel(ADDRESS_TYPE_OPTIONS, address.address_type_code)}</td>
                          <td>
                            <strong>{address.address_line1}</strong>
                            {address.address_line2 ? <div>{address.address_line2}</div> : null}
                            <div style={{ marginTop: "4px" }}>
                              <ReferenceText>{address.public_id}</ReferenceText>
                            </div>
                          </td>
                          <td>
                            {address.city}, {address.state}
                            <div>{displayValue(address.postal_code)} / {address.country_code}</div>
                          </td>
                          <td>{address.is_primary ? "Yes" : "No"}</td>
                          <td>{formatDateTime(address.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}

              {createAccess.status === "allowed" ? (
                <form onSubmit={handleCreateAddress} style={SECTION_FORM_STYLE}>
                  <h5 style={FORM_HEADING_STYLE}>Add Address</h5>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Address type *
                    <select value={addressTypeCode} onChange={(event) => setAddressTypeCode(event.target.value)} style={{ padding: "8px" }}>
                      {ADDRESS_TYPE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Address line 1 *
                    <input value={addressLine1} onChange={(event) => setAddressLine1(event.target.value)} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Address line 2
                    <input value={addressLine2} onChange={(event) => setAddressLine2(event.target.value)} style={{ padding: "8px" }} />
                  </label>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      City *
                      <input value={city} onChange={(event) => setCity(event.target.value)} style={{ padding: "8px" }} />
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      District
                      <input value={district} onChange={(event) => setDistrict(event.target.value)} style={{ padding: "8px" }} />
                    </label>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 120px", gap: "12px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      State *
                      <input value={stateName} onChange={(event) => setStateName(event.target.value)} style={{ padding: "8px" }} />
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Postal code
                      <input value={postalCode} onChange={(event) => setPostalCode(event.target.value)} style={{ padding: "8px" }} />
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Country
                      <input value={countryCode} onChange={(event) => setCountryCode(event.target.value.toUpperCase())} style={{ padding: "8px" }} />
                    </label>
                  </div>

                  <label style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <input type="checkbox" checked={isPrimaryAddress} onChange={(event) => setIsPrimaryAddress(event.target.checked)} />
                    Primary address
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Remarks
                    <textarea value={addressRemarks} onChange={(event) => setAddressRemarks(event.target.value)} rows={3} style={{ padding: "8px" }} />
                  </label>

                  <button type="submit" style={{ padding: "10px", cursor: "pointer", maxWidth: "180px" }}>
                    Add Address
                  </button>
                </form>
              ) : (
                <p className="helper-text" style={{ marginTop: "16px" }}>
                  Your role can view Addresses, but cannot add them.
                </p>
              )}
              {addressMessage ? <p className="action-feedback text-success">{addressMessage}</p> : null}
              {addressError ? <p className="action-feedback text-danger">{addressError}</p> : null}
            </SectionCard>
          </SectionGroup>

          <SectionGroup
            id="account-tax"
            title="Tax identity"
            tone="amber"
            description="PAN and GSTIN details. These are for sales use and are not Finance-approved Customer Master data."
          >
            <SectionCard title="PAN">
              {taxLoading ? <p>Loading PAN / GST details...</p> : null}
              {taxActionSource === "" && taxMessage ? <p className="text-success">{taxMessage}</p> : null}
              {taxActionSource === "" && taxError ? <p className="text-danger">{taxError}</p> : null}

              {taxProfile ? (
                <dl style={DETAIL_GRID_STYLE}>
                  <DetailRow label="PAN">{displayValue(taxProfile.pan)}</DetailRow>
                  <DetailRow label="Verification">
                    {optionLabel(TAX_VERIFICATION_STATE_OPTIONS, taxProfile.pan_verification_state_code)}
                  </DetailRow>
                  <DetailRow label="Legal name as per PAN">{displayValue(taxProfile.pan_legal_name)}</DetailRow>
                  <DetailRow label="Last updated">{formatDateTime(taxProfile.updated_at)}</DetailRow>
                </dl>
              ) : (
                <p>No PAN recorded for this Account yet.</p>
              )}

              {taxAccess.status === "allowed" ? (
                <form onSubmit={handleSaveTaxProfile} style={SECTION_FORM_STYLE}>
                  <h5 style={FORM_HEADING_STYLE}>Update PAN details</h5>
                  <p className="helper-text" style={{ margin: 0 }}>
                    Sales and Admin users can record details as not verified or pending. Only Finance can mark them
                    Verified or Rejected.
                  </p>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      PAN
                      <input value={pan} onChange={(event) => { setPan(event.target.value.toUpperCase()); setTaxActionSource("pan"); setTaxError(""); setTaxMessage(""); }} style={{ padding: "8px" }} />
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      PAN verification state
                      <select value={panVerificationStateCode} onChange={(event) => { setPanVerificationStateCode(event.target.value); setTaxActionSource("pan"); setTaxError(""); setTaxMessage(""); }} style={{ padding: "8px" }}>
                        {taxVerificationStateOptions.map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <label style={{ display: "grid", gap: "4px" }}>
                    PAN legal name
                    <input value={panLegalName} onChange={(event) => { setPanLegalName(event.target.value); setTaxActionSource("pan"); setTaxError(""); setTaxMessage(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Remarks
                    <textarea value={taxRemarks} onChange={(event) => { setTaxRemarks(event.target.value); setTaxActionSource("pan"); setTaxError(""); setTaxMessage(""); }} rows={3} style={{ padding: "8px" }} />
                  </label>

                  <button type="submit" style={{ padding: "10px", cursor: "pointer", maxWidth: "200px" }}>
                    Save PAN Profile
                  </button>
                  {taxActionSource === "pan" && taxMessage ? <p className="text-success" style={{ margin: 0 }}>{taxMessage}</p> : null}
                  {taxActionSource === "pan" && taxError ? <p className="text-danger" style={{ margin: 0 }}>{taxError}</p> : null}
                </form>
              ) : (
                <p className="helper-text" style={{ marginTop: "16px" }}>
                  Your role can view PAN details, but cannot change them.
                </p>
              )}
            </SectionCard>

            <SectionCard title="GSTINs">
              {gstins.length === 0 ? <p>No GSTINs recorded for this Account yet.</p> : null}
              {gstins.length > 0 ? (
                <div className="data-table-wrap" style={{ marginTop: "12px" }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>GSTIN</th>
                        <th>State</th>
                        <th>Verification</th>
                        <th>Primary</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gstins.map((gstinRow) => (
                        <tr key={gstinRow.public_id}>
                          <td>
                            <strong>{gstinRow.gstin}</strong>
                            <div style={{ marginTop: "4px" }}>
                              <ReferenceText>{gstinRow.public_id}</ReferenceText>
                            </div>
                          </td>
                          <td>
                            {gstinRow.state_code} / {displayValue(gstinRow.state_name)}
                          </td>
                          <td>
                            {optionLabel(TAX_VERIFICATION_STATE_OPTIONS, gstinRow.gstin_verification_state_code)}
                          </td>
                          <td>{gstinRow.is_primary ? "Yes" : "No"}</td>
                          <td>{formatDateTime(gstinRow.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}

              {taxAccess.status === "allowed" ? (
                <form onSubmit={handleCreateGstin} style={SECTION_FORM_STYLE}>
                  <h5 style={FORM_HEADING_STYLE}>Add GSTIN</h5>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      GSTIN *
                      <input value={gstin} maxLength={15} onChange={(event) => { setGstin(normalizeTaxCode(event.target.value)); setTaxActionSource("gstin"); setTaxError(""); setTaxMessage(""); }} style={{ padding: "8px" }} />
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      GSTIN verification state
                      <select value={gstinVerificationStateCode} onChange={(event) => { setGstinVerificationStateCode(event.target.value); setTaxActionSource("gstin"); setTaxError(""); setTaxMessage(""); }} style={{ padding: "8px" }}>
                        {taxVerificationStateOptions.map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: "12px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      State code
                      <input value={gstinStateCode} onChange={(event) => { setGstinStateCode(event.target.value); setTaxActionSource("gstin"); setTaxError(""); setTaxMessage(""); }} style={{ padding: "8px" }} />
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      State name
                      <input value={gstinStateName} onChange={(event) => { setGstinStateName(event.target.value); setTaxActionSource("gstin"); setTaxError(""); setTaxMessage(""); }} style={{ padding: "8px" }} />
                    </label>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Legal name
                      <input value={gstinLegalName} onChange={(event) => { setGstinLegalName(event.target.value); setTaxActionSource("gstin"); setTaxError(""); setTaxMessage(""); }} style={{ padding: "8px" }} />
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Trade name
                      <input value={gstinTradeName} onChange={(event) => { setGstinTradeName(event.target.value); setTaxActionSource("gstin"); setTaxError(""); setTaxMessage(""); }} style={{ padding: "8px" }} />
                    </label>
                  </div>

                  <label style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <input type="checkbox" checked={isPrimaryGstin} onChange={(event) => { setIsPrimaryGstin(event.target.checked); setTaxActionSource("gstin"); setTaxError(""); setTaxMessage(""); }} />
                    Primary GSTIN
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Remarks
                    <textarea value={gstinRemarks} onChange={(event) => { setGstinRemarks(event.target.value); setTaxActionSource("gstin"); setTaxError(""); setTaxMessage(""); }} rows={3} style={{ padding: "8px" }} />
                  </label>

                  <button type="submit" style={{ padding: "10px", cursor: "pointer", maxWidth: "180px" }}>
                    Add GSTIN
                  </button>
                  {taxActionSource === "gstin" && taxMessage ? <p className="text-success" style={{ margin: 0 }}>{taxMessage}</p> : null}
                  {taxActionSource === "gstin" && taxError ? <p className="text-danger" style={{ margin: 0 }}>{taxError}</p> : null}
                </form>
              ) : (
                <p className="helper-text" style={{ marginTop: "16px" }}>
                  Your role can view GSTINs, but cannot add them.
                </p>
              )}
            </SectionCard>
          </SectionGroup>

          <SectionGroup
            id="account-documents"
            title="Documents and conversations"
            tone="violet"
            description="Files for this Account, and the record of conversations with them."
          >
            <SectionCard title="Documents">
              <DocumentsPanel
                linkedRecordType="business_party"
                linkedRecordPublicId={account.public_id}
                canUpload={documentAccess.status === "allowed"}
                refreshKey={documentsRefreshKey}
              />

              {documentAccess.status === "allowed" ? (
                <details className="secondary-disclosure">
                  <summary>Record a link to a file stored elsewhere</summary>
                  <form
                    onSubmit={handleCreateDocument}
                    style={{ ...SECTION_FORM_STYLE, marginTop: "12px", paddingTop: 0, borderTop: "none" }}
                  >
                  <p className="helper-text" style={{ margin: 0 }}>
                    For a file kept somewhere else, such as a shared drive. Only its name and link are saved here, not the
                    file itself.
                  </p>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Document type *
                      <select value={documentType} onChange={(event) => { setDocumentType(event.target.value); setDocumentError(""); setDocumentMessage(""); }} style={{ padding: "8px" }}>
                        {DOCUMENT_TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Status
                      <select value={documentStatus} onChange={(event) => { setDocumentStatus(event.target.value); setDocumentError(""); setDocumentMessage(""); }} style={{ padding: "8px" }}>
                        {DOCUMENT_STATUS_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <label style={{ display: "grid", gap: "4px" }}>
                    File / reference name *
                    <input value={documentFileName} onChange={(event) => { setDocumentFileName(event.target.value); setDocumentError(""); setDocumentMessage(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Original file name
                    <input value={documentOriginalFileName} onChange={(event) => { setDocumentOriginalFileName(event.target.value); setDocumentError(""); setDocumentMessage(""); }} style={{ padding: "8px" }} />
                  </label>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 120px", gap: "12px" }}>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Storage mode
                      <select value={documentStorageMode} onChange={(event) => { setDocumentStorageMode(event.target.value); setDocumentError(""); setDocumentMessage(""); }} style={{ padding: "8px" }}>
                        {DOCUMENT_STORAGE_MODE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </label>
                    <label style={{ display: "grid", gap: "4px" }}>
                      Version
                      <input value={documentVersionNo} onChange={(event) => { setDocumentVersionNo(event.target.value); setDocumentError(""); setDocumentMessage(""); }} style={{ padding: "8px" }} />
                    </label>
                  </div>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Storage path / URL / reference
                    <input value={documentStoragePathOrUrl} onChange={(event) => { setDocumentStoragePathOrUrl(event.target.value); setDocumentError(""); setDocumentMessage(""); }} style={{ padding: "8px" }} />
                  </label>

                  <label style={{ display: "grid", gap: "4px" }}>
                    Remarks
                    <textarea value={documentRemarks} onChange={(event) => { setDocumentRemarks(event.target.value); setDocumentError(""); setDocumentMessage(""); }} rows={3} style={{ padding: "8px" }} />
                  </label>

                  <button type="submit" style={{ padding: "10px", cursor: "pointer", maxWidth: "240px" }}>
                    Record link
                  </button>
                  {documentMessage ? <p className="text-success" style={{ margin: 0 }}>{documentMessage}</p> : null}
                  {documentError ? <p className="text-danger" style={{ margin: 0 }}>{documentError}</p> : null}
                  </form>
                </details>
              ) : null}
            </SectionCard>

            <InteractionLog
              linkedRecordType="business_party"
              linkedRecordPublicId={account.public_id}
              supportsInheritance
            />
          </SectionGroup>

          <SectionGroup
            id="account-record"
            title="Record details"
            tone="slate"
            description="The reference and dates for this record, and what is not in this version yet."
          >
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
              <SectionCard title="Reference and dates">
                <dl style={COMPACT_DETAIL_GRID_STYLE}>
                  <DetailRow label="Reference">
                    <ReferenceText>{account.public_id}</ReferenceText>
                  </DetailRow>
                  <DetailRow label="Created by">{displayValue(account.created_by_display_name ?? account.created_by)}</DetailRow>
                  <DetailRow label="Created">{formatDateTime(account.created_at)}</DetailRow>
                  <DetailRow label="Last updated">{formatDateTime(account.updated_at)}</DetailRow>
                </dl>
              </SectionCard>

              <SectionCard title="Not in this version yet">
                <ul style={{ margin: 0, paddingLeft: "20px" }}>
                  <li>Editing the Account's name, legal name or status</li>
                  <li>Editing or removing contacts and addresses</li>
                  <li>Choosing the owner from a list of users, sales territories, and approval of owner changes</li>
                  <li>Approving or verifying documents</li>
                  <li>Automatic checking of PAN and GSTIN</li>
                  <li>Viewing this Account's change history from this page</li>
                </ul>
              </SectionCard>
            </div>
          </SectionGroup>
        </div>
      ) : null}
    </section>
  );
}
