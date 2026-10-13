import { StatusBadge } from "../../components/PageLayout";
import { hrefWithReturnTarget } from "../resource-requirements/pageSession";
import {
  type Assignment,
  assetLabel,
  assignmentDaysText,
  billingCycleLabel,
  complianceLabel,
  complianceTone,
  statusLabel,
  statusTone,
} from "./allocationState";

// The allocations of a Work Order, a requirement or a machine, one row each - held ones and the history of replaced
// and freed ones. Every list of allocations shows the same columns, so it is one component (DRY).

type Column = "work-order" | "requirement" | "machine";

export default function AllocationsTable({
  assignments,
  hide = [],
  returnTo,
}: {
  assignments: Assignment[];
  hide?: Column[];
  returnTo?: { href: string; label: string };
}) {
  const link = (assignment: Assignment) => {
    const href = `/resource-assignments/${assignment.assignment_public_id}`;
    return returnTo ? hrefWithReturnTarget(href, returnTo.href, returnTo.label) : href;
  };
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Allocation</th>
            {hide.includes("work-order") ? null : <th>Work Order</th>}
            {hide.includes("requirement") ? null : <th>Requirement, unit</th>}
            {hide.includes("machine") ? null : <th>Machine</th>}
            <th>Days</th>
            <th>Status</th>
            <th>Today</th>
            <th>Billing cycle</th>
          </tr>
        </thead>
        <tbody>
          {assignments.map((assignment) => (
            <tr key={assignment.assignment_public_id}>
              <td>
                <a href={link(assignment)}>{assignment.assignment_reference}</a>
              </td>
              {hide.includes("work-order") ? null : (
                <td>
                  {assignment.work_order_code}, line {assignment.work_order_line_number}
                </td>
              )}
              {hide.includes("requirement") ? null : (
                <td>
                  {assignment.requirement.requirement_reference}, unit {assignment.unit_number}
                </td>
              )}
              {hide.includes("machine") ? null : <td>{assetLabel(assignment.machine)}</td>}
              <td>{assignmentDaysText(assignment)}</td>
              <td>
                <StatusBadge code={assignment.assignment_status_code} label={statusLabel(assignment.assignment_status_code)} tone={statusTone(assignment.assignment_status_code)} />
              </td>
              <td>
                {assignment.assignment_status_code === "HELD" ? (
                  <StatusBadge code={assignment.compliance_state_code} label={complianceLabel(assignment.compliance_state_code)} tone={complianceTone(assignment.compliance_state_code)} />
                ) : (
                  "-"
                )}
              </td>
              <td>{billingCycleLabel(assignment.billing_cycle_code)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
