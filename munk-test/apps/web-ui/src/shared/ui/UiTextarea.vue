<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
})

withDefaults(defineProps<{
  placeholder?: string
  rows?: number
  disabled?: boolean
}>(), {
  placeholder: '',
  rows: 6,
  disabled: false,
})

const model = defineModel<string>({ default: '' })
</script>

<template>
  <textarea
    v-model="model"
    v-bind="$attrs"
    :placeholder="placeholder"
    :rows="rows"
    :disabled="disabled"
    class="min-h-32 w-full rounded-xl border border-border bg-surface-default px-3.5 py-3 text-sm text-text-primary shadow-sm outline-none transition-all duration-150 placeholder:text-text-muted hover:border-border-strong focus:border-accent focus:shadow-glow disabled:cursor-not-allowed disabled:opacity-60"
  />
</template>
