/**
 * PromptItem - Draggable prompt with expandable answer
 */

import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { useState } from "react"
import type { PromptInGroup, EvaluationAnswer } from "@/client/api"
import type { BrandMentionResult } from "@/types/groups"
import type { PromptFreshnessInfo } from "@/types/billing"
import { HighlightedResponse } from "./HighlightedResponse"
import { formatReportTime } from "@/hooks/useReports"
import { getBrandColor } from "./constants"

interface PromptItemProps {
  prompt: PromptInGroup & {
    answer?: EvaluationAnswer | null
    brand_mentions?: BrandMentionResult[] | null
    isLoading?: boolean
  }
  groupId: number
  accentColor: string
  targetBrandName?: string | null
  competitorNames?: string[]
  onDelete: (promptId: number) => void
  isDragOverlay?: boolean
  freshnessInfo?: PromptFreshnessInfo
}


export function PromptItem({
  prompt,
  groupId,
  accentColor,
  targetBrandName,
  competitorNames = [],
  onDelete,
  isDragOverlay = false,
  freshnessInfo,
}: PromptItemProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Get all brands that are mentioned in the answer
  const mentionedBrands = prompt.brand_mentions?.filter(
    (bm) => bm.mentions.length > 0
  ) || []

  // Check if target brand is among mentioned brands
  const hasTargetBrandMention = mentionedBrands.some(
    (bm) => bm.brand_name === targetBrandName
  )

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: `${groupId}-${prompt.prompt_id}`,
    data: {
      type: "prompt",
      prompt,
      groupId,
    },
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const hasAnswer = !!prompt.answer

  return (
    <div
      ref={setNodeRef}
      style={{
        ...style,
        ...(hasTargetBrandMention ? { borderLeftColor: accentColor, borderLeftWidth: "3px" } : {}),
      }}
      className={`
        group relative bg-white rounded-xl border border-gray-100
        transition-all duration-200
        ${isDragging ? "opacity-50 scale-[0.98]" : ""}
        ${isDragOverlay ? "shadow-xl rotate-[-2deg] scale-105 max-w-sm" : "hover:shadow-md"}
        ${hasTargetBrandMention ? "shadow-sm" : ""}
      `}
    >
      {/* Main prompt row */}
      <div className="flex items-start gap-3 p-3">
        {/* Drag handle */}
        <button
          {...attributes}
          {...listeners}
          className="shrink-0 mt-1 cursor-grab active:cursor-grabbing
            text-gray-300 hover:text-gray-500 transition-colors
            focus:outline-none focus:ring-2 focus:ring-offset-2 rounded"
          style={{ ["--tw-ring-color" as string]: accentColor }}
          aria-label="Drag to reorder"
        >
          <svg
            className="w-4 h-4"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
          </svg>
        </button>

        {/* Prompt content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2">
            <p className="text-[14px] leading-relaxed text-gray-800 line-clamp-2 flex-1">
              {prompt.prompt_text}
            </p>
            {/* Brand mention tags */}
            {mentionedBrands.length > 0 && (
              <div className="shrink-0 flex flex-wrap gap-1 justify-end max-w-[180px]">
                {mentionedBrands.map((bm) => {
                  const isTargetBrand = bm.brand_name === targetBrandName
                  const brandColor = getBrandColor(bm.brand_name, targetBrandName, competitorNames, accentColor)

                  return (
                    <span
                      key={bm.brand_name}
                      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] ${
                        isTargetBrand ? "font-semibold" : "font-normal"
                      }`}
                      style={{
                        backgroundColor: brandColor.bg,
                        color: brandColor.text,
                      }}
                      title={`${bm.mentions.length} mention${bm.mentions.length !== 1 ? "s" : ""} in answer`}
                    >
                      {bm.brand_name}
                    </span>
                  )
                })}
              </div>
            )}
          </div>

          {/* Freshness info */}
          {freshnessInfo && (
            <div className="mt-1.5 flex items-center gap-2 text-[10px]">
              {/* Fresh badge */}
              {freshnessInfo.has_fresher_answer && (
                <span
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-medium"
                  style={{ backgroundColor: "#dcfce7", color: "#16a34a" }}
                >
                  <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  Fresh
                </span>
              )}
              {/* Latest answer timestamp */}
              {freshnessInfo.latest_answer_at && (
                <span className="text-gray-400">
                  Updated {formatReportTime(freshnessInfo.latest_answer_at)}
                </span>
              )}
              {/* Next refresh estimate (when not fresh) */}
              {!freshnessInfo.has_fresher_answer && !freshnessInfo.has_in_progress_evaluation && (
                <span className="text-gray-400">
                  Next: {freshnessInfo.next_refresh_estimate}
                </span>
              )}
              {/* In progress indicator */}
              {freshnessInfo.has_in_progress_evaluation && (
                <span className="inline-flex items-center gap-1 text-amber-600">
                  <div
                    className="w-2 h-2 border border-amber-600 border-t-transparent rounded-full animate-spin"
                  />
                  {freshnessInfo.next_refresh_estimate}
                </span>
              )}
            </div>
          )}

          {/* Loading indicator */}
          {prompt.isLoading && (
            <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
              <div
                className="w-3 h-3 border-2 rounded-full animate-spin"
                style={{
                  borderColor: `${accentColor}30`,
                  borderTopColor: accentColor,
                }}
              />
              Loading answer...
            </div>
          )}
        </div>

        {/* Expand/collapse button - only show when answer exists */}
        {hasAnswer && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="shrink-0 w-7 h-7 rounded-md flex items-center justify-center
              transition-all duration-200 hover:bg-gray-100"
            style={{ color: accentColor }}
            aria-label={isExpanded ? "Collapse answer" : "Expand answer"}
          >
            <svg
              className={`w-4 h-4 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        )}

        {/* Delete button */}
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete(prompt.prompt_id)
          }}
          className="shrink-0 w-7 h-7 rounded-md flex items-center justify-center
            text-gray-300 hover:text-red-500 hover:bg-red-50
            transition-all duration-150 opacity-0 group-hover:opacity-100
            focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-red-200"
          aria-label="Delete prompt"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Expanded answer section */}
      {isExpanded && prompt.answer && (
        <div
          className="border-t px-4 py-3 animate-in slide-in-from-top-2 duration-200"
          style={{ borderColor: `${accentColor}20`, backgroundColor: `${accentColor}05` }}
        >

          {/* Response */}
          {prompt.brand_mentions && prompt.brand_mentions.length > 0 ? (
            <HighlightedResponse
              response={prompt.answer.response}
              brandMentions={prompt.brand_mentions}
              accentColor={accentColor}
              targetBrandName={targetBrandName}
              competitorNames={competitorNames}
            />
          ) : (
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {prompt.answer.response}
            </p>
          )}

          {/* Citations */}
          {prompt.answer.citations.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs font-medium text-gray-500 mb-2">Sources</p>
              <ul className="space-y-1.5">
                {prompt.answer.citations.map((citation, idx) => (
                  <li key={idx} className="text-xs">
                    <a
                      href={citation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline transition-colors"
                      style={{ color: accentColor }}
                    >
                      {citation.text || citation.url}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Timestamp */}
          <p className="mt-2 text-[10px] text-gray-400">
            Evaluated: {new Date(prompt.answer.timestamp).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  )
}
