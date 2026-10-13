import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";

// One wording for signing in and out (owner, 27 September 2026): while someone is signed in, the sign-in page
// says who and offers Sign out in place of the form; the menu's Session panel says Sign out, never Logout.
// Needs no seeded data.

test.describe("Sign in and Sign out", () => {
  test("the sign-in page offers Sign out while signed in, and the form again after", async ({ page }) => {
    await login(page, "admin1");
    const main = page.locator("main");
    const menu = page.locator(".session-panel");
    await expect(menu.getByRole("button", { name: "Sign out" })).toBeVisible();
    await expect(page.getByText(/\bLog ?(in|out)\b/i)).toHaveCount(0);

    // Coming back to the page while signed in: no form, the name, and Sign out.
    await page.goto("/login");
    await expect(main.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expect(main.getByText("You are signed in as")).toBeVisible();
    await expect(main.getByLabel("Username")).toHaveCount(0);
    await main.getByRole("button", { name: "Sign out" }).click();

    // Signed out: the form is back, and the menu offers Sign in.
    await expect(main.getByLabel("Username")).toBeVisible();
    await expect(menu).toContainText("Not signed in");
    await expect(menu.getByRole("link", { name: "Sign in" })).toBeVisible();

    // Signing in as someone else from there.
    await login(page, "readonly1");
    await expect(menu).toContainText("Signed in as");
    await expect(menu).not.toContainText("Admin");
  });
});
