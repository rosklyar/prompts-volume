/**
 * Types for execution queue and report data API.
 * Maps to backend models in src/execution/models/api_models.py
 */

// Freshness categories based on time since last evaluation
export type FreshnessCategory = "fresh" | "stale" | "very_stale" | "none"

// An available evaluation (answer) for a prompt
export interface EvaluationOption {
  evaluation_id: number
  completed_at: string // ISO datetime
  is_consumed: boolean // User already paid for this
}

// Per-prompt data for report generation UI
export interface PromptReportData {
  prompt_id: number
  prompt_text: string

  // Available evaluations (answers)
  evaluations: EvaluationOption[]

  // Freshness metadata
  freshness_category: FreshnessCategory
  hours_since_latest: number | null

  // Default selection logic result
  default_evaluation_id: number | null
  show_ask_for_fresh: boolean
  auto_ask_for_fresh: boolean

  // Queue status (if already requested)
  pending_execution: boolean
  estimated_wait: string | null

  // Billing info
  is_consumed: boolean // User already paid for latest evaluation
}

// Full report data response
export interface ReportDataResponse {
  group_id: number
  prompts: PromptReportData[]

  // Summary counts
  total_prompts: number
  prompts_with_data: number
  prompts_fresh: number
  prompts_stale: number
  prompts_very_stale: number
  prompts_no_data: number

  // Queue info
  prompts_pending_execution: number
  global_queue_size: number
}

// === Request Fresh Execution ===

export interface RequestFreshExecutionRequest {
  prompt_ids: number[]
}

export interface QueuedItemInfo {
  prompt_id: number
  status: "queued" | "already_pending" | "in_progress"
  estimated_wait: string | null
}

export interface RequestFreshExecutionResponse {
  batch_id: string
  queued_count: number
  already_pending_count: number
  estimated_total_wait: string
  estimated_completion_at: string // ISO datetime
  items: QueuedItemInfo[]
}

// === Queue Status ===

export interface QueueStatusItem {
  prompt_id: number
  status: "pending" | "in_progress" | "completed" | "failed" | "cancelled"
  requested_at: string // ISO datetime
  estimated_wait: string | null
}

export interface CompletedItemInfo {
  prompt_id: number
  evaluation_id: number
  completed_at: string // ISO datetime
}

export interface QueueStatusResponse {
  pending_items: QueueStatusItem[]
  in_progress_items: QueueStatusItem[]
  recently_completed: CompletedItemInfo[]
  total_pending: number
  global_queue_size: number
}

// === Cancel Execution ===

export interface CancelExecutionResponse {
  cancelled_count: number
  prompt_ids: number[]
}
