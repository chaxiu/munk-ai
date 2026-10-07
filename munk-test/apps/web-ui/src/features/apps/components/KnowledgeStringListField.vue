<script setup lang="ts">
import { Plus, Trash2 } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import UiButton from '@/shared/ui/UiButton.vue'
import UiInput from '@/shared/ui/UiInput.vue'

const props = withDefaults(defineProps<{
  disabled?: boolean
  placeholder?: string
}>(), {
  disabled: false,
  placeholder: '',
})

const model = defineModel<string[]>({ required: true })

const { t } = useI18n()

function addItem() {
  model.value = [...model.value, '']
}

function updateItem(index: number, value: string) {
  model.value = model.value.map((item, itemIndex) => (itemIndex === index ? value : item))
}

function removeItem(index: number) {
  model.value = model.value.filter((_, itemIndex) => itemIndex !== index)
}
</script>

<template>
  <div class="grid gap-3">
    <div
      v-for="(item, index) in model"
      :key="`${index}-${item}`"
      class="flex items-start gap-2"
    >
      <UiInput
        :model-value="item"
        :disabled="props.disabled"
        :placeholder="props.placeholder"
        @update:model-value="updateItem(index, $event)"
      />
      <UiButton
        type="button"
        variant="ghost"
        :disabled="props.disabled"
        :aria-label="t('apps.knowledge.actions.removePayloadItem')"
        @click="removeItem(index)"
      >
        <Trash2 class="h-4 w-4" />
      </UiButton>
    </div>

    <UiButton type="button" variant="secondary" :disabled="props.disabled" @click="addItem">
      <Plus class="h-4 w-4" />
      {{ t('apps.knowledge.actions.addPayloadItem') }}
    </UiButton>
  </div>
</template>
