/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_AGENTIC_URL?: string;
  readonly VITE_SIMPLE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
