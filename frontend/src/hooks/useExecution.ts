/**
 * React Query hooks for Execution Queue management
 * Provides report data with freshness, execution requests, and queue status
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { reportsApi, executionApi } from "@/client/api"
import type { ReportDataResponse } from "@/types/execution"
import { reportKeys } from "./useReports"

// ===== Query Keys =====

export const executionKeys = {
  all: ["execution"] as const,
  reportData: (groupId: number) =>
    [...executionKeys.all, "reportData", groupId] as const,
  queueStatus: () => [...executionKeys.all, "queueStatus"] as const,
}

// ===== Queries =====

/**
 * Fetch report data with freshness metadata for a group
 * Returns prompts with their evaluations, freshness categories, and default selections
 */
export function useReportData(groupId: number, enabled: boolean = true) {
  return useQuery({
    queryKey: executionKeys.reportData(groupId),
    queryFn: () => reportsApi.getReportData(groupId),
    enabled: enabled && groupId > 0,
    staleTime: 30 * 1000, // 30 seconds - can change as evaluations complete
  })
}

/**
 * Fetch current queue status for the user
 * Shows pending and in-progress executions, recently completed items
 */
export function useQueueStatus(enabled: boolean = true) {
  return useQuery({
    queryKey: executionKeys.queueStatus(),
    queryFn: () => executionApi.getQueueStatus(),
    enabled,
    staleTime: 10 * 1000, // 10 seconds - queue changes frequently
    refetchInterval: 30 * 1000, // Poll every 30 seconds while visible
  })
}

// ===== Mutations =====

/**
 * Request fresh execution for prompts
 * Adds prompts to execution queue and returns estimated wait time
 */
export function useRequestFresh() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (promptIds: number[]) => executionApi.requestFresh(promptIds),
    onSuccess: () => {
      // Invalidate queue status to show new pending items
      queryClient.invalidateQueries({
        queryKey: executionKeys.queueStatus(),
      })
      // Also invalidate all report data queries to update pending_execution status
      queryClient.invalidateQueries({
        queryKey: executionKeys.all,
      })
    },
  })
}

/**
 * Cancel a pending execution request
 */
export function useCancelExecution() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (promptId: number) => executionApi.cancelExecution(promptId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: executionKeys.queueStatus(),
      })
      queryClient.invalidateQueries({
        queryKey: executionKeys.all,
      })
    },
  })
}

/**
 * Cancel multiple pending execution requests
 */
export function useCancelExecutionsBatch() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (promptIds: number[]) => executionApi.cancelExecutionsBatch(promptIds),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: executionKeys.queueStatus(),
      })
      queryClient.invalidateQueries({
        queryKey: executionKeys.all,
      })
    },
  })
}

// ===== Helper Hooks =====

/**
 * Invalidate execution-related queries after report generation
 */
export function useInvalidateExecutionQueries() {
  const queryClient = useQueryClient()

  return (groupId?: number) => {
    // Invalidate queue status
    queryClient.invalidateQueries({
      queryKey: executionKeys.queueStatus(),
    })
    // Invalidate report data for specific group or all
    if (groupId) {
      queryClient.invalidateQueries({
        queryKey: executionKeys.reportData(groupId),
      })
      // Also invalidate comparison (old endpoint)
      queryClient.invalidateQueries({
        queryKey: reportKeys.compare(groupId),
      })
    } else {
      queryClient.invalidateQueries({
        queryKey: executionKeys.all,
      })
    }
  }
}

// ===== Utility Types =====

/**
 * Selection state for report modal (internal to modal component)
 * - number: evaluation_id to include in report
 * - 'ask_fresh': request fresh execution
 * - null: skip this prompt
 */
type SelectionValue = number | "ask_fresh" | null

/**
 * Get derived selection info from report data and user selections
 */
export function getSelectionSummary(
  reportData: ReportDataResponse | undefined,
  selections: Map<number, SelectionValue>
): {
  promptsForReport: number[]
  promptsForFresh: number[]
  skippedCount: number
} {
  if (!reportData) {
    return { promptsForReport: [], promptsForFresh: [], skippedCount: 0 }
  }

  const promptsForReport: number[] = []
  const promptsForFresh: number[] = []
  let skippedCount = 0

  for (const prompt of reportData.prompts) {
    const selection = selections.get(prompt.prompt_id)
    if (typeof selection === "number") {
      promptsForReport.push(prompt.prompt_id)
    } else if (selection === "ask_fresh") {
      promptsForFresh.push(prompt.prompt_id)
    } else {
      skippedCount++
    }
  }

  return { promptsForReport, promptsForFresh, skippedCount }
}
