/**
 * PromptGapsList - List of prompts where target brand is not mentioned
 * Warning-styled cards with amber accent
 */

import { useState } from "react"
import type { PromptGap } from "@/types/dashboard"

interface PromptGapsListProps {
  promptGaps: PromptGap[]
  totalCount: number
  hasData: boolean
}

const INITIAL_VISIBLE = 5

export function PromptGapsList({
  promptGaps,
  totalCount,
  hasData,
}: PromptGapsListProps) {
  const [expanded, setExpanded] = useState(false)

  if (!hasData) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6]">
        <h3 className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-6">
          Prompt Gaps
        </h3>
        <p className="text-sm text-[#9CA3AF] text-center py-8">
          No report data available
        </p>
      </div>
    )
  }

  if (promptGaps.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6]">
        <h3 className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-6">
          Prompt Gaps
        </h3>
        <div className="flex flex-col items-center py-8">
          <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center mb-3">
            <svg
              className="w-5 h-5 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <p className="text-sm text-[#6B7280]">
            Your brand is mentioned in all prompts
          </p>
        </div>
      </div>
    )
  }

  const visibleGaps = expanded ? promptGaps : promptGaps.slice(0, INITIAL_VISIBLE)
  const hasMore = promptGaps.length > INITIAL_VISIBLE

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6]">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide">
          Prompt Gaps
        </h3>
        <span className="text-xs px-2 py-1 rounded-full bg-amber-100 text-amber-700 font-medium">
          {totalCount} missing
        </span>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {visibleGaps.map((gap) => (
          <div
            key={gap.prompt_id}
            className="p-3 bg-amber-50/50 rounded-lg border-l-2 border-amber-400"
          >
            <div className="flex items-start gap-2">
              <svg
                className="w-4 h-4 text-amber-500 shrink-0 mt-0.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <p
                className="text-sm text-[#1F2937] line-clamp-2"
                title={gap.prompt_text}
              >
                {gap.prompt_text}
              </p>
            </div>
          </div>
        ))}
      </div>

      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-4 w-full text-center text-sm text-[#C4553D] hover:text-[#A3442F] font-medium transition-colors"
        >
          {expanded
            ? "Show less"
            : `View all ${totalCount} prompts`}
        </button>
      )}
    </div>
  )
}
