/**
 * React Query hooks for Batch Prompts Upload feature
 */

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { groupsApi } from "@/client/api"
import { groupKeys } from "@/hooks/useGroups"
import { reportKeys } from "@/hooks/useReports"
import { billingKeys } from "@/hooks/useBilling"
import type { BatchConfirmRequest } from "@/types/batch-upload"

/**
 * Hook to analyze a batch of prompts for similarity matches
 */
export function useAnalyzeBatch() {
  return useMutation({
    mutationFn: ({ groupId, prompts }: { groupId: number; prompts: string[] }) =>
      groupsApi.analyzeBatch(groupId, prompts),
  })
}

/**
 * Hook to confirm batch selections and add prompts to group
 */
export function useConfirmBatch() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      groupId,
      request,
    }: {
      groupId: number
      request: BatchConfirmRequest
    }) => groupsApi.confirmBatch(groupId, request),
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
