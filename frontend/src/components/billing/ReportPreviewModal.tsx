/**
 * ReportPreviewModal - Fresh execution flow with per-prompt evaluation selection
 * Editorial/refined aesthetic matching the existing app design
 */

import { useState, useEffect, useMemo, useCallback, useRef } from "react"
import { useReportData, useRequestFresh } from "@/hooks/useExecution"
import { formatCredits } from "@/hooks/useBilling"
import type { PromptReportData, FreshnessCategory } from "@/types/execution"
import type { PromptSelection } from "@/types/billing"

// Selection can be: evaluation_id (number), 'ask_fresh', or null (skip)
type SelectionValue = number | "ask_fresh" | null

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

// Freshness badge component
function FreshnessBadge({ category }: { category: FreshnessCategory }) {
  const config: Record<FreshnessCategory, { label: string; color: string; bg: string }> = {
    fresh: { label: "Fresh", color: "text-green-600", bg: "bg-green-50" },
    stale: { label: "Stale", color: "text-amber-600", bg: "bg-amber-50" },
    very_stale: { label: "Old", color: "text-red-600", bg: "bg-red-50" },
    none: { label: "No data", color: "text-gray-500", bg: "bg-gray-100" },
  }
  const { label, color, bg } = config[category]

  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded font-['DM_Sans'] ${color} ${bg}`}>
      {label}
    </span>
  )
}

// Per-prompt selection card
function PromptSelectionCard({
  promptInfo,
  selection,
  onSelectionChange,
  onRemove,
  accentColor,
  globalQueueWait,
}: {
  promptInfo: PromptReportData
  selection: SelectionValue
  onSelectionChange: (promptId: number, selection: SelectionValue) => void
  onRemove: (promptId: number) => void
  accentColor: string
  globalQueueWait: string | null
}) {
  const hasEvaluations = promptInfo.evaluations.length > 0
  const isPending = promptInfo.pending_execution
  const isAskFresh = selection === "ask_fresh"
  const selectedEvalId = typeof selection === "number" ? selection : null

  // Status display
  let statusElement = <FreshnessBadge category={promptInfo.freshness_category} />
  if (isPending) {
    statusElement = (
      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 font-['DM_Sans']">
        Pending
      </span>
    )
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white transition-all duration-200 hover:border-gray-300">
      {/* Header row */}
      <div className="px-3 py-2.5 flex items-start justify-between gap-3">
        <p className="text-sm font-['DM_Sans'] line-clamp-2 text-gray-700 flex-1 min-w-0">
          {promptInfo.prompt_text}
        </p>
        <div className="flex items-center gap-2 shrink-0">
          {statusElement}
          <button
            type="button"
            onClick={() => onRemove(promptInfo.prompt_id)}
            className="p-0.5 rounded hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-600"
            title="Remove from report"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Selection options */}
      <div className="px-3 pb-2.5 pt-0 space-y-1.5">
        {/* Evaluation options */}
        {promptInfo.evaluations.map((evaluation) => (
          <label
            key={evaluation.evaluation_id}
            className={`
              flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-md cursor-pointer
              border transition-colors text-sm font-['DM_Sans']
              ${selectedEvalId === evaluation.evaluation_id ? "border-gray-300 bg-gray-50" : "border-gray-100 hover:border-gray-200 bg-gray-50/50"}
            `}
          >
            <div className="flex items-center gap-2 min-w-0">
              <input
                type="radio"
                name={`prompt-${promptInfo.prompt_id}`}
                checked={selectedEvalId === evaluation.evaluation_id}
                onChange={() => onSelectionChange(promptInfo.prompt_id, evaluation.evaluation_id)}
                className="w-3.5 h-3.5 text-gray-700 focus:ring-gray-400"
              />
              <span className="truncate text-gray-700">{formatShortDate(evaluation.completed_at)}</span>
            </div>
            {evaluation.is_consumed ? (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-green-50 text-green-600 shrink-0">
                FREE
              </span>
            ) : (
              <span
                className="text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0"
                style={{ backgroundColor: `${accentColor}15`, color: accentColor }}
              >
                $0.01
              </span>
            )}
          </label>
        ))}

        {/* Ask for fresh option */}
        {promptInfo.show_ask_for_fresh && !isPending && (
          <label
            className={`
              flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-md cursor-pointer
              border transition-colors text-sm font-['DM_Sans']
              ${isAskFresh ? "border-blue-300 bg-blue-50/50" : "border-gray-100 hover:border-gray-200 bg-gray-50/50"}
            `}
          >
            <div className="flex items-center gap-2 min-w-0">
              <input
                type="radio"
                name={`prompt-${promptInfo.prompt_id}`}
                checked={isAskFresh}
                onChange={() => onSelectionChange(promptInfo.prompt_id, "ask_fresh")}
                className="w-3.5 h-3.5 text-blue-600 focus:ring-blue-400"
              />
              <span className="text-blue-600">Request fresh answer</span>
            </div>
            {globalQueueWait && (
              <span className="text-[10px] text-blue-500 shrink-0">~{globalQueueWait}</span>
            )}
          </label>
        )}

        {/* Pending execution indicator */}
        {isPending && (
          <div className="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-md bg-blue-50/50 border border-blue-100">
            <div className="flex items-center gap-2">
              <div className="w-3.5 h-3.5 flex items-center justify-center">
                <div
                  className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"
                />
              </div>
              <span className="text-sm text-blue-600 font-['DM_Sans']">Execution pending...</span>
            </div>
            {promptInfo.estimated_wait && (
              <span className="text-[10px] text-blue-500">~{promptInfo.estimated_wait}</span>
            )}
          </div>
        )}

        {/* No data, no pending - auto ask_fresh */}
        {!hasEvaluations && !isPending && promptInfo.auto_ask_for_fresh && (
          <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-gray-50 border border-gray-200">
            <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-sm text-gray-500 font-['DM_Sans']">Will request fresh answer</span>
          </div>
        )}
      </div>
    </div>
  )
}

export function ReportPreviewModal(props: ReportPreviewModalProps) {
  const { groupId, groupTitle, accentColor, isOpen, onClose, onConfirm } = props
  const { data: reportData, isLoading, isError, refetch } = useReportData(groupId, isOpen)
  const requestFreshMutation = useRequestFresh()

  // Track user selections: promptId -> SelectionValue (empty = use defaults)
  const [selections, setSelections] = useState<Map<number, SelectionValue>>(new Map())
  // Track removed prompts (excluded from report)
  const [removedPrompts, setRemovedPrompts] = useState<Set<number>>(new Set())
  // Success state for the combined generate action
  const [generateSuccess, setGenerateSuccess] = useState<{
    reportCount: number
    freshCount: number
    estimatedWait: string | null
  } | null>(null)

  // Build default selections from report data
  const defaultSelections = useMemo(() => {
    if (!reportData?.prompts) return new Map<number, SelectionValue>()
    const map = new Map<number, SelectionValue>()
    reportData.prompts.forEach((p) => {
      if (p.pending_execution) {
        map.set(p.prompt_id, null)
      } else if (p.auto_ask_for_fresh) {
        map.set(p.prompt_id, "ask_fresh")
      } else if (p.default_evaluation_id !== null) {
        map.set(p.prompt_id, p.default_evaluation_id)
      } else {
        map.set(p.prompt_id, null)
      }
    })
    return map
  }, [reportData])

  // Merge user selections with defaults (user selections override defaults)
  const effectiveSelections = useMemo(() => {
    const merged = new Map(defaultSelections)
    for (const [promptId, selection] of selections) {
      merged.set(promptId, selection)
    }
    return merged
  }, [selections, defaultSelections])

  // Refetch when modal opens
  useEffect(() => {
    if (isOpen) {
      refetch()
    }
  }, [isOpen, refetch])

  // Reset state when modal opens - this is the standard React pattern for resetting
  // state when a prop changes. The lint rule is overly strict for this use case.
  const prevIsOpenRef = useRef(false)
  useEffect(() => {
    if (isOpen && !prevIsOpenRef.current) {
      // Modal just opened, reset selections to allow fresh defaults to take effect
      // eslint-disable-next-line react-hooks/set-state-in-effect -- Intentional reset on prop change
      setSelections(new Map())
      setRemovedPrompts(new Set())
      setGenerateSuccess(null)
    }
    prevIsOpenRef.current = isOpen
  }, [isOpen])

  // Handle selection change
  const handleSelectionChange = useCallback((promptId: number, selection: SelectionValue) => {
    setSelections((prev) => {
      const next = new Map(prev)
      next.set(promptId, selection)
      return next
    })
  }, [])

  // Handle removing a prompt from the report
  const handleRemovePrompt = useCallback((promptId: number) => {
    setRemovedPrompts((prev) => {
      const next = new Set(prev)
      next.add(promptId)
      return next
    })
  }, [])

  // Derived state for summary (excludes removed prompts)
  const summary = useMemo(() => {
    if (!reportData) {
      return {
        forReport: [] as number[],
        forReportFresh: 0,
        forReportConsumed: 0,
        forFresh: [] as number[],
        removed: 0,
        estimatedCost: 0,
      }
    }

    const forReport: number[] = []
    const forFresh: number[] = []
    let forReportFresh = 0
    let forReportConsumed = 0

    for (const prompt of reportData.prompts) {
      // Skip removed prompts
      if (removedPrompts.has(prompt.prompt_id)) continue

      const sel = effectiveSelections.get(prompt.prompt_id)
      if (typeof sel === "number") {
        forReport.push(prompt.prompt_id)
        const evaluation = prompt.evaluations.find((e) => e.evaluation_id === sel)
        if (evaluation?.is_consumed) {
          forReportConsumed++
        } else {
          forReportFresh++
        }
      } else if (sel === "ask_fresh") {
        forFresh.push(prompt.prompt_id)
      }
    }

    return {
      forReport,
      forReportFresh,
      forReportConsumed,
      forFresh,
      removed: removedPrompts.size,
      estimatedCost: forReportFresh * 0.01, // $0.01 per fresh evaluation
    }
  }, [reportData, effectiveSelections, removedPrompts])

  // Combined generate handler: generates report AND requests fresh executions
  const handleGenerate = async () => {
    const hasReport = summary.forReport.length > 0
    const hasFresh = summary.forFresh.length > 0

    if (!hasReport && !hasFresh) return

    let freshResult: { queued_count: number; estimated_total_wait: string } | null = null

    // Request fresh executions first (if any)
    if (hasFresh) {
      try {
        freshResult = await requestFreshMutation.mutateAsync(summary.forFresh)
      } catch (error) {
        console.error("Failed to request fresh execution:", error)
        return // Don't proceed if fresh request fails
      }
    }

    // Generate report (if any prompts have selected evaluations)
    if (hasReport) {
      const reportSelections = reportData!.prompts
        .filter((p) => !removedPrompts.has(p.prompt_id))
        .filter((p) => typeof effectiveSelections.get(p.prompt_id) === "number")
        .map((p) => ({
          prompt_id: p.prompt_id,
          evaluation_id: effectiveSelections.get(p.prompt_id) as number,
        }))

      onConfirm(reportSelections)
    }

    // Show success state
    setGenerateSuccess({
      reportCount: hasReport ? summary.forReport.length : 0,
      freshCount: freshResult?.queued_count ?? 0,
      estimatedWait: freshResult?.estimated_total_wait ?? null,
    })

    // Refetch to update pending status if we requested fresh
    if (hasFresh) {
      refetch()
    }
  }

  if (!isOpen) return null

  const canGenerateReport = summary.forReport.length > 0
  const canRequestFresh = summary.forFresh.length > 0
  const globalQueueWait = reportData
    ? `${Math.ceil(reportData.global_queue_size * 0.5)}m`
    : null

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
        {reportData && !isLoading && (
          <>
            {/* Success message after generate */}
            {generateSuccess && (
              <div className="mx-5 mt-4 p-4 rounded-lg bg-green-50 border border-green-100 shrink-0">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                    <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-green-800 font-['DM_Sans']">
                      {generateSuccess.reportCount > 0 && generateSuccess.freshCount > 0
                        ? "Report generated & fresh answers requested"
                        : generateSuccess.reportCount > 0
                          ? "Report generated"
                          : "Fresh answers requested"}
                    </p>
                    <div className="mt-1.5 space-y-1">
                      {generateSuccess.reportCount > 0 && (
                        <p className="text-xs text-green-700 font-['DM_Sans']">
                          ✓ {generateSuccess.reportCount} prompt{generateSuccess.reportCount !== 1 ? "s" : ""} included in report
                        </p>
                      )}
                      {generateSuccess.freshCount > 0 && generateSuccess.estimatedWait && (
                        <p className="text-xs text-green-700 font-['DM_Sans']">
                          ✓ {generateSuccess.freshCount} prompt{generateSuccess.freshCount !== 1 ? "s" : ""} queued — ready in ~{generateSuccess.estimatedWait}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={onClose}
                      className="mt-3 text-xs font-medium text-green-700 hover:text-green-800 underline underline-offset-2 font-['DM_Sans']"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Summary stats */}
            <div className="px-5 py-3 flex items-center justify-between border-b border-gray-100 shrink-0">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="text-xs text-gray-500 font-['DM_Sans']">
                    <span className="font-medium text-gray-700">{reportData.prompts_fresh}</span> fresh
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500" />
                  <span className="text-xs text-gray-500 font-['DM_Sans']">
                    <span className="font-medium text-gray-700">{reportData.prompts_stale}</span> stale
                  </span>
                </div>
                {reportData.prompts_no_data > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-gray-300" />
                    <span className="text-xs text-gray-500 font-['DM_Sans']">
                      <span className="font-medium text-gray-700">{reportData.prompts_no_data}</span> no data
                    </span>
                  </div>
                )}
              </div>
              {reportData.prompts_pending_execution > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                  <span className="text-xs text-gray-500 font-['DM_Sans']">
                    <span className="font-medium text-gray-700">{reportData.prompts_pending_execution}</span> pending
                  </span>
                </div>
              )}
            </div>

            {/* Scrollable prompts list */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-2 prompts-scroll">
              {reportData.prompts
                .filter((prompt) => !removedPrompts.has(prompt.prompt_id))
                .map((prompt) => (
                  <PromptSelectionCard
                    key={prompt.prompt_id}
                    promptInfo={prompt}
                    selection={effectiveSelections.get(prompt.prompt_id) ?? null}
                    onSelectionChange={handleSelectionChange}
                    onRemove={handleRemovePrompt}
                    accentColor={accentColor}
                    globalQueueWait={globalQueueWait}
                  />
                ))}
            </div>

            {/* Footer with actions */}
            <div className="px-5 py-4 border-t border-gray-100 bg-gray-50/50 shrink-0">
              {/* Selection summary */}
              <div className="flex items-center justify-between mb-4">
                <div className="text-xs text-gray-500 font-['DM_Sans']">
                  {summary.forReport.length > 0 && (
                    <span>
                      <span className="font-medium text-gray-700">{summary.forReport.length}</span> for report
                      {summary.forReportFresh > 0 && (
                        <span className="text-gray-400"> ({summary.forReportFresh} chargeable)</span>
                      )}
                    </span>
                  )}
                  {summary.forReport.length > 0 && summary.forFresh.length > 0 && <span className="mx-2">•</span>}
                  {summary.forFresh.length > 0 && (
                    <span>
                      <span className="font-medium text-blue-600">{summary.forFresh.length}</span> for fresh execution
                    </span>
                  )}
                  {summary.removed > 0 && (
                    <>
                      {(summary.forReport.length > 0 || summary.forFresh.length > 0) && (
                        <span className="mx-2">•</span>
                      )}
                      <span className="text-gray-400">{summary.removed} excluded</span>
                    </>
                  )}
                </div>
                {summary.estimatedCost > 0 && (
                  <div className="text-sm font-medium font-['DM_Sans']" style={{ color: accentColor }}>
                    ${formatCredits(summary.estimatedCost)}
                  </div>
                )}
              </div>

              {/* Action buttons */}
              {!generateSuccess && (
                <div className="flex gap-3">
                  <button
                    onClick={onClose}
                    className="
                      py-3 px-6 rounded-lg text-sm font-medium
                      text-gray-600 bg-gray-100 hover:bg-gray-200
                      transition-colors font-['DM_Sans']
                    "
                  >
                    Cancel
                  </button>

                  {/* Single Generate button */}
                  <button
                    onClick={handleGenerate}
                    disabled={!canGenerateReport && !canRequestFresh || requestFreshMutation.isPending}
                    className="
                      flex-1 py-3 px-4 rounded-lg text-sm font-medium
                      text-white transition-all font-['DM_Sans']
                      disabled:opacity-50 disabled:cursor-not-allowed
                    "
                    style={{ backgroundColor: accentColor }}
                  >
                    {requestFreshMutation.isPending ? (
                      <span className="flex items-center justify-center gap-2">
                        <div className="w-3.5 h-3.5 border-2 border-white/50 border-t-white rounded-full animate-spin" />
                        Processing...
                      </span>
                    ) : !canGenerateReport && !canRequestFresh ? (
                      "Select prompts"
                    ) : (
                      <span>
                        Generate
                        {summary.forReport.length > 0 && summary.forFresh.length > 0 && (
                          <span className="opacity-75 ml-1">
                            ({summary.forReport.length} + {summary.forFresh.length} fresh)
                          </span>
                        )}
                        {summary.forReport.length > 0 && summary.forFresh.length === 0 && (
                          <span className="opacity-75 ml-1">({summary.forReport.length})</span>
                        )}
                        {summary.forReport.length === 0 && summary.forFresh.length > 0 && (
                          <span className="opacity-75 ml-1">({summary.forFresh.length} fresh)</span>
                        )}
                        {summary.estimatedCost > 0 && (
                          <span className="ml-1">— ${formatCredits(summary.estimatedCost)}</span>
                        )}
                      </span>
                    )}
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
