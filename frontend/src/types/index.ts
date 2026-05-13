export interface User {
  user_id: string
  username: string
}

export interface ChatMessage {
  type: string
  role?: string
  content?: string
  stage?: string
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
  career_vision?: string
  family_influence?: string
}

export interface Recommendation {
  rank: number
  college_name: string
  major_name: string
  level: string
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
