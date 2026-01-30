/**
 * SettingsTabs - Vertical navigation for settings page
 * Matches TabSidebar styling from the main dashboard
 */

import { Tag, Lock, Globe } from "lucide-react"

export type SettingsTabId = "brand" | "password" | "gsc"

interface Tab {
  id: SettingsTabId
  label: string
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>
}

const tabs: Tab[] = [
  { id: "brand", label: "Brand", icon: Tag },
  { id: "password", label: "Password", icon: Lock },
  { id: "gsc", label: "GSC", icon: Globe },
]

interface SettingsTabsProps {
  activeTab: SettingsTabId
  onTabChange: (tab: SettingsTabId) => void
}

export function SettingsTabs({ activeTab, onTabChange }: SettingsTabsProps) {
  return (
    <nav className="flex flex-col gap-1">
      {tabs.map(({ id, label, icon: Icon }) => {
        const isActive = activeTab === id
        return (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200
              ${isActive
                ? "bg-[#C4553D] text-white shadow-sm"
                : "text-[#6B7280] hover:bg-gray-100 hover:text-[#1F2937]"
              }`}
          >
            <Icon className="w-5 h-5" strokeWidth={isActive ? 2 : 1.5} />
            <span className="text-sm font-['DM_Sans'] font-medium">
              {label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}
