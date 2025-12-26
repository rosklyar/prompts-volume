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
  completed_at: string | null
}

export interface GenerateReportResponse {
  report_id: number
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
