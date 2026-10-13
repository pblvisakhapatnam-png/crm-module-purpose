/**
 * React Router configuration built from the explicit route table in `./routes`.
 *
 * Every application route is a child of the shell route, so the sidebar/session panel render
 * once and only the page content changes - the same structure the Next root layout provided.
 */

import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import AppShell from "./layout/AppShell";
import { appRouteDefinitions, notFoundRouteDefinition } from "./routes";
import type { AppRouteDefinition } from "./routes";

function toChildRoute(definition: AppRouteDefinition): RouteObject {
  const element = createElement(definition.Component);

  // A child route path is relative to its parent, and the shell route already owns "/".
  if (definition.path === "/") {
    return { id: definition.id, index: true, element };
  }

  return { id: definition.id, path: definition.path.replace(/^\//, ""), element };
}

/**
 * The route objects the application actually runs on. Exported so the route tests exercise the
 * real table through React Router's own matching, not a parallel copy of it.
 *
 * This module stays free of browser APIs on purpose: `createBrowserRouter` reads `document` at
 * call time, so it lives in `main.tsx` and the route table can be imported in a plain Node test
 * environment without a DOM.
 */
export const routeObjects: RouteObject[] = [
  {
    id: "app-shell",
    path: "/",
    element: createElement(AppShell),
    children: [
      ...appRouteDefinitions.map(toChildRoute),
      toChildRoute(notFoundRouteDefinition),
    ],
  },
];
