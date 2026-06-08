import { beforeEach, describe, expect, it } from 'vitest'

import { initializeTheme, setThemePreference, theme } from '../useTheme'

describe('theme', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: () => ({
        matches: false,
        media: '(prefers-color-scheme: dark)',
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }),
    })
    window.localStorage.clear()
    document.documentElement.dataset.theme = ''
  })

  it('applies explicit preference and persists it', () => {
    initializeTheme()
    setThemePreference('dark')

    expect(theme.value).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(window.localStorage.getItem('munk-ui-theme')).toBe('dark')
  })
})
