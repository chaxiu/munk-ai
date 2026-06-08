export const testsKeys = {
  all: ['tests'] as const,
  plans: (input?: {
    appId?: string
    source?: string
    caseCountMode?: 'all' | 'single' | 'multi'
    includeLatestRun?: boolean
    limit?: number
    offset?: number
  }) => [
    ...testsKeys.all,
    'plans',
    input?.appId ?? 'all',
    input?.source ?? 'all',
    input?.caseCountMode ?? 'all',
    input?.includeLatestRun ?? false,
    input?.limit ?? 20,
    input?.offset ?? 0,
  ] as const,
  caseSearch: (input?: {
    appId?: string
    planId?: string
    caseId?: string
    query?: string
    isCoreCase?: boolean
    startMode?: string
    limit?: number
    offset?: number
  }) => [
    ...testsKeys.all,
    'case-search',
    input?.appId ?? 'all',
    input?.planId ?? 'all',
    input?.caseId ?? '',
    input?.query ?? '',
    input?.isCoreCase ?? 'all',
    input?.startMode ?? 'all',
    input?.limit ?? 20,
    input?.offset ?? 0,
  ] as const,
  planDetail: (appId: string, planId: string) => [...testsKeys.all, 'plan-detail', appId, planId] as const,
  caseDetail: (appId: string, planId: string, caseId: string) =>
    [...testsKeys.all, 'case-detail', appId, planId, caseId] as const,
  createOperation: (operationId: string) => [...testsKeys.all, 'create-operation', operationId] as const,
  createOperationEvents: (operationId: string) =>
    [...testsKeys.all, 'create-operation-events', operationId] as const,
}
