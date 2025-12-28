/**
 * LowBalanceModal - Shown when user can't afford all evaluations
 * Offers partial load option or navigation to top-up
 */

import { Link } from "@tanstack/react-router"
import { formatCredits } from "@/hooks/useBilling"
import type { ReportPreview } from "@/types/billing"

interface LowBalanceModalProps {
  preview: ReportPreview
  accentColor: string
  isOpen: boolean
  onClose: () => void
  onLoadPartial: () => void
}

export function LowBalanceModal({
  preview,
  accentColor,
  isOpen,
  onClose,
  onLoadPartial,
}: LowBalanceModalProps) {
  if (!isOpen) return null

  const shortfall = preview.estimated_cost - preview.user_balance
  const canLoadSome = preview.affordable_count > 0

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
          relative w-full max-w-sm mx-4 bg-white rounded-xl shadow-2xl overflow-hidden
          animate-in fade-in slide-in-from-bottom-4 duration-300
        "
        style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}
      >
        {/* Header accent bar - amber for warning */}
        <div
          className="h-1 w-full"
          style={{
            background: "linear-gradient(90deg, #F59E0B 0%, #D97706 100%)",
          }}
        />

        <div className="p-6">
          {/* Icon and title */}
          <div className="text-center mb-6">
            <div
              className="
                w-14 h-14 rounded-full bg-amber-50 mx-auto mb-4
                flex items-center justify-center
              "
            >
              <svg
                className="w-7 h-7 text-amber-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h2 className="text-xl tracking-tight text-amber-700 mb-2">
              Insufficient Balance
            </h2>
            <p className="text-sm text-gray-500 font-['DM_Sans'] max-w-[260px] mx-auto">
              You need{" "}
              <span className="font-medium text-gray-700">
                ${formatCredits(shortfall)}
              </span>{" "}
              more to load all {preview.fresh_evaluations} evaluations
            </p>
          </div>

          {/* Current balance */}
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500 font-['DM_Sans']">Your balance</span>
              <span className="font-medium text-gray-800 tabular-nums font-['DM_Sans']">
                ${formatCredits(preview.user_balance)}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm mt-2">
              <span className="text-gray-500 font-['DM_Sans']">Required</span>
              <span className="font-medium text-amber-600 tabular-nums font-['DM_Sans']">
                ${formatCredits(preview.estimated_cost)}
              </span>
            </div>
          </div>

          {/* Options */}
          <div className="space-y-3">
            {/* Partial load option */}
            {canLoadSome && (
              <button
                onClick={onLoadPartial}
                className="
                  w-full p-4 rounded-lg text-left
                  bg-gray-50 hover:bg-gray-100 border border-gray-100
                  transition-all duration-200 group
                "
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-800 font-['DM_Sans']">
                    Load {preview.affordable_count} evaluations
                  </span>
                  <span
                    className="
                      text-xs font-medium px-2 py-0.5 rounded-full
                      bg-gray-200 text-gray-600 group-hover:bg-[#C4553D] group-hover:text-white
                      transition-colors
                    "
                  >
                    ${formatCredits(preview.user_balance)}
                  </span>
                </div>
                <p className="text-xs text-gray-400 font-['DM_Sans']">
                  Load what you can afford now
                </p>
              </button>
            )}

            {/* Top-up option */}
            <Link
              to="/top-up"
              onClick={onClose}
              className="
                w-full p-4 rounded-lg text-left block
                border-2 border-dashed transition-all duration-200
                hover:border-solid
              "
              style={{
                borderColor: `${accentColor}40`,
                backgroundColor: `${accentColor}05`,
              }}
            >
              <div className="flex items-center justify-between mb-1">
                <span
                  className="text-sm font-medium font-['DM_Sans']"
                  style={{ color: accentColor }}
                >
                  Add Credits
                </span>
                <svg
                  className="w-4 h-4"
                  style={{ color: accentColor }}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                  />
                </svg>
              </div>
              <p className="text-xs text-gray-400 font-['DM_Sans']">
                Top up to load all evaluations
              </p>
            </Link>
          </div>

          {/* Cancel button */}
          <button
            onClick={onClose}
            className="
              w-full mt-4 py-2.5 text-sm text-gray-500 hover:text-gray-700
              transition-colors font-['DM_Sans']
            "
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
