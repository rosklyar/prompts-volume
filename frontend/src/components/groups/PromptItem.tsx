/**
 * PromptItem - Draggable prompt with expandable answer
 */

import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { useState } from "react"
import type { PromptInGroup, EvaluationAnswer } from "@/client/api"
import type { BrandMentionResult } from "@/types/groups"
import { HighlightedResponse } from "./HighlightedResponse"

interface PromptItemProps {
  prompt: PromptInGroup & {
    answer?: EvaluationAnswer | null
    brand_mentions?: BrandMentionResult[] | null
    isLoading?: boolean
  }
  groupId: number
  accentColor: string
  onDelete: (promptId: number) => void
  isDragOverlay?: boolean
}

export function PromptItem({
  prompt,
  groupId,
  accentColor,
  onDelete,
  isDragOverlay = false,
}: PromptItemProps) {
  const [isExpanded, setIsExpanded] = useState(false)

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
      style={style}
      className={`
        group relative bg-white rounded-xl border border-gray-100
        transition-all duration-200
        ${isDragging ? "opacity-50 scale-[0.98]" : ""}
        ${isDragOverlay ? "shadow-xl rotate-[-2deg] scale-105 max-w-sm" : "hover:shadow-md"}
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
          <button
            onClick={() => hasAnswer && setIsExpanded(!isExpanded)}
            className={`text-left w-full text-[14px] leading-relaxed text-gray-800
              ${hasAnswer ? "cursor-pointer hover:text-gray-600" : "cursor-default"}`}
          >
            <span className="line-clamp-2">{prompt.prompt_text}</span>
          </button>

          {/* Answer indicator */}
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

          {hasAnswer && !isExpanded && (
            <button
              onClick={() => setIsExpanded(true)}
              className="mt-2 flex items-center gap-1.5 text-xs transition-colors"
              style={{ color: accentColor }}
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              View answer
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
        </div>

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
          <button
            onClick={() => setIsExpanded(false)}
            className="flex items-center gap-1 text-xs mb-2 transition-colors"
            style={{ color: accentColor }}
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
            Hide answer
          </button>

          {/* Response */}
          {prompt.brand_mentions && prompt.brand_mentions.length > 0 ? (
            <HighlightedResponse
              response={prompt.answer.response}
              brandMentions={prompt.brand_mentions}
              accentColor={accentColor}
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
