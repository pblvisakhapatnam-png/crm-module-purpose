import { hrefWithReturnTarget } from "../resource-requirements/pageSession";
import AllocationsSection from "./AllocationsSection";
import AllocationsTable from "./AllocationsTable";
import { unitRows } from "./allocationState";

// "Machines" on a requirement's page (design section 7, screen 2): one row per unit with its allocations over time,
// how many units are covered, and "Allocate a machine" for each unit, to those who may allocate while the
// requirement is live.

export default function RequirementMachinesSection({
  requirementPublicId,
  unitsRequired,
  unitsCovered,
  coveredUnits,
  canAllocateHere,
  siteProblem,
}: {
  requirementPublicId: string;
  unitsRequired: number;
  unitsCovered: number;
  // The units the server says are covered on every day: no link to allocate to them again.
  coveredUnits: number[];
  canAllocateHere: boolean;
  // Why no machine can be allocated yet (lineSiteProblem): said in place of the links, which would only be refused.
  siteProblem: string | null;
}) {
  const page = `/resource-requirements/${requirementPublicId}`;
  return (
    <AllocationsSection
      id="machines"
      title={`Machines - ${unitsCovered} of ${unitsRequired} unit${unitsRequired === 1 ? "" : "s"} covered`}
      tone="violet"
      filter="requirement_public_id"
      recordPublicId={requirementPublicId}
      empty="No machine has been allocated yet."
      render={(assignments) => (
        <>
          {canAllocateHere && siteProblem ? <p className="text-warning">{siteProblem}</p> : null}
          {unitRows(unitsRequired, assignments, coveredUnits).map((row) => (
            <div key={row.unit} className="divided-item">
              <p>
                <strong>Unit {row.unit}</strong>
                {row.required ? "" : " - above the number now required: free its machine"}
              </p>
              {row.allocations.length > 0 ? (
                <AllocationsTable assignments={row.allocations} hide={["work-order", "requirement"]} returnTo={{ href: page, label: "Back to the requirement" }} />
              ) : (
                <p className="helper-text">No machine yet.</p>
              )}
              {canAllocateHere && !siteProblem && row.required && !row.covered ? (
                <div className="form-actions">
                  <a
                    className="button-link-secondary"
                    href={hrefWithReturnTarget(`/resource-assignments/new?requirement=${requirementPublicId}&unit=${row.unit}`, page, "Back to the requirement")}
                  >
                    Allocate a machine to unit {row.unit}
                  </a>
                </div>
              ) : null}
            </div>
          ))}
        </>
      )}
    />
  );
}
