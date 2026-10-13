/**
 * Build-time switches for the hosted pilot (TE-5).
 *
 * Vite replaces `import.meta.env.VITE_*` with the literal value present when the bundle is built,
 * so a switched-off branch is removed from the bundle, not just hidden on screen.
 * frontend/Dockerfile.nginx sets both switches and fails the build if a demo username survives.
 *
 * Unset means development behaviour, so `npm run dev`, the Compose image (frontend/Dockerfile) and
 * the Playwright suite are unchanged.
 */

/** The prefilled admin1 / password sign-in and the list of demo users on the login page. */
export const SHOW_DEMO_CREDENTIALS = import.meta.env.VITE_HIDE_DEMO_CREDENTIALS !== "true";

/** A shared HTTP Basic Auth login protects the whole site. See src/perimeter.ts. */
export const PERIMETER_BASIC_AUTH = import.meta.env.VITE_PERIMETER_BASIC_AUTH === "true";
