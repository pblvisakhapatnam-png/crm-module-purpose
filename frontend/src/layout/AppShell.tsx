/**
 * Application shell.
 *
 * This renders the sidebar, primary navigation links, lifecycle demo guide and `SessionActions`
 * panel around every page, with the same markup and class names the application has always used.
 * `<html>`/`<body>`, the page title and the description meta tag live in `frontend/index.html`,
 * and page content arrives through React Router's `<Outlet />`.
 *
 * The navigation deliberately keeps ordinary anchors. The pages already navigate with plain
 * `<a href>` and `window.location`, so leaving them as anchors preserves the browser history and
 * reload behavior they were built and accepted against.
 *
 * The menu can be hidden and shown again (the project owner, 26 September 2026), leaving the page the
 * full width. One class on `.app-shell` does it in globals.css; the choice is kept per browser.
 *
 * Alerts (ELG-2) carries the count of certificate reminders that have reached the signed-in person and that they
 * have not seen; the Menu button carries it too while the menu is hidden. The count is read when a page loads, at
 * most every five minutes, at once after reminders are marked seen, and when the session changes - and a count
 * read for one session is never shown for another (pages/alerts/alertsState.ts).
 */

import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";

import SessionActions from "../components/SessionActions";
import { ALERTS_SEEN_EVENT, type AlertCount, countLabel, createCountLoader } from "../pages/alerts/alertsState";
import { SESSION_CHANGED_EVENT, getToken } from "../pages/resource-requirements/pageSession";
import { readMenuShown, STACKED_MENU_QUERY, writeMenuShown } from "./menuPreference";
import "../styles/globals.css";

const ALERTS_HREF = "/alerts";

const navigationLinks = [
  { href: "/", label: "Dashboard" },
  { href: ALERTS_HREF, label: "Alerts" },
  { href: "/accounts", label: "Accounts" },
  { href: "/leads", label: "Leads" },
  { href: "/opportunities", label: "Opportunities" },
  { href: "/commercial-offers", label: "Commercial Offers" },
  { href: "/terms-and-conditions", label: "T&C Library" },
  { href: "/work-orders", label: "Work Orders" },
  // HOL-1: PBL's holiday calendar, which every Work Order follows.
  { href: "/holiday-calendar", label: "Holiday Calendar" },
  { href: "/resource-requirements", label: "Resource Planning" },
  { href: "/resource-assignments", label: "Allocations" },
  { href: "/equipment", label: "Equipment" },
  { href: "/documents", label: "Documents" },
  { href: "/workflow-statuses", label: "Workflow Statuses" },
  { href: "/events", label: "Events" },
];

const demoFlowLinks = [
  { href: "/leads", label: "Lead" },
  { href: "/accounts", label: "Account" },
  { href: "/opportunities", label: "Opportunity" },
  { href: "/commercial-offers", label: "Commercial Offer" },
  { href: "/work-orders", label: "Work Order" },
];

function browserStore() {
  return window.localStorage;
}

function sessionStore() {
  return window.sessionStorage;
}

async function fetchAlertCount(token: string): Promise<number> {
  const response = await fetch("/api/eligibility/alerts/count", { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error("The alerts count could not be read.");
  return ((await response.json()) as AlertCount).unseen;
}

/** The count of reminders not yet seen, for the session in use; null while there is none to show. */
function useAlertCount(): number | null {
  const [count, setCount] = useState<number | null>(null);
  const [loader] = useState(() =>
    createCountLoader({ getToken, fetchCount: fetchAlertCount, store: sessionStore, now: () => Date.now(), show: setCount }),
  );

  useEffect(() => {
    void loader.load(false);
    const again = () => void loader.load(true);
    const tokenChangedElsewhere = (event: StorageEvent) => {
      if (event.key === null || event.key === "pbl_auth_token") again();
    };
    window.addEventListener(SESSION_CHANGED_EVENT, again);
    window.addEventListener(ALERTS_SEEN_EVENT, again);
    window.addEventListener("storage", tokenChangedElsewhere);
    return () => {
      window.removeEventListener(SESSION_CHANGED_EVENT, again);
      window.removeEventListener(ALERTS_SEEN_EVENT, again);
      window.removeEventListener("storage", tokenChangedElsewhere);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return count;
}

export default function AppShell() {
  const [menuShown, setMenuShown] = useState(() =>
    readMenuShown(browserStore, window.matchMedia(STACKED_MENU_QUERY).matches),
  );
  const alertCount = useAlertCount();
  const alertLabel = countLabel(alertCount);
  const alertWords = alertLabel ? `${alertCount} ${alertCount === 1 ? "alert" : "alerts"} not seen` : "";

  function toggleMenu() {
    setMenuShown(!menuShown);
    writeMenuShown(browserStore, !menuShown);
  }

  return (
    <div className={menuShown ? "app-shell" : "app-shell app-shell--menu-hidden"}>
      <aside className="app-sidebar">
        <div className="app-sidebar-top">
          <div className="app-brand">
            <h1 className="app-brand-name">PBL CRM</h1>
            <p className="app-brand-subtitle">Equipment hiring</p>
          </div>
          <button
            type="button"
            className="app-menu-toggle"
            aria-label="Menu"
            aria-controls="app-menu"
            aria-expanded={menuShown}
            title={menuShown ? "Hide the menu" : alertWords ? `Show the menu - ${alertWords}` : "Show the menu"}
            onClick={toggleMenu}
          >
            <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true" focusable="false">
              <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            {!menuShown && alertLabel ? (
              <span className="app-nav-count app-menu-count" aria-hidden="true">
                {alertLabel}
              </span>
            ) : null}
          </button>
        </div>

        <div className="app-menu" id="app-menu">
          <p className="app-nav-title">Primary navigation</p>
          <nav className="app-nav" aria-label="Primary navigation">
            {navigationLinks.map((link) => (
              <a className="app-nav-link" href={link.href} key={link.href}>
                {link.label}
                {link.href === ALERTS_HREF && alertLabel ? (
                  <span className="app-nav-count" title={alertWords} aria-label={alertWords}>
                    {alertLabel}
                  </span>
                ) : null}
              </a>
            ))}
          </nav>

          <div className="app-demo-flow" aria-label="Lifecycle guide">
            <p className="app-demo-flow-title">Lifecycle guide</p>
            <div className="app-demo-flow-list">
              {demoFlowLinks.map((link, index) => (
                <div className="app-flow-step" key={link.href}>
                  <a className="app-flow-link" href={link.href}>
                    {link.label}
                  </a>
                  {index < demoFlowLinks.length - 1 ? (
                    <span className="app-flow-step-arrow" aria-hidden="true">&darr;</span>
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          <SessionActions />
        </div>
      </aside>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
