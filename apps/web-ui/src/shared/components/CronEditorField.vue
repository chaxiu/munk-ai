<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import {
  DEFAULT_CRON_TEMPLATE_STATE,
  buildCronFromTemplate,
  computeNextRunPreview,
  describeCronTemplate,
  normalizeCronExpr,
  parseCronTemplate,
  validateCronExpr,
  type CronTemplateMode,
  type CronTemplateState,
} from '@/shared/time/cron'
import { useTime } from '@/shared/time/useTime'
import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiSelect from '@/shared/ui/UiSelect.vue'

const props = withDefaults(defineProps<{
  label?: string
  placeholder?: string
  disabled?: boolean
  timezone?: string
  error?: string | null
}>(), {
  label: '',
  placeholder: '',
  disabled: false,
  timezone: '',
  error: null,
})

const model = defineModel<string>({ default: '' })
const emit = defineEmits<{
  'validation-change': [hasError: boolean]
}>()

const { t } = useI18n()
const time = useTime()
const selectedModeOverride = ref<CronTemplateMode | null>(null)
const syncingFromModel = ref(false)
const editorState = reactive<CronTemplateState>({ ...DEFAULT_CRON_TEMPLATE_STATE })

const resolvedLabel = computed(() => props.label || t('cronEditor.title'))
const resolvedPlaceholder = computed(() => props.placeholder || t('runsCreate.placeholders.cronExpr'))
const modeOptions = computed(() => ([
  { label: t('cronEditor.modes.daily'), value: 'daily' },
  { label: t('cronEditor.modes.weekdays'), value: 'weekdays' },
  { label: t('cronEditor.modes.weekly'), value: 'weekly' },
  { label: t('cronEditor.modes.monthly'), value: 'monthly' },
  { label: t('cronEditor.modes.custom'), value: 'custom' },
]))
const hourOptions = computed(() => (
  Array.from({ length: 24 }, (_, hour) => ({
    label: hour.toString().padStart(2, '0'),
    value: String(hour),
  }))
))
const minuteOptions = computed(() => (
  Array.from({ length: 60 }, (_, minute) => ({
    label: minute.toString().padStart(2, '0'),
    value: String(minute),
  }))
))
const weekdayOptions = computed(() => ([
  { label: t('cronEditor.weekdays.monday'), value: '1' },
  { label: t('cronEditor.weekdays.tuesday'), value: '2' },
  { label: t('cronEditor.weekdays.wednesday'), value: '3' },
  { label: t('cronEditor.weekdays.thursday'), value: '4' },
  { label: t('cronEditor.weekdays.friday'), value: '5' },
  { label: t('cronEditor.weekdays.saturday'), value: '6' },
  { label: t('cronEditor.weekdays.sunday'), value: '0' },
]))
const dayOfMonthOptions = computed(() => (
  Array.from({ length: 31 }, (_, index) => {
    const day = String(index + 1)
    return {
      label: t('cronEditor.dayOfMonthValue', { day }),
      value: day,
    }
  })
))
const currentExpression = computed(() => buildCronFromTemplate(editorState))
const internalErrorCode = computed(() => validateCronExpr(currentExpression.value))
const internalError = computed(() => {
  switch (internalErrorCode.value) {
    case 'required':
      return t('cronEditor.errors.required')
    case 'field_count':
      return t('cronEditor.errors.fieldCount')
    case 'invalid':
      return t('cronEditor.errors.invalid')
    default:
      return ''
  }
})
const displayedError = computed(() => props.error || internalError.value || null)
const summary = computed(() => describeCronTemplate(editorState, {
  daily: (timeLabel) => t('cronEditor.summary.daily', { time: timeLabel }),
  weekdays: (timeLabel) => t('cronEditor.summary.weekdays', { time: timeLabel }),
  weekly: (weekdayLabel, timeLabel) => t('cronEditor.summary.weekly', { weekday: weekdayLabel, time: timeLabel }),
  monthly: (dayLabel, timeLabel) => t('cronEditor.summary.monthly', { day: dayLabel, time: timeLabel }),
  custom: (expression) => t('cronEditor.summary.custom', { expression }),
  weekdayLabels: {
    0: t('cronEditor.weekdays.sunday'),
    1: t('cronEditor.weekdays.monday'),
    2: t('cronEditor.weekdays.tuesday'),
    3: t('cronEditor.weekdays.wednesday'),
    4: t('cronEditor.weekdays.thursday'),
    5: t('cronEditor.weekdays.friday'),
    6: t('cronEditor.weekdays.saturday'),
  },
  dayOfMonth: (day) => t('cronEditor.dayOfMonthValue', { day }),
}))
const effectiveTimezone = computed(() => {
  if (props.timezone) {
    return props.timezone
  }

  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || ''
  } catch {
    return ''
  }
})
const nextRunAt = computed(() => {
  if (!effectiveTimezone.value || internalErrorCode.value) {
    return null
  }
  return computeNextRunPreview(currentExpression.value, effectiveTimezone.value)
})

watch(() => model.value, (value) => {
  const normalizedValue = normalizeCronExpr(value ?? '')
  syncingFromModel.value = true
  if (selectedModeOverride.value === 'custom' && normalizedValue === currentExpression.value) {
    applyEditorState({
      ...editorState,
      mode: 'custom',
      rawExpr: normalizedValue,
    })
  } else {
    const parsedState = parseCronTemplate(value)
    applyEditorState(parsedState)
    if (selectedModeOverride.value && selectedModeOverride.value !== parsedState.mode) {
      selectedModeOverride.value = null
    }
  }
  syncingFromModel.value = false
}, { immediate: true })

watch(
  () => [
    editorState.mode,
    editorState.minute,
    editorState.hour,
    editorState.weekday,
    editorState.dayOfMonth,
    editorState.rawExpr,
  ],
  () => {
    if (syncingFromModel.value) {
      return
    }
    const nextExpression = currentExpression.value
    if (editorState.mode !== 'custom' && editorState.rawExpr !== nextExpression) {
      editorState.rawExpr = nextExpression
    }
    if (model.value !== nextExpression) {
      model.value = nextExpression
    }
  },
)

watch(internalErrorCode, (value) => {
  emit('validation-change', Boolean(value))
}, { immediate: true })

function applyEditorState(nextState: CronTemplateState) {
  editorState.mode = nextState.mode
  editorState.minute = nextState.minute
  editorState.hour = nextState.hour
  editorState.weekday = nextState.weekday
  editorState.dayOfMonth = nextState.dayOfMonth
  editorState.rawExpr = nextState.rawExpr
}

function handleModeChange(value: string) {
  const nextMode = value as CronTemplateMode
  selectedModeOverride.value = nextMode
  editorState.mode = nextMode
  if (editorState.mode === 'custom') {
    editorState.rawExpr = normalizeCronExpr(model.value || editorState.rawExpr)
    return
  }
  editorState.rawExpr = buildCronFromTemplate(editorState)
}
</script>

<template>
  <UiField :label="resolvedLabel" :hint="t('cronEditor.helperText')" :error="displayedError">
    <div class="grid gap-3">
      <div class="grid gap-3 rounded-xl border border-border-muted bg-surface-muted p-4">
        <div class="grid gap-1">
          <p class="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">
            {{ t('cronEditor.templateLabel') }}
          </p>
          <p class="text-sm text-text-secondary">
            {{ t('cronEditor.description') }}
          </p>
        </div>
        <div class="grid gap-3 md:grid-cols-2">
          <div class="grid gap-2 md:col-span-2">
            <span class="text-sm font-medium text-text-primary">{{ t('cronEditor.modeLabel') }}</span>
            <UiSelect
              :model-value="editorState.mode"
              :options="modeOptions"
              :disabled="disabled"
              :placeholder="t('cronEditor.modeLabel')"
              @update:model-value="handleModeChange"
            />
          </div>

          <div v-if="editorState.mode === 'weekly'" class="grid gap-2 md:col-span-2">
            <span class="text-sm font-medium text-text-primary">{{ t('cronEditor.weekdayLabel') }}</span>
            <UiSelect
              v-model="editorState.weekday"
              :options="weekdayOptions"
              :disabled="disabled"
              :placeholder="t('cronEditor.weekdayLabel')"
            />
          </div>

          <div v-if="editorState.mode === 'monthly'" class="grid gap-2 md:col-span-2">
            <span class="text-sm font-medium text-text-primary">{{ t('cronEditor.dayOfMonthLabel') }}</span>
            <UiSelect
              v-model="editorState.dayOfMonth"
              :options="dayOfMonthOptions"
              :disabled="disabled"
              :placeholder="t('cronEditor.dayOfMonthLabel')"
            />
          </div>

          <template v-if="editorState.mode !== 'custom'">
            <div class="grid gap-2">
              <span class="text-sm font-medium text-text-primary">{{ t('cronEditor.hourLabel') }}</span>
              <UiSelect
                v-model="editorState.hour"
                :options="hourOptions"
                :disabled="disabled"
                :placeholder="t('cronEditor.hourLabel')"
              />
            </div>
            <div class="grid gap-2">
              <span class="text-sm font-medium text-text-primary">{{ t('cronEditor.minuteLabel') }}</span>
              <UiSelect
                v-model="editorState.minute"
                :options="minuteOptions"
                :disabled="disabled"
                :placeholder="t('cronEditor.minuteLabel')"
              />
            </div>
          </template>

          <div v-else class="grid gap-2 md:col-span-2">
            <span class="text-sm font-medium text-text-primary">{{ t('cronEditor.rawInputLabel') }}</span>
            <UiInput
              v-model="editorState.rawExpr"
              :placeholder="resolvedPlaceholder"
              :disabled="disabled"
              :aria-label="t('cronEditor.rawInputLabel')"
              autocapitalize="off"
              autocomplete="off"
              spellcheck="false"
            />
            <p class="text-sm text-text-secondary">
              {{ t('cronEditor.rawInputHelp') }}
            </p>
          </div>
        </div>
      </div>

      <div class="grid gap-3 rounded-xl border border-border-muted bg-surface-default p-4">
        <div class="grid gap-1">
          <p class="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">
            {{ t('cronEditor.previewLabel') }}
          </p>
          <p class="text-sm text-text-secondary">
            {{ summary }}
          </p>
        </div>
        <dl class="grid gap-3 sm:grid-cols-3">
          <div class="grid gap-1">
            <dt class="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">
              {{ t('cronEditor.currentExpressionLabel') }}
            </dt>
            <dd class="break-all text-sm text-text-primary">{{ currentExpression }}</dd>
          </div>
          <div class="grid gap-1">
            <dt class="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">
              {{ t('cronEditor.timezoneLabel') }}
            </dt>
            <dd class="text-sm text-text-primary">{{ effectiveTimezone || '-' }}</dd>
          </div>
          <div class="grid gap-1">
            <dt class="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">
              {{ t('cronEditor.nextRunLabel') }}
            </dt>
            <dd class="text-sm text-text-primary">
              {{ nextRunAt ? time.absolute(nextRunAt) : t('cronEditor.nextRunUnavailable') }}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  </UiField>
</template>
