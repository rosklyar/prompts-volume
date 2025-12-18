/**
 * React hook for managing quarantine state (frontend-only)
 *
 * Quarantine is a temporary holding space for prompts added from Prompt Discovery.
 * - Prompts live in local state only (not persisted to backend)
 * - Custom prompts are created via priority_prompt API immediately
 * - Moving prompts to groups calls the backend API
 */

import { useState, useCallback } from "react"
import { useMutation } from "@tanstack/react-query"
import { evaluationsApi, groupsApi } from "@/client/api"
import type { QuarantinePrompt } from "@/types/groups"

export function useQuarantine() {
  const [prompts, setPrompts] = useState<QuarantinePrompt[]>([])

  // Add an existing prompt (from search results) to quarantine
  const addExistingPrompt = useCallback(
    (promptId: number, promptText: string) => {
      setPrompts((prev) => {
        // Skip if already in quarantine
        if (prev.some((p) => p.prompt_id === promptId)) {
          return prev
        }
        return [
          ...prev,
          {
            prompt_id: promptId,
            prompt_text: promptText,
            added_at: new Date().toISOString(),
            isCustom: false,
          },
        ]
      })
    },
    []
  )

  // Remove a prompt from quarantine
  const removePrompt = useCallback((promptId: number) => {
    setPrompts((prev) => prev.filter((p) => p.prompt_id !== promptId))
  }, [])

  // Clear all prompts from quarantine
  const clearQuarantine = useCallback(() => {
    setPrompts([])
  }, [])

  // Mutation for adding custom prompt (creates in backend first)
  const addCustomPromptMutation = useMutation({
    mutationFn: async (promptText: string) => {
      const result = await evaluationsApi.addPriorityPrompts([promptText])
      return result.prompts[0]
    },
    onSuccess: (result) => {
      if (result) {
        setPrompts((prev) => [
          ...prev,
          {
            prompt_id: result.prompt_id,
            prompt_text: result.prompt_text,
            added_at: new Date().toISOString(),
            isCustom: true,
          },
        ])
      }
    },
  })

  // Mutation for moving prompt from quarantine to a group
  const moveToGroupMutation = useMutation({
    mutationFn: async ({
      promptId,
      targetGroupId,
    }: {
      promptId: number
      targetGroupId: number
    }) => {
      await groupsApi.addPromptsToGroup(targetGroupId, [promptId])
      return { promptId, targetGroupId }
    },
    onSuccess: ({ promptId }) => {
      // Remove from quarantine after successful move
      removePrompt(promptId)
    },
  })

  return {
    prompts,
    addExistingPrompt,
    addCustomPrompt: addCustomPromptMutation.mutate,
    addCustomPromptAsync: addCustomPromptMutation.mutateAsync,
    isAddingCustomPrompt: addCustomPromptMutation.isPending,
    removePrompt,
    clearQuarantine,
    moveToGroup: moveToGroupMutation.mutate,
    moveToGroupAsync: moveToGroupMutation.mutateAsync,
    isMovingToGroup: moveToGroupMutation.isPending,
  }
}

export type UseQuarantineReturn = ReturnType<typeof useQuarantine>
