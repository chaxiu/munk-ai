export const operationKeys = {
  all: ['operations'] as const,
  list: () => [...operationKeys.all, 'list'] as const,
  detail: (operationId: string) => [...operationKeys.all, 'detail', operationId] as const,
}
