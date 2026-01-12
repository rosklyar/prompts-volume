/**
 * AssistantSelectionModal - Small popup to select AI Assistant before generating report
 */

import { useState } from "react"
import { useAssistants } from "@/hooks/useAssistants"

interface AssistantSelectionModalProps {
  isOpen: boolean
  accentColor: string
  onClose: () => void
  onSelect: (assistantId: number) => void
}

export function AssistantSelectionModal({
  isOpen,
  accentColor,
  onClose,
  onSelect,
}: AssistantSelectionModalProps) {
  const { data: assistantsData, isLoading } = useAssistants()
  const [selectedId, setSelectedId] = useState<number>(1) // Default to ChatGPT (id=1)

  if (!isOpen) return null

  const handleContinue = () => {
    onSelect(selectedId)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="
          relative w-full max-w-xs mx-4 bg-white rounded-xl shadow-2xl overflow-hidden
          animate-in fade-in slide-in-from-bottom-4 duration-300
        "
      >
        {/* Header accent bar */}
        <div className="h-1 w-full" style={{ backgroundColor: accentColor }} />

        {/* Content */}
        <div className="p-5">
          <h3 className="text-lg font-medium text-gray-900 mb-4 font-['DM_Sans']">
            Select AI Assistant
          </h3>

          {isLoading ? (
            <div className="py-4 text-center">
              <div
                className="w-6 h-6 border-2 rounded-full animate-spin mx-auto"
                style={{
                  borderColor: `${accentColor}30`,
                  borderTopColor: accentColor,
                }}
              />
            </div>
          ) : (
            <div className="space-y-2">
              {assistantsData?.assistants.map((assistant) => (
                <label
                  key={assistant.id}
                  className={`
                    flex items-center gap-3 p-3 rounded-lg cursor-pointer
                    border transition-colors
                    ${selectedId === assistant.id
                      ? "border-gray-300 bg-gray-50"
                      : "border-gray-100 hover:border-gray-200 bg-white"
                    }
                  `}
                >
                  <div
                    className={`
                      w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0
                      ${selectedId === assistant.id ? "border-gray-600" : "border-gray-300"}
                    `}
                  >
                    {selectedId === assistant.id && (
                      <div className="w-2 h-2 rounded-full bg-gray-600" />
                    )}
                  </div>
                  <input
                    type="radio"
                    name="assistant"
                    value={assistant.id}
                    checked={selectedId === assistant.id}
                    onChange={() => setSelectedId(assistant.id)}
                    className="sr-only"
                  />
                  <span className="text-sm text-gray-700 font-['DM_Sans']">
                    {assistant.name}
                  </span>
                </label>
              ))}
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-3 mt-5">
            <button
              onClick={onClose}
              className="
                flex-1 py-2.5 px-4 rounded-lg text-sm font-medium
                text-gray-600 bg-gray-100 hover:bg-gray-200
                transition-colors font-['DM_Sans']
              "
            >
              Cancel
            </button>
            <button
              onClick={handleContinue}
              disabled={isLoading || !assistantsData?.assistants.length}
              className="
                flex-1 py-2.5 px-4 rounded-lg text-sm font-medium
                text-white transition-colors font-['DM_Sans']
                disabled:opacity-50 disabled:cursor-not-allowed
              "
              style={{ backgroundColor: accentColor }}
            >
              Continue
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
