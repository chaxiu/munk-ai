export const homeKeys = {
  all: ['home'] as const,
  summary: () => [...homeKeys.all, 'summary'] as const,
  recentRuns: () => [...homeKeys.all, 'recent-runs'] as const,
}
