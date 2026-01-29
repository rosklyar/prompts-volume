/**
 * React Query hook for aggregated citations leaderboard
 */

import { useQuery } from "@tanstack/react-query"
import { reportsApi } from "@/client/api"

export const citationsKeys = {
  all: ["citations"] as const,
  leaderboard: (
    groupId: number | null,
    period: "1d" | "7d" | "30d",
    assistantId?: number
  ) => [...citationsKeys.all, "leaderboard", groupId, period, assistantId] as const,
}

export function useCitationsLeaderboard(
  groupId: number | null,
  period: "1d" | "7d" | "30d",
  assistantId?: number,
  enabled?: boolean
) {
  return useQuery({
    queryKey: citationsKeys.leaderboard(groupId, period, assistantId),
    queryFn: () => reportsApi.getCitationsLeaderboard(groupId!, period, assistantId),
    enabled: enabled !== false && groupId !== null,
    staleTime: 60 * 1000, // 1 minute
  })
}
