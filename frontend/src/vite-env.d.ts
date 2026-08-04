interface ImportMetaEnv {
  readonly DEV: boolean
  readonly VITE_API_BASE_URL?: string
  readonly VITE_ENABLE_DEVELOPMENT_WATCH_EMBED?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
