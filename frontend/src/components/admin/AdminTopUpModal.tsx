/**
 * Modal for topping up a user's balance
 */

import { useState } from "react"
import { useAdminTopUp } from "@/hooks/useAdminUsers"
import { formatCredits } from "@/hooks/useBilling"
import type { UserWithBalance } from "@/types/admin"

interface AdminTopUpModalProps {
  user: UserWithBalance
  onClose: () => void
  onSuccess: () => void
}

export function AdminTopUpModal({
  user,
  onClose,
  onSuccess,
}: AdminTopUpModalProps) {
  const [amount, setAmount] = useState("")
  const [note, setNote] = useState("")

  const topUpMutation = useAdminTopUp()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const numAmount = parseFloat(amount)
    if (isNaN(numAmount) || numAmount <= 0) return

    topUpMutation.mutate(
      {
        userId: user.id,
        request: {
          amount: numAmount,
          note: note || null,
        },
      },
      {
        onSuccess: () => {
          onSuccess()
          onClose()
        },
      }
    )
  }

  // Quick amount buttons
  const quickAmounts = [10, 25, 50, 100]

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div
        className="bg-white rounded-2xl w-full max-w-md shadow-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Accent bar */}
        <div
          className="h-1 w-full"
          style={{
            background: "linear-gradient(90deg, #C4553D 0%, #9B4332 100%)",
          }}
        />

        <div className="p-6">
          <h2 className="font-['Fraunces'] text-xl font-medium text-gray-900 mb-4">
            Top Up User Balance
          </h2>

          {/* User info */}
          <div className="bg-gray-50 rounded-xl p-4 mb-6">
            <p className="font-medium text-gray-900">{user.email}</p>
            {user.full_name && (
              <p className="text-sm text-gray-500">{user.full_name}</p>
            )}
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-sm text-gray-500">Current balance:</span>
              <span className="font-medium text-gray-900">
                ${formatCredits(user.available_balance)}
              </span>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Quick amount buttons */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Quick amounts
              </label>
              <div className="flex gap-2">
                {quickAmounts.map((quickAmount) => (
                  <button
                    key={quickAmount}
                    type="button"
                    onClick={() => setAmount(quickAmount.toString())}
                    className={`flex-1 py-2 px-3 rounded-lg border text-sm font-medium transition-all
                      ${
                        amount === quickAmount.toString()
                          ? "border-[#C4553D] bg-[#C4553D]/5 text-[#C4553D]"
                          : "border-gray-200 text-gray-600 hover:border-gray-300"
                      }`}
                  >
                    ${quickAmount}
                  </button>
                ))}
              </div>
            </div>

            {/* Custom amount input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Amount
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                  $
                </span>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  className="w-full pl-7 pr-4 py-3 border border-gray-200 rounded-xl
                    focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
                    outline-none transition-all tabular-nums"
                  required
                />
              </div>
            </div>

            {/* Optional note */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Note{" "}
                <span className="text-gray-400 font-normal">(optional)</span>
              </label>
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="e.g., Trial extension, promo credit"
                maxLength={255}
                className="w-full px-4 py-3 border border-gray-200 rounded-xl
                  focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
                  placeholder:text-gray-400 outline-none transition-all"
              />
            </div>

            {/* Error message */}
            {topUpMutation.isError && (
              <div className="p-3 bg-red-50 rounded-lg border border-red-100 text-red-600 text-sm">
                {topUpMutation.error?.message || "Failed to top up. Please try again."}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={topUpMutation.isPending}
                className="flex-1 px-4 py-3 border border-gray-200 rounded-xl
                  text-gray-700 font-medium hover:bg-gray-50 transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={
                  topUpMutation.isPending ||
                  !amount ||
                  parseFloat(amount) <= 0
                }
                className="flex-1 px-4 py-3 bg-[#C4553D] text-white rounded-xl
                  font-medium hover:bg-[#B04A35] transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {topUpMutation.isPending ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg
                      className="animate-spin h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Processing...
                  </span>
                ) : (
                  "Top Up"
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
