/**
 * Types for execution queue and report data API.
 * Maps to backend models in src/execution/models/api_models.py
 */

// Simplified 3-state status for report generation
// - fresh: latest answer exists and is <=24h old
// - stale: latest answer exists but is >24h old
// - absent: no answer exists
export type PromptStatus = "fresh" | "stale" | "absent"

// Simplified per-prompt data for report generation UI
export interface PromptReportData {
  prompt_id: number
  prompt_text: string

  // Latest evaluation only (not a list)
  latest_evaluation_id: number | null
  latest_evaluation_at: string | null // ISO datetime

  // Simple 3-state status
  status: PromptStatus

  // Queue status (if already requested)
  pending_execution: boolean
  estimated_wait: string | null
}

// Simplified report data response
export interface ReportDataResponse {
  group_id: number
  prompts: PromptReportData[]

  // Summary counts
  total_prompts: number
  prompts_fresh: number
  prompts_stale: number
  prompts_absent: number

  // Queue info
  prompts_pending_execution: number
  global_queue_size: number
}

// === Request Fresh Execution ===

export interface RequestFreshExecutionRequest {
  prompt_ids: number[]
  assistant_id?: number // AI Assistant ID (default: 1 for ChatGPT)
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
