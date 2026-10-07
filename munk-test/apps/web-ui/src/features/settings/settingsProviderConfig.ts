import type {
  GeminiProviderFieldKey,
  GeminiSectionForm,
  OpenAIProviderFieldKey,
  OpenAISectionForm,
  ProviderFieldKeyByKind,
  ProviderFieldMeta,
  ProviderKind,
  ProviderSectionFormByKind,
} from './settingsFormTypes'
import { hasConfiguredExtraHeaders, parseHeaders } from './settingsValueUtils'

const PROVIDER_FIELD_METADATA = {
  openai_compatible: {
    base_url: {
      labelKey: 'settings.fields.baseUrl',
      descriptionKey: 'settings.fieldDescriptions.openaiCompatible.baseUrl',
      requiredWhenActive: true,
    },
    model: {
      labelKey: 'settings.fields.model',
      descriptionKey: 'settings.fieldDescriptions.openaiCompatible.model',
      requiredWhenActive: true,
    },
    timeout_sec: {
      labelKey: 'settings.fields.timeoutSec',
      descriptionKey: 'settings.fieldDescriptions.openaiCompatible.timeoutSec',
    },
    api_key: {
      labelKey: 'settings.fields.apiKey',
      descriptionKey: 'settings.fieldDescriptions.openaiCompatible.apiKey',
      secret: true,
    },
    extra_headers_json: {
      labelKey: 'settings.fields.extraHeaders',
      descriptionKey: 'settings.fieldDescriptions.openaiCompatible.extraHeaders',
    },
    output_strategy: {
      labelKey: 'settings.fields.outputStrategy',
      descriptionKey: 'settings.fieldDescriptions.openaiCompatible.outputStrategy',
    },
    thinking_mode: {
      labelKey: 'settings.fields.thinking',
      descriptionKey: 'settings.fieldDescriptions.openaiCompatible.thinking',
    },
  },
  gemini: {
    model: {
      labelKey: 'settings.fields.model',
      descriptionKey: 'settings.fieldDescriptions.gemini.model',
      requiredWhenActive: true,
    },
    api_key: {
      labelKey: 'settings.fields.apiKey',
      descriptionKey: 'settings.fieldDescriptions.gemini.apiKey',
      secret: true,
    },
    timeout_sec: {
      labelKey: 'settings.fields.timeoutSec',
      descriptionKey: 'settings.fieldDescriptions.gemini.timeoutSec',
    },
    credentials_path: {
      labelKey: 'settings.fields.credentialsPath',
      descriptionKey: 'settings.fieldDescriptions.gemini.credentialsPath',
    },
    base_url: {
      labelKey: 'settings.fields.baseUrl',
      descriptionKey: 'settings.fieldDescriptions.gemini.baseUrl',
    },
    project: {
      labelKey: 'settings.fields.project',
      descriptionKey: 'settings.fieldDescriptions.gemini.project',
    },
    location: {
      labelKey: 'settings.fields.location',
      descriptionKey: 'settings.fieldDescriptions.gemini.location',
    },
  },
} satisfies {
  [K in ProviderKind]: Record<ProviderFieldKeyByKind[K], ProviderFieldMeta>
}

const PROVIDER_FIELD_ACCESSORS = {
  openai_compatible: {
    base_url: section => section.base_url,
    model: section => section.model,
    timeout_sec: section => section.timeout_sec,
    api_key: section => section.api_key,
    extra_headers_json: section => section.extra_headers_json,
    output_strategy: section => section.output_strategy,
    thinking_mode: section => section.thinking_mode,
  },
  gemini: {
    model: section => section.model,
    api_key: section => section.api_key,
    timeout_sec: section => section.timeout_sec,
    credentials_path: section => section.credentials_path,
    base_url: section => section.base_url,
    project: section => section.project,
    location: section => section.location,
  },
} satisfies {
  [K in ProviderKind]: Record<ProviderFieldKeyByKind[K], (section: ProviderSectionFormByKind[K]) => string>
}

const PROVIDER_SECTION_CONFIG_CHECKS = {
  openai_compatible: [
    (section: ProviderSectionFormByKind['openai_compatible']) => section.base_url.trim().length > 0,
    (section: ProviderSectionFormByKind['openai_compatible']) => section.model.trim().length > 0,
    (section: ProviderSectionFormByKind['openai_compatible']) => section.api_key.trim().length > 0,
    (section: ProviderSectionFormByKind['openai_compatible']) => section.api_key_configured,
    (section: ProviderSectionFormByKind['openai_compatible']) => section.timeout_sec.trim().length > 0,
    (section: ProviderSectionFormByKind['openai_compatible']) => hasConfiguredExtraHeaders(section.extra_headers_json),
    (section: ProviderSectionFormByKind['openai_compatible']) => section.output_strategy !== 'auto',
    (section: ProviderSectionFormByKind['openai_compatible']) => section.thinking_mode !== 'default',
  ],
  gemini: [
    (section: ProviderSectionFormByKind['gemini']) => section.model.trim().length > 0,
    (section: ProviderSectionFormByKind['gemini']) => section.api_key.trim().length > 0,
    (section: ProviderSectionFormByKind['gemini']) => section.api_key_configured,
    (section: ProviderSectionFormByKind['gemini']) => section.vertexai,
    (section: ProviderSectionFormByKind['gemini']) => section.project.trim().length > 0,
    (section: ProviderSectionFormByKind['gemini']) => section.location.trim().length > 0,
    (section: ProviderSectionFormByKind['gemini']) => section.credentials_path.trim().length > 0,
    (section: ProviderSectionFormByKind['gemini']) => section.base_url.trim().length > 0,
    (section: ProviderSectionFormByKind['gemini']) => section.timeout_sec.trim().length > 0,
  ],
} satisfies {
  [K in ProviderKind]: Array<(section: ProviderSectionFormByKind[K]) => boolean>
}

export function getProviderFieldMeta<K extends ProviderKind>(
  kind: K,
  field: ProviderFieldKeyByKind[K],
): ProviderFieldMeta {
  return kind === 'openai_compatible'
    ? getOpenAIProviderFieldMeta(field as OpenAIProviderFieldKey)
    : getGeminiProviderFieldMeta(field as GeminiProviderFieldKey)
}

export function isProviderFieldRequired<K extends ProviderKind>(
  kind: K,
  field: ProviderFieldKeyByKind[K],
  active: boolean,
): boolean {
  return active && Boolean(getProviderFieldMeta(kind, field).requiredWhenActive)
}

export function isActiveProviderSectionMissingRequiredFields<K extends ProviderKind>(
  kind: K,
  section: ProviderSectionFormByKind[K],
): boolean {
  if (kind === 'openai_compatible') {
    return isOpenAISectionMissingRequiredFields(section as OpenAISectionForm)
  }
  return isGeminiSectionMissingRequiredFields(section as GeminiSectionForm)
}

export function isProviderSectionConfigured<K extends ProviderKind>(
  kind: K,
  section: ProviderSectionFormByKind[K],
): boolean {
  return kind === 'openai_compatible'
    ? PROVIDER_SECTION_CONFIG_CHECKS.openai_compatible.some(check => check(section as OpenAISectionForm))
    : PROVIDER_SECTION_CONFIG_CHECKS.gemini.some(check => check(section as GeminiSectionForm))
}

function hasValidOpenAIHeaders(section: ProviderSectionFormByKind['openai_compatible']): boolean {
  try {
    parseHeaders(section.extra_headers_json)
    return true
  } catch {
    return false
  }
}

function getProviderFieldTextValue<K extends ProviderKind>(
  kind: K,
  field: ProviderFieldKeyByKind[K],
  section: ProviderSectionFormByKind[K],
): string {
  return kind === 'openai_compatible'
    ? getOpenAIProviderFieldTextValue(field as OpenAIProviderFieldKey, section as OpenAISectionForm)
    : getGeminiProviderFieldTextValue(field as GeminiProviderFieldKey, section as GeminiSectionForm)
}

function getOpenAIProviderFieldMeta(field: OpenAIProviderFieldKey): ProviderFieldMeta {
  return PROVIDER_FIELD_METADATA.openai_compatible[field]
}

function getGeminiProviderFieldMeta(field: GeminiProviderFieldKey): ProviderFieldMeta {
  return PROVIDER_FIELD_METADATA.gemini[field]
}

function isOpenAISectionMissingRequiredFields(section: OpenAISectionForm): boolean {
  for (const field of Object.keys(PROVIDER_FIELD_METADATA.openai_compatible) as OpenAIProviderFieldKey[]) {
    const meta = getOpenAIProviderFieldMeta(field)
    if (!meta.requiredWhenActive) {
      continue
    }
    if (!getOpenAIProviderFieldTextValue(field, section).trim()) {
      return true
    }
  }

  return !hasValidOpenAIHeaders(section)
}

function isGeminiSectionMissingRequiredFields(section: GeminiSectionForm): boolean {
  for (const field of Object.keys(PROVIDER_FIELD_METADATA.gemini) as GeminiProviderFieldKey[]) {
    const meta = getGeminiProviderFieldMeta(field)
    if (!meta.requiredWhenActive) {
      continue
    }
    if (!getGeminiProviderFieldTextValue(field, section).trim()) {
      return true
    }
  }

  return false
}

function getOpenAIProviderFieldTextValue(field: OpenAIProviderFieldKey, section: OpenAISectionForm): string {
  return PROVIDER_FIELD_ACCESSORS.openai_compatible[field](section)
}

function getGeminiProviderFieldTextValue(field: GeminiProviderFieldKey, section: GeminiSectionForm): string {
  return PROVIDER_FIELD_ACCESSORS.gemini[field](section)
}
