/**
 * Modal showing user info and available admin actions
 */

import { formatCredits } from "@/hooks/useBilling"
import type { UserWithBalance } from "@/types/admin"

interface AdminUserActionsModalProps {
  user: UserWithBalance
  onClose: () => void
  onTopUp: () => void
  onDelete: () => void
}

export function AdminUserActionsModal({
  user,
  onClose,
  onTopUp,
  onDelete,
}: AdminUserActionsModalProps) {
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
            User Actions
          </h2>

          {/* User info card */}
          <div className="bg-gray-50 rounded-xl p-4 mb-6">
            <p className="font-medium text-gray-900">{user.email}</p>
            {user.full_name && (
              <p className="text-sm text-gray-500">{user.full_name}</p>
            )}
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-sm text-gray-500">Balance:</span>
              <span className="font-medium text-gray-900">
                ${formatCredits(user.available_balance)}
              </span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            {/* Top Up button */}
            <button
              onClick={onTopUp}
              className="flex flex-col items-center gap-2 p-4 rounded-xl border border-gray-200
                hover:border-green-300 hover:bg-green-50 transition-all group"
            >
              <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center
                group-hover:bg-green-200 transition-colors">
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
                    d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                  />
                </svg>
              </div>
              <span className="text-sm font-medium text-gray-700 group-hover:text-green-700">
                Top Up Balance
              </span>
            </button>

            {/* Delete button */}
            <button
              onClick={onDelete}
              className="flex flex-col items-center gap-2 p-4 rounded-xl border border-gray-200
                hover:border-red-300 hover:bg-red-50 transition-all group"
            >
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center
                group-hover:bg-red-200 transition-colors">
                <svg
                  className="w-5 h-5 text-red-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
              </div>
              <span className="text-sm font-medium text-gray-700 group-hover:text-red-700">
                Delete User
              </span>
            </button>
          </div>

          {/* Cancel button */}
          <button
            onClick={onClose}
            className="w-full px-4 py-3 border border-gray-200 rounded-xl
              text-gray-700 font-medium hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
