/**
 * Tab navigation for admin dashboard
 */

import { Users, FileText } from "lucide-react"

export type AdminTab = "users" | "prompts"

interface AdminTabsProps {
  activeTab: AdminTab
  onTabChange: (tab: AdminTab) => void
}

export function AdminTabs({ activeTab, onTabChange }: AdminTabsProps) {
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
    </div>
  )
}
