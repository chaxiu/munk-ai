import type { AppDetailData, AppUpsertRequest } from '@/shared/api/apps'

export type AppPlatform = 'android' | 'ios' | 'web'

export type AppFormModel = {
  appId: string
  appName: string
  platform: AppPlatform
  introductionMarkdown: string
  appKnowledgeFileName: string
  appKnowledgeContent: string
  hasExistingAppKnowledge: boolean
  appKnowledgeDirty: boolean
  androidPackageName: string
  androidActivityName: string
  iosBundleId: string
  webBaseUrl: string
  webOrigin: string
}

export function createAppFormModel(platform: AppPlatform = 'android'): AppFormModel {
  return {
    appId: '',
    appName: '',
    platform,
    introductionMarkdown: '',
    appKnowledgeFileName: '',
    appKnowledgeContent: '',
    hasExistingAppKnowledge: false,
    appKnowledgeDirty: false,
    androidPackageName: '',
    androidActivityName: '',
    iosBundleId: '',
    webBaseUrl: '',
    webOrigin: '',
  }
}

export function populateAppForm(form: AppFormModel, detail: AppDetailData): void {
  form.appId = detail.profile.app_id
  form.appName = detail.profile.app_name ?? ''
  form.platform = detail.profile.platform
  form.introductionMarkdown = detail.introduction_markdown
  form.appKnowledgeFileName = detail.app_knowledge_exists ? (detail.profile.app_knowledge_ref ?? 'app_knowledge.json') : ''
  form.appKnowledgeContent = detail.app_knowledge_content ?? ''
  form.hasExistingAppKnowledge = detail.app_knowledge_exists
  form.appKnowledgeDirty = false
  form.androidPackageName = detail.profile.android?.package_name ?? ''
  form.androidActivityName = detail.profile.android?.activity_name ?? ''
  form.iosBundleId = detail.profile.ios?.bundle_id ?? ''
  form.webBaseUrl = detail.profile.web?.base_url ?? ''
  form.webOrigin = detail.profile.web?.origin ?? ''
}

export function buildAppUpsertRequest(form: AppFormModel): AppUpsertRequest {
  return {
    profile: {
      app_id: form.appId.trim(),
      app_name: form.appName.trim(),
      platform: form.platform,
      app_introduction_ref: 'introduction.md',
      app_knowledge_ref: 'app_knowledge.json',
      android: form.platform === 'android'
        ? {
            package_name: form.androidPackageName.trim(),
            activity_name: form.androidActivityName.trim() || null,
          }
        : null,
      ios: form.platform === 'ios'
        ? {
            bundle_id: form.iosBundleId.trim(),
          }
        : null,
      web: form.platform === 'web'
        ? {
            base_url: form.webBaseUrl.trim(),
            origin: form.webOrigin.trim() || null,
          }
        : null,
    },
    introduction_markdown: form.introductionMarkdown.trim(),
    app_knowledge_file_name: form.appKnowledgeDirty ? form.appKnowledgeFileName.trim() || 'app_knowledge.json' : null,
    app_knowledge_content: form.appKnowledgeDirty ? form.appKnowledgeContent.trim() : null,
  }
}

export function isAppFormSubmittable(form: AppFormModel): boolean {
  if (!form.appId.trim() || !form.appName.trim() || !form.introductionMarkdown.trim()) {
    return false
  }
  if (!form.hasExistingAppKnowledge && !form.appKnowledgeContent.trim()) {
    return false
  }
  if (form.platform === 'android') {
    return Boolean(form.androidPackageName.trim())
  }
  if (form.platform === 'ios') {
    return Boolean(form.iosBundleId.trim())
  }
  return Boolean(form.webBaseUrl.trim())
}
