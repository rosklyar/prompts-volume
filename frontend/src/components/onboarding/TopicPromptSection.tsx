/**
 * TopicPromptSection - Collapsible section per topic for prompt selection
 */

import { useState } from "react"
import { ChevronDown, Check } from "lucide-react"
import type { Topic } from "@/types/admin"
import type { TopicPrompt } from "@/client/api"

interface TopicPromptSectionProps {
  topic: Topic
  prompts: TopicPrompt[]
  isLoading: boolean
  selectedPromptIds: number[]
  onTogglePrompt: (topicId: number, promptId: number) => void
  onSelectAll: (topicId: number, promptIds: number[]) => void
  onDeselectAll: (topicId: number) => void
}

export function TopicPromptSection({
  topic,
  prompts,
  isLoading,
  selectedPromptIds,
  onTogglePrompt,
  onSelectAll,
  onDeselectAll,
}: TopicPromptSectionProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  const selectedCount = selectedPromptIds.length
  const totalCount = prompts.length
  const allSelected = totalCount > 0 && selectedCount === totalCount

  const handleToggleAll = () => {
    if (allSelected) {
      onDeselectAll(topic.id)
    } else {
      onSelectAll(topic.id, prompts.map((p) => p.id))
    }
  }

  if (isLoading) {
    return (
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
          <span className="font-['Fraunces'] text-base font-medium text-[#1F2937]">
            {topic.title}
          </span>
          <span className="text-sm text-gray-400">Loading...</span>
        </div>
        <div className="p-4 space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-10 rounded-lg bg-gray-50 animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  if (prompts.length === 0) {
    return (
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 bg-gray-50">
          <span className="font-['Fraunces'] text-base font-medium text-[#1F2937]">
            {topic.title}
          </span>
        </div>
        <div className="p-4 text-center text-sm text-gray-400">
          No prompts available for this topic
        </div>
      </div>
    )
  }

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-left"
        >
          <ChevronDown
            className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${
              isExpanded ? "" : "-rotate-90"
            }`}
          />
          <span className="font-['Fraunces'] text-base font-medium text-[#1F2937]">
            {topic.title}
          </span>
        </button>
        <button
          type="button"
          onClick={handleToggleAll}
          className="text-sm text-[#C4553D] hover:underline"
        >
          {allSelected ? "Deselect all" : `Select all (${totalCount})`}
        </button>
      </div>

      {/* Prompts list */}
      {isExpanded && (
        <div className="divide-y divide-gray-100">
          {prompts.map((prompt) => {
            const isSelected = selectedPromptIds.includes(prompt.id)
            return (
              <button
                key={prompt.id}
                type="button"
                onClick={() => onTogglePrompt(topic.id, prompt.id)}
                className={`
                  w-full flex items-start gap-3 px-4 py-3 text-left transition-colors
                  hover:bg-gray-50
                  ${isSelected ? "bg-[#C4553D]/[0.02]" : "bg-white"}
                `}
              >
                {/* Checkbox */}
                <div
                  className={`
                    flex-shrink-0 w-5 h-5 mt-0.5 rounded border-2 flex items-center justify-center
                    transition-colors duration-200
                    ${isSelected
                      ? "border-[#C4553D] bg-[#C4553D]"
                      : "border-gray-300 bg-white"
                    }
                  `}
                >
                  {isSelected && (
                    <Check className="w-3 h-3 text-white" strokeWidth={3} />
                  )}
                </div>

                {/* Prompt text */}
                <span className="text-sm text-[#374151] leading-relaxed">
                  {prompt.prompt_text}
                </span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
