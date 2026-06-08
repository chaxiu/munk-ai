import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import SettingsPage from '../pages/SettingsPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const refetchMock = typedViFn(async () => undefined)
const updateSettingsConfigMock = typedViFn()

const settingsData = ref({
  config_path: '/Users/demo/project/.munk/config.yaml',
  file_exists: true,
  provider: 'openai_compatible' as const,
  openai_compatible: {
    configured: true,
    base_url: 'https://openrouter.ai/api/v1/',
    api_key: null,
    api_key_configured: true,
    model: 'google/gemma-4-26b-a4b-it',
    timeout_sec: 300,
    extra_headers: {},
    output_strategy: 'prompted' as const,
    thinking: false,
  },
  gemini: {
    configured: true,
    model: 'gemini-3-flash-preview',
    api_key: null,
    api_key_configured: true,
    vertexai: true,
    project: 'legacy-project',
    location: 'us-central1',
    base_url: 'https://legacy-gateway.example.com',
    timeout_sec: 45,
  },
  agents: {
    plan: { enabled: false, provider: null, openai_compatible: { configured: false, base_url: null, api_key: null, api_key_configured: false, model: null, timeout_sec: null, extra_headers: {}, output_strategy: 'auto', thinking: null }, gemini: { configured: false, model: null, api_key: null, api_key_configured: false, vertexai: false, project: null, location: null, base_url: null, timeout_sec: null } },
    runner: { enabled: false, provider: null, openai_compatible: { configured: false, base_url: null, api_key: null, api_key_configured: false, model: null, timeout_sec: null, extra_headers: {}, output_strategy: 'auto', thinking: null }, gemini: { configured: false, model: null, api_key: null, api_key_configured: false, vertexai: false, project: null, location: null, base_url: null, timeout_sec: null } },
    judge: { enabled: true, provider: 'gemini', openai_compatible: { configured: false, base_url: null, api_key: null, api_key_configured: false, model: null, timeout_sec: null, extra_headers: {}, output_strategy: 'auto', thinking: null }, gemini: { configured: true, model: 'gemini-2.5-pro', api_key: null, api_key_configured: true, vertexai: false, project: null, location: null, base_url: null, timeout_sec: 120 } },
    review: { enabled: false, provider: null, openai_compatible: { configured: false, base_url: null, api_key: null, api_key_configured: false, model: null, timeout_sec: null, extra_headers: {}, output_strategy: 'auto', thinking: null }, gemini: { configured: false, model: null, api_key: null, api_key_configured: false, vertexai: false, project: null, location: null, base_url: null, timeout_sec: null } },
    analysis: { enabled: false, provider: null, openai_compatible: { configured: false, base_url: null, api_key: null, api_key_configured: false, model: null, timeout_sec: null, extra_headers: {}, output_strategy: 'auto', thinking: null }, gemini: { configured: false, model: null, api_key: null, api_key_configured: false, vertexai: false, project: null, location: null, base_url: null, timeout_sec: null } },
  },
  proxy: {
    enabled: true,
    url: 'http://127.0.0.1:7890',
    no_proxy: ['internal.example.com'],
  },
  runtime: {
    max_tokens: 8192,
    temperature: 0.2,
    max_steps: 30,
    max_seconds: 300,
    interval: 0.5,
    settle_timeout: null,
    max_side: 1024,
    vl_max_side: 768,
    icon_conf: 0.12,
  },
  orchestration: {
    max_retry_attempts: 2,
    allow_retry_on_failed: false,
    allow_retry_on_inconclusive: true,
    escalate_after_max_attempts: true,
  },
})

vi.mock('@/features/settings/queries/useSettingsConfigQuery', () => ({
  useSettingsConfigQuery: () => ({
    data: computed(() => settingsData.value),
    error: ref(null),
    isFetching: ref(false),
    refetch: refetchMock,
  }),
}))

vi.mock('@/features/settings/queries/useSettingsConfigMutation', () => ({
  useSettingsConfigMutation: () => ({
    isPending: ref(false),
    mutateAsync: updateSettingsConfigMock,
  }),
}))

describe('SettingsPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    refetchMock.mockReset()
    updateSettingsConfigMock.mockReset()
    updateSettingsConfigMock.mockResolvedValue(settingsData.value)
  })

  it('renders the active config path and keeps Gemini advanced fields hidden by default', async () => {
    const wrapper = mount(SettingsPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Settings')
    expect(wrapper.text()).toContain('/Users/demo/project/.munk/config.yaml')
    expect(wrapper.text()).toContain('Show details')
    const detailButtons = wrapper.findAll('button').filter((node) => node.text().includes('Show details'))
    await detailButtons[1]?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Already configured. Leave blank to keep the current value.')
    expect(wrapper.text()).toContain('gemini-3-flash-preview')
    expect(wrapper.text()).toContain('API key saved')
    expect(wrapper.text()).toContain('structured output: prompted')
    expect(wrapper.text()).toContain('thinking: disabled')
    expect(wrapper.text()).toContain('Show advanced')
    expect(wrapper.text()).not.toContain('Vertex AI')
    expect(wrapper.text()).not.toContain('legacy-project')
    expect(
      wrapper.findAll('input').some((node) => (node.element as HTMLInputElement).value === 'https://legacy-gateway.example.com'),
    ).toBe(false)
    await wrapper.findAll('button').find((node) => node.text().includes('Show advanced'))?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Advanced settings')
    expect(
      wrapper.findAll('input').some((node) => (node.element as HTMLInputElement).value === 'https://legacy-gateway.example.com'),
    ).toBe(true)
    expect(wrapper.text()).toContain('Proxy')
    expect(wrapper.text()).toContain('Use proxy for external requests')
    expect(wrapper.text()).toContain('Orchestration')
    expect(wrapper.text()).toContain('max_retry_attempts')
    expect(wrapper.text()).toContain('allow_retry_on_failed')
    expect(wrapper.text()).toContain('allow_retry_on_inconclusive')
    expect(wrapper.text()).toContain('escalate_after_max_attempts')
  })

  it('submits the current config shape when saving', async () => {
    const wrapper = mount(SettingsPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(updateSettingsConfigMock).toHaveBeenCalledTimes(1)
    expect(updateSettingsConfigMock).toHaveBeenCalledWith(expect.objectContaining({
      provider: 'openai_compatible',
      openai_compatible: expect.objectContaining({
        configured: true,
        base_url: 'https://openrouter.ai/api/v1/',
        api_key: null,
        api_key_configured: true,
        output_strategy: 'prompted',
        thinking: false,
      }),
      gemini: expect.objectContaining({
        configured: true,
        model: 'gemini-3-flash-preview',
        api_key: null,
        api_key_configured: true,
        vertexai: true,
        project: 'legacy-project',
        location: 'us-central1',
        base_url: 'https://legacy-gateway.example.com',
        timeout_sec: 45,
      }),
      agents: expect.objectContaining({
        judge: expect.objectContaining({
          enabled: true,
          provider: 'gemini',
          gemini: expect.objectContaining({
            configured: true,
            model: 'gemini-2.5-pro',
            api_key: null,
            api_key_configured: true,
          }),
        }),
      }),
      proxy: {
        enabled: true,
        url: 'http://127.0.0.1:7890',
        no_proxy: ['internal.example.com'],
      },
      orchestration: {
        max_retry_attempts: 2,
        allow_retry_on_failed: false,
        allow_retry_on_inconclusive: true,
        escalate_after_max_attempts: true,
      },
    }))
    expect(wrapper.text()).toContain('Settings saved to the active config.')
  })
})
