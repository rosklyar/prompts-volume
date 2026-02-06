/**
 * TypeScript types for Dashboard API responses
 */

export type DashboardPeriod = "1d" | "7d" | "30d"

/** Date range for API requests */
export interface DateRangeParams {
  from_date: string  // ISO 8601
  to_date: string    // ISO 8601
}

export interface CompetitorVisibility {
  name: string
  domain: string | null
  visibility_percent: number
  is_target_brand: boolean
}

export interface SourceStat {
  domain: string
  citation_count: number
  citation_percent: number
  coverage_percent?: number
}

export interface PromptGap {
  prompt_id: number
  prompt_text: string
}

export interface DashboardResponse {
  group_id: number
  from_date: string      // ISO 8601
  to_date: string        // ISO 8601
  preset_used: DashboardPeriod | null
  reports_included: number
  assistant_name: string
  brand_name: string | null
  brand_visibility_percent: number
  competitors: CompetitorVisibility[]
  sources: SourceStat[]
  prompt_gaps: PromptGap[]
  prompt_gaps_count: number
}
