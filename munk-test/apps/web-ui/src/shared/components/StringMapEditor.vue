<script setup lang="ts">
import { Plus, Trash2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { createEmptyStringMapEntry, type StringMapEntry } from '@/shared/lib/stringMapForm'
import UiButton from '@/shared/ui/UiButton.vue'
import UiInput from '@/shared/ui/UiInput.vue'

withDefaults(defineProps<{
  disabled?: boolean
  keyPlaceholder?: string
  valuePlaceholder?: string
}>(), {
  disabled: false,
  keyPlaceholder: '',
  valuePlaceholder: '',
})

const model = defineModel<StringMapEntry[]>({ required: true })

const { t } = useI18n()

function addEntry() {
  model.value = [...model.value, createEmptyStringMapEntry()]
}

function removeEntry(index: number) {
  model.value = model.value.filter((_, itemIndex) => itemIndex !== index)
}

function updateEntry<K extends keyof StringMapEntry>(
  index: number,
  key: K,
  value: StringMapEntry[K],
) {
  model.value = model.value.map((entry, itemIndex) => (
    itemIndex === index ? { ...entry, [key]: value } : entry
  ))
}
</script>

<template>
  <div class="grid gap-3">
    <div v-if="model.length === 0" class="text-sm text-text-secondary">
      {{ t('stringMap.empty') }}
    </div>

    <div
      v-for="(entry, index) in model"
      :key="`string-map-${index}`"
      class="grid gap-3 rounded-xl border border-border bg-surface/60 p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] md:items-center"
    >
      <UiInput
        :model-value="entry.key"
        :placeholder="keyPlaceholder || t('stringMap.keyPlaceholder')"
        :disabled="disabled"
        @update:model-value="updateEntry(index, 'key', $event)"
      />
      <UiInput
        :model-value="entry.value"
        :placeholder="valuePlaceholder || t('stringMap.valuePlaceholder')"
        :disabled="disabled"
        @update:model-value="updateEntry(index, 'value', $event)"
      />
      <UiButton
        type="button"
        variant="ghost"
        :disabled="disabled"
        :aria-label="t('stringMap.removeEntry')"
        @click="removeEntry(index)"
      >
        <Trash2 class="h-4 w-4" />
      </UiButton>
    </div>

    <UiButton type="button" variant="secondary" :disabled="disabled" @click="addEntry">
      <Plus class="h-4 w-4" />
      {{ t('stringMap.addEntry') }}
    </UiButton>
  </div>
</template>
