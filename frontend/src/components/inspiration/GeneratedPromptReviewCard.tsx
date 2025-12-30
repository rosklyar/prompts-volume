/**
 * GeneratedPromptReviewCard - Review card for a single generated prompt
 * Radio selection between keep original and use match (like BatchUploadModal)
 */

import { useState } from "react"
import { ChevronRight, Sparkles } from "lucide-react"
import type { GeneratedPromptReview } from "@/types/inspiration"

interface GeneratedPromptReviewCardProps {
  prompt: GeneratedPromptReview
  accentColor: string
  onChange: (
    selectedOption: "keep-original" | "use-match",
    matchId: number | null
  ) => void
}

export function GeneratedPromptReviewCard({
  prompt,
  accentColor,
  onChange,
}: GeneratedPromptReviewCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const hasMatches = prompt.matches.length > 0
  const selectedMatch = prompt.matches.find((m) => m.promptId === prompt.selectedMatchId)

  // Determine badge text
  const getBadgeText = () => {
    if (prompt.selectedOption === "use-match" && selectedMatch) {
      return `Match ${Math.round(selectedMatch.similarity * 100)}%`
    }
    return "New"
  }

  return (
    <div className="group">
      {/* Collapsed header */}
      <div
        className="flex items-center gap-3 px-5 py-3 cursor-pointer select-none transition-colors hover:bg-[#FAFAFA]"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {/* Expand chevron */}
        <ChevronRight
          className="w-4 h-4 text-[#9CA3AF] transition-transform duration-200 flex-shrink-0"
          style={{ transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)" }}
        />

        {/* Prompt text */}
        <p className="flex-1 text-sm text-[#4B5563] font-['DM_Sans'] truncate min-w-0">
          {prompt.inputText}
        </p>

        {/* Selection badge */}
        <span
          className="text-[11px] font-medium px-2 py-1 rounded-full whitespace-nowrap flex-shrink-0 transition-colors"
          style={{
            backgroundColor:
              prompt.selectedOption === "use-match" ? `${accentColor}15` : "#F3F4F6",
            color: prompt.selectedOption === "use-match" ? accentColor : "#6B7280",
          }}
        >
          {getBadgeText()}
        </span>
      </div>

      {/* Expanded content */}
      <div
        className="overflow-hidden transition-all duration-200"
        style={{
          maxHeight: isExpanded ? "500px" : "0",
          opacity: isExpanded ? 1 : 0,
        }}
      >
        <div className="px-5 pb-4 pt-1 space-y-2 ml-7">
          {/* Keywords */}
          {prompt.keywords.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {prompt.keywords.slice(0, 5).map((keyword, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 text-[10px] font-medium text-[#6B7280] bg-[#F3F4F6] rounded-full"
                >
                  {keyword}
                </span>
              ))}
              {prompt.keywords.length > 5 && (
                <span className="px-2 py-0.5 text-[10px] text-[#9CA3AF]">
                  +{prompt.keywords.length - 5} more
                </span>
              )}
            </div>
          )}

          {/* Keep original option */}
          <label
            className={`
              flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-all
              ${
                prompt.selectedOption === "keep-original"
                  ? "ring-2"
                  : "hover:bg-[#FAFAFA]"
              }
            `}
            style={{
              backgroundColor:
                prompt.selectedOption === "keep-original" ? `${accentColor}08` : undefined,
              ["--tw-ring-color" as string]:
                prompt.selectedOption === "keep-original" ? accentColor : undefined,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <input
              type="radio"
              name={`selection-${prompt.inputText}`}
              checked={prompt.selectedOption === "keep-original"}
              onChange={() => onChange("keep-original", null)}
              className="mt-0.5"
              style={{ accentColor }}
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-[#C4553D]" />
                <p className="text-sm font-medium text-[#374151] font-['DM_Sans']">
                  Keep original (add as new)
                </p>
              </div>
              <p className="text-xs text-[#9CA3AF] mt-0.5 font-['DM_Sans']">
                {prompt.inputText}
              </p>
            </div>
          </label>

          {/* Match options */}
          {prompt.matches.map((match) => {
            const isSelected =
              prompt.selectedOption === "use-match" &&
              prompt.selectedMatchId === match.promptId
            return (
              <label
                key={match.promptId}
                className={`
                  flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-all
                  ${isSelected ? "ring-2" : "hover:bg-[#FAFAFA]"}
                `}
                style={{
                  backgroundColor: isSelected ? `${accentColor}08` : undefined,
                  ["--tw-ring-color" as string]: isSelected ? accentColor : undefined,
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <input
                  type="radio"
                  name={`selection-${prompt.inputText}`}
                  checked={isSelected}
                  onChange={() => onChange("use-match", match.promptId)}
                  className="mt-0.5"
                  style={{ accentColor }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm text-[#4B5563] font-['DM_Sans']">
                      {match.promptText}
                    </p>
                    <span
                      className="text-[10px] font-medium px-1.5 py-0.5 rounded-full whitespace-nowrap"
                      style={{
                        backgroundColor: `${accentColor}15`,
                        color: accentColor,
                      }}
                    >
                      {Math.round(match.similarity * 100)}%
                    </span>
                  </div>
                  <p className="text-xs text-[#9CA3AF] mt-0.5 font-['DM_Sans']">
                    Use existing prompt from database
                  </p>
                </div>
              </label>
            )
          })}

          {/* No matches indicator */}
          {!hasMatches && (
            <div className="px-3 py-2 text-xs text-[#9CA3AF] font-['DM_Sans'] italic">
              No similar prompts found in database
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
