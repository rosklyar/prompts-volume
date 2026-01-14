/**
 * Tab navigation for admin dashboard
 */

import { Users, FileText, ClipboardCheck } from "lucide-react"

export type AdminTab = "users" | "prompts" | "approvals"

interface AdminTabsProps {
  activeTab: AdminTab
  onTabChange: (tab: AdminTab) => void
  pendingCount?: number
}

export function AdminTabs({ activeTab, onTabChange, pendingCount }: AdminTabsProps) {
  return (
    <div className="flex gap-1 p-1 bg-gray-100 rounded-xl mb-8">
      <button
        onClick={() => onTabChange("users")}
        className={`flex-1 flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg text-sm font-medium transition-all
          ${
            activeTab === "users"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
      >
        <Users className="w-4 h-4" />
        Users
      </button>
      <button
        onClick={() => onTabChange("prompts")}
        className={`flex-1 flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg text-sm font-medium transition-all
          ${
            activeTab === "prompts"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
      >
        <FileText className="w-4 h-4" />
        Prompts
      </button>
      <button
        onClick={() => onTabChange("approvals")}
        className={`flex-1 flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg text-sm font-medium transition-all relative
          ${
            activeTab === "approvals"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
      >
        <ClipboardCheck className="w-4 h-4" />
        Approvals
        {pendingCount !== undefined && pendingCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-5 h-5 px-1.5 bg-[#C4553D] text-white text-xs font-medium rounded-full flex items-center justify-center">
            {pendingCount > 99 ? "99+" : pendingCount}
          </span>
        )}
      </button>
    </div>
  )
}
