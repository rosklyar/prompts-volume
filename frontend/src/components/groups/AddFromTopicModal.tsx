/**
 * AddFromTopicModal - Modal for adding prompts from the group's bound topic
 *
 * Shows prompts from the topic that aren't already in the group.
 * Allows multi-select with Select All/Deselect All functionality.
 */

import { useState, useMemo } from "react"
import { useAvailablePrompts, useAddPromptsToGroup } from "@/hooks/useGroups"

interface AddFromTopicModalProps {
  groupId: number
  groupTitle: string
  accentColor: string
  isOpen: boolean
  onClose: () => void
}

export function AddFromTopicModal({
  groupId,
  groupTitle,
  accentColor,
  isOpen,
  onClose,
}: AddFromTopicModalProps) {
  const [selectedPromptIds, setSelectedPromptIds] = useState<Set<number>>(new Set())

  const { data: availablePromptsData, isLoading, error } = useAvailablePrompts(isOpen ? groupId : undefined)
  const addPromptsMutation = useAddPromptsToGroup()

  const prompts = useMemo(() => {
    return availablePromptsData?.prompts ?? []
  }, [availablePromptsData])

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
      setSelectedPromptIds(new Set())
      onClose()
    } catch {
      // Error handled by mutation state
    }
  }

  const handleClose = () => {
    setSelectedPromptIds(new Set())
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={handleClose}
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
                Add more prompts from topic
              </h2>
              <p className="text-sm text-gray-500 mt-0.5">
                Select prompts to add to "{groupTitle}"
              </p>
            </div>
            <button
              onClick={handleClose}
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
              <p className="text-sm text-red-600">Failed to load available prompts</p>
            </div>
          )}

          {/* All prompts added state */}
          {!isLoading && !error && prompts.length === 0 && (
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-full bg-green-100 mx-auto mb-3 flex items-center justify-center">
                <svg className="w-6 h-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-sm font-medium text-gray-700">All prompts added</p>
              <p className="text-xs text-gray-400 mt-1">
                All prompts from this topic are already in the group
              </p>
            </div>
          )}

          {/* Prompts list */}
          {!isLoading && !error && prompts.length > 0 && (
            <div className="space-y-3">
              {/* Header with count and Select All */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">
                  {prompts.length} available prompt{prompts.length !== 1 ? "s" : ""}
                </span>
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
            onClick={handleClose}
            disabled={addPromptsMutation.isPending}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors disabled:opacity-50"
          >
            {prompts.length === 0 ? "Close" : "Cancel"}
          </button>
          {prompts.length > 0 && (
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
          )}
        </div>
      </div>
    </div>
  )
}
