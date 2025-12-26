/**
 * ReportPreviewModal - Shows cost breakdown before generating a report
 * Displays fresh vs already-consumed evaluations and total charge
 */

import { useState, useEffect } from "react"
import { useReportPreview, formatCredits } from "@/hooks/useBilling"
import type { ReportPreview } from "@/types/billing"

interface ReportPreviewModalProps {
  groupId: number
  groupTitle: string
  accentColor: string
  isOpen: boolean
  onClose: () => void
  onConfirm: (includePrevious: boolean) => void
  onNeedsTopUp?: (preview: ReportPreview) => void
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
  const [includePrevious, setIncludePrevious] = useState(true)
  const { data: preview, isLoading, isError, refetch } = useReportPreview(groupId, isOpen)

  // Refetch when modal opens
  useEffect(() => {
    if (isOpen) {
      refetch()
    }
  }, [isOpen, refetch])

  if (!isOpen) return null

  const handleConfirm = () => {
    if (preview?.needs_top_up && onNeedsTopUp) {
      onNeedsTopUp(preview)
    } else {
      onConfirm(includePrevious)
    }
  }

  const isFree = preview && preview.estimated_cost === 0
  const canAfford = preview && !preview.needs_top_up

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
          relative w-full max-w-md mx-4 bg-white rounded-xl shadow-2xl overflow-hidden
          animate-in fade-in slide-in-from-bottom-4 duration-300
        "
        style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}
      >
        {/* Header accent bar */}
        <div className="h-1 w-full" style={{ backgroundColor: accentColor }} />

        <div className="p-6">
          {/* Title */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl tracking-tight" style={{ color: accentColor }}>
                Generate Report
              </h2>
              <p className="text-sm text-gray-400 mt-1 font-['DM_Sans'] truncate max-w-[280px]">
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

          {/* Loading state */}
          {isLoading && (
            <div className="py-8 text-center">
              <div
                className="w-8 h-8 border-2 rounded-full animate-spin mx-auto mb-3"
                style={{
                  borderColor: `${accentColor}30`,
                  borderTopColor: accentColor,
                }}
              />
              <p className="text-sm text-gray-400 font-['DM_Sans']">
                Calculating costs...
              </p>
            </div>
          )}

          {/* Error state */}
          {isError && (
            <div className="py-8 text-center">
              <p className="text-sm text-red-500 font-['DM_Sans'] mb-3">
                Failed to load preview
              </p>
              <button
                onClick={() => refetch()}
                className="text-sm text-[#C4553D] hover:underline font-['DM_Sans']"
              >
                Try again
              </button>
            </div>
          )}

          {/* Preview content */}
          {preview && !isLoading && (
            <>
              {/* Cost breakdown */}
              <div className="space-y-3 mb-6">
                <p className="text-xs uppercase tracking-widest text-gray-400 font-['DM_Sans']">
                  Cost Breakdown
                </p>

                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                  {/* Fresh evaluations */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: accentColor }}
                      />
                      <span className="text-sm text-gray-700 font-['DM_Sans']">
                        Fresh evaluations
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-medium text-gray-800 font-['DM_Sans'] tabular-nums">
                        {preview.fresh_evaluations} × $1.00
                      </span>
                      <span className="text-sm text-gray-500 font-['DM_Sans'] ml-2">
                        = ${formatCredits(preview.estimated_cost)}
                      </span>
                    </div>
                  </div>

                  {/* Already consumed */}
                  {preview.already_consumed > 0 && (
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-green-400" />
                        <span className="text-sm text-gray-700 font-['DM_Sans']">
                          Already included
                        </span>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-medium text-green-600 font-['DM_Sans']">
                          {preview.already_consumed}
                        </span>
                        <span className="text-sm text-green-500 font-['DM_Sans'] ml-2">
                          FREE
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Awaiting data */}
                  {preview.prompts_awaiting > 0 && (
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-gray-300" />
                        <span className="text-sm text-gray-500 font-['DM_Sans']">
                          Awaiting data
                        </span>
                      </div>
                      <span className="text-sm text-gray-400 font-['DM_Sans']">
                        {preview.prompts_awaiting}
                      </span>
                    </div>
                  )}

                  {/* Divider */}
                  <div className="border-t border-gray-200 pt-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-800">
                        Total charge
                      </span>
                      <span
                        className="text-lg font-semibold tabular-nums font-['DM_Sans']"
                        style={{ color: isFree ? "#10B981" : accentColor }}
                      >
                        {isFree ? "FREE" : `$${formatCredits(preview.estimated_cost)}`}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Balance info */}
              <div
                className={`
                  flex items-center justify-between p-3 rounded-lg mb-6
                  ${preview.needs_top_up ? "bg-amber-50 border border-amber-100" : "bg-gray-50"}
                `}
              >
                <span className="text-sm text-gray-600 font-['DM_Sans']">
                  Your balance
                </span>
                <span
                  className={`
                    text-sm font-medium tabular-nums font-['DM_Sans']
                    ${preview.needs_top_up ? "text-amber-600" : "text-gray-800"}
                  `}
                >
                  ${formatCredits(preview.user_balance)}
                </span>
              </div>

              {/* Include previous checkbox */}
              {preview.already_consumed > 0 && (
                <label className="flex items-center gap-3 mb-6 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={includePrevious}
                    onChange={(e) => setIncludePrevious(e.target.checked)}
                    className="
                      w-4 h-4 rounded border-gray-300
                      text-[#C4553D] focus:ring-[#C4553D]/20
                    "
                  />
                  <span className="text-sm text-gray-600 font-['DM_Sans'] group-hover:text-gray-800 transition-colors">
                    Include previously loaded data
                  </span>
                </label>
              )}

              {/* Low balance warning */}
              {preview.needs_top_up && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-100 mb-6">
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
                      You can load {preview.affordable_count} of {preview.fresh_evaluations} evaluations
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
                  disabled={!canAfford && !onNeedsTopUp}
                  className={`
                    flex-1 py-3 px-4 rounded-lg text-sm font-medium
                    text-white transition-all font-['DM_Sans']
                    disabled:opacity-50 disabled:cursor-not-allowed
                    ${isFree ? "bg-green-500 hover:bg-green-600" : ""}
                  `}
                  style={{
                    backgroundColor: isFree ? undefined : accentColor,
                  }}
                >
                  {preview.needs_top_up ? (
                    "View Options"
                  ) : isFree ? (
                    "Generate Free"
                  ) : (
                    <>Generate — ${formatCredits(preview.estimated_cost)}</>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
