/**
 * CitationsView - Container component for the Citations tab
 * Assembles GroupChipsSelector + CitationFilters + CitationLeaderboardDisplay
 */

import { useState } from "react"
import type { GroupSummary } from "@/types/groups"
import { useCitationsLeaderboard } from "@/hooks/useCitationsLeaderboard"
import { useAssistants } from "@/hooks/useAssistants"
import { getGroupColor } from "@/components/groups/constants"
import { GroupChipsSelector } from "./GroupChipsSelector"
import { CitationFilters } from "./CitationFilters"
import { CitationLeaderboardDisplay } from "./CitationLeaderboardDisplay"

interface CitationsViewProps {
  groups: GroupSummary[]
  isLoadingGroups: boolean
}

export function CitationsView({ groups, isLoadingGroups }: CitationsViewProps) {
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null)
  const [period, setPeriod] = useState<"1d" | "7d" | "30d">("7d")
  const [assistantId, setAssistantId] = useState<number | undefined>(undefined)

  const { data: assistantsData, isLoading: isLoadingAssistants } = useAssistants()
  const assistants = assistantsData?.assistants ?? []

  const { data, isLoading } = useCitationsLeaderboard(
    selectedGroupId,
    period,
    assistantId
  )

  // Auto-select first group when groups load
  if (groups.length > 0 && selectedGroupId === null) {
    setSelectedGroupId(groups[0].id)
  }

  // Determine accent color based on selected group index
  const selectedGroupIndex = groups.findIndex((g) => g.id === selectedGroupId)
  const accentColor =
    selectedGroupIndex >= 0
      ? getGroupColor(selectedGroupIndex).accent
      : "#C4553D"

  return (
    <div className="space-y-6">
      {/* Header row: group chips + filters */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <GroupChipsSelector
            groups={groups}
            selectedGroupId={selectedGroupId}
            onSelectGroup={setSelectedGroupId}
            isLoading={isLoadingGroups}
          />
        </div>
        <CitationFilters
          period={period}
          onPeriodChange={setPeriod}
          assistantId={assistantId}
          onAssistantChange={setAssistantId}
          assistants={assistants}
          isLoadingAssistants={isLoadingAssistants}
        />
      </div>

      {/* Leaderboard display */}
      <CitationLeaderboardDisplay
        data={data}
        isLoading={isLoading}
        accentColor={accentColor}
      />
    </div>
  )
}
