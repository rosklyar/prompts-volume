/**
 * TypeScript types for Batch Prompts Upload feature
 */

// ===== Similar Match Types =====

export interface SimilarPromptMatch {
  prompt_id: number
  prompt_text: string
  similarity: number
}

export interface BatchPromptAnalysis {
  index: number
  input_text: string
  matches: SimilarPromptMatch[]
  has_matches: boolean
}

export interface BatchAnalyzeResponse {
  items: BatchPromptAnalysis[]
  total_prompts: number
  prompts_with_matches: number
  prompts_without_matches: number
}

// ===== Selection Types =====

export interface BatchPromptSelection {
  index: number
  use_existing: boolean
  selected_prompt_id: number | null
}

export interface BatchConfirmRequest {
  selections: BatchPromptSelection[]
  original_prompts: string[]
}

export interface BatchConfirmResponse {
  group_id: number
  bound_existing: number
  created_new: number
  skipped_duplicates: number
  total_processed: number
  prompt_ids: number[]
}

// ===== UI State Types =====

export type BatchUploadStep = "upload" | "review" | "complete"

export interface ParsedCSVResult {
  prompts: string[]
  errors: string[]
}
