/**
 * Recent files the user may open, across every record, with a download for stored files.
 *
 * Files are added on the Account and Commercial Offer pages (DocumentsPanel), not here. The server
 * returns only files linked to records the caller may read, so this page never needs its own
 * permission logic.
 */
import { useEffect, useState } from "react";

import { formatDateTime } from "../components/dateTimeDisplay";
import { DocumentFileAction, documentTypeLabel, fetchDocumentRows } from "../components/DocumentsPanel";
import type { DocumentRow } from "../components/DocumentsPanel";
import { ReferenceText } from "../components/PageLayout";

const RECENT_DOCUMENTS_PATH = "/api/documents/recent?limit=50";
const RETURN_QUERY = `returnTo=${encodeURIComponent("/documents")}&returnLabel=${encodeURIComponent("Back to Documents")}`;

// The words a user reads for the record a file belongs to, and that record's page. Some older rows
// name an Account "account" rather than "business_party". A conversation has no page of its own.
const LINKED_RECORDS: Readonly<Record<string, { label: string; basePath?: string }>> = {
  business_party: { label: "Account", basePath: "/accounts" },
  account: { label: "Account", basePath: "/accounts" },
  commercial_offer: { label: "Commercial Offer", basePath: "/commercial-offers" },
  lead: { label: "Lead", basePath: "/leads" },
  opportunity: { label: "Opportunity", basePath: "/opportunities" },
  work_order: { label: "Work Order", basePath: "/work-orders" },
  interaction: { label: "Conversation" },
};

function LinkedRecord({ row }: { row: DocumentRow }) {
  const known = LINKED_RECORDS[row.linked_record_type];
  const label = known?.label ?? "Other record";

  return (
    <>
      {known?.basePath ? (
        <a href={`${known.basePath}/${encodeURIComponent(row.linked_record_public_id)}?${RETURN_QUERY}`}>{label}</a>
      ) : (
        label
      )}
      <div>
        <ReferenceText>{row.linked_record_public_id}</ReferenceText>
      </div>
    </>
  );
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadRecentDocuments() {
      const result = await fetchDocumentRows(RECENT_DOCUMENTS_PATH);
      if (!active) return;
      if (result.ok) {
        setDocuments(result.rows);
      } else {
        setError(result.message);
      }
      setLoading(false);
    }

    void loadRecentDocuments();
    return () => {
      active = false;
    };
  }, []);

  return (
    <section>
      <h2>Documents</h2>
      <p>
        The most recent files, across every record you can open. Files are added on the Account and
        Commercial Offer pages. A file stored in the system can be downloaded, unless it belongs to a
        conversation whose messages your role may not read; a file kept elsewhere shows its link.
      </p>

      {loading ? <p>Loading files...</p> : null}
      {error ? <p className="text-danger">{error}</p> : null}
      {!loading && !error && documents.length === 0 ? <p className="helper-text">No files yet.</p> : null}

      {documents.length > 0 ? (
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>File</th>
                <th>Belongs to</th>
                <th>Added (India time)</th>
                <th>Download</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((row) => (
                <tr key={row.public_id}>
                  <td>{documentTypeLabel(row.document_type)}</td>
                  <td className="text-break-anywhere">
                    <strong>{row.file_name}</strong>
                    <div style={{ marginTop: "4px" }}>
                      <ReferenceText>{row.public_id}</ReferenceText>
                    </div>
                  </td>
                  <td>
                    <LinkedRecord row={row} />
                  </td>
                  <td>{formatDateTime(row.uploaded_at)}</td>
                  <td>
                    <DocumentFileAction row={row} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
