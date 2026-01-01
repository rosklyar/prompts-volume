/**
 * React Query hooks for DataForSEO Inspiration feature
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  inspirationApi,
  promptsApi,
  groupsApi,
  type GeneratePromptsRequest,
} from "@/client/api"
import type {
  MetaInfoResponse,
  TopicPromptsResponse,
  GeneratePromptsResponse,
} from "@/types/inspiration"
import { groupKeys } from "./useGroups"
import { reportKeys } from "./useReports"
import { billingKeys } from "./useBilling"
import type { BrandInfo, CompetitorInfo } from "@/types/groups"

// ===== Query Keys =====

export const inspirationKeys = {
  all: ["inspiration"] as const,
  metaInfo: (companyUrl: string, countryCode: string) =>
    [...inspirationKeys.all, "meta-info", companyUrl, countryCode] as const,
  topicPrompts: (topicIds: number[]) =>
    [...inspirationKeys.all, "topic-prompts", topicIds.sort().join(",")] as const,
  similarPrompts: (text: string) =>
    [...inspirationKeys.all, "similar", text] as const,
}

// ===== Hooks =====

/**
 * Fetch meta info for a company (matched topics, unmatched topics, brand variations)
 */
export function useMetaInfo(companyUrl: string, countryCode: string) {
  return useQuery<MetaInfoResponse>({
    queryKey: inspirationKeys.metaInfo(companyUrl, countryCode),
    queryFn: () => inspirationApi.getMetaInfo(companyUrl, countryCode),
    enabled: Boolean(companyUrl && countryCode),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  })
}

/**
 * Fetch prompts for matched topics from DB (fast ~50ms)
 */
export function useTopicPrompts(topicIds: number[]) {
  return useQuery<TopicPromptsResponse>({
    queryKey: inspirationKeys.topicPrompts(topicIds),
    queryFn: () => inspirationApi.getTopicPrompts(topicIds),
    enabled: topicIds.length > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Mutation for generating prompts (long-running 30-60s)
 * Charges $1 on success - invalidates balance cache
 */
export function useGeneratePrompts() {
  const queryClient = useQueryClient()

  return useMutation<GeneratePromptsResponse, Error, GeneratePromptsRequest>({
    mutationFn: (request) => inspirationApi.generatePrompts(request),
    onSuccess: () => {
      // Invalidate balance cache (user was charged)
      queryClient.invalidateQueries({ queryKey: billingKeys.balance() })
      queryClient.invalidateQueries({ queryKey: billingKeys.generationPrice() })
      queryClient.invalidateQueries({ queryKey: billingKeys.transactions() })
    },
  })
}

/**
 * Mutation for fetching meta info (for wizard flow)
 */
export function useAnalyzeCompany() {
  return useMutation<
    MetaInfoResponse,
    Error,
    { companyUrl: string; countryCode: string }
  >({
    mutationFn: ({ companyUrl, countryCode }) =>
      inspirationApi.getMetaInfo(companyUrl, countryCode),
  })
}

/**
 * Mutation for loading prompts for a single topic
 */
export function useLoadTopicPrompts() {
  return useMutation<TopicPromptsResponse, Error, number[]>({
    mutationFn: (topicIds) => inspirationApi.getTopicPrompts(topicIds),
  })
}

/**
 * Fetch similar prompts for a text (for review step)
 */
export function useSimilarPromptsForText(
  text: string,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: inspirationKeys.similarPrompts(text),
    queryFn: () => promptsApi.getSimilarPrompts(text, 5, 0.75),
    enabled: Boolean(text && text.length >= 3 && enabled),
    staleTime: 60 * 1000, // 1 minute
  })
}

/**
 * Batch fetch similar prompts for multiple texts
 */
export function useBatchSimilarPrompts() {
  return useMutation({
    mutationFn: async (texts: string[]) => {
      const results = await Promise.all(
        texts.map((text) =>
          promptsApi.getSimilarPrompts(text, 5, 0.75).catch(() => ({
            query_text: text,
            prompts: [],
            total_found: 0,
          }))
        )
      )
      return results
    },
  })
}

/**
 * Mutation for adding prompts to a group (with cache invalidation)
 */
export function useAddPromptsToGroupFromInspiration() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      groupId,
      promptIds,
    }: {
      groupId: number
      promptIds: number[]
    }) => groupsApi.addPromptsToGroup(groupId, promptIds),
    onSuccess: (_data, variables) => {
      const { groupId } = variables
      // Invalidate groups cache to reflect new prompts
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
      // Invalidate report comparison to detect new data for Report button
      queryClient.invalidateQueries({ queryKey: reportKeys.compare(groupId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.reportPreview(groupId) })
    },
  })
}

/**
 * Mutation for creating a new group and adding prompts
 */
export function useCreateGroupWithPrompts() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      title,
      brand,
      competitors,
      promptIds,
    }: {
      title: string
      brand: BrandInfo
      competitors?: CompetitorInfo[]
      promptIds: number[]
    }) => {
      const group = await groupsApi.createGroup(title, brand, competitors)
      if (promptIds.length > 0) {
        await groupsApi.addPromptsToGroup(group.id, promptIds)
      }
      return group
    },
    onSuccess: (group) => {
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
      // Invalidate report queries for the new group
      queryClient.invalidateQueries({ queryKey: reportKeys.compare(group.id) })
      queryClient.invalidateQueries({ queryKey: billingKeys.reportPreview(group.id) })
    },
  })
}
