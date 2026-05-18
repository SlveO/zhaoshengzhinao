export interface BrandConfig {
  name: string
  shortName: string
  primaryColor: string
  secondaryColor: string
  logoUrl: string
  faviconUrl: string | null
  loginBgUrl: string | null
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
