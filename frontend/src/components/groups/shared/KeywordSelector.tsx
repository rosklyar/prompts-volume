/**
 * KeywordSelector - Keyword selection component for GSC two-step flow
 *
 * Features:
 * - Sort dropdown: clicks | impressions | CTR | position
 * - Keyword list with metrics (query, clicks, impressions, CTR, position)
 * - Checkbox selection with max 20 limit
 * - Counter showing "X/20 selected"
 * - "Generate Prompts" button
 */

import { useMemo } from "react"
import { ChevronDown, Loader2 } from "lucide-react"
import type { GSCSortBy, GSCKeywordInfo } from "@/client/api"

const MAX_KEYWORDS = 20

const SORT_OPTIONS: { value: GSCSortBy; label: string }[] = [
  { value: "clicks", label: "Clicks" },
  { value: "impressions", label: "Impressions" },
  { value: "ctr", label: "CTR" },
  { value: "position", label: "Position" },
]

interface KeywordSelectorProps {
  keywords: GSCKeywordInfo[]
  selectedKeywords: Set<string>
  onToggleKeyword: (query: string) => void
  sortBy: GSCSortBy
  onSortChange: (sortBy: GSCSortBy) => void
  onGeneratePrompts: () => void
  isLoading?: boolean
  isGenerating?: boolean
  accentColor?: string
  maxHeight?: string
}

export function KeywordSelector({
  keywords,
  selectedKeywords,
  onToggleKeyword,
  sortBy,
  onSortChange,
  onGeneratePrompts,
  isLoading = false,
  isGenerating = false,
  accentColor = "#C4553D",
  maxHeight = "320px",
}: KeywordSelectorProps) {
  const canSelect = (query: string) => {
    return selectedKeywords.has(query) || selectedKeywords.size < MAX_KEYWORDS
  }

  const formatMetric = (value: number, type: "clicks" | "impressions" | "ctr" | "position") => {
    if (type === "ctr") {
      return `${(value * 100).toFixed(1)}%`
    }
    if (type === "position") {
      return value.toFixed(1)
    }
    if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`
    }
    return value.toString()
  }

  const sortedKeywords = useMemo(() => {
    const sorted = [...keywords]
    switch (sortBy) {
      case "clicks":
        sorted.sort((a, b) => b.clicks - a.clicks)
        break
      case "impressions":
        sorted.sort((a, b) => b.impressions - a.impressions)
        break
      case "ctr":
        sorted.sort((a, b) => b.ctr - a.ctr)
        break
      case "position":
        sorted.sort((a, b) => a.position - b.position) // Lower is better
        break
    }
    return sorted
  }, [keywords, sortBy])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div
          className="w-6 h-6 border-2 rounded-full animate-spin"
          style={{ borderColor: "#e5e7eb", borderTopColor: accentColor }}
        />
        <span className="ml-3 text-sm text-gray-500">Loading keywords...</span>
      </div>
    )
  }

  if (keywords.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="w-12 h-12 rounded-full bg-gray-100 mx-auto mb-3 flex items-center justify-center">
          <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-700">No keywords found</p>
        <p className="text-xs text-gray-400 mt-1">Try a different GSC property</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header with sort and count */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Sort by:</span>
          <div className="relative">
            <select
              value={sortBy}
              onChange={(e) => onSortChange(e.target.value as GSCSortBy)}
              className="appearance-none bg-white border border-gray-200 rounded-lg px-3 py-1.5 pr-8 text-sm
                focus:outline-none focus:ring-2 cursor-pointer"
              style={{ ["--tw-ring-color" as string]: accentColor }}
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>
        </div>
        <span className="text-sm text-gray-500">
          {selectedKeywords.size}/{MAX_KEYWORDS} selected
        </span>
      </div>

      {/* Keywords list */}
      <div
        className="overflow-y-auto rounded-lg border border-gray-200 divide-y divide-gray-100"
        style={{ maxHeight }}
      >
        {sortedKeywords.map((keyword) => {
          const isSelected = selectedKeywords.has(keyword.query)
          const isDisabled = !canSelect(keyword.query)

          return (
            <label
              key={keyword.query}
              className={`flex items-start gap-3 px-4 py-3 transition-colors ${
                isDisabled && !isSelected ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
              } ${isSelected ? "" : isDisabled ? "" : "hover:bg-gray-50"}`}
              style={{
                backgroundColor: isSelected ? `${accentColor}08` : undefined,
              }}
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => !isDisabled && onToggleKeyword(keyword.query)}
                disabled={isDisabled && !isSelected}
                className="mt-0.5 rounded"
                style={{ accentColor }}
              />
              <div className="flex-1 min-w-0">
                <span className="text-sm text-gray-700 block">{keyword.query}</span>
                <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-xs text-gray-400">
                  <span>Clicks: {formatMetric(keyword.clicks, "clicks")}</span>
                  <span>Imp: {formatMetric(keyword.impressions, "impressions")}</span>
                  <span>CTR: {formatMetric(keyword.ctr, "ctr")}</span>
                  <span>Pos: {formatMetric(keyword.position, "position")}</span>
                </div>
              </div>
            </label>
          )
        })}
      </div>

      {/* Generate button */}
      <div className="flex justify-end pt-2">
        <button
          onClick={onGeneratePrompts}
          disabled={selectedKeywords.size === 0 || isGenerating}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-white font-medium rounded-xl
            transition-colors shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            backgroundColor: accentColor,
            boxShadow: `0 10px 25px -5px ${accentColor}33`,
          }}
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>Generate Prompts</>
          )}
        </button>
      </div>
    </div>
  )
}
