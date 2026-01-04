/**
 * Review step for prompts before upload - shows similar prompts and allows selection
 */

import { useState, useMemo } from "react"
import { AlertTriangle, Check, Loader2, Upload } from "lucide-react"
import type { Topic, PromptUploadResponse } from "@/types/admin"
import type { BatchPromptAnalysis } from "@/types/batch-upload"
import { useUploadPrompts } from "@/hooks/useAdminPrompts"

interface PromptReviewStepProps {
  items: BatchPromptAnalysis[]
  prompts: string[]
  selectedTopic: Topic
  onBack: () => void
  onSuccess: (result: PromptUploadResponse) => void
}

export function PromptReviewStep({
  items,
  prompts,
  selectedTopic,
  onBack,
  onSuccess,
}: PromptReviewStepProps) {
  // Initialize selection: all non-duplicates selected
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(() => {
    const initial = new Set<number>()
    items.forEach((item) => {
      if (!item.is_duplicate) {
        initial.add(item.index)
      }
    })
    return initial
  })

  const uploadMutation = useUploadPrompts()

  const stats = useMemo(() => {
    const duplicates = items.filter((item) => item.is_duplicate).length
    const withSimilar = items.filter(
      (item) => item.has_matches && !item.is_duplicate
    ).length
    const selected = selectedIndices.size
    return { duplicates, withSimilar, selected, total: items.length }
  }, [items, selectedIndices])

  const toggleSelection = (index: number) => {
    // Can't toggle duplicates
    const item = items.find((i) => i.index === index)
    if (item?.is_duplicate) return

    setSelectedIndices((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const selectAll = () => {
    const all = new Set<number>()
    items.forEach((item) => {
      if (!item.is_duplicate) {
        all.add(item.index)
      }
    })
    setSelectedIndices(all)
  }

  const deselectAll = () => {
    setSelectedIndices(new Set())
  }

  const handleUpload = () => {
    if (selectedIndices.size === 0) return

    uploadMutation.mutate(
      {
        prompts,
        selected_indices: Array.from(selectedIndices),
        topic_id: selectedTopic.id,
      },
      {
        onSuccess: (result) => {
          onSuccess(result)
        },
      }
    )
  }

  const formatSimilarity = (similarity: number) => {
    return `${(similarity * 100).toFixed(1)}%`
  }

  // Get best match for an item (highest similarity)
  const getBestMatch = (item: BatchPromptAnalysis) => {
    if (item.matches.length === 0) return null
    return item.matches.reduce((best, current) =>
      current.similarity > best.similarity ? current : best
    )
  }

  return (
    <div className="space-y-4">
      {/* Stats header */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600">
          <span className="font-medium">{stats.total}</span> prompts total
          {stats.duplicates > 0 && (
            <span className="text-amber-600 ml-2">
              ({stats.duplicates} duplicate{stats.duplicates !== 1 ? "s" : ""})
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={selectAll}
            className="text-xs text-[#C4553D] hover:underline"
          >
            Select all
          </button>
          <span className="text-gray-300">|</span>
          <button
            onClick={deselectAll}
            className="text-xs text-gray-500 hover:underline"
          >
            Deselect all
          </button>
        </div>
      </div>

      {/* Prompts list */}
      <div className="border border-gray-200 rounded-xl overflow-hidden max-h-[400px] overflow-y-auto">
        {items.map((item) => {
          const isSelected = selectedIndices.has(item.index)
          const isDuplicate = item.is_duplicate
          const bestMatch = getBestMatch(item)

          return (
            <div
              key={item.index}
              className={`border-b border-gray-100 last:border-b-0 ${
                isDuplicate ? "bg-gray-50" : ""
              }`}
            >
              <div
                onClick={() => toggleSelection(item.index)}
                className={`flex items-start gap-3 p-3 ${
                  isDuplicate
                    ? "cursor-not-allowed opacity-60"
                    : "cursor-pointer hover:bg-gray-50"
                }`}
              >
                {/* Checkbox */}
                <div
                  className={`flex-shrink-0 w-5 h-5 mt-0.5 rounded border flex items-center justify-center ${
                    isDuplicate
                      ? "bg-gray-200 border-gray-300"
                      : isSelected
                        ? "bg-[#C4553D] border-[#C4553D]"
                        : "border-gray-300 hover:border-gray-400"
                  }`}
                >
                  {(isSelected || isDuplicate) && (
                    <Check className="w-3 h-3 text-white" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p
                    className={`text-sm ${isDuplicate ? "text-gray-500 line-through" : "text-gray-900"}`}
                  >
                    {item.input_text}
                  </p>

                  {/* Similar prompt info - show best match */}
                  {bestMatch && (
                    <div
                      className={`mt-2 text-xs rounded-lg p-2 ${
                        isDuplicate
                          ? "bg-amber-50 border border-amber-200"
                          : "bg-blue-50 border border-blue-100"
                      }`}
                    >
                      <div className="flex items-center gap-1 mb-1">
                        {isDuplicate ? (
                          <>
                            <AlertTriangle className="w-3 h-3 text-amber-600" />
                            <span className="font-medium text-amber-700">
                              Duplicate ({formatSimilarity(bestMatch.similarity)} match)
                            </span>
                          </>
                        ) : (
                          <span className="font-medium text-blue-700">
                            Similar ({formatSimilarity(bestMatch.similarity)} match)
                          </span>
                        )}
                        {item.matches.length > 1 && !isDuplicate && (
                          <span className="text-blue-500 ml-1">
                            +{item.matches.length - 1} more
                          </span>
                        )}
                      </div>
                      <p
                        className={`${isDuplicate ? "text-amber-600" : "text-blue-600"}`}
                      >
                        {bestMatch.prompt_text}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Error message */}
      {uploadMutation.isError && (
        <div className="p-3 bg-red-50 rounded-lg border border-red-100 text-red-600 text-sm">
          {uploadMutation.error?.message || "Upload failed"}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={onBack}
          disabled={uploadMutation.isPending}
          className="flex-1 px-4 py-3 border border-gray-200 rounded-xl
            text-gray-700 font-medium hover:bg-gray-50 transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Back
        </button>
        <button
          onClick={handleUpload}
          disabled={uploadMutation.isPending || selectedIndices.size === 0}
          className="flex-1 px-4 py-3 bg-[#C4553D] text-white rounded-xl
            font-medium hover:bg-[#B04A35] transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed
            flex items-center justify-center gap-2"
        >
          {uploadMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Upload {stats.selected} Prompt{stats.selected !== 1 ? "s" : ""}
            </>
          )}
        </button>
      </div>
    </div>
  )
}
