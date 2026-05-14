export interface User {
  user_id: string
  username: string
}

export interface ChatMessage {
  type: string
  role?: string
  content?: string
  message?: string
  stage?: string
  from?: string
  to?: string
  field?: string
  value?: any
  confidence?: number
  profile_snapshot?: any
}

export interface ProfileSlot {
  score?: number
  subjects?: string
  riasec?: Record<string, number>
  values?: string[]
  region_pref?: string[]
  completeness?: string   // L1/L2/L3/L4
  engagement?: {
    trust_level: string
    willingness_to_share: number
    indicators: string[]
  }
}

export interface EvidenceItem {
  id: string
  dimension: string
  source_turn: number
  user_quote: string
  inferred_value: {
    dimension: string
    score: number
    rationale: string
  }
  confidence: number
}

export interface DimensionState {
  dimension: string
  label: string
  score?: number
  evidence_count: number
  confidence: number
  evidence?: EvidenceItem[]
}

export interface Recommendation {
  rank: number
  college_name: string
  major_name: string
  level: string
  city?: string
  category: string
  match_score: number
  reasons: Reason[]
  scores: {
    admission_probability: number
    interest_match: number
    career_prospect: number
  }
}

export interface Reason {
  type: string
  content: string
  source: string
  source_url?: string
  confidence?: number
}
