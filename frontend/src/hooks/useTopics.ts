/**
 * React Query hooks for Topics, Countries, and Business Domains
 */

import { useQuery } from "@tanstack/react-query"
import { referenceApi } from "@/client/api"

// ===== Query Keys =====

export const topicKeys = {
  all: ["topics"] as const,
  lists: () => [...topicKeys.all, "list"] as const,
  list: (filters: { countryId?: number; businessDomainId?: number }) =>
    [...topicKeys.lists(), filters] as const,
}

export const countryKeys = {
  all: ["countries"] as const,
  lists: () => [...countryKeys.all, "list"] as const,
}

export const businessDomainKeys = {
  all: ["businessDomains"] as const,
  lists: () => [...businessDomainKeys.all, "list"] as const,
}

// ===== Queries =====

/**
 * Fetch all countries
 */
export function useCountries() {
  return useQuery({
    queryKey: countryKeys.lists(),
    queryFn: () => referenceApi.getCountries(),
    staleTime: 1000 * 60 * 60, // 1 hour - countries rarely change
  })
}

/**
 * Fetch all business domains
 */
export function useBusinessDomains() {
  return useQuery({
    queryKey: businessDomainKeys.lists(),
    queryFn: () => referenceApi.getBusinessDomains(),
    staleTime: 1000 * 60 * 60, // 1 hour - business domains rarely change
  })
}

/**
 * Fetch topics with optional filtering by country and business domain
 */
export function useTopicsFiltered(countryId?: number, businessDomainId?: number) {
  return useQuery({
    queryKey: topicKeys.list({ countryId, businessDomainId }),
    queryFn: () => referenceApi.getTopics(businessDomainId, countryId),
    enabled: countryId !== undefined && businessDomainId !== undefined,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })
}
