<script setup lang="ts">
import { Plus, Trash2 } from '@lucide/vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import StringMapEditor from '@/shared/components/StringMapEditor.vue'
import UiButton from '@/shared/ui/UiButton.vue'
import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'

import {
  createEmptyCommandSetupStepForm,
  createEmptyHttpSetupStepForm,
  httpMethodSupportsBody,
  type CommandSetupStepForm,
  type HttpMethod,
  type HttpSetupStepForm,
  type SetupStepForm,
  type SetupStepKind,
} from '../setupStepForm'

const props = withDefaults(defineProps<{
  baseOptions: Array<{ value: string; label: string }>
  execOptions: Array<{ value: string; label: string }>
  disabled?: boolean
}>(), {
  disabled: false,
})

const model = defineModel<SetupStepForm[]>({ required: true })

const { t } = useI18n()

const kindOptions = computed(() => [
  { value: 'http', label: t('caseDetail.setup.kindHttp') },
  { value: 'command', label: t('caseDetail.setup.kindCommand') },
])

const methodOptions = computed(() => (
  ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'] as HttpMethod[]
).map((method) => ({ value: method, label: method })))

const hasBaseOptions = computed(() => props.baseOptions.length > 0)
const hasExecOptions = computed(() => props.execOptions.length > 0)

function stepSupportsBody(step: SetupStepForm): boolean {
  return step.kind === 'http' && httpMethodSupportsBody(step.method)
}

function addStep() {
  model.value = [...model.value, createEmptyHttpSetupStepForm()]
}

function removeStep(index: number) {
  model.value = model.value.filter((_, itemIndex) => itemIndex !== index)
}

function updateKind(index: number, kind: SetupStepKind) {
  model.value = model.value.map((step, itemIndex) => {
    if (itemIndex !== index) {
      return step
    }
    if (kind === 'http') {
      return createEmptyHttpSetupStepForm()
    }
    return createEmptyCommandSetupStepForm()
  })
}

function updateHttpStep<K extends keyof HttpSetupStepForm>(
  index: number,
  key: K,
  value: HttpSetupStepForm[K],
) {
  model.value = model.value.map((step, itemIndex) => {
    if (itemIndex !== index || step.kind !== 'http') {
      return step
    }
    return { ...step, [key]: value }
  })
}

function updateCommandStep<K extends keyof CommandSetupStepForm>(
  index: number,
  key: K,
  value: CommandSetupStepForm[K],
) {
  model.value = model.value.map((step, itemIndex) => {
    if (itemIndex !== index || step.kind !== 'command') {
      return step
    }
    return { ...step, [key]: value }
  })
}
</script>

<template>
  <div class="grid gap-4">
    <p v-if="!hasBaseOptions && !hasExecOptions" class="text-sm text-text-secondary">
      {{ t('caseDetail.setup.settingsMissingHint') }}
    </p>

    <div v-if="model.length === 0" class="text-sm text-text-secondary">
      {{ t('caseDetail.setup.empty') }}
    </div>

    <div
      v-for="(step, index) in model"
      :key="`setup-step-${index}`"
      class="grid gap-4 rounded-2xl border border-border bg-surface-muted/20 p-4"
    >
      <div class="flex items-center justify-between gap-3">
        <h4 class="text-sm font-medium text-text-primary">
          {{ t('caseDetail.setup.stepTitle', { index: index + 1 }) }}
        </h4>
        <UiButton
          type="button"
          variant="ghost"
          :disabled="disabled"
          :aria-label="t('caseDetail.setup.removeStep')"
          @click="removeStep(index)"
        >
          <Trash2 class="h-4 w-4" />
        </UiButton>
      </div>

      <UiField :label="t('caseDetail.setup.fields.kind')">
        <UiSelect
          :model-value="step.kind"
          :options="kindOptions"
          :disabled="disabled"
          @update:model-value="updateKind(index, $event as SetupStepKind)"
        />
      </UiField>

      <template v-if="step.kind === 'http'">
        <UiField :label="t('caseDetail.setup.fields.base')" required>
          <UiSelect
            :model-value="step.base"
            :options="baseOptions"
            :placeholder="t('caseDetail.setup.placeholders.base')"
            :disabled="disabled || !hasBaseOptions"
            @update:model-value="updateHttpStep(index, 'base', $event)"
          />
        </UiField>
        <div class="grid gap-4 md:grid-cols-2">
          <UiField :label="t('caseDetail.setup.fields.method')">
            <UiSelect
              :model-value="step.method"
              :options="methodOptions"
              :disabled="disabled"
              @update:model-value="updateHttpStep(index, 'method', $event as HttpMethod)"
            />
          </UiField>
          <UiField :label="t('caseDetail.setup.fields.path')">
            <UiInput
              :model-value="step.path"
              :disabled="disabled"
              @update:model-value="updateHttpStep(index, 'path', $event)"
            />
          </UiField>
        </div>
        <UiField
          :label="t('caseDetail.setup.fields.headers')"
          optional
          :description="t('caseDetail.setup.fieldDescriptions.headers')"
        >
          <StringMapEditor
            :model-value="step.headers"
            :disabled="disabled"
            :key-placeholder="t('caseDetail.setup.placeholders.headerKey')"
            :value-placeholder="t('caseDetail.setup.placeholders.headerValue')"
            @update:model-value="updateHttpStep(index, 'headers', $event)"
          />
        </UiField>
        <UiField
          :label="t('caseDetail.setup.fields.query')"
          optional
          :description="t('caseDetail.setup.fieldDescriptions.query')"
        >
          <StringMapEditor
            :model-value="step.query"
            :disabled="disabled"
            :key-placeholder="t('caseDetail.setup.placeholders.queryKey')"
            :value-placeholder="t('caseDetail.setup.placeholders.queryValue')"
            @update:model-value="updateHttpStep(index, 'query', $event)"
          />
        </UiField>
        <UiField
          v-if="stepSupportsBody(step)"
          :label="t('caseDetail.setup.fields.body')"
          optional
          :description="t('caseDetail.setup.fieldDescriptions.body')"
        >
          <UiTextarea
            :model-value="step.body_json"
            :rows="5"
            :disabled="disabled"
            @update:model-value="updateHttpStep(index, 'body_json', $event)"
          />
        </UiField>
        <UiField :label="t('caseDetail.setup.fields.expectedStatus')">
          <UiInput
            :model-value="step.expected_status_text"
            :disabled="disabled"
            @update:model-value="updateHttpStep(index, 'expected_status_text', $event)"
          />
        </UiField>
      </template>

      <template v-else>
        <UiField :label="t('caseDetail.setup.fields.exec')" required>
          <UiSelect
            :model-value="step.exec"
            :options="execOptions"
            :placeholder="t('caseDetail.setup.placeholders.exec')"
            :disabled="disabled || !hasExecOptions"
            @update:model-value="updateCommandStep(index, 'exec', $event)"
          />
        </UiField>
        <UiField :label="t('caseDetail.setup.fields.args')" optional>
          <UiTextarea
            :model-value="step.args_text"
            :rows="4"
            :disabled="disabled"
            @update:model-value="updateCommandStep(index, 'args_text', $event)"
          />
        </UiField>
        <UiField :label="t('caseDetail.setup.fields.expectedExitCode')">
          <UiInput
            :model-value="step.expected_exit_code"
            type="number"
            :disabled="disabled"
            @update:model-value="updateCommandStep(index, 'expected_exit_code', $event)"
          />
        </UiField>
      </template>
    </div>

    <UiButton type="button" variant="secondary" :disabled="disabled" @click="addStep">
      <Plus class="h-4 w-4" />
      {{ t('caseDetail.setup.addStep') }}
    </UiButton>
  </div>
</template>
