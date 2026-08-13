/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GOOGLE_CLIENT_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

// Augment vue-router RouteMeta to include custom meta fields
import 'vue-router'
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresStaff?: boolean
    guestOnly?: boolean
  }
}
