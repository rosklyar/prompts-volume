/**
 * ReportHistoryPanel - Horizontal timeline of previously generated reports
 * Allows selecting a report to view its details
 * Supports filtering by time period and AI assistant
 */

import { useMemo, useState } from "react"
import { useReportHistory, formatReportTime, type ReportHistoryFilters } from "@/hooks/useReports"
import { formatCredits } from "@/hooks/useBilling"
import { getAssistantLogo } from "@/utils/assistantLogos"
import { useAssistants } from "@/hooks/useAssistants"

type TimeFilterOption = "all" | "7d" | "30d" | "90d"

const TIME_FILTER_OPTIONS: { value: TimeFilterOption; label: string }[] = [
  { value: "all", label: "All time" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
]

function getFromDateForFilter(filter: TimeFilterOption): string | undefined {
  if (filter === "all") return undefined
  const now = new Date()
  const days = filter === "7d" ? 7 : filter === "30d" ? 30 : 90
  now.setDate(now.getDate() - days)
  return now.toISOString()
}

interface ReportHistoryPanelProps {
  groupId: number
  selectedReportId: number | null
  onSelectReport: (reportId: number | null) => void
  onDoubleClickReport: (reportId: number) => void
  accentColor: string
}

export function ReportHistoryPanel({
  groupId,
  selectedReportId,
  onSelectReport,
  onDoubleClickReport,
  accentColor,
}: ReportHistoryPanelProps) {
  // Filter state
  const [timeFilter, setTimeFilter] = useState<TimeFilterOption>("all")
  const [assistantFilter, setAssistantFilter] = useState<number | undefined>(undefined)

  // Get available assistants for filter dropdown
  const { data: assistantsData } = useAssistants()
  const assistants = assistantsData?.assistants ?? []

  // Build filters object
  const filters: ReportHistoryFilters | undefined = useMemo(() => {
    const fromDate = getFromDateForFilter(timeFilter)
    if (!fromDate && assistantFilter === undefined) return undefined
    return {
      assistantId: assistantFilter,
      fromDate,
    }
  }, [timeFilter, assistantFilter])

  const { data: historyData, isLoading, error } = useReportHistory(groupId, true, 20, 0, filters)

  const reports = historyData?.reports ?? []
  const hasReports = reports.length > 0

  // Handle report card click - switch to another report (no deselection)
  const handleCardClick = (reportId: number) => {
    if (selectedReportId !== reportId) {
      onSelectReport(reportId)
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="mt-3">
        <div className="flex items-center gap-2 mb-2">
          <div
            className="w-1 h-4 rounded-full"
            style={{ backgroundColor: accentColor }}
          />
          <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-400">
            Reports
          </span>
        </div>
        <div className="flex gap-2 overflow-hidden">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex-shrink-0 w-[175px] h-[72px] rounded-lg bg-gray-100 animate-pulse"
              style={{ animationDelay: `${i * 100}ms` }}
            />
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return null
  }

  const hasFiltersApplied = timeFilter !== "all" || assistantFilter !== undefined

  // Empty state
  if (!hasReports) {
    return (
      <div className="mt-3">
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <div
              className="w-1 h-4 rounded-full opacity-40"
              style={{ backgroundColor: accentColor }}
            />
            <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-300">
              Reports
            </span>
          </div>

          {/* Show filters even in empty state if filters were applied */}
          {hasFiltersApplied && (
            <div className="flex items-center gap-2">
              <select
                value={timeFilter}
                onChange={(e) => setTimeFilter(e.target.value as TimeFilterOption)}
                className="text-[10px] h-6 px-2 py-0.5 rounded border bg-white text-gray-600 focus:outline-none focus:ring-1 cursor-pointer"
                style={{ borderColor: `${accentColor}30` }}
              >
                {TIME_FILTER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>

              <select
                value={assistantFilter ?? ""}
                onChange={(e) => setAssistantFilter(e.target.value ? Number(e.target.value) : undefined)}
                className="text-[10px] h-6 px-2 py-0.5 rounded border bg-white text-gray-600 focus:outline-none focus:ring-1 cursor-pointer"
                style={{ borderColor: `${accentColor}30` }}
              >
                <option value="">All assistants</option>
                {assistants.map((assistant) => (
                  <option key={assistant.id} value={assistant.id}>
                    {assistant.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
        <div
          className="flex items-center justify-center py-4 rounded-lg border border-dashed"
          style={{ borderColor: `${accentColor}20` }}
        >
          <p className="text-xs text-gray-400 italic">
            {hasFiltersApplied ? "No reports match the selected filters" : "No reports generated yet"}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-3">
      {/* Section header with filters */}
      <div className="flex items-center justify-between mb-2 gap-2">
        <div className="flex items-center gap-2">
          <div
            className="w-1 h-4 rounded-full"
            style={{ backgroundColor: accentColor }}
          />
          <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-400">
            Reports
          </span>
          <span
            className="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
            style={{
              backgroundColor: `${accentColor}15`,
              color: accentColor,
            }}
          >
            {historyData?.total ?? reports.length}
          </span>
        </div>

        {/* Filter dropdowns */}
        <div className="flex items-center gap-2">
          {/* Time filter */}
          <select
            value={timeFilter}
            onChange={(e) => setTimeFilter(e.target.value as TimeFilterOption)}
            className="text-[10px] h-6 px-2 py-0.5 rounded border bg-white text-gray-600 focus:outline-none focus:ring-1 cursor-pointer"
            style={{ borderColor: `${accentColor}30` }}
          >
            {TIME_FILTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Assistant filter */}
          <select
            value={assistantFilter ?? ""}
            onChange={(e) => setAssistantFilter(e.target.value ? Number(e.target.value) : undefined)}
            className="text-[10px] h-6 px-2 py-0.5 rounded border bg-white text-gray-600 focus:outline-none focus:ring-1 cursor-pointer"
            style={{ borderColor: `${accentColor}30` }}
          >
            <option value="">All assistants</option>
            {assistants.map((assistant) => (
              <option key={assistant.id} value={assistant.id}>
                {assistant.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Horizontal scrollable timeline */}
      <div
        className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1"
        style={{
          scrollbarWidth: "thin",
          scrollbarColor: `${accentColor}30 transparent`,
        }}
      >
        {reports.map((report) => {
          const isSelected = selectedReportId === report.id

          return (
            <button
              key={report.id}
              onClick={() => handleCardClick(report.id)}
              onDoubleClick={() => onDoubleClickReport(report.id)}
              className={`
                flex-shrink-0 relative group
                w-[175px] px-3 py-2.5 rounded-lg
                text-left transition-all duration-200
                hover:shadow-md
                ${isSelected ? "shadow-md" : "hover:scale-[1.02]"}
              `}
              style={{
                backgroundColor: isSelected ? `${accentColor}08` : "white",
                borderWidth: isSelected ? "2px" : "1px",
                borderColor: isSelected ? accentColor : `${accentColor}20`,
                boxShadow: isSelected ? `0 0 0 2px ${accentColor}40` : undefined,
              }}
            >
              {/* Selected indicator dot */}
              {isSelected && (
                <div
                  className="absolute top-2 left-2 w-1.5 h-1.5 rounded-full animate-pulse"
                  style={{ backgroundColor: accentColor }}
                />
              )}

              {/* Assistant badge row */}
              {(() => {
                const assistantName = report.assistant_name || "ChatGPT"
                const logo = getAssistantLogo(assistantName)
                return (
                  <div className="flex items-center gap-1.5 mb-1">
                    {logo ? (
                      <img
                        src={logo}
                        alt={assistantName}
                        className="w-4 h-4"
                      />
                    ) : (
                      <span
                        className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold"
                        style={{
                          backgroundColor: isSelected ? `${accentColor}20` : "#e5e7eb",
                          color: isSelected ? accentColor : "#6b7280",
                        }}
                      >
                        {assistantName.charAt(0)}
                      </span>
                    )}
                    <span
                      className="text-[10px] font-medium"
                      style={{ color: isSelected ? accentColor : "#6b7280" }}
                    >
                      {assistantName}
                    </span>
                  </div>
                )
              })()}

              {/* Timestamp row */}
              <p
                className="text-xs font-medium truncate mb-1"
                style={{ color: isSelected ? accentColor : "#374151" }}
              >
                {formatReportTime(report.created_at)}
              </p>

              {/* Stats row */}
              <div className="flex items-center gap-2 text-[10px] text-gray-500">
                {/* Prompts with data */}
                <div className="flex items-center gap-1">
                  <svg className="w-3 h-3 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="tabular-nums">
                    {report.prompts_with_data}/{report.total_prompts}
                  </span>
                </div>

                {/* Cost */}
                <div className="flex items-center gap-0.5">
                  <span className="opacity-60">$</span>
                  <span className="tabular-nums font-medium">
                    {formatCredits(report.total_cost)}
                  </span>
                </div>
              </div>

              {/* Subtle hover effect overlay */}
              <div
                className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
                style={{
                  background: `linear-gradient(135deg, ${accentColor}05 0%, transparent 50%)`,
                }}
              />
            </button>
          )
        })}
      </div>

      {/* Selection hint */}
      {hasReports && (
        <p className="text-[10px] text-gray-400 mt-1.5 text-center italic">
          {selectedReportId
            ? "Double-click a report to view full summary"
            : "Click a report to select, double-click to view summary"}
        </p>
      )}
    </div>
  )
}
