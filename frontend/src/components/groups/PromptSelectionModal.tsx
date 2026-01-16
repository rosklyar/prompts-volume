/**
 * PromptSelectionModal - Modal for selecting prompts from a topic to add to a newly created group
 *
 * Shown after creating a group with an existing public topic binding.
 * Allows users to select which prompts from the topic they want to add.
 */

import { useState, useMemo } from "react"
import { useTopicPrompts } from "@/hooks/useTopicPrompts"
import { useAddPromptsToGroup } from "@/hooks/useGroups"

interface PromptSelectionModalProps {
  groupId: number
  groupTitle: string
  topicId: number
  topicTitle: string
  accentColor: string
  isOpen: boolean
  onClose: () => void
}

export function PromptSelectionModal({
  groupId,
  groupTitle,
  topicId,
  topicTitle,
  accentColor,
  isOpen,
  onClose,
}: PromptSelectionModalProps) {
  const [selectedPromptIds, setSelectedPromptIds] = useState<Set<number>>(new Set())

  const { data: topicPromptsData, isLoading, error } = useTopicPrompts(isOpen ? topicId : undefined)
  const addPromptsMutation = useAddPromptsToGroup()

  // Flatten prompts from all topics (typically just one)
  const prompts = useMemo(() => {
    if (!topicPromptsData?.topics) return []
    return topicPromptsData.topics.flatMap((t) => t.prompts)
  }, [topicPromptsData])

  const allSelected = prompts.length > 0 && selectedPromptIds.size === prompts.length
  const noneSelected = selectedPromptIds.size === 0

  const handleTogglePrompt = (promptId: number) => {
    setSelectedPromptIds((prev) => {
      const next = new Set(prev)
      if (next.has(promptId)) {
        next.delete(promptId)
      } else {
        next.add(promptId)
      }
      return next
    })
  }

  const handleSelectAll = () => {
    if (allSelected) {
      setSelectedPromptIds(new Set())
    } else {
      setSelectedPromptIds(new Set(prompts.map((p) => p.id)))
    }
  }

  const handleAddSelected = async () => {
    if (selectedPromptIds.size === 0) return

    try {
      await addPromptsMutation.mutateAsync({
        groupId,
        promptIds: Array.from(selectedPromptIds),
      })
      onClose()
    } catch {
      // Error handled by mutation state
    }
  }

  const handleSkip = () => {
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={handleSkip}
      />

      {/* Modal */}
      <div
        className="relative bg-white rounded-2xl shadow-xl max-w-lg w-full mx-4 overflow-hidden animate-in fade-in zoom-in-95 duration-200"
        style={{ maxHeight: "85vh" }}
      >
        {/* Accent bar */}
        <div className="h-1.5 w-full" style={{ backgroundColor: accentColor }} />

        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Add prompts from topic
              </h2>
              <p className="text-sm text-gray-500 mt-0.5">
                Select prompts to add to "{groupTitle}"
              </p>
            </div>
            <button
              onClick={handleSkip}
              className="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto" style={{ maxHeight: "calc(85vh - 180px)" }}>
          {/* Loading state */}
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <div
                className="w-6 h-6 border-2 rounded-full animate-spin"
                style={{ borderColor: "#e5e7eb", borderTopColor: accentColor }}
              />
              <span className="ml-3 text-sm text-gray-500">Loading prompts...</span>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="p-4 rounded-lg bg-red-50 border border-red-100">
              <p className="text-sm text-red-600">Failed to load prompts from topic</p>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && prompts.length === 0 && (
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-full bg-gray-100 mx-auto mb-3 flex items-center justify-center">
                <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-sm text-gray-500">No prompts found in this topic</p>
              <p className="text-xs text-gray-400 mt-1">You can add prompts manually later</p>
            </div>
          )}

          {/* Prompts list */}
          {!isLoading && !error && prompts.length > 0 && (
            <div className="space-y-3">
              {/* Topic info + Select All */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="px-2.5 py-1 text-xs font-medium rounded-full"
                    style={{ backgroundColor: `${accentColor}15`, color: accentColor }}
                  >
                    {topicTitle}
                  </span>
                  <span className="text-sm text-gray-400">
                    {prompts.length} prompt{prompts.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <button
                  onClick={handleSelectAll}
                  className="text-sm font-medium transition-colors"
                  style={{ color: accentColor }}
                >
                  {allSelected ? "Deselect All" : "Select All"}
                </button>
              </div>

              {/* Prompts */}
              <div className="space-y-2 max-h-80 overflow-y-auto rounded-lg border border-gray-200 divide-y divide-gray-100">
                {prompts.map((prompt) => {
                  const isSelected = selectedPromptIds.has(prompt.id)
                  return (
                    <label
                      key={prompt.id}
                      className={`flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors ${
                        isSelected ? "" : "hover:bg-gray-50"
                      }`}
                      style={{
                        backgroundColor: isSelected ? `${accentColor}08` : undefined,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleTogglePrompt(prompt.id)}
                        className="mt-0.5 rounded"
                        style={{ accentColor }}
                      />
                      <span className="text-sm text-gray-700 flex-1">{prompt.prompt_text}</span>
                    </label>
                  )
                })}
              </div>
            </div>
          )}

          {/* Mutation error */}
          {addPromptsMutation.isError && (
            <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-100">
              <p className="text-sm text-red-600">
                {addPromptsMutation.error?.message || "Failed to add prompts"}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex justify-between">
          <button
            onClick={handleSkip}
            disabled={addPromptsMutation.isPending}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors disabled:opacity-50"
          >
            Skip
          </button>
          <button
            onClick={handleAddSelected}
            disabled={noneSelected || addPromptsMutation.isPending || isLoading}
            className="px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: accentColor }}
          >
            {addPromptsMutation.isPending ? (
              <span className="flex items-center gap-2">
                <div
                  className="w-4 h-4 border-2 rounded-full animate-spin"
                  style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "white" }}
                />
                Adding...
              </span>
            ) : (
              `Add ${selectedPromptIds.size} prompt${selectedPromptIds.size !== 1 ? "s" : ""}`
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
