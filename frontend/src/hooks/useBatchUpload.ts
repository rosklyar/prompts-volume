/**
 * React Query hooks for Batch Prompts Upload feature
 *
 * 3-step flow:
 * 1. useAnalyzeBatch - Analyze prompts for similarity matches
 * 2. useCreateBatchPrompts - Create new prompts via priority pipeline
 * 3. useBindPromptsToGroup - Bind prompt IDs to group (existing endpoint)
 */

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { batchApi, groupsApi } from "@/client/api"
import { groupKeys } from "@/hooks/useGroups"
import { reportKeys } from "@/hooks/useReports"
import { billingKeys } from "@/hooks/useBilling"
import type { BatchCreateRequest } from "@/types/batch-upload"

/**
 * Hook to analyze a batch of prompts for similarity matches
 */
export function useAnalyzeBatch() {
  return useMutation({
    mutationFn: (prompts: string[]) => batchApi.analyze(prompts),
  })
}

/**
 * Hook to create new prompts via priority pipeline
 */
export function useCreateBatchPrompts() {
  return useMutation({
    mutationFn: (request: BatchCreateRequest) => batchApi.create(request),
  })
}

/**
 * Hook to bind prompt IDs to a group
 */
export function useBindPromptsToGroup() {
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
      // Invalidate report comparison to detect new data for Report button
      queryClient.invalidateQueries({ queryKey: reportKeys.compare(groupId) })
      // Invalidate billing preview as well
      queryClient.invalidateQueries({ queryKey: billingKeys.reportPreview(groupId) })
    },
  })
}

/**
 * Parse CSV file content into array of prompt strings
 * Expects single column format (one prompt per line)
 */
export function parseCSV(content: string): { prompts: string[]; errors: string[] } {
  const errors: string[] = []
  const lines = content.split(/\r?\n/)

  const prompts: string[] = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()

    // Skip empty lines
    if (!line) continue

    // Skip header row if it looks like a header
    if (i === 0 && (line.toLowerCase() === "prompt" || line.toLowerCase() === "prompts" || line.toLowerCase() === "text")) {
      continue
    }

    // Remove surrounding quotes if present
    let text = line
    if ((text.startsWith('"') && text.endsWith('"')) || (text.startsWith("'") && text.endsWith("'"))) {
      text = text.slice(1, -1)
    }

    // Validate prompt is not empty after cleaning
    if (text.trim()) {
      prompts.push(text.trim())
    }
  }

  if (prompts.length === 0) {
    errors.push("No valid prompts found in the file")
  }

  if (prompts.length > 100) {
    errors.push(`Too many prompts (${prompts.length}). Maximum is 100 per batch.`)
  }

  return { prompts: prompts.slice(0, 100), errors }
}
