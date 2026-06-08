export const recordingKeys = {
  all: ['recording'] as const,
  detail: (recordingId: string) => [...recordingKeys.all, recordingId] as const,
  session: (recordingId: string) => [...recordingKeys.detail(recordingId), 'session'] as const,
  timeline: (recordingId: string) => [...recordingKeys.detail(recordingId), 'timeline'] as const,
}
