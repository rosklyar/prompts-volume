/**
 * React Query hook for dashboard analytics data
 */

import { useQuery } from "@tanstack/react-query"
import { reportsApi } from "@/client/api"
import type { DashboardPeriod } from "@/types/dashboard"

export const dashboardKeys = {
  all: ["dashboard"] as const,
  data: (groupId: number | null, assistantId: number | undefined, period: DashboardPeriod) =>
    [...dashboardKeys.all, "data", groupId, assistantId, period] as const,
}

export function useDashboardData(
  groupId: number | null,
  assistantId: number | undefined,
  period: DashboardPeriod = "7d",
  enabled?: boolean
) {
  return useQuery({
    queryKey: dashboardKeys.data(groupId, assistantId, period),
    queryFn: () => reportsApi.getDashboard(groupId!, assistantId!, period),
    enabled: enabled !== false && groupId !== null && assistantId !== undefined,
    staleTime: 60 * 1000, // 1 minute
  })
}
