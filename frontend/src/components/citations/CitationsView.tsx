/**
 * CitationsView - Container component for the Citations tab
 * Assembles GroupChipsSelector + CitationFilters + CitationLeaderboardDisplay
 */

import { useState, useMemo, useEffect } from "react"
import type { GroupSummary } from "@/types/groups"
import type { DashboardPeriod } from "@/types/dashboard"
import type { DateRange } from "@/types/date-range"
import { useCitationsLeaderboard, type CitationsDateRangeOption } from "@/hooks/useCitationsLeaderboard"
import { useAssistants } from "@/hooks/useAssistants"
import { getGroupColor } from "@/components/groups/constants"
import { GroupChipsSelector } from "./GroupChipsSelector"
import { CitationFilters } from "./CitationFilters"
import { CitationLeaderboardDisplay } from "./CitationLeaderboardDisplay"

interface CitationsViewProps {
  groups: GroupSummary[]
  isLoadingGroups: boolean
  activePreset: DashboardPeriod | null
  dateRange: DateRange | null
  assistantId: number | undefined
  setAssistantId: (id: number | undefined) => void
  handleDateRangeChange: (range: DateRange, preset: string | null) => void
}

export function CitationsView({ groups, isLoadingGroups, activePreset, dateRange, assistantId, setAssistantId, handleDateRangeChange }: CitationsViewProps) {
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null)

  const { data: assistantsData, isLoading: isLoadingAssistants } = useAssistants()
  const assistants = useMemo(() => assistantsData?.assistants ?? [], [assistantsData?.assistants])

  // Convert date range state to API option
  const dateRangeOption: CitationsDateRangeOption = useMemo(() => {
    if (activePreset) {
      return { period: activePreset }
    }
    if (dateRange) {
      return {
        fromDate: dateRange.from.toISOString(),
        toDate: dateRange.to.toISOString(),
      }
    }
    // Default to 30d
    return { period: "30d" }
  }, [activePreset, dateRange])

  const { data, isLoading } = useCitationsLeaderboard(
    selectedGroupId,
    dateRangeOption,
    assistantId
  )

  // Auto-select first group when groups load
  if (groups.length > 0 && selectedGroupId === null) {
    setSelectedGroupId(groups[0].id)
  }

  // Validate stored assistant exists in current list, otherwise reset to first
  useEffect(() => {
    if (assistants.length === 0) return
    if (assistantId === undefined) {
      setAssistantId(assistants[0].id)
    } else {
      const exists = assistants.some(a => a.id === assistantId)
      if (!exists) {
        setAssistantId(assistants[0].id)
      }
    }
  }, [assistants, assistantId, setAssistantId])

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
          dateRange={dateRange}
          activePreset={activePreset}
          onDateRangeChange={handleDateRangeChange}
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
