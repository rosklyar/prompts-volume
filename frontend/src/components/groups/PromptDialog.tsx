/**
 * PromptDialog — "The Reading Room"
 * Almost-full-screen modal for viewing AI evaluation answers.
 * Light editorial aesthetic matching the app's clean style.
 */

import { useEffect, useState, useCallback } from "react"
import { createPortal } from "react-dom"
import type { EvaluationAnswer } from "@/client/api"
import type { BrandMentionResult, DomainMentionResult } from "@/types/groups"
import { HighlightedResponse } from "./HighlightedResponse"

interface PromptDialogProps {
  isOpen: boolean
  onClose: () => void
  promptText: string
  answer: EvaluationAnswer
  brandMentions?: BrandMentionResult[] | null
  domainMentions?: DomainMentionResult[] | null
  accentColor: string
  targetBrandName?: string | null
  competitorNames?: string[]
}

type Tab = "answer" | "sources"

export function PromptDialog({
  isOpen,
  onClose,
  promptText,
  answer,
  brandMentions,
  domainMentions,
  accentColor,
  targetBrandName,
  competitorNames = [],
}: PromptDialogProps) {
  const [activeTab, setActiveTab] = useState<Tab>("answer")

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    },
    [onClose],
  )

  useEffect(() => {
    if (!isOpen) return
    document.addEventListener("keydown", handleKeyDown)
    document.body.style.overflow = "hidden"
    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      document.body.style.overflow = ""
    }
  }, [isOpen, handleKeyDown])

  if (!isOpen) return null

  const hasCitations = answer.citations.length > 0
  const hasSearchQueries =
    answer.web_search_queries && answer.web_search_queries.length > 0

  const hasHighlights =
    (brandMentions && brandMentions.length > 0) ||
    (domainMentions && domainMentions.length > 0)

  const formattedDate = new Date(answer.timestamp).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-200">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Modal panel */}
      <div
        className="relative flex flex-col w-full max-w-4xl h-[90vh] bg-white rounded-xl shadow-xl
          overflow-hidden animate-in zoom-in-95 duration-200"
      >
        {/* Accent top bar */}
        <div className="h-[3px] shrink-0" style={{ backgroundColor: accentColor }} />

        {/* Close button — pinned top-right */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 w-8 h-8 rounded-lg flex items-center justify-center
            text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          aria-label="Close dialog"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Scrollable content — single flow */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-[720px] mx-auto px-8 py-8 sm:px-12 sm:py-10">
            {/* Prompt text */}
            <h2
              className="text-xl sm:text-2xl leading-relaxed text-gray-900 pr-8"
              style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
            >
              {promptText}
            </h2>

            {/* Tabs */}
            <div className="mt-4 mb-6 flex gap-4 border-b border-gray-200">
              <button
                onClick={() => setActiveTab("answer")}
                className={`pb-2 text-sm font-medium transition-colors ${
                  activeTab === "answer"
                    ? "text-gray-900 border-b-2"
                    : "text-gray-400 hover:text-gray-600"
                }`}
                style={activeTab === "answer" ? { borderBottomColor: accentColor } : undefined}
              >
                Answer
              </button>
              {hasCitations && (
                <button
                  onClick={() => setActiveTab("sources")}
                  className={`pb-2 text-sm font-medium transition-colors ${
                    activeTab === "sources"
                      ? "text-gray-900 border-b-2"
                      : "text-gray-400 hover:text-gray-600"
                  }`}
                  style={activeTab === "sources" ? { borderBottomColor: accentColor } : undefined}
                >
                  Sources
                  <span className="ml-1.5 text-xs text-gray-400">{answer.citations.length}</span>
                </button>
              )}
            </div>

            {/* Tab: Answer */}
            {activeTab === "answer" && (
              <>
                {hasHighlights ? (
                  <HighlightedResponse
                    response={answer.response}
                    brandMentions={brandMentions || null}
                    domainMentions={domainMentions || null}
                    accentColor={accentColor}
                    targetBrandName={targetBrandName}
                    competitorNames={competitorNames}
                  />
                ) : (
                  <p
                    className="text-base text-gray-700 leading-relaxed whitespace-pre-wrap"
                    style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
                  >
                    {answer.response}
                  </p>
                )}

                {/* Search queries under the answer */}
                {hasSearchQueries && (
                  <div className="mt-8 pt-6 border-t border-gray-100">
                    <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
                      Search Queries
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {answer.web_search_queries!.map((query, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center px-2.5 py-1 rounded-full text-xs
                            bg-gray-100 text-gray-600"
                        >
                          {query}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Tab: Sources */}
            {activeTab === "sources" && hasCitations && (
              <ul className="space-y-1.5">
                {answer.citations.map((citation, idx) => (
                  <li key={idx} className="text-sm">
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
            )}

            {/* Timestamp at bottom */}
            <div className="mt-8 pt-4 border-t border-gray-100">
              <p className="text-[10px] text-gray-400">
                Evaluated: {formattedDate}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}
