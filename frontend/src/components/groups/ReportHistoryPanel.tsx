/**
 * ReportHistoryPanel - Horizontal timeline of previously generated reports
 * Allows selecting a report to view its details
 */

import { useReportHistory, formatReportTime } from "@/hooks/useReports"
import { formatCredits } from "@/hooks/useBilling"

interface ReportHistoryPanelProps {
  groupId: number
  selectedReportId: number | null
  onSelectReport: (reportId: number | null) => void
  accentColor: string
}

export function ReportHistoryPanel({
  groupId,
  selectedReportId,
  onSelectReport,
  accentColor,
}: ReportHistoryPanelProps) {
  const { data: historyData, isLoading, error } = useReportHistory(groupId, true)

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
            Report history
          </span>
        </div>
        <div className="flex gap-2 overflow-hidden">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex-shrink-0 w-[140px] h-[72px] rounded-lg bg-gray-100 animate-pulse"
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

  // Empty state
  if (!hasReports) {
    return (
      <div className="mt-3">
        <div className="flex items-center gap-2 mb-2">
          <div
            className="w-1 h-4 rounded-full opacity-40"
            style={{ backgroundColor: accentColor }}
          />
          <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-300">
            Report history
          </span>
        </div>
        <div
          className="flex items-center justify-center py-4 rounded-lg border border-dashed"
          style={{ borderColor: `${accentColor}20` }}
        >
          <p className="text-xs text-gray-400 italic">
            No reports generated yet
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-3">
      {/* Section header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div
            className="w-1 h-4 rounded-full"
            style={{ backgroundColor: accentColor }}
          />
          <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-gray-400">
            Report history
          </span>
          <span
            className="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
            style={{
              backgroundColor: `${accentColor}15`,
              color: accentColor,
            }}
          >
            {reports.length}
          </span>
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
              className={`
                flex-shrink-0 relative group
                w-[140px] px-3 py-2.5 rounded-lg
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

              {/* Timestamp */}
              <p
                className="text-xs font-medium mb-1.5 truncate"
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
      {!selectedReportId && hasReports && (
        <p className="text-[10px] text-gray-400 mt-1.5 text-center italic">
          Click a report to view its details
        </p>
      )}
    </div>
  )
}
