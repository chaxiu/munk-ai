export const cloudKeys = {
  all: ['cloud'] as const,
  session: () => [...cloudKeys.all, 'session'] as const,
  workspaces: () => [...cloudKeys.all, 'workspaces'] as const,
  links: () => [...cloudKeys.all, 'links'] as const,
  apps: (workspaceId: string) => [...cloudKeys.all, 'apps', workspaceId] as const,
  syncStatus: (appId?: string | null) => [...cloudKeys.all, 'syncStatus', appId ?? null] as const,
}
