<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  title: string
  description: string
  icon?: Component
}>()
</script>

<template>
  <section class="grid gap-3 rounded-xl border border-dashed border-border-strong bg-surface-muted px-6 py-8 text-left">
    <component :is="icon" v-if="icon" class="h-5 w-5 text-text-muted" />
    <h2 class="text-base font-semibold text-text-primary">{{ title }}</h2>
    <p class="max-w-2xl text-sm leading-6 text-text-secondary">{{ description }}</p>
    <div v-if="$slots.actions" class="flex flex-wrap items-center gap-3 pt-2">
      <slot name="actions" />
    </div>
  </section>
</template>
