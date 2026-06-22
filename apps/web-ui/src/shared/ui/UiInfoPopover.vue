<script setup lang="ts">
import { Info } from '@lucide/vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = withDefaults(defineProps<{
  description: string
  label: string
  forceOpen?: boolean
}>(), {
  forceOpen: false,
})

const rootRef = ref<HTMLElement | null>(null)
const isPinned = ref(false)
const isFocused = ref(false)

const popoverId = `ui-info-popover-${Math.random().toString(36).slice(2, 10)}`
const isVisible = computed(() => Boolean(props.description) && (props.forceOpen || isPinned.value || isFocused.value))

function handleDocumentPointerDown(event: PointerEvent) {
  if (!isPinned.value) {
    return
  }
  if (rootRef.value?.contains(event.target as Node)) {
    return
  }
  isPinned.value = false
}

function handleDocumentKeyDown(event: KeyboardEvent) {
  if (event.key !== 'Escape') {
    return
  }
  isPinned.value = false
}

function togglePinned() {
  isPinned.value = !isPinned.value
}

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  document.addEventListener('keydown', handleDocumentKeyDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
  document.removeEventListener('keydown', handleDocumentKeyDown)
})
</script>

<template>
  <span ref="rootRef" class="relative inline-flex items-center">
    <button
      type="button"
      class="inline-flex h-4 w-4 items-center justify-center rounded-full text-text-muted outline-none transition-colors hover:text-text-primary focus-visible:text-text-primary focus-visible:ring-2 focus-visible:ring-accent/30"
      :aria-expanded="isPinned"
      :aria-describedby="isVisible ? popoverId : undefined"
      :aria-label="label"
      :title="label"
      @click="togglePinned"
      @focus="isFocused = true"
      @blur="isFocused = false"
    >
      <Info class="h-3.5 w-3.5" aria-hidden="true" />
    </button>

    <div
      v-if="isVisible"
      :id="popoverId"
      role="tooltip"
      class="absolute left-0 top-full z-[90] mt-2 w-72 max-w-[min(20rem,calc(100vw-2rem))] rounded-xl border border-border bg-surface-elevated px-3 py-2.5 text-xs leading-5 text-text-secondary shadow-panel"
    >
      {{ description }}
    </div>
  </span>
</template>
