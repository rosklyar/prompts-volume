/**
 * CitationLeaderboardDisplay - Full scrollable citation leaderboard with domains and page paths
 * Editorial aesthetic matching ReportPanel style but expanded to full width with no item limit
 */

import type { AggregatedCitationsResponse, CitationCountItem } from "@/types/groups"

interface CitationLeaderboardDisplayProps {
  data: AggregatedCitationsResponse | undefined
  isLoading: boolean
  accentColor: string
}

function RankedList({
  title,
  items,
  accentColor,
  isDomain,
}: {
  title: string
  items: CitationCountItem[]
  accentColor: string
  isDomain: boolean
}) {
  return (
    <div className="flex flex-col">
      {/* Section header */}
      <div className="flex items-center gap-2 mb-3">
        <div
          className="w-1 h-4 rounded-full"
          style={{ backgroundColor: accentColor }}
        />
        <span
          className="text-[10px] font-semibold uppercase tracking-[0.15em]"
          style={{ color: accentColor }}
        >
          {title}
        </span>
        <span
          className="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
          style={{
            backgroundColor: `${accentColor}15`,
            color: accentColor,
          }}
        >
          {items.length}
        </span>
      </div>

      {/* List container */}
      <div
        className="bg-white rounded-lg border overflow-hidden flex-1"
        style={{ borderColor: `${accentColor}15` }}
      >
        {items.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-xs text-gray-400 italic font-sans">
              No {isDomain ? "domains" : "paths"} found
            </p>
          </div>
        ) : (
          <div className="max-h-[480px] overflow-y-auto">
            {/* Column headers */}
            <div className="sticky top-0 z-10 flex items-center gap-3 px-3 py-2 border-b border-gray-100 bg-gray-50">
              <span className="w-5 flex-shrink-0" />
              <span className="flex-1 text-[10px] font-medium uppercase tracking-wide text-gray-400">
                {isDomain ? "Domain" : "Path"}
              </span>
              <span className="w-16 text-[10px] font-medium uppercase tracking-wide text-gray-400 text-center flex-shrink-0">
                Citations
              </span>
              <span className="w-16 text-[10px] font-medium uppercase tracking-wide text-gray-400 text-center flex-shrink-0">
                Coverage
              </span>
            </div>
            {items.map((item, index) => (
              <div
                key={item.path}
                className={`flex items-center gap-3 px-3 py-2 transition-colors hover:bg-gray-50 ${
                  index !== 0 ? "border-t border-gray-50" : ""
                }`}
              >
                {/* Rank indicator */}
                <span
                  className="text-xs font-sans tabular-nums w-5 text-center flex-shrink-0"
                  style={{
                    color: index < 3 ? accentColor : "#9CA3AF",
                    fontWeight: index < 3 ? 600 : 400,
                  }}
                >
                  {index + 1}
                </span>

                {/* Domain/path text */}
                <div className="flex-1 min-w-0">
                  <p
                    className={`text-sm truncate font-sans ${isDomain ? "font-medium" : ""}`}
                    style={{ color: "#1E1E1E" }}
                    title={item.path}
                  >
                    {isDomain && (
                      <span
                        className="inline-block w-1.5 h-1.5 rounded-full mr-1.5 -translate-y-px bg-[#1E1E1E]"
                      />
                    )}
                    {item.path}
                  </p>
                </div>

                {/* Citations count badge */}
                <span
                  className="w-16 text-xs font-sans font-medium px-2 py-0.5 rounded-full flex-shrink-0 text-center"
                  style={{
                    backgroundColor: `${accentColor}15`,
                    color: accentColor,
                  }}
                >
                  {item.count}
                </span>

                {/* Coverage percentage */}
                <span className="w-16 text-xs font-sans font-medium text-gray-500 tabular-nums flex-shrink-0 text-center">
                  {(item.coverage_percent ?? 0).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {[0, 1].map((col) => (
        <div key={col} className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <div className="w-1 h-4 rounded-full bg-gray-200 animate-pulse" />
            <div className="w-24 h-3 rounded bg-gray-200 animate-pulse" />
          </div>
          <div className="bg-white rounded-lg border border-gray-100 overflow-hidden">
            {[0, 1, 2, 3, 4].map((row) => (
              <div
                key={row}
                className={`flex items-center gap-3 px-3 py-2.5 ${row > 0 ? "border-t border-gray-50" : ""}`}
              >
                <div className="w-5 h-3 rounded bg-gray-100 animate-pulse" />
                <div
                  className="flex-1 h-3 rounded bg-gray-100 animate-pulse"
                  style={{ width: `${80 - row * 12}%`, animationDelay: `${row * 60}ms` }}
                />
                <div className="w-8 h-5 rounded-full bg-gray-100 animate-pulse" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export function CitationLeaderboardDisplay({
  data,
  isLoading,
  accentColor,
}: CitationLeaderboardDisplayProps) {
  if (isLoading) {
    return <LoadingSkeleton />
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <p className="text-sm text-gray-400 font-['DM_Sans']">
            Select a group to view aggregated citations
          </p>
        </div>
      </div>
    )
  }

  const { citation_leaderboard: leaderboard, reports_included } = data

  if (leaderboard.total_citations === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center">
          <p className="text-sm text-gray-400 font-['DM_Sans']">
            No citations found for this period
          </p>
          <p className="text-xs text-gray-300 mt-1 font-['DM_Sans']">
            {reports_included} report{reports_included !== 1 ? "s" : ""} checked
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RankedList
          title="Domain sources"
          items={leaderboard.domains}
          accentColor={accentColor}
          isDomain={true}
        />
        <RankedList
          title="Page paths"
          items={leaderboard.subpaths}
          accentColor={accentColor}
          isDomain={false}
        />
      </div>

      {/* Metadata footer */}
      <div className="text-center pt-2">
        <span className="text-[10px] text-gray-400 font-sans tracking-wide">
          {reports_included} report{reports_included !== 1 ? "s" : ""} aggregated
          {" \u00B7 "}
          {leaderboard.total_citations} total citation{leaderboard.total_citations !== 1 ? "s" : ""}
        </span>
      </div>
    </div>
  )
}
