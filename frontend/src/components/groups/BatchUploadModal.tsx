/**
 * BatchUploadModal - Multi-step modal for batch prompt upload with similarity matching
 *
 * 3-step flow:
 * 1. Upload CSV → Analyze for similar prompts
 * 2. Review matches → Select existing or keep as new
 * 3. Create new prompts → Bind all to group
 */

import { useState, useRef, useCallback } from "react"
import { useAnalyzeBatch, useCreateBatchPrompts, useBindPromptsToGroup, parseCSV } from "@/hooks/useBatchUpload"
import type {
  BatchUploadStep,
  BatchAnalyzeResponse,
  BatchPromptAnalysis,
  BatchCreateResponse,
} from "@/types/batch-upload"
import type { AddPromptsResult } from "@/client/api"

// Auto-selection threshold: if similarity >= 98%, auto-select the match
const AUTO_SELECT_THRESHOLD = 0.98

interface PromptSelection {
  index: number
  useExisting: boolean
  selectedPromptId: number | null
}

interface BatchUploadResult {
  createdCount: number
  reusedCount: number
  boundExisting: number
  totalBound: number
}

interface BatchUploadModalProps {
  groupId: number
  groupTitle: string
  accentColor: string
  isOpen: boolean
  onClose: () => void
}

export function BatchUploadModal({
  groupId,
  groupTitle,
  accentColor,
  isOpen,
  onClose,
}: BatchUploadModalProps) {
  const [step, setStep] = useState<BatchUploadStep>("upload")
  const [prompts, setPrompts] = useState<string[]>([])
  const [analysis, setAnalysis] = useState<BatchAnalyzeResponse | null>(null)
  const [visibleItems, setVisibleItems] = useState<BatchPromptAnalysis[]>([])
  const [selections, setSelections] = useState<Map<number, PromptSelection>>(new Map())
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set())
  const [result, setResult] = useState<BatchUploadResult | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [processingError, setProcessingError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const analyzeMutation = useAnalyzeBatch()
  const createMutation = useCreateBatchPrompts()
  const bindMutation = useBindPromptsToGroup()

  // Reset modal state
  const resetState = useCallback(() => {
    setStep("upload")
    setPrompts([])
    setAnalysis(null)
    setVisibleItems([])
    setSelections(new Map())
    setExpandedItems(new Set())
    setResult(null)
    setParseError(null)
    setIsDragging(false)
    setIsProcessing(false)
    setProcessingError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
    analyzeMutation.reset()
    createMutation.reset()
    bindMutation.reset()
  }, [analyzeMutation, createMutation, bindMutation])

  // Toggle expanded state for a prompt card
  const toggleExpanded = (index: number) => {
    setExpandedItems((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  // Handle close with reset
  const handleClose = () => {
    resetState()
    onClose()
  }

  // Handle file selection
  const handleFileSelect = async (file: File) => {
    setParseError(null)

    if (!file.name.endsWith(".csv") && !file.name.endsWith(".txt")) {
      setParseError("Please upload a CSV or TXT file")
      return
    }

    try {
      const content = await file.text()
      const { prompts: parsed, errors } = parseCSV(content)

      if (errors.length > 0) {
        setParseError(errors.join(". "))
        return
      }

      setPrompts(parsed)
    } catch {
      setParseError("Failed to read file")
    }
  }

  // Handle drag & drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileSelect(file)
  }

  // Delete prompt from upload step
  const handleDeletePromptUpload = (index: number) => {
    setPrompts((prev) => prev.filter((_, i) => i !== index))
  }

  // Delete prompt from review step
  const handleDeletePromptReview = (itemIndex: number) => {
    setVisibleItems((prev) => prev.filter((item) => item.index !== itemIndex))
    setSelections((prev) => {
      const next = new Map(prev)
      next.delete(itemIndex)
      return next
    })
  }

  // Handle analyze action
  const handleAnalyze = async () => {
    try {
      const data = await analyzeMutation.mutateAsync(prompts)
      setAnalysis(data)
      setVisibleItems(data.items)

      // Initialize selections with smart auto-selection:
      // - Duplicates (is_duplicate=true) are auto-selected to use existing
      // - If any match has similarity >= 98%, auto-select the highest match
      // - Otherwise, default to "keep original"
      const initialSelections = new Map<number, PromptSelection>()
      data.items.forEach((item) => {
        // Find the highest similarity match
        const highestMatch = item.matches.length > 0
          ? item.matches.reduce((best, current) =>
              current.similarity > best.similarity ? current : best
            )
          : null

        if (item.is_duplicate && highestMatch) {
          // Duplicates are forced to use existing (non-editable)
          initialSelections.set(item.index, {
            index: item.index,
            useExisting: true,
            selectedPromptId: highestMatch.prompt_id,
          })
        } else if (highestMatch && highestMatch.similarity >= AUTO_SELECT_THRESHOLD) {
          // Auto-select high similarity matches
          initialSelections.set(item.index, {
            index: item.index,
            useExisting: true,
            selectedPromptId: highestMatch.prompt_id,
          })
        } else {
          // Default to creating new
          initialSelections.set(item.index, {
            index: item.index,
            useExisting: false,
            selectedPromptId: null,
          })
        }
      })
      setSelections(initialSelections)
      setExpandedItems(new Set()) // All collapsed by default
      setStep("review")
    } catch {
      // Error handled by mutation state
    }
  }

  // Handle selection change
  const handleSelectionChange = (
    index: number,
    useExisting: boolean,
    promptId: number | null
  ) => {
    // Don't allow changing duplicates
    const item = visibleItems.find((i) => i.index === index)
    if (item?.is_duplicate) return

    setSelections((prev) => {
      const next = new Map(prev)
      next.set(index, {
        index,
        useExisting,
        selectedPromptId: promptId,
      })
      return next
    })
  }

  // Handle confirm action - 3 API calls
  const handleConfirm = async () => {
    setIsProcessing(true)
    setProcessingError(null)

    try {
      // Separate into: create new vs use existing
      const indicesToCreate: number[] = []
      const existingPromptIds: number[] = []

      visibleItems.forEach((item) => {
        const selection = selections.get(item.index)
        if (!selection) return

        if (selection.useExisting && selection.selectedPromptId) {
          // Using existing prompt
          existingPromptIds.push(selection.selectedPromptId)
        } else {
          // Creating new (non-duplicate only)
          if (!item.is_duplicate) {
            indicesToCreate.push(item.index)
          }
        }
      })

      let createResult: BatchCreateResponse | null = null
      let bindResult: AddPromptsResult | null = null
      const allPromptIds: number[] = [...existingPromptIds]

      // Step 1: Create new prompts if any (topic is derived from group)
      if (indicesToCreate.length > 0) {
        createResult = await createMutation.mutateAsync({
          prompts,
          selected_indices: indicesToCreate,
          group_id: groupId,
        })
        allPromptIds.push(...createResult.prompt_ids)
      }

      // Step 2: Bind all prompts to group
      if (allPromptIds.length > 0) {
        bindResult = await bindMutation.mutateAsync({
          groupId,
          promptIds: allPromptIds,
        })
      }

      // Build result
      setResult({
        createdCount: createResult?.created_count ?? 0,
        reusedCount: createResult?.reused_count ?? 0,
        boundExisting: existingPromptIds.length,
        totalBound: bindResult?.added_count ?? 0,
      })
      setStep("complete")
    } catch (error) {
      setProcessingError(
        error instanceof Error ? error.message : "Failed to process prompts"
      )
    } finally {
      setIsProcessing(false)
    }
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
        className="relative bg-white rounded-2xl shadow-xl max-w-2xl w-full mx-4 overflow-hidden animate-in fade-in zoom-in-95 duration-200"
        style={{ maxHeight: "85vh" }}
      >
        {/* Accent bar */}
        <div className="h-1.5 w-full" style={{ backgroundColor: accentColor }} />

        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {step === "upload" && "Upload prompts"}
                {step === "review" && "Review matches"}
                {step === "complete" && "Upload complete"}
              </h2>
              <p className="text-sm text-gray-500 mt-0.5">
                {step === "upload" && `Add prompts to "${groupTitle}"`}
                {step === "review" && `${visibleItems.length} prompts to review`}
                {step === "complete" && `Added to "${groupTitle}"`}
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

          {/* Step indicator */}
          <div className="flex items-center gap-2 mt-4">
            {["upload", "review", "complete"].map((s, i) => (
              <div key={s} className="flex items-center">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors ${
                    step === s
                      ? "text-white"
                      : ["upload", "review", "complete"].indexOf(step) > i
                      ? "text-white"
                      : "text-gray-400 bg-gray-100"
                  }`}
                  style={{
                    backgroundColor:
                      step === s || ["upload", "review", "complete"].indexOf(step) > i
                        ? accentColor
                        : undefined,
                  }}
                >
                  {["upload", "review", "complete"].indexOf(step) > i ? (
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    i + 1
                  )}
                </div>
                {i < 2 && (
                  <div
                    className={`w-8 h-0.5 mx-1 transition-colors ${
                      ["upload", "review", "complete"].indexOf(step) > i ? "" : "bg-gray-200"
                    }`}
                    style={{
                      backgroundColor:
                        ["upload", "review", "complete"].indexOf(step) > i ? accentColor : undefined,
                    }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4 overflow-y-auto" style={{ maxHeight: "calc(85vh - 200px)" }}>
          {/* Step 1: Upload */}
          {step === "upload" && (
            <div className="space-y-4">
              {/* Dropzone */}
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                  isDragging ? "border-solid" : ""
                }`}
                style={{
                  borderColor: isDragging ? accentColor : "#e5e7eb",
                  backgroundColor: isDragging ? `${accentColor}08` : "#fafafa",
                }}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.txt"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) handleFileSelect(file)
                    // Reset input value to allow re-selecting the same file
                    e.target.value = ""
                  }}
                />
                <div
                  className="w-12 h-12 rounded-full mx-auto mb-3 flex items-center justify-center"
                  style={{ backgroundColor: `${accentColor}15` }}
                >
                  <svg
                    className="w-6 h-6"
                    style={{ color: accentColor }}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                </div>
                <p className="text-sm font-medium text-gray-700 mb-1">
                  {isDragging ? "Drop your file here" : "Drop CSV file here or click to browse"}
                </p>
                <p className="text-xs text-gray-400">
                  Single column with one prompt per line (max 100)
                </p>
              </div>

              {/* Parse error */}
              {parseError && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-100">
                  <p className="text-sm text-red-600">{parseError}</p>
                </div>
              )}

              {/* Parsed prompts list with delete buttons */}
              {prompts.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-gray-700">
                    {prompts.length} prompt{prompts.length !== 1 ? "s" : ""} ready
                  </p>
                  <div className="max-h-60 overflow-y-auto rounded-lg border border-gray-200 divide-y divide-gray-100">
                    {prompts.map((prompt, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 px-3 py-2 group hover:bg-gray-50"
                      >
                        <p className="flex-1 text-sm text-gray-600 truncate">{prompt}</p>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeletePromptUpload(i)
                          }}
                          className="p-1 rounded text-gray-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover:opacity-100"
                          title="Remove prompt"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Review */}
          {step === "review" && analysis && (
            <div className="space-y-4">
              {/* Stats */}
              {(() => {
                // Count stats
                const duplicates = visibleItems.filter((item) => item.is_duplicate).length
                const usingExisting = visibleItems.filter((item) => {
                  const sel = selections.get(item.index)
                  return sel?.useExisting && !item.is_duplicate
                }).length
                const addingNew = visibleItems.filter((item) => {
                  const sel = selections.get(item.index)
                  return !sel?.useExisting && !item.is_duplicate
                }).length

                return (
                  <div className="flex gap-3">
                    {duplicates > 0 && (
                      <div className="flex-1 p-3 rounded-lg bg-amber-50">
                        <p className="text-2xl font-semibold text-amber-600">
                          {duplicates}
                        </p>
                        <p className="text-xs text-gray-500">duplicates</p>
                      </div>
                    )}
                    <div
                      className="flex-1 p-3 rounded-lg"
                      style={{ backgroundColor: `${accentColor}08` }}
                    >
                      <p className="text-2xl font-semibold" style={{ color: accentColor }}>
                        {usingExisting}
                      </p>
                      <p className="text-xs text-gray-500">using matches</p>
                    </div>
                    <div className="flex-1 p-3 rounded-lg bg-gray-50">
                      <p className="text-2xl font-semibold text-gray-900">
                        {addingNew}
                      </p>
                      <p className="text-xs text-gray-500">adding as new</p>
                    </div>
                  </div>
                )
              })()}

              {/* Empty state */}
              {visibleItems.length === 0 && (
                <div className="text-center py-8 text-gray-400">
                  <p>All prompts have been removed.</p>
                  <button
                    onClick={() => setStep("upload")}
                    className="mt-2 text-sm underline hover:text-gray-600"
                  >
                    Go back to upload
                  </button>
                </div>
              )}

              {/* Prompts list - collapsible cards */}
              <div className="space-y-2">
                {visibleItems.map((item) => {
                  const selection = selections.get(item.index)
                  const isExpanded = expandedItems.has(item.index)
                  const isDuplicate = item.is_duplicate

                  // Determine what's currently selected for the collapsed state indicator
                  const selectedMatch = selection?.useExisting
                    ? item.matches.find((m) => m.prompt_id === selection.selectedPromptId)
                    : null
                  const selectionLabel = isDuplicate
                    ? "Duplicate"
                    : selectedMatch
                    ? `Match ${Math.round(selectedMatch.similarity * 100)}%`
                    : "New"

                  return (
                    <div
                      key={item.index}
                      className={`rounded-xl border overflow-hidden transition-all duration-200 group ${
                        isDuplicate ? "border-amber-200 bg-amber-50/50" : "border-gray-200"
                      }`}
                      style={{
                        boxShadow: isExpanded ? "0 4px 12px rgba(0,0,0,0.08)" : undefined,
                      }}
                    >
                      {/* Collapsed header - always visible */}
                      <div
                        className={`flex items-center gap-3 px-4 py-3 select-none transition-colors ${
                          isDuplicate
                            ? "cursor-default"
                            : "cursor-pointer hover:bg-gray-50"
                        }`}
                        onClick={() => !isDuplicate && toggleExpanded(item.index)}
                      >
                        {/* Expand/collapse chevron */}
                        {!isDuplicate && (
                          <svg
                            className="w-4 h-4 text-gray-400 transition-transform duration-200 flex-shrink-0"
                            style={{ transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)" }}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        )}
                        {isDuplicate && (
                          <svg className="w-4 h-4 text-amber-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                        )}

                        {/* Prompt text */}
                        <p className={`flex-1 text-sm truncate min-w-0 ${
                          isDuplicate ? "text-gray-500 line-through" : "text-gray-700"
                        }`}>
                          {item.input_text}
                        </p>

                        {/* Selection indicator badge */}
                        <span
                          className={`text-[11px] font-medium px-2 py-1 rounded-full whitespace-nowrap flex-shrink-0 transition-colors ${
                            isDuplicate
                              ? "bg-amber-100 text-amber-700"
                              : ""
                          }`}
                          style={!isDuplicate ? {
                            backgroundColor: selectedMatch ? `${accentColor}15` : "#f3f4f6",
                            color: selectedMatch ? accentColor : "#6b7280",
                          } : undefined}
                        >
                          {selectionLabel}
                        </span>

                        {/* Delete button - only for non-duplicates */}
                        {!isDuplicate && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDeletePromptReview(item.index)
                            }}
                            className="p-1.5 rounded-lg text-gray-300 hover:text-red-500 hover:bg-red-50 transition-all opacity-0 group-hover:opacity-100 flex-shrink-0"
                            title="Remove prompt"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        )}
                      </div>

                      {/* Expanded content - only for non-duplicates */}
                      {!isDuplicate && (
                        <div
                          className="overflow-hidden transition-all duration-200"
                          style={{
                            maxHeight: isExpanded ? "500px" : "0px",
                            opacity: isExpanded ? 1 : 0,
                          }}
                        >
                          <div className="px-4 pb-4 pt-1 space-y-2 border-t border-gray-100">
                            {/* Keep original option */}
                            <label
                              className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                                !selection?.useExisting
                                  ? "ring-2"
                                  : "hover:bg-gray-50"
                              }`}
                              style={{
                                backgroundColor: !selection?.useExisting ? `${accentColor}08` : undefined,
                                ["--tw-ring-color" as string]: !selection?.useExisting ? accentColor : undefined,
                              }}
                            >
                              <input
                                type="radio"
                                name={`selection-${item.index}`}
                                checked={!selection?.useExisting}
                                onChange={() => handleSelectionChange(item.index, false, null)}
                                className="mt-0.5"
                                style={{ accentColor }}
                              />
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-700">
                                  Keep original (add as new)
                                </p>
                                <p className="text-xs text-gray-400 mt-0.5">
                                  Will be added to evaluation queue
                                </p>
                              </div>
                            </label>

                            {/* Match options */}
                            {item.matches.map((match) => {
                              const isSelected = selection?.useExisting && selection.selectedPromptId === match.prompt_id
                              return (
                                <label
                                  key={match.prompt_id}
                                  className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-all ${
                                    isSelected
                                      ? "ring-2"
                                      : "hover:bg-gray-50"
                                  }`}
                                  style={{
                                    backgroundColor: isSelected ? `${accentColor}08` : undefined,
                                    ["--tw-ring-color" as string]: isSelected ? accentColor : undefined,
                                  }}
                                >
                                  <input
                                    type="radio"
                                    name={`selection-${item.index}`}
                                    checked={isSelected}
                                    onChange={() => handleSelectionChange(item.index, true, match.prompt_id)}
                                    className="mt-0.5"
                                    style={{ accentColor }}
                                  />
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                      <p className="text-sm text-gray-700">{match.prompt_text}</p>
                                      <span
                                        className="text-[10px] font-medium px-1.5 py-0.5 rounded-full whitespace-nowrap"
                                        style={{
                                          backgroundColor: `${accentColor}15`,
                                          color: accentColor,
                                        }}
                                      >
                                        {Math.round(match.similarity * 100)}%
                                      </span>
                                    </div>
                                    <p className="text-xs text-gray-400 mt-0.5">Use existing prompt</p>
                                  </div>
                                </label>
                              )
                            })}

                            {/* No matches indicator */}
                            {item.matches.length === 0 && (
                              <div className="px-3 py-2 text-xs text-gray-400 italic">
                                No similar prompts found in database
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Step 3: Complete */}
          {step === "complete" && result && (
            <div className="text-center py-6">
              <div
                className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center"
                style={{ backgroundColor: `${accentColor}15` }}
              >
                <svg
                  className="w-8 h-8"
                  style={{ color: accentColor }}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Successfully added {result.totalBound} prompts
              </h3>
              <div className="space-y-1 text-sm text-gray-500">
                {result.boundExisting > 0 && (
                  <p>{result.boundExisting} existing prompts linked</p>
                )}
                {result.createdCount > 0 && (
                  <p>{result.createdCount} new prompts created</p>
                )}
                {result.reusedCount > 0 && (
                  <p>{result.reusedCount} duplicates reused</p>
                )}
              </div>
            </div>
          )}

          {/* Errors */}
          {(analyzeMutation.isError || processingError) && (
            <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-100">
              <p className="text-sm text-red-600">
                {analyzeMutation.error?.message || processingError || "An error occurred"}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex justify-end gap-3">
          {step === "upload" && (
            <>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAnalyze}
                disabled={prompts.length === 0 || analyzeMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ backgroundColor: accentColor }}
              >
                {analyzeMutation.isPending ? (
                  <span className="flex items-center gap-2">
                    <div
                      className="w-4 h-4 border-2 rounded-full animate-spin"
                      style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "white" }}
                    />
                    Analyzing...
                  </span>
                ) : (
                  "Analyze"
                )}
              </button>
            </>
          )}

          {step === "review" && (
            <>
              <button
                onClick={() => setStep("upload")}
                disabled={isProcessing}
                className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors disabled:opacity-50"
              >
                Back
              </button>
              <button
                onClick={handleConfirm}
                disabled={isProcessing || visibleItems.length === 0}
                className="px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ backgroundColor: accentColor }}
              >
                {isProcessing ? (
                  <span className="flex items-center gap-2">
                    <div
                      className="w-4 h-4 border-2 rounded-full animate-spin"
                      style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "white" }}
                    />
                    Adding...
                  </span>
                ) : (
                  `Add ${visibleItems.reduce((count, item) => {
                    const selection = selections.get(item.index)
                    if (!selection) return count
                    // Count existing prompts being linked (including duplicates)
                    if (selection.useExisting && selection.selectedPromptId) {
                      return count + 1
                    }
                    // Count new prompts being created (non-duplicates only)
                    if (!item.is_duplicate) {
                      return count + 1
                    }
                    return count
                  }, 0)} to Group`
                )}
              </button>
            </>
          )}

          {step === "complete" && (
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors"
              style={{ backgroundColor: accentColor }}
            >
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
