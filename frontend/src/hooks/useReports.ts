/**
 * React Query hooks for Report History management
 * Provides report listing, fetching, and comparison queries
 */

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { reportsApi } from "@/client/api"
import { billingKeys } from "./useBilling"

// ===== Query Keys =====

export const reportKeys = {
  all: ["reports"] as const,
  history: (groupId: number) => [...reportKeys.all, "history", groupId] as const,
  detail: (groupId: number, reportId: number) =>
    [...reportKeys.all, "detail", groupId, reportId] as const,
  compare: (groupId: number) => [...reportKeys.all, "compare", groupId] as const,
}

// ===== Queries =====

/**
 * Fetch report history for a group with pagination
 */
export function useReportHistory(
  groupId: number,
  enabled: boolean = true,
  limit: number = 20,
  offset: number = 0
) {
  return useQuery({
    queryKey: [...reportKeys.history(groupId), limit, offset],
    queryFn: () => reportsApi.listReports(groupId, limit, offset),
    enabled: enabled && groupId > 0,
    staleTime: 60 * 1000, // 1 minute
  })
}

/**
 * Fetch a specific report with full details (items, answers, brand mentions)
 */
export function useReport(
  groupId: number,
  reportId: number | null,
  enabled: boolean = true
) {
  return useQuery({
    queryKey: reportKeys.detail(groupId, reportId!),
    queryFn: () => reportsApi.getReport(groupId, reportId!),
    enabled: enabled && groupId > 0 && reportId !== null,
    staleTime: 5 * 60 * 1000, // 5 minutes - reports don't change once generated
  })
}

/**
 * Compare current data with latest report
 * Used to determine if Report button should be disabled
 */
export function useReportComparison(groupId: number, enabled: boolean = true) {
  return useQuery({
    queryKey: reportKeys.compare(groupId),
    queryFn: () => reportsApi.compare(groupId),
    enabled: enabled && groupId > 0,
    staleTime: 30 * 1000, // 30 seconds - can change as evaluations complete
  })
}

// ===== Helper Hooks =====

/**
 * Check if there's new data to generate a report
 * Returns hasFreshData boolean, canGenerate, and related data
 */
export function useHasFreshData(groupId: number, enabled: boolean = true) {
  const { data: comparison, isLoading, error } = useReportComparison(groupId, enabled)

  return {
    // Based on new selectable comparison response
    hasFreshData: comparison ? comparison.default_fresh_count > 0 : null,
    freshDataCount: comparison?.default_fresh_count ?? 0,
    hasExistingReport: comparison?.last_report_at !== null,

    // New fields from selectable comparison
    canGenerate: comparison?.can_generate ?? false,
    generationDisabledReason: comparison?.generation_disabled_reason ?? null,
    promptsWithOptions: comparison?.prompts_with_options ?? 0,
    promptsAwaiting: comparison?.prompts_awaiting ?? 0,
    brandChanged: comparison?.brand_changes?.brand_changed ?? false,
    competitorsChanged: comparison?.brand_changes?.competitors_changed ?? false,
    promptSelections: comparison?.prompt_selections ?? [],
    defaultEstimatedCost: comparison?.default_estimated_cost ?? "0.00",
    userBalance: comparison?.user_balance ?? "0.00",
    pricePerEvaluation: comparison?.price_per_evaluation ?? "0.01",

    isLoading,
    error,
    comparison,
  }
}

/**
 * Invalidate report-related queries after generating a new report
 */
export function useInvalidateReportQueries() {
  const queryClient = useQueryClient()

  return (groupId: number) => {
    // Invalidate report history list
    queryClient.invalidateQueries({
      queryKey: reportKeys.history(groupId),
    })
    // Invalidate comparison
    queryClient.invalidateQueries({
      queryKey: reportKeys.compare(groupId),
    })
    // Also invalidate billing preview
    queryClient.invalidateQueries({
      queryKey: billingKeys.reportPreview(groupId),
    })
  }
}

// ===== Utility Functions =====

/**
 * Format relative time for report timestamps
 */
export function formatReportTime(timestamp: string): string {
  const now = new Date()
  const reportDate = new Date(timestamp)
  const diffMs = now.getTime() - reportDate.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return "just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return "yesterday"
  if (diffDays < 7) return `${diffDays}d ago`
  if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7)
    return `${weeks}w ago`
  }
  return reportDate.toLocaleDateString()
}
