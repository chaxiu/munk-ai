<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDown } from '@lucide/vue'
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuTrigger,
} from 'radix-vue'

import ImportPlanDialog from '@/features/tests/components/ImportPlanDialog.vue'

const { t } = useI18n()
const importDialogOpen = ref(false)

function openImportDialog() {
  importDialogOpen.value = true
}

function closeImportDialog() {
  importDialogOpen.value = false
}
</script>

<template>
  <div class="flex shrink-0 items-center gap-2">
    <DropdownMenuRoot>
      <DropdownMenuTrigger class="inline-flex min-h-8 items-center gap-2 rounded-md border border-accent bg-accent px-3 text-sm font-medium text-white shadow-sm transition-colors hover:border-accent-strong hover:bg-accent-strong">
        <span>{{ t('tests.createTitle') }}</span>
        <ChevronDown class="h-4 w-4" />
      </DropdownMenuTrigger>
      <DropdownMenuPortal>
        <DropdownMenuContent :side-offset="8" class="z-50 min-w-36 rounded-lg border border-border bg-surface-elevated p-1.5 shadow-panel">
          <DropdownMenuItem class="flex min-h-8 items-center rounded-md px-3 py-1.5 text-sm text-text-primary outline-none transition-colors data-[highlighted]:bg-accent-soft" @select.prevent="openImportDialog">
            {{ t('tests.import.actions.import') }}
          </DropdownMenuItem>
          <DropdownMenuItem as-child>
            <RouterLink class="flex min-h-8 items-center rounded-md px-3 py-1.5 text-sm text-text-primary outline-none transition-colors hover:bg-accent-soft" to="/tests/create">
              {{ t('tests.import.actions.new') }}
            </RouterLink>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenuPortal>
    </DropdownMenuRoot>
    <RouterLink class="inline-flex min-h-8 items-center rounded-md border border-accent bg-accent-soft px-3 text-sm font-medium text-accent shadow-sm transition-colors hover:border-accent-strong hover:bg-accent/15" to="/runs/new">
      {{ t('home.actions.runTests') }}
    </RouterLink>
  </div>
  <ImportPlanDialog :open="importDialogOpen" @close="closeImportDialog" />
</template>
