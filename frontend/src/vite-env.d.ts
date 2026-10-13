/// <reference types="vite/client" />

// Build-time switches read through `import.meta.env`. Vite replaces each reference with the value
// present when the bundle is built. See src/config/buildFlags.ts.
interface ImportMetaEnv {
  readonly VITE_HIDE_DEMO_CREDENTIALS?: string;
  readonly VITE_PERIMETER_BASIC_AUTH?: string;
}
