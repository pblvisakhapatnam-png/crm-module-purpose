/**
 * Shared page layout building blocks (UI cleanup, September 2026).
 *
 * Detail pages used to define their own section cards with inline styles, so every page looked a
 * little different and none could be restyled in one place. These components carry class names
 * styled in globals.css, giving every detail page the same header, the same grouped and boxed
 * sections and the same jump-to-section index. They are presentation only: no data loading and
 * no permission logic, so they cannot change what a user is allowed to do.
 */

import { Children } from "react";
import type { ReactNode } from "react";

export type SectionTone = "blue" | "teal" | "amber" | "violet" | "slate";

type PageHeaderProps = {
  eyebrow?: string;
  title: ReactNode;
  badges?: ReactNode;
  subtitle?: ReactNode;
  back?: { href: string; label: string };
  actions?: ReactNode;
  children?: ReactNode;
};

export function PageHeader({ eyebrow, title, badges, subtitle, back, actions, children }: PageHeaderProps) {
  // Children.toArray drops null and false, so a header whose notes are all conditional - and
  // currently all empty - renders no empty notes area.
  const notes = Children.toArray(children);
  return (
    <header className="page-header">
      {back ? (
        <a className="page-header-back" href={back.href}>
          <span aria-hidden="true">&larr;</span>
          {back.label}
        </a>
      ) : null}
      <div className="page-header-main">
        <div className="page-header-titles">
          {eyebrow ? <p className="page-header-eyebrow">{eyebrow}</p> : null}
          <h2 className="page-header-title">{title}</h2>
          {badges ? <div className="page-header-badges">{badges}</div> : null}
          {subtitle ? <p className="page-header-subtitle">{subtitle}</p> : null}
        </div>
        {actions ? <div className="page-header-actions">{actions}</div> : null}
      </div>
      {notes.length > 0 ? <div className="page-header-notes">{notes}</div> : null}
    </header>
  );
}

type SectionGroupProps = {
  id: string;
  title: string;
  description?: ReactNode;
  tone?: SectionTone;
  children: ReactNode;
};

/** A labelled, coloured band that holds related section cards together. */
export function SectionGroup({ id, title, description, tone = "teal", children }: SectionGroupProps) {
  const titleId = `${id}-title`;
  return (
    <section className={`section-group section-group--${tone}`} id={id} aria-labelledby={titleId}>
      <div className="section-group-header">
        <h3 className="section-group-title" id={titleId}>
          {title}
        </h3>
        {description ? <p className="section-group-description">{description}</p> : null}
      </div>
      <div className="section-group-body">{children}</div>
    </section>
  );
}

type SectionCardProps = {
  title: ReactNode;
  id?: string;
  tone?: SectionTone;
  soft?: boolean;
  children: ReactNode;
};

/** One bordered section. Inside a SectionGroup it takes the group's colour; alone, pass a tone. */
export function SectionCard({ title, id, tone, soft = false, children }: SectionCardProps) {
  const classes = ["section-card", tone ? `section-card--${tone}` : "", soft ? "section-card--soft" : ""]
    .filter(Boolean)
    .join(" ");
  return (
    <section className={classes} id={id}>
      <h4 className="section-card-title">{title}</h4>
      <div className="section-card-body">{children}</div>
    </section>
  );
}

type SectionIndexProps = {
  /** `target`, where given, finds the element to scroll to when the link is used - the one nearest the screen, say -
   * instead of the element with `id`, which stays the link's address. */
  items: { id: string; label: string; target?: () => HTMLElement | null }[];
  label?: string;
};

/** A sticky row of links that scroll to the named sections on a long page. */
export function SectionIndex({ items, label = "Jump to" }: SectionIndexProps) {
  return (
    <nav className="section-index" aria-label="Sections on this page">
      <span className="section-index-label">{label}</span>
      {items.map((item) => (
        <a
          key={item.id}
          href={`#${item.id}`}
          onClick={(event) => {
            // Scroll in place rather than changing the URL hash, so the page's origin-aware Back
            // link and any return query string are left exactly as they were.
            event.preventDefault();
            (item.target?.() ?? document.getElementById(item.id))?.scrollIntoView({ behavior: "smooth", block: "start" });
          }}
        >
          {item.label}
        </a>
      ))}
      <a
        className="section-index-top"
        href="#"
        onClick={(event) => {
          // Same reasoning as the section links above: scroll in place rather than letting the
          // browser put a bare "#" in the address bar, which would drop a return query string.
          event.preventDefault();
          window.scrollTo({ top: 0, behavior: "smooth" });
        }}
      >
        Back to top
      </a>
    </nav>
  );
}

export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger" | "muted";

// Colour only - the label always comes from the page's own formatter, so badge text stays
// identical to the status wording used everywhere else on that page.
const STATUS_TONES: Record<string, StatusTone> = {
  DRAFT: "neutral",
  NEW: "neutral",
  RECEIVED: "neutral",
  READY_FOR_REVIEW: "neutral",
  SUBMITTED: "info",
  REVISED: "info",
  RESUBMITTED: "info",
  OPEN: "info",
  UNDER_REVIEW: "info",
  CONTACTED: "info",
  REVIEW_PENDING: "info",
  NEEDS_REVIEW: "info",
  QUALIFICATION_PENDING: "info",
  QUALIFICATION_READY: "info",
  QUOTE_PENDING: "info",
  QUALIFIED_PROSPECT: "info",
  HANDOFF_CREATED: "info",
  ACCEPTED: "success",
  APPROVED_FOR_ISSUE: "success",
  VALIDATED: "success",
  QUALIFIED: "success",
  CONVERTED: "success",
  WON: "success",
  CUSTOMER_ACTIVE: "success",
  ON_HOLD: "warning",
  REVISION_REQUESTED: "warning",
  CUSTOMER_ACTIVATION_PENDING: "warning",
  REJECTED: "danger",
  LOST: "danger",
  UNQUALIFIED: "danger",
  DISQUALIFIED: "danger",
  BLACKLISTED: "danger",
  WITHDRAWN: "muted",
  CLOSED: "muted",
  CANCELLED: "muted",
  EXECUTION_DEFERRED: "muted",
};

/** A status in its tone: the tone of a record status code, or one given where the page decides it (ELG-1's
 *  answers and certificate outcomes, whose codes are not record statuses). */
export function StatusBadge({ code, label, tone: given }: { code: string | null | undefined; label: ReactNode; tone?: StatusTone }) {
  const tone = given ?? ((code && STATUS_TONES[code]) || "neutral");
  return <span className={`status-badge status-badge--${tone}`}>{label}</span>;
}

// The words a user reads for a Work Order status. The status code itself never changes; a code
// not listed here is shown title-cased, the same way the pages format every other status.
const WORK_ORDER_STATUS_LABELS: Record<string, string> = {
  HANDOFF_CREATED: "Awaiting release to Ops",
};

export function formatWorkOrderStatusLabel(code: string | null | undefined): string {
  if (!code) return "-";
  const label = WORK_ORDER_STATUS_LABELS[code];
  if (label) return label;
  return code
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

/** A long internal identifier, kept visible for traceability but visually secondary. */
export function ReferenceText({ children }: { children: ReactNode }) {
  return <span className="reference-text">{children}</span>;
}
