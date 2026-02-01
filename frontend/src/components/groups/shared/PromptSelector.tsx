/**
 * PromptSelector - Reusable prompt checkbox list component
 *
 * Used for selecting prompts from a list with select-all/deselect-all functionality.
 * Supports both numeric IDs (for topic prompts) and string IDs (for GSC prompts).
 */

interface Prompt {
  id: number | string
  text: string
  subtitle?: string
}

interface PromptSelectorProps {
  prompts: Prompt[]
  selectedIds: Set<number | string>
  onToggle: (id: number | string) => void
  onSelectAll: () => void
  accentColor?: string
  isLoading?: boolean
  emptyMessage?: string
  emptySubtitle?: string
  maxHeight?: string
}

export function PromptSelector({
  prompts,
  selectedIds,
  onToggle,
  onSelectAll,
  accentColor = "#C4553D",
  isLoading = false,
  emptyMessage = "No prompts available",
  emptySubtitle,
  maxHeight = "320px",
}: PromptSelectorProps) {
  const allSelected = prompts.length > 0 && selectedIds.size === prompts.length

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div
          className="w-6 h-6 border-2 rounded-full animate-spin"
          style={{ borderColor: "#e5e7eb", borderTopColor: accentColor }}
        />
        <span className="ml-3 text-sm text-gray-500">Loading prompts...</span>
      </div>
    )
  }

  if (prompts.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="w-12 h-12 rounded-full bg-gray-100 mx-auto mb-3 flex items-center justify-center">
          <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-700">{emptyMessage}</p>
        {emptySubtitle && (
          <p className="text-xs text-gray-400 mt-1">{emptySubtitle}</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header with count and Select All */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">
          {prompts.length} prompt{prompts.length !== 1 ? "s" : ""} available
        </span>
        <button
          onClick={onSelectAll}
          className="text-sm font-medium transition-colors"
          style={{ color: accentColor }}
        >
          {allSelected ? "Deselect All" : "Select All"}
        </button>
      </div>

      {/* Prompts list */}
      <div
        className="overflow-y-auto rounded-lg border border-gray-200 divide-y divide-gray-100"
        style={{ maxHeight }}
      >
        {prompts.map((prompt) => {
          const isSelected = selectedIds.has(prompt.id)
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
                onChange={() => onToggle(prompt.id)}
                className="mt-0.5 rounded"
                style={{ accentColor }}
              />
              <div className="flex-1 min-w-0">
                <span className="text-sm text-gray-700">{prompt.text}</span>
                {prompt.subtitle && (
                  <p className="text-xs text-gray-400 mt-0.5">{prompt.subtitle}</p>
                )}
              </div>
            </label>
          )
        })}
      </div>

      {/* Selection count */}
      <p className="text-sm text-gray-500">
        {selectedIds.size} prompt{selectedIds.size !== 1 ? "s" : ""} selected
      </p>
    </div>
  )
}
