<script setup lang="ts">
import { computed } from 'vue'

defineOptions({
  inheritAttrs: false,
})

const props = withDefaults(defineProps<{
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md'
  block?: boolean
}>(), {
  variant: 'secondary',
  size: 'md',
  block: false,
})

const classes = computed(() => {
  const base = 'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl border text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-0 disabled:cursor-not-allowed disabled:opacity-50'
  const size = props.size === 'sm' ? 'min-h-9 px-3.5 text-xs' : 'min-h-10 px-4 text-sm'
  const width = props.block ? 'w-full' : ''

  if (props.variant === 'primary') {
    return `${base} ${size} ${width} primary-button border-accent bg-accent text-white shadow-[0_10px_22px_rgba(37,99,235,0.22)] hover:-translate-y-px hover:border-accent-strong hover:bg-accent-strong`
  }

  if (props.variant === 'danger') {
    return `${base} ${size} ${width} border-error-text/30 bg-error-bg text-error-text shadow-sm hover:-translate-y-px hover:border-error-text/50 hover:bg-error-bg/80`
  }

  if (props.variant === 'ghost') {
    return `${base} ${size} ${width} border-transparent bg-transparent text-text-secondary hover:bg-surface-accent hover:text-text-primary`
  }

  return `${base} ${size} ${width} secondary-button border-border bg-surface-default text-text-primary shadow-sm hover:-translate-y-px hover:border-border-strong hover:bg-surface-muted`
})
</script>

<template>
  <button v-bind="$attrs" :class="classes">
    <slot />
  </button>
</template>
