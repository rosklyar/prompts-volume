/**
 * GroupChipsSelector - Horizontal scrollable row of pill-shaped group chips
 * Used in Citations view to select which group's aggregated citations to display
 */

import type { GroupSummary } from "@/types/groups"
import { getGroupColor } from "@/components/groups/constants"

interface GroupChipsSelectorProps {
  groups: GroupSummary[]
  selectedGroupId: number | null
  onSelectGroup: (groupId: number) => void
  isLoading: boolean
}

export function GroupChipsSelector({
  groups,
  selectedGroupId,
  onSelectGroup,
  isLoading,
}: GroupChipsSelectorProps) {
  if (isLoading) {
    return (
      <div className="flex gap-2 overflow-hidden">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="flex-shrink-0 h-8 w-28 rounded-full bg-gray-100 animate-pulse"
            style={{ animationDelay: `${i * 80}ms` }}
          />
        ))}
      </div>
    )
  }

  if (groups.length === 0) {
    return (
      <p className="text-xs text-[#9CA3AF] italic font-['DM_Sans']">
        No groups created yet
      </p>
    )
  }

  return (
    <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
      {groups.map((group, index) => {
        const isSelected = group.id === selectedGroupId
        const color = getGroupColor(index)

        return (
          <button
            key={group.id}
            onClick={() => onSelectGroup(group.id)}
            className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full
              text-xs font-['DM_Sans'] font-medium transition-all duration-200
              ${isSelected
                ? "text-white shadow-sm"
                : "hover:opacity-80"
              }`}
            style={{
              backgroundColor: isSelected ? color.accent : color.bg,
              color: isSelected ? "#FFFFFF" : color.accent,
              borderWidth: 1,
              borderColor: isSelected ? color.accent : `${color.accent}30`,
            }}
          >
            <span className="truncate max-w-[120px]">{group.title}</span>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                isSelected
                  ? "bg-white/20 text-white"
                  : ""
              }`}
              style={
                isSelected
                  ? undefined
                  : { backgroundColor: `${color.accent}15`, color: color.accent }
              }
            >
              {group.prompt_count}
            </span>
          </button>
        )
      })}
    </div>
  )
}
