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
  is_duplicate: boolean  // True if best match >= 99.5% similarity
}

export interface BatchAnalyzeResponse {
  items: BatchPromptAnalysis[]
  total_prompts: number
  duplicates_count: number
  with_matches_count: number
}

// ===== Create Prompts Types (new shared endpoint) =====

export interface BatchCreateRequest {
  prompts: string[]          // Original prompt texts
  selected_indices: number[] // Indices to create
  topic_id?: number | null   // Optional topic
}

export interface BatchCreateResponse {
  created_count: number
  reused_count: number
  prompt_ids: number[]
  request_id: string
}

// ===== Legacy Types (for backward compatibility during migration) =====

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
