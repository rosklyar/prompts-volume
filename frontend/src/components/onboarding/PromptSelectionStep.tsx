/**
 * PromptSelectionStep - Step 6 of onboarding for selecting prompts per topic
 */

import { ListChecks } from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { promptsApi } from "@/client/api"
import { TopicPromptSection } from "./TopicPromptSection"
import type { Topic } from "@/types/admin"

interface PromptSelectionStepProps {
  selectedTopics: Topic[]
  selectedPromptsByTopic: Record<number, number[]>
  onTogglePrompt: (topicId: number, promptId: number) => void
  onSelectAllForTopic: (topicId: number, promptIds: number[]) => void
  onDeselectAllForTopic: (topicId: number) => void
}

export function PromptSelectionStep({
  selectedTopics,
  selectedPromptsByTopic,
  onTogglePrompt,
  onSelectAllForTopic,
  onDeselectAllForTopic,
}: PromptSelectionStepProps) {
  const topicIds = selectedTopics.map((t) => t.id)

  const { data: promptsData, isLoading } = useQuery({
    queryKey: ["topicPrompts", "batch", topicIds],
    queryFn: () => promptsApi.getPromptsByTopicIds(topicIds),
    enabled: topicIds.length > 0,
  })

  const totalSelectedCount = Object.values(selectedPromptsByTopic).reduce(
    (sum, ids) => sum + ids.length,
    0
  )

  const topicsWithPrompts = selectedTopics.length

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
          <ListChecks className="w-5 h-5 text-[#C4553D]" />
        </div>
        <div>
          <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
            Choose your prompts
          </h2>
          <p className="text-sm text-[#6B7280]">
            Select which questions to track for each topic
          </p>
        </div>
      </div>

      <div className="space-y-4 mb-4">
        {selectedTopics.map((topic) => {
          const topicPromptsGroup = promptsData?.topics.find(
            (t) => t.topic_id === topic.id
          )
          const prompts = topicPromptsGroup?.prompts || []
          const selectedIds = selectedPromptsByTopic[topic.id] || []

          return (
            <TopicPromptSection
              key={topic.id}
              topic={topic}
              prompts={prompts}
              isLoading={isLoading}
              selectedPromptIds={selectedIds}
              onTogglePrompt={onTogglePrompt}
              onSelectAll={onSelectAllForTopic}
              onDeselectAll={onDeselectAllForTopic}
            />
          )
        })}
      </div>

      {totalSelectedCount > 0 && (
        <p className="text-center text-sm text-[#6B7280]">
          {totalSelectedCount} {totalSelectedCount === 1 ? "prompt" : "prompts"}{" "}
          selected across {topicsWithPrompts}{" "}
          {topicsWithPrompts === 1 ? "topic" : "topics"}
        </p>
      )}
    </div>
  )
}
