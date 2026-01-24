/**
 * TopicSelectionStep - Step 5 of onboarding for selecting topics
 */

import { LayoutGrid, AlertCircle } from "lucide-react"
import { TopicCard } from "./TopicCard"
import type { Topic } from "@/types/admin"

interface TopicSelectionStepProps {
  topics: Topic[]
  isLoading: boolean
  selectedTopics: Topic[]
  onToggleTopic: (topic: Topic) => void
}

export function TopicSelectionStep({
  topics,
  isLoading,
  selectedTopics,
  onToggleTopic,
}: TopicSelectionStepProps) {
  const selectedCount = selectedTopics.length

  if (isLoading) {
    return (
      <div className="animate-in fade-in duration-300">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
            <LayoutGrid className="w-5 h-5 text-[#C4553D]" />
          </div>
          <div>
            <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
              What topics interest you?
            </h2>
            <p className="text-sm text-[#6B7280]">
              Loading available topics...
            </p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-24 rounded-xl border-2 border-gray-100 bg-gray-50 animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  if (topics.length === 0) {
    return (
      <div className="animate-in fade-in duration-300">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
            <LayoutGrid className="w-5 h-5 text-[#C4553D]" />
          </div>
          <div>
            <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
              What topics interest you?
            </h2>
          </div>
        </div>

        <div className="text-center py-8 px-4 bg-gray-50 rounded-xl border border-gray-200">
          <AlertCircle className="w-10 h-10 text-gray-400 mx-auto mb-3" />
          <p className="text-[#6B7280] mb-1">
            No topics available for your selected market yet.
          </p>
          <p className="text-sm text-gray-400">
            You can skip this step and add topics later from the dashboard.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
          <LayoutGrid className="w-5 h-5 text-[#C4553D]" />
        </div>
        <div>
          <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
            What topics interest you?
          </h2>
          <p className="text-sm text-[#6B7280]">
            Select the areas you'd like to track for your brand
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        {topics.map((topic) => (
          <TopicCard
            key={topic.id}
            topic={topic}
            isSelected={selectedTopics.some((t) => t.id === topic.id)}
            onToggle={onToggleTopic}
          />
        ))}
      </div>

      {selectedCount > 0 && (
        <p className="text-center text-sm text-[#6B7280]">
          {selectedCount} {selectedCount === 1 ? "topic" : "topics"} selected
        </p>
      )}
    </div>
  )
}
