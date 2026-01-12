/**
 * React Query hooks for AI Assistants management
 * Provides assistants list query
 */

import { useQuery } from "@tanstack/react-query"
import { assistantsApi } from "@/client/api"

// ===== Query Keys =====

export const assistantKeys = {
  all: ["assistants"] as const,
  list: () => [...assistantKeys.all, "list"] as const,
}

// ===== Queries =====

/**
 * Fetch all available AI assistants
 * Returns list of assistants with id and name
 */
export function useAssistants() {
  return useQuery({
    queryKey: assistantKeys.list(),
    queryFn: () => assistantsApi.listAssistants(),
    staleTime: 5 * 60 * 1000, // 5 minutes - assistants rarely change
  })
}
