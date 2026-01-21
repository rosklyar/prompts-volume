import type { BrandInfo, CompetitorInfo } from "./groups"

export interface OnboardingStatusResponse {
  is_completed: boolean
  completed_at: string | null
  has_preferences: boolean
}

export interface UserPreferencesResponse {
  default_country_id: number
  default_business_domain_id: number | null
  default_brand: BrandInfo | null
  default_competitors: CompetitorInfo[]
  onboarding_status: OnboardingStatusResponse
}

export interface CompleteOnboardingRequest {
  default_country_id: number
  default_business_domain_id?: number
  default_brand: BrandInfo
  default_competitors?: CompetitorInfo[]
}

export interface SavePreferencesRequest {
  default_country_id: number
  default_business_domain_id?: number
  default_brand: BrandInfo
  default_competitors?: CompetitorInfo[]
}
