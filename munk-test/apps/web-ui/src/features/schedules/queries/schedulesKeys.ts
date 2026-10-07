export const schedulesKeys = {
  all: ['schedules'] as const,
  list: (filters: { enabled?: boolean; appId?: string; limit?: number } = {}) => [
    ...schedulesKeys.all,
    'list',
    filters.enabled ?? null,
    filters.appId ?? null,
    filters.limit ?? null,
  ] as const,
  detail: (scheduleId: string | null | undefined) => [...schedulesKeys.all, 'detail', scheduleId ?? null] as const,
  runs: (scheduleId: string | null | undefined, limit = 20) => [...schedulesKeys.all, 'runs', scheduleId ?? null, limit] as const,
}
