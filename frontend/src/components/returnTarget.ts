// Where a page's "Back to ..." link may lead: only to a page of this site (Slice 6A: an external,
// protocol-style or protocol-relative returnTo is ignored). One guard for every page. TB-1 found it
// copied into eight pages as a prefix test that a browser reads differently (TB1-805): "/\evil.example"
// and "/<tab>/evil.example" passed it, and a browser opens both as another site.

export type ReturnTarget = { href: string; label: string };

const LABEL_MAX_LENGTH = 60;

// A browser reads a backslash as "/" in a web address and drops a tab or a line break, so either can
// turn "/x" into "//host". Neither belongs in a link the application builds.
const UNSAFE_CHARACTERS = /[\\\u0000-\u001f\u007f]/;

/**
 * The value, when it is a path on this site ("/", not "//") that as a link leads to a page of the same site; otherwise
 * null. A protocol-relative value is refused even when it names this site, as Slice 6A's rule says.
 */
export function safeReturnHref(value: string | null | undefined, origin: string): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//") || UNSAFE_CHARACTERS.test(value)) return null;
  try {
    return new URL(value, origin).origin === origin ? value : null;
  } catch {
    return null;
  }
}

/** The page's Back link from its returnTo and returnLabel, or the default when returnTo is missing or not safe. */
export function readSafeReturnTarget(defaultHref: string, defaultLabel: string): ReturnTarget {
  if (typeof window === "undefined") return { href: defaultHref, label: defaultLabel };
  const params = new URLSearchParams(window.location.search);
  const href = safeReturnHref(params.get("returnTo"), window.location.origin);
  if (!href) return { href: defaultHref, label: defaultLabel };
  const label = params.get("returnLabel")?.trim();
  return { href, label: label ? label.slice(0, LABEL_MAX_LENGTH) : defaultLabel };
}
