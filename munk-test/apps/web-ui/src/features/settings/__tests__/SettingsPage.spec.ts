import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import SettingsPage from '../pages/SettingsPage.vue'
import { i18n, setLocale } from '@/shared/i18n'

const refetchMock = typedViFn(async () => undefined)
const updateSettingsConfigMock = typedViFn()

function createSettingsData() {
  return {
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
  ios_bridge: {
    sudo_enabled: true,
    sudo_password: null,
    sudo_password_configured: true,
  },
  test_env: {
    bases: {
      test_backend: {
        url: 'http://127.0.0.1:8080',
        headers: { Authorization: 'Bearer token' },
      },
    },
    allowed_exec: ['echo'],
  },
  runtime: {
    max_tokens: 8192,
    temperature: 0.2,
    max_steps: 30,
    max_seconds: 300,
    interval: 0.5,
    settle_timeout: null,
    settle_mode: 'ratio' as const,
    settle_ratio_threshold: 0.3,
    settle_delay_sec: 0.8,
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
  }
}

const settingsData = ref(createSettingsData())

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
    settingsData.value = createSettingsData()
    refetchMock.mockReset()
    updateSettingsConfigMock.mockReset()
    updateSettingsConfigMock.mockResolvedValue(settingsData.value)
  })

  it('renders the active config path and reveals provider descriptions on demand', async () => {
    const wrapper = mount(SettingsPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Settings')
    expect(wrapper.text()).toContain('/Users/demo/project/.munk/config.yaml')

    const providerDetailButtons = () => wrapper.findAll('button').filter((node) => node.text().includes('Show details'))

    await providerDetailButtons()[0]?.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Base URL')
    expect(wrapper.text()).toContain('google/gemma-4-26b-a4b-it')
    expect(wrapper.text()).toContain('API key saved')
    expect(wrapper.text()).toContain('structured output: prompted')
    expect(wrapper.text()).toContain('thinking: disabled')
    expect(wrapper.text()).not.toContain('If a value is already configured, leaving this blank keeps the current value.')

    await wrapper.findAll('button').find((node) => node.attributes('title') === 'API Key')?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('If a value is already configured, leaving this blank keeps the current value.')

    await providerDetailButtons()[0]?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('gemini-3-flash-preview')
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
    expect(wrapper.text()).toContain('Role override')
    expect(wrapper.text()).toContain('iOS Bridge')
    expect(wrapper.text()).toContain('Enable sudo startup')
    expect(wrapper.text()).toContain('Orchestration')
    expect(wrapper.text()).toContain('max_retry_attempts')
    expect(wrapper.text()).toContain('allow_retry_on_failed')
    expect(wrapper.text()).toContain('allow_retry_on_inconclusive')
    expect(wrapper.text()).toContain('escalate_after_max_attempts')
    expect(wrapper.text()).toContain('settle_mode')
    expect(wrapper.text()).toContain('settle_ratio_threshold')
    expect(wrapper.text()).toContain('settle_delay_sec')
  })

  it('disables save until proxy and iOS bridge required fields are filled', async () => {
    settingsData.value = {
      ...createSettingsData(),
      proxy: {
        enabled: true,
        url: '',
        no_proxy: [],
      },
      ios_bridge: {
        sudo_enabled: true,
        sudo_password: null,
        sudo_password_configured: false,
      },
    }

    const wrapper = mount(SettingsPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    const saveButton = wrapper.find('.primary-button')
    expect(saveButton.attributes('disabled')).toBeDefined()

    await wrapper.find('input[placeholder="http://127.0.0.1:7890"]').setValue('http://127.0.0.1:7890')
    await wrapper.find('input[placeholder="Enter the local sudo password"]').setValue('secret-pass')
    await flushPromises()

    expect(saveButton.attributes('disabled')).toBeUndefined()
  })

  it('uses the shared provider-required rules for enabled agent overrides', async () => {
    settingsData.value = {
      ...createSettingsData(),
      agents: {
        ...createSettingsData().agents,
        judge: {
          ...createSettingsData().agents.judge,
          enabled: true,
          provider: 'gemini',
          gemini: {
            ...createSettingsData().agents.judge.gemini,
            model: '',
          },
        },
      },
    }

    const wrapper = mount(SettingsPage, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.find('.primary-button').attributes('disabled')).toBeDefined()
  })

  it('submits the current config shape when saving', async () => {
    settingsData.value = {
      ...settingsData.value,
      openai_compatible: {
        ...settingsData.value.openai_compatible,
        configured: false,
      },
      agents: {
        ...settingsData.value.agents,
        judge: {
          ...settingsData.value.agents.judge,
          gemini: {
            ...settingsData.value.agents.judge.gemini,
            configured: false,
          },
        },
      },
    }
    updateSettingsConfigMock.mockResolvedValue(settingsData.value)

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
      ios_bridge: {
        sudo_enabled: true,
        sudo_password: null,
        sudo_password_configured: true,
      },
      test_env: {
        bases: {
          test_backend: {
            url: 'http://127.0.0.1:8080',
            headers: { Authorization: 'Bearer token' },
          },
        },
        allowed_exec: ['echo'],
      },
      orchestration: {
        max_retry_attempts: 2,
        allow_retry_on_failed: false,
        allow_retry_on_inconclusive: true,
        escalate_after_max_attempts: true,
      },
      runtime: expect.objectContaining({
        settle_mode: 'ratio',
        settle_ratio_threshold: 0.3,
        settle_delay_sec: 0.8,
      }),
    }))
    expect(wrapper.text()).toContain('Settings saved to the active config.')
  })
})
