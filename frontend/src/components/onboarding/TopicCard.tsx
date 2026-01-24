/**
 * TopicCard - Selectable card for topic selection in onboarding
 */

import { Check } from "lucide-react"
import type { Topic } from "@/types/admin"

interface TopicCardProps {
  topic: Topic
  isSelected: boolean
  onToggle: (topic: Topic) => void
}

export function TopicCard({ topic, isSelected, onToggle }: TopicCardProps) {
  return (
    <button
      type="button"
      onClick={() => onToggle(topic)}
      className={`
        relative w-full text-left p-5 rounded-xl border-2 transition-all duration-200
        hover:-translate-y-0.5 hover:shadow-md
        ${isSelected
          ? "border-[#C4553D] bg-[#C4553D]/[0.04] shadow-sm"
          : "border-gray-200 bg-white hover:border-gray-300"
        }
      `}
    >
      {/* Selection indicator */}
      <div
        className={`
          absolute top-4 right-4 w-5 h-5 rounded-md border-2 flex items-center justify-center
          transition-colors duration-200
          ${isSelected
            ? "border-[#C4553D] bg-[#C4553D]"
            : "border-gray-300 bg-white"
          }
        `}
      >
        {isSelected && <Check className="w-3 h-3 text-white" strokeWidth={3} />}
      </div>

      {/* Content */}
      <div className="pr-8">
        <h3 className="font-['Fraunces'] text-base font-medium text-[#1F2937] mb-1.5">
          {topic.title}
        </h3>
        <p className="text-sm text-[#6B7280] leading-relaxed line-clamp-2">
          {topic.description}
        </p>
      </div>
    </button>
  )
}
