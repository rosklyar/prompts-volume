import { useQuery } from "@tanstack/react-query"
import { useState, useEffect } from "react"
import { promptsApi, type SimilarPromptsResponse } from "@/client/api"

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

export function useSimilarPrompts(
  searchQuery: string,
  options?: {
    k?: number
    minSimilarity?: number
    debounceMs?: number
  }
) {
  const {
    k = 10,
    minSimilarity = 0.55,
    debounceMs = 300,
  } = options || {}

  const debouncedQuery = useDebounce(searchQuery.trim(), debounceMs)
  const shouldSearch = debouncedQuery.split(/\s+/).some(word => word.length > 3)

  const query = useQuery<SimilarPromptsResponse>({
    queryKey: ["similarPrompts", debouncedQuery, k, minSimilarity],
    queryFn: () => promptsApi.getSimilarPrompts(debouncedQuery, k, minSimilarity),
    enabled: shouldSearch,
    staleTime: 60 * 1000,
  })

  return {
    suggestions: query.data?.prompts || [],
    totalFound: query.data?.total_found || 0,
    isLoading: shouldSearch && query.isLoading,
    isFetching: shouldSearch && query.isFetching,
    error: query.error,
    debouncedQuery,
    shouldSearch,
  }
}
