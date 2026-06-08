export const appsKeys = {
  all: ['apps'] as const,
  list: (input?: { platform?: string }) => [...appsKeys.all, 'list', input ?? {}] as const,
  detail: (appId: string | null | undefined) => [...appsKeys.all, 'detail', appId ?? null] as const,
}
