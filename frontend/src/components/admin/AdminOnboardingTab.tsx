/**
 * Onboarding notifications tab — shows users who completed onboarding
 * but haven't been set up by admin yet.
 */

import { useState } from "react"
import { ChevronDown, ChevronUp, UserCheck, Eye } from "lucide-react"
import { toast } from "sonner"
import {
  useOnboardingNotifications,
  useMarkUserSetup,
} from "@/hooks/useOnboardingNotifications"
import { useImpersonation } from "@/hooks/useImpersonation"
import type { OnboardingUserInfo } from "@/types/admin"

export function AdminOnboardingTab() {
  const { data, isLoading } = useOnboardingNotifications()
  const markSetup = useMarkUserSetup()
  const { startImpersonation } = useImpersonation()
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const handleMarkSetup = (userId: string) => {
    markSetup.mutate(userId, {
      onSuccess: () => toast.success("User marked as set up"),
      onError: (err) => toast.error(err.message),
    })
  }

  const handleImpersonate = async (user: OnboardingUserInfo) => {
    try {
      await startImpersonation(user.user_id, user.email)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Impersonation failed")
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="w-6 h-6 border-2 border-[#C4553D]/20 border-t-[#C4553D] rounded-full animate-spin" />
      </div>
    )
  }

  if (!data?.users.length) {
    return (
      <div className="text-center py-12">
        <UserCheck className="w-12 h-12 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500">No pending onboarding users</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {data.users.map((user) => {
        const isExpanded = expandedId === user.user_id
        return (
          <div
            key={user.user_id}
            className="bg-white rounded-xl border border-gray-200 overflow-hidden"
          >
            {/* Header row */}
            <button
              onClick={() =>
                setExpandedId(isExpanded ? null : user.user_id)
              }
              className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors"
            >
              <div className="min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {user.email}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Onboarded{" "}
                  {new Date(user.onboarding_completed_at).toLocaleDateString()}
                </p>
              </div>
              {isExpanded ? (
                <ChevronUp className="w-4 h-4 text-gray-400 shrink-0" />
              ) : (
                <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
              )}
            </button>

            {/* Expanded details */}
            {isExpanded && (
              <div className="border-t border-gray-100 px-5 py-4 space-y-4">
                {/* User preferences */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {user.full_name && (
                    <div>
                      <span className="text-gray-400">Name</span>
                      <p className="text-gray-900">{user.full_name}</p>
                    </div>
                  )}
                  {user.country_name && (
                    <div>
                      <span className="text-gray-400">Country</span>
                      <p className="text-gray-900">{user.country_name}</p>
                    </div>
                  )}
                  {user.business_domain_name && (
                    <div>
                      <span className="text-gray-400">Business Domain</span>
                      <p className="text-gray-900">
                        {user.business_domain_name}
                      </p>
                    </div>
                  )}
                  {user.default_brand && (
                    <div>
                      <span className="text-gray-400">Brand</span>
                      <p className="text-gray-900">
                        {user.default_brand.name}
                        {user.default_brand.domain && (
                          <span className="text-gray-400 ml-1">
                            ({user.default_brand.domain})
                          </span>
                        )}
                      </p>
                    </div>
                  )}
                </div>

                {/* Competitors */}
                {user.default_competitors &&
                  user.default_competitors.length > 0 && (
                    <div className="text-sm">
                      <span className="text-gray-400">Competitors</span>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {user.default_competitors.map((c, i) => (
                          <span
                            key={i}
                            className="inline-flex items-center px-2.5 py-0.5 bg-gray-100 text-gray-700 rounded-full text-xs"
                          >
                            {c.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                {/* Action buttons */}
                <div className="flex gap-2 pt-2">
                  <button
                    onClick={() => handleImpersonate(user)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                      border border-blue-200 text-blue-700 hover:bg-blue-50 transition-colors text-sm font-medium"
                  >
                    <Eye className="w-4 h-4" />
                    Impersonate
                  </button>
                  <button
                    onClick={() => handleMarkSetup(user.user_id)}
                    disabled={markSetup.isPending}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                      bg-[#C4553D] text-white hover:bg-[#B04A35] transition-colors text-sm font-medium
                      disabled:opacity-50"
                  >
                    <UserCheck className="w-4 h-4" />
                    Mark as Set Up
                  </button>
                </div>
              </div>
            )}
          </div>
        )
      })}

      {/* Total count */}
      {data.total > data.users.length && (
        <p className="text-center text-sm text-gray-400 pt-2">
          Showing {data.users.length} of {data.total}
        </p>
      )}
    </div>
  )
}
