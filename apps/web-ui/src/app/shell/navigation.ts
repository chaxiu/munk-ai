import {
  Boxes,
  CalendarClock,
  Clapperboard,
  LayoutDashboard,
  PlayCircle,
  Package,
  Settings,
  Smartphone,
  TestTube2,
} from '@lucide/vue'

import { routes } from '@/app/router/routes'
import type { SidebarNavigationItem } from '@/app/router/routeMeta'

const sidebarIcons = {
  dashboard: LayoutDashboard,
  devices: Smartphone,
  tests: TestTube2,
  recording: Clapperboard,
  runs: PlayCircle,
  schedules: CalendarClock,
  assets: Package,
  apps: Boxes,
  settings: Settings,
} as const

function isSidebarFeature(feature: string): feature is keyof typeof sidebarIcons {
  return feature in sidebarIcons
}

export const sidebarNavigationItems: SidebarNavigationItem[] = routes
  .filter((route) => route.meta?.sidebar === true)
  .map((route) => {
    if (typeof route.name !== 'string') {
      throw new Error(`Sidebar route is missing a string name: ${route.path}`)
    }
    if (typeof route.meta?.navLabel !== 'string') {
      throw new Error(`Sidebar route is missing navLabel metadata: ${route.path}`)
    }
    const feature = route.meta.feature
    if (!feature || !isSidebarFeature(feature)) {
      throw new Error(`Sidebar route is missing a sidebar icon mapping: ${route.path}`)
    }
    return {
      routeName: route.name,
      labelKey: route.meta.navLabel,
      icon: sidebarIcons[feature],
    }
  })
