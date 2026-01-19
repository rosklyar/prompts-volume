/**
 * React Query hooks for Report Request management
 * Supports the unified manual/scheduled report generation flow
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { reportsApi } from "@/client/api"
import type { CreateReportRequestBody } from "@/types/billing"
import { reportKeys } from "./useReports"

// ===== Query Keys =====

export const reportRequestKeys = {
  all: ["reportRequests"] as const,
  status: (groupId: number) => [...reportRequestKeys.all, "status", groupId] as const,
}

// ===== Queries =====

/**
 * Get pending report request status for a group
 * Polls every 30 seconds when there's a pending request
 */
export function useReportRequestStatus(groupId: number, enabled: boolean = true) {
  return useQuery({
    queryKey: reportRequestKeys.status(groupId),
    queryFn: () => reportsApi.getRequestStatus(groupId),
    enabled: enabled && groupId > 0,
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: (query) => {
      // Poll every 30 seconds if there's a pending request
      const data = query.state.data
      if (data?.has_pending && data?.request?.status === "awaiting") {
        return 30 * 1000
      }
      // Poll every 10 seconds if generating
      if (data?.has_pending && data?.request?.status === "generating") {
        return 10 * 1000
      }
      // Stop polling otherwise
      return false
    },
  })
}

// ===== Mutations =====

/**
 * Create a new report request
 * This triggers BrightData for stale/absent prompts
 */
export function useCreateReportRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      groupId,
      assistantId = 1,
    }: {
      groupId: number
      assistantId?: number
    }) => {
      const body: CreateReportRequestBody = { assistant_id: assistantId }
      return reportsApi.createRequest(groupId, body)
    },
    onSuccess: (data) => {
      // Invalidate the status query for this group
      queryClient.invalidateQueries({
        queryKey: reportRequestKeys.status(data.group_id),
      })
    },
  })
}

/**
 * Cancel a pending report request
 */
export function useCancelReportRequest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (groupId: number) => reportsApi.cancelRequest(groupId),
    onSuccess: (_, groupId) => {
      // Invalidate the status query for this group
      queryClient.invalidateQueries({
        queryKey: reportRequestKeys.status(groupId),
      })
    },
  })
}

// ===== Helper Hooks =====

/**
 * Combined hook for report request state and actions
 */
export function useReportRequest(groupId: number, enabled: boolean = true) {
  const queryClient = useQueryClient()
  const statusQuery = useReportRequestStatus(groupId, enabled)
  const createMutation = useCreateReportRequest()
  const cancelMutation = useCancelReportRequest()

  const hasPending = statusQuery.data?.has_pending ?? false
  const pendingRequest = statusQuery.data?.request ?? null
  const isAwaiting = pendingRequest?.status === "awaiting"
  const isReady = pendingRequest?.status === "ready"
  const isGenerating = pendingRequest?.status === "generating"
  const isCompleted = pendingRequest?.status === "completed"

  return {
    // Status
    hasPending,
    pendingRequest,
    isAwaiting,
    isReady,
    isGenerating,
    isCompleted,
    isLoading: statusQuery.isLoading,
    error: statusQuery.error,

    // Progress info
    progress: pendingRequest
      ? {
          total: pendingRequest.total_prompts,
          fresh: pendingRequest.prompts_fresh_at_request,
          requested: pendingRequest.prompts_requested,
          reportId: pendingRequest.report_id,
        }
      : null,

    // Actions
    createRequest: (assistantId?: number) =>
      createMutation.mutateAsync({ groupId, assistantId }),
    cancelRequest: () => cancelMutation.mutateAsync(groupId),
    refetch: () => statusQuery.refetch(),

    // Invalidate reports when request completes
    invalidateReports: () => {
      queryClient.invalidateQueries({
        queryKey: reportKeys.history(groupId),
      })
    },

    // Mutation states
    isCreating: createMutation.isPending,
    isCancelling: cancelMutation.isPending,
    createError: createMutation.error,
    cancelError: cancelMutation.error,
  }
}
