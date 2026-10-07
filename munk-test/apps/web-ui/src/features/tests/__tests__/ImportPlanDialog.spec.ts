import { ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { VueQueryPlugin } from '@tanstack/vue-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { typedViFn } from '@/shared/testing/typedViFn'

import ImportPlanDialog from '../components/ImportPlanDialog.vue'
import { i18n, setLocale } from '@/shared/i18n'
import { queryClient } from '@/shared/query/queryClient'

const pushMock = typedViFn(async () => undefined)
const mutateAsyncMock = typedViFn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}))

vi.mock('@/features/apps/queries/useAppsQuery', () => ({
  useAppsQuery: () => ({
    data: ref([
      {
        app_id: 'demo-app',
        platform: 'android',
        entry_identity: 'com.example.demo',
        introduction_exists: true,
        plan_count: 0,
        case_count: 0,
      },
    ]),
    error: ref(null),
    isFetching: ref(false),
  }),
}))

vi.mock('../queries/usePlanImportMutation', () => ({
  usePlanImportMutation: () => ({
    isPending: ref(false),
    mutateAsync: mutateAsyncMock,
  }),
}))

function buildFile(text: string, name = 'plan.json') {
  return {
    name,
    text: typedViFn(async () => text),
  }
}

describe('ImportPlanDialog', () => {
  beforeEach(() => {
    setLocale('en-US')
    queryClient.clear()
    pushMock.mockReset()
    mutateAsyncMock.mockReset()
  })

  it('validates and submits a plan import request', async () => {
    mutateAsyncMock.mockResolvedValue({ app_id: 'demo-app', plan_id: 'plan-123' })

    const wrapper = mount(ImportPlanDialog, {
      props: {
        open: true,
      },
      global: {
        plugins: [i18n, [VueQueryPlugin, { queryClient }]],
        stubs: {
          Teleport: true,
          UiInput: {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
          UiSelect: {
            props: ['modelValue', 'options'],
            emits: ['update:modelValue'],
            template: '<select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="option in options" :key="option.value" :value="option.value">{{ option.label }}</option></select>',
          },
        },
      },
    })

    const inputs = wrapper.findAll('input')
    await inputs[0]!.setValue('Imported nearby coverage')
    await wrapper.find('select').setValue('demo-app')
    const fileInput = inputs[1]!
    Object.defineProperty(fileInput.element, 'files', {
      value: [
        buildFile(JSON.stringify({
          cases: [
            {
              title: 'Open nearby',
              intent: 'Open nearby page',
              runner_goal: 'Reach nearby page',
            },
          ],
        })),
      ],
      configurable: true,
    })
    await fileInput.trigger('change')
    await flushPromises()

    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(mutateAsyncMock).toHaveBeenCalledWith({
      app_id: 'demo-app',
      name: 'Imported nearby coverage',
      file_name: 'plan.json',
      raw_plan: {
        cases: [
          {
            title: 'Open nearby',
            intent: 'Open nearby page',
            runner_goal: 'Reach nearby page',
          },
        ],
      },
    })
    expect(wrapper.emitted('close')).toBeTruthy()
    expect(pushMock).toHaveBeenCalledWith('/tests/plans/demo-app/plan-123')
  })

  it('shows a front-end validation error for invalid json shape', async () => {
    const wrapper = mount(ImportPlanDialog, {
      props: {
        open: true,
      },
      global: {
        plugins: [i18n, [VueQueryPlugin, { queryClient }]],
        stubs: {
          Teleport: true,
          UiInput: {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
          UiSelect: {
            props: ['modelValue', 'options'],
            emits: ['update:modelValue'],
            template: '<select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="option in options" :key="option.value" :value="option.value">{{ option.label }}</option></select>',
          },
        },
      },
    })

    const fileInput = wrapper.findAll('input')[1]!
    Object.defineProperty(fileInput.element, 'files', {
      value: [buildFile(JSON.stringify({ foo: 'bar' }))],
      configurable: true,
    })
    await fileInput.trigger('change')
    await flushPromises()

    expect(wrapper.text()).toContain('The file is missing required fields')
    expect(mutateAsyncMock).not.toHaveBeenCalled()
  })
})
