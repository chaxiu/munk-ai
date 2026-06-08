<script setup lang="ts">
import { toRef } from 'vue'
import { useI18n } from 'vue-i18n'

import UiField from '@/shared/ui/UiField.vue'
import UiInput from '@/shared/ui/UiInput.vue'
import UiTextarea from '@/shared/ui/UiTextarea.vue'
import type { ProxyConfigForm as ProxyConfigFormState } from '../types'

const props = defineProps<{
  proxy: ProxyConfigFormState
}>()

const { t } = useI18n()
const proxy = toRef(props, 'proxy')
</script>

<template>
  <div class="grid gap-4">
    <UiField :label="t('settings.fields.proxyEnabled')" :hint="t('settings.proxy.enabledHint')">
      <label class="flex min-h-11 items-center gap-2 rounded-xl border border-border bg-surface-muted/35 px-3.5 text-sm text-text-secondary">
        <input v-model="proxy.enabled" type="checkbox" class="h-4 w-4 rounded border-border">
        {{ t('settings.proxy.enableToggle') }}
      </label>
    </UiField>

    <UiField :label="t('settings.fields.proxyUrl')" :hint="t('settings.proxy.urlHint')">
      <UiInput v-model="proxy.url" :placeholder="t('settings.placeholders.proxyUrl')" />
    </UiField>

    <UiField :label="t('settings.fields.noProxy')" :hint="t('settings.proxy.noProxyHint')">
      <UiTextarea
        v-model="proxy.no_proxy_text"
        :rows="5"
        :placeholder="t('settings.placeholders.noProxy')"
      />
    </UiField>
  </div>
</template>
