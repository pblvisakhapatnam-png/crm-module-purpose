/**
 * Explicit route table for the Vite/React Router application.
 *
 * One entry per public frontend URL. The `path` values reproduce the public URLs the application
 * has always served, including parameter names (`accountId`, `leadId`, `opportunityId`,
 * `commercialOfferId`, `workOrderId`, `amendmentId`, `requirementId`, `assignmentId`, `assetId`, `importId`), because those names are what the pages read
 * through `useParams`.
 *
 * This table is the migration's single source of truth for what the application serves, and the
 * route tests in `routes.test.ts` exercise it directly.
 */

import type { ComponentType } from "react";

import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";

import AccountsPage from "./pages/accounts/AccountsPage";
import NewAccountPage from "./pages/accounts/NewAccountPage";
import AccountDetailPage from "./pages/accounts/AccountDetailPage";

import LeadsPage from "./pages/leads/LeadsPage";
import NewLeadPage from "./pages/leads/NewLeadPage";
import LeadDetailPage from "./pages/leads/LeadDetailPage";

import OpportunitiesPage from "./pages/opportunities/OpportunitiesPage";
import NewOpportunityPage from "./pages/opportunities/NewOpportunityPage";
import OpportunityDetailPage from "./pages/opportunities/OpportunityDetailPage";

import CommercialOffersPage from "./pages/commercial-offers/CommercialOffersPage";
import NewCommercialOfferPage from "./pages/commercial-offers/NewCommercialOfferPage";
import CommercialOfferDetailPage from "./pages/commercial-offers/CommercialOfferDetailPage";
import NewRelatedOfferPage from "./pages/commercial-offers/NewRelatedOfferPage";

import TermsAndConditionsPage from "./pages/TermsAndConditionsPage";

import WorkOrdersPage from "./pages/work-orders/WorkOrdersPage";
import NewWorkOrderPage from "./pages/work-orders/NewWorkOrderPage";
import WorkOrderDetailPage from "./pages/work-orders/WorkOrderDetailPage";
import NewWorkOrderAmendmentPage from "./pages/work-orders/NewWorkOrderAmendmentPage";
import WorkOrderAmendmentDetailPage from "./pages/work-orders/WorkOrderAmendmentDetailPage";

import ResourceRequirementsPage from "./pages/resource-requirements/ResourceRequirementsPage";
import NewResourceRequirementPage from "./pages/resource-requirements/NewResourceRequirementPage";
import ResourceRequirementDetailPage from "./pages/resource-requirements/ResourceRequirementDetailPage";

import AllocationsPage from "./pages/allocations/AllocationsPage";
import AllocatePage from "./pages/allocations/AllocatePage";
import AllocationPage from "./pages/allocations/AllocationPage";

import MachinesPage from "./pages/equipment/MachinesPage";
import MachinePage from "./pages/equipment/MachinePage";
import ModelsPage from "./pages/equipment/ModelsPage";
import PlumReportPage from "./pages/equipment/PlumReportPage";
import ImportPreviewPage from "./pages/equipment/ImportPreviewPage";
import CertificatesDuePage from "./pages/equipment/CertificatesDuePage";
import CertificateRulesPage from "./pages/equipment/CertificateRulesPage";
import AlertSettingsPage from "./pages/equipment/AlertSettingsPage";

import AlertsPage from "./pages/alerts/AlertsPage";

import HolidayCalendarPage from "./pages/holiday-calendar/HolidayCalendarPage";

import DocumentsPage from "./pages/DocumentsPage";
import WorkflowStatusesPage from "./pages/WorkflowStatusesPage";
import EventsPage from "./pages/EventsPage";

import NotFoundPage from "./pages/NotFoundPage";

export type AppRouteDefinition = {
  /** Stable identifier used by the router and by the route-table tests. */
  id: string;
  /** Public URL pattern. React Router ranks these, so `/accounts/new` wins over `/accounts/:accountId`. */
  path: string;
  Component: ComponentType;
};

export const appRouteDefinitions: AppRouteDefinition[] = [
  { id: "dashboard", path: "/", Component: DashboardPage },
  { id: "login", path: "/login", Component: LoginPage },
  // ELG-2: the certificate reminders that have reached the signed-in person.
  { id: "alerts", path: "/alerts", Component: AlertsPage },

  { id: "accounts", path: "/accounts", Component: AccountsPage },
  { id: "accounts.new", path: "/accounts/new", Component: NewAccountPage },
  { id: "accounts.detail", path: "/accounts/:accountId", Component: AccountDetailPage },

  { id: "leads", path: "/leads", Component: LeadsPage },
  { id: "leads.new", path: "/leads/new", Component: NewLeadPage },
  { id: "leads.detail", path: "/leads/:leadId", Component: LeadDetailPage },

  { id: "opportunities", path: "/opportunities", Component: OpportunitiesPage },
  { id: "opportunities.new", path: "/opportunities/new", Component: NewOpportunityPage },
  { id: "opportunities.detail", path: "/opportunities/:opportunityId", Component: OpportunityDetailPage },

  { id: "commercial-offers", path: "/commercial-offers", Component: CommercialOffersPage },
  { id: "commercial-offers.new", path: "/commercial-offers/new", Component: NewCommercialOfferPage },
  {
    id: "commercial-offers.detail",
    path: "/commercial-offers/:commercialOfferId",
    Component: CommercialOfferDetailPage,
  },
  {
    id: "commercial-offers.related-offers.new",
    path: "/commercial-offers/:commercialOfferId/related-offers/new",
    Component: NewRelatedOfferPage,
  },

  { id: "terms-and-conditions", path: "/terms-and-conditions", Component: TermsAndConditionsPage },

  { id: "work-orders", path: "/work-orders", Component: WorkOrdersPage },
  { id: "work-orders.new", path: "/work-orders/new", Component: NewWorkOrderPage },
  { id: "work-orders.detail", path: "/work-orders/:workOrderId", Component: WorkOrderDetailPage },
  {
    id: "work-orders.amendments.new",
    path: "/work-orders/:workOrderId/amendments/new",
    Component: NewWorkOrderAmendmentPage,
  },
  {
    id: "work-orders.amendments.detail",
    path: "/work-orders/:workOrderId/amendments/:amendmentId",
    Component: WorkOrderAmendmentDetailPage,
  },

  // HOL-1: PBL's holiday calendar, year by year (`?year=2027` picks one).
  { id: "holiday-calendar", path: "/holiday-calendar", Component: HolidayCalendarPage },

  // WRR-001: the planning list, a new requirement for one Work Order line, and one requirement.
  { id: "resource-requirements", path: "/resource-requirements", Component: ResourceRequirementsPage },
  { id: "resource-requirements.new", path: "/resource-requirements/new", Component: NewResourceRequirementPage },
  {
    id: "resource-requirements.detail",
    path: "/resource-requirements/:requirementId",
    Component: ResourceRequirementDetailPage,
  },

  // 8A core: the allocations list, finding and allocating a machine (or replacing one), and one allocation.
  { id: "resource-assignments", path: "/resource-assignments", Component: AllocationsPage },
  { id: "resource-assignments.new", path: "/resource-assignments/new", Component: AllocatePage },
  {
    id: "resource-assignments.detail",
    path: "/resource-assignments/:assignmentId",
    Component: AllocationPage,
  },

  // ERT-1: machines, one machine, models, and Plum's report with the preview of one upload.
  { id: "equipment", path: "/equipment", Component: MachinesPage },
  { id: "equipment.machines.detail", path: "/equipment/machines/:assetId", Component: MachinePage },
  { id: "equipment.models", path: "/equipment/models", Component: ModelsPage },
  { id: "equipment.plum-report", path: "/equipment/plum-report", Component: PlumReportPage },
  { id: "equipment.plum-report.import", path: "/equipment/plum-report/:importId", Component: ImportPreviewPage },
  // ELG-1: the renewal list, and the rules behind it.
  { id: "equipment.certificates", path: "/equipment/certificates", Component: CertificatesDuePage },
  { id: "equipment.certificate-rules", path: "/equipment/certificate-rules", Component: CertificateRulesPage },
  // ELG-2: each reminder's schedule and path.
  { id: "equipment.alert-settings", path: "/equipment/alert-settings", Component: AlertSettingsPage },

  { id: "documents", path: "/documents", Component: DocumentsPage },
  { id: "workflow-statuses", path: "/workflow-statuses", Component: WorkflowStatusesPage },
  { id: "events", path: "/events", Component: EventsPage },
];

/**
 * Catch-all for unknown URLs. The SPA fallback serves `index.html` for every path, so the
 * application supplies its own not-found page rather than relying on a server 404.
 */
export const notFoundRouteDefinition: AppRouteDefinition = {
  id: "not-found",
  path: "*",
  Component: NotFoundPage,
};
