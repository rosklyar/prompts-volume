/**
 * SourcesLeaderboard - Citation domain leaderboard table
 * Clean table with rank, domain, and citation percentage
 */

import type { SourceStat } from "@/types/dashboard"

interface SourcesLeaderboardProps {
  sources: SourceStat[]
  hasData: boolean
}

export function SourcesLeaderboard({ sources, hasData }: SourcesLeaderboardProps) {
  if (!hasData || sources.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6]">
        <h3 className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-6">
          Sources
        </h3>
        <p className="text-sm text-[#9CA3AF] text-center py-8">
          No citations available
        </p>
      </div>
    )
  }

  // Find max percentage for bar scaling
  const maxPercent = Math.max(...sources.map((s) => s.citation_percent), 1)

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6]">
      <h3 className="font-['Fraunces'] text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-6">
        Sources
      </h3>

      <div className="space-y-2">
        {sources.map((source, index) => {
          const barWidth = (source.citation_percent / maxPercent) * 100

          return (
            <div
              key={source.domain}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors group"
            >
              {/* Rank */}
              <span className="w-5 text-xs text-[#9CA3AF] font-medium tabular-nums">
                {index + 1}
              </span>

              {/* Domain with link */}
              <a
                href={`https://${source.domain}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 text-sm text-[#1F2937] group-hover:text-[#C4553D] transition-colors truncate"
              >
                {source.domain}
              </a>

              {/* Bar and percentage */}
              <div className="flex items-center gap-2 shrink-0 w-32">
                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-[#C4553D]/60 transition-all duration-500"
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
                <span className="text-xs text-[#6B7280] font-medium tabular-nums w-10 text-right">
                  {source.citation_percent.toFixed(1)}%
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
