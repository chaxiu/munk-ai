export const workflowKeys = {
  all: ['workflows'] as const,
  submit: (kind: string) => [...workflowKeys.all, 'submit', kind] as const,
}
