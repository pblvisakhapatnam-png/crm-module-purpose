import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { installPerimeterFetchShim, PERIMETER_TOKEN_HEADER, relocateAuthorization } from "./perimeter";

const ORIGIN = "https://crm-uat.example.test";
const BEARER = "Bearer header.payload.signature";

function headersOf(init: RequestInit | undefined): Headers {
  return new Headers(init?.headers);
}

describe("relocateAuthorization", () => {
  it("moves the token of a same-origin API call out of Authorization", () => {
    const init: RequestInit = { method: "GET", headers: { Authorization: BEARER } };

    const result = relocateAuthorization("/api/accounts?limit=21", init, ORIGIN);

    const headers = headersOf(result);
    expect(headers.get("Authorization")).toBeNull();
    expect(headers.get(PERIMETER_TOKEN_HEADER)).toBe(BEARER);
    expect(result?.method).toBe("GET");
  });

  it("finds the header whatever its case, and in every header shape", () => {
    const shapes: HeadersInit[] = [
      { authorization: BEARER },
      [["AUTHORIZATION", BEARER]],
      new Headers({ Authorization: BEARER }),
    ];

    for (const shape of shapes) {
      const headers = headersOf(relocateAuthorization("/api/leads", { headers: shape }, ORIGIN));
      expect(headers.get("Authorization")).toBeNull();
      expect(headers.get(PERIMETER_TOKEN_HEADER)).toBe(BEARER);
    }
  });

  it("keeps the other headers, the body and the method", () => {
    const body = JSON.stringify({ offer_title: "x" });
    const init: RequestInit = {
      method: "POST",
      body,
      headers: { Authorization: BEARER, "Content-Type": "application/json" },
    };

    const result = relocateAuthorization("/api/commercial-offers", init, ORIGIN);

    expect(result?.method).toBe("POST");
    expect(result?.body).toBe(body);
    expect(headersOf(result).get("Content-Type")).toBe("application/json");
  });

  it("does not change the caller's own objects", () => {
    const original = { Authorization: BEARER };
    const init: RequestInit = { headers: original };

    relocateAuthorization("/api/accounts", init, ORIGIN);

    expect(init.headers).toBe(original);
    expect(original).toEqual({ Authorization: BEARER });
  });

  it("accepts absolute same-origin URLs and URL objects", () => {
    for (const input of [`${ORIGIN}/api/accounts`, new URL("/api/accounts", ORIGIN)]) {
      const headers = headersOf(relocateAuthorization(input, { headers: { Authorization: BEARER } }, ORIGIN));
      expect(headers.get(PERIMETER_TOKEN_HEADER)).toBe(BEARER);
    }
  });

  it("leaves requests that are not same-origin API calls untouched", () => {
    const init: RequestInit = { headers: { Authorization: BEARER } };

    for (const input of ["/login", "/assets/index.js", "/apiary", "https://elsewhere.example.test/api/accounts"]) {
      expect(relocateAuthorization(input, init, ORIGIN)).toBe(init);
    }
  });

  it("leaves API calls without an Authorization header untouched, such as sign-in itself", () => {
    const withoutHeaders: RequestInit = { method: "POST", body: "{}" };
    const withOtherHeaders: RequestInit = { method: "POST", headers: { "Content-Type": "application/json" } };

    expect(relocateAuthorization("/api/auth/login", withoutHeaders, ORIGIN)).toBe(withoutHeaders);
    expect(relocateAuthorization("/api/auth/login", withOtherHeaders, ORIGIN)).toBe(withOtherHeaders);
    expect(relocateAuthorization("/api/auth/login", undefined, ORIGIN)).toBeUndefined();
  });

  it("leaves a Request object alone", () => {
    const request = new Request(`${ORIGIN}/api/accounts`, { headers: { Authorization: BEARER } });
    const init: RequestInit = { headers: { Authorization: BEARER } };

    expect(relocateAuthorization(request, init, ORIGIN)).toBe(init);
  });
});

describe("installPerimeterFetchShim", () => {
  it("sends every fetch through the relocation", async () => {
    const calls: Array<[RequestInfo | URL, RequestInit | undefined]> = [];
    const target = {
      location: { origin: ORIGIN },
      fetch: (input: RequestInfo | URL, init?: RequestInit) => {
        calls.push([input, init]);
        return Promise.resolve(new Response(null, { status: 204 }));
      },
    } as unknown as Window;

    installPerimeterFetchShim(target);
    await target.fetch("/api/accounts", { headers: { Authorization: BEARER } });
    await target.fetch("/login");

    expect(calls).toHaveLength(2);
    expect(calls[0][0]).toBe("/api/accounts");
    expect(headersOf(calls[0][1]).get(PERIMETER_TOKEN_HEADER)).toBe(BEARER);
    expect(headersOf(calls[0][1]).get("Authorization")).toBeNull();
    expect(calls[1]).toEqual(["/login", undefined]);
  });
});

describe("the nginx configuration", () => {
  // The header only works if nginx reads the same name the pages write. nginx exposes a request
  // header as $http_<name>, lower-cased with dashes turned into underscores.
  const conf = readFileSync(new URL("../nginx/default.conf", import.meta.url), "utf8");
  const nginxVariable = `$http_${PERIMETER_TOKEN_HEADER.toLowerCase().replace(/-/g, "_")}`;

  it("copies the relocated token back into Authorization for the backend", () => {
    expect(conf).toContain(`map ${nginxVariable} $pbl_upstream_authorization`);
    expect(conf).toContain("proxy_set_header Authorization $pbl_upstream_authorization;");
  });

  it("does not pass the relocated header on to the backend", () => {
    expect(conf).toContain(`proxy_set_header ${PERIMETER_TOKEN_HEADER} "";`);
  });

  it("passes the browser's scheme on, so the backend's redirects keep https", () => {
    // The hosted pilot's backend trusts this header from nginx (FORWARDED_ALLOW_IPS).
    expect(conf).toContain("map $http_x_forwarded_proto $pbl_forwarded_proto");
    expect(conf).toContain("proxy_set_header X-Forwarded-Proto $pbl_forwarded_proto;");
  });
});
