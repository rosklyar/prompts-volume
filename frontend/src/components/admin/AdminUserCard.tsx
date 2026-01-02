/**
 * User card for admin dashboard
 */

import type { UserWithBalance } from "@/types/admin"
import { formatCredits } from "@/hooks/useBilling"

interface AdminUserCardProps {
  user: UserWithBalance
  onClick: () => void
}

export function AdminUserCard({ user, onClick }: AdminUserCardProps) {
  return (
    <button
      onClick={onClick}
      className="w-full p-4 bg-white rounded-xl border border-gray-100
        shadow-[0_2px_16px_-4px_rgba(0,0,0,0.06)]
        hover:border-[#C4553D]/30 hover:shadow-[0_4px_24px_-4px_rgba(196,85,61,0.1)]
        transition-all duration-200 text-left group"
    >
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <p className="font-medium text-gray-900 group-hover:text-[#C4553D] transition-colors truncate">
            {user.email}
          </p>
          {user.full_name && (
            <p className="text-sm text-gray-500 truncate">{user.full_name}</p>
          )}
          {!user.is_active && (
            <span className="inline-flex items-center px-2 py-0.5 mt-1 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
              Inactive
            </span>
          )}
        </div>
        <div className="text-right ml-4 shrink-0">
          <p className="font-medium text-gray-900 tabular-nums">
            ${formatCredits(user.available_balance)}
          </p>
          {user.expiring_soon_amount > 0 && (
            <p className="text-xs text-amber-600">
              ${formatCredits(user.expiring_soon_amount)} expiring
            </p>
          )}
        </div>
      </div>
    </button>
  )
}
