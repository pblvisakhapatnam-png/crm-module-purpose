import { useEffect, useRef, useState, type ReactNode } from "react";

import { SectionCard, type SectionTone } from "../../components/PageLayout";
import { createQueryController, initialQueryView, queryView, type QueryView } from "../equipment/certificatesState";
import { getToken, SESSION_CHANGED_EVENT } from "../resource-requirements/pageSession";
import { fetchAssignments } from "./allocationRequests";
import type { Assignment } from "./allocationState";
import AllocationsTable from "./AllocationsTable";

// The allocations of one record - a Work Order, a requirement or a machine - as a section of that record's page.
// Every allocation is kept, so this is the record's allocation history (FRS 2.6.1). Loading is a query controller
// keyed to the record: an answer for another record is never shown here.

export default function AllocationsSection({
  id,
  title,
  tone = "teal",
  filter,
  recordPublicId,
  hide,
  returnTo,
  empty,
  children,
  render,
}: {
  id?: string;
  title: string;
  tone?: SectionTone;
  filter: "work_order_public_id" | "requirement_public_id" | "machine_public_id";
  recordPublicId: string;
  hide?: ("work-order" | "requirement" | "machine")[];
  returnTo?: { href: string; label: string };
  empty: string;
  children?: ReactNode;
  // A page that shows its allocations its own way (the requirement's units) renders them itself.
  render?: (assignments: Assignment[]) => ReactNode;
}) {
  const [view, setView] = useState<QueryView<Assignment[]>>(initialQueryView<Assignment[]>());
  const controller = useRef(
    createQueryController<string, Assignment[]>({
      initialQuery: recordPublicId,
      getToken,
      fetchAnswer: (token, publicId) => fetchAssignments(token, new URLSearchParams({ [filter]: publicId })),
      show: (update) => setView((current) => queryView(current, update)),
      failure: "The allocations could not be loaded.",
    }),
  );

  useEffect(() => {
    if (recordPublicId) void controller.current.setQuery(recordPublicId);
  }, [recordPublicId]);

  useEffect(() => {
    const reload = () => void controller.current.refresh();
    window.addEventListener(SESSION_CHANGED_EVENT, reload);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, reload);
  }, []);

  const assignments = view.answer ?? [];
  return (
    <SectionCard id={id} title={title} tone={tone}>
      {view.error ? <p className="text-danger">{view.error}</p> : null}
      {view.loading ? <p className="helper-text">Loading the allocations...</p> : null}
      {view.answer && render ? render(assignments) : null}
      {view.answer && !render && assignments.length === 0 ? <p className="helper-text">{empty}</p> : null}
      {view.answer && !render && assignments.length > 0 ? <AllocationsTable assignments={assignments} hide={hide} returnTo={returnTo} /> : null}
      {children}
    </SectionCard>
  );
}
