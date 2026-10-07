import type { KnowledgeCardStatus, KnowledgeCardType } from '@/shared/api/knowledge'

export type KnowledgeDocumentSummary = {
  schemaVersion: string
  appId: string
  cardCount: number
  typeCounts: Array<{ type: KnowledgeCardType | 'unknown', count: number }>
}

export function parseKnowledgeDocument(raw: string | null | undefined): KnowledgeDocumentSummary | null {
  if (!raw?.trim()) {
    return null
  }
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>
    const cardsInDocument = Array.isArray(parsed.cards) ? parsed.cards : []
    const counts = new Map<KnowledgeCardType | 'unknown', number>()
    for (const item of cardsInDocument) {
      const cardType = typeof item === 'object' && item && typeof (item as Record<string, unknown>).card_type === 'string'
        ? ((item as Record<string, unknown>).card_type as KnowledgeCardType)
        : 'unknown'
      counts.set(cardType, (counts.get(cardType) ?? 0) + 1)
    }
    return {
      schemaVersion: typeof parsed.schema_version === 'string' ? parsed.schema_version : '-',
      appId: typeof parsed.app_id === 'string' ? parsed.app_id : '-',
      cardCount: cardsInDocument.length,
      typeCounts: [...counts.entries()].map(([type, count]) => ({ type, count })).sort((a, b) => b.count - a.count),
    }
  } catch {
    return null
  }
}

export function knowledgeCardStatusTone(status: KnowledgeCardStatus): 'neutral' | 'warning' | 'error' {
  if (status === 'deprecated') {
    return 'warning'
  }
  if (status === 'archived') {
    return 'error'
  }
  return 'neutral'
}
