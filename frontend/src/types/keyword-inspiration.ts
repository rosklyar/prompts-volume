// Request/Response types matching backend keyword-inspiration API

export interface DiscoverClustersRequest {
  domains: string[]
  country_code: string
  language_name: string
  brand_names: string[]
}

export interface ScoredCluster {
  cluster_id: number
  keywords: string[]
  score: number
  title: string
  keyword_count: number
}

export interface ClusterKeywordsResponse {
  clusters: ScoredCluster[]
  total_keywords: number
  noise_keywords: number
}

export interface ClusterSelection {
  cluster_id: number
  keywords: string[]
  title: string
}

export interface GeneratePromptsRequest {
  clusters: ClusterSelection[]
  business_domain: string
  language: string
}

export interface GeneratedPromptItem {
  prompt_text: string
  source_keyword: string
}

export interface ClusterPrompts {
  cluster_id: number
  title: string
  prompts: GeneratedPromptItem[]
}

export interface GeneratePromptsResponse {
  clusters: ClusterPrompts[]
  total_prompts: number
}

export interface ConfirmGroupsRequest {
  clusters: { title: string; prompts: string[] }[]
  country_id: number
  brand: { name: string; domain?: string | null; variations: string[] }
  competitors?: { name: string; domain?: string | null; variations: string[] }[] | null
}

export interface CreatedGroupInfo {
  group_id: number
  title: string
  prompts_count: number
}

export interface CreateGroupsResponse {
  groups: CreatedGroupInfo[]
  total_prompts: number
}
