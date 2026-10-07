export const runsKeys = {
  all: ['runs'] as const,
  list: (input?: {
    limit?: number
    offset?: number
    status?: string
    kind?: string
    deviceRef?: string
    surface?: string
    verificationVerdict?: string
    platform?: string
    query?: string
    runType?: string
  }) => [
    ...runsKeys.all,
    'list',
    input?.limit ?? 50,
    input?.offset ?? 0,
    input?.status ?? 'all',
    input?.kind ?? 'all',
    input?.deviceRef ?? 'all',
    input?.surface ?? 'all',
    input?.verificationVerdict ?? 'all',
    input?.platform ?? 'all',
    input?.query ?? '',
    input?.runType ?? 'all',
  ] as const,
  detail: (operationId: string) => [...runsKeys.all, 'detail', operationId] as const,
  events: (operationId: string) => [...runsKeys.all, 'events', operationId] as const,
  artifacts: (operationId: string) => [...runsKeys.all, 'artifacts', operationId] as const,
  batchChildren: (operationId: string) => [...runsKeys.all, 'batch-children', operationId] as const,
  children: (operationId: string, artifactId: string) => [...runsKeys.all, 'children', operationId, artifactId] as const,
}
