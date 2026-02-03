/**
 * DashboardView - Container component for the Dashboard tab
 * Assembles GroupChipsSelector + AssistantSelector + PeriodSelector + Dashboard cards
 */

import { useState } from "react"
import type { GroupSummary } from "@/types/groups"
import type { DashboardPeriod } from "@/types/dashboard"
import { useDashboardData } from "@/hooks/useDashboardData"
import { useAssistants } from "@/hooks/useAssistants"
import { GroupChipsSelector } from "@/components/citations/GroupChipsSelector"
import { DashboardSkeleton } from "./DashboardSkeleton"
import { BrandVisibilityCard } from "./BrandVisibilityCard"
import { CompetitorsList } from "./CompetitorsList"
import { SourcesLeaderboard } from "./SourcesLeaderboard"
import { PromptGapsList } from "./PromptGapsList"

const PERIOD_OPTIONS = [
  { value: "1d", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
] as const

interface DashboardViewProps {
  groups: GroupSummary[]
  isLoadingGroups: boolean
}

export function DashboardView({ groups, isLoadingGroups }: DashboardViewProps) {
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null)
  const [assistantId, setAssistantId] = useState<number | undefined>(undefined)
  const [period, setPeriod] = useState<DashboardPeriod>("7d")

  const { data: assistantsData, isLoading: isLoadingAssistants } = useAssistants()
  const assistants = assistantsData?.assistants ?? []

  // Auto-select first group when groups load
  if (groups.length > 0 && selectedGroupId === null) {
    setSelectedGroupId(groups[0].id)
  }

  // Set default assistant to first one (usually ChatGPT)
  if (assistants.length > 0 && assistantId === undefined) {
    setAssistantId(assistants[0].id)
  }

  const { data, isLoading } = useDashboardData(selectedGroupId, assistantId, period)

  const hasData = (data?.reports_included ?? 0) > 0

  return (
    <div className="space-y-6">
      {/* Header row: group chips + assistant selector */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <GroupChipsSelector
            groups={groups}
            selectedGroupId={selectedGroupId}
            onSelectGroup={setSelectedGroupId}
            isLoading={isLoadingGroups}
          />
        </div>
        <div className="flex-shrink-0 flex gap-2">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as DashboardPeriod)}
            className="text-[10px] h-6 px-2 py-0.5 rounded border bg-white text-gray-600 focus:outline-none focus:ring-1 cursor-pointer"
            style={{ borderColor: "#C4553D30" }}
          >
            {PERIOD_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            value={assistantId ?? ""}
            onChange={(e) =>
              setAssistantId(e.target.value ? Number(e.target.value) : undefined)
            }
            disabled={isLoadingAssistants}
            className="text-[10px] h-6 px-2 py-0.5 rounded border bg-white text-gray-600 focus:outline-none focus:ring-1 cursor-pointer disabled:opacity-50"
            style={{ borderColor: "#C4553D30" }}
          >
            {assistants.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Report info */}
      {hasData && data && (
        <p className="text-xs text-[#9CA3AF]">
          Based on {data.reports_included} report{data.reports_included > 1 ? "s" : ""} via {data.assistant_name}
        </p>
      )}

      {/* Dashboard cards grid */}
      {isLoading ? (
        <DashboardSkeleton />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <BrandVisibilityCard
            brandName={data?.brand_name ?? null}
            visibilityPercent={data?.brand_visibility_percent ?? 0}
            hasData={hasData}
          />

          <CompetitorsList
            competitors={data?.competitors ?? []}
            hasData={hasData}
          />

          <SourcesLeaderboard
            sources={data?.sources ?? []}
            hasData={hasData}
          />

          <PromptGapsList
            promptGaps={data?.prompt_gaps ?? []}
            totalCount={data?.prompt_gaps_count ?? 0}
            hasData={hasData}
          />
        </div>
      )}

      {/* Empty state when no groups */}
      {!isLoadingGroups && groups.length === 0 && (
        <div className="text-center py-16">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
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
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          </div>
          <h3 className="font-['Fraunces'] text-xl text-[#1F2937] mb-2">
            No groups yet
          </h3>
          <p className="text-sm text-[#6B7280] max-w-sm mx-auto">
            Create a prompt group and generate a report to see your brand visibility analytics.
          </p>
        </div>
      )}
    </div>
  )
}
