/**
 * Top-up Page - Add credits to user balance
 * Features mock payment integration for future Stripe implementation
 */

import { createFileRoute, redirect, Link } from "@tanstack/react-router"
import { useState } from "react"
import { isLoggedIn } from "@/hooks/useAuth"
import { useBalance, useTopUp, useTransactions, formatCredits, formatExpirationTime } from "@/hooks/useBilling"

export const Route = createFileRoute("/top-up")({
  component: TopUpPage,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
  },
})

function TopUpPage() {
  const { data: balance, isLoading: isLoadingBalance } = useBalance()
  const { data: transactionsData, isLoading: isLoadingTransactions } = useTransactions(10)
  const topUp = useTopUp()

  const [selectedAmount, setSelectedAmount] = useState<number | null>(25)
  const [customAmount, setCustomAmount] = useState("")
  const [showSuccess, setShowSuccess] = useState(false)
  const [lastTopUp, setLastTopUp] = useState<number | null>(null)

  // Payment form state (mock)
  const [cardNumber, setCardNumber] = useState("")
  const [expiry, setExpiry] = useState("")
  const [cvc, setCvc] = useState("")

  const presetAmounts = [10, 25, 50, 100]
  const hasExpiringSoon = balance && balance.expiring_soon_amount > 0
  const expirationText = balance ? formatExpirationTime(balance.expiring_soon_at) : null

  const effectiveAmount = selectedAmount || (customAmount ? parseFloat(customAmount) : 0)
  const isValidAmount = effectiveAmount > 0

  const handleAmountSelect = (amount: number) => {
    setSelectedAmount(amount)
    setCustomAmount("")
  }

  const handleCustomAmountChange = (value: string) => {
    // Only allow numbers and one decimal point
    const sanitized = value.replace(/[^0-9.]/g, "").replace(/(\..*)\./g, "$1")
    setCustomAmount(sanitized)
    setSelectedAmount(null)
  }

  const handleTopUp = async () => {
    if (!isValidAmount) return

    try {
      await topUp.mutateAsync({ amount: effectiveAmount })
      setLastTopUp(effectiveAmount)
      setShowSuccess(true)
      setSelectedAmount(25)
      setCustomAmount("")
      setCardNumber("")
      setExpiry("")
      setCvc("")

      // Hide success message after delay
      setTimeout(() => setShowSuccess(false), 5000)
    } catch (error) {
      console.error("Top-up failed:", error)
    }
  }

  // Format card number with spaces
  const formatCardNumber = (value: string) => {
    const digits = value.replace(/\D/g, "").slice(0, 16)
    return digits.replace(/(.{4})/g, "$1 ").trim()
  }

  // Format expiry as MM/YY
  const formatExpiry = (value: string) => {
    const digits = value.replace(/\D/g, "").slice(0, 4)
    if (digits.length >= 2) {
      return `${digits.slice(0, 2)}/${digits.slice(2)}`
    }
    return digits
  }

  return (
    <div className="min-h-screen bg-[#FDFBF7] font-['DM_Sans']">
      {/* Header with back link */}
      <header className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-[#C4553D] transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12">
        {/* Page title */}
        <div className="text-center mb-12">
          <h1 className="font-['Fraunces'] text-3xl md:text-4xl font-medium text-[#1F2937] tracking-tight mb-3">
            Add Credits
          </h1>
          <p className="text-gray-500 max-w-md mx-auto">
            Credits are used to load fresh evaluation data in your reports
          </p>
        </div>

        {/* Success message */}
        {showSuccess && lastTopUp && (
          <div
            className="
              mb-8 p-4 rounded-xl bg-green-50 border border-green-100
              flex items-center gap-3 animate-in fade-in slide-in-from-top-2 duration-300
            "
          >
            <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-green-800">
                ${formatCredits(lastTopUp)} added successfully!
              </p>
              <p className="text-sm text-green-600">
                Your new balance is ${formatCredits(balance?.available_balance || 0)}
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Left column - Payment form */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-2xl border border-gray-100 shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)] overflow-hidden">
              {/* Accent bar */}
              <div
                className="h-1 w-full"
                style={{
                  background: "linear-gradient(90deg, #C4553D 0%, #9B4332 100%)",
                }}
              />

              <div className="p-6 md:p-8">
                {/* Amount selection */}
                <div className="mb-8">
                  <label className="block text-xs uppercase tracking-widest text-gray-400 mb-4">
                    Select Amount
                  </label>
                  <div className="grid grid-cols-4 gap-3 mb-4">
                    {presetAmounts.map((amount) => (
                      <button
                        key={amount}
                        onClick={() => handleAmountSelect(amount)}
                        className={`
                          py-4 px-3 rounded-xl text-lg font-medium tabular-nums
                          transition-all duration-200 border-2
                          ${
                            selectedAmount === amount
                              ? "border-[#C4553D] bg-[#C4553D]/5 text-[#C4553D]"
                              : "border-gray-100 hover:border-gray-200 text-gray-700"
                          }
                        `}
                      >
                        ${amount}
                      </button>
                    ))}
                  </div>

                  {/* Custom amount */}
                  <div className="relative">
                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 text-lg">
                      $
                    </span>
                    <input
                      type="text"
                      value={customAmount}
                      onChange={(e) => handleCustomAmountChange(e.target.value)}
                      placeholder="Custom amount"
                      className={`
                        w-full pl-8 pr-4 py-3 rounded-xl border-2 text-lg
                        transition-all duration-200
                        focus:outline-none focus:ring-0
                        ${
                          customAmount
                            ? "border-[#C4553D] bg-[#C4553D]/5"
                            : "border-gray-100 focus:border-gray-200"
                        }
                      `}
                    />
                  </div>
                </div>

                {/* Payment details (mock) */}
                <div className="mb-8">
                  <label className="block text-xs uppercase tracking-widest text-gray-400 mb-4">
                    Payment Details
                  </label>

                  {/* Card number */}
                  <div className="mb-4">
                    <input
                      type="text"
                      value={cardNumber}
                      onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
                      placeholder="4242 4242 4242 4242"
                      className="
                        w-full px-4 py-3 rounded-xl border border-gray-200
                        focus:border-gray-300 focus:outline-none focus:ring-0
                        placeholder:text-gray-300 tabular-nums
                      "
                    />
                  </div>

                  {/* Expiry and CVC */}
                  <div className="grid grid-cols-2 gap-4">
                    <input
                      type="text"
                      value={expiry}
                      onChange={(e) => setExpiry(formatExpiry(e.target.value))}
                      placeholder="MM/YY"
                      className="
                        px-4 py-3 rounded-xl border border-gray-200
                        focus:border-gray-300 focus:outline-none focus:ring-0
                        placeholder:text-gray-300 tabular-nums
                      "
                    />
                    <input
                      type="text"
                      value={cvc}
                      onChange={(e) => setCvc(e.target.value.replace(/\D/g, "").slice(0, 4))}
                      placeholder="CVC"
                      className="
                        px-4 py-3 rounded-xl border border-gray-200
                        focus:border-gray-300 focus:outline-none focus:ring-0
                        placeholder:text-gray-300 tabular-nums
                      "
                    />
                  </div>

                  {/* Mock payment notice */}
                  <p className="mt-3 text-xs text-gray-400 italic">
                    This is a demo payment form. No real charges will be made.
                  </p>
                </div>

                {/* Submit button */}
                <button
                  onClick={handleTopUp}
                  disabled={!isValidAmount || topUp.isPending}
                  className="
                    w-full py-4 rounded-xl text-white font-medium text-lg
                    transition-all duration-200
                    disabled:opacity-50 disabled:cursor-not-allowed
                    bg-[#C4553D] hover:bg-[#9B4332]
                    flex items-center justify-center gap-2
                  "
                >
                  {topUp.isPending ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      Add ${isValidAmount ? formatCredits(effectiveAmount) : "0.00"} Credits
                    </>
                  )}
                </button>

                {/* Error message */}
                {topUp.isError && (
                  <p className="mt-4 text-sm text-red-500 text-center">
                    Failed to add credits. Please try again.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Right column - Balance & History */}
          <div className="lg:col-span-2 space-y-6">
            {/* Current balance */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)] p-6">
              <h3 className="text-xs uppercase tracking-widest text-gray-400 mb-4">
                Current Balance
              </h3>

              {isLoadingBalance ? (
                <div className="h-12 bg-gray-100 rounded animate-pulse" />
              ) : (
                <>
                  <div className="flex items-baseline gap-1 mb-2">
                    <span className="text-gray-400 text-xl font-light">$</span>
                    <span className="text-4xl font-['Fraunces'] font-medium text-[#1F2937] tabular-nums">
                      {formatCredits(balance?.available_balance || 0)}
                    </span>
                  </div>

                  {hasExpiringSoon && expirationText && (
                    <div className="flex items-center gap-2 text-sm text-amber-600 mt-3">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      ${formatCredits(balance?.expiring_soon_amount || 0)} expires {expirationText}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Transaction history */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)] p-6">
              <h3 className="text-xs uppercase tracking-widest text-gray-400 mb-4">
                Recent Activity
              </h3>

              {isLoadingTransactions ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
                  ))}
                </div>
              ) : transactionsData?.transactions && transactionsData.transactions.length > 0 ? (
                <div className="space-y-3">
                  {transactionsData.transactions.slice(0, 5).map((tx) => (
                    <div
                      key={tx.id}
                      className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0"
                    >
                      <div>
                        <p className="text-sm text-gray-700">{tx.reason}</p>
                        <p className="text-xs text-gray-400">
                          {new Date(tx.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <span
                        className={`
                          text-sm font-medium tabular-nums
                          ${tx.type === "credit" ? "text-green-600" : "text-gray-600"}
                        `}
                      >
                        {tx.type === "credit" ? "+" : "-"}${formatCredits(tx.amount)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400 text-center py-4">
                  No transactions yet
                </p>
              )}
            </div>

            {/* Pricing info */}
            <div className="bg-gray-50 rounded-2xl p-6">
              <h3 className="text-xs uppercase tracking-widest text-gray-400 mb-4">
                Pricing
              </h3>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Per evaluation</span>
                  <span className="font-medium text-gray-800">$1.00</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Already loaded</span>
                  <span className="font-medium text-green-600">Free</span>
                </div>
              </div>
              <p className="mt-4 text-xs text-gray-400">
                You only pay for new evaluations. Previously loaded data is always free to access.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
