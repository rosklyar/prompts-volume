/**
 * CompetitorsList - Ranked list of competitors by visibility
 * Target brand is highlighted with gold background
 */

import type { CompetitorVisibility } from "@/types/dashboard"

interface CompetitorsListProps {
  competitors: CompetitorVisibility[]
  hasData: boolean
}

export function CompetitorsList({ competitors, hasData }: CompetitorsListProps) {
  if (!hasData || competitors.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6]">
        <h3 className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-6">
          Competitors
        </h3>
        <p className="text-sm text-[#9CA3AF] text-center py-8">
          No visibility data available
        </p>
      </div>
    )
  }

  // Find max visibility for bar scaling
  const maxVisibility = Math.max(...competitors.map((c) => c.visibility_percent), 1)

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6]">
      <h3 className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-6">
        Competitors
      </h3>

      <div className="space-y-2">
        {competitors.slice(0, 10).map((competitor, index) => {
          const barWidth = (competitor.visibility_percent / maxVisibility) * 100

          return (
            <div
              key={competitor.name}
              className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${
                competitor.is_target_brand
                  ? "bg-[#FEF7F5] border border-[#C4553D]/20"
                  : "hover:bg-gray-50"
              }`}
            >
              {/* Rank badge */}
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium shrink-0 ${
                  competitor.is_target_brand
                    ? "bg-[#C4553D] text-white"
                    : "bg-gray-100 text-[#6B7280]"
                }`}
              >
                {index + 1}
              </span>

              {/* Name and bar */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-sm font-medium truncate ${
                      competitor.is_target_brand
                        ? "text-[#C4553D]"
                        : "text-[#1F2937]"
                    }`}
                  >
                    {competitor.name}
                  </span>
                  {competitor.is_target_brand && (
                    <span className="text-[10px] uppercase tracking-wide text-[#C4553D] font-medium">
                      You
                    </span>
                  )}
                </div>
                {/* Mini progress bar */}
                <div className="mt-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      competitor.is_target_brand
                        ? "bg-[#C4553D]"
                        : "bg-[#9CA3AF]"
                    }`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
              </div>

              {/* Percentage */}
              <span
                className={`text-sm font-medium tabular-nums shrink-0 ${
                  competitor.is_target_brand
                    ? "text-[#C4553D]"
                    : "text-[#6B7280]"
                }`}
              >
                {competitor.visibility_percent.toFixed(1)}%
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
