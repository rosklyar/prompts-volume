/**
 * ReportPanel - Collapsible panel showing visibility scores and citation leaderboard
 * Editorial/magazine aesthetic with refined data visualization
 */

import type { BrandVisibilityScore, CitationLeaderboard } from "@/types/groups"
import { getBrandColor } from "./constants"

interface ReportPanelProps {
  visibilityScores: BrandVisibilityScore[]
  citationLeaderboard: CitationLeaderboard
  accentColor: string
  targetBrandName?: string | null
  competitorNames?: string[]
  isCollapsed: boolean
  onToggleCollapse: () => void
}

export function ReportPanel({
  visibilityScores,
  citationLeaderboard,
  accentColor,
  targetBrandName,
  competitorNames = [],
  isCollapsed,
  onToggleCollapse,
}: ReportPanelProps) {
  const hasVisibilityData = visibilityScores.length > 0
  const hasDomainData = citationLeaderboard.domains.length > 0
  const hasSubpathData = citationLeaderboard.subpaths.length > 0
  const hasCitationData = hasDomainData || hasSubpathData

  if (!hasVisibilityData && !hasCitationData) {
    return null
  }

  return (
    <div
      className="rounded-lg border overflow-hidden transition-all duration-300"
      style={{
        borderColor: `${accentColor}25`,
        backgroundColor: `${accentColor}05`,
        fontFamily: "'Georgia', 'Times New Roman', serif",
      }}
    >
      {/* Header - always visible */}
      <button
        onClick={onToggleCollapse}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg
            className="w-4 h-4 transition-transform duration-200"
            style={{
              color: accentColor,
              transform: isCollapsed ? "rotate(-90deg)" : "rotate(0deg)",
            }}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          <span
            className="text-sm font-medium tracking-wide"
            style={{ color: accentColor }}
          >
            Report summary
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs font-sans text-gray-400">
          {hasVisibilityData && (
            <span>{visibilityScores.length} brand{visibilityScores.length !== 1 ? "s" : ""}</span>
          )}
          {hasCitationData && (
            <span>{citationLeaderboard.total_citations} citation{citationLeaderboard.total_citations !== 1 ? "s" : ""}</span>
          )}
        </div>
      </button>

      {/* Content - collapsible */}
      <div
        className={`transition-all duration-300 ease-in-out overflow-hidden ${
          isCollapsed ? "max-h-0 opacity-0" : "max-h-[500px] opacity-100"
        }`}
      >
        <div className="px-4 pb-4 space-y-4">
          {/* Visibility Scores Section */}
          {hasVisibilityData && (
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-gray-400 font-sans mb-2">
                Brand visibility
              </p>
              <div className="flex flex-wrap gap-2">
                {visibilityScores.map((score) => {
                  const brandColor = getBrandColor(score.brand_name, targetBrandName, competitorNames, accentColor)
                  const isTargetBrand = score.brand_name === targetBrandName

                  return (
                    <div
                      key={score.brand_name}
                      className="group relative flex items-center gap-2 px-3 py-2 rounded-lg bg-white border transition-all hover:shadow-sm"
                      style={{ borderColor: `${brandColor.text}20` }}
                    >
                      {/* Brand name */}
                      <span
                        className={`text-sm ${isTargetBrand ? "font-semibold" : ""}`}
                        style={{ color: brandColor.text }}
                      >
                        {score.brand_name}
                      </span>

                      {/* Percentage with visual bar */}
                      <div className="flex items-center gap-1.5">
                        <div
                          className="h-1.5 rounded-full bg-gray-100 overflow-hidden"
                          style={{ width: "40px" }}
                        >
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${score.visibility_percentage}%`,
                              backgroundColor: brandColor.text,
                            }}
                          />
                        </div>
                        <span
                          className="text-xs font-sans font-medium tabular-nums"
                          style={{ color: brandColor.text }}
                        >
                          {score.visibility_percentage}%
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Domain Sources Section */}
          {hasDomainData && (
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-gray-400 font-sans mb-2">
                Domain sources
              </p>
              <div className="bg-white rounded-lg border overflow-hidden" style={{ borderColor: `${accentColor}15` }}>
                <div className="max-h-[180px] overflow-y-auto">
                  {citationLeaderboard.domains.slice(0, 10).map((item, index) => (
                    <div
                      key={item.path}
                      className={`flex items-center gap-3 px-3 py-2 transition-colors hover:bg-gray-50 ${
                        index !== 0 ? "border-t border-gray-50" : ""
                      }`}
                    >
                      {/* Rank indicator */}
                      <span
                        className="text-xs font-sans tabular-nums w-5 text-center"
                        style={{
                          color: index < 3 ? accentColor : "#9CA3AF",
                          fontWeight: index < 3 ? 600 : 400,
                        }}
                      >
                        {index + 1}
                      </span>

                      {/* Domain with styling */}
                      <div className="flex-1 min-w-0">
                        <p
                          className="text-sm truncate font-sans font-medium"
                          style={{ color: accentColor }}
                        >
                          <span className="inline-block w-1.5 h-1.5 rounded-full mr-1.5 -translate-y-px" style={{ backgroundColor: accentColor }} />
                          {item.path}
                        </p>
                      </div>

                      {/* Count badge */}
                      <span
                        className="text-xs font-sans font-medium px-2 py-0.5 rounded-full"
                        style={{
                          backgroundColor: `${accentColor}15`,
                          color: accentColor,
                        }}
                      >
                        {item.count}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Show more indicator if truncated */}
                {citationLeaderboard.domains.length > 10 && (
                  <div className="px-3 py-2 border-t text-center" style={{ borderColor: `${accentColor}10` }}>
                    <span className="text-xs text-gray-400 font-sans italic">
                      +{citationLeaderboard.domains.length - 10} more domains
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Page Paths Section */}
          {hasSubpathData && (
            <div>
              <p className="text-[10px] uppercase tracking-[0.2em] text-gray-400 font-sans mb-2">
                Page paths
              </p>
              <div className="bg-white rounded-lg border overflow-hidden" style={{ borderColor: `${accentColor}15` }}>
                <div className="max-h-[180px] overflow-y-auto">
                  {citationLeaderboard.subpaths.slice(0, 10).map((item, index) => (
                    <div
                      key={item.path}
                      className={`flex items-center gap-3 px-3 py-2 transition-colors hover:bg-gray-50 ${
                        index !== 0 ? "border-t border-gray-50" : ""
                      }`}
                    >
                      {/* Rank indicator */}
                      <span
                        className="text-xs font-sans tabular-nums w-5 text-center"
                        style={{
                          color: index < 3 ? accentColor : "#9CA3AF",
                          fontWeight: index < 3 ? 600 : 400,
                        }}
                      >
                        {index + 1}
                      </span>

                      {/* Path styling */}
                      <div className="flex-1 min-w-0">
                        <p
                          className="text-sm truncate font-sans"
                          style={{ color: "#4B5563" }}
                        >
                          {item.path}
                        </p>
                      </div>

                      {/* Count badge */}
                      <span
                        className="text-xs font-sans font-medium px-2 py-0.5 rounded-full"
                        style={{
                          backgroundColor: `${accentColor}15`,
                          color: accentColor,
                        }}
                      >
                        {item.count}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Show more indicator if truncated */}
                {citationLeaderboard.subpaths.length > 10 && (
                  <div className="px-3 py-2 border-t text-center" style={{ borderColor: `${accentColor}10` }}>
                    <span className="text-xs text-gray-400 font-sans italic">
                      +{citationLeaderboard.subpaths.length - 10} more paths
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
