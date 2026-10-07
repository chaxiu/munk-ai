import { defineComponent, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { i18n, setLocale } from '@/shared/i18n'
import KnowledgeCardEditor from '../KnowledgeCardEditor.vue'
import { createEmptyKnowledgeCardEditorErrors, createEmptyKnowledgeCardForm } from '../../knowledgeEditor'

vi.mock('@/shared/time/useTime', () => ({
  useTime: () => ({
    tooltip: (value: string) => value,
  }),
}))

const TestHarness = defineComponent({
  components: {
    KnowledgeCardEditor,
  },
  setup() {
    const form = ref(createEmptyKnowledgeCardForm('screen'))
    const formErrors = ref(createEmptyKnowledgeCardEditorErrors())
    const lastEditorMode = ref<string | null>(null)
    const lastCardType = ref<string | null>(null)

    return {
      form,
      formErrors,
      lastEditorMode,
      lastCardType,
      cardTypeOptions: [
        { value: 'screen', label: 'Screen' },
        { value: 'flow', label: 'Flow' },
        { value: 'assertion', label: 'Assertion' },
        { value: 'issue', label: 'Issue' },
        { value: 'data', label: 'Data' },
        { value: 'policy', label: 'Policy' },
        { value: 'domain_term', label: 'Domain Term' },
      ],
      sourceKindOptions: [
        { value: 'manual', label: 'Manual' },
      ],
      statusOptions: [
        { value: 'active', label: 'Active' },
      ],
    }
  },
  template: `
    <KnowledgeCardEditor
      v-model:form="form"
      :selected-card="null"
      :selected-card-error-message="null"
      :is-creating="true"
      :is-fetching="false"
      :is-saving="false"
      :is-deleting="false"
      :action-error="null"
      :action-message="null"
      :form-errors="formErrors"
      :card-type-options="cardTypeOptions"
      :source-kind-options="sourceKindOptions"
      :status-options="statusOptions"
      @save="() => {}"
      @reset="() => {}"
      @delete="() => {}"
      @new-card="() => {}"
      @card-type-change="lastCardType = $event"
      @editor-mode-change="lastEditorMode = $event"
    />
  `,
})

describe('KnowledgeCardEditor', () => {
  beforeEach(() => {
    setLocale('en-US')
  })

  it('renders structured payload fields by default for screen cards', async () => {
    const wrapper = mount(TestHarness, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Entry')
    expect(wrapper.text()).toContain('Recognition')
    expect(wrapper.text()).toContain('Show Advanced JSON')
    expect(wrapper.text()).not.toContain('Enter valid JSON')
  })

  it('emits editor mode changes when toggling advanced json', async () => {
    const wrapper = mount(TestHarness, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()
    await wrapper.findAll('button').find((node) => node.text().includes('Show Advanced JSON'))?.trigger('click')

    expect((wrapper.vm as { lastEditorMode: string | null }).lastEditorMode).toBe('json')
  })

  it('adds and removes structured array items through the nested payload editor', async () => {
    const wrapper = mount(TestHarness, {
      global: {
        plugins: [i18n],
      },
    })

    await flushPromises()

    await wrapper.findAll('button').find((node) => node.text().includes('Add Item'))?.trigger('click')
    await flushPromises()

    expect((wrapper.vm as { form: ReturnType<typeof createEmptyKnowledgeCardForm> }).form.payloadDraft.key_elements).toEqual([''])
    expect(wrapper.find('button[aria-label="Remove Item"]').exists()).toBe(true)

    await wrapper.find('button[aria-label="Remove Item"]').trigger('click')
    await flushPromises()

    expect((wrapper.vm as { form: ReturnType<typeof createEmptyKnowledgeCardForm> }).form.payloadDraft.key_elements).toEqual([])
  })

  it('renders translated field errors for common and payload fields', async () => {
    const wrapper = mount(TestHarness, {
      global: {
        plugins: [i18n],
      },
    })

    ;(wrapper.vm as {
      formErrors: ReturnType<typeof createEmptyKnowledgeCardEditorErrors>
    }).formErrors = {
      title: 'Title is required.',
      confidence: 'Enter a decimal value between 0 and 1.',
      payload: null,
      payloadFields: {
        enter: 'This field is required.',
      },
    }

    await flushPromises()

    expect(wrapper.text()).toContain('Title is required.')
    expect(wrapper.text()).toContain('Enter a decimal value between 0 and 1.')
    expect(wrapper.text()).toContain('This field is required.')
  })
})
