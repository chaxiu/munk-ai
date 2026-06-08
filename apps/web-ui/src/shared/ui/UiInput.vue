<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
})

withDefaults(defineProps<{
  type?: string
  placeholder?: string
  disabled?: boolean
}>(), {
  type: 'text',
  placeholder: '',
  disabled: false,
})

const model = defineModel<string>({ default: '' })
</script>

<template>
  <input
    v-model="model"
    v-bind="$attrs"
    :type="type"
    :placeholder="placeholder"
    :disabled="disabled"
    class="min-h-11 w-full rounded-xl border border-border bg-surface-default px-3.5 py-2 text-sm text-text-primary shadow-sm outline-none transition-all duration-150 placeholder:text-text-muted hover:border-border-strong focus:border-accent focus:shadow-glow disabled:cursor-not-allowed disabled:opacity-60"
  >
</template>
