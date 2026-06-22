import type { KnowledgeCardType } from '@/shared/api/knowledge'

export type KnowledgePayloadFieldKind = 'text' | 'textarea' | 'string-list'

export type KnowledgePayloadFieldConfig = {
  key: string
  labelKey: string
  kind: KnowledgePayloadFieldKind
  required?: boolean
  placeholderKey?: string
  descriptionKey?: string
}

export type KnowledgePayloadSectionConfig = {
  key: string
  titleKey?: string
  fields: KnowledgePayloadFieldConfig[]
}

export const knowledgePayloadSections: Record<KnowledgeCardType, KnowledgePayloadSectionConfig[]> = {
  screen: [
    {
      key: 'screen-main',
      fields: [
        {
          key: 'enter',
          labelKey: 'apps.knowledge.payloadFields.enter.label',
          kind: 'textarea',
          required: true,
          placeholderKey: 'apps.knowledge.payloadFields.enter.placeholder',
        },
        {
          key: 'recognize',
          labelKey: 'apps.knowledge.payloadFields.recognize.label',
          kind: 'textarea',
          required: true,
          placeholderKey: 'apps.knowledge.payloadFields.recognize.placeholder',
        },
        {
          key: 'key_elements',
          labelKey: 'apps.knowledge.payloadFields.key_elements.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.key_elements.placeholder',
          descriptionKey: 'apps.knowledge.payloadFields.key_elements.description',
        },
        {
          key: 'exit_signals',
          labelKey: 'apps.knowledge.payloadFields.exit_signals.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.exit_signals.placeholder',
          descriptionKey: 'apps.knowledge.payloadFields.exit_signals.description',
        },
      ],
    },
  ],
  flow: [
    {
      key: 'flow-main',
      fields: [
        {
          key: 'goal',
          labelKey: 'apps.knowledge.payloadFields.goal.label',
          kind: 'textarea',
          required: true,
          placeholderKey: 'apps.knowledge.payloadFields.goal.placeholder',
        },
        {
          key: 'preconditions',
          labelKey: 'apps.knowledge.payloadFields.preconditions.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.preconditions.placeholder',
        },
        {
          key: 'typical_steps',
          labelKey: 'apps.knowledge.payloadFields.typical_steps.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.typical_steps.placeholder',
        },
        {
          key: 'completion_signals',
          labelKey: 'apps.knowledge.payloadFields.completion_signals.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.completion_signals.placeholder',
        },
      ],
    },
  ],
  assertion: [
    {
      key: 'assertion-main',
      fields: [
        {
          key: 'when',
          labelKey: 'apps.knowledge.payloadFields.when.label',
          kind: 'textarea',
          required: true,
          placeholderKey: 'apps.knowledge.payloadFields.when.placeholder',
        },
        {
          key: 'success_signals',
          labelKey: 'apps.knowledge.payloadFields.success_signals.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.success_signals.placeholder',
        },
        {
          key: 'failure_signals',
          labelKey: 'apps.knowledge.payloadFields.failure_signals.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.failure_signals.placeholder',
        },
        {
          key: 'verdict_hint',
          labelKey: 'apps.knowledge.payloadFields.verdict_hint.label',
          kind: 'textarea',
          placeholderKey: 'apps.knowledge.payloadFields.verdict_hint.placeholder',
        },
      ],
    },
  ],
  issue: [
    {
      key: 'issue-main',
      fields: [
        {
          key: 'symptoms',
          labelKey: 'apps.knowledge.payloadFields.symptoms.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.symptoms.placeholder',
        },
        {
          key: 'trigger_conditions',
          labelKey: 'apps.knowledge.payloadFields.trigger_conditions.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.trigger_conditions.placeholder',
        },
        {
          key: 'workaround',
          labelKey: 'apps.knowledge.payloadFields.workaround.label',
          kind: 'textarea',
          placeholderKey: 'apps.knowledge.payloadFields.workaround.placeholder',
        },
        {
          key: 'severity',
          labelKey: 'apps.knowledge.payloadFields.severity.label',
          kind: 'text',
          placeholderKey: 'apps.knowledge.payloadFields.severity.placeholder',
        },
      ],
    },
  ],
  data: [
    {
      key: 'data-main',
      fields: [
        {
          key: 'fixtures',
          labelKey: 'apps.knowledge.payloadFields.fixtures.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.fixtures.placeholder',
        },
        {
          key: 'accounts',
          labelKey: 'apps.knowledge.payloadFields.accounts.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.accounts.placeholder',
        },
        {
          key: 'preloaded_state',
          labelKey: 'apps.knowledge.payloadFields.preloaded_state.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.preloaded_state.placeholder',
        },
        {
          key: 'cleanup_requirements',
          labelKey: 'apps.knowledge.payloadFields.cleanup_requirements.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.cleanup_requirements.placeholder',
        },
      ],
    },
  ],
  policy: [
    {
      key: 'policy-main',
      fields: [
        {
          key: 'platform_constraints',
          labelKey: 'apps.knowledge.payloadFields.platform_constraints.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.platform_constraints.placeholder',
        },
        {
          key: 'environment_rules',
          labelKey: 'apps.knowledge.payloadFields.environment_rules.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.environment_rules.placeholder',
        },
        {
          key: 'permission_rules',
          labelKey: 'apps.knowledge.payloadFields.permission_rules.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.permission_rules.placeholder',
        },
        {
          key: 'risk_controls',
          labelKey: 'apps.knowledge.payloadFields.risk_controls.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.risk_controls.placeholder',
        },
      ],
    },
  ],
  domain_term: [
    {
      key: 'domain-term-main',
      fields: [
        {
          key: 'term',
          labelKey: 'apps.knowledge.payloadFields.term.label',
          kind: 'text',
          required: true,
          placeholderKey: 'apps.knowledge.payloadFields.term.placeholder',
        },
        {
          key: 'aliases',
          labelKey: 'apps.knowledge.payloadFields.aliases.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.aliases.placeholder',
        },
        {
          key: 'meaning',
          labelKey: 'apps.knowledge.payloadFields.meaning.label',
          kind: 'textarea',
          required: true,
          placeholderKey: 'apps.knowledge.payloadFields.meaning.placeholder',
        },
        {
          key: 'related_terms',
          labelKey: 'apps.knowledge.payloadFields.related_terms.label',
          kind: 'string-list',
          placeholderKey: 'apps.knowledge.payloadFields.related_terms.placeholder',
        },
        {
          key: 'business_scope',
          labelKey: 'apps.knowledge.payloadFields.business_scope.label',
          kind: 'textarea',
          placeholderKey: 'apps.knowledge.payloadFields.business_scope.placeholder',
        },
      ],
    },
  ],
}

export function getKnowledgePayloadSections(cardType: KnowledgeCardType): KnowledgePayloadSectionConfig[] {
  return knowledgePayloadSections[cardType]
}
