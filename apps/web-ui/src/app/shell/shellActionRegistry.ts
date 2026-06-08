import type { Component } from 'vue'

import type { ShellActionId } from '@/app/router/routeMeta'
import TestsShellActions from '@/features/tests/components/TestsShellActions.vue'

const shellActionRegistry: Record<ShellActionId, Component> = {
  'tests-planning': TestsShellActions,
}

export function resolveShellActionComponent(actionId: ShellActionId | undefined): Component | null {
  if (!actionId) {
    return null
  }
  return shellActionRegistry[actionId] ?? null
}
