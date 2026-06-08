import { computed, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import DevicesPage from '../pages/DevicesPage.vue'
import { setLocale, i18n } from '@/shared/i18n'

const devicesState = ref([
  {
    platform: 'ios',
    device_ref: 'sim-1',
    display_name: 'iPhone 16',
    kind: 'simulator',
    availability: 'available',
    is_booted: true,
    raw: { model: 'iPhone 16 Pro', os_version: '18.0' },
  },
  {
    platform: 'android',
    device_ref: 'emulator-5554',
    display_name: 'Pixel',
    kind: 'emulator',
    availability: 'busy',
    is_booted: false,
    raw: { model: 'Pixel 9' },
  },
])

vi.mock('../queries/useDevicesQuery', () => ({
  useDevicesQuery: (platform: { value: string }) => ({
    data: computed(() => devicesState.value.filter((item) => platform.value === 'all' || item.platform === platform.value)),
    isFetching: ref(false),
    error: ref(null),
    refetch: async () => ({ data: devicesState.value }),
  }),
}))

describe('DevicesPage', () => {
  beforeEach(() => {
    setLocale('en-US')
    devicesState.value = [
      {
        platform: 'ios',
        device_ref: 'sim-1',
        display_name: 'iPhone 16',
        kind: 'simulator',
        availability: 'available',
        is_booted: true,
        raw: { model: 'iPhone 16 Pro', os_version: '18.0' },
      },
      {
        platform: 'android',
        device_ref: 'emulator-5554',
        display_name: 'Pixel',
        kind: 'emulator',
        availability: 'busy',
        is_booted: false,
        raw: { model: 'Pixel 9' },
      },
    ]
  })

  it('renders devices and supports platform filtering', async () => {
    const wrapper = mount(DevicesPage, {
      global: {
        plugins: [i18n],
        stubs: ['RouterLink'],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('iPhone 16')
    expect(wrapper.text()).toContain('Pixel')

    const buttons = wrapper.findAll('button')
    await buttons[2]!.trigger('click')

    expect(wrapper.text()).toContain('iPhone 16')
    expect(wrapper.text()).not.toContain('Pixel')
  })

  it('renders empty state when filtered result is empty', async () => {
    devicesState.value = []

    const wrapper = mount(DevicesPage, {
      global: {
        plugins: [i18n],
        stubs: ['RouterLink'],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('No devices available')
  })
})
