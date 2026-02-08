/**
 * React Query hook for dashboard analytics data
 */

import { useQuery } from "@tanstack/react-query"
import { reportsApi } from "@/client/api"
import type { DashboardPeriod } from "@/types/dashboard"

export type DateRangeOption =
  | { period: DashboardPeriod }
  | { fromDate: string; toDate: string }

export const dashboardKeys = {
  all: ["dashboard"] as const,
  data: (
    groupId: number | null,
    assistantId: number | undefined,
    options?: DateRangeOption
  ) => [...dashboardKeys.all, "data", groupId, assistantId, options] as const,
}

export function useDashboardData(
  groupId: number | null,
  assistantId: number | undefined,
  options?: DateRangeOption,
  enabled?: boolean
) {
  return useQuery({
    queryKey: dashboardKeys.data(groupId, assistantId, options),
    queryFn: () => reportsApi.getDashboard(groupId!, assistantId!, options),
    enabled: enabled !== false && groupId !== null && assistantId !== undefined,
    staleTime: 60 * 1000, // 1 minute
  })
}
