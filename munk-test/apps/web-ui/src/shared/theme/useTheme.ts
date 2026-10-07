import { computed, ref } from 'vue'

export type ThemePreference = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

const STORAGE_KEY = 'munk-ui-theme'

export const themePreference = ref<ThemePreference>('system')
export const theme = ref<ResolvedTheme>('light')

function resolveTheme(preference: ThemePreference): ResolvedTheme {
  if (preference === 'light' || preference === 'dark') {
    return preference
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(resolved: ResolvedTheme): void {
  document.documentElement.dataset.theme = resolved
  theme.value = resolved
}

export function setThemePreference(preference: ThemePreference): void {
  themePreference.value = preference
  window.localStorage.setItem(STORAGE_KEY, preference)
  applyTheme(resolveTheme(preference))
}

export function initializeTheme(): void {
  const saved = window.localStorage.getItem(STORAGE_KEY)
  if (saved === 'light' || saved === 'dark' || saved === 'system') {
    themePreference.value = saved
  }
  applyTheme(resolveTheme(themePreference.value))
}

export function useTheme() {
  return {
    themePreference: computed(() => themePreference.value),
    theme: computed(() => theme.value),
    setThemePreference,
  }
}
