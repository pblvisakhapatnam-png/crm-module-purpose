import type { ReactNode } from "react";

import type { Feedback } from "./equipmentState";

// Small pieces the Equipment pages share: the links between the pages, a message beside the button
// that caused it, and a label-value row of a `facts-list`. How they look is globals.css's.

const SECTIONS = [
  { href: "/equipment", label: "Machines" },
  { href: "/equipment/models", label: "Models" },
  { href: "/equipment/plum-report", label: "Plum report" },
  // ELG-1: the renewal list and the rules behind it.
  { href: "/equipment/certificates", label: "Certificates due" },
  { href: "/equipment/certificate-rules", label: "Certificate rules" },
  // ELG-2: the reminders themselves, and who each reaches, and when.
  { href: "/alerts", label: "Alerts" },
  { href: "/equipment/alert-settings", label: "Reminder settings" },
];

export function EquipmentNav({ current }: { current: string }) {
  return (
    <nav className="page-actions" aria-label="Equipment">
      {SECTIONS.map((section) =>
        section.href === current ? (
          <strong key={section.href} aria-current="page">
            {section.label}
          </strong>
        ) : (
          <a key={section.href} href={section.href}>
            {section.label}
          </a>
        ),
      )}
    </nav>
  );
}

export function FeedbackLine({ feedback }: { feedback: Feedback | undefined }) {
  if (!feedback) return null;
  return (
    <p className={`action-feedback ${feedback.kind === "success" ? "text-success" : "text-danger"}`} role={feedback.kind === "error" ? "alert" : "status"}>
      {feedback.text}
    </p>
  );
}

export function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </>
  );
}
