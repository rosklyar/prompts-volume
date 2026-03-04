/**
 * Tab navigation for admin dashboard
 */

import { Users, FileText, ClipboardCheck, UserCheck, Globe } from "lucide-react"

export type AdminTab = "users" | "prompts" | "approvals" | "onboarding" | "domains"

interface AdminTabsProps {
  activeTab: AdminTab
  onTabChange: (tab: AdminTab) => void
  pendingCount?: number
  onboardingCount?: number
}

function BadgeCount({ count }: { count: number }) {
  if (count <= 0) return null
  return (
    <span className="absolute -top-1 -right-1 min-w-5 h-5 px-1.5 bg-[#C4553D] text-white text-xs font-medium rounded-full flex items-center justify-center">
      {count > 99 ? "99+" : count}
    </span>
  )
}

export function AdminTabs({
  activeTab,
  onTabChange,
  pendingCount,
  onboardingCount,
}: AdminTabsProps) {
  const tabClass = (tab: AdminTab, hasRelBadge = false) =>
    `flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all${
      hasRelBadge ? " relative" : ""
    } ${
      activeTab === tab
        ? "bg-white text-gray-900 shadow-sm"
        : "text-gray-500 hover:text-gray-700"
    }`

  return (
    <div className="flex gap-1 p-1 bg-gray-100 rounded-xl mb-8">
      <button onClick={() => onTabChange("users")} className={tabClass("users")}>
        <Users className="w-4 h-4" />
        Users
      </button>
      <button
        onClick={() => onTabChange("onboarding")}
        className={tabClass("onboarding", true)}
      >
        <UserCheck className="w-4 h-4" />
        Onboarding
        {onboardingCount !== undefined && <BadgeCount count={onboardingCount} />}
      </button>
      <button onClick={() => onTabChange("domains")} className={tabClass("domains")}>
        <Globe className="w-4 h-4" />
        Domains
      </button>
      <button onClick={() => onTabChange("prompts")} className={tabClass("prompts")}>
        <FileText className="w-4 h-4" />
        Prompts
      </button>
      <button
        onClick={() => onTabChange("approvals")}
        className={tabClass("approvals", true)}
      >
        <ClipboardCheck className="w-4 h-4" />
        Approvals
        {pendingCount !== undefined && <BadgeCount count={pendingCount} />}
      </button>
    </div>
  )
}
