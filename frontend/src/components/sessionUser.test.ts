// Who is signed in, as the sidebar shows it. The frontend has no component-test capability yet
// (docs/agent/DEFERRED_REQUIREMENTS.md), so the rule is tested here and the wiring by the screen check.

import { describe, expect, it } from "vitest";

import { signedInRolesText, signedInUserFromResponse, userForToken, type ResolvedSessionUser } from "./sessionUser";

describe("who is signed in", () => {
  it("reads the name and roles the server returns", () => {
    const user = signedInUserFromResponse({
      public_id: "u-1",
      username: "sales1",
      display_name: "Sales User 1",
      roles: ["Sales User"],
      role_codes: ["SALES_USER"],
    });
    expect(user).toEqual({ display_name: "Sales User 1", roles: ["Sales User"] });
    expect(signedInRolesText(user!)).toBe("Sales User");
  });

  it("lists several roles together", () => {
    expect(signedInRolesText({ display_name: "A", roles: ["Sales User", "Sales Manager"] })).toBe(
      "Sales User, Sales Manager",
    );
  });

  it("shows no name rather than a wrong one when the response is not what it should be", () => {
    expect(signedInUserFromResponse(null)).toBeNull();
    expect(signedInUserFromResponse({ detail: "Not authenticated" })).toBeNull();
    expect(signedInUserFromResponse({ display_name: "  " })).toBeNull();
  });

  it("keeps the name when the roles are missing or malformed", () => {
    expect(signedInUserFromResponse({ display_name: "Ops User 1", roles: "OPS" })).toEqual({
      display_name: "Ops User 1",
      roles: [],
    });
  });
});

describe("a name is shown only for the session it was fetched for (review round 5, F-01)", () => {
  const userA = { display_name: "Sales User 1", roles: ["Sales User"] };
  const userB = { display_name: "Finance User 1", roles: ["Finance User"] };
  const resolvedA: ResolvedSessionUser = { token: "token-A", user: userA };

  it("shows A while A's token is the one in use", () => {
    expect(userForToken(resolvedA, "token-A")).toEqual(userA);
  });

  it("shows no name the moment the token becomes B's, while B's request is still pending", () => {
    // B's request has not answered, so the only name known is still A's.
    expect(userForToken(resolvedA, "token-B")).toBeNull();
  });

  it("still shows no name when B's request fails", () => {
    const resolvedBFailed: ResolvedSessionUser = { token: "token-B", user: null };
    expect(userForToken(resolvedBFailed, "token-B")).toBeNull();
  });

  it("shows B once B's own answer arrives", () => {
    expect(userForToken({ token: "token-B", user: userB }, "token-B")).toEqual(userB);
  });

  it("shows no name when signed out, whatever was fetched before", () => {
    expect(userForToken(resolvedA, null)).toBeNull();
    expect(userForToken(null, "token-A")).toBeNull();
  });
});
