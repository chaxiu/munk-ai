import { beforeEach, describe, expect, it } from 'vitest'

import { i18n, setLocale } from '../index'
import { translateErrorCode } from '../errorMessages'

describe('i18n', () => {
  beforeEach(() => {
    setLocale('en-US')
  })

  it('translates known error codes and falls back for unknown ones', () => {
    expect(translateErrorCode('recording_ui_unavailable', '')).toBe('Recording UI build output is missing.')
    expect(
      translateErrorCode(
        'app_validation_failed',
        'app knowledge document app_id mismatch: expected com.immomo.momo, got momo',
      ),
    ).toBe(
      'App configuration is invalid. app knowledge document app_id mismatch: expected com.immomo.momo, got momo',
    )
    expect(translateErrorCode('unknown_code', 'fallback')).toBe('fallback')
  })

  it('switches locale for shell messages', () => {
    setLocale('zh-CN')
    expect(i18n.global.t('nav.dashboard')).toBe('首页看板')
  })
})
