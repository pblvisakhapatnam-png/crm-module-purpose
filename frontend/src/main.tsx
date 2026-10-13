/**
 * Vite entry point.
 *
 * The application renders inside `React.StrictMode`. The Next App Router enabled Strict Mode by
 * default in development, so keeping it here preserves the development diagnostics the pages were
 * written against rather than silently relaxing them during the framework migration.
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { PERIMETER_BASIC_AUTH } from "./config/buildFlags";
import { installPerimeterFetchShim } from "./perimeter";
import { routeObjects } from "./router";

// Before any page can call fetch. Only in a build made for a Basic Auth perimeter; see perimeter.ts.
if (PERIMETER_BASIC_AUTH) {
  installPerimeterFetchShim(window);
}

const container = document.getElementById("root");

if (!container) {
  throw new Error('Root container "#root" was not found in index.html.');
}

const router = createBrowserRouter(routeObjects);

createRoot(container).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
