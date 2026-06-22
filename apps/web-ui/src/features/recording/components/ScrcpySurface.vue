<script setup lang="ts">
import { useScrcpySurfaceSession } from '../composables/useScrcpySurfaceSession'
import type { ScrcpyInteractionForwardedPayload } from '../lib/scrcpySurfaceTypes'

const props = defineProps<{
  wsUrl: string
}>()

const emit = defineEmits<{
  (e: 'interactionForwarded', payload: ScrcpyInteractionForwardedPayload): void
}>()

const {
  canvasRef,
  connect,
  errorMessage,
  handleBack,
  handleInput,
  handlePointerCancel,
  handlePointerDown,
  handlePointerMove,
  handlePointerUp,
  inputText,
  status,
  videoSizeText
} = useScrcpySurfaceSession({
  wsUrl: props.wsUrl,
  onInteractionForwarded: (payload) => {
    emit('interactionForwarded', payload)
  }
})
</script>

<template>
  <div class="scrcpy-surface">
    <div class="meta-toolbar">
      <div class="status-info">
        <span class="badge" :class="status">{{ status }}</span>
        <span>{{ videoSizeText }}</span>
        <span v-if="errorMessage" class="error-msg">{{ errorMessage }}</span>
      </div>
      <div class="actions">
        <button :disabled="status !== 'ready'" @click="handleBack">Back</button>
        <div class="input-group">
          <input
            v-model="inputText"
            :disabled="status !== 'ready'"
            type="text"
            placeholder="Input text"
            @keydown.enter.prevent="handleInput"
          >
          <button :disabled="status !== 'ready' || !inputText.trim()" @click="handleInput">Send</button>
        </div>
        <button v-if="status === 'error' || status === 'closed'" class="primary" @click="connect">Reconnect</button>
      </div>
    </div>
    <div class="canvas-container">
      <canvas
        ref="canvasRef"
        class="canvas"
        @pointerdown="handlePointerDown"
        @pointermove="handlePointerMove"
        @pointerup="handlePointerUp"
        @pointercancel="handlePointerCancel"
        @lostpointercapture="handlePointerCancel"
      ></canvas>
    </div>
  </div>
</template>

<style scoped>
.scrcpy-surface {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: var(--surface-default);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-default);
}

.meta-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-default);
  background: var(--surface-muted);
  flex-wrap: wrap;
  gap: 12px;
}

.status-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: ui-monospace, SFMono-Regular, Consolas, 'Courier New', monospace;
  font-size: 12px;
  color: var(--text-secondary);
}

.badge {
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--border-default);
  color: var(--text-primary);
  font-weight: 600;
  text-transform: uppercase;
  font-size: 11px;
}

.badge.ready {
  background: var(--status-success-bg);
  color: var(--status-success-text);
}

.badge.error {
  background: var(--status-error-bg);
  color: var(--status-error-text);
}

.error-msg {
  color: var(--status-error-text);
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.input-group {
  display: flex;
  gap: 4px;
}

.input-group input {
  min-width: 140px;
}

.canvas-container {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  overflow: hidden;
  position: relative;
}

.canvas {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  touch-action: none;
  user-select: none;
}
</style>
