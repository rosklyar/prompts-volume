/**
 * Admin Dashboard - User and prompts management for superusers
 */

import { useState } from "react"
import { createFileRoute, redirect, Link } from "@tanstack/react-router"
import { isLoggedIn } from "@/hooks/useAuth"
import useAuth from "@/hooks/useAuth"
import {
  AdminUserList,
  AdminTopUpModal,
  AdminTabs,
  AdminPromptsTab,
} from "@/components/admin"
import type { UserWithBalance } from "@/types/admin"
import type { AdminTab } from "@/components/admin"

export const Route = createFileRoute("/admin")({
  component: AdminDashboard,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
  },
})

function AdminDashboard() {
  const { user, isUserLoading } = useAuth()
  const [selectedUser, setSelectedUser] = useState<UserWithBalance | null>(null)
  const [showTopUpModal, setShowTopUpModal] = useState(false)
  const [activeTab, setActiveTab] = useState<AdminTab>("users")

  const handleSelectUser = (user: UserWithBalance) => {
    setSelectedUser(user)
    setShowTopUpModal(true)
  }

  const handleTopUpSuccess = () => {
    setShowTopUpModal(false)
    setSelectedUser(null)
  }

  // Loading state
  if (isUserLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFBF7] font-['DM_Sans']">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-[#C4553D]/20 border-t-[#C4553D] rounded-full animate-spin" />
          <span className="text-gray-500 text-sm">Loading...</span>
        </div>
      </div>
    )
  }

  // Access denied for non-superusers
  if (!user?.is_superuser) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFBF7] font-['DM_Sans']">
        <div className="text-center max-w-md px-6">
          {/* Lock icon */}
          <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-gray-100 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
          <h1 className="font-['Fraunces'] text-2xl font-medium text-gray-900 mb-2">
            Access Denied
          </h1>
          <p className="text-gray-500 mb-6">
            You don't have permission to access the admin dashboard.
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#C4553D] text-white rounded-xl
              font-medium hover:bg-[#B04A35] transition-colors"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Return to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#FDFBF7] font-['DM_Sans']">
      {/* Header with back link */}
      <header className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-[#C4553D] transition-colors"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Back to dashboard
          </Link>

          {/* Admin badge */}
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[#C4553D]/10 text-[#C4553D] rounded-full text-xs font-medium">
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
            Admin
          </span>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-12">
        {/* Page title */}
        <div className="text-center mb-10">
          <h1 className="font-['Fraunces'] text-3xl md:text-4xl font-medium text-[#1F2937] tracking-tight mb-3">
            Admin Dashboard
          </h1>
          <p className="text-gray-500 max-w-md mx-auto">
            {activeTab === "users"
              ? "Search and top up user balances"
              : "Upload prompts and manage topics"}
          </p>
        </div>

        {/* Tabs */}
        <AdminTabs activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Tab content */}
        {activeTab === "users" && (
          <AdminUserList onSelectUser={handleSelectUser} />
        )}
        {activeTab === "prompts" && <AdminPromptsTab />}

        {/* Top-up modal */}
        {showTopUpModal && selectedUser && (
          <AdminTopUpModal
            user={selectedUser}
            onClose={() => setShowTopUpModal(false)}
            onSuccess={handleTopUpSuccess}
          />
        )}
      </main>
    </div>
  )
}
