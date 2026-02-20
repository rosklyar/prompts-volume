/**
 * CompetitorsList - Ranked list of all brands by visibility
 * Target brand is highlighted with accent styling
 */

import { useNavigate } from "@tanstack/react-router"
import type { CompetitorVisibility } from "@/types/dashboard"
import { BrandLogo } from "@/components/BrandLogo"

interface CompetitorsListProps {
  competitors: CompetitorVisibility[]
  hasData: boolean
  colorMap: Map<string, string>
}

export function CompetitorsList({ competitors, hasData, colorMap }: CompetitorsListProps) {
  const navigate = useNavigate()

  if (!hasData || competitors.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full min-h-0 flex flex-col">
        <h3
          className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-6 shrink-0 cursor-pointer hover:text-[#1F2937] transition-colors"
          onClick={() => navigate({ to: "/", search: { tab: "competitors" } })}
        >
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

  // Find target brand rank (1-based)
  const brandRank = competitors.findIndex((c) => c.is_target_brand) + 1

  // Find max visibility for bar scaling
  const maxVisibility = Math.max(...competitors.map((c) => c.visibility_percent), 1)

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full min-h-0 flex flex-col">
      <h3
        className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide shrink-0 cursor-pointer hover:text-[#1F2937] transition-colors"
        onClick={() => navigate({ to: "/", search: { tab: "competitors" } })}
      >
        Competitors
      </h3>
      {brandRank > 0 && (
        <p className="text-xs text-[#9CA3AF] mt-1 mb-4 shrink-0">
          Your brand is ranked <span className="font-semibold text-indigo-600">#{brandRank}</span> of {competitors.length}
        </p>
      )}
      {brandRank === 0 && <div className="mb-6" />}

      <div className="space-y-2 flex-1 overflow-y-auto min-h-0">
        {competitors.map((competitor, index) => {
          const barWidth = (competitor.visibility_percent / maxVisibility) * 100
          const isTarget = competitor.is_target_brand
          const color = colorMap.get(competitor.name)

          return (
            <div
              key={competitor.name}
              className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${
                isTarget
                  ? "bg-indigo-50 hover:bg-indigo-100"
                  : "hover:bg-gray-50"
              }`}
            >
              {/* Rank badge */}
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium shrink-0 ${
                  isTarget ? "bg-indigo-600 text-white" : "text-white"
                }`}
                style={!isTarget && color ? { backgroundColor: color } : undefined}
              >
                {index + 1}
              </span>

              {/* Brand logo */}
              <BrandLogo domain={competitor.domain} name={competitor.name} size={24} />

              {/* Name and bar */}
              <div className="flex-1 min-w-0">
                <span
                  className={`text-sm truncate ${
                    isTarget
                      ? "font-semibold text-indigo-900"
                      : "font-medium text-[#1F2937]"
                  }`}
                >
                  {competitor.name}
                </span>
                {/* Mini progress bar */}
                <div className="mt-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${isTarget ? "bg-indigo-500" : ""}`}
                    style={!isTarget && color ? { width: `${barWidth}%`, backgroundColor: color } : { width: `${barWidth}%` }}
                  />
                </div>
              </div>

              {/* Percentage + delta */}
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className={`text-sm font-medium tabular-nums ${
                    isTarget ? "text-indigo-700" : "text-[#6B7280]"
                  }`}
                >
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
