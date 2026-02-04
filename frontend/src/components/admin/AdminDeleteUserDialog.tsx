/**
 * Confirmation dialog for permanently deleting a user
 */

import { useState } from "react"
import { useAdminDeleteUser } from "@/hooks/useAdminUsers"
import type { UserWithBalance, UserDeletionResponse } from "@/types/admin"

interface AdminDeleteUserDialogProps {
  user: UserWithBalance
  onClose: () => void
  onSuccess: () => void
}

export function AdminDeleteUserDialog({
  user,
  onClose,
  onSuccess,
}: AdminDeleteUserDialogProps) {
  const [confirmEmail, setConfirmEmail] = useState("")
  const [deletionResult, setDeletionResult] = useState<UserDeletionResponse | null>(null)

  const deleteMutation = useAdminDeleteUser()

  const emailMatches = confirmEmail.toLowerCase() === user.email.toLowerCase()

  const handleDelete = async () => {
    deleteMutation.mutate(user.id, {
      onSuccess: (result) => {
        setDeletionResult(result)
      },
    })
  }

  const handleClose = () => {
    if (deletionResult) {
      onSuccess()
    }
    onClose()
  }

  // Success state
  if (deletionResult) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div
          className="bg-white rounded-2xl w-full max-w-md shadow-xl overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Green accent bar for success */}
          <div
            className="h-1 w-full"
            style={{
              background: "linear-gradient(90deg, #22c55e 0%, #16a34a 100%)",
            }}
          />

          <div className="p-6 text-center">
            {/* Success icon */}
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 flex items-center justify-center">
              <svg
                className="w-8 h-8 text-green-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>

            <h2 className="font-['Fraunces'] text-xl font-medium text-gray-900 mb-2">
              User Deleted Successfully
            </h2>

            <p className="text-gray-600 mb-4">
              Deleted {deletionResult.total_records_deleted} records for{" "}
              <span className="font-medium">{deletionResult.user_email}</span>
            </p>

            {/* Deletion details */}
            <div className="bg-gray-50 rounded-xl p-4 mb-6 text-left">
              <ul className="space-y-1 text-sm text-gray-600">
                {deletionResult.details.map((detail) => {
                  const deletedEntries = Object.entries(detail.deleted).filter(
                    ([, count]) => count > 0
                  )
                  return deletedEntries.map(([table, count]) => (
                    <li key={`${detail.database}-${table}`} className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
                      {count} {table.replace(/_/g, " ")}
                    </li>
                  ))
                })}
              </ul>
            </div>

            <button
              onClick={handleClose}
              className="w-full px-4 py-3 bg-gray-900 text-white rounded-xl
                font-medium hover:bg-gray-800 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Confirmation state
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div
        className="bg-white rounded-2xl w-full max-w-md shadow-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Red accent bar for danger */}
        <div
          className="h-1 w-full"
          style={{
            background: "linear-gradient(90deg, #dc2626 0%, #b91c1c 100%)",
          }}
        />

        <div className="p-6">
          {/* Warning icon */}
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-red-600"
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
          </div>

          <h2 className="font-['Fraunces'] text-xl font-medium text-gray-900 mb-2 text-center">
            Delete User Permanently
          </h2>

          <p className="text-gray-600 text-sm mb-4 text-center">
            This will permanently delete:
          </p>

          <ul className="bg-red-50 rounded-xl p-4 mb-4 text-sm text-red-800 space-y-1">
            <li className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              User account and preferences
            </li>
            <li className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              All prompt groups
            </li>
            <li className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              All reports and history
            </li>
          </ul>

          {/* User email display */}
          <div className="bg-gray-50 rounded-xl p-4 mb-4">
            <p className="font-medium text-gray-900 text-center">{user.email}</p>
            {user.full_name && (
              <p className="text-sm text-gray-500 text-center">{user.full_name}</p>
            )}
          </div>

          {/* Confirm email input */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Type email to confirm
            </label>
            <input
              type="email"
              value={confirmEmail}
              onChange={(e) => setConfirmEmail(e.target.value)}
              placeholder={user.email}
              className="w-full px-4 py-3 border border-gray-200 rounded-xl
                focus:ring-2 focus:ring-red-500/20 focus:border-red-500/30
                placeholder:text-gray-400 outline-none transition-all"
              autoComplete="off"
            />
          </div>

          {/* Error message */}
          {deleteMutation.isError && (
            <div className="p-3 mb-4 bg-red-50 rounded-lg border border-red-100 text-red-600 text-sm">
              {deleteMutation.error?.message || "Failed to delete user. Please try again."}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={deleteMutation.isPending}
              className="flex-1 px-4 py-3 border border-gray-200 rounded-xl
                text-gray-700 font-medium hover:bg-gray-50 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={!emailMatches || deleteMutation.isPending}
              className="flex-1 px-4 py-3 bg-red-600 text-white rounded-xl
                font-medium hover:bg-red-700 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {deleteMutation.isPending ? (
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
                  Deleting...
                </span>
              ) : (
                "Delete User"
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
