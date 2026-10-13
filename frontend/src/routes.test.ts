/**
 * Route-table regression tests.
 *
 * These run React Router's own `matchRoutes` against the exact route objects the application
 * mounts (`src/router.tsx`), so a removed route, a renamed URL segment, a renamed dynamic
 * parameter or a route wired to the wrong page module all fail here.
 *
 * The page-module identity assertions matter as much as the URL assertions: matching
 * `/accounts/:accountId` is only correct if it actually renders the Account detail page.
 */

import { matchRoutes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { routeObjects } from "./router";
import { appRouteDefinitions, notFoundRouteDefinition } from "./routes";

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

/**
 * Every public URL the application serves, with the route id it must resolve to and the dynamic
 * parameters it must produce. Sourced from the TE-2A route list; the sample ids use UUID-shaped
 * values because that is what the application's public ids look like.
 */
const ACCOUNT_ID = "11111111-1111-1111-1111-111111111111";
const LEAD_ID = "22222222-2222-2222-2222-222222222222";
const OPPORTUNITY_ID = "33333333-3333-3333-3333-333333333333";
const OFFER_ID = "44444444-4444-4444-4444-444444444444";
const WORK_ORDER_ID = "55555555-5555-5555-5555-555555555555";
const AMENDMENT_ID = "66666666-6666-6666-6666-666666666666";
const REQUIREMENT_ID = "77777777-7777-7777-7777-777777777777";
const ASSET_ID = "88888888-8888-8888-8888-888888888888";
const IMPORT_ID = "99999999-9999-9999-9999-999999999999";
const ASSIGNMENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";

const expectedMatches: Array<{
  url: string;
  routeId: string;
  params: Record<string, string>;
}> = [
  { url: "/", routeId: "dashboard", params: {} },
  { url: "/login", routeId: "login", params: {} },

  { url: "/accounts", routeId: "accounts", params: {} },
  { url: "/accounts/new", routeId: "accounts.new", params: {} },
  { url: `/accounts/${ACCOUNT_ID}`, routeId: "accounts.detail", params: { accountId: ACCOUNT_ID } },

  { url: "/leads", routeId: "leads", params: {} },
  { url: "/leads/new", routeId: "leads.new", params: {} },
  { url: `/leads/${LEAD_ID}`, routeId: "leads.detail", params: { leadId: LEAD_ID } },

  { url: "/opportunities", routeId: "opportunities", params: {} },
  { url: "/opportunities/new", routeId: "opportunities.new", params: {} },
  {
    url: `/opportunities/${OPPORTUNITY_ID}`,
    routeId: "opportunities.detail",
    params: { opportunityId: OPPORTUNITY_ID },
  },

  { url: "/commercial-offers", routeId: "commercial-offers", params: {} },
  { url: "/commercial-offers/new", routeId: "commercial-offers.new", params: {} },
  {
    url: `/commercial-offers/${OFFER_ID}`,
    routeId: "commercial-offers.detail",
    params: { commercialOfferId: OFFER_ID },
  },
  {
    url: `/commercial-offers/${OFFER_ID}/related-offers/new`,
    routeId: "commercial-offers.related-offers.new",
    params: { commercialOfferId: OFFER_ID },
  },

  { url: "/terms-and-conditions", routeId: "terms-and-conditions", params: {} },

  { url: "/work-orders", routeId: "work-orders", params: {} },
  { url: "/work-orders/new", routeId: "work-orders.new", params: {} },
  {
    url: `/work-orders/${WORK_ORDER_ID}`,
    routeId: "work-orders.detail",
    params: { workOrderId: WORK_ORDER_ID },
  },
  {
    url: `/work-orders/${WORK_ORDER_ID}/amendments/new`,
    routeId: "work-orders.amendments.new",
    params: { workOrderId: WORK_ORDER_ID },
  },
  {
    url: `/work-orders/${WORK_ORDER_ID}/amendments/${AMENDMENT_ID}`,
    routeId: "work-orders.amendments.detail",
    params: { workOrderId: WORK_ORDER_ID, amendmentId: AMENDMENT_ID },
  },

  { url: "/resource-requirements", routeId: "resource-requirements", params: {} },
  { url: "/resource-requirements/new", routeId: "resource-requirements.new", params: {} },
  {
    url: `/resource-requirements/${REQUIREMENT_ID}`,
    routeId: "resource-requirements.detail",
    params: { requirementId: REQUIREMENT_ID },
  },

  { url: "/resource-assignments", routeId: "resource-assignments", params: {} },
  { url: "/resource-assignments/new", routeId: "resource-assignments.new", params: {} },
  {
    url: `/resource-assignments/${ASSIGNMENT_ID}`,
    routeId: "resource-assignments.detail",
    params: { assignmentId: ASSIGNMENT_ID },
  },

  { url: "/equipment", routeId: "equipment", params: {} },
  { url: `/equipment/machines/${ASSET_ID}`, routeId: "equipment.machines.detail", params: { assetId: ASSET_ID } },
  { url: "/equipment/models", routeId: "equipment.models", params: {} },
  { url: "/equipment/plum-report", routeId: "equipment.plum-report", params: {} },
  { url: `/equipment/plum-report/${IMPORT_ID}`, routeId: "equipment.plum-report.import", params: { importId: IMPORT_ID } },
  { url: "/equipment/certificates", routeId: "equipment.certificates", params: {} },
  { url: "/equipment/certificate-rules", routeId: "equipment.certificate-rules", params: {} },
  { url: "/equipment/alert-settings", routeId: "equipment.alert-settings", params: {} },
  { url: "/alerts", routeId: "alerts", params: {} },
  { url: "/holiday-calendar", routeId: "holiday-calendar", params: {} },

  { url: "/documents", routeId: "documents", params: {} },
  { url: "/workflow-statuses", routeId: "workflow-statuses", params: {} },
  { url: "/events", routeId: "events", params: {} },
];

/**
 * Every URL pattern the route table must declare, written out literally so a renamed segment or
 * a renamed dynamic parameter fails here rather than silently changing a public URL.
 */
const expectedPaths = [
  "/",
  "/login",
  "/accounts",
  "/accounts/new",
  "/accounts/:accountId",
  "/leads",
  "/leads/new",
  "/leads/:leadId",
  "/opportunities",
  "/opportunities/new",
  "/opportunities/:opportunityId",
  "/commercial-offers",
  "/commercial-offers/new",
  "/commercial-offers/:commercialOfferId",
  "/commercial-offers/:commercialOfferId/related-offers/new",
  "/terms-and-conditions",
  "/work-orders",
  "/work-orders/new",
  "/work-orders/:workOrderId",
  "/work-orders/:workOrderId/amendments/new",
  "/work-orders/:workOrderId/amendments/:amendmentId",
  "/resource-requirements",
  "/resource-requirements/new",
  "/resource-requirements/:requirementId",
  "/resource-assignments",
  "/resource-assignments/new",
  "/resource-assignments/:assignmentId",
  "/equipment",
  "/equipment/machines/:assetId",
  "/equipment/models",
  "/equipment/plum-report",
  "/equipment/plum-report/:importId",
  "/equipment/certificates",
  "/equipment/certificate-rules",
  "/equipment/alert-settings",
  "/alerts",
  "/holiday-calendar",
  "/documents",
  "/workflow-statuses",
  "/events",
];

/** Route id -> the page module that route must render. */
const expectedComponents: Record<string, unknown> = {
  dashboard: DashboardPage,
  login: LoginPage,
  accounts: AccountsPage,
  "accounts.new": NewAccountPage,
  "accounts.detail": AccountDetailPage,
  leads: LeadsPage,
  "leads.new": NewLeadPage,
  "leads.detail": LeadDetailPage,
  opportunities: OpportunitiesPage,
  "opportunities.new": NewOpportunityPage,
  "opportunities.detail": OpportunityDetailPage,
  "commercial-offers": CommercialOffersPage,
  "commercial-offers.new": NewCommercialOfferPage,
  "commercial-offers.detail": CommercialOfferDetailPage,
  "commercial-offers.related-offers.new": NewRelatedOfferPage,
  "terms-and-conditions": TermsAndConditionsPage,
  "work-orders": WorkOrdersPage,
  "work-orders.new": NewWorkOrderPage,
  "work-orders.detail": WorkOrderDetailPage,
  "work-orders.amendments.new": NewWorkOrderAmendmentPage,
  "work-orders.amendments.detail": WorkOrderAmendmentDetailPage,
  "resource-requirements": ResourceRequirementsPage,
  "resource-requirements.new": NewResourceRequirementPage,
  "resource-requirements.detail": ResourceRequirementDetailPage,
  "resource-assignments": AllocationsPage,
  "resource-assignments.new": AllocatePage,
  "resource-assignments.detail": AllocationPage,
  equipment: MachinesPage,
  "equipment.machines.detail": MachinePage,
  "equipment.models": ModelsPage,
  "equipment.plum-report": PlumReportPage,
  "equipment.plum-report.import": ImportPreviewPage,
  "equipment.certificates": CertificatesDuePage,
  "equipment.certificate-rules": CertificateRulesPage,
  "equipment.alert-settings": AlertSettingsPage,
  alerts: AlertsPage,
  "holiday-calendar": HolidayCalendarPage,
  documents: DocumentsPage,
  "workflow-statuses": WorkflowStatusesPage,
  events: EventsPage,
};

function matchLeaf(url: string) {
  const matches = matchRoutes(routeObjects, url);
  expect(matches, `no route matched ${url}`).not.toBeNull();
  return matches![matches!.length - 1];
}

describe("route table", () => {
  it("defines exactly the routes TE-2A requires, with no duplicates", () => {
    const ids = appRouteDefinitions.map((definition) => definition.id);
    const paths = appRouteDefinitions.map((definition) => definition.path);

    expect(new Set(ids).size).toBe(ids.length);
    expect(new Set(paths).size).toBe(paths.length);

    expect([...ids].sort()).toEqual([...Object.keys(expectedComponents)].sort());
    expect([...paths].sort()).toEqual([...expectedPaths].sort());
  });

  it("covers every expected public URL exactly once", () => {
    expect(expectedMatches).toHaveLength(appRouteDefinitions.length);
    expect(new Set(expectedMatches.map((entry) => entry.routeId)).size).toBe(
      appRouteDefinitions.length,
    );
  });

  it.each(expectedMatches)("matches $url to the $routeId route", ({ url, routeId, params }) => {
    const leaf = matchLeaf(url);

    expect(leaf.route.id).toBe(routeId);
    expect(leaf.params).toEqual(params);
  });

  it.each(Object.keys(expectedComponents))("wires the %s route to its own page module", (routeId) => {
    const definition = appRouteDefinitions.find((entry) => entry.id === routeId);

    expect(definition, `route id ${routeId} is missing from the route table`).toBeDefined();
    expect(definition!.Component).toBe(expectedComponents[routeId]);
  });

  it("renders every route inside the application shell", () => {
    for (const entry of expectedMatches) {
      const matches = matchRoutes(routeObjects, entry.url);

      expect(matches).not.toBeNull();
      expect(matches![0].route.id).toBe("app-shell");
      expect(matches!.length).toBe(2);
    }
  });

  it("prefers static segments over dynamic ones", () => {
    // `/accounts/new` must reach the create page, not the detail page with accountId="new".
    expect(matchLeaf("/accounts/new").route.id).toBe("accounts.new");
    expect(matchLeaf("/leads/new").route.id).toBe("leads.new");
    expect(matchLeaf("/opportunities/new").route.id).toBe("opportunities.new");
    expect(matchLeaf("/commercial-offers/new").route.id).toBe("commercial-offers.new");
    expect(matchLeaf("/work-orders/new").route.id).toBe("work-orders.new");
    expect(matchLeaf("/resource-requirements/new").route.id).toBe("resource-requirements.new");
    // 8A core: finding a machine is a page of its own, never an allocation called "new".
    expect(matchLeaf("/resource-assignments/new").route.id).toBe("resource-assignments.new");
    // `/equipment/models` and `/equipment/plum-report` are pages of their own, never a machine or an import.
    expect(matchLeaf("/equipment/models").route.id).toBe("equipment.models");
    expect(matchLeaf("/equipment/plum-report").route.id).toBe("equipment.plum-report");
    // ELG-1: the renewal list and the rules are pages of their own too.
    expect(matchLeaf("/equipment/certificates").route.id).toBe("equipment.certificates");
    expect(matchLeaf("/equipment/certificate-rules").route.id).toBe("equipment.certificate-rules");
    // ELG-2: the reminder settings are a page of their own, never a machine.
    expect(matchLeaf("/equipment/alert-settings").route.id).toBe("equipment.alert-settings");
    expect(matchLeaf(`/work-orders/${WORK_ORDER_ID}/amendments/new`).route.id).toBe(
      "work-orders.amendments.new",
    );
  });

  it("preserves query strings outside route matching", () => {
    // Pages read query strings through `window.location.search`; matching must ignore them.
    const leaf = matchLeaf("/commercial-offers/new?opportunityId=" + OPPORTUNITY_ID);

    expect(leaf.route.id).toBe("commercial-offers.new");
    // A new requirement names its Work Order line in the query string.
    expect(matchLeaf(`/resource-requirements/new?work_order_line=${WORK_ORDER_ID}`).route.id).toBe("resource-requirements.new");
    // Allocating names the requirement, the unit and any allocation being replaced in the query string.
    expect(matchLeaf(`/resource-assignments/new?requirement=${REQUIREMENT_ID}&unit=2&replacing=${ASSIGNMENT_ID}`).route.id).toBe(
      "resource-assignments.new",
    );
  });

  it("falls back to the not-found route for unknown URLs", () => {
    expect(matchLeaf("/not-a-real-page").route.id).toBe(notFoundRouteDefinition.id);
    expect(matchLeaf("/accounts/one/two/three").route.id).toBe(notFoundRouteDefinition.id);
  });
});
