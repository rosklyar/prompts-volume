/**
 * PromptSelectionModal - Modal for reviewing and selecting prompts after group creation
 * Opens immediately after a group is created, allowing users to add prompts from the bound topic
 */

import { useState, useEffect, useCallback } from "react"
import { createPortal } from "react-dom"
import {
  X,
  Check,
  CheckSquare,
  Square,
  Loader2,
  Sparkles,
  FolderPlus,
  SkipForward,
} from "lucide-react"
import {
  useLoadTopicPrompts,
  useAddPromptsToGroupFromInspiration,
} from "@/hooks/useInspiration"

interface PromptSelectionModalProps {
  isOpen: boolean
  groupId: number
  groupTitle: string
  topicId: number
  topicTitle: string
  onClose: () => void
  onSuccess: () => void
}

interface PromptItem {
  id: number
  text: string
  isSelected: boolean
}

const ACCENT_COLOR = "#C4553D"

export function PromptSelectionModal({
  isOpen,
  groupId,
  groupTitle,
  topicId,
  topicTitle,
  onClose,
  onSuccess,
}: PromptSelectionModalProps) {
  const [prompts, setPrompts] = useState<PromptItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadTopicPrompts = useLoadTopicPrompts()
  const addPromptsToGroup = useAddPromptsToGroupFromInspiration()

  // Derived state
  const selectedPrompts = prompts.filter((p) => p.isSelected)
  const selectedCount = selectedPrompts.length
  const allSelected = prompts.length > 0 && selectedCount === prompts.length
  const hasSelections = selectedCount > 0

  // Load prompts when modal opens
  useEffect(() => {
    if (isOpen && topicId) {
      loadPrompts()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, topicId])

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose()
      }
    }
    document.addEventListener("keydown", handleEscape)
    return () => document.removeEventListener("keydown", handleEscape)
  }, [isOpen, onClose])

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden"
    } else {
      document.body.style.overflow = ""
    }
    return () => {
      document.body.style.overflow = ""
    }
  }, [isOpen])

  const loadPrompts = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await loadTopicPrompts.mutateAsync([topicId])
      const topicData = response.topics.find((t) => t.topic_id === topicId)
      const promptList: PromptItem[] =
        topicData?.prompts.map((p) => ({
          id: p.id,
          text: p.prompt_text,
          isSelected: false,
        })) ?? []
      setPrompts(promptList)
    } catch {
      setError("Failed to load prompts. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }, [topicId, loadTopicPrompts])

  const handleTogglePrompt = (promptId: number) => {
    setPrompts((prev) =>
      prev.map((p) =>
        p.id === promptId ? { ...p, isSelected: !p.isSelected } : p
      )
    )
  }

  const handleSelectAll = () => {
    setPrompts((prev) => prev.map((p) => ({ ...p, isSelected: true })))
  }

  const handleDeselectAll = () => {
    setPrompts((prev) => prev.map((p) => ({ ...p, isSelected: false })))
  }

  const handleAddSelected = async () => {
    if (selectedCount === 0) return

    try {
      await addPromptsToGroup.mutateAsync({
        groupId,
        promptIds: selectedPrompts.map((p) => p.id),
      })
      onSuccess()
    } catch {
      setError("Failed to add prompts. Please try again.")
    }
  }

  const handleSkip = () => {
    onClose()
  }

  if (!isOpen) return null

  const modalContent = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200"
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className="relative w-full max-w-xl bg-white rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 fade-in duration-300"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Accent bar */}
        <div
          className="h-1.5 w-full"
          style={{ backgroundColor: ACCENT_COLOR }}
        />

        {/* Header */}
        <div className="px-6 pt-5 pb-4 border-b border-gray-100">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Sparkles
                  className="w-4 h-4 flex-shrink-0"
                  style={{ color: ACCENT_COLOR }}
                />
                <span className="text-xs uppercase tracking-widest text-gray-400 font-['DM_Sans']">
                  Add prompts to group
                </span>
              </div>
              <h2
                id="modal-title"
                className="font-['Fraunces'] text-xl font-semibold text-gray-900 truncate"
              >
                {groupTitle}
              </h2>
              <p className="text-sm text-gray-500 font-['DM_Sans'] mt-1">
                Select prompts from{" "}
                <span className="font-medium" style={{ color: ACCENT_COLOR }}>
                  {topicTitle}
                </span>
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-full hover:bg-gray-100 transition-colors -mr-2 -mt-1"
              aria-label="Close modal"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="max-h-[400px] overflow-y-auto">
          {/* Loading state */}
          {isLoading && (
            <div className="px-6 py-12 text-center">
              <Loader2
                className="w-8 h-8 animate-spin mx-auto mb-3"
                style={{ color: ACCENT_COLOR }}
              />
              <p className="text-sm text-gray-500 font-['DM_Sans']">
                Loading prompts...
              </p>
            </div>
          )}

          {/* Error state */}
          {!isLoading && error && (
            <div className="px-6 py-12 text-center">
              <p className="text-sm text-red-600 font-['DM_Sans'] mb-3">
                {error}
              </p>
              <button
                onClick={loadPrompts}
                className="text-sm font-medium px-4 py-2 rounded-lg transition-colors"
                style={{ color: ACCENT_COLOR }}
              >
                Try again
              </button>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && prompts.length === 0 && (
            <div className="px-6 py-12 text-center">
              <div
                className="w-12 h-12 rounded-full mx-auto mb-4 flex items-center justify-center"
                style={{ backgroundColor: `${ACCENT_COLOR}10` }}
              >
                <FolderPlus
                  className="w-6 h-6"
                  style={{ color: ACCENT_COLOR }}
                />
              </div>
              <p className="text-sm text-gray-500 font-['DM_Sans']">
                No prompts available for this topic yet.
              </p>
              <p className="text-xs text-gray-400 font-['DM_Sans'] mt-1">
                You can add prompts manually later.
              </p>
            </div>
          )}

          {/* Prompts list */}
          {!isLoading && !error && prompts.length > 0 && (
            <>
              {/* Bulk actions bar */}
              <div
                className="px-6 py-3 flex items-center justify-between border-b border-gray-100 sticky top-0 bg-white z-10"
                style={{ backgroundColor: `${ACCENT_COLOR}05` }}
              >
                <button
                  onClick={allSelected ? handleDeselectAll : handleSelectAll}
                  className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 font-['DM_Sans'] transition-colors"
                >
                  {allSelected ? (
                    <>
                      <CheckSquare
                        className="w-4 h-4"
                        style={{ color: ACCENT_COLOR }}
                      />
                      <span>Deselect all</span>
                    </>
                  ) : (
                    <>
                      <Square className="w-4 h-4" />
                      <span>Select all</span>
                    </>
                  )}
                </button>

                {hasSelections && (
                  <span
                    className="px-3 py-1 rounded-full text-xs font-medium font-['DM_Sans']"
                    style={{
                      backgroundColor: `${ACCENT_COLOR}15`,
                      color: ACCENT_COLOR,
                    }}
                  >
                    {selectedCount} selected
                  </span>
                )}
              </div>

              {/* Prompt items */}
              <div className="divide-y divide-gray-100">
                {prompts.map((prompt) => (
                  <label
                    key={prompt.id}
                    className="flex items-start gap-3 px-6 py-3.5 cursor-pointer transition-colors hover:bg-gray-50"
                  >
                    <div className="mt-0.5 flex-shrink-0">
                      <input
                        type="checkbox"
                        checked={prompt.isSelected}
                        onChange={() => handleTogglePrompt(prompt.id)}
                        className="sr-only"
                      />
                      <div
                        className="w-5 h-5 rounded border-2 flex items-center justify-center transition-all duration-150"
                        style={{
                          borderColor: prompt.isSelected
                            ? ACCENT_COLOR
                            : "#D1D5DB",
                          backgroundColor: prompt.isSelected
                            ? ACCENT_COLOR
                            : "transparent",
                        }}
                      >
                        {prompt.isSelected && (
                          <Check
                            className="w-3 h-3 text-white"
                            strokeWidth={3}
                          />
                        )}
                      </div>
                    </div>
                    <span
                      className={`text-sm font-['DM_Sans'] leading-relaxed transition-colors ${
                        prompt.isSelected ? "text-gray-900" : "text-gray-600"
                      }`}
                    >
                      {prompt.text}
                    </span>
                  </label>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50/50 flex items-center justify-between gap-4">
          <button
            onClick={handleSkip}
            disabled={addPromptsToGroup.isPending}
            className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 font-['DM_Sans']"
          >
            <SkipForward className="w-4 h-4" />
            Skip for now
          </button>

          <button
            onClick={handleAddSelected}
            disabled={selectedCount === 0 || addPromptsToGroup.isPending}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed font-['DM_Sans']"
            style={{
              backgroundColor: ACCENT_COLOR,
              boxShadow:
                selectedCount > 0 ? `0 4px 12px ${ACCENT_COLOR}40` : "none",
            }}
          >
            {addPromptsToGroup.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Adding...
              </>
            ) : (
              <>
                <FolderPlus className="w-4 h-4" />
                Add {selectedCount > 0 ? selectedCount : ""} prompt
                {selectedCount !== 1 ? "s" : ""}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )

  return createPortal(modalContent, document.body)
}
