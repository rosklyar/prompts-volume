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

export interface Language {
  id: number
  name: string
  code: string
}

export interface Country {
  id: number
  name: string
  iso_code: string
  languages: Language[]
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

// ===== Onboarding Notifications Types =====

export interface OnboardingUserInfo {
  user_id: string
  email: string
  full_name: string | null
  onboarding_completed_at: string
  default_brand: {
    name: string
    domain?: string | null
    variations: string[]
  } | null
  default_competitors: {
    name: string
    domain?: string | null
    variations: string[]
  }[] | null
  country_name: string | null
  business_domain_name: string | null
}

export interface OnboardingNotificationsResponse {
  users: OnboardingUserInfo[]
  total: number
}

export interface OnboardingNotificationsCountResponse {
  count: number
}

// ===== User Deletion Types =====

export interface DatabaseCleanupDetail {
  database: "users_db" | "prompts_db" | "evals_db"
  deleted: Record<string, number>
  orphaned: Record<string, number>
}

export interface UserDeletionResponse {
  user_id: string
  user_email: string
  total_records_deleted: number
  details: DatabaseCleanupDetail[]
}

// ===== Admin Business Domains Types =====

export interface AdminBusinessDomain {
  id: number
  name: string
  description: string
  system_prompt_template: string | null
  is_active: boolean
}

export interface AdminBusinessDomainsListResponse {
  business_domains: AdminBusinessDomain[]
}

export interface CreateAdminBusinessDomainRequest {
  name: string
  description: string
  system_prompt_template: string
}

export interface UpdateAdminBusinessDomainRequest {
  description?: string
  system_prompt_template?: string
}
