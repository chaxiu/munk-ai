<script setup lang="ts">
import { Check, ChevronDown } from '@lucide/vue'
import {
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectItemIndicator,
  SelectItemText,
  SelectLabel,
  SelectPortal,
  SelectRoot,
  SelectTrigger,
  SelectValue,
  SelectViewport,
} from 'radix-vue'

type UiSelectOption = {
  label: string
  value: string
  disabled?: boolean
}

type UiSelectGroup = {
  label: string
  options: UiSelectOption[]
}

withDefaults(defineProps<{
  options: Array<UiSelectOption | UiSelectGroup>
  placeholder?: string
  disabled?: boolean
}>(), {
  placeholder: '',
  disabled: false,
})

const model = defineModel<string>({ default: '' })

function isGroup(option: UiSelectOption | UiSelectGroup): option is UiSelectGroup {
  return 'options' in option
}
</script>

<template>
  <div class="relative">
    <select
      v-model="model"
      :disabled="disabled"
      class="absolute inset-0 h-full w-full opacity-0 pointer-events-none"
      tabindex="-1"
      aria-hidden="true"
    >
      <option value="">{{ placeholder }}</option>
      <template v-for="option in options" :key="isGroup(option) ? option.label : option.value">
        <optgroup v-if="isGroup(option)" :label="option.label">
          <option v-for="item in option.options" :key="item.value" :value="item.value" :disabled="item.disabled">
            {{ item.label }}
          </option>
        </optgroup>
        <option v-else :value="option.value" :disabled="option.disabled">
          {{ option.label }}
        </option>
      </template>
    </select>

    <SelectRoot v-model="model" :disabled="disabled">
    <SelectTrigger
      class="inline-flex min-h-11 w-full items-center justify-between gap-2 rounded-xl border border-border bg-surface-default px-3.5 py-2 text-left text-sm text-text-primary shadow-sm outline-none transition-all duration-150 hover:border-border-strong data-[placeholder]:text-text-muted data-[state=open]:border-accent data-[state=open]:shadow-glow disabled:cursor-not-allowed disabled:opacity-60"
      aria-label="select"
    >
      <SelectValue :placeholder="placeholder" class="min-w-0 flex-1 truncate whitespace-nowrap" />
      <ChevronDown class="h-4 w-4 shrink-0 text-text-muted" />
    </SelectTrigger>

    <SelectPortal>
      <SelectContent
        position="popper"
        :side-offset="8"
        class="z-[90] min-w-[var(--radix-select-trigger-width)] max-h-[min(20rem,var(--radix-select-content-available-height))] overflow-hidden rounded-xl border border-border bg-surface-elevated p-1.5 shadow-panel"
      >
        <SelectViewport class="grid max-h-[min(20rem,var(--radix-select-content-available-height))] gap-1 overflow-y-auto overscroll-contain">
          <template v-for="option in options" :key="isGroup(option) ? option.label : option.value">
            <SelectGroup v-if="isGroup(option)">
              <SelectLabel class="px-2 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">
                {{ option.label }}
              </SelectLabel>
              <SelectItem
                v-for="item in option.options"
                :key="item.value"
                :value="item.value"
                :disabled="item.disabled"
                class="relative flex min-h-8 select-none items-center rounded-md px-8 py-1.5 text-[13px] text-text-primary outline-none transition-colors data-[disabled]:pointer-events-none data-[disabled]:opacity-40 data-[highlighted]:bg-accent-soft data-[highlighted]:text-text-primary"
              >
                <span class="absolute left-2 inline-flex h-4 w-4 items-center justify-center">
                  <SelectItemIndicator>
                    <Check class="h-4 w-4 text-accent" />
                  </SelectItemIndicator>
                </span>
                <SelectItemText class="truncate whitespace-nowrap">{{ item.label }}</SelectItemText>
              </SelectItem>
            </SelectGroup>

            <SelectItem
              v-else
              :value="option.value"
              :disabled="option.disabled"
              class="relative flex min-h-8 select-none items-center rounded-md px-8 py-1.5 text-[13px] text-text-primary outline-none transition-colors data-[disabled]:pointer-events-none data-[disabled]:opacity-40 data-[highlighted]:bg-accent-soft data-[highlighted]:text-text-primary"
            >
              <span class="absolute left-2 inline-flex h-4 w-4 items-center justify-center">
                <SelectItemIndicator>
                  <Check class="h-4 w-4 text-accent" />
                </SelectItemIndicator>
              </span>
              <SelectItemText class="truncate whitespace-nowrap">{{ option.label }}</SelectItemText>
            </SelectItem>
          </template>
        </SelectViewport>
      </SelectContent>
    </SelectPortal>
    </SelectRoot>
  </div>
</template>
