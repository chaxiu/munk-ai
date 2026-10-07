export const deviceKeys = {
  all: ['devices'] as const,
  list: (platform: string) => [...deviceKeys.all, 'list', platform] as const,
}
