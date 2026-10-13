import { Page, expect } from "@playwright/test";

/**
 * Signs in through the real sign-in form using one of the documented prototype
 * seed users (docs/agent/AGENT_HANDOFF.md). Since 7 October 2026 (TB-1 TB1-203)
 * the backend creates them when it starts with a development or CI APP_ENV
 * (`python -m tooling.user_admin seed-demo-users`), not Alembic revision
 * 20260629_0002. While someone is signed in, the sign-in page offers Sign out
 * in place of the form, so a test signing in again signs out there first. The
 * page does not redirect after success -- it stays on /login, says who is
 * signed in and links to the Dashboard -- so callers navigate to their target
 * page explicitly after this resolves.
 */
export async function login(page: Page, username: string, password = "password"): Promise<void> {
  await page.goto("/login");
  const main = page.locator("main");
  const signOut = main.getByRole("button", { name: "Sign out" });
  const usernameField = main.getByLabel("Username");
  await expect(signOut.or(usernameField)).toBeVisible();
  if (await signOut.isVisible()) {
    await signOut.click();
  }
  await usernameField.fill(username);
  await main.getByLabel("Password").fill(password);
  await main.getByRole("button", { name: "Sign in" }).click();
  await expect(main.getByText("You are signed in as")).toBeVisible();
  await expect(main.getByRole("link", { name: "here", exact: true })).toHaveAttribute("href", "/");
}
