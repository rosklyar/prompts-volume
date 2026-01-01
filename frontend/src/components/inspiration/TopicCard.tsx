/**
 * TopicCard - Collapsible card for displaying a topic with its prompts
 * Editorial design with color accents and smooth animations
 */

import { getGroupColor } from "@/components/groups/constants"
import {
  ChevronRight,
  Loader2,
  Check,
  CheckSquare,
  Square,
  FolderPlus,
  CheckCircle2,
} from "lucide-react"
import type { TopicWithPrompts } from "@/types/inspiration"

interface TopicCardProps {
  topic: TopicWithPrompts
  colorIndex: number
  onToggleExpand: () => void
  onTogglePrompt: (promptId: number) => void
  onSelectAll: () => void
  onDeselectAll: () => void
  onAddToGroup?: () => void
}

export function TopicCard({
  topic,
  colorIndex,
  onToggleExpand,
  onTogglePrompt,
  onSelectAll,
  onDeselectAll,
  onAddToGroup,
}: TopicCardProps) {
  const color = getGroupColor(colorIndex)
  const selectedCount = topic.prompts.filter((p) => p.isSelected).length
  const allSelected = topic.prompts.length > 0 && selectedCount === topic.prompts.length
  const hasSelections = selectedCount > 0

  // Already added to a group
  if (topic.addedToGroupId) {
    return (
      <div
        className="rounded-2xl border-2 border-dashed overflow-hidden transition-all duration-200"
        style={{ borderColor: color.accent, backgroundColor: `${color.bg}40` }}
      >
        <div className="px-5 py-4 flex items-center gap-4">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ backgroundColor: `${color.accent}20` }}
          >
            <CheckCircle2 className="w-5 h-5" style={{ color: color.accent }} />
          </div>
          <div className="flex-1 min-w-0">
            <h3
              className="font-['Fraunces'] text-base font-semibold truncate"
              style={{ color: color.accent }}
            >
              {topic.topicTitle}
            </h3>
            <p className="text-sm text-[#6B7280] font-['DM_Sans']">
              Added to{" "}
              <span className="font-medium" style={{ color: color.accent }}>
                {topic.addedToGroupTitle}
              </span>
            </p>
          </div>
          <span
            className="px-3 py-1.5 rounded-full text-xs font-medium font-['DM_Sans']"
            style={{ backgroundColor: `${color.accent}15`, color: color.accent }}
          >
            Complete
          </span>
        </div>
      </div>
    )
  }

  return (
    <div
      className="rounded-2xl border overflow-hidden transition-all duration-200 group"
      style={{
        borderColor: topic.isExpanded ? color.accent : "#E5E7EB",
        boxShadow: topic.isExpanded
          ? `0 4px 20px -4px ${color.accent}25`
          : "0 2px 8px -2px rgba(0,0,0,0.05)",
      }}
    >
      {/* Header */}
      <div
        className="px-5 py-4 cursor-pointer select-none transition-colors"
        style={{
          backgroundColor: topic.isExpanded ? color.bg : "white",
        }}
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-4">
          {/* Expand chevron */}
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200"
            style={{
              backgroundColor: topic.isExpanded ? `${color.accent}20` : "#F3F4F6",
            }}
          >
            {topic.isLoading ? (
              <Loader2
                className="w-4 h-4 animate-spin"
                style={{ color: color.accent }}
              />
            ) : (
              <ChevronRight
                className="w-4 h-4 transition-transform duration-200"
                style={{
                  color: topic.isExpanded ? color.accent : "#9CA3AF",
                  transform: topic.isExpanded ? "rotate(90deg)" : "rotate(0deg)",
                }}
              />
            )}
          </div>

          {/* Topic info */}
          <div className="flex-1 min-w-0">
            <h3
              className="font-['Fraunces'] text-base font-semibold truncate transition-colors"
              style={{ color: topic.isExpanded ? color.accent : "#1F2937" }}
            >
              {topic.topicTitle}
            </h3>
            <p className="text-sm text-[#6B7280] font-['DM_Sans']">
              {topic.prompts.length > 0
                ? `${topic.prompts.length} prompts available`
                : "Click to load prompts"}
            </p>
          </div>

          {/* Selection badge */}
          {hasSelections && (
            <span
              className="px-3 py-1.5 rounded-full text-xs font-medium font-['DM_Sans'] transition-all"
              style={{ backgroundColor: `${color.accent}15`, color: color.accent }}
            >
              {selectedCount} selected
            </span>
          )}
        </div>
      </div>

      {/* Expanded content */}
      <div
        className="overflow-hidden transition-all duration-300"
        style={{
          maxHeight: topic.isExpanded ? "600px" : "0",
          opacity: topic.isExpanded ? 1 : 0,
        }}
      >
        {topic.prompts.length > 0 && (
          <div className="border-t" style={{ borderColor: `${color.accent}30` }}>
            {/* Bulk actions */}
            <div
              className="px-5 py-3 flex items-center justify-between"
              style={{ backgroundColor: `${color.bg}60` }}
            >
              <div className="flex items-center gap-3">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    if (allSelected) {
                      onDeselectAll()
                    } else {
                      onSelectAll()
                    }
                  }}
                  className="flex items-center gap-2 text-sm text-[#6B7280] hover:text-[#1F2937] font-['DM_Sans'] transition-colors"
                >
                  {allSelected ? (
                    <>
                      <CheckSquare className="w-4 h-4" style={{ color: color.accent }} />
                      <span>Deselect all</span>
                    </>
                  ) : (
                    <>
                      <Square className="w-4 h-4" />
                      <span>Select all</span>
                    </>
                  )}
                </button>
              </div>

              {hasSelections && onAddToGroup && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onAddToGroup()
                  }}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white rounded-lg transition-all hover:shadow-md"
                  style={{ backgroundColor: color.accent }}
                >
                  <FolderPlus className="w-4 h-4" />
                  <span className="font-['DM_Sans']">Add to Group</span>
                </button>
              )}
            </div>

            {/* Prompts list */}
            <div className="max-h-80 overflow-y-auto">
              {topic.prompts.map((prompt) => (
                <label
                  key={prompt.promptId}
                  className="flex items-start gap-3 px-5 py-3 cursor-pointer transition-colors hover:bg-[#FAFAFA] border-b border-[#E5E7EB]/50 last:border-b-0"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="mt-0.5">
                    <input
                      type="checkbox"
                      checked={prompt.isSelected}
                      onChange={() => onTogglePrompt(prompt.promptId)}
                      className="sr-only"
                    />
                    <div
                      className="w-5 h-5 rounded border-2 flex items-center justify-center transition-all duration-150"
                      style={{
                        borderColor: prompt.isSelected ? color.accent : "#D1D5DB",
                        backgroundColor: prompt.isSelected ? color.accent : "transparent",
                      }}
                    >
                      {prompt.isSelected && (
                        <Check className="w-3 h-3 text-white" strokeWidth={3} />
                      )}
                    </div>
                  </div>
                  <span
                    className={`text-sm font-['DM_Sans'] leading-relaxed transition-colors ${
                      prompt.isSelected ? "text-[#1F2937]" : "text-[#6B7280]"
                    }`}
                  >
                    {prompt.promptText}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Loading state */}
        {topic.isLoading && (
          <div className="px-5 py-8 text-center border-t border-[#E5E7EB]/50">
            <Loader2
              className="w-6 h-6 animate-spin mx-auto mb-2"
              style={{ color: color.accent }}
            />
            <p className="text-sm text-[#6B7280] font-['DM_Sans']">
              Loading prompts...
            </p>
          </div>
        )}

        {/* Empty state after loading */}
        {!topic.isLoading && topic.prompts.length === 0 && topic.isExpanded && (
          <div className="px-5 py-8 text-center border-t border-[#E5E7EB]/50">
            <p className="text-sm text-[#9CA3AF] font-['DM_Sans']">
              No prompts found for this topic
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
