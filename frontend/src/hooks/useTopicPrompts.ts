/**
 * React Query hook for fetching prompts by topic IDs
 */

import { useQuery } from "@tanstack/react-query"
import { promptsApi } from "@/client/api"

export const topicPromptsKeys = {
  all: ["topicPrompts"] as const,
  byTopic: (topicId: number) => [...topicPromptsKeys.all, topicId] as const,
}

export function useTopicPrompts(topicId: number | undefined) {
  return useQuery({
    queryKey: topicPromptsKeys.byTopic(topicId!),
    queryFn: () => promptsApi.getPromptsByTopicIds([topicId!]),
    enabled: !!topicId,
  })
}
