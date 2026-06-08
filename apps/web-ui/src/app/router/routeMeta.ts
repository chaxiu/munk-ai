import type { Component } from 'vue'

export type AppFeature =
  | 'dashboard'
  | 'devices'
  | 'tests'
  | 'runs'
  | 'schedules'
  | 'recording'
  | 'assets'
  | 'apps'
  | 'settings'
  | 'not-found'

export type ShellActionId = 'tests-planning'

export interface AppRouteMeta {
  title?: string
  navLabel?: string
  feature?: AppFeature
  sidebar?: boolean
  shellAction?: ShellActionId
}

export interface SidebarNavigationItem {
  routeName: string
  labelKey: string
  icon: Component
}

declare module 'vue-router' {
  // vue-router requires declaration merging for RouteMeta augmentation.
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  interface RouteMeta extends AppRouteMeta {}
}
