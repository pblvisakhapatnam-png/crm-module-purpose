import { useEffect, useMemo, useState } from "react";

import { readSafeReturnTarget, type ReturnTarget } from "../components/returnTarget";

const RECENT_EVENTS_PATH = "/api/events/recent?limit=25";

const BUTTON_STYLE = {
  display: "inline-block",
  padding: "10px 12px",
  border: "1px solid #1d4ed8",
  background: "#ffffff",
  color: "#1d4ed8",
  fontWeight: 700,
  textDecoration: "none",
  cursor: "pointer",
} as const;

type BusinessEvent = {
  public_id: string;
  event_name: string;
  source_module: string;
  record_type: string | null;
  record_public_id: string | null;
  user_public_id: string | null;
  event_timestamp: string;
  reason: string | null;
  remarks: string | null;
  event_payload: Record<string, unknown> | null;
};

// No default page: without a safe returnTo the page offers the browser's own Back instead.
function getSafeReturnTargetFromQuery(): ReturnTarget | null {
  const target = readSafeReturnTarget("", "Back");
  return target.href ? target : null;
}

function displayValue(value: string | null): string {
  return value && value.trim().length > 0 ? value : "-";
}

export default function EventsPage() {
  const [message, setMessage] = useState("");
  const [events, setEvents] = useState<BusinessEvent[]>([]);
  const [returnTarget, setReturnTarget] = useState<ReturnTarget | null>(null);

  useEffect(() => {
    setReturnTarget(getSafeReturnTargetFromQuery());
  }, []);

  const returnAction = useMemo(() => {
    if (returnTarget) {
      return (
        <a href={returnTarget.href} style={BUTTON_STYLE}>
          {returnTarget.label}
        </a>
      );
    }

    return (
      <button type="button" onClick={() => window.history.back()} style={BUTTON_STYLE}>
        Back to previous page
      </button>
    );
  }, [returnTarget]);

  async function loadRecentEvents() {
    const token = localStorage.getItem("pbl_auth_token");
    if (!token) {
      setEvents([]);
      setMessage("Sign in first, with a role that may view events.");
      return;
    }

    const response = await fetch(RECENT_EVENTS_PATH, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      setEvents([]);
      setMessage("Could not load events. Your role may not have permission to view business events.");
      return;
    }

    const data = (await response.json()) as BusinessEvent[];
    setEvents(data);
    setMessage(`Loaded ${data.length} recent business events.`);
  }

  return (
    <section>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "16px", flexWrap: "wrap" }}>
        <div>
          <h2 style={{ marginTop: 0 }}>Business Events</h2>
          <p>
            The audit trail: important actions recorded by the system, newest first.
          </p>
        </div>
        <div>{returnAction}</div>
      </div>

      <button onClick={loadRecentEvents} style={{ padding: "10px", cursor: "pointer" }}>
        Load recent events
      </button>

      {message && <p style={{ marginTop: "16px" }}>{message}</p>}

      <div style={{ marginTop: "24px", display: "grid", gap: "12px" }}>
        {events.map((event) => (
          <div key={event.public_id} style={{ padding: "16px", border: "1px solid #ddd" }}>
            <h3 style={{ marginTop: 0 }}>{event.event_name}</h3>
            <p><strong>Module:</strong> {event.source_module}</p>
            <p><strong>Record type:</strong> {displayValue(event.record_type)}</p>
            <p><strong>Record public id:</strong> {displayValue(event.record_public_id)}</p>
            <p><strong>User public id:</strong> {displayValue(event.user_public_id)}</p>
            <p><strong>Time:</strong> {event.event_timestamp}</p>
            {event.reason && <p><strong>Reason:</strong> {event.reason}</p>}
            {event.remarks && <p><strong>Remarks:</strong> {event.remarks}</p>}
            {event.event_payload && (
              <pre style={{ whiteSpace: "pre-wrap", background: "#f5f5f5", padding: "8px" }}>
                {JSON.stringify(event.event_payload, null, 2)}
              </pre>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
