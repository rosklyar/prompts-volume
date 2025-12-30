/**
 * BalanceCard - Detailed credits card for the dashboard
 * Shows balance, expiration warnings, and quick top-up options
 */

import { Link } from "@tanstack/react-router"
import { useBalance, useTopUp, formatCredits, formatExpirationTime } from "@/hooks/useBilling"

interface BalanceCardProps {
  className?: string
}

export function BalanceCard({ className = "" }: BalanceCardProps) {
  const { data: balance, isLoading, isError } = useBalance()
  const topUp = useTopUp()

  const isLowBalance = balance && balance.available_balance < 5
  const hasExpiringSoon = balance && balance.expiring_soon_amount > 0
  const expirationText = balance ? formatExpirationTime(balance.expiring_soon_at) : null

  // Quick top-up amounts
  const quickAmounts = [10, 25, 50]

  const handleQuickTopUp = async (amount: number) => {
    try {
      await topUp.mutateAsync({ amount })
    } catch (error) {
      console.error("Top-up failed:", error)
    }
  }

  // Loading skeleton
  if (isLoading) {
    return (
      <div
        className={`
          rounded-2xl bg-white border border-gray-100 p-5
          shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)]
          animate-pulse
          ${className}
        `}
      >
        <div className="h-4 w-24 bg-gray-100 rounded mb-4" />
        <div className="h-10 w-32 bg-gray-100 rounded mb-3" />
        <div className="h-3 w-20 bg-gray-100 rounded" />
      </div>
    )
  }

  // Error state
  if (isError || !balance) {
    return (
      <div
        className={`
          rounded-2xl bg-white border border-red-100 p-5
          shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)]
          ${className}
        `}
      >
        <p className="text-sm text-red-500 font-['DM_Sans']">
          Unable to load balance
        </p>
      </div>
    )
  }

  return (
    <div
      className={`
        rounded-2xl bg-white border border-gray-100 overflow-hidden
        shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)]
        transition-all duration-300 hover:shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)]
        ${className}
      `}
    >
      {/* Accent bar */}
      <div
        className="h-1 w-full"
        style={{
          background: isLowBalance
            ? "linear-gradient(90deg, #F59E0B 0%, #EF4444 100%)"
            : "linear-gradient(90deg, #C4553D 0%, #9B4332 100%)",
        }}
      />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3
            className="text-xs uppercase tracking-widest text-gray-400 font-['DM_Sans'] font-medium"
          >
            Credits balance
          </h3>
          <Link
            to="/top-up"
            className="
              text-xs text-[#C4553D] hover:text-[#9B4332] font-medium
              transition-colors font-['DM_Sans']
            "
          >
            + Add
          </Link>
        </div>

        {/* Balance display */}
        <div className="mb-4">
          <div className="flex items-baseline gap-1">
            <span className="text-gray-400 text-lg font-light">$</span>
            <span
              className={`
                text-3xl font-['Fraunces'] font-medium tabular-nums tracking-tight
                ${isLowBalance ? "text-amber-600" : "text-[#1F2937]"}
              `}
            >
              {formatCredits(balance.available_balance)}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1 font-['DM_Sans']">
            available credits
          </p>
        </div>

        {/* Expiration warning */}
        {hasExpiringSoon && expirationText && (
          <div
            className="
              flex items-start gap-2 p-3 rounded-lg mb-4
              bg-amber-50 border border-amber-100
            "
          >
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
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div className="min-w-0">
              <p className="text-xs font-medium text-amber-800 font-['DM_Sans']">
                ${formatCredits(balance.expiring_soon_amount)} expires {expirationText}
              </p>
              <p className="text-[10px] text-amber-600 mt-0.5 font-['DM_Sans']">
                Use them before they expire
              </p>
            </div>
          </div>
        )}

        {/* Quick top-up buttons */}
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-widest text-gray-300 font-['DM_Sans']">
            Quick top-up
          </p>
          <div className="flex gap-2">
            {quickAmounts.map((amount) => (
              <button
                key={amount}
                onClick={() => handleQuickTopUp(amount)}
                disabled={topUp.isPending}
                className={`
                  flex-1 py-2 px-3 rounded-lg text-sm font-medium
                  transition-all duration-200
                  disabled:opacity-50 disabled:cursor-not-allowed
                  font-['DM_Sans'] tabular-nums
                  ${
                    topUp.isPending
                      ? "bg-gray-100 text-gray-400"
                      : "bg-gray-50 text-gray-600 hover:bg-[#C4553D] hover:text-white"
                  }
                `}
              >
                {topUp.isPending ? (
                  <span className="w-3 h-3 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin mx-auto block" />
                ) : (
                  `$${amount}`
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Success message */}
        {topUp.isSuccess && (
          <div
            className="
              mt-3 text-xs text-center text-green-600 font-['DM_Sans']
              animate-in fade-in duration-300
            "
          >
            Credits added successfully!
          </div>
        )}
      </div>
    </div>
  )
}
