/**
 * C 端学生小程序 API 类型定义
 *
 * 对齐 docs/C端学生小程序API契约.md
 * - API 前缀：/api/v1
 * - 统一返回格式：{ data, error }
 * - 字段命名优先使用后端契约中的 snake_case
 */

export interface ApiError {
  code: string
  message: string
}

export interface ApiResponse<T = unknown> {
  data: T | null
  error: ApiError | null
}

export interface StudentBasicInfo {
  province: string
  subject_type: "物理类" | "历史类" | string
  score: number
  intent_majors: string[]
}

export interface ProfileSnapshot {
  riasec: Record<string, number>
  values: string[]
  confidence: number
  completeness: "L1" | "L2" | "L3"
}

export interface StudentProfileData {
  student: StudentBasicInfo
  profile: ProfileSnapshot
  updated_at: string
}

export type ChatStage = "explore" | "focus" | "confirm" | "done"

export interface WsClientMessage {
  type: "message"
  content: string
}

export interface WsThinkingMessage {
  type: "thinking"
}

export interface WsAssistantMessage {
  type: "message"
  content: string
  stage?: ChatStage
}

export interface WsProfileUpdateMessage {
  type: "profile_update"
  riasec?: Record<string, number>
  values?: string[]
  confidence?: number
  completeness?: "L1" | "L2" | "L3"
}

export interface WsStageChangeMessage {
  type: "stage_change"
  from: ChatStage
  to: ChatStage
}

export interface WsSummaryMessage {
  type: "summary"
  content: string
  profile_snapshot?: ProfileSnapshot
}

export interface WsErrorMessage {
  type: "error"
  code: string
  message: string
}

export type WsServerMessage =
  | WsThinkingMessage
  | WsAssistantMessage
  | WsProfileUpdateMessage
  | WsStageChangeMessage
  | WsSummaryMessage
  | WsErrorMessage

export interface RecommendationItem {
  id: string
  college_id?: string
  college_name: string
  major_name: string
  province: string
  city: string
  level: string
  match_score: number
  min_score?: number
  min_rank?: number
  subjects?: string
  reasons: string[]
  risk_level?: "safe" | "match" | "reach"
}

export interface PaginationData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface CompareMajorItem {
  college_name: string
  major_name: string
  level: string
  province: string
  city: string
  min_rank: number
  min_score: number
  subjects: string
  source_url: string
}

export interface CompareRecommendationItem {
  tenant_slug: string
  tenant_name: string
  majors: CompareMajorItem[]
  match_score: number
}

export interface CompareRecommendationsData {
  recommendations: CompareRecommendationItem[]
  profile_snapshot: ProfileSnapshot
  tenants_compared: number
}