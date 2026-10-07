<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import type { RecordedInputEvent, RecordingSession, TimelineEntry } from '@/shared/api/recording'
import AppCard from '@/shared/components/AppCard.vue'
import { useTime } from '@/shared/time/useTime'

defineProps<{
  session: RecordingSession | null
  events: RecordedInputEvent[]
  timeline: TimelineEntry[]
}>()

const { t } = useI18n()
const time = useTime()
</script>

<template>
  <AppCard class="grid gap-5">
    <header class="grid gap-2">
      <h2 class="text-lg font-semibold text-text-primary">{{ t('recording.status') }}</h2>
    </header>

    <div v-if="session" class="grid gap-4 rounded-xl border border-border-muted bg-surface-muted p-4 md:grid-cols-2">
      <div class="grid gap-1">
        <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.recordingId') }}</label>
        <span class="break-all text-sm text-text-primary">{{ session.recording_id }}</span>
      </div>
      <div class="grid gap-1">
        <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.status') }}</label>
        <span class="inline-flex w-fit rounded-full bg-surface-default px-2.5 py-1 text-xs font-semibold text-text-secondary">{{ session.status }}</span>
      </div>
      <div class="grid gap-1">
        <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.latestFrameSeq') }}</label>
        <span class="text-sm text-text-primary">{{ session.latest_frame_seq ?? t('recording.none') }}</span>
      </div>
      <div class="grid gap-1">
        <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.finishedAt') }}</label>
        <time
          v-if="session.finished_at"
          class="text-sm text-text-primary"
          :datetime="time.datetime(session.finished_at) ?? undefined"
          :title="time.tooltip(session.finished_at)"
        >
          {{ time.absolute(session.finished_at) }}
        </time>
        <span v-else class="text-sm text-text-primary">{{ t('recording.none') }}</span>
      </div>
      <div v-if="session.failure_reason" class="grid gap-1 md:col-span-2">
        <label class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">{{ t('recording.fields.failureReason') }}</label>
        <span class="text-sm text-error-text">{{ session.failure_reason }}</span>
      </div>
    </div>
    <div v-else class="rounded-xl border border-dashed border-border-strong bg-surface-muted px-4 py-6 text-center text-sm text-text-muted">
      {{ t('recording.sessionNotCreated') }}
    </div>

    <div class="grid gap-5">
      <section class="grid gap-3">
        <header>
          <h3 class="text-sm font-semibold text-text-primary">{{ t('recording.events') }}</h3>
        </header>
        <ul class="overflow-hidden rounded-xl border border-border bg-surface-default">
          <li v-for="event in events" :key="event.event_id" class="flex flex-wrap items-center gap-3 border-b border-border-muted px-4 py-3 text-sm last:border-b-0">
            <span class="font-mono text-xs text-text-muted">{{ event.event_id.split('-')[0] }}</span>
            <span class="inline-flex rounded-full bg-surface-muted px-2.5 py-1 text-xs font-semibold text-text-secondary">{{ event.kind }}</span>
            <span class="min-w-0 flex-1 truncate text-text-secondary">{{ event.summary || t('recording.none') }}</span>
          </li>
          <li v-if="events.length === 0" class="px-4 py-4 text-center text-sm text-text-muted">{{ t('recording.noEvents') }}</li>
        </ul>
      </section>

      <section class="grid gap-3">
        <header>
          <h3 class="text-sm font-semibold text-text-primary">{{ t('recording.timeline') }}</h3>
        </header>
        <ul class="overflow-hidden rounded-xl border border-border bg-surface-default">
          <li v-for="entry in timeline" :key="entry.entry_id" class="flex flex-wrap items-center gap-3 border-b border-border-muted px-4 py-3 text-sm last:border-b-0">
            <span class="font-mono text-xs text-text-muted">{{ entry.entry_id.split('-')[0] }}</span>
            <span class="inline-flex rounded-full bg-surface-muted px-2.5 py-1 text-xs font-semibold text-text-secondary">{{ entry.kind }}</span>
            <span class="min-w-0 flex-1 truncate text-text-secondary">{{ entry.before_observation_id }} &rarr; {{ entry.after_observation_id }}</span>
          </li>
          <li v-if="timeline.length === 0" class="px-4 py-4 text-center text-sm text-text-muted">{{ t('recording.noTimeline') }}</li>
        </ul>
      </section>
    </div>
  </AppCard>
</template>
