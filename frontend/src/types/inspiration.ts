/**
 * Types for DataForSEO Inspiration feature
 * Multi-step wizard for discovering and organizing prompts
 */

// ===== API Response Types =====

export interface MatchedTopic {
  id: number
  title: string
  description: string
  business_domain_id: number
  country_id: number
}

export interface UnmatchedTopic {
  title: string
  source: "generated"
}

export interface MetaInfoResponse {
  business_domain: string | null
  topics: {
    matched_topics: MatchedTopic[]
    unmatched_topics: UnmatchedTopic[]
  }
  brand_variations: string[]
}

export interface PromptFromTopic {
  id: number
  prompt_text: string
}

export interface TopicPromptsItem {
  topic_id: number
  prompts: PromptFromTopic[]
}

export interface TopicPromptsResponse {
  topics: TopicPromptsItem[]
}

export interface GeneratedCluster {
  cluster_id: number
  keywords: string[]
  prompts: string[]
}

export interface GeneratedTopicResult {
  topic: string
  clusters: GeneratedCluster[]
}

export interface GeneratePromptsResponse {
  topics: GeneratedTopicResult[]
}

// ===== UI State Types =====

export type InspirationStep =
  | "configure"
  | "matched"
  | "generate"
  | "review"

export interface PromptSelectionState {
  promptId: number
  promptText: string
  isSelected: boolean
}

export interface TopicWithPrompts {
  topicId: number
  topicTitle: string
  prompts: PromptSelectionState[]
  isExpanded: boolean
  isLoading: boolean
  addedToGroupId: number | null
  addedToGroupTitle: string | null
}

export interface GeneratedPromptMatch {
  promptId: number
  promptText: string
  similarity: number
}

export interface GeneratedPromptReview {
  inputText: string
  keywords: string[]
  matches: GeneratedPromptMatch[]
  selectedOption: "keep-original" | "use-match"
  selectedMatchId: number | null
}

export interface GeneratedTopicReview {
  topicTitle: string
  prompts: GeneratedPromptReview[]
  isExpanded: boolean
  addedToGroupId: number | null
  addedToGroupTitle: string | null
}

export interface WizardState {
  step: InspirationStep
  companyUrl: string
  isoCountryCode: string
  metaInfo: MetaInfoResponse | null
  matchedTopics: TopicWithPrompts[]
  selectedUnmatchedTopics: Set<string>
  brandVariations: string[]
  generatedTopics: GeneratedTopicReview[]
  error: string | null
}

// ===== Country Code Options =====

export interface CountryOption {
  code: string
  name: string
  flag: string
}

export const COUNTRY_OPTIONS: CountryOption[] = [
  { code: "UA", name: "Ukraine", flag: "🇺🇦" },
  { code: "US", name: "United States", flag: "🇺🇸" },
  { code: "GB", name: "United Kingdom", flag: "🇬🇧" },
  { code: "DE", name: "Germany", flag: "🇩🇪" },
  { code: "FR", name: "France", flag: "🇫🇷" },
  { code: "PL", name: "Poland", flag: "🇵🇱" },
  { code: "ES", name: "Spain", flag: "🇪🇸" },
  { code: "IT", name: "Italy", flag: "🇮🇹" },
  { code: "NL", name: "Netherlands", flag: "🇳🇱" },
  { code: "CA", name: "Canada", flag: "🇨🇦" },
  { code: "AU", name: "Australia", flag: "🇦🇺" },
  { code: "BR", name: "Brazil", flag: "🇧🇷" },
  { code: "MX", name: "Mexico", flag: "🇲🇽" },
  { code: "JP", name: "Japan", flag: "🇯🇵" },
  { code: "KR", name: "South Korea", flag: "🇰🇷" },
  { code: "IN", name: "India", flag: "🇮🇳" },
]
