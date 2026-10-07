<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  label: string
  value: string | number
  hint?: string
  icon?: Component
}>()
</script>

<template>
  <section class="overflow-hidden rounded-xl border border-border bg-surface-elevated p-4 shadow-card transition-colors duration-150">
    <div class="flex items-start justify-between gap-4">
      <div class="grid gap-2">
        <span class="text-[11px] font-semibold tracking-[0.16em] text-text-muted">{{ label }}</span>
        <strong class="text-3xl font-semibold tracking-tight text-text-primary">{{ value }}</strong>
      </div>
      <div
        v-if="icon"
        class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border-muted bg-surface-muted text-text-secondary"
      >
        <component :is="icon" class="h-4.5 w-4.5" />
      </div>
    </div>
    <div class="mt-4 h-px w-full bg-border-muted" />
    <div class="mt-3 grid gap-2">
      <span v-if="hint" class="text-sm text-text-secondary">{{ hint }}</span>
    </div>
  </section>
</template>
