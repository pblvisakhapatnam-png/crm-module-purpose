import { describe, expect, it } from "vitest";

import { SIGN_IN_FAILED, signInRefusal } from "./signInMessages";

// TB-1 TB1-204 part a: a username stopped after repeated wrong passwords is answered 429, and the sign-in page says
// so beside its button, in the server's words, rather than calling it a wrong password.

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("signInRefusal", () => {
  it("gives the server's words for a stopped username", async () => {
    const detail = "Too many failed sign-ins for this username. Try again in 12 minutes.";
    expect(await signInRefusal(jsonResponse(429, { detail }))).toBe(detail);
  });

  it("still says the username is stopped when the answer cannot be read", async () => {
    const plain = new Response("Too Many Requests", { status: 429, headers: { "Content-Type": "text/plain" } });
    expect(await signInRefusal(plain)).toBe("Too many failed sign-ins for this username. Try again later. HTTP 429.");
  });

  it("calls any other refusal a wrong username or password, whatever the server said", async () => {
    expect(await signInRefusal(jsonResponse(401, { detail: "Invalid credentials." }))).toBe(SIGN_IN_FAILED);
    expect(await signInRefusal(jsonResponse(422, { detail: [{ loc: ["body", "password"] }] }))).toBe(SIGN_IN_FAILED);
  });
});
