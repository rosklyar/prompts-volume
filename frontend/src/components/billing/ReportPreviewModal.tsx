/**
 * ReportPreviewModal - Simplified report generation with automatic selection
 *
 * Shows read-only status of each prompt:
 * - Fresh (≤24h): will be included in report
 * - Stale (>24h): will request fresh answer
 * - Absent (no data): will request fresh answer
 *
 * Single "Generate" button handles everything automatically.
 */

import { useState, useEffect } from "react"
import { useReportData, useRequestFresh } from "@/hooks/useExecution"
import type { PromptStatus, PromptReportData } from "@/types/execution"
import type { PromptSelection } from "@/types/billing"

interface ReportPreviewModalProps {
  groupId: number
  groupTitle: string
  accentColor: string
  isOpen: boolean
  assistantId: number
  onClose: () => void
  onConfirm: (selections: PromptSelection[], assistantId: number) => void
  onNeedsTopUp?: (estimatedCost: number) => void
}

// Status badge component with 3 states
function StatusBadge({ status }: { status: PromptStatus }) {
  const config: Record<PromptStatus, { label: string; color: string; bg: string }> = {
    fresh: { label: "Fresh", color: "text-green-600", bg: "bg-green-50" },
    stale: { label: "Stale", color: "text-amber-600", bg: "bg-amber-50" },
    absent: { label: "Absent", color: "text-gray-500", bg: "bg-gray-100" },
  }
  const { label, color, bg } = config[status]

  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded font-['DM_Sans'] ${color} ${bg}`}>
      {label}
    </span>
  )
}

// Simple prompt row (read-only, no selection)
function PromptRow({
  prompt,
  globalQueueWait,
}: {
  prompt: PromptReportData
  globalQueueWait: string | null
}) {
  const isPending = prompt.pending_execution

  return (
    <div className="px-3 py-2.5 rounded-lg border border-gray-200 bg-white flex items-center justify-between gap-2">
      <p className="text-sm font-['DM_Sans'] line-clamp-1 text-gray-700 min-w-0 flex-1">
        {prompt.prompt_text}
      </p>

      <div className="flex items-center gap-2 shrink-0">
        {/* Status indicator */}
        {isPending ? (
          <span className="text-xs text-blue-600 font-['DM_Sans'] flex items-center gap-1">
            <span className="w-2 h-2 border border-blue-400 border-t-transparent rounded-full animate-spin" />
            Pending
            {prompt.estimated_wait && <span className="text-blue-400">({prompt.estimated_wait})</span>}
          </span>
        ) : prompt.status === "fresh" ? (
          <span className="text-xs text-green-600 font-['DM_Sans']">Ready</span>
        ) : (
          <span className="text-xs text-amber-600 font-['DM_Sans']">
            Will refresh
            {globalQueueWait && <span className="text-amber-400 ml-1">({globalQueueWait})</span>}
          </span>
        )}

        <StatusBadge status={prompt.status} />
      </div>
    </div>
  )
}

export function ReportPreviewModal(props: ReportPreviewModalProps) {
  const { groupId, groupTitle, accentColor, isOpen, assistantId, onClose, onConfirm } = props

  // Fetch report data for the selected assistant
  const { data: reportData, isLoading, isError, refetch } = useReportData(
    groupId,
    assistantId,
    isOpen
  )
  const requestFreshMutation = useRequestFresh()

  // Success state for the generate action
  const [generateSuccess, setGenerateSuccess] = useState<{
    reportCount: number
    freshCount: number
    estimatedWait: string | null
  } | null>(null)

  // Confirmation state for partial report generation
  const [showConfirmation, setShowConfirmation] = useState(false)

  // Track previous isOpen to reset state when modal opens (React-approved pattern)
  const [prevIsOpen, setPrevIsOpen] = useState(false)
  if (isOpen && !prevIsOpen) {
    setGenerateSuccess(null)
    setShowConfirmation(false)
  }
  if (isOpen !== prevIsOpen) {
    setPrevIsOpen(isOpen)
  }

  // Refetch when modal opens or assistant changes
  useEffect(() => {
    if (isOpen) {
      refetch()
    }
  }, [isOpen, assistantId, refetch])

  // Get counts for confirmation dialog
  const getFreshPrompts = () => reportData?.prompts.filter(
    (p) => p.status === "fresh" && !p.pending_execution
  ) ?? []
  const getNeedsFreshPrompts = () => reportData?.prompts.filter(
    (p) => (p.status === "stale" || p.status === "absent") && !p.pending_execution
  ) ?? []

  // Handle Generate button click - show confirmation only for partial reports
  const handleGenerateClick = () => {
    if (!reportData) return

    const freshPrompts = getFreshPrompts()
    const needsFreshPrompts = getNeedsFreshPrompts()

    // If we have both fresh AND stale/absent prompts, it's a partial report - confirm
    if (freshPrompts.length > 0 && needsFreshPrompts.length > 0) {
      setShowConfirmation(true)
      return
    }

    // All prompts are fresh - generate full report immediately
    if (freshPrompts.length > 0 && needsFreshPrompts.length === 0) {
      const selections: PromptSelection[] = freshPrompts.map((p) => ({
        prompt_id: p.prompt_id,
        evaluation_id: p.latest_evaluation_id!,
      }))
      onConfirm(selections, assistantId)
      setGenerateSuccess({
        reportCount: freshPrompts.length,
        freshCount: 0,
        estimatedWait: null,
      })
      return
    }

    // No fresh prompts - just request fresh for stale/absent
    if (needsFreshPrompts.length > 0) {
      handleRequestFreshOnly()
    }
  }

  // Request fresh only (no report generation)
  const handleRequestFreshOnly = async () => {
    const needsFreshPrompts = getNeedsFreshPrompts()
    if (needsFreshPrompts.length === 0) return

    try {
      const freshResult = await requestFreshMutation.mutateAsync({
        promptIds: needsFreshPrompts.map((p) => p.prompt_id),
        assistantId,
      })

      setGenerateSuccess({
        reportCount: 0,
        freshCount: freshResult.queued_count,
        estimatedWait: freshResult.estimated_total_wait,
      })

      refetch()
    } catch (error) {
      console.error("Failed to request fresh execution:", error)
    }
  }

  // Confirmed generation: generate report with fresh + request fresh for stale/absent
  const handleConfirmedGenerate = async () => {
    setShowConfirmation(false)

    const freshPrompts = getFreshPrompts()
    const needsFreshPrompts = getNeedsFreshPrompts()

    let freshResult: { queued_count: number; estimated_total_wait: string } | null = null

    // Request fresh for stale/absent prompts
    if (needsFreshPrompts.length > 0) {
      try {
        freshResult = await requestFreshMutation.mutateAsync({
          promptIds: needsFreshPrompts.map((p) => p.prompt_id),
          assistantId,
        })
      } catch (error) {
        console.error("Failed to request fresh execution:", error)
        return
      }
    }

    // Generate report with fresh prompts
    if (freshPrompts.length > 0) {
      const selections: PromptSelection[] = freshPrompts.map((p) => ({
        prompt_id: p.prompt_id,
        evaluation_id: p.latest_evaluation_id!,
      }))
      onConfirm(selections, assistantId)
    }

    // Show success state
    setGenerateSuccess({
      reportCount: freshPrompts.length,
      freshCount: freshResult?.queued_count ?? 0,
      estimatedWait: freshResult?.estimated_total_wait ?? null,
    })

    // Refetch to update pending status
    if (needsFreshPrompts.length > 0) {
      refetch()
    }
  }

  if (!isOpen) return null

  const freshCount = reportData?.prompts_fresh ?? 0
  const staleCount = reportData?.prompts_stale ?? 0
  const absentCount = reportData?.prompts_absent ?? 0
  const pendingCount = reportData?.prompts_pending_execution ?? 0

  // Count actionable (non-pending) prompts
  const actionableFresh = reportData?.prompts.filter(
    (p) => p.status === "fresh" && !p.pending_execution
  ).length ?? 0
  const actionableStaleAbsent = reportData?.prompts.filter(
    (p) => (p.status === "stale" || p.status === "absent") && !p.pending_execution
  ).length ?? 0

  const canGenerate = (actionableFresh > 0 || actionableStaleAbsent > 0) && !generateSuccess
  const allFresh = actionableFresh > 0 && actionableStaleAbsent === 0
  const globalQueueWait = reportData && reportData.global_queue_size > 0
    ? `~${Math.ceil(reportData.global_queue_size * 0.5)}m`
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
              <p className="text-sm text-gray-400 font-['DM_Sans'] truncate max-w-[320px] mt-1">
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
            <p className="text-sm text-gray-400 font-['DM_Sans']">Loading...</p>
          </div>
        )}

        {/* Error state */}
        {isError && (
          <div className="py-12 text-center flex-1">
            <p className="text-sm text-red-500 font-['DM_Sans'] mb-3">Failed to load</p>
            <button
              onClick={() => refetch()}
              className="text-sm hover:underline font-['DM_Sans']"
              style={{ color: accentColor }}
            >
              Try again
            </button>
          </div>
        )}

        {/* Content */}
        {reportData && !isLoading && (
          <>
            {/* Success message */}
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
                          ✓ {generateSuccess.reportCount} prompt{generateSuccess.reportCount !== 1 ? "s" : ""} included
                        </p>
                      )}
                      {generateSuccess.freshCount > 0 && (
                        <p className="text-xs text-green-700 font-['DM_Sans']">
                          ✓ {generateSuccess.freshCount} prompt{generateSuccess.freshCount !== 1 ? "s" : ""} queued
                          {generateSuccess.estimatedWait && ` — ready in ~${generateSuccess.estimatedWait}`}
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
                {freshCount > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-green-500" />
                    <span className="text-xs text-gray-500 font-['DM_Sans']">
                      <span className="font-medium text-gray-700">{freshCount}</span> fresh
                    </span>
                  </div>
                )}
                {staleCount > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-amber-500" />
                    <span className="text-xs text-gray-500 font-['DM_Sans']">
                      <span className="font-medium text-gray-700">{staleCount}</span> stale
                    </span>
                  </div>
                )}
                {absentCount > 0 && (
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-gray-300" />
                    <span className="text-xs text-gray-500 font-['DM_Sans']">
                      <span className="font-medium text-gray-700">{absentCount}</span> absent
                    </span>
                  </div>
                )}
              </div>
              {pendingCount > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                  <span className="text-xs text-gray-500 font-['DM_Sans']">
                    <span className="font-medium text-gray-700">{pendingCount}</span> pending
                  </span>
                </div>
              )}
            </div>

            {/* Scrollable prompts list (read-only) */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-2 prompts-scroll">
              {reportData.prompts.map((prompt) => (
                <PromptRow
                  key={prompt.prompt_id}
                  prompt={prompt}
                  globalQueueWait={globalQueueWait}
                />
              ))}
            </div>

            {/* Confirmation dialog */}
            {showConfirmation && (
              <div className="mx-5 mb-4 p-4 rounded-lg bg-amber-50 border border-amber-200 shrink-0">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center shrink-0">
                    <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-amber-800 font-['DM_Sans']">
                      Generate partial report?
                    </p>
                    <p className="mt-1 text-xs text-amber-700 font-['DM_Sans']">
                      Only <span className="font-medium">{actionableFresh}</span> of {reportData.total_prompts} prompts have fresh answers.
                      {actionableStaleAbsent > 0 && (
                        <> The remaining <span className="font-medium">{actionableStaleAbsent}</span> will be queued for refresh.</>
                      )}
                    </p>
                    <div className="mt-3 flex gap-2">
                      <button
                        onClick={() => setShowConfirmation(false)}
                        className="px-3 py-1.5 text-xs font-medium text-amber-700 bg-amber-100 hover:bg-amber-200 rounded transition-colors font-['DM_Sans']"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleConfirmedGenerate}
                        disabled={requestFreshMutation.isPending}
                        className="px-3 py-1.5 text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 rounded transition-colors font-['DM_Sans'] disabled:opacity-50"
                      >
                        {requestFreshMutation.isPending ? "Processing..." : "Generate anyway"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Footer with actions */}
            <div className="px-5 py-4 border-t border-gray-100 bg-gray-50/50 shrink-0">
              {/* Action buttons */}
              {!generateSuccess && !showConfirmation && (
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

                  <button
                    onClick={handleGenerateClick}
                    disabled={!canGenerate || requestFreshMutation.isPending}
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
                    ) : allFresh ? (
                      "Generate"
                    ) : (
                      "Request answers"
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
