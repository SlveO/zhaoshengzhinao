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

export interface ModuleItem {
  key: string
  name: string
  desc: string
  depends: string[]
  enabled: boolean
}

// ── Distribution ──

export interface DistributionChannel {
  id: string
  name: string
  channel_type: string
  webhook_url_masked: string
  config: Record<string, any>
  status: string
  last_test_at: string | null
  error_message: string | null
  created_at: string
}

export interface DistributionFile {
  id: string
  original_filename: string
  file_size: number
  mime_type: string | null
  created_by: string | null
  created_at: string
}

export interface DistributionTask {
  id: string
  name: string
  file_id: string
  channel_id: string
  schedule_type: string
  schedule_config: Record<string, any>
  scheduled_at: string | null
  status: string
  message_text: string | null
  created_at: string
  file_name?: string
  channel_name?: string
}

export interface DistributionLog {
  id: string
  task_id: string
  channel_id: string
  file_id: string
  status: string
  attempt: number
  request_payload: Record<string, any> | null
  response_body: Record<string, any> | null
  error_message: string | null
  duration_ms: number | null
  created_at: string
  task_name?: string
  channel_name?: string
  file_name?: string
}
