/**
 * React Query hooks for admin prompt approvals
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { adminApi } from "@/client/api"
import type { ApprovalResultResponse, BatchApprovalResponse } from "@/types/admin"

// Query keys
export const approvalKeys = {
  all: ["admin", "approvals"] as const,
  pending: (limit: number, offset: number) =>
    [...approvalKeys.all, "pending", { limit, offset }] as const,
}

/**
 * Fetch pending prompts for approval
 */
export function usePendingPrompts(limit: number = 20, offset: number = 0) {
  return useQuery({
    queryKey: approvalKeys.pending(limit, offset),
    queryFn: () => adminApi.getPendingPrompts(limit, offset),
    staleTime: 30 * 1000, // 30 seconds
  })
}

/**
 * Approve a single prompt
 */
export function useApprovePrompt() {
  const queryClient = useQueryClient()

  return useMutation<
    ApprovalResultResponse,
    Error,
    { promptId: number; topicId?: number | null }
  >({
    mutationFn: ({ promptId, topicId }) =>
      adminApi.approvePrompt(promptId, topicId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: approvalKeys.all })
    },
  })
}

/**
 * Reject a single prompt
 */
export function useRejectPrompt() {
  const queryClient = useQueryClient()

  return useMutation<ApprovalResultResponse, Error, number>({
    mutationFn: (promptId) => adminApi.rejectPrompt(promptId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: approvalKeys.all })
    },
  })
}

/**
 * Batch approve prompts
 */
export function useBatchApprove() {
  const queryClient = useQueryClient()

  return useMutation<
    BatchApprovalResponse,
    Error,
    { promptIds: number[]; topicId?: number | null }
  >({
    mutationFn: ({ promptIds, topicId }) =>
      adminApi.batchApprovePrompts(promptIds, topicId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: approvalKeys.all })
    },
  })
}

/**
 * Batch reject prompts
 */
export function useBatchReject() {
  const queryClient = useQueryClient()

  return useMutation<BatchApprovalResponse, Error, number[]>({
    mutationFn: (promptIds) => adminApi.batchRejectPrompts(promptIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: approvalKeys.all })
    },
  })
}
