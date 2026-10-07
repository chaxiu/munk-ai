<script setup lang="ts">
import { Check, ChevronDown, Globe, MonitorCog, MoonStar, SunMedium } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import {
  DropdownMenuContent,
  DropdownMenuItemIndicator,
  DropdownMenuPortal,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuRoot,
  DropdownMenuTrigger,
} from 'radix-vue'

import { setLocale } from '@/shared/i18n'
import type { SupportedLocale } from '@/shared/i18n/messageKeys'
import { useTheme } from '@/shared/theme/useTheme'

const { locale, t } = useI18n()
const { themePreference, setThemePreference } = useTheme()

function handleLocaleChange(value: string) {
  setLocale(value as SupportedLocale)
}

function handleThemeChange(value: string) {
  setThemePreference(value as 'light' | 'dark' | 'system')
}
</script>

<template>
  <header class="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-border bg-surface-default/90 px-6 backdrop-blur">
    <div class="min-w-0 flex-1">
      <slot />
    </div>
    <div class="ml-auto flex shrink-0 items-center gap-3">
      <slot name="actions" />
      <DropdownMenuRoot>
        <DropdownMenuTrigger class="inline-flex min-h-8 items-center gap-2 rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary shadow-sm transition-all duration-150 hover:border-border-strong hover:bg-surface-muted">
          <span class="sr-only">{{ t('common.locale') }}</span>
          <Globe class="h-4 w-4 text-text-secondary" />
          <span>{{ locale === 'zh-CN' ? '中文' : 'English' }}</span>
          <ChevronDown class="h-4 w-4 text-text-muted" />
        </DropdownMenuTrigger>
        <DropdownMenuPortal>
          <DropdownMenuContent :side-offset="8" class="z-50 min-w-44 rounded-lg border border-border bg-surface-elevated p-1.5 shadow-panel">
            <DropdownMenuRadioGroup :model-value="locale" @update:model-value="handleLocaleChange">
              <DropdownMenuRadioItem value="zh-CN" class="relative flex min-h-8 items-center rounded-md px-8 py-1.5 text-sm text-text-primary outline-none transition-colors data-[highlighted]:bg-accent-soft">
                <span class="absolute left-2 inline-flex h-4 w-4 items-center justify-center">
                  <DropdownMenuItemIndicator>
                    <Check class="h-4 w-4 text-accent" />
                  </DropdownMenuItemIndicator>
                </span>
                中文
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="en-US" class="relative flex min-h-8 items-center rounded-md px-8 py-1.5 text-sm text-text-primary outline-none transition-colors data-[highlighted]:bg-accent-soft">
                <span class="absolute left-2 inline-flex h-4 w-4 items-center justify-center">
                  <DropdownMenuItemIndicator>
                    <Check class="h-4 w-4 text-accent" />
                  </DropdownMenuItemIndicator>
                </span>
                English
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenuPortal>
      </DropdownMenuRoot>

      <DropdownMenuRoot>
        <DropdownMenuTrigger class="inline-flex min-h-8 items-center gap-2 rounded-md border border-border bg-surface-default px-3 text-sm font-medium text-text-primary shadow-sm transition-all duration-150 hover:border-border-strong hover:bg-surface-muted">
          <span class="sr-only">{{ t('common.theme') }}</span>
          <MonitorCog class="h-4 w-4 text-text-secondary" />
          <span>
            {{
              themePreference === 'light'
                ? t('common.light')
                : themePreference === 'dark'
                  ? t('common.dark')
                  : t('common.system')
            }}
          </span>
          <ChevronDown class="h-4 w-4 text-text-muted" />
        </DropdownMenuTrigger>
        <DropdownMenuPortal>
          <DropdownMenuContent :side-offset="8" class="z-50 min-w-44 rounded-lg border border-border bg-surface-elevated p-1.5 shadow-panel">
            <DropdownMenuRadioGroup :model-value="themePreference" @update:model-value="handleThemeChange">
              <DropdownMenuRadioItem value="light" class="relative flex min-h-8 items-center gap-2 rounded-md px-8 py-1.5 text-sm text-text-primary outline-none transition-colors data-[highlighted]:bg-accent-soft">
                <span class="absolute left-2 inline-flex h-4 w-4 items-center justify-center">
                  <DropdownMenuItemIndicator>
                    <Check class="h-4 w-4 text-accent" />
                  </DropdownMenuItemIndicator>
                </span>
                <SunMedium class="h-4 w-4 text-text-secondary" />
                {{ t('common.light') }}
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="dark" class="relative flex min-h-8 items-center gap-2 rounded-md px-8 py-1.5 text-sm text-text-primary outline-none transition-colors data-[highlighted]:bg-accent-soft">
                <span class="absolute left-2 inline-flex h-4 w-4 items-center justify-center">
                  <DropdownMenuItemIndicator>
                    <Check class="h-4 w-4 text-accent" />
                  </DropdownMenuItemIndicator>
                </span>
                <MoonStar class="h-4 w-4 text-text-secondary" />
                {{ t('common.dark') }}
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="system" class="relative flex min-h-8 items-center gap-2 rounded-md px-8 py-1.5 text-sm text-text-primary outline-none transition-colors data-[highlighted]:bg-accent-soft">
                <span class="absolute left-2 inline-flex h-4 w-4 items-center justify-center">
                  <DropdownMenuItemIndicator>
                    <Check class="h-4 w-4 text-accent" />
                  </DropdownMenuItemIndicator>
                </span>
                <MonitorCog class="h-4 w-4 text-text-secondary" />
                {{ t('common.system') }}
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenuPortal>
      </DropdownMenuRoot>
    </div>
  </header>
</template>
