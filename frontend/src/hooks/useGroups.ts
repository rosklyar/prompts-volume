/**
 * React Query hooks for Prompt Groups management
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  groupsApi,
  evaluationsApi,
  type GroupDetail,
} from "@/client/api"

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
    mutationFn: (title: string) => groupsApi.createGroup(title),
    onSuccess: () => {
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
    },
  })
}

export function useUpdateGroup() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ groupId, title }: { groupId: number; title: string }) =>
      groupsApi.updateGroup(groupId, title),
    onSuccess: () => {
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
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
    onSuccess: () => {
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
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
    onSuccess: () => {
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
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
    onSettled: () => {
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
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
    onSuccess: () => {
      // Invalidate all group queries to ensure UI updates
      queryClient.invalidateQueries({ queryKey: groupKeys.all })
    },
  })
}

// ===== Load Answers =====

export function useLoadAnswers() {
  return useMutation({
    mutationFn: async ({
      promptIds,
      assistantName = "ChatGPT",
      planName = "FREE",
    }: {
      promptIds: number[]
      assistantName?: string
      planName?: string
    }) => {
      return evaluationsApi.getResults(assistantName, planName, promptIds)
    },
  })
}
