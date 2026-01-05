import type { BrandInfo, CompetitorInfo, TopicInput } from "@/types/groups"
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
} from "@/types/admin"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000"

export interface UserPublic {
  id: string
  email: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
}

export interface Token {
  access_token: string
  token_type: string
}

export interface UserRegister {
  email: string
  password: string
  full_name?: string
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

export interface LoginCredentials {
  username: string
  password: string
}

class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
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
    throw new ApiError(response.status, errorData.detail || "Request failed")
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

  async signup(data: UserRegister): Promise<UserPublic> {
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
}

// ===== Group Types =====

export interface GroupSummary {
  id: number
  title: string
  prompt_count: number
  brand_name: string
  competitor_count: number
  topic_id: number
  topic_title: string
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

// ===== Evaluation Types =====

export interface Citation {
  url: string
  text: string
}

export interface EvaluationAnswer {
  response: string
  citations: Citation[]
  timestamp: string
}

export interface PriorityPromptResult {
  prompt_id: number
  prompt_text: string
  topic_id: number | null
  was_duplicate: boolean
  similarity_score: number | null
}

export interface AddPriorityPromptsResponse {
  created_count: number
  reused_count: number
  total_count: number
  prompts: PriorityPromptResult[]
  request_id: string
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
    topic: TopicInput,
    brand: BrandInfo,
    competitors?: CompetitorInfo[]
  ): Promise<GroupSummary> {
    const response = await fetchWithAuth("/prompt-groups/api/v1/groups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, topic, brand, competitors }),
    })
    return response.json()
  },

  async updateGroup(
    groupId: number,
    data: {
      title?: string
      brand?: BrandInfo
      competitors?: CompetitorInfo[] | null
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
}

// ===== Evaluations API =====

export const evaluationsApi = {
  async addPriorityPrompts(
    prompts: string[],
    topicId?: number
  ): Promise<AddPriorityPromptsResponse> {
    const response = await fetchWithAuth(
      "/evaluations/api/v1/priority-prompts",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompts: prompts.map((prompt_text) => ({ prompt_text })),
          topic_id: topicId,
        }),
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
}

// ===== Reports API =====

export const reportsApi = {
  /**
   * Get report preview with cost breakdown (no charge)
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
   * List all reports for a group with pagination
   */
  async listReports(
    groupId: number,
    limit: number = 20,
    offset: number = 0
  ): Promise<ReportListResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    })
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
}

// ===== Inspiration API Types =====

import type {
  MetaInfoResponse,
  TopicPromptsResponse,
  GeneratePromptsResponse,
} from "@/types/inspiration"

export interface GeneratePromptsRequest {
  company_url: string
  iso_country_code: string
  topics: string[]
  brand_variations: string[]
}

// ===== Inspiration API =====

export const inspirationApi = {
  /**
   * Get meta info with matched/unmatched topics and brand variations
   */
  async getMetaInfo(
    companyUrl: string,
    isoCountryCode: string
  ): Promise<MetaInfoResponse> {
    const params = new URLSearchParams({
      company_url: companyUrl,
      iso_country_code: isoCountryCode,
    })
    const response = await fetchWithAuth(`/prompts/api/v1/meta-info?${params}`)
    return response.json()
  },

  /**
   * Get prompts from DB for matched topics (fast ~50ms)
   */
  async getTopicPrompts(topicIds: number[]): Promise<TopicPromptsResponse> {
    const params = new URLSearchParams()
    topicIds.forEach((id) => params.append("topic_ids", id.toString()))
    const response = await fetchWithAuth(`/prompts/api/v1/prompts?${params}`)
    return response.json()
  },

  /**
   * Generate prompts for unmatched topics (slow 30-60s)
   */
  async generatePrompts(
    request: GeneratePromptsRequest
  ): Promise<GeneratePromptsResponse> {
    const params = new URLSearchParams({
      company_url: request.company_url,
      iso_country_code: request.iso_country_code,
    })
    request.topics.forEach((t) => params.append("topics", t))
    request.brand_variations.forEach((b) => params.append("brand_variations", b))
    const response = await fetchWithAuth(`/prompts/api/v1/generate?${params}`)
    return response.json()
  },
}

export { ApiError }
