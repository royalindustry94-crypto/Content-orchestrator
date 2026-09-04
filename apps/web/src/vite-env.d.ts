/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CREATIVE_PREVIEW?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
