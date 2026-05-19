export interface BrandConfig {
  name: string
  short_name: string
  primary_color: string
  secondary_color: string
  logo_url: string
  favicon_url: string | null
  login_bg_url: string | null
  welcome_text?: string
}

export interface FunnelData {
  period: { start: string; end: string }
  stages: {
    visitors: number
    conversations: number
    deepConsultations: number
    intentExpressed: number
    enrolled: number
  }
  conversionRates: Record<string, number>
  _stub?: boolean
}

export interface ProfileDashboard {
  riasecDistribution: { dimension: string; avgScore: number; count: number }[]
  valuesDistribution: { value: string; percentage: number }[]
  completenessBreakdown: { level: string; count: number }[]
  totalProfiles: number
  _stub?: boolean
}

export interface TenantInfo {
  id: string
  name: string
  slug: string
  subscription_tier: string
  status: string
}

export interface TenantConfig {
  brand?: BrandConfig
  modules?: Record<string, boolean>
  knowledge_base?: { doc_count: number; last_updated: string }
}

export interface DocumentItem {
  id: string
  title: string
  data_type: string
  year: number | null
  indexed_at: string | null
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user_id: string
  username: string
}

export interface TopicCloudItem {
  word: string
  count: number
}

export interface EmotionTimelineData {
  timeline: {
    emotion: string
    data: { date: string; count: number }[]
  }[]
  dates: string[]
}

export interface HotQuestionItem {
  topic: string
  count: number
}

export interface PersonaConfig {
  custom_prompt: string
  style: 'casual' | 'formal'
  proactive_recommend: boolean
}
