/**
 * Files attached to one record (owner decision, 11 September 2026): the record's files, a Download
 * button for the ones stored in this application and, for the roles that may change the record, a
 * form to add a new file.
 *
 * Shared by the Account and Commercial Offer detail pages so files look and behave the same on
 * both. It renders content only - the page supplies the surrounding SectionCard - so a page can
 * keep its own extra actions in the same card, as the Account page does with its older "record a
 * link" form. The Documents page reuses the row helpers exported below.
 *
 * `canUpload` only decides whether the form is shown. The server decides who may attach a file to
 * a record and refuses everyone else with 403; hiding the form is a convenience, not security.
 */
import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent } from "react";

import { formatDateTime } from "./dateTimeDisplay";
import { ReferenceText } from "./PageLayout";
import { SIGN_IN_AGAIN } from "./signInMessages";

const DOCUMENTS_BASE_PATH = "/api/documents";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const STORAGE_MODE_LOCAL_UPLOAD = "local_upload";

/** The server's upload limit (documents/contract.py MAX_UPLOAD_BYTES). */
export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

/**
 * The exact content type the server requires for each accepted extension
 * (documents/contract.py ALLOWED_UPLOAD_EXTENSIONS). The server refuses a file declared with any
 * other type, and browsers do not always report these - Windows often reports a .csv as
 * application/vnd.ms-excel - so a file is sent with the type the server expects for its extension.
 */
export const UPLOAD_CONTENT_TYPES: Readonly<Record<string, string>> = {
  ".pdf": "application/pdf",
  ".doc": "application/msword",
  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".xls": "application/vnd.ms-excel",
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".txt": "text/plain",
  ".csv": "text/csv",
};

const UPLOAD_ACCEPT_ATTRIBUTE = Object.keys(UPLOAD_CONTENT_TYPES).join(",");

export const UPLOAD_LIMITS_TEXT = "PDF, Word, Excel, PNG or JPG, text or CSV, up to 25 MB";

/** The types a user may choose. QUOTATION is set only by the system, when it generates a quotation. */
export const UPLOADABLE_DOCUMENT_TYPES = [
  { value: "PAN", label: "PAN" },
  { value: "GST", label: "GST" },
  { value: "KYC", label: "KYC" },
  { value: "RFQ", label: "RFQ / enquiry" },
  { value: "COMMERCIAL", label: "Commercial" },
  { value: "OTHER", label: "Other" },
] as const;

/** A machine certificate's copy (ELG-1): the one type offered when a file is attached to a certificate. */
export const CERTIFICATE_DOCUMENT_TYPES = [{ value: "CERTIFICATE", label: "Certificate" }] as const;

/** A market rate's quote copy (Slice 4G): a broker's screenshot, email or document, the one type a rate takes. */
export const VENDOR_QUOTE_DOCUMENT_TYPES = [{ value: "VENDOR_QUOTE", label: "Vendor quote" }] as const;

const DOCUMENT_TYPE_LABELS: Readonly<Record<string, string>> = {
  ...Object.fromEntries(UPLOADABLE_DOCUMENT_TYPES.map((option) => [option.value, option.label])),
  ...Object.fromEntries(CERTIFICATE_DOCUMENT_TYPES.map((option) => [option.value, option.label])),
  ...Object.fromEntries(VENDOR_QUOTE_DOCUMENT_TYPES.map((option) => [option.value, option.label])),
  QUOTATION: "Quotation",
};

const UPLOAD_FORM_STYLE = {
  display: "grid",
  gap: "12px",
  maxWidth: "560px",
  marginTop: "16px",
  paddingTop: "14px",
  borderTop: "1px solid #e5e7eb",
} as const;

/** One row from GET /api/documents/by-record/... or GET /api/documents/recent. */
export type DocumentRow = {
  public_id: string;
  document_type: string;
  linked_record_type: string;
  linked_record_public_id: string;
  file_name: string;
  original_file_name?: string | null;
  storage_mode: string;
  storage_path_or_url?: string | null;
  uploaded_at?: string | null;
  remarks?: string | null;
};

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

function clearSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("pbl_auth_token");
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}

function getSessionToken(): string | null {
  if (typeof window === "undefined") return null;

  const token = window.localStorage.getItem("pbl_auth_token");
  if (!token) return null;

  const payload = decodeTokenPayload(token);
  const exp = typeof payload?.exp === "number" ? payload.exp : Number(payload?.exp ?? 0);

  if (!payload || !exp || exp * 1000 <= Date.now()) {
    clearSession();
    return null;
  }

  return token;
}

function titleCase(code: string): string {
  return code
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

/** The words a user reads for a document type code. */
export function documentTypeLabel(code: string | null | undefined): string {
  if (!code) return "-";
  return DOCUMENT_TYPE_LABELS[code] ?? titleCase(code);
}

/** A file's extension as the server reads it: lower case, with its dot, or "" if it has none. */
export function uploadExtension(fileName: string): string {
  // As in Python's os.path.splitext, leading dots belong to the name, so ".txt" alone has no extension.
  const name = fileName.toLowerCase().replace(/^\.+/, "");
  const dot = name.lastIndexOf(".");
  return dot === -1 ? "" : name.slice(dot);
}

export type UploadFileCheck = { ok: true; contentType: string } | { ok: false; message: string };

/** Refuses, before anything is sent, a file the server would refuse for its type or its size. */
export function checkUploadFile(file: { name: string; size: number }): UploadFileCheck {
  const contentType = UPLOAD_CONTENT_TYPES[uploadExtension(file.name)];
  if (!contentType) {
    return {
      ok: false,
      message: "This type of file cannot be added. Choose a PDF, Word, Excel, PNG, JPG, text or CSV file.",
    };
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return { ok: false, message: "This file is larger than 25 MB. Choose a smaller file." };
  }
  return { ok: true, contentType };
}

export type DocumentListResult = { ok: true; rows: DocumentRow[] } | { ok: false; message: string };

/** Loads a list of document rows from a documents API path, turning every failure into plain words. */
export async function fetchDocumentRows(path: string): Promise<DocumentListResult> {
  const token = getSessionToken();
  if (!token) return { ok: false, message: SIGN_IN_AGAIN };

  let response: Response;
  try {
    response = await fetch(path, { headers: { Authorization: `Bearer ${token}` } });
  } catch {
    return { ok: false, message: "Could not reach the server while loading files. Please try again shortly." };
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearSession();
      return { ok: false, message: SIGN_IN_AGAIN };
    }
    if (response.status === 403) return { ok: false, message: "You don't have permission to see these files." };
    return { ok: false, message: `The files could not be loaded (error ${response.status}). Please try again.` };
  }

  try {
    return { ok: true, rows: (await response.json()) as DocumentRow[] };
  } catch {
    return { ok: false, message: "The files could not be loaded. Please try again." };
  }
}

function downloadFileName(row: DocumentRow): string {
  return row.original_file_name?.trim() || row.file_name || "document";
}

/** Downloads a stored file and saves it under its original name. Returns "" or what went wrong. */
async function saveStoredFile(row: DocumentRow): Promise<string> {
  const token = getSessionToken();
  if (!token) return SIGN_IN_AGAIN;

  let response: Response;
  try {
    response = await fetch(`${DOCUMENTS_BASE_PATH}/${encodeURIComponent(row.public_id)}/content`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    return "Could not reach the server. The file was not downloaded. Please try again.";
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearSession();
      return SIGN_IN_AGAIN;
    }
    if (response.status === 403) return "You don't have permission to download this file.";
    if (response.status === 404) return "This file could not be found.";
    if (response.status === 409) return "This file is not stored in the system, so it cannot be downloaded.";
    return `The file could not be downloaded (error ${response.status}). Please try again.`;
  }

  let blob: Blob;
  try {
    blob = await response.blob();
  } catch {
    return "The file could not be downloaded. Please try again.";
  }

  const objectUrl = URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = objectUrl;
  link.download = downloadFileName(row);
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  // Released a moment later rather than at once, so no browser loses the file before saving it.
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  return "";
}

/** The Download button for a stored file, or where a file kept elsewhere can be found. */
export function DocumentFileAction({ row }: { row: DocumentRow }) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  if (row.storage_mode !== STORAGE_MODE_LOCAL_UPLOAD) {
    const reference = row.storage_path_or_url?.trim();
    return (
      <span className="helper-text">
        Stored elsewhere
        {reference ? (
          <span style={{ display: "block", overflowWrap: "anywhere" }}>
            {/^https?:\/\//i.test(reference) ? (
              <a href={reference} target="_blank" rel="noopener noreferrer">
                {reference}
              </a>
            ) : (
              reference
            )}
          </span>
        ) : null}
      </span>
    );
  }

  async function handleDownload() {
    setError("");
    setDownloading(true);
    const problem = await saveStoredFile(row);
    setDownloading(false);
    setError(problem);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => void handleDownload()}
        disabled={downloading}
        aria-label={`Download ${downloadFileName(row)}`}
      >
        {downloading ? "Downloading..." : "Download"}
      </button>
      {error ? <p className="text-danger" style={{ margin: "4px 0 0" }}>{error}</p> : null}
    </>
  );
}

type DocumentsPanelProps = {
  linkedRecordType:
    | "business_party"
    | "lead"
    | "opportunity"
    | "commercial_offer"
    | "work_order"
    | "eligibility_certificate"
    | "commercial_offer_market_rate";
  linkedRecordPublicId: string;
  /** Show the form for adding a file. A usability aid only: the server decides who may add files. */
  canUpload: boolean;
  /** Change this value to make the panel load its list again, e.g. after the page records a file another way. */
  refreshKey?: number;
  /** The types offered; with one, it is chosen already. The user's own choice of every type by default. */
  documentTypes?: ReadonlyArray<{ value: string; label: string }>;
  /** Called after a file is added, so the page can show what it changes - a certificate's copy, say. */
  onUploaded?: () => void;
  /** Called when the server refuses a file (4xx), so the page can read again what changed - a market rate's offer
   * sent meanwhile, say (Slice 4G). */
  onUploadRefused?: (message: string) => void;
};

export default function DocumentsPanel({
  linkedRecordType,
  linkedRecordPublicId,
  canUpload,
  refreshKey = 0,
  documentTypes = UPLOADABLE_DOCUMENT_TYPES,
  onUploaded,
  onUploadRefused,
}: DocumentsPanelProps) {
  const onlyType = documentTypes.length === 1 ? documentTypes[0].value : "";
  const fieldId = useId();
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState("");
  const loadSequence = useRef(0);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState(onlyType);
  const [remarks, setRemarks] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");

  async function loadDocuments() {
    const sequence = ++loadSequence.current;
    setLoading(true);
    setListError("");

    const result = await fetchDocumentRows(
      `${DOCUMENTS_BASE_PATH}/by-record/${encodeURIComponent(linkedRecordType)}/${encodeURIComponent(linkedRecordPublicId)}`,
    );

    // A newer load has started since this one - the record changed, or a refresh was asked for -
    // and its answer is the one to show.
    if (sequence !== loadSequence.current) return;

    if (result.ok) {
      setDocuments(result.rows);
    } else {
      setDocuments([]);
      setListError(result.message);
    }
    setLoading(false);
  }

  useEffect(() => {
    void loadDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [linkedRecordType, linkedRecordPublicId, refreshKey]);

  // Editing the form clears the last upload's message, so an old confirmation or error is not left
  // beside the button. Only the user's own edits call this; the reset after a successful upload uses
  // the plain setters, or it would wipe the confirmation the user needs to see.
  function clearUploadFeedback() {
    setUploadError("");
    setUploadMessage("");
  }

  function handleFileChosen(file: File | null) {
    clearUploadFeedback();
    setSelectedFile(file);
    if (!file) return;
    const check = checkUploadFile(file);
    if (!check.ok) setUploadError(check.message);
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearUploadFeedback();

    if (!selectedFile) {
      setUploadError("Choose a file first.");
      return;
    }

    const check = checkUploadFile(selectedFile);
    if (!check.ok) {
      setUploadError(check.message);
      return;
    }

    if (!documentType) {
      setUploadError("Choose the document type.");
      return;
    }

    const token = getSessionToken();
    if (!token) {
      setUploadError(SIGN_IN_AGAIN);
      return;
    }

    const uploadedName = selectedFile.name;
    const formData = new FormData();
    formData.append("linked_record_type", linkedRecordType);
    formData.append("linked_record_public_id", linkedRecordPublicId);
    formData.append("document_type", documentType);
    if (remarks.trim()) formData.append("remarks", remarks.trim());
    formData.append("file", new File([selectedFile], uploadedName, { type: check.contentType }));

    setUploading(true);

    let response: Response;
    try {
      // No Content-Type header: the browser sets multipart/form-data with its boundary itself.
      response = await fetch(`${DOCUMENTS_BASE_PATH}/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
    } catch {
      // The request may have reached the server, and the file been stored, before the connection
      // failed - so this is not a refusal. Reload the list so the user can see whether it is there.
      setUploadError(
        "The upload could not be confirmed because the connection failed. The list above has been reloaded: check whether the file is there before uploading it again.",
      );
      setUploading(false);
      void loadDocuments();
      return;
    }

    if (!response.ok) {
      const refusal = await uploadErrorMessage(response);
      setUploadError(refusal);
      setUploading(false);
      // A server error, or a gateway timing out, leaves it unknown whether the file was stored.
      if (response.status >= 500) void loadDocuments();
      else onUploadRefused?.(refusal);
      return;
    }

    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setDocumentType(onlyType);
    setRemarks("");
    setUploadMessage(`File added: ${uploadedName}.`);
    setUploading(false);
    void loadDocuments();
    onUploaded?.();
  }

  return (
    <div>
      {loading && documents.length === 0 ? <p>Loading files...</p> : null}
      {listError ? <p className="text-danger">{listError}</p> : null}
      {!loading && !listError && documents.length === 0 ? <p className="helper-text">No files yet.</p> : null}

      {documents.length > 0 ? (
        <div className="data-table-wrap" style={{ marginTop: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>File</th>
                <th>Added (India time)</th>
                <th>Remarks</th>
                <th>Download</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((row) => (
                <tr key={row.public_id}>
                  <td>{documentTypeLabel(row.document_type)}</td>
                  <td className="text-break-anywhere">
                    <strong>{row.file_name}</strong>
                    {row.original_file_name && row.original_file_name !== row.file_name ? (
                      <div className="helper-text">{row.original_file_name}</div>
                    ) : null}
                    {/* The file's own reference, as the older Account list showed, for reporting a problem with it. */}
                    <div style={{ marginTop: "4px" }}>
                      <ReferenceText>{row.public_id}</ReferenceText>
                    </div>
                  </td>
                  <td>{formatDateTime(row.uploaded_at)}</td>
                  <td className="text-pre-wrap">{row.remarks?.trim() || "-"}</td>
                  <td>
                    <DocumentFileAction row={row} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {canUpload ? (
        <form onSubmit={handleUpload} aria-labelledby={`${fieldId}-heading`} style={UPLOAD_FORM_STYLE}>
          <h5 id={`${fieldId}-heading`} style={{ margin: 0, fontSize: "15px" }}>
            Add a file
          </h5>

          <div className="field-stack">
            <label htmlFor={`${fieldId}-file`}>File</label>
            <input
              id={`${fieldId}-file`}
              ref={fileInputRef}
              type="file"
              accept={UPLOAD_ACCEPT_ATTRIBUTE}
              aria-describedby={`${fieldId}-limits`}
              onChange={(event) => handleFileChosen(event.target.files?.[0] ?? null)}
            />
            <span id={`${fieldId}-limits`} className="helper-text" style={{ fontSize: "13px" }}>
              {UPLOAD_LIMITS_TEXT}
            </span>
          </div>

          <div className="field-stack">
            <label htmlFor={`${fieldId}-type`}>Document type</label>
            <select
              id={`${fieldId}-type`}
              value={documentType}
              onChange={(event) => {
                clearUploadFeedback();
                setDocumentType(event.target.value);
              }}
            >
              <option value="">Choose a type</option>
              {documentTypes.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="field-stack">
            <label htmlFor={`${fieldId}-remarks`}>Remarks (optional)</label>
            <input
              id={`${fieldId}-remarks`}
              type="text"
              maxLength={1000}
              value={remarks}
              onChange={(event) => {
                clearUploadFeedback();
                setRemarks(event.target.value);
              }}
            />
          </div>

          <div>
            <button type="submit" disabled={uploading}>
              {uploading ? "Uploading..." : "Upload"}
            </button>
            {uploadError ? <p className="text-danger" style={{ margin: "8px 0 0" }}>{uploadError}</p> : null}
            {uploadMessage ? <p className="text-success" style={{ margin: "8px 0 0" }}>{uploadMessage}</p> : null}
          </div>
        </form>
      ) : (
        <p className="helper-text" style={{ marginTop: "12px" }}>
          Your role can view these files but cannot add new ones.
        </p>
      )}
    </div>
  );
}

async function uploadErrorMessage(response: Response): Promise<string> {
  if (response.status === 401) {
    clearSession();
    return SIGN_IN_AGAIN;
  }
  if (response.status === 403) return "You don't have permission to add files to this record.";
  if (response.status === 413) return "This file is larger than 25 MB. Choose a smaller file.";
  if (response.status === 422) {
    const fallback = "The file could not be added. Check the file and the document type.";
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string" && body.detail.trim()) return body.detail;
      if (Array.isArray(body.detail)) {
        const messages = body.detail
          .map((item) => (item as { msg?: unknown }).msg)
          .filter((msg): msg is string => typeof msg === "string" && msg.trim().length > 0);
        if (messages.length > 0) return messages.join(" ");
      }
    } catch {
      // Fall through to the plain message.
    }
    return fallback;
  }
  if (response.status >= 500) {
    return `The upload could not be confirmed (error ${response.status}). The list above has been reloaded: check whether the file is there before uploading it again.`;
  }
  return `The file could not be added (error ${response.status}). Please try again.`;
}
