/**
 * Top-up Page - Pricing and contact information
 */

import { createFileRoute, redirect, Link } from "@tanstack/react-router"
import { isLoggedIn } from "@/hooks/useAuth"
import { useBalance, formatCredits, formatExpirationTime } from "@/hooks/useBilling"

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

  const hasExpiringSoon = balance && balance.expiring_soon_amount > 0
  const expirationText = balance ? formatExpirationTime(balance.expiring_soon_at) : null

  return (
    <div className="min-h-screen bg-[#FDFBF7] font-['DM_Sans']">
      {/* Header with back link */}
      <header className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-[#C4553D] transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to dashboard
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12">
        {/* Page title */}
        <div className="text-center mb-12">
          <h1 className="font-['Fraunces'] text-3xl md:text-4xl font-medium text-[#1F2937] tracking-tight mb-3">
            Top up your balance
          </h1>
          <p className="text-gray-500 max-w-md mx-auto">
            Contact us to add credits to your account
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Current balance */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)] p-6">
            <h3 className="text-xs uppercase tracking-widest text-gray-400 mb-4">
              Current balance
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

          {/* Pricing info */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)] p-6">
            <h3 className="text-xs uppercase tracking-widest text-gray-400 mb-4">
              Pricing
            </h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Per answer</span>
                <span className="font-medium text-gray-800">$0.01</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Already loaded</span>
                <span className="font-medium text-green-600">Free</span>
              </div>
            </div>
            <p className="mt-4 text-xs text-gray-400">
              You only pay for new answers. Previously loaded data is always free to access.
            </p>
          </div>
        </div>

        {/* Contact section */}
        <div className="mt-8 bg-white rounded-2xl border border-gray-100 shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)] overflow-hidden">
          {/* Accent bar */}
          <div
            className="h-1 w-full"
            style={{
              background: "linear-gradient(90deg, #C4553D 0%, #9B4332 100%)",
            }}
          />

          <div className="p-6 md:p-8">
            <h3 className="text-xs uppercase tracking-widest text-gray-400 mb-6">
              Contact us to top up
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Email */}
              <a
                href="mailto:llmheroai@gmail.com"
                className="flex items-center gap-4 p-4 rounded-xl border border-gray-100 hover:border-[#C4553D]/30 hover:bg-[#C4553D]/5 transition-all group"
              >
                <div className="w-10 h-10 rounded-full bg-gray-100 group-hover:bg-[#C4553D]/10 flex items-center justify-center shrink-0 transition-colors">
                  <svg className="w-5 h-5 text-gray-500 group-hover:text-[#C4553D] transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Email</p>
                  <p className="text-sm text-gray-700 group-hover:text-[#C4553D] transition-colors truncate">
                    llmheroai@gmail.com
                  </p>
                </div>
              </a>

              {/* Telegram */}
              <a
                href="https://t.me/rostyslav_skliar"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-4 p-4 rounded-xl border border-gray-100 hover:border-[#C4553D]/30 hover:bg-[#C4553D]/5 transition-all group"
              >
                <div className="w-10 h-10 rounded-full bg-gray-100 group-hover:bg-[#C4553D]/10 flex items-center justify-center shrink-0 transition-colors">
                  <svg className="w-5 h-5 text-gray-500 group-hover:text-[#C4553D] transition-colors" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                  </svg>
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Telegram</p>
                  <p className="text-sm text-gray-700 group-hover:text-[#C4553D] transition-colors">
                    @rostyslav_skliar
                  </p>
                </div>
              </a>

              {/* WhatsApp */}
              <a
                href="https://wa.me/380667683288"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-4 p-4 rounded-xl border border-gray-100 hover:border-[#C4553D]/30 hover:bg-[#C4553D]/5 transition-all group"
              >
                <div className="w-10 h-10 rounded-full bg-gray-100 group-hover:bg-[#C4553D]/10 flex items-center justify-center shrink-0 transition-colors">
                  <svg className="w-5 h-5 text-gray-500 group-hover:text-[#C4553D] transition-colors" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                  </svg>
                </div>
                <div className="min-w-0">
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">WhatsApp</p>
                  <p className="text-sm text-gray-700 group-hover:text-[#C4553D] transition-colors">
                    +380 66 768 3288
                  </p>
                </div>
              </a>
            </div>

            <p className="mt-6 text-sm text-gray-500 text-center">
              We typically respond within a few hours during business hours.
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
