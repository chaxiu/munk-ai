<script setup lang="ts">
const props = withDefaults(defineProps<{
  tone?: 'neutral' | 'success' | 'error' | 'warning'
}>(), {
  tone: 'neutral',
})
</script>

<template>
  <span class="inline-flex h-6 items-center justify-center rounded-full px-2.5 py-0.5 text-xs font-semibold" :data-tone="props.tone">
    <slot />
  </span>
</template>

<style scoped>
.inline-flex {
  background: var(--surface-muted);
  color: var(--text-secondary);
}

.inline-flex[data-tone='success'] {
  background: var(--status-success-bg);
  color: var(--status-success-text);
}

.inline-flex[data-tone='error'] {
  background: var(--status-error-bg);
  color: var(--status-error-text);
}

.inline-flex[data-tone='warning'] {
  background: var(--status-warning-bg);
  color: var(--status-warning-text);
}
</style>
