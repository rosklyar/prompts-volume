/**
 * ReportModal - Simplified report generation modal
 *
 * Flow:
 * 1. User selects assistant from dropdown (data refetches on change)
 * 2. Summary shows: "X ready • Y need fresh answers"
 * 3. Optional: expand to see individual prompt statuses
 * 4. One-click action: "Generate" or "Request Report"
 *
 * States:
 * - Ready: all prompts fresh → "Generate" → immediate report
 * - Needs Refresh: stale/absent prompts → "Request Report" → waits for answers
 * - Pending: request in progress → shows progress
 * - Generating: report being generated
 * - Completed: report ready to view
 */

import { useState, useEffect, useRef } from "react"
import { useReportData } from "@/hooks/useExecution"
import { useReportRequest } from "@/hooks/useReportRequest"
import { useAssistants } from "@/hooks/useAssistants"
import { getAssistantLogo } from "@/utils/assistantLogos"
import type { PromptStatus, PromptReportData } from "@/types/execution"
import type { PromptSelection } from "@/types/billing"

interface ReportModalProps {
  groupId: number
  groupTitle: string
  accentColor: string
  isOpen: boolean
  onClose: () => void
  onReportGenerated?: (selections: PromptSelection[], assistantId: number) => void
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

// Compact prompt row for details section
function PromptRow({
  prompt,
  globalQueueWait,
}: {
  prompt: PromptReportData
  globalQueueWait: string | null
}) {
  const isPending = prompt.pending_execution

  return (
    <div className="px-3 py-2 rounded-lg border border-gray-200 bg-white flex items-center justify-between gap-2">
      <p className="text-sm font-['DM_Sans'] line-clamp-1 text-gray-700 min-w-0 flex-1">
        {prompt.prompt_text}
      </p>

      <div className="flex items-center gap-2 shrink-0">
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

export function ReportModal(props: ReportModalProps) {
  const { groupId, groupTitle, accentColor, isOpen, onClose, onReportGenerated } = props

  // Assistant selection state (drives data fetching)
  const [assistantId, setAssistantId] = useState(1) // Default to ChatGPT
  const { data: assistantsData, isLoading: isLoadingAssistants } = useAssistants()

  // Collapsible prompt details state
  const [showDetails, setShowDetails] = useState(false)

  // Custom dropdown state
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // Fetch report data for the selected assistant
  const {
    data: reportData,
    isLoading: isLoadingData,
    isError,
    refetch,
  } = useReportData(groupId, assistantId, isOpen)

  // Unified report request hook
  const {
    hasPending,
    pendingRequest,
    isAwaiting,
    isReady,
    isGenerating,
    isCompleted,
    progress,
    createRequest,
    cancelRequest,
    invalidateReports,
    isCreating,
    isCancelling,
  } = useReportRequest(groupId, isOpen)

  // Success state for the generate action
  const [generateSuccess, setGenerateSuccess] = useState<{
    reportCount: number
    requestCreated?: boolean
  } | null>(null)

  // Track previous isOpen to reset state when modal opens
  const [prevIsOpen, setPrevIsOpen] = useState(false)
  if (isOpen && !prevIsOpen) {
    setGenerateSuccess(null)
    setShowDetails(false)
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

  // When request completes, invalidate reports
  useEffect(() => {
    if (isCompleted && pendingRequest?.report_id) {
      invalidateReports()
    }
  }, [isCompleted, pendingRequest?.report_id, invalidateReports])

  // Get counts for button logic
  const getFreshPrompts = () =>
    reportData?.prompts.filter((p) => p.status === "fresh" && !p.pending_execution) ?? []
  const getNeedsFreshPrompts = () =>
    reportData?.prompts.filter(
      (p) => (p.status === "stale" || p.status === "absent") && !p.pending_execution
    ) ?? []

  // Handle Generate/Request button click
  const handleGenerateClick = async () => {
    if (!reportData) return

    const freshPrompts = getFreshPrompts()
    const needsFreshPrompts = getNeedsFreshPrompts()

    // All prompts are fresh - generate full report immediately
    if (freshPrompts.length > 0 && needsFreshPrompts.length === 0) {
      const selections: PromptSelection[] = freshPrompts.map((p) => ({
        prompt_id: p.prompt_id,
        evaluation_id: p.latest_evaluation_id!,
      }))
      onReportGenerated?.(selections, assistantId)
      setGenerateSuccess({
        reportCount: freshPrompts.length,
      })
      return
    }

    // Has stale/absent prompts - create unified report request
    if (needsFreshPrompts.length > 0 || freshPrompts.length > 0) {
      try {
        await createRequest(assistantId)
        setGenerateSuccess({
          reportCount: 0,
          requestCreated: true,
        })
      } catch (error) {
        console.error("Failed to create report request:", error)
      }
    }
  }

  // Handle cancel request
  const handleCancelRequest = async () => {
    try {
      await cancelRequest()
    } catch (error) {
      console.error("Failed to cancel request:", error)
    }
  }

  if (!isOpen) return null

  const isLoading = isLoadingData || isLoadingAssistants

  const freshCount = reportData?.prompts_fresh ?? 0
  const needsRefreshCount = (reportData?.prompts_stale ?? 0) + (reportData?.prompts_absent ?? 0)
  const pendingCount = reportData?.prompts_pending_execution ?? 0
  const totalPrompts = reportData?.total_prompts ?? 0

  // Count actionable (non-pending) prompts
  const actionableFresh =
    reportData?.prompts.filter((p) => p.status === "fresh" && !p.pending_execution).length ?? 0
  const actionableStaleAbsent =
    reportData?.prompts.filter(
      (p) => (p.status === "stale" || p.status === "absent") && !p.pending_execution
    ).length ?? 0

  const wouldBeDuplicate = reportData?.would_be_duplicate ?? false
  const canGenerate =
    (actionableFresh > 0 || actionableStaleAbsent > 0) &&
    !generateSuccess &&
    !hasPending &&
    !wouldBeDuplicate
  const allFresh = actionableFresh > 0 && actionableStaleAbsent === 0
  const globalQueueWait =
    reportData && reportData.global_queue_size > 0
      ? `~${Math.ceil(reportData.global_queue_size * 0.5)}m`
      : null

  // Determine button text
  const getButtonText = () => {
    if (allFresh) return "Generate"
    return "Request Report"
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
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M6 18L18 6M6 6l12 12"
                />
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
            {/* Assistant Dropdown */}
            <div className="px-5 pt-4 pb-3 shrink-0">
              <label className="block text-sm font-medium text-gray-600 mb-2 font-['DM_Sans']">
                AI Assistant
              </label>
              <div className="relative" ref={dropdownRef}>
                <button
                  type="button"
                  onClick={() => !generateSuccess && setDropdownOpen(!dropdownOpen)}
                  disabled={!!generateSuccess}
                  className="
                    w-full px-3 py-2.5 rounded-lg border border-gray-200
                    bg-white text-gray-700 text-sm font-['DM_Sans']
                    text-left flex items-center gap-2
                    focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-opacity-50
                    disabled:opacity-50 disabled:cursor-not-allowed
                  "
                >
                  {(() => {
                    const selectedAssistant = assistantsData?.assistants.find((a) => a.id === assistantId)
                    const logo = selectedAssistant ? getAssistantLogo(selectedAssistant.name) : null
                    return (
                      <>
                        {logo && <img src={logo} alt="" className="w-5 h-5" />}
                        <span className="flex-1">{selectedAssistant?.name ?? "Select..."}</span>
                        <svg
                          className={`w-4 h-4 text-gray-400 transition-transform ${dropdownOpen ? "rotate-180" : ""}`}
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </>
                    )
                  })()}
                </button>

                {dropdownOpen && (
                  <div className="absolute top-full left-0 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 py-1">
                    {assistantsData?.assistants.map((assistant) => {
                      const logo = getAssistantLogo(assistant.name)
                      const isSelected = assistant.id === assistantId
                      return (
                        <button
                          key={assistant.id}
                          type="button"
                          onClick={() => {
                            setAssistantId(assistant.id)
                            setDropdownOpen(false)
                          }}
                          className={`
                            w-full px-3 py-2 flex items-center gap-2
                            text-sm font-['DM_Sans'] text-left
                            hover:bg-gray-50 transition-colors
                            ${isSelected ? "bg-gray-50" : ""}
                          `}
                        >
                          {logo && <img src={logo} alt="" className="w-5 h-5" />}
                          <span className={isSelected ? "font-medium" : ""}>{assistant.name}</span>
                          {isSelected && (
                            <svg className="w-4 h-4 ml-auto text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Summary Card - fixed height to prevent layout shift */}
            <div className="px-5 pb-3 shrink-0">
              <div className="p-4 rounded-lg bg-gray-50 border border-gray-100 min-h-[72px]">
                <div className="flex items-center gap-4">
                  {freshCount > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
                      <span className="text-sm text-gray-700 font-['DM_Sans']">
                        <span className="font-medium">{freshCount}</span> prompt
                        {freshCount !== 1 ? "s" : ""} ready
                      </span>
                    </div>
                  )}
                  {needsRefreshCount > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                      <span className="text-sm text-gray-700 font-['DM_Sans']">
                        <span className="font-medium">{needsRefreshCount}</span> need fresh answers
                      </span>
                    </div>
                  )}
                  {pendingCount > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
                      <span className="text-sm text-gray-700 font-['DM_Sans']">
                        <span className="font-medium">{pendingCount}</span> pending
                      </span>
                    </div>
                  )}
                  {totalPrompts === 0 && (
                    <span className="text-sm text-gray-500 font-['DM_Sans']">
                      No prompts in this group
                    </span>
                  )}
                </div>

                {/* Subtle note - always reserve space to prevent layout shift */}
                <p
                  className={`text-xs font-['DM_Sans'] mt-2 transition-opacity ${
                    needsRefreshCount > 0 && !hasPending && !generateSuccess
                      ? "text-gray-500"
                      : "text-transparent select-none"
                  }`}
                >
                  Report will generate automatically when answers are ready
                </p>
              </div>
            </div>

            {/* Success message */}
            {generateSuccess && (
              <div className="mx-5 mb-3 p-4 rounded-lg bg-green-50 border border-green-100 shrink-0">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                    <svg
                      className="w-5 h-5 text-green-600"
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
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-green-800 font-['DM_Sans']">
                      {generateSuccess.requestCreated ? "Report requested" : "Report generated"}
                    </p>
                    <p className="text-xs text-green-700 font-['DM_Sans'] mt-1">
                      {generateSuccess.requestCreated
                        ? "We'll generate your report automatically once all answers are ready"
                        : `${generateSuccess.reportCount} prompt${generateSuccess.reportCount !== 1 ? "s" : ""} included`}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Pending request status */}
            {hasPending && !generateSuccess && pendingRequest && (
              <div className="mx-5 mb-3 p-4 rounded-lg bg-blue-50 border border-blue-100 shrink-0">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                    {isAwaiting || isGenerating ? (
                      <div className="w-4 h-4 border-2 border-blue-400 border-t-blue-600 rounded-full animate-spin" />
                    ) : (
                      <svg
                        className="w-5 h-5 text-blue-600"
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
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-blue-800 font-['DM_Sans']">
                      {isAwaiting && "Waiting for answers..."}
                      {isGenerating && "Generating report..."}
                      {isReady && "Report ready"}
                      {isCompleted && "Report generated!"}
                    </p>
                    <div className="mt-1 text-xs text-blue-700 font-['DM_Sans']">
                      {progress && (
                        <p>
                          {progress.fresh} fresh, {progress.requested} being fetched
                        </p>
                      )}
                      {isCompleted && pendingRequest.report_id && (
                        <p className="mt-1">Your report is ready to view.</p>
                      )}
                    </div>
                    {isAwaiting && (
                      <button
                        onClick={handleCancelRequest}
                        disabled={isCancelling}
                        className="mt-2 text-xs font-medium text-blue-700 hover:text-blue-800 underline underline-offset-2 font-['DM_Sans'] disabled:opacity-50"
                      >
                        {isCancelling ? "Cancelling..." : "Cancel request"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Collapsible Prompt Details */}
            <div className="px-5 shrink-0">
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 font-['DM_Sans'] transition-colors"
              >
                <svg
                  className={`w-4 h-4 transition-transform duration-200 ${showDetails ? "rotate-90" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
                {showDetails ? "Hide" : "Show"} prompt details
              </button>
            </div>

            {/* Expandable prompts list */}
            {showDetails && (
              <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2 prompts-scroll">
                {reportData.prompts.map((prompt) => (
                  <PromptRow key={prompt.prompt_id} prompt={prompt} globalQueueWait={globalQueueWait} />
                ))}
              </div>
            )}

            {/* Spacer when details hidden */}
            {!showDetails && <div className="flex-1 min-h-[16px]" />}

            {/* Duplicate warning */}
            {wouldBeDuplicate && !hasPending && !generateSuccess && (
              <div className="px-5 pb-3">
                <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
                  <p className="text-sm text-amber-800 font-['DM_Sans']">
                    Report would be identical to the most recent one. Wait for new evaluation data.
                  </p>
                </div>
              </div>
            )}

            {/* Footer with actions */}
            <div className="px-5 py-4 border-t border-gray-100 bg-gray-50/50 shrink-0">
              {/* Action buttons */}
              {!generateSuccess && !hasPending && (
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
                    disabled={!canGenerate || isCreating}
                    className="
                      flex-1 py-3 px-4 rounded-lg text-sm font-medium
                      text-white transition-all font-['DM_Sans']
                      disabled:opacity-50 disabled:cursor-not-allowed
                    "
                    style={{ backgroundColor: accentColor }}
                  >
                    {isCreating ? (
                      <span className="flex items-center justify-center gap-2">
                        <div className="w-3.5 h-3.5 border-2 border-white/50 border-t-white rounded-full animate-spin" />
                        Processing...
                      </span>
                    ) : (
                      getButtonText()
                    )}
                  </button>
                </div>
              )}

              {/* Show close button when pending or success */}
              {(hasPending || generateSuccess) && (
                <button
                  onClick={onClose}
                  className="
                    w-full py-3 px-6 rounded-lg text-sm font-medium
                    text-gray-600 bg-gray-100 hover:bg-gray-200
                    transition-colors font-['DM_Sans']
                  "
                >
                  Close
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
