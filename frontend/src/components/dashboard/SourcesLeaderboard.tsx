/**
 * SourcesLeaderboard - Citation domain leaderboard table
 * Clean table with rank, domain, citations count, and coverage percentage
 * Matches styling with Sources tab (CitationLeaderboardDisplay)
 */

import { useNavigate } from "@tanstack/react-router"
import type { SourceStat } from "@/types/dashboard"

interface SourcesLeaderboardProps {
  sources: SourceStat[]
  hasData: boolean
  className?: string
}

const accentColor = "#C4553D"

export function SourcesLeaderboard({ sources, hasData, className = "" }: SourcesLeaderboardProps) {
  const navigate = useNavigate()

  if (!hasData || sources.length === 0) {
    return (
      <div className={`bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full min-h-0 flex flex-col ${className}`}>
        <h3
          className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-6 shrink-0 cursor-pointer hover:text-[#1F2937] transition-colors"
          onClick={() => navigate({ to: "/", search: { tab: "sources" } })}
        >
          Sources
        </h3>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-[#9CA3AF] text-center">
            No citations available
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full min-h-0 flex flex-col ${className}`}>
      <h3
        className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-4 shrink-0 cursor-pointer hover:text-[#1F2937] transition-colors"
        onClick={() => navigate({ to: "/", search: { tab: "sources" } })}
      >
        Sources
      </h3>

      {/* Column headers */}
      <div className="flex items-center gap-3 px-2 pb-2 border-b border-gray-100 shrink-0">
        <span className="w-5" />
        <span className="flex-1 text-[10px] font-medium uppercase tracking-wide text-[#9CA3AF]">
          Domain
        </span>
        <span className="w-16 text-[10px] font-medium uppercase tracking-wide text-[#9CA3AF] text-center">
          Citations
        </span>
        <span className="w-16 text-[10px] font-medium uppercase tracking-wide text-[#9CA3AF] text-center">
          Coverage
        </span>
      </div>

      {/* Scrollable list */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="space-y-1 pt-2">
          {sources.map((source, index) => (
            <div
              key={source.domain}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors group"
            >
              {/* Rank */}
              <span
                className="w-5 text-xs font-medium tabular-nums text-center"
                style={{
                  color: index < 3 ? accentColor : "#9CA3AF",
                  fontWeight: index < 3 ? 600 : 400,
                }}
              >
                {index + 1}
              </span>

              {/* Domain with link */}
              <a
                href={`https://${source.domain}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 text-sm font-medium truncate transition-colors"
                style={{ color: accentColor }}
              >
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full mr-1.5 -translate-y-px"
                  style={{ backgroundColor: accentColor }}
                />
                {source.domain}
              </a>

              {/* Citations count badge */}
              <span
                className="w-16 text-xs font-medium px-2 py-0.5 rounded-full text-center"
                style={{
                  backgroundColor: `${accentColor}15`,
                  color: accentColor,
                }}
              >
                {source.citation_count}
              </span>

              {/* Coverage percentage */}
              <span className="w-16 text-xs text-[#6B7280] font-medium tabular-nums text-center">
                {(source.coverage_percent ?? 0).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
