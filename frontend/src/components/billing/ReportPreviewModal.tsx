/**
 * ReportPreviewModal - Selection-based report preview with per-prompt evaluation choices
 * Editorial/refined aesthetic matching the existing app design
 */

import { useState, useEffect, useMemo, useCallback } from "react"
import { useReportComparison } from "@/hooks/useReports"
import { formatCredits } from "@/hooks/useBilling"
import type {
  PromptSelectionInfo,
  EvaluationOption,
  PromptSelection,
} from "@/types/billing"

interface ReportPreviewModalProps {
  groupId: number
  groupTitle: string
  accentColor: string
  isOpen: boolean
  onClose: () => void
  onConfirm: (selections: PromptSelection[]) => void
  onNeedsTopUp?: (estimatedCost: number) => void
}

// Format short datetime for compact display
function formatShortDate(isoString: string): string {
  const date = new Date(isoString)
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

// Evaluation option dropdown item
function EvaluationOptionItem({
  option,
  accentColor,
}: {
  option: EvaluationOption
  accentColor: string
}) {
  return (
    <div className="flex items-center justify-between gap-2 w-full">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-sm font-['DM_Sans'] truncate">
          {option.assistant_name} {option.assistant_plan_name}
        </span>
        <span className="text-xs text-gray-400 font-['DM_Sans'] shrink-0">
          {formatShortDate(option.completed_at)}
        </span>
      </div>
      {option.is_fresh ? (
        <span
          className="text-[10px] font-medium px-1.5 py-0.5 rounded font-['DM_Sans'] shrink-0"
          style={{ backgroundColor: `${accentColor}15`, color: accentColor }}
        >
          ${formatCredits(option.unit_price)}
        </span>
      ) : (
        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-green-50 text-green-600 font-['DM_Sans'] shrink-0">
          FREE
        </span>
      )}
    </div>
  )
}

// Per-prompt selection card
function PromptSelectionCard({
  promptInfo,
  selectedEvaluationId,
  onSelectionChange,
  accentColor,
}: {
  promptInfo: PromptSelectionInfo
  selectedEvaluationId: number | null
  onSelectionChange: (promptId: number, evaluationId: number | null) => void
  accentColor: string
}) {
  const [isExpanded, setIsExpanded] = useState(false)

  const hasOptions = promptInfo.available_options.length > 0
  const selectedOption = promptInfo.available_options.find(
    (o) => o.evaluation_id === selectedEvaluationId
  )
  const isSkipped = selectedEvaluationId === null && hasOptions

  // Determine status
  let statusBadge = null
  if (!hasOptions) {
    if (promptInfo.has_in_progress_evaluation) {
      statusBadge = (
        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 font-['DM_Sans']">
          In progress
        </span>
      )
    } else {
      statusBadge = (
        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 font-['DM_Sans']">
          Awaiting
        </span>
      )
    }
  } else if (isSkipped) {
    statusBadge = (
      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-gray-100 text-gray-400 font-['DM_Sans']">
        Skipped
      </span>
    )
  } else if (selectedOption?.is_fresh) {
    statusBadge = (
      <span
        className="text-[10px] font-medium px-1.5 py-0.5 rounded font-['DM_Sans']"
        style={{ backgroundColor: `${accentColor}15`, color: accentColor }}
      >
        ${formatCredits(selectedOption.unit_price)}
      </span>
    )
  } else {
    statusBadge = (
      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-green-50 text-green-600 font-['DM_Sans']">
        FREE
      </span>
    )
  }

  return (
    <div
      className={`
        rounded-lg border transition-all duration-200
        ${isSkipped ? "bg-gray-50/50 border-gray-200" : "bg-white border-gray-200 hover:border-gray-300"}
      `}
    >
      {/* Header row */}
      <div className="px-3 py-2.5 flex items-start justify-between gap-3">
        {/* Prompt text */}
        <div className="flex-1 min-w-0">
          <p
            className={`text-sm font-['DM_Sans'] line-clamp-2 ${isSkipped ? "text-gray-400" : "text-gray-700"}`}
          >
            {promptInfo.prompt_text}
          </p>
        </div>

        {/* Status badge */}
        <div className="flex items-center gap-2 shrink-0">
          {statusBadge}
        </div>
      </div>

      {/* Selection controls - only show if has options */}
      {hasOptions && (
        <div className="px-3 pb-2.5 pt-0">
          {/* Compact dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className={`
                w-full flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-md text-left
                border transition-colors text-sm font-['DM_Sans']
                ${isExpanded ? "border-gray-300 bg-gray-50" : "border-gray-200 hover:border-gray-300 bg-gray-50/50"}
              `}
            >
              <span className={`truncate ${isSkipped ? "text-gray-400 italic" : "text-gray-700"}`}>
                {isSkipped
                  ? "Skip this prompt"
                  : selectedOption
                    ? `${selectedOption.assistant_name} ${selectedOption.assistant_plan_name} — ${formatShortDate(selectedOption.completed_at)}`
                    : "Select evaluation..."}
              </span>
              <svg
                className={`w-4 h-4 text-gray-400 transition-transform duration-200 shrink-0 ${isExpanded ? "rotate-180" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Dropdown options */}
            {isExpanded && (
              <div className="absolute z-20 mt-1 w-full bg-white rounded-lg border border-gray-200 shadow-lg overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
                {/* Skip option */}
                <button
                  onClick={() => {
                    onSelectionChange(promptInfo.prompt_id, null)
                    setIsExpanded(false)
                  }}
                  className={`
                    w-full px-3 py-2 text-left hover:bg-gray-50 transition-colors
                    flex items-center justify-between
                    ${isSkipped ? "bg-gray-50" : ""}
                  `}
                >
                  <span className="text-sm text-gray-500 font-['DM_Sans'] italic">
                    Skip this prompt
                  </span>
                  {isSkipped && (
                    <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </button>

                {/* Evaluation options */}
                {promptInfo.available_options.map((option) => (
                  <button
                    key={option.evaluation_id}
                    onClick={() => {
                      onSelectionChange(promptInfo.prompt_id, option.evaluation_id)
                      setIsExpanded(false)
                    }}
                    className={`
                      w-full px-3 py-2 text-left hover:bg-gray-50 transition-colors border-t border-gray-100
                      ${selectedEvaluationId === option.evaluation_id ? "bg-gray-50" : ""}
                    `}
                  >
                    <EvaluationOptionItem
                      option={option}
                      accentColor={accentColor}
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export function ReportPreviewModal({
  groupId,
  groupTitle,
  accentColor,
  isOpen,
  onClose,
  onConfirm,
  onNeedsTopUp,
}: ReportPreviewModalProps) {
  const { data: comparison, isLoading, isError, refetch } = useReportComparison(groupId, isOpen)

  // Track user selections: promptId -> evaluationId (null means skip)
  const [selections, setSelections] = useState<Map<number, number | null>>(new Map())

  // Initialize selections from default values when comparison loads
  useEffect(() => {
    if (comparison?.prompt_selections) {
      const initialSelections = new Map<number, number | null>()
      comparison.prompt_selections.forEach((ps) => {
        initialSelections.set(ps.prompt_id, ps.default_selection)
      })
      setSelections(initialSelections)
    }
  }, [comparison])

  // Refetch when modal opens
  useEffect(() => {
    if (isOpen) {
      refetch()
    }
  }, [isOpen, refetch])

  // Handle selection change
  const handleSelectionChange = useCallback((promptId: number, evaluationId: number | null) => {
    setSelections((prev) => {
      const next = new Map(prev)
      next.set(promptId, evaluationId)
      return next
    })
  }, [])

  // Calculate cost based on current selections
  const { selectedCount, freshCount, estimatedCost, canAfford, needsTopUp } = useMemo(() => {
    if (!comparison) {
      return { selectedCount: 0, freshCount: 0, estimatedCost: 0, canAfford: true, needsTopUp: false }
    }

    let selected = 0
    let fresh = 0
    let cost = 0
    const pricePerEval = parseFloat(comparison.price_per_evaluation)

    comparison.prompt_selections.forEach((ps) => {
      const evalId = selections.get(ps.prompt_id)
      if (evalId !== null && evalId !== undefined) {
        selected++
        const option = ps.available_options.find((o) => o.evaluation_id === evalId)
        if (option?.is_fresh) {
          fresh++
          cost += pricePerEval
        }
      }
    })

    const balance = parseFloat(comparison.user_balance)
    return {
      selectedCount: selected,
      freshCount: fresh,
      estimatedCost: cost,
      canAfford: balance >= cost,
      needsTopUp: cost > 0 && balance < cost,
    }
  }, [comparison, selections])

  // Determine if we can generate
  const canGenerate = useMemo(() => {
    if (!comparison) return false
    // Can generate if: has fresh selections OR brand/competitors changed
    return (
      freshCount > 0 ||
      comparison.brand_changes.brand_changed ||
      comparison.brand_changes.competitors_changed
    )
  }, [comparison, freshCount])

  // Build final selections array
  const buildSelectionsArray = useCallback((): PromptSelection[] => {
    if (!comparison) return []
    return comparison.prompt_selections.map((ps) => ({
      prompt_id: ps.prompt_id,
      evaluation_id: selections.get(ps.prompt_id) ?? null,
    }))
  }, [comparison, selections])

  const handleConfirm = () => {
    if (needsTopUp && onNeedsTopUp) {
      onNeedsTopUp(estimatedCost)
    } else {
      onConfirm(buildSelectionsArray())
    }
  }

  if (!isOpen) return null

  const isFree = estimatedCost === 0
  const totalPrompts = comparison?.total_prompts ?? 0
  const promptsAwaiting = comparison?.prompts_awaiting ?? 0
  const hasBrandChanges =
    comparison?.brand_changes?.brand_changed || comparison?.brand_changes?.competitors_changed

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
          relative w-full max-w-lg mx-4 bg-white rounded-xl shadow-2xl overflow-hidden
          animate-in fade-in slide-in-from-bottom-4 duration-300
          max-h-[85vh] flex flex-col
        "
        style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}
      >
        {/* Header accent bar */}
        <div className="h-1 w-full shrink-0" style={{ backgroundColor: accentColor }} />

        {/* Header */}
        <div className="px-5 pt-5 pb-4 border-b border-gray-100 shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl tracking-tight" style={{ color: accentColor }}>
                Generate report
              </h2>
              <p className="text-sm text-gray-400 mt-1 font-['DM_Sans'] truncate max-w-[340px]">
                {groupTitle}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-full hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-600"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="py-12 text-center flex-1">
            <div
              className="w-8 h-8 border-2 rounded-full animate-spin mx-auto mb-3"
              style={{
                borderColor: `${accentColor}30`,
                borderTopColor: accentColor,
              }}
            />
            <p className="text-sm text-gray-400 font-['DM_Sans']">Loading options...</p>
          </div>
        )}

        {/* Error state */}
        {isError && (
          <div className="py-12 text-center flex-1">
            <p className="text-sm text-red-500 font-['DM_Sans'] mb-3">Failed to load preview</p>
            <button
              onClick={() => refetch()}
              className="text-sm text-[#C4553D] hover:underline font-['DM_Sans']"
            >
              Try again
            </button>
          </div>
        )}

        {/* Content */}
        {comparison && !isLoading && (
          <>
            {/* Brand changes warning */}
            {hasBrandChanges && (
              <div className="mx-5 mt-4 flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-100 shrink-0">
                <svg
                  className="w-4 h-4 text-amber-500 mt-0.5 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-amber-800 font-['DM_Sans']">
                    {comparison.brand_changes.brand_changed && comparison.brand_changes.competitors_changed
                      ? "Brand & competitors changed"
                      : comparison.brand_changes.brand_changed
                        ? "Brand configuration changed"
                        : "Competitors changed"}
                  </p>
                  <p className="text-[11px] text-amber-600 mt-0.5 font-['DM_Sans']">
                    Report will be regenerated with updated settings
                  </p>
                </div>
              </div>
            )}

            {/* Summary stats */}
            <div className="px-5 py-3 flex items-center justify-between border-b border-gray-100 shrink-0">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: accentColor }}
                  />
                  <span className="text-xs text-gray-500 font-['DM_Sans']">
                    <span className="font-medium text-gray-700">{selectedCount}</span>/{totalPrompts} selected
                  </span>
                </div>
                {promptsAwaiting > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-gray-300" />
                    <span className="text-xs text-gray-400 font-['DM_Sans']">
                      {promptsAwaiting} awaiting
                    </span>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-gray-400 font-['DM_Sans']">
                  {freshCount} chargeable
                </span>
              </div>
            </div>

            {/* Scrollable prompts list */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-2 prompts-scroll">
              {comparison.prompt_selections.map((ps) => (
                <PromptSelectionCard
                  key={ps.prompt_id}
                  promptInfo={ps}
                  selectedEvaluationId={selections.get(ps.prompt_id) ?? null}
                  onSelectionChange={handleSelectionChange}
                  accentColor={accentColor}
                />
              ))}
            </div>

            {/* Footer with cost and actions */}
            <div className="px-5 py-4 border-t border-gray-100 bg-gray-50/50 shrink-0">
              {/* Cost summary */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-xs uppercase tracking-widest text-gray-400 font-['DM_Sans'] mb-1">
                    Estimated cost
                  </p>
                  <p
                    className="text-2xl font-semibold tabular-nums font-['DM_Sans']"
                    style={{ color: isFree ? "#10B981" : accentColor }}
                  >
                    {isFree ? "FREE" : `$${formatCredits(estimatedCost)}`}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-400 font-['DM_Sans'] mb-1">Your balance</p>
                  <p
                    className={`text-lg font-medium tabular-nums font-['DM_Sans'] ${
                      needsTopUp ? "text-amber-600" : "text-gray-700"
                    }`}
                  >
                    ${formatCredits(comparison.user_balance)}
                  </p>
                </div>
              </div>

              {/* Insufficient balance warning */}
              {needsTopUp && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-100 mb-4">
                  <svg
                    className="w-4 h-4 text-amber-500 mt-0.5 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-amber-800 font-['DM_Sans']">
                      Insufficient balance
                    </p>
                    <p className="text-[11px] text-amber-600 mt-0.5 font-['DM_Sans']">
                      Top up to generate this report
                    </p>
                  </div>
                </div>
              )}

              {/* No fresh data message */}
              {!canGenerate && !hasBrandChanges && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-gray-100 border border-gray-200 mb-4">
                  <svg
                    className="w-4 h-4 text-gray-400 mt-0.5 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-gray-600 font-['DM_Sans']">
                      No new data available
                    </p>
                    <p className="text-[11px] text-gray-500 mt-0.5 font-['DM_Sans']">
                      All prompts have been included in a previous report. New answers will appear as they become available.
                    </p>
                  </div>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  className="
                    flex-1 py-3 px-4 rounded-lg text-sm font-medium
                    text-gray-600 bg-gray-100 hover:bg-gray-200
                    transition-colors font-['DM_Sans']
                  "
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirm}
                  disabled={!canGenerate || (!canAfford && !onNeedsTopUp)}
                  className={`
                    flex-1 py-3 px-4 rounded-lg text-sm font-medium
                    text-white transition-all font-['DM_Sans']
                    disabled:opacity-50 disabled:cursor-not-allowed
                    ${isFree && canGenerate ? "bg-green-500 hover:bg-green-600" : ""}
                  `}
                  style={{
                    backgroundColor: isFree && canGenerate ? undefined : accentColor,
                  }}
                >
                  {!canGenerate ? (
                    "No new data"
                  ) : needsTopUp ? (
                    "Top up to continue"
                  ) : isFree ? (
                    "Generate free"
                  ) : (
                    <>Generate — ${formatCredits(estimatedCost)}</>
                  )}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
