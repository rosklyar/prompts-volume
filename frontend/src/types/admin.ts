/**
 * Admin dashboard types
 */

export interface UserWithBalance {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  available_balance: number
  expiring_soon_amount: number
  expiring_soon_at: string | null
}

export interface AdminUsersListResponse {
  users: UserWithBalance[]
  total: number
}

export interface AdminTopUpRequest {
  amount: number
  expires_at?: string | null
  note?: string | null
}

// ===== Admin Prompts Types =====

export interface BusinessDomain {
  id: number
  name: string
  description: string
}

export interface BusinessDomainsListResponse {
  business_domains: BusinessDomain[]
}

export interface Country {
  id: number
  name: string
  iso_code: string
}

export interface CountriesListResponse {
  countries: Country[]
}

export interface Topic {
  id: number
  title: string
  description: string
  business_domain_id: number
  business_domain_name: string
  country_id: number
  country_name: string
}

export interface TopicsListResponse {
  topics: Topic[]
}

export interface CreateTopicRequest {
  title: string
  description: string
  business_domain_id: number
  country_id: number
}

export interface PromptUploadResponse {
  total_uploaded: number
  topic_id: number
  topic_title: string
}

// ===== Prompts Analysis Types =====
// Uses shared types from batch-upload.ts: BatchPromptAnalysis, BatchAnalyzeResponse

export interface UploadPromptsRequest {
  prompts: string[]
  selected_indices: number[]
  topic_id: number
}

// ===== Pending Prompts Approval Types =====

export interface PendingPromptResponse {
  id: number
  prompt_text: string
  topic_id: number | null
  topic_title: string | null
  user_id: string
  group_ids: number[]
  group_titles: string[]
}

export interface PendingPromptsListResponse {
  prompts: PendingPromptResponse[]
  total: number
  limit: number
  offset: number
}

export interface ApprovalResultResponse {
  prompt_id: number
  new_status: string
  reviewed_by: string
  reviewed_at: string
}

export interface BatchApprovalResponse {
  results: ApprovalResultResponse[]
  success_count: number
  failed_ids: number[]
}
