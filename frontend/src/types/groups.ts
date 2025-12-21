/**
 * TypeScript types for Prompt Groups feature
 */

// ===== Group Types =====

export interface GroupSummary {
  id: number
  title: string
  prompt_count: number
  brand_count: number
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
  brands: BrandVariation[] | null
  prompts: PromptInGroup[]
}

// ===== Quarantine Types =====

export interface QuarantinePrompt {
  prompt_id: number
  prompt_text: string
  added_at: string
  isCustom: boolean
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

// ===== Brand Types =====

export interface BrandVariation {
  name: string
  variations: string[]
}

export interface MentionPosition {
  start: number
  end: number
  matched_text: string
  variation: string
}

export interface BrandMentionResult {
  brand_name: string
  mentions: MentionPosition[]
}

// ===== Citation Leaderboard Types =====

export interface CitationCountItem {
  path: string
  count: number
  is_domain: boolean
}

export interface CitationLeaderboard {
  items: CitationCountItem[]
  total_citations: number
}

// ===== Enriched Result Types =====

export interface EnrichedEvaluationResultItem extends EvaluationResultItem {
  brand_mentions: BrandMentionResult[] | null
}

export interface EnrichedResultsResponse {
  results: EnrichedEvaluationResultItem[]
  citation_leaderboard: CitationLeaderboard
}

export interface EnrichedResultsRequest {
  brands?: BrandVariation[] | null
  group_id?: number
}

// ===== Visibility Score Types =====

export interface BrandVisibilityScore {
  brand_name: string
  prompts_with_mentions: number
  total_prompts: number
  visibility_percentage: number
}

export interface PriorityPromptItem {
  prompt_text: string
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

// ===== UI State Types =====

export interface PromptWithAnswer extends PromptInGroup {
  answer?: EvaluationAnswer | null
  brand_mentions?: BrandMentionResult[] | null
  isExpanded?: boolean
  isLoading?: boolean
}

export interface GroupWithPrompts extends Omit<GroupDetail, "prompts"> {
  prompts: PromptWithAnswer[]
  isLoadingAnswers?: boolean
  answersLoaded?: boolean
  visibilityScores?: BrandVisibilityScore[] | null
  citationLeaderboard?: CitationLeaderboard | null
}

// ===== Drag & Drop Types =====

export interface DragItem {
  promptId: number
  sourceGroupId: number | "quarantine"
  prompt: PromptWithAnswer | QuarantinePrompt
}

export type DropResult = {
  targetGroupId: number
  targetIndex?: number
}
