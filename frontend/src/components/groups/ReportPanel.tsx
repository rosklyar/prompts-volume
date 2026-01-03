/**
 * ReportPanel - Collapsible panel showing visibility scores, domain mentions, and citation leaderboard
 * Editorial/magazine aesthetic with refined data visualization
 */

import { useState } from "react"
import type { BrandVisibilityScore, CitationLeaderboard } from "@/types/groups"
import type {
  AggregatedDomainMention,
  CitationDomainCount,
} from "@/lib/report-utils"
import { getBrandColor } from "./constants"

interface ReportPanelProps {
  visibilityScores: BrandVisibilityScore[]
  citationLeaderboard: CitationLeaderboard
  domainMentions: AggregatedDomainMention[]
  citationDomainCounts: CitationDomainCount[]
  accentColor: string
  targetBrandName?: string | null
  competitorNames?: string[]
  isCollapsed: boolean
  onToggleCollapse: () => void
}

// Chevron icon component for consistent styling
function ChevronIcon({ isCollapsed, color }: { isCollapsed: boolean; color: string }) {
  return (
    <svg
      className="w-3.5 h-3.5 transition-transform duration-200"
      style={{
        color,
        transform: isCollapsed ? "rotate(-90deg)" : "rotate(0deg)",
      }}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  )
}

// Collapsible section wrapper
function CollapsibleSection({
  title,
  isCollapsed,
  onToggle,
  accentColor,
  badge,
  children,
}: {
  title: string
  isCollapsed: boolean
  onToggle: () => void
  accentColor: string
  badge?: string
  children: React.ReactNode
}) {
  return (
    <div className="border-t" style={{ borderColor: `${accentColor}15` }}>
      <button
        onClick={onToggle}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-white/50 transition-colors text-left"
      >
        <div className="flex items-center gap-1.5">
          <ChevronIcon isCollapsed={isCollapsed} color={accentColor} />
          <span
            className="text-[10px] uppercase tracking-[0.15em] font-sans"
            style={{ color: accentColor }}
          >
            {title}
          </span>
        </div>
        {badge && (
          <span className="text-[10px] font-sans text-gray-400">{badge}</span>
        )}
      </button>
      <div
        className={`transition-all duration-300 ease-in-out overflow-hidden ${
          isCollapsed ? "max-h-0 opacity-0" : "max-h-[400px] opacity-100"
        }`}
      >
        <div className="px-3 pb-3">{children}</div>
      </div>
    </div>
  )
}

export function ReportPanel({
  visibilityScores,
  citationLeaderboard,
  domainMentions,
  citationDomainCounts,
  accentColor,
  targetBrandName,
  competitorNames = [],
  isCollapsed,
  onToggleCollapse,
}: ReportPanelProps) {
  // Section collapse states
  const [sectionStates, setSectionStates] = useState({
    brandVisibility: false, // expanded by default
    domainMentions: true,   // collapsed by default
    citationDomains: true,
    domainSources: true,
    pagePaths: true,
  })

  const toggleSection = (section: keyof typeof sectionStates) => {
    setSectionStates((prev) => ({ ...prev, [section]: !prev[section] }))
  }

  const hasVisibilityData = visibilityScores.length > 0
  const hasDomainMentions = domainMentions.length > 0 && domainMentions.some(dm => dm.total_mentions > 0)
  const hasCitationDomains = citationDomainCounts.length > 0 && citationDomainCounts.some(cd => cd.count > 0)
  const hasDomainData = citationLeaderboard.domains.length > 0
  const hasSubpathData = citationLeaderboard.subpaths.length > 0
  const hasCitationData = hasDomainData || hasSubpathData

  if (!hasVisibilityData && !hasCitationData && !hasDomainMentions && !hasCitationDomains) {
    return null
  }

  // Sort visibility scores: target brand first, then by percentage descending
  const sortedVisibilityScores = [...visibilityScores].sort((a, b) => {
    if (a.brand_name === targetBrandName) return -1
    if (b.brand_name === targetBrandName) return 1
    return b.visibility_percentage - a.visibility_percentage
  })

  // Calculate max values for progress bars (domain mentions and citations are relative)
  const maxDomainMentions = Math.max(...domainMentions.map((d) => d.total_mentions), 1)
  const maxCitationDomains = Math.max(...citationDomainCounts.map((c) => c.count), 1)

  return (
    <div
      className="rounded-lg border overflow-hidden transition-all duration-300"
      style={{
        borderColor: `${accentColor}25`,
        backgroundColor: `${accentColor}05`,
        fontFamily: "'Georgia', 'Times New Roman', serif",
      }}
    >
      {/* Main Header - always visible */}
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
          isCollapsed ? "max-h-0 opacity-0" : "max-h-[2000px] opacity-100"
        }`}
      >
        {/* Brand Visibility Section */}
        {hasVisibilityData && (
          <CollapsibleSection
            title="Brand visibility"
            isCollapsed={sectionStates.brandVisibility}
            onToggle={() => toggleSection("brandVisibility")}
            accentColor={accentColor}
            badge={`${sortedVisibilityScores.filter(s => s.visibility_percentage > 0).length} mentioned`}
          >
            <div className="space-y-1.5">
              {sortedVisibilityScores.map((score) => {
                const brandColor = getBrandColor(score.brand_name, targetBrandName, competitorNames, accentColor)
                const isTargetBrand = score.brand_name === targetBrandName

                return (
                  <div
                    key={score.brand_name}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-white/60 hover:bg-white transition-colors"
                  >
                    {/* Target indicator dot */}
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: isTargetBrand ? accentColor : `${brandColor.text}40` }}
                    />
                    {/* Brand name */}
                    <span
                      className={`text-sm flex-shrink-0 w-28 truncate ${isTargetBrand ? "font-semibold" : ""}`}
                      style={{ color: brandColor.text }}
                      title={score.brand_name}
                    >
                      {score.brand_name}
                    </span>
                    {/* Progress bar - actual percentage out of 100% */}
                    <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${score.visibility_percentage}%`,
                          backgroundColor: brandColor.text,
                        }}
                      />
                    </div>
                    {/* Percentage */}
                    <span
                      className="text-xs font-sans font-medium tabular-nums w-10 text-right"
                      style={{ color: brandColor.text }}
                    >
                      {score.visibility_percentage}%
                    </span>
                  </div>
                )
              })}
            </div>
          </CollapsibleSection>
        )}

        {/* Domain Mentions Section */}
        {hasDomainMentions && (
          <CollapsibleSection
            title="Domain mentions"
            isCollapsed={sectionStates.domainMentions}
            onToggle={() => toggleSection("domainMentions")}
            accentColor={accentColor}
            badge={`${domainMentions.reduce((sum, d) => sum + d.total_mentions, 0)} total`}
          >
            <div className="space-y-1.5">
              {domainMentions.filter(dm => dm.total_mentions > 0).map((dm) => {
                const brandColor = getBrandColor(dm.name, targetBrandName, competitorNames, accentColor)
                const barWidth = (dm.total_mentions / maxDomainMentions) * 100

                return (
                  <div
                    key={dm.domain}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-white/60 hover:bg-white transition-colors"
                  >
                    {/* Target indicator dot */}
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: dm.is_brand ? accentColor : `${brandColor.text}40` }}
                    />
                    {/* Domain */}
                    <span
                      className={`text-sm flex-shrink-0 w-32 truncate font-mono text-[12px] ${dm.is_brand ? "font-semibold" : ""}`}
                      style={{ color: brandColor.text }}
                      title={dm.domain}
                    >
                      {dm.domain}
                    </span>
                    {/* Progress bar */}
                    <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${barWidth}%`,
                          backgroundColor: brandColor.text,
                        }}
                      />
                    </div>
                    {/* Count */}
                    <span
                      className="text-xs font-sans font-medium tabular-nums w-16 text-right"
                      style={{ color: brandColor.text }}
                    >
                      {dm.total_mentions} {dm.total_mentions === 1 ? "mention" : "mentions"}
                    </span>
                  </div>
                )
              })}
            </div>
          </CollapsibleSection>
        )}

        {/* Citation Domains Section */}
        {hasCitationDomains && (
          <CollapsibleSection
            title="Citation domains"
            isCollapsed={sectionStates.citationDomains}
            onToggle={() => toggleSection("citationDomains")}
            accentColor={accentColor}
            badge={`${citationDomainCounts.reduce((sum, c) => sum + c.count, 0)} citations`}
          >
            <div className="space-y-1.5">
              {citationDomainCounts.filter(cd => cd.count > 0).map((cd) => {
                const brandColor = getBrandColor(cd.name, targetBrandName, competitorNames, accentColor)
                const barWidth = (cd.count / maxCitationDomains) * 100

                return (
                  <div
                    key={cd.domain}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-white/60 hover:bg-white transition-colors"
                  >
                    {/* Target indicator dot */}
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: cd.is_brand ? accentColor : `${brandColor.text}40` }}
                    />
                    {/* Domain */}
                    <span
                      className={`text-sm flex-shrink-0 w-32 truncate font-mono text-[12px] ${cd.is_brand ? "font-semibold" : ""}`}
                      style={{ color: brandColor.text }}
                      title={cd.domain}
                    >
                      {cd.domain}
                    </span>
                    {/* Progress bar */}
                    <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${barWidth}%`,
                          backgroundColor: brandColor.text,
                        }}
                      />
                    </div>
                    {/* Count */}
                    <span
                      className="text-xs font-sans font-medium tabular-nums w-16 text-right"
                      style={{ color: brandColor.text }}
                    >
                      {cd.count} {cd.count === 1 ? "citation" : "citations"}
                    </span>
                  </div>
                )
              })}
            </div>
          </CollapsibleSection>
        )}

        {/* Domain Sources Section */}
        {hasDomainData && (
          <CollapsibleSection
            title="Domain sources"
            isCollapsed={sectionStates.domainSources}
            onToggle={() => toggleSection("domainSources")}
            accentColor={accentColor}
            badge={`${citationLeaderboard.domains.length} domains`}
          >
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
          </CollapsibleSection>
        )}

        {/* Page Paths Section */}
        {hasSubpathData && (
          <CollapsibleSection
            title="Page paths"
            isCollapsed={sectionStates.pagePaths}
            onToggle={() => toggleSection("pagePaths")}
            accentColor={accentColor}
            badge={`${citationLeaderboard.subpaths.length} paths`}
          >
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
          </CollapsibleSection>
        )}
      </div>
    </div>
  )
}
