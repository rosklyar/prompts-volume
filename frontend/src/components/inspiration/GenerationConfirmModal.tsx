/**
 * GenerationConfirmModal - Shows price confirmation before generating prompts
 * Displays price, balance, and handles insufficient balance scenario
 */

import { useEffect } from "react"
import { Link } from "@tanstack/react-router"
import { useGenerationPrice, formatCredits } from "@/hooks/useBilling"

interface GenerationConfirmModalProps {
  isOpen: boolean
  topicsCount: number
  onClose: () => void
  onConfirm: () => void
  onNeedsTopUp: () => void
}

export function GenerationConfirmModal({
  isOpen,
  topicsCount,
  onClose,
  onConfirm,
  onNeedsTopUp,
}: GenerationConfirmModalProps) {
  const { data: priceInfo, isLoading, isError, refetch } = useGenerationPrice(isOpen)

  // Refetch when modal opens
  useEffect(() => {
    if (isOpen) {
      refetch()
    }
  }, [isOpen, refetch])

  if (!isOpen) return null

  const canAfford = priceInfo?.can_afford ?? false

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
        <div className="h-1 w-full bg-violet-500" />

        <div className="p-6">
          {/* Title */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl tracking-tight text-violet-600">
                Generate prompts
              </h2>
              <p className="text-sm text-gray-400 mt-1 font-['DM_Sans']">
                {topicsCount} topic{topicsCount !== 1 ? "s" : ""} selected
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
                className="w-8 h-8 border-2 rounded-full animate-spin mx-auto mb-3 border-violet-200 border-t-violet-500"
              />
              <p className="text-sm text-gray-400 font-['DM_Sans']">
                Checking balance...
              </p>
            </div>
          )}

          {/* Error state */}
          {isError && (
            <div className="py-8 text-center">
              <p className="text-sm text-red-500 font-['DM_Sans'] mb-3">
                Failed to load pricing
              </p>
              <button
                onClick={() => refetch()}
                className="text-sm text-violet-500 hover:underline font-['DM_Sans']"
              >
                Try again
              </button>
            </div>
          )}

          {/* Price content */}
          {priceInfo && !isLoading && (
            <>
              {/* Cost breakdown */}
              <div className="space-y-3 mb-6">
                <p className="text-xs uppercase tracking-widest text-gray-400 font-['DM_Sans']">
                  Cost
                </p>

                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                  {/* Generation cost */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-violet-500" />
                      <span className="text-sm text-gray-700 font-['DM_Sans']">
                        Prompt generation
                      </span>
                    </div>
                    <span className="text-sm font-medium text-gray-800 font-['DM_Sans'] tabular-nums">
                      ${formatCredits(priceInfo.price)}
                    </span>
                  </div>

                  {/* Divider */}
                  <div className="border-t border-gray-200 pt-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-800">
                        Total charge
                      </span>
                      <span className="text-lg font-semibold tabular-nums font-['DM_Sans'] text-violet-600">
                        ${formatCredits(priceInfo.price)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Balance info */}
              <div
                className={`
                  flex items-center justify-between p-3 rounded-lg mb-6
                  ${!canAfford ? "bg-amber-50 border border-amber-100" : "bg-gray-50"}
                `}
              >
                <span className="text-sm text-gray-600 font-['DM_Sans']">
                  Your balance
                </span>
                <span
                  className={`
                    text-sm font-medium tabular-nums font-['DM_Sans']
                    ${!canAfford ? "text-amber-600" : "text-gray-800"}
                  `}
                >
                  ${formatCredits(priceInfo.user_balance)}
                </span>
              </div>

              {/* Low balance warning */}
              {!canAfford && (
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
                      Please add credits to continue
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
                {canAfford ? (
                  <button
                    onClick={onConfirm}
                    className="
                      flex-1 py-3 px-4 rounded-lg text-sm font-medium
                      text-white transition-all font-['DM_Sans']
                      bg-violet-500 hover:bg-violet-600
                    "
                  >
                    Generate — ${formatCredits(priceInfo.price)}
                  </button>
                ) : (
                  <Link
                    to="/top-up"
                    onClick={onNeedsTopUp}
                    className="
                      flex-1 py-3 px-4 rounded-lg text-sm font-medium text-center
                      text-white transition-all font-['DM_Sans']
                      bg-amber-500 hover:bg-amber-600
                    "
                  >
                    Add credits
                  </Link>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
