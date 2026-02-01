/**
 * AddFromGSCModal - Modal for adding GSC-generated prompts to an existing group
 *
 * Similar to AddFromTopicModal but uses GSC integration to generate prompts
 * from search keywords.
 */

import { useState, useCallback } from "react"
import { GSCPromptsStep } from "./shared/GSCPromptsStep"
import { useAddGSCPromptsToGroup } from "@/hooks/useGroups"

interface AddFromGSCModalProps {
  groupId: number
  groupTitle: string
  brandDomain: string | null
  countryId: number
  businessDomain?: string
  accentColor: string
  isOpen: boolean
  onClose: () => void
}

export function AddFromGSCModal({
  groupId,
  groupTitle,
  brandDomain,
  countryId,
  businessDomain,
  accentColor,
  isOpen,
  onClose,
}: AddFromGSCModalProps) {
  const [selectedPrompts, setSelectedPrompts] = useState<Set<string>>(new Set())
  const addGSCPromptsMutation = useAddGSCPromptsToGroup()

  const handleTogglePrompt = useCallback((prompt: string) => {
    setSelectedPrompts((prev) => {
      const next = new Set(prev)
      if (next.has(prompt)) {
        next.delete(prompt)
      } else {
        next.add(prompt)
      }
      return next
    })
  }, [])

  const handleAddSelected = async () => {
    if (selectedPrompts.size === 0) return

    try {
      await addGSCPromptsMutation.mutateAsync({
        groupId,
        prompts: Array.from(selectedPrompts),
      })
      setSelectedPrompts(new Set())
      onClose()
    } catch {
      // Error handled by mutation state
    }
  }

  const handleClose = () => {
    setSelectedPrompts(new Set())
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
                Add from Google Search Console
              </h2>
              <p className="text-sm text-gray-500 mt-0.5">
                Import keywords for "{groupTitle}"
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
          <GSCPromptsStep
            brandDomain={brandDomain}
            countryId={countryId}
            businessDomain={businessDomain}
            selectedPrompts={selectedPrompts}
            onTogglePrompt={handleTogglePrompt}
            accentColor={accentColor}
            redirectUri={window.location.href}
          />

          {/* Mutation error */}
          {addGSCPromptsMutation.isError && (
            <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-100">
              <p className="text-sm text-red-600">
                {addGSCPromptsMutation.error?.message || "Failed to add prompts"}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex justify-between">
          <button
            onClick={handleClose}
            disabled={addGSCPromptsMutation.isPending}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleAddSelected}
            disabled={selectedPrompts.size === 0 || addGSCPromptsMutation.isPending}
            className="px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: accentColor }}
          >
            {addGSCPromptsMutation.isPending ? (
              <span className="flex items-center gap-2">
                <div
                  className="w-4 h-4 border-2 rounded-full animate-spin"
                  style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "white" }}
                />
                Adding...
              </span>
            ) : (
              `Add ${selectedPrompts.size} prompt${selectedPrompts.size !== 1 ? "s" : ""}`
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
