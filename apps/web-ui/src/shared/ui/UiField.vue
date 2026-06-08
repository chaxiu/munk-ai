<script setup lang="ts">
defineProps<{
  label: string
  hint?: string
  error?: string | null
}>()
</script>

<template>
  <label class="grid gap-2.5">
    <div class="flex items-center justify-between gap-3">
      <span class="text-sm font-medium text-text-primary">{{ label }}</span>
      <span v-if="hint && !error" class="text-xs text-text-muted">{{ hint }}</span>
    </div>
    <slot />
    <p v-if="error" class="text-sm text-error-text">{{ error }}</p>
  </label>
</template>
