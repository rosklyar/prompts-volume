import type { AggregatedCitationsResponse, BrandInfo, CompetitorInfo, TopicInput } from "@/types/groups"
import type { GeoAuditStoredResponse } from "@/types/geo-audit"
import type {
  OnboardingStatusResponse,
  UserPreferencesResponse,
  CompleteOnboardingRequest,
  SavePreferencesRequest,
  DiscoverCompetitorsRequest,
  DiscoverCompetitorsResponse,
} from "@/types/onboarding"
import type {
  BatchAnalyzeResponse,
  BatchCreateRequest,
  BatchCreateResponse,
} from "@/types/batch-upload"
import type {
  UserBalance,
  GenerationPrice,
  ReportPreview,
  GenerateReportResponse,
  TopUpRequest,
  TopUpResponse,
  TransactionsResponse,
  ReportListResponse,
  FullReportResponse,
  ComparisonResponse,
  SelectiveGenerateReportRequest,
  ReportRequest,
  CreateReportRequestBody,
  ReportRequestStatusResponse,
} from "@/types/billing"
import type {
  AdminUsersListResponse,
  AdminTopUpRequest,
  BusinessDomainsListResponse,
  CountriesListResponse,
  TopicsListResponse,
  CreateTopicRequest,
  Topic,
  PromptUploadResponse,
  UploadPromptsRequest,
  PendingPromptsListResponse,
  ApprovalResultResponse,
  BatchApprovalResponse,
  UserDeletionResponse,
  OnboardingNotificationsResponse,
  OnboardingNotificationsCountResponse,
  AdminBusinessDomainsListResponse,
  AdminBusinessDomain,
  CreateAdminBusinessDomainRequest,
  UpdateAdminBusinessDomainRequest,
} from "@/types/admin"
import type {
  ReportDataResponse,
  RequestFreshExecutionResponse,
} from "@/types/execution"
import type { AIAssistantListResponse } from "@/types/assistants"
import type { DashboardResponse } from "@/types/dashboard"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export interface UserPublic {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  email_verified: boolean
}

export interface SignupResponse {
  message: string
  email: string
}

export interface VerifyEmailResponse {
  message: string
  status: "success" | "already_verified"
}

export interface Token {
  access_token: string
  token_type: string
}

export interface OAuthLoginResponse extends Token {
  is_new_user: boolean
}

export interface UserRegister {
  email: string
  password: string
  full_name?: string
}

export interface UpdatePasswordRequest {
  current_password: string
  new_password: string
}

export interface MessageResponse {
  message: string
}

export interface SimilarPrompt {
  id: number
  prompt_text: string
  similarity: number
}

export interface SimilarPromptsResponse {
  query_text: string
  prompts: SimilarPrompt[]
  total_found: number
}

// Topic Prompts types
export interface TopicPrompt {
  id: number
  prompt_text: string
}

export interface TopicPromptsGroup {
  topic_id: number
  prompts: TopicPrompt[]
}

export interface TopicPromptsListResponse {
  topics: TopicPromptsGroup[]
}

export interface LoginCredentials {
  username: string
  password: string
}

class ApiError extends Error {
  status: number
  retryAfter: number | null

  constructor(status: number, message: string, retryAfter: number | null = null) {
    super(message)
    this.status = status
    this.retryAfter = retryAfter
    this.name = "ApiError"
  }
}

async function fetchWithAuth(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem("access_token")

  const headers: HeadersInit = {
    ...options.headers,
  }

  if (token) {
    ;(headers as Record<string, string>)["Authorization"] = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))

    // Auto-clear stale token on auth failures (invalid/expired token or deleted user)
    // 401 = user not found for token subject
    // 403 "Could not validate credentials" = invalid/expired JWT
    // Do NOT logout on 403 for permission errors (e.g. non-superuser hitting admin routes)
    const isInvalidSession =
      response.status === 401 ||
      (response.status === 403 &&
        errorData.detail === "Could not validate credentials")
    if (isInvalidSession) {
      localStorage.removeItem("access_token")
      localStorage.removeItem("admin_token")
      window.location.href = "/login"
    }

    const retryAfter = response.status === 429
      ? parseInt(response.headers.get("Retry-After") || "0", 10)
      : null
    throw new ApiError(response.status, errorData.detail || "Request failed", retryAfter)
  }

  return response
}

export const authApi = {
  async login(credentials: LoginCredentials): Promise<Token> {
    const formData = new URLSearchParams()
    formData.append("username", credentials.username)
    formData.append("password", credentials.password)

    const response = await fetch(`${API_URL}/api/v1/login/access-token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new ApiError(response.status, errorData.detail || "Login failed")
    }

    return response.json()
  },

  async signup(data: UserRegister): Promise<SignupResponse> {
    const response = await fetch(`${API_URL}/api/v1/users/signup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new ApiError(response.status, errorData.detail || "Signup failed")
    }

    return response.json()
  },

  async getCurrentUser(): Promise<UserPublic> {
    const response = await fetchWithAuth("/api/v1/users/me")
    return response.json()
  },

  async verifyEmail(token: string): Promise<VerifyEmailResponse> {
    const response = await fetch(
      `${API_URL}/api/v1/verify-email?token=${encodeURIComponent(token)}`
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new ApiError(
        response.status,
        errorData.detail || "Verification failed"
      )
    }

    return response.json()
  },

  async resendVerification(email: string): Promise<{ message: string }> {
    const response = await fetch(`${API_URL}/api/v1/resend-verification`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new ApiError(
        response.status,
        errorData.detail || "Failed to resend verification"
      )
    }

    return response.json()
  },

  async loginWithGoogle(idToken: string): Promise<OAuthLoginResponse> {
    const response = await fetch(`${API_URL}/api/v1/oauth/google`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id_token: idToken }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new ApiError(
        response.status,
        errorData.detail || "Google login failed"
      )
    }

    return response.json()
  },

  async updatePassword(data: UpdatePasswordRequest): Promise<MessageResponse> {
    const response = await fetchWithAuth("/api/v1/users/me/password", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })
    return response.json()
  },
}

export const promptsApi = {
  async getSimilarPrompts(
    text: string,
    k: number = 10,
    minSimilarity: number = 0.75
  ): Promise<SimilarPromptsResponse> {
    const params = new URLSearchParams({
      text,
      k: k.toString(),
      min_similarity: minSimilarity.toString(),
    })
    const response = await fetchWithAuth(`/prompts/api/v1/similar?${params}`)
    return response.json()
  },

  async getPromptsByTopicIds(topicIds: number[]): Promise<TopicPromptsListResponse> {
    const params = new URLSearchParams()
    topicIds.forEach((id) => params.append("topic_ids", id.toString()))
    const response = await fetchWithAuth(`/prompts/api/v1/prompts?${params}`)
    return response.json()
  },
}

// ===== Group Types =====

export interface CountryInfo {
  id: number
  name: string
  iso_code: string
}

export interface GroupSummary {
  id: number
  title: string
  prompt_count: number
  brand_name: string
  competitor_count: number
  topic_id: number
  topic_title: string
  country: CountryInfo
  country_locked: boolean
  created_at: string
  updated_at: string
}

export interface PromptInGroup {
  binding_id: number
  prompt_id: number
  prompt_text: string
  added_at: string
}

export interface GroupDetail {
  id: number
  title: string
  topic_id: number
  topic_title: string
  topic_description: string
  country: CountryInfo
  country_locked: boolean
  created_at: string
  updated_at: string
  brand: BrandInfo
  competitors: CompetitorInfo[]
  prompts: PromptInGroup[]
}

export interface GroupListResponse {
  groups: GroupSummary[]
  total: number
}

export interface AddPromptsResult {
  added_count: number
  skipped_count: number
  bindings: PromptInGroup[]
}

export interface RemovePromptsResult {
  removed_count: number
}

export interface ScheduleConfig {
  group_id: number
  enabled: boolean
  assistant_ids: number[] | null
  last_run_at: string | null
}

export interface AvailablePrompt {
  id: number
  prompt_text: string
}

export interface AvailablePromptsResponse {
  prompts: AvailablePrompt[]
  total: number
}

// ===== Evaluation Types =====

export interface Citation {
  url: string
  text: string
}

export interface EvaluationAnswer {
  response: string
  citations: Citation[]
  web_search_queries?: string[]
  timestamp: string
}

// ===== Batch Prompts API (shared) =====

export const batchApi = {
  /**
   * Analyze prompts for similarity matches
   */
  async analyze(prompts: string[]): Promise<BatchAnalyzeResponse> {
    const response = await fetchWithAuth("/prompts/api/v1/batch/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompts }),
    })
    return response.json()
  },

  /**
   * Create prompts via priority pipeline
   */
  async create(request: BatchCreateRequest): Promise<BatchCreateResponse> {
    const response = await fetchWithAuth("/prompts/api/v1/batch/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },
}

// ===== Groups API =====

export const groupsApi = {
  async getGroups(): Promise<GroupListResponse> {
    const response = await fetchWithAuth("/prompt-groups/api/v1/groups")
    return response.json()
  },

  async getGroupDetail(groupId: number): Promise<GroupDetail> {
    const response = await fetchWithAuth(
      `/prompt-groups/api/v1/groups/${groupId}`
    )
    return response.json()
  },

  async createGroup(
    title: string,
    topic: TopicInput | null,
    brand: BrandInfo,
    competitors?: CompetitorInfo[],
    countryId?: number
  ): Promise<GroupSummary> {
    const body: {
      title: string
      brand: BrandInfo
      topic?: TopicInput
      competitors?: CompetitorInfo[]
      country_id?: number
    } = { title, brand }

    // Only include topic if provided
    if (topic !== null) {
      body.topic = topic
    }

    if (competitors && competitors.length > 0) {
      body.competitors = competitors
    }

    // Include country_id if provided (required when no topic)
    if (countryId !== undefined) {
      body.country_id = countryId
    }

    const response = await fetchWithAuth("/prompt-groups/api/v1/groups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    return response.json()
  },

  async updateGroup(
    groupId: number,
    data: {
      title?: string
      brand?: BrandInfo
      competitors?: CompetitorInfo[] | null
      country_id?: number
    }
  ): Promise<GroupSummary> {
    const response = await fetchWithAuth(
      `/prompt-groups/api/v1/groups/${groupId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }
    )
    return response.json()
  },

  async deleteGroup(groupId: number): Promise<void> {
    await fetchWithAuth(`/prompt-groups/api/v1/groups/${groupId}`, {
      method: "DELETE",
    })
  },

  async addPromptsToGroup(
    groupId: number,
    promptIds: number[]
  ): Promise<AddPromptsResult> {
    const response = await fetchWithAuth(
      `/prompt-groups/api/v1/groups/${groupId}/prompts`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt_ids: promptIds }),
      }
    )
    return response.json()
  },

  async removePromptsFromGroup(
    groupId: number,
    promptIds: number[]
  ): Promise<RemovePromptsResult> {
    const response = await fetchWithAuth(
      `/prompt-groups/api/v1/groups/${groupId}/prompts`,
      {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt_ids: promptIds }),
      }
    )
    return response.json()
  },

  async getGroupSchedule(groupId: number): Promise<ScheduleConfig> {
    const response = await fetchWithAuth(
      `/prompt-groups/api/v1/groups/${groupId}/schedule`
    )
    return response.json()
  },

  async setGroupSchedule(
    groupId: number,
    enabled: boolean,
    assistantIds?: number[]
  ): Promise<ScheduleConfig> {
    const response = await fetchWithAuth(
      `/prompt-groups/api/v1/groups/${groupId}/schedule`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled,
          assistant_ids: assistantIds,
        }),
      }
    )
    return response.json()
  },

  async getAvailablePrompts(groupId: number): Promise<AvailablePromptsResponse> {
    const response = await fetchWithAuth(
      `/prompt-groups/api/v1/groups/${groupId}/available-prompts`
    )
    return response.json()
  },

  async addGSCPromptsToGroup(
    groupId: number,
    prompts: string[]
  ): Promise<{ prompts_added: number }> {
    const response = await fetchWithAuth(
      `/prompt-groups/api/v1/groups/${groupId}/gsc-prompts`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompts }),
      }
    )
    return response.json()
  },
}

// ===== Billing API =====

export const billingApi = {
  /**
   * Get current user balance
   */
  async getBalance(): Promise<UserBalance> {
    const response = await fetchWithAuth("/billing/api/v1/balance")
    return response.json()
  },

  /**
   * Top up user balance
   */
  async topUp(request: TopUpRequest): Promise<TopUpResponse> {
    const response = await fetchWithAuth("/billing/api/v1/top-up", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  /**
   * Get transaction history
   */
  async getTransactions(
    limit: number = 20,
    offset: number = 0
  ): Promise<TransactionsResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    })
    const response = await fetchWithAuth(
      `/billing/api/v1/transactions?${params}`
    )
    return response.json()
  },

  /**
   * Get generation price and affordability check
   */
  async getGenerationPrice(): Promise<GenerationPrice> {
    const response = await fetchWithAuth("/billing/api/v1/generation/price")
    return response.json()
  },
}

// ===== Reference Data API (all authenticated users) =====

export const referenceApi = {
  /**
   * Get all business domains
   */
  async getBusinessDomains(): Promise<BusinessDomainsListResponse> {
    const response = await fetchWithAuth("/api/v1/reference/business-domains")
    return response.json()
  },

  /**
   * Get all countries
   */
  async getCountries(): Promise<CountriesListResponse> {
    const response = await fetchWithAuth("/api/v1/reference/countries")
    return response.json()
  },

  /**
   * Get topics with optional filtering
   */
  async getTopics(
    businessDomainId?: number,
    countryId?: number
  ): Promise<TopicsListResponse> {
    const params = new URLSearchParams()
    if (businessDomainId !== undefined) {
      params.append("business_domain_id", businessDomainId.toString())
    }
    if (countryId !== undefined) {
      params.append("country_id", countryId.toString())
    }
    const response = await fetchWithAuth(`/api/v1/reference/topics?${params}`)
    return response.json()
  },
}

// ===== Admin API =====

export const adminApi = {
  /**
   * Get users with balances (admin only)
   */
  async getUsers(
    search?: string,
    limit: number = 20,
    offset: number = 0
  ): Promise<AdminUsersListResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      skip: offset.toString(),
    })
    if (search) {
      params.append("search", search)
    }
    const response = await fetchWithAuth(`/billing/api/v1/admin/users?${params}`)
    return response.json()
  },

  /**
   * Top up a user's balance (admin only)
   */
  async topUpUser(
    userId: string,
    request: AdminTopUpRequest
  ): Promise<TopUpResponse> {
    const response = await fetchWithAuth(
      `/billing/api/v1/admin/users/${userId}/top-up`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }
    )
    return response.json()
  },

  /**
   * Get all business domains (delegates to referenceApi)
   */
  async getBusinessDomains(): Promise<BusinessDomainsListResponse> {
    return referenceApi.getBusinessDomains()
  },

  /**
   * Get all countries (delegates to referenceApi)
   */
  async getCountries(): Promise<CountriesListResponse> {
    return referenceApi.getCountries()
  },

  /**
   * Get topics with optional filtering (delegates to referenceApi)
   */
  async getTopics(
    businessDomainId?: number,
    countryId?: number
  ): Promise<TopicsListResponse> {
    return referenceApi.getTopics(businessDomainId, countryId)
  },

  /**
   * Create a new topic (admin only)
   */
  async createTopic(request: CreateTopicRequest): Promise<Topic> {
    const response = await fetchWithAuth("/admin/api/v1/topics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  /**
   * Analyze prompts for similarity before uploading (uses shared endpoint)
   */
  async analyzePrompts(prompts: string[]): Promise<BatchAnalyzeResponse> {
    return batchApi.analyze(prompts)
  },

  /**
   * Upload selected prompts (admin only)
   */
  async uploadPrompts(request: UploadPromptsRequest): Promise<PromptUploadResponse> {
    const response = await fetchWithAuth("/admin/api/v1/prompts/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  /**
   * Get pending prompts for approval (admin only)
   */
  async getPendingPrompts(
    limit: number = 20,
    offset: number = 0
  ): Promise<PendingPromptsListResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    })
    const response = await fetchWithAuth(`/admin/api/v1/prompts/pending?${params}`)
    return response.json()
  },

  /**
   * Approve a single prompt (admin only)
   */
  async approvePrompt(
    promptId: number,
    topicId?: number | null
  ): Promise<ApprovalResultResponse> {
    const body: { topic_id?: number | null } = {}
    if (topicId !== undefined && topicId !== null) {
      body.topic_id = topicId
    }
    const response = await fetchWithAuth(`/admin/api/v1/prompts/${promptId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    return response.json()
  },

  /**
   * Reject a single prompt (admin only)
   */
  async rejectPrompt(promptId: number): Promise<ApprovalResultResponse> {
    const response = await fetchWithAuth(`/admin/api/v1/prompts/${promptId}/reject`, {
      method: "POST",
    })
    return response.json()
  },

  /**
   * Batch approve prompts (admin only)
   */
  async batchApprovePrompts(
    promptIds: number[],
    topicId?: number | null
  ): Promise<BatchApprovalResponse> {
    const body: { prompt_ids: number[]; topic_id?: number | null } = {
      prompt_ids: promptIds,
    }
    if (topicId !== undefined && topicId !== null) {
      body.topic_id = topicId
    }
    const response = await fetchWithAuth("/admin/api/v1/prompts/batch/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    return response.json()
  },

  /**
   * Batch reject prompts (admin only)
   */
  async batchRejectPrompts(promptIds: number[]): Promise<BatchApprovalResponse> {
    const response = await fetchWithAuth("/admin/api/v1/prompts/batch/reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt_ids: promptIds }),
    })
    return response.json()
  },

  /**
   * Hard delete a user and all their data (admin only)
   */
  async hardDeleteUser(userId: string): Promise<UserDeletionResponse> {
    const response = await fetchWithAuth(
      `/admin/api/v1/users/${userId}/hard-delete`,
      { method: "DELETE" }
    )
    return response.json()
  },

  /**
   * Impersonate a user (admin only) — returns a 1-hour JWT
   */
  async impersonateUser(userId: string): Promise<Token> {
    const response = await fetchWithAuth(
      `/admin/api/v1/impersonate/${userId}`,
      { method: "POST" }
    )
    return response.json()
  },

  /**
   * Get users who completed onboarding but haven't been set up (admin only)
   */
  async getOnboardingNotifications(
    limit: number = 20,
    offset: number = 0
  ): Promise<OnboardingNotificationsResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    })
    const response = await fetchWithAuth(
      `/admin/api/v1/onboarding-notifications?${params}`
    )
    return response.json()
  },

  /**
   * Get count of pending onboarding notifications (admin only)
   */
  async getOnboardingNotificationsCount(): Promise<OnboardingNotificationsCountResponse> {
    const response = await fetchWithAuth(
      "/admin/api/v1/onboarding-notifications/count"
    )
    return response.json()
  },

  /**
   * Mark a user's admin setup as complete (admin only)
   */
  async markUserSetupComplete(userId: string): Promise<{ message: string }> {
    const response = await fetchWithAuth(
      `/admin/api/v1/users/${userId}/mark-setup`,
      { method: "POST" }
    )
    return response.json()
  },

  /**
   * List all business domains including inactive (admin only)
   */
  async listBusinessDomains(): Promise<AdminBusinessDomainsListResponse> {
    const response = await fetchWithAuth("/admin/api/v1/business-domains")
    return response.json()
  },

  /**
   * Get default system prompt template
   */
  async getDefaultDomainTemplate(): Promise<{ template: string }> {
    const response = await fetchWithAuth("/admin/api/v1/business-domains/default-template")
    return response.json()
  },

  /**
   * Create a new business domain (admin only)
   */
  async createBusinessDomain(request: CreateAdminBusinessDomainRequest): Promise<AdminBusinessDomain> {
    const response = await fetchWithAuth("/admin/api/v1/business-domains", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  /**
   * Update a business domain (admin only)
   */
  async updateBusinessDomain(domainId: number, request: UpdateAdminBusinessDomainRequest): Promise<AdminBusinessDomain> {
    const response = await fetchWithAuth(`/admin/api/v1/business-domains/${domainId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  /**
   * Deactivate a business domain (admin only)
   */
  async deactivateBusinessDomain(domainId: number): Promise<void> {
    await fetchWithAuth(`/admin/api/v1/business-domains/${domainId}`, {
      method: "DELETE",
    })
  },
}

// ===== Reports API =====

export const reportsApi = {
  /**
   * Get report data with freshness metadata for report generation UI
   * @param groupId - The group ID
   * @param assistantId - AI Assistant ID (default: 1 for ChatGPT)
   */
  async getReportData(
    groupId: number,
    assistantId: number = 1
  ): Promise<ReportDataResponse> {
    const params = new URLSearchParams({
      assistant_id: assistantId.toString(),
    })
    const response = await fetchWithAuth(
      `/reports/api/v1/groups/${groupId}/report-data?${params}`
    )
    return response.json()
  },

  /**
   * Get report preview with cost breakdown (no charge)
   * @deprecated Use getReportData instead
   */
  async getPreview(groupId: number): Promise<ReportPreview> {
    const response = await fetchWithAuth(
      `/reports/api/v1/groups/${groupId}/preview`
    )
    return response.json()
  },

  /**
   * Generate report with evaluation selections (charges for fresh evaluations)
   */
  async generate(
    groupId: number,
    request: SelectiveGenerateReportRequest
  ): Promise<GenerateReportResponse> {
    const response = await fetchWithAuth(
      `/reports/api/v1/groups/${groupId}/generate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }
    )
    return response.json()
  },

  /**
   * List all reports for a group with pagination and optional filters
   */
  async listReports(
    groupId: number,
    limit: number = 20,
    offset: number = 0,
    filters?: {
      assistantId?: number
      fromDate?: string // ISO date string
      toDate?: string // ISO date string
    }
  ): Promise<ReportListResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    })
    if (filters?.assistantId !== undefined) {
      params.set("assistant_id", filters.assistantId.toString())
    }
    if (filters?.fromDate) {
      params.set("from_date", filters.fromDate)
    }
    if (filters?.toDate) {
      params.set("to_date", filters.toDate)
    }
    const response = await fetchWithAuth(
      `/reports/api/v1/groups/${groupId}/reports?${params}`
    )
    return response.json()
  },

  /**
   * Get a specific report with full items and data
   */
  async getReport(
    groupId: number,
    reportId: number
  ): Promise<FullReportResponse> {
    const response = await fetchWithAuth(
      `/reports/api/v1/groups/${groupId}/reports/${reportId}`
    )
    return response.json()
  },

  /**
   * Compare current data with latest report (for "no diff" detection)
   */
  async compare(groupId: number): Promise<ComparisonResponse> {
    const response = await fetchWithAuth(
      `/reports/api/v1/groups/${groupId}/compare`
    )
    return response.json()
  },

  /**
   * Export report as JSON file (returns blob and filename for download)
   */
  async exportJson(
    groupId: number,
    reportId: number
  ): Promise<{ blob: Blob; filename: string }> {
    const response = await fetchWithAuth(
      `/reports/api/v1/groups/${groupId}/reports/${reportId}/export/json`
    )
    if (!response.ok) {
      throw new Error("Export failed")
    }
    const blob = await response.blob()
    const contentDisposition = response.headers.get("Content-Disposition")
    const filenameMatch = contentDisposition?.match(/filename="(.+)"/)
    const filename = filenameMatch?.[1] ?? `report_${reportId}.json`
    return { blob, filename }
  },

  /**
   * Get aggregated citation leaderboard across reports for a group
   * @param groupId - The group ID
   * @param options - Either period (preset) OR fromDate/toDate (custom range)
   * @param assistantId - Optional assistant ID filter
   */
  async getCitationsLeaderboard(
    groupId: number,
    options: { period: "1d" | "7d" | "30d" } | { fromDate: string; toDate: string },
    assistantId?: number
  ): Promise<AggregatedCitationsResponse> {
    const params = new URLSearchParams()
    if ("period" in options) {
      params.set("period", options.period)
    } else {
      params.set("from_date", options.fromDate)
      params.set("to_date", options.toDate)
    }
    if (assistantId !== undefined) {
      params.set("assistant_id", assistantId.toString())
    }
    const response = await fetchWithAuth(
      `/reports/api/v1/groups/${groupId}/citations-leaderboard?${params}`
    )
    return response.json()
  },

  /**
   * Get dashboard analytics aggregated across reports in a time period
   * @param groupId - The group ID
   * @param assistantId - AI Assistant ID (required)
   * @param options - Either period (preset) OR fromDate/toDate (custom range). Defaults to last 30 days.
   */
  async getDashboard(
    groupId: number,
    assistantId: number,
    options?: { period: "1d" | "7d" | "30d" } | { fromDate: string; toDate: string }
  ): Promise<DashboardResponse> {
    const params = new URLSearchParams({
      assistant_id: assistantId.toString(),
    })
    if (options) {
      if ("period" in options) {
        params.set("period", options.period)
      } else {
        params.set("from_date", options.fromDate)
        params.set("to_date", options.toDate)
      }
    }
    // If no options provided, backend defaults to last 30 days
    const response = await fetchWithAuth(
      `/reports/api/v1/groups/${groupId}/dashboard?${params}`
    )
    return response.json()
  },

  // ===== Report Request (Unified Manual/Scheduled) =====

  /**
   * Create a new report request for a group
   * Triggers BrightData for stale/absent prompts and waits for completion
   */
  async createRequest(
    groupId: number,
    body: CreateReportRequestBody = {}
  ): Promise<ReportRequest> {
    const response = await fetchWithAuth(
      `/reports/api/v1/groups/${groupId}/request`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    )
    return response.json()
  },

  /**
   * Get the status of any pending report request for a group
   * @param assistantId - Optional assistant ID to filter by specific assistant
   */
  async getRequestStatus(
    groupId: number,
    assistantId?: number
  ): Promise<ReportRequestStatusResponse> {
    const params = new URLSearchParams()
    if (assistantId !== undefined) {
      params.set("assistant_id", String(assistantId))
    }
    const queryString = params.toString()
    const url = `/reports/api/v1/groups/${groupId}/request-status${queryString ? `?${queryString}` : ""}`
    const response = await fetchWithAuth(url)
    return response.json()
  },

  /**
   * Cancel a pending report request for a group
   * @param assistantId - Optional assistant ID to filter by specific assistant
   */
  async cancelRequest(groupId: number, assistantId?: number): Promise<void> {
    const params = new URLSearchParams()
    if (assistantId !== undefined) {
      params.set("assistant_id", String(assistantId))
    }
    const queryString = params.toString()
    const url = `/reports/api/v1/groups/${groupId}/request${queryString ? `?${queryString}` : ""}`
    await fetchWithAuth(url, {
      method: "DELETE",
    })
  },
}

// ===== Execution Queue API =====

export const executionApi = {
  /**
   * Request fresh execution for prompts
   * @param promptIds - Array of prompt IDs to request fresh evaluation for
   * @param countryId - Country ID for scraping (determines geo-location for results)
   * @param assistantId - AI Assistant ID (default: 1 for ChatGPT)
   */
  async requestFresh(
    promptIds: number[],
    countryId: number,
    assistantId: number = 1
  ): Promise<RequestFreshExecutionResponse> {
    const response = await fetchWithAuth("/execution/api/v1/request-fresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt_ids: promptIds,
        country_id: countryId,
        assistant_id: assistantId,
      }),
    })
    return response.json()
  },
}

// ===== Assistants API =====

export const assistantsApi = {
  /**
   * Get all available AI assistants
   */
  async listAssistants(): Promise<AIAssistantListResponse> {
    const response = await fetchWithAuth("/assistants/api/v1/assistants")
    return response.json()
  },
}

// ===== Onboarding API =====

export const onboardingApi = {
  /**
   * Get onboarding status for current user
   */
  async getStatus(): Promise<OnboardingStatusResponse> {
    const response = await fetchWithAuth("/onboarding/api/v1/status")
    return response.json()
  },

  /**
   * Complete onboarding with brand and competitor preferences
   */
  async complete(request: CompleteOnboardingRequest): Promise<UserPreferencesResponse> {
    const response = await fetchWithAuth("/onboarding/api/v1/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  /**
   * Get user preferences (for settings page and group prefill)
   */
  async getPreferences(): Promise<UserPreferencesResponse> {
    const response = await fetchWithAuth("/onboarding/api/v1/preferences")
    return response.json()
  },

  /**
   * Update user preferences (from settings page)
   */
  async updatePreferences(request: SavePreferencesRequest): Promise<UserPreferencesResponse> {
    const response = await fetchWithAuth("/onboarding/api/v1/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  /**
   * Discover competitors using AI web search
   */
  async discoverCompetitors(request: DiscoverCompetitorsRequest): Promise<DiscoverCompetitorsResponse> {
    const response = await fetchWithAuth("/onboarding/api/v1/discover-competitors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },
}

// ===== GSC (Google Search Console) API =====

export interface GSCSiteInfo {
  site_url: string
  permission_level: "siteOwner" | "siteFullUser" | "siteRestrictedUser" | "siteUnverifiedUser"
}

export interface GSCConnectionStatus {
  is_connected: boolean
  connected_at: string | null
  sites: GSCSiteInfo[] | null
}

export interface GSCAuthInitResponse {
  auth_url: string
}

export interface GSCDisconnectResponse {
  message: string
}

export interface GSCSearchAnalyticsRequest {
  site_url: string
  start_date: string  // YYYY-MM-DD
  end_date: string    // YYYY-MM-DD
  row_limit?: number
}

export interface GSCSearchQueryRow {
  keys: string[]  // Query text (first element is the query)
  clicks: number
  impressions: number
  ctr: number
  position: number
}

export interface GSCSearchAnalyticsResponse {
  rows: GSCSearchQueryRow[]
}

// GSC Onboarding types
export interface GSCPropertyMatchRequest {
  brand_domain: string
}

export interface GSCPropertyMatchResponse {
  match_type: "exact" | "partial" | "multiple" | "none"
  matched_property: string | null
  available_properties: GSCSiteInfo[]
}

export interface GSCKeywordExtractRequest {
  site_url: string
  min_word_count?: number
  result_limit?: number
  generate_prompts?: boolean
  country_id?: number
  business_domain?: string
}

export interface GSCKeywordInfo {
  query: string
  clicks: number
  impressions: number
  ctr: number
  position: number
}

export interface GeneratedPromptResponse {
  prompt: string
  source_keyword: string
}

export interface GSCKeywordExtractResponse {
  keywords: GSCKeywordInfo[]
  total_fetched: number
  total_after_filter: number
  generated_prompts?: GeneratedPromptResponse[]
}

export interface GSCCreatePromptsRequest {
  prompts: string[]
  group_title: string
  country_id: number
  brand: {
    name: string
    domain?: string | null
    variations: string[]
  }
  competitors?: {
    name: string
    domain?: string | null
    variations: string[]
  }[] | null
}

export interface GSCCreatePromptsResponse {
  group_id: number
  group_title: string
  prompts_created: number
  prompt_ids: number[]
}

// Two-step GSC flow types
export type GSCSortBy = "clicks" | "impressions" | "ctr" | "position"

export interface GSCFetchKeywordsRequest {
  site_url: string
  sort_by?: GSCSortBy
  result_limit?: number
}

export interface GSCFetchKeywordsResponse {
  keywords: GSCKeywordInfo[]
  total_fetched: number
}

export interface GSCGeneratePromptsRequest {
  keywords: string[]
  country_id: number
  business_domain?: string
}

export interface GSCGeneratePromptsResponse {
  prompts: string[]
}

export const gscApi = {
  /**
   * Initiate GSC OAuth flow - returns URL to redirect user to
   * @param redirectUri - Optional URL to redirect to after OAuth completes
   */
  async initiateAuth(redirectUri?: string): Promise<GSCAuthInitResponse> {
    const params = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : ""
    const response = await fetchWithAuth(`/api/v1/gsc/auth/initiate${params}`)
    return response.json()
  },

  /**
   * Get GSC connection status and list of properties
   */
  async getStatus(): Promise<GSCConnectionStatus> {
    const response = await fetchWithAuth("/api/v1/gsc/status")
    return response.json()
  },

  /**
   * Disconnect GSC account
   */
  async disconnect(): Promise<GSCDisconnectResponse> {
    const response = await fetchWithAuth("/api/v1/gsc/disconnect", {
      method: "DELETE",
    })
    return response.json()
  },

  /**
   * Get search analytics data for a GSC property
   */
  async getSearchAnalytics(request: GSCSearchAnalyticsRequest): Promise<GSCSearchAnalyticsResponse> {
    const response = await fetchWithAuth("/api/v1/gsc/search-analytics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  // ===== GSC Onboarding endpoints =====

  /**
   * Match brand domain to a GSC property
   */
  async matchProperty(request: GSCPropertyMatchRequest): Promise<GSCPropertyMatchResponse> {
    const response = await fetchWithAuth("/onboarding/api/v1/gsc/match-property", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  /**
   * Extract long-tail keywords from GSC search analytics
   * When generate_prompts=true and country_id is provided, returns AI-generated prompts
   */
  async extractKeywords(request: GSCKeywordExtractRequest): Promise<GSCKeywordExtractResponse> {
    const response = await fetchWithAuth("/onboarding/api/v1/gsc/extract-keywords", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  /**
   * Create prompts and group from selected prompts
   */
  async createPromptsFromGSC(request: GSCCreatePromptsRequest): Promise<GSCCreatePromptsResponse> {
    const response = await fetchWithAuth("/onboarding/api/v1/gsc/create-prompts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  // ===== Two-step GSC flow endpoints =====

  /**
   * Fetch ALL keywords from GSC (no word count filter)
   * Step 1 of two-step flow: user selects which keywords to use
   */
  async fetchKeywords(request: GSCFetchKeywordsRequest): Promise<GSCFetchKeywordsResponse> {
    const response = await fetchWithAuth("/onboarding/api/v1/gsc/fetch-keywords", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  /**
   * Generate prompts from selected keywords (max 20)
   * Step 2 of two-step flow: generates 3 prompts per keyword
   */
  async generatePromptsFromKeywords(request: GSCGeneratePromptsRequest): Promise<GSCGeneratePromptsResponse> {
    const response = await fetchWithAuth("/onboarding/api/v1/gsc/generate-prompts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },
}

// ===== Keyword Inspiration API =====

import type {
  DiscoverClustersRequest,
  ClusterKeywordsResponse,
  GeneratePromptsRequest,
  GeneratePromptsResponse,
  ConfirmGroupsRequest,
  CreateGroupsResponse,
} from "@/types/keyword-inspiration"

export const keywordInspirationApi = {
  async discoverClusters(request: DiscoverClustersRequest): Promise<ClusterKeywordsResponse> {
    const response = await fetchWithAuth("/keyword-inspiration/api/v1/discover-clusters", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  async generatePrompts(request: GeneratePromptsRequest): Promise<GeneratePromptsResponse> {
    const response = await fetchWithAuth("/keyword-inspiration/api/v1/generate-prompts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },

  async createGroups(request: ConfirmGroupsRequest): Promise<CreateGroupsResponse> {
    const response = await fetchWithAuth("/keyword-inspiration/api/v1/create-groups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    })
    return response.json()
  },
}

export const geoAuditApi = {
  async getLatest(): Promise<GeoAuditStoredResponse> {
    const response = await fetchWithAuth("/api/v1/geo-audit")
    return response.json()
  },

  async runAudit(url?: string): Promise<GeoAuditStoredResponse> {
    const response = await fetchWithAuth("/api/v1/geo-audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: url ? JSON.stringify({ url }) : undefined,
    })
    return response.json()
  },
}

export { ApiError }
