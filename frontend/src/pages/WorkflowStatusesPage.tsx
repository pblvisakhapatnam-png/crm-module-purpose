import { useState } from "react";

import { SHOW_DEMO_CREDENTIALS } from "../config/buildFlags";

const API_BASE = "";

const NOT_SIGNED_IN_MESSAGE = SHOW_DEMO_CREDENTIALS
  ? "Sign in first as admin1, sales1 or readonly1."
  : "You are not signed in. Sign in first.";

type WorkflowStatus = {
  public_id: string;
  module: string;
  status_code: string;
  status_name: string;
  is_active: boolean;
  sort_order: number;
};

export default function WorkflowStatusesPage() {
  const [message, setMessage] = useState("");
  const [statuses, setStatuses] = useState<WorkflowStatus[]>([]);
  const [modules, setModules] = useState<string[]>([]);

  function getToken(): string | null {
    return localStorage.getItem("pbl_auth_token");
  }

  async function loadBusinessPartyStatuses() {
    const token = getToken();
    if (!token) {
      setStatuses([]);
      setMessage(NOT_SIGNED_IN_MESSAGE);
      return;
    }

    const response = await fetch(`${API_BASE}/api/workflow/statuses?module=business_party`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      setStatuses([]);
      setMessage("Could not load workflow statuses. Sign in again and retry.");
      return;
    }

    const data = (await response.json()) as WorkflowStatus[];
    setStatuses(data);
    setMessage(`Loaded ${data.length} Account workflow statuses.`);
  }

  async function loadModules() {
    const token = getToken();
    if (!token) {
      setModules([]);
      setMessage(NOT_SIGNED_IN_MESSAGE);
      return;
    }

    const response = await fetch(`${API_BASE}/api/workflow/modules`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      setModules([]);
      setMessage("Could not load workflow modules. Sign in again and retry.");
      return;
    }

    const data = (await response.json()) as string[];
    setModules(data);
    setMessage(`Loaded ${data.length} workflow module(s).`);
  }

  return (
    <section>
      <h2>Workflow Statuses</h2>
      <p>
        The status values each kind of record can move through. Account statuses are listed under their
        internal name, <code>business_party</code>.
      </p>

      <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
        <button onClick={loadBusinessPartyStatuses} style={{ padding: "10px", cursor: "pointer" }}>
          Load Account statuses
        </button>
        <button onClick={loadModules} style={{ padding: "10px", cursor: "pointer" }}>
          Load workflow modules
        </button>
      </div>

      {message && <p style={{ marginTop: "16px" }}>{message}</p>}

      {modules.length > 0 && (
        <div style={{ marginTop: "24px", padding: "16px", border: "1px solid #ddd" }}>
          <h3>Workflow modules</h3>
          <ul>
            {modules.map((moduleName) => (
              <li key={moduleName}>{moduleName}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ marginTop: "24px", display: "grid", gap: "12px" }}>
        {statuses.map((status) => (
          <div key={status.public_id} style={{ padding: "16px", border: "1px solid #ddd" }}>
            <h3 style={{ marginTop: 0 }}>{status.status_name}</h3>
            <p><strong>Code:</strong> {status.status_code}</p>
            <p><strong>Module:</strong> {status.module}</p>
            <p><strong>Sort order:</strong> {status.sort_order}</p>
            <p><strong>Active:</strong> {status.is_active ? "Yes" : "No"}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
