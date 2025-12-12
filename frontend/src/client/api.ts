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

export { ApiError }
