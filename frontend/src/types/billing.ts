/**
 * TypeScript types for Billing/Credits feature
 * Supports the chargeable reports flow
 */

// ===== Balance Types =====

export interface UserBalance {
  available_balance: number // e.g., 10.00
  expiring_soon_amount: number // Amount expiring within 7 days
  expiring_soon_at: string | null // Earliest expiration date ISO string
}

// ===== Generation Price Types =====

export interface GenerationPrice {
  price: number // e.g., 1.00
  user_balance: number // User's current balance
  can_afford: boolean // Whether user can afford generation
}

// ===== Report Preview Types =====

export interface ReportPreview {
  total_prompts: number
  prompts_with_data: number
  prompts_awaiting: number
  fresh_evaluations: number // Count never charged for
  already_consumed: number // Previously paid
  estimated_cost: number // price * fresh_evaluations
  user_balance: number
  affordable_count: number // How many user can afford
  needs_top_up: boolean
}

// ===== Report Statistics Types (from backend) =====

export interface BrandVisibilityScore {
  brand_name: string
  is_target_brand: boolean
  prompts_with_mentions: number
  total_prompts: number
  visibility_percentage: number
}

export interface DomainMentionStat {
  name: string
  domain: string
  is_target_brand: boolean
  total_mentions: number
  prompts_with_mentions: number
}

export interface CitationDomainStat {
  name: string
  domain: string
  is_target_brand: boolean
  citation_count: number
}

export interface ReportStatistics {
  brand_visibility: BrandVisibilityScore[]
  domain_mentions: DomainMentionStat[]
  citation_domains: CitationDomainStat[]
}

// ===== Report Generation Types =====

export interface GenerateReportRequest {
  include_previous?: boolean // Include already-consumed evaluations
  title?: string
}

export interface GeneratedReportItem {
  prompt_id: number
  prompt_text: string
  evaluation_id: number | null
  status: "included" | "awaiting" | "skipped"
  is_fresh: boolean // Was this charged for in this report?
  amount_charged: number
  answer: {
    response: string
    citations: Array<{ url: string; text: string }>
    timestamp: string
  } | null
  brand_mentions: Array<{
    brand_name: string
    mentions: Array<{
      start: number
      end: number
      matched_text: string
      variation: string
    }>
  }> | null
  domain_mentions: Array<{
    name: string
    domain: string
    is_brand: boolean
    mentions: Array<{
      start: number
      end: number
      matched_text: string
      matched_domain: string
    }>
  }> | null
  completed_at: string | null
}

export interface GenerateReportResponse {
  id: number // Report ID
  total_cost: number // Only fresh evaluations charged
  items: GeneratedReportItem[]
  citation_leaderboard: {
    domains: Array<{
      path: string
      count: number
      is_domain: boolean
    }>
    subpaths: Array<{
      path: string
      count: number
      is_domain: boolean
    }>
    total_citations: number
  }
  statistics: ReportStatistics | null
  generated_at: string
}

// ===== Top-up Types =====

export interface TopUpRequest {
  amount: number
}

export interface TopUpResponse {
  transaction_id: string
  amount: number
  new_balance: number
  created_at: string
}

// ===== Transaction History Types =====

export interface Transaction {
  id: string
  type: "credit" | "debit"
  amount: number
  balance_after: number
  reason: string
  reference_type: string | null
  reference_id: string | null
  created_at: string
}

export interface TransactionsResponse {
  transactions: Transaction[]
  total: number
}

// ===== Report History Types =====

export interface ReportSummary {
  id: number
  group_id: number
  title: string | null
  created_at: string
  total_prompts: number
  prompts_with_data: number
  prompts_awaiting: number
  total_cost: number
}

export interface ReportListResponse {
  reports: ReportSummary[]
  total: number
}

// ===== Per-Prompt Freshness Types (Legacy) =====

export interface PromptFreshnessInfo {
  prompt_id: number
  prompt_text: string
  has_fresher_answer: boolean
  latest_answer_at: string | null
  previous_answer_at: string | null
  next_refresh_estimate: string
  has_in_progress_evaluation: boolean
}

export interface BrandChangeInfo {
  brand_changed: boolean
  competitors_changed: boolean
  current_brand: Record<string, unknown> | null
  current_competitors: Array<Record<string, unknown>> | null
  previous_brand: Record<string, unknown> | null
  previous_competitors: Array<Record<string, unknown>> | null
}

// ===== New Selection-based Types =====

export interface EvaluationOption {
  evaluation_id: number
  assistant_plan_id: number
  assistant_plan_name: string // e.g., "PLUS", "PRO"
  assistant_name: string // e.g., "ChatGPT", "Claude"
  completed_at: string // ISO datetime
  is_fresh: boolean // true if not yet consumed (will be charged)
  unit_price: string // decimal string e.g., "0.01"
}

export interface PromptSelectionInfo {
  prompt_id: number
  prompt_text: string
  available_options: EvaluationOption[]
  default_selection: number | null // evaluation_id
  was_awaiting_in_last_report: boolean
  last_report_evaluation_id: number | null
  last_report_evaluation_at: string | null
  has_in_progress_evaluation: boolean
}

export interface SelectableComparisonResponse {
  group_id: number
  last_report_at: string | null
  prompt_selections: PromptSelectionInfo[]
  total_prompts: number
  prompts_with_options: number
  prompts_awaiting: number
  brand_changes: BrandChangeInfo
  default_selection_count: number
  default_fresh_count: number
  default_estimated_cost: string // decimal string
  user_balance: string // decimal string
  price_per_evaluation: string // decimal string
  can_generate: boolean
  generation_disabled_reason: string | null // "no_new_data_or_changes" if disabled
}

export interface PromptSelection {
  prompt_id: number
  evaluation_id: number | null // null = skip/awaiting
}

export interface SelectiveGenerateReportRequest {
  title?: string
  selections: PromptSelection[]
  use_defaults_for_unspecified?: boolean // default: true
}

// ===== Enhanced Comparison Response (Legacy - now alias) =====

export interface EnhancedComparisonResponse {
  group_id: number
  last_report_at: string | null

  // Current state
  current_prompts_count: number
  current_evaluations_count: number

  // Comparison with last report
  new_prompts_added: number
  prompts_with_fresher_answers: number

  // Per-prompt freshness details
  prompt_freshness: PromptFreshnessInfo[]

  // Brand change detection
  brand_changes: BrandChangeInfo

  // Cost estimation (merged from preview)
  fresh_evaluations: number
  already_consumed: number
  estimated_cost: number
  user_balance: number
  affordable_count: number
  needs_top_up: boolean

  // Generate button state
  can_generate: boolean
  generation_disabled_reason: string | null
}

// The new response type for comparison endpoint
export type ComparisonResponse = SelectableComparisonResponse

// ===== Full Report Types (for viewing historical reports) =====

export interface FullReportResponse {
  id: number
  group_id: number
  title: string | null
  created_at: string
  total_prompts: number
  prompts_with_data: number
  prompts_awaiting: number
  total_evaluations_loaded: number
  total_cost: number
  items: GeneratedReportItem[]
  citation_leaderboard: {
    domains: Array<{
      path: string
      count: number
      is_domain: boolean
    }>
    subpaths: Array<{
      path: string
      count: number
      is_domain: boolean
    }>
    total_citations: number
  } | null
  statistics: ReportStatistics | null
  // Brand/competitor snapshots from when report was generated
  brand_snapshot: Record<string, unknown> | null
  competitors_snapshot: Array<Record<string, unknown>> | null
}
