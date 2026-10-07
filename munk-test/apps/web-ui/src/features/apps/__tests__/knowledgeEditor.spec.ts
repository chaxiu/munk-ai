import { describe, expect, it } from 'vitest'

import type { KnowledgeCard } from '@/shared/api/knowledge'
import {
  createEmptyKnowledgeCardForm,
  formFromKnowledgeCard,
  shouldConfirmCardTypeReset,
  updateFormEditorMode,
  validateKnowledgeCardForm,
} from '../knowledgeEditor'

describe('knowledgeEditor', () => {
  it('creates a structured screen form with normalized payload defaults', () => {
    const form = createEmptyKnowledgeCardForm('screen')

    expect(form.editorMode).toBe('structured')
    expect(form.payloadDraft).toEqual({
      enter: '',
      recognize: '',
      key_elements: [],
      exit_signals: [],
    })
    expect(form.jsonModeText).toContain('"recognize": ""')
  })

  it('hydrates a flow card into structured payload draft state', () => {
    const card: KnowledgeCard = {
      app_id: 'app-1',
      card_id: 'flow-1',
      card_type: 'flow',
      title: 'Checkout flow',
      status: 'active',
      confidence: 0.9,
      updated_at: '2026-06-06T00:00:00Z',
      source: {
        kind: 'manual',
        ref: null,
        note: null,
      },
      payload: {
        goal: 'Complete checkout',
        preconditions: ['User is logged in'],
        typical_steps: ['Open cart', 'Tap checkout'],
        completion_signals: ['Success screen appears'],
      },
    }

    const form = formFromKnowledgeCard(card)

    expect(form.cardType).toBe('flow')
    expect(form.payloadDraft.goal).toBe('Complete checkout')
    expect(form.payloadDraft.preconditions).toEqual(['User is logged in'])
    expect(form.jsonModeText).toContain('"goal": "Complete checkout"')
  })

  it('switches between structured and json modes while keeping payload synchronized', () => {
    const form = createEmptyKnowledgeCardForm('screen')
    form.payloadDraft.enter = 'Open home'
    form.payloadDraft.recognize = 'Bottom tab is highlighted'

    const jsonForm = updateFormEditorMode(form, 'json')
    expect(jsonForm.editorMode).toBe('json')
    expect(jsonForm.jsonModeText).toContain('"enter": "Open home"')

    jsonForm.jsonModeText = JSON.stringify({
      enter: 'Tap profile',
      recognize: 'Profile header is visible',
      key_elements: ['Avatar'],
      exit_signals: [],
    }, null, 2)

    const structuredForm = updateFormEditorMode(jsonForm, 'structured')
    expect(structuredForm.editorMode).toBe('structured')
    expect(structuredForm.payloadDraft).toEqual({
      enter: 'Tap profile',
      recognize: 'Profile header is visible',
      key_elements: ['Avatar'],
      exit_signals: [],
    })
  })

  it('validates required fields for all configured types', () => {
    const screenForm = createEmptyKnowledgeCardForm('screen')
    const screenResult = validateKnowledgeCardForm(screenForm)
    expect(screenResult.isValid).toBe(false)
    expect(screenResult.errors.title).toBe('title-required')
    expect(screenResult.errors.payloadFields.enter).toBe('field-required')
    expect(screenResult.errors.payloadFields.recognize).toBe('field-required')

    const assertionForm = createEmptyKnowledgeCardForm('assertion')
    assertionForm.title = 'Assertion'
    const assertionResult = validateKnowledgeCardForm(assertionForm)
    expect(assertionResult.errors.payloadFields.when).toBe('field-required')

    const domainTermForm = createEmptyKnowledgeCardForm('domain_term')
    domainTermForm.title = 'Domain term'
    const domainTermResult = validateKnowledgeCardForm(domainTermForm)
    expect(domainTermResult.errors.payloadFields.term).toBe('field-required')
    expect(domainTermResult.errors.payloadFields.meaning).toBe('field-required')
  })

  it('requires card type reset confirmation only after payload changes', () => {
    const defaultForm = createEmptyKnowledgeCardForm('flow')
    expect(shouldConfirmCardTypeReset(defaultForm)).toBe(false)

    defaultForm.payloadDraft.goal = 'Complete checkout'
    expect(shouldConfirmCardTypeReset(defaultForm)).toBe(true)
  })
})
