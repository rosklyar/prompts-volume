/**
 * React Query hooks for admin prompts management
 *
 * Note: useBusinessDomains, useCountries, and useTopics now use the shared
 * reference API accessible to all authenticated users.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { adminApi, referenceApi } from "@/client/api"
import type {
  CreateTopicRequest,
  PromptUploadResponse,
  UploadPromptsRequest,
} from "@/types/admin"
import type { BatchAnalyzeResponse } from "@/types/batch-upload"

// Query keys
export const adminPromptsKeys = {
  all: ["admin", "prompts"] as const,
  businessDomains: () => ["reference", "business-domains"] as const,
  countries: () => ["reference", "countries"] as const,
  topics: (businessDomainId?: number, countryId?: number) =>
    ["reference", "topics", { businessDomainId, countryId }] as const,
}

/**
 * Hook to fetch all business domains (available to all authenticated users)
 */
export function useBusinessDomains() {
  return useQuery({
    queryKey: adminPromptsKeys.businessDomains(),
    queryFn: () => referenceApi.getBusinessDomains(),
    staleTime: 5 * 60 * 1000, // 5 minutes - these rarely change
  })
}

/**
 * Hook to fetch all countries (available to all authenticated users)
 */
export function useCountries() {
  return useQuery({
    queryKey: adminPromptsKeys.countries(),
    queryFn: () => referenceApi.getCountries(),
    staleTime: 5 * 60 * 1000, // 5 minutes - these rarely change
  })
}

/**
 * Hook to fetch topics with optional filtering (available to all authenticated users)
 */
export function useTopics(businessDomainId?: number, countryId?: number) {
  return useQuery({
    queryKey: adminPromptsKeys.topics(businessDomainId, countryId),
    queryFn: () => referenceApi.getTopics(businessDomainId, countryId),
    staleTime: 1 * 60 * 1000, // 1 minute
  })
}

/**
 * Hook to create a new topic
 */
export function useCreateTopic() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: CreateTopicRequest) => adminApi.createTopic(request),
    onSuccess: () => {
      // Invalidate topics query to refetch the list
      queryClient.invalidateQueries({ queryKey: adminPromptsKeys.topics() })
    },
  })
}

/**
 * Hook to analyze prompts for similarity
 */
export function useAnalyzePrompts() {
  return useMutation<BatchAnalyzeResponse, Error, string[]>({
    mutationFn: (prompts) => adminApi.analyzePrompts(prompts),
  })
}

/**
 * Hook to upload selected prompts
 */
export function useUploadPrompts() {
  const queryClient = useQueryClient()

  return useMutation<PromptUploadResponse, Error, UploadPromptsRequest>({
    mutationFn: (request) => adminApi.uploadPrompts(request),
    onSuccess: () => {
      // Optionally invalidate any prompts-related queries
      queryClient.invalidateQueries({ queryKey: ["prompts"] })
    },
  })
}
