/**
 * React Query hooks for Prompt Groups management
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  groupsApi,
  evaluationsApi,
  type GroupDetail,
} from "@/client/api"
import { reportKeys } from "@/hooks/useReports"
import { billingKeys } from "@/hooks/useBilling"
import type { BrandInfo, CompetitorInfo, TopicInput } from "@/types/groups"

// ===== Query Keys =====

export const groupKeys = {
  all: ["groups"] as const,
  lists: () => [...groupKeys.all, "list"] as const,
  details: () => [...groupKeys.all, "detail"] as const,
  detail: (id: number) => [...groupKeys.details(), id] as const,
}

// ===== Queries =====

export function useGroups() {
  return useQuery({
    queryKey: groupKeys.lists(),
    queryFn: () => groupsApi.getGroups(),
  })
}

export function useGroupDetail(groupId: number | undefined) {
  return useQuery({
    queryKey: groupKeys.detail(groupId!),
    queryFn: () => groupsApi.getGroupDetail(groupId!),
    enabled: !!groupId,
  })
}

export function useAllGroupDetails(groupIds: number[]) {
  return useQuery({
    queryKey: [...groupKeys.details(), groupIds],
    queryFn: async () => {
      const details = await Promise.all(
        groupIds.map((id) => groupsApi.getGroupDetail(id))
      )
      return details
    },
    enabled: groupIds.length > 0,
  })
}

// ===== Mutations =====

export function useCreateGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      title,
      topic,
      brand,
      competitors,
    }: {
      title: string
      topic: TopicInput
      brand: BrandInfo
      competitors?: CompetitorInfo[]
    }) => groupsApi.createGroup(title, topic, brand, competitors),
    onSuccess: () => {
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
    },
  })
}

export function useUpdateGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      groupId,
      title,
      brand,
      competitors,
    }: {
      groupId: number
      title?: string
      brand?: BrandInfo
      competitors?: CompetitorInfo[] | null
    }) => groupsApi.updateGroup(groupId, { title, brand, competitors }),
    onSuccess: (_data, variables) => {
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
      // Invalidate compare query since brand/competitors may have changed
      queryClient.invalidateQueries({ queryKey: reportKeys.compare(variables.groupId) })
    },
  })
}

export function useDeleteGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (groupId: number) => groupsApi.deleteGroup(groupId),
    onSuccess: () => {
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
    },
  })
}

export function useAddPromptsToGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      groupId,
      promptIds,
    }: {
      groupId: number
      promptIds: number[]
    }) => groupsApi.addPromptsToGroup(groupId, promptIds),
    onSuccess: (_data, variables) => {
      const { groupId } = variables
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
      // Explicitly invalidate group details to update prompts in group cards
      queryClient.invalidateQueries({ queryKey: groupKeys.details() })
      // Invalidate report comparison to detect new data for Report button
      queryClient.invalidateQueries({ queryKey: reportKeys.compare(groupId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.reportPreview(groupId) })
    },
  })
}

export function useRemovePromptsFromGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      groupId,
      promptIds,
    }: {
      groupId: number
      promptIds: number[]
    }) => groupsApi.removePromptsFromGroup(groupId, promptIds),
    onSuccess: (_data, variables) => {
      const { groupId } = variables
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
      // Invalidate report comparison since prompt count changed
      queryClient.invalidateQueries({ queryKey: reportKeys.compare(groupId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.reportPreview(groupId) })
    },
  })
}

// ===== Move Prompt (optimistic) =====

export function useMovePrompt() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      promptId,
      sourceGroupId,
      targetGroupId,
    }: {
      promptId: number
      sourceGroupId: number
      targetGroupId: number
    }) => {
      // Remove from source, add to target
      await groupsApi.removePromptsFromGroup(sourceGroupId, [promptId])
      await groupsApi.addPromptsToGroup(targetGroupId, [promptId])
    },
    onMutate: async ({ promptId, sourceGroupId, targetGroupId }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: groupKeys.detail(sourceGroupId),
      })
      await queryClient.cancelQueries({
        queryKey: groupKeys.detail(targetGroupId),
      })

      // Snapshot previous values
      const previousSource = queryClient.getQueryData<GroupDetail>(
        groupKeys.detail(sourceGroupId)
      )
      const previousTarget = queryClient.getQueryData<GroupDetail>(
        groupKeys.detail(targetGroupId)
      )

      // Optimistically update source group
      if (previousSource) {
        const movedPrompt = previousSource.prompts.find(
          (p) => p.prompt_id === promptId
        )
        queryClient.setQueryData<GroupDetail>(
          groupKeys.detail(sourceGroupId),
          {
            ...previousSource,
            prompts: previousSource.prompts.filter(
              (p) => p.prompt_id !== promptId
            ),
          }
        )

        // Optimistically update target group
        if (previousTarget && movedPrompt) {
          queryClient.setQueryData<GroupDetail>(
            groupKeys.detail(targetGroupId),
            {
              ...previousTarget,
              prompts: [...previousTarget.prompts, movedPrompt],
            }
          )
        }
      }

      return { previousSource, previousTarget }
    },
    onError: (_, { sourceGroupId, targetGroupId }, context) => {
      // Revert on error
      if (context?.previousSource) {
        queryClient.setQueryData(
          groupKeys.detail(sourceGroupId),
          context.previousSource
        )
      }
      if (context?.previousTarget) {
        queryClient.setQueryData(
          groupKeys.detail(targetGroupId),
          context.previousTarget
        )
      }
    },
    onSettled: (_data, _error, variables) => {
      const { sourceGroupId, targetGroupId } = variables
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
      // Invalidate report comparison for both groups
      queryClient.invalidateQueries({ queryKey: reportKeys.compare(sourceGroupId) })
      queryClient.invalidateQueries({ queryKey: reportKeys.compare(targetGroupId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.reportPreview(sourceGroupId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.reportPreview(targetGroupId) })
    },
  })
}

// ===== Priority Prompts =====

export function useAddPriorityPrompt() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      promptText,
      targetGroupId,
    }: {
      promptText: string
      targetGroupId: number
    }) => {
      // First add as priority prompt to get the prompt_id
      const result = await evaluationsApi.addPriorityPrompts([promptText])
      const promptId = result.prompts[0]?.prompt_id

      if (promptId) {
        // Then add to the target group
        await groupsApi.addPromptsToGroup(targetGroupId, [promptId])
      }

      return result
    },
    onSuccess: (_data, variables) => {
      const { targetGroupId } = variables
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
      // Explicitly invalidate group details to update prompts in group cards
      queryClient.invalidateQueries({ queryKey: groupKeys.details() })
      // Invalidate report comparison to detect new data for Report button
      queryClient.invalidateQueries({ queryKey: reportKeys.compare(targetGroupId) })
      queryClient.invalidateQueries({ queryKey: billingKeys.reportPreview(targetGroupId) })
    },
  })
}

