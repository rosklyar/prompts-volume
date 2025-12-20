import type {
  BrandVariation,
  EnrichedResultsResponse,
} from "@/types/groups"

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
  created_at: string
  updated_at: string
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

export interface EvaluationResultItem {
  prompt_id: number
  prompt_text: string
  evaluation_id: number | null
  status: string | null
  answer: EvaluationAnswer | null
  completed_at: string | null
}

export interface GetResultsResponse {
  results: EvaluationResultItem[]
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

  async createGroup(title: string): Promise<GroupSummary> {
    const response = await fetchWithAuth("/prompt-groups/api/v1/groups", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    })
    return response.json()
  },

  async updateGroup(groupId: number, title: string): Promise<GroupSummary> {
    const response = await fetchWithAuth(
      `/prompt-groups/api/v1/groups/${groupId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
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
  async getResults(
    assistantName: string,
    planName: string,
    promptIds: number[]
  ): Promise<GetResultsResponse> {
    const params = new URLSearchParams({
      assistant_name: assistantName,
      plan_name: planName,
      prompt_ids: promptIds.join(','),
    })
    const response = await fetchWithAuth(
      `/evaluations/api/v1/results?${params.toString()}`,
      {
        method: "GET",
      }
    )
    return response.json()
  },

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

  async getEnrichedResults(
    assistantName: string,
    planName: string,
    promptIds: number[],
    brands: BrandVariation[] | null
  ): Promise<EnrichedResultsResponse> {
    const params = new URLSearchParams()
    params.append("assistant_name", assistantName)
    params.append("plan_name", planName)
    // Backend expects multiple prompt_ids params, not comma-separated
    promptIds.forEach((id) => params.append("prompt_ids", id.toString()))

    const response = await fetchWithAuth(
      `/evaluations/api/v1/results/enriched?${params.toString()}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brands }),
      }
    )
    return response.json()
  },
}

export { ApiError }
