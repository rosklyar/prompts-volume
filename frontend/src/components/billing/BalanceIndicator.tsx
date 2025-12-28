/**
 * BalanceIndicator - Compact balance display for the header
 * Shows current balance with elegant styling and warning states
 */

import { Link } from "@tanstack/react-router"
import { useBalance, formatCredits, formatExpirationTime } from "@/hooks/useBilling"
import { useState } from "react"

interface BalanceIndicatorProps {
  className?: string
}

export function BalanceIndicator({ className = "" }: BalanceIndicatorProps) {
  const { data: balance, isLoading, isError } = useBalance()
  const [showTooltip, setShowTooltip] = useState(false)

  const isLowBalance = balance && balance.available_balance < 5
  const isCriticalBalance = balance && balance.available_balance < 2
  const hasExpiringSoon = balance && balance.expiring_soon_amount > 0

  // Loading skeleton
  if (isLoading) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="w-16 h-8 bg-gray-100 rounded-lg animate-pulse" />
      </div>
    )
  }

  // Error state - show nothing gracefully
  if (isError || !balance) {
    return null
  }

  const expirationText = formatExpirationTime(balance.expiring_soon_at)

  return (
    <div className={`relative ${className}`}>
      <Link
        to="/top-up"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`
          flex items-center gap-2 px-3 py-1.5 rounded-lg
          transition-all duration-300 group
          ${
            isCriticalBalance
              ? "bg-red-50 hover:bg-red-100 text-red-700"
              : isLowBalance
                ? "bg-amber-50 hover:bg-amber-100 text-amber-700"
                : "bg-gray-50 hover:bg-gray-100 text-gray-700"
          }
        `}
      >
        {/* Coin icon */}
        <span
          className={`
            flex items-center justify-center w-5 h-5 rounded-full
            transition-transform duration-300 group-hover:scale-110
            ${
              isCriticalBalance
                ? "bg-red-200 text-red-600"
                : isLowBalance
                  ? "bg-amber-200 text-amber-600"
                  : "bg-[#C4553D]/20 text-[#C4553D]"
            }
          `}
        >
          <svg
            className="w-3 h-3"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.736 6.979C9.208 6.193 9.696 6 10 6c.304 0 .792.193 1.264.979a1 1 0 001.715-1.029C12.279 4.784 11.232 4 10 4s-2.279.784-2.979 1.95c-.285.475-.507 1-.67 1.55H6a1 1 0 000 2h.013a9.358 9.358 0 000 1H6a1 1 0 100 2h.351c.163.55.385 1.075.67 1.55C7.721 15.216 8.768 16 10 16s2.279-.784 2.979-1.95a1 1 0 10-1.715-1.029c-.472.786-.96.979-1.264.979-.304 0-.792-.193-1.264-.979a4.265 4.265 0 01-.264-.521H10a1 1 0 100-2H8.017a7.36 7.36 0 010-1H10a1 1 0 100-2H8.472c.08-.185.167-.36.264-.521z" />
          </svg>
        </span>

        {/* Balance amount */}
        <span
          className={`
            font-medium text-sm tabular-nums font-['DM_Sans']
            transition-all duration-300
          `}
        >
          ${formatCredits(balance.available_balance)}
        </span>

        {/* Warning indicator dot */}
        {(isLowBalance || hasExpiringSoon) && (
          <span
            className={`
              w-1.5 h-1.5 rounded-full animate-pulse
              ${isCriticalBalance ? "bg-red-500" : "bg-amber-500"}
            `}
          />
        )}
      </Link>

      {/* Tooltip */}
      {showTooltip && (hasExpiringSoon || isLowBalance) && (
        <div
          className="
            absolute right-0 top-full mt-2 z-50
            bg-white rounded-lg shadow-lg border border-gray-100
            px-3 py-2 min-w-[180px]
            animate-in fade-in slide-in-from-top-1 duration-200
          "
        >
          <div className="text-xs text-gray-500 font-['DM_Sans']">
            {hasExpiringSoon && expirationText && (
              <p className="flex items-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-amber-400" />
                <span className="text-amber-700 font-medium">
                  ${formatCredits(balance.expiring_soon_amount)}
                </span>
                <span>expires {expirationText}</span>
              </p>
            )}
            {isLowBalance && (
              <p className="mt-1 text-gray-400 italic">
                Click to add credits
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
