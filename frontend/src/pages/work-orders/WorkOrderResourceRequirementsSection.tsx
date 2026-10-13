import { useEffect, useState } from "react";

import { SectionCard, StatusBadge } from "../../components/PageLayout";
import {
  type ResourceRequirement,
  fetchAllRequirementPages,
  newRequirementHref,
  requirementDatesText,
  requirementSummary,
  statusLabel,
  warningLabel,
} from "../resource-requirements/resourceRequirementState";
import { type WorkOrderLine } from "./workOrderPageState";

// WRR-001: what each line of this Work Order needs on site, recorded by Operations. A line may have
// several requirements, or none - a line without one is not reported as missing (owner, Q1). Loaded by
// this section itself, again whenever the page loads a new generation, so a stale answer is dropped.

type Props = {
  workOrderPublicId: string;
  lines: WorkOrderLine[];
  canWrite: boolean;
  isClosed: boolean;
  token: string | null;
  loadGeneration: number;
};

type Loaded = { status: "loading" } | { status: "failed"; error: string } | { status: "loaded"; requirements: ResourceRequirement[] };

export default function WorkOrderResourceRequirementsSection({ workOrderPublicId, lines, canWrite, isClosed, token, loadGeneration }: Props) {
  const [loaded, setLoaded] = useState<Loaded>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setLoaded({ status: "loading" });
    if (!token) {
      setLoaded({ status: "failed", error: "Sign in to see the resources needed." });
      return undefined;
    }
    void (async () => {
      try {
        // Every page, so a line is never shown as having no requirement because its requirements were
        // on a page not fetched.
        const requirements = await fetchAllRequirementPages<ResourceRequirement>(async (offset, limit) => {
          const params = new URLSearchParams({
            work_order_public_id: workOrderPublicId,
            limit: String(limit),
            offset: String(offset),
          });
          const response = await fetch(`/api/resource-requirements?${params.toString()}`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (!response.ok) throw new Error(`The resources needed could not be loaded. HTTP ${response.status}.`);
          return (await response.json()) as ResourceRequirement[];
        });
        if (!cancelled) setLoaded({ status: "loaded", requirements });
      } catch (error) {
        if (cancelled) return;
        const message = error instanceof TypeError ? "Network error while loading the resources needed." : String((error as Error).message);
        setLoaded({ status: "failed", error: message });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workOrderPublicId, token, loadGeneration]);

  const returnTo = `/work-orders/${workOrderPublicId}`;

  return (
    <SectionCard title="What each line needs on site">
      <p style={{ marginTop: 0 }}>
        Operations records the machines and crew each line needs, so planning can start before the Work Order is released.
        Recording a requirement does not change the Work Order and does not reserve or assign anything.
      </p>
      {isClosed ? <p style={{ color: "#6b7280" }}>This Work Order is closed, so no requirement can be added or changed.</p> : null}
      {loaded.status === "loading" ? <p className="helper-text">Loading the resources needed...</p> : null}
      {loaded.status === "failed" ? <p style={{ color: "crimson" }}>{loaded.error}</p> : null}
      {loaded.status === "loaded" ? (
        <div style={{ display: "grid", gap: "12px" }}>
          {lines.map((line) => {
            const forLine = loaded.requirements.filter((item) => item.work_order_line_public_id === line.public_id);
            return (
              <article key={line.public_id} style={{ padding: "10px 12px", border: "1px solid #ddd", background: "#fff" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap", alignItems: "baseline" }}>
                  <strong>
                    Line {line.line_number}: {line.scope_description}
                  </strong>
                  {canWrite && !isClosed ? (
                    <a href={newRequirementHref(line.public_id, returnTo, "Back to Work Order")} style={{ color: "#1d4ed8", fontWeight: 700 }}>
                      Add a requirement
                    </a>
                  ) : null}
                </div>
                {forLine.length === 0 ? (
                  <p style={{ margin: "6px 0 0 0", color: "#6b7280" }}>No requirement recorded for this line.</p>
                ) : (
                  <ul style={{ margin: "6px 0 0 0", paddingLeft: "20px", display: "grid", gap: "6px" }}>
                    {forLine.map((requirement) => (
                      <li key={requirement.requirement_public_id}>
                        <a
                          href={`/resource-requirements/${requirement.requirement_public_id}?returnTo=${encodeURIComponent(returnTo)}&returnLabel=${encodeURIComponent("Back to Work Order")}`}
                          style={{ color: "#1d4ed8", fontWeight: 700 }}
                        >
                          {requirement.requirement_reference}
                        </a>{" "}
                        {requirementSummary(requirement)}. {requirementDatesText(requirement)}.{" "}
                        <StatusBadge code={requirement.requirement_status_code} label={statusLabel(requirement.requirement_status_code)} />
                        {requirement.priority_code === "URGENT" ? (
                          <>
                            {" "}
                            <span className="status-badge status-badge--warning">Urgent</span>
                          </>
                        ) : null}
                        {requirement.warnings.length > 0 ? (
                          <div style={{ color: "#92400e" }}>{requirement.warnings.map(warningLabel).join(". ")}.</div>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </article>
            );
          })}
        </div>
      ) : null}
    </SectionCard>
  );
}
