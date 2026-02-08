/**
 * React Query hook for aggregated citations leaderboard
 */

import { useQuery } from "@tanstack/react-query"
import { reportsApi } from "@/client/api"

export type CitationsDateRangeOption =
  | { period: "1d" | "7d" | "30d" }
  | { fromDate: string; toDate: string }

export const citationsKeys = {
  all: ["citations"] as const,
  leaderboard: (
    groupId: number | null,
    options: CitationsDateRangeOption,
    assistantId?: number
  ) => [...citationsKeys.all, "leaderboard", groupId, options, assistantId] as const,
}

export function useCitationsLeaderboard(
  groupId: number | null,
  options: CitationsDateRangeOption,
  assistantId?: number,
  enabled?: boolean
) {
  return useQuery({
    queryKey: citationsKeys.leaderboard(groupId, options, assistantId),
    queryFn: () => reportsApi.getCitationsLeaderboard(groupId!, options, assistantId),
    enabled: enabled !== false && groupId !== null,
    staleTime: 60 * 1000, // 1 minute
  })
}
