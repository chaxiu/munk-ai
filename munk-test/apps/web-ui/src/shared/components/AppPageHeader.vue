<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <header class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
    <div class="grid gap-2.5">
      <h1 class="text-[2rem] font-semibold tracking-tight text-text-primary">{{ title }}</h1>
      <p v-if="description" class="max-w-3xl text-sm leading-6 text-text-secondary">{{ description }}</p>
    </div>
    <div v-if="$slots.default" class="flex flex-wrap items-center gap-2.5 lg:justify-end">
      <slot />
    </div>
  </header>
</template>
