/**
 * CompetitorsList - Ranked list of competitors by visibility
 * Target brand is excluded (shown on the gauge card instead)
 */

import type { CompetitorVisibility } from "@/types/dashboard"

interface CompetitorsListProps {
  competitors: CompetitorVisibility[]
  hasData: boolean
}

export function CompetitorsList({ competitors, hasData }: CompetitorsListProps) {
  const filtered = competitors.filter((c) => !c.is_target_brand)

  if (!hasData || filtered.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full flex flex-col">
        <h3 className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-6 shrink-0">
          Competitors
        </h3>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-[#9CA3AF] text-center">
            No visibility data available
          </p>
        </div>
      </div>
    )
  }

  // Find max visibility for bar scaling
  const maxVisibility = Math.max(...filtered.map((c) => c.visibility_percent), 1)

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full flex flex-col">
      <h3 className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-6 shrink-0">
        Competitors
      </h3>

      <div className="space-y-2 flex-1 overflow-y-auto min-h-0">
        {filtered.map((competitor, index) => {
          const barWidth = (competitor.visibility_percent / maxVisibility) * 100

          return (
            <div
              key={competitor.name}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors"
            >
              {/* Rank badge */}
              <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium shrink-0 bg-gray-100 text-[#6B7280]">
                {index + 1}
              </span>

              {/* Name and bar */}
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium truncate text-[#1F2937]">
                  {competitor.name}
                </span>
                {/* Mini progress bar */}
                <div className="mt-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 bg-[#9CA3AF]"
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
              </div>

              {/* Percentage + delta */}
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-sm font-medium tabular-nums text-[#6B7280]">
                  {competitor.visibility_percent.toFixed(1)}%
                </span>
                {competitor.visibility_change != null && (
                  <span
                    className={`text-xs font-medium tabular-nums ${
                      competitor.visibility_change > 0
                        ? "text-green-600"
                        : "text-red-500"
                    }`}
                  >
                    {competitor.visibility_change > 0 ? "▲" : "▼"}{" "}
                    {competitor.visibility_change > 0 ? "+" : ""}
                    {competitor.visibility_change.toFixed(1)}%
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
