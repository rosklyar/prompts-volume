/**
 * ReportSummaryDialog — Full-screen modal for viewing report summary data.
 * Portal-based dialog following the PromptDialog pattern.
 * Shows brand visibility, domain mentions, citations, domain sources, and page paths.
 */

import { useEffect, useCallback } from "react"
import { createPortal } from "react-dom"
import type { CitationLeaderboard } from "@/types/groups"
import type { ReportStatistics } from "@/types/billing"
import { getBrandColor } from "./constants"

interface ReportSummaryDialogProps {
  isOpen: boolean
  onClose: () => void
  statistics: ReportStatistics | null
  citationLeaderboard: CitationLeaderboard
  accentColor: string
  targetBrandName?: string | null
  competitorNames?: string[]
  reportId: number | null
  onExportJson: () => void
  isExporting: boolean
}

function DownloadIcon({ color, className }: { color: string; className?: string }) {
  return (
    <svg
      className={className}
      style={{ color }}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
      />
    </svg>
  )
}

function SpinnerIcon({ color, className }: { color: string; className?: string }) {
  return (
    <svg
      className={`animate-spin ${className}`}
      style={{ color }}
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

function SectionHeader({
  title,
  badge,
  accentColor,
}: {
  title: string
  badge?: string
  accentColor: string
}) {
  return (
    <div className="flex items-center justify-between mb-3">
      <span
        className="text-[11px] uppercase tracking-[0.15em] font-sans font-semibold"
        style={{ color: accentColor }}
      >
        {title}
      </span>
      {badge && (
        <span className="text-[10px] font-sans text-gray-400">{badge}</span>
      )}
    </div>
  )
}

export function ReportSummaryDialog({
  isOpen,
  onClose,
  statistics,
  citationLeaderboard,
  accentColor,
  targetBrandName,
  competitorNames = [],
  reportId,
  onExportJson,
  isExporting,
}: ReportSummaryDialogProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    },
    [onClose],
  )

  useEffect(() => {
    if (!isOpen) return
    document.addEventListener("keydown", handleKeyDown)
    document.body.style.overflow = "hidden"
    return () => {
      document.removeEventListener("keydown", handleKeyDown)
      document.body.style.overflow = ""
    }
  }, [isOpen, handleKeyDown])

  if (!isOpen) return null

  const visibilityScores = statistics?.brand_visibility ?? []
  const domainMentions = statistics?.domain_mentions ?? []
  const citationDomainCounts = statistics?.citation_domains ?? []

  const hasVisibilityData = visibilityScores.length > 0
  const hasDomainMentions = domainMentions.length > 0 && domainMentions.some(dm => dm.total_mentions > 0)
  const hasCitationDomains = citationDomainCounts.length > 0 && citationDomainCounts.some(cd => cd.citation_count > 0)
  const hasDomainData = citationLeaderboard.domains.length > 0
  const hasSubpathData = citationLeaderboard.subpaths.length > 0

  const sortedVisibilityScores = [...visibilityScores].sort((a, b) => {
    if (a.is_target_brand) return -1
    if (b.is_target_brand) return 1
    return b.visibility_percentage - a.visibility_percentage
  })

  const maxDomainMentions = Math.max(...domainMentions.map((d) => d.total_mentions), 1)
  const maxCitationDomains = Math.max(...citationDomainCounts.map((c) => c.citation_count), 1)

  const showExportButton = reportId != null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-200">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      {/* Modal panel */}
      <div
        className="relative flex flex-col w-full max-w-4xl h-[90vh] bg-white rounded-xl shadow-xl
          overflow-hidden animate-in zoom-in-95 duration-200"
      >
        {/* Accent top bar */}
        <div className="h-[3px] shrink-0" style={{ backgroundColor: accentColor }} />

        {/* Header */}
        <div className="flex items-center justify-between px-8 py-4 border-b border-gray-100 shrink-0">
          <h2
            className="text-lg text-gray-900 font-medium"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          >
            Report Summary
          </h2>
          <div className="flex items-center gap-2">
            {/* Export JSON button */}
            {showExportButton && (
              <button
                onClick={onExportJson}
                disabled={isExporting}
                title="Download JSON"
                className="p-2 rounded-lg transition-all duration-200 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed group"
                style={{ color: accentColor }}
              >
                {isExporting ? (
                  <SpinnerIcon color={accentColor} className="w-4 h-4" />
                ) : (
                  <DownloadIcon
                    color={accentColor}
                    className="w-4 h-4 group-hover:scale-110 transition-transform duration-150"
                  />
                )}
              </button>
            )}
            {/* Close button */}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center
                text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              aria-label="Close dialog"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-[720px] mx-auto px-8 py-8 sm:px-12 sm:py-10">
            {/* Loading state */}
            {!statistics ? (
              <div className="flex items-center justify-center py-16">
                <p className="text-sm text-gray-400 italic" style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}>
                  Loading report data...
                </p>
              </div>
            ) : (
              <div className="space-y-8">
                {/* 1. Brand Visibility */}
                {hasVisibilityData && (
                  <section>
                    <SectionHeader
                      title="Brand visibility"
                      badge={`${sortedVisibilityScores.filter(s => s.visibility_percentage > 0).length} mentioned`}
                      accentColor={accentColor}
                    />
                    <div className="space-y-1.5">
                      {sortedVisibilityScores.map((score) => {
                        const brandColor = getBrandColor(score.brand_name, targetBrandName, competitorNames, accentColor)
                        const isTargetBrand = score.is_target_brand
                        return (
                          <div
                            key={score.brand_name}
                            className="flex items-center gap-3 px-3 py-2 rounded-md bg-gray-50/80 hover:bg-gray-50 transition-colors"
                          >
                            <span
                              className="w-2 h-2 rounded-full flex-shrink-0"
                              style={{ backgroundColor: isTargetBrand ? accentColor : `${brandColor.text}40` }}
                            />
                            <span
                              className={`text-sm flex-shrink-0 w-36 truncate ${isTargetBrand ? "font-semibold" : ""}`}
                              style={{ color: brandColor.text }}
                              title={score.brand_name}
                            >
                              {score.brand_name}
                            </span>
                            <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all duration-500"
                                style={{
                                  width: `${score.visibility_percentage}%`,
                                  backgroundColor: brandColor.text,
                                }}
                              />
                            </div>
                            <span
                              className="text-xs font-sans font-medium tabular-nums w-12 text-right"
                              style={{ color: brandColor.text }}
                            >
                              {score.visibility_percentage}%
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </section>
                )}

                {/* 2. Domain Mentions */}
                {hasDomainMentions && (
                  <section className="border-t border-gray-100 pt-8">
                    <SectionHeader
                      title="Domain mentions"
                      badge={`${domainMentions.reduce((sum, d) => sum + d.total_mentions, 0)} total`}
                      accentColor={accentColor}
                    />
                    <div className="space-y-1.5">
                      {domainMentions.filter(dm => dm.total_mentions > 0).map((dm) => {
                        const brandColor = getBrandColor(dm.name, targetBrandName, competitorNames, accentColor)
                        const barWidth = (dm.total_mentions / maxDomainMentions) * 100
                        return (
                          <div
                            key={dm.domain}
                            className="flex items-center gap-3 px-3 py-2 rounded-md bg-gray-50/80 hover:bg-gray-50 transition-colors"
                          >
                            <span
                              className="w-2 h-2 rounded-full flex-shrink-0"
                              style={{ backgroundColor: dm.is_target_brand ? accentColor : `${brandColor.text}40` }}
                            />
                            <span
                              className={`text-sm flex-shrink-0 w-40 truncate font-mono text-[12px] ${dm.is_target_brand ? "font-semibold" : ""}`}
                              style={{ color: brandColor.text }}
                              title={dm.domain}
                            >
                              {dm.domain}
                            </span>
                            <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all duration-500"
                                style={{
                                  width: `${barWidth}%`,
                                  backgroundColor: brandColor.text,
                                }}
                              />
                            </div>
                            <span
                              className="text-xs font-sans font-medium tabular-nums w-20 text-right"
                              style={{ color: brandColor.text }}
                            >
                              {dm.total_mentions} {dm.total_mentions === 1 ? "mention" : "mentions"}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </section>
                )}

                {/* 3. Citation Domains */}
                {hasCitationDomains && (
                  <section className="border-t border-gray-100 pt-8">
                    <SectionHeader
                      title="Citation domains"
                      badge={`${citationDomainCounts.reduce((sum, c) => sum + c.citation_count, 0)} citations`}
                      accentColor={accentColor}
                    />
                    <div className="space-y-1.5">
                      {citationDomainCounts.filter(cd => cd.citation_count > 0).map((cd) => {
                        const brandColor = getBrandColor(cd.name, targetBrandName, competitorNames, accentColor)
                        const barWidth = (cd.citation_count / maxCitationDomains) * 100
                        return (
                          <div
                            key={cd.domain}
                            className="flex items-center gap-3 px-3 py-2 rounded-md bg-gray-50/80 hover:bg-gray-50 transition-colors"
                          >
                            <span
                              className="w-2 h-2 rounded-full flex-shrink-0"
                              style={{ backgroundColor: cd.is_target_brand ? accentColor : `${brandColor.text}40` }}
                            />
                            <span
                              className={`text-sm flex-shrink-0 w-40 truncate font-mono text-[12px] ${cd.is_target_brand ? "font-semibold" : ""}`}
                              style={{ color: brandColor.text }}
                              title={cd.domain}
                            >
                              {cd.domain}
                            </span>
                            <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all duration-500"
                                style={{
                                  width: `${barWidth}%`,
                                  backgroundColor: brandColor.text,
                                }}
                              />
                            </div>
                            <span
                              className="text-xs font-sans font-medium tabular-nums w-20 text-right"
                              style={{ color: brandColor.text }}
                            >
                              {cd.citation_count} {cd.citation_count === 1 ? "citation" : "citations"}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </section>
                )}

                {/* 4. Domain Sources */}
                {hasDomainData && (
                  <section className="border-t border-gray-100 pt-8">
                    <SectionHeader
                      title="Domain sources"
                      badge={`${citationLeaderboard.domains.length} domains`}
                      accentColor={accentColor}
                    />
                    <div className="bg-white rounded-lg border overflow-hidden" style={{ borderColor: `${accentColor}15` }}>
                      {citationLeaderboard.domains.map((item, index) => (
                        <div
                          key={item.path}
                          className={`flex items-center gap-3 px-3 py-2 transition-colors hover:bg-gray-50 ${
                            index !== 0 ? "border-t border-gray-50" : ""
                          }`}
                        >
                          <span
                            className="text-xs font-sans tabular-nums w-5 text-center"
                            style={{
                              color: index < 3 ? accentColor : "#9CA3AF",
                              fontWeight: index < 3 ? 600 : 400,
                            }}
                          >
                            {index + 1}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p
                              className="text-sm truncate font-sans font-medium"
                              style={{ color: accentColor }}
                            >
                              <span className="inline-block w-1.5 h-1.5 rounded-full mr-1.5 -translate-y-px" style={{ backgroundColor: accentColor }} />
                              {item.path}
                            </p>
                          </div>
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
                  </section>
                )}

                {/* 5. Page Paths */}
                {hasSubpathData && (
                  <section className="border-t border-gray-100 pt-8">
                    <SectionHeader
                      title="Page paths"
                      badge={`${citationLeaderboard.subpaths.length} paths`}
                      accentColor={accentColor}
                    />
                    <div className="bg-white rounded-lg border overflow-hidden" style={{ borderColor: `${accentColor}15` }}>
                      {citationLeaderboard.subpaths.map((item, index) => (
                        <div
                          key={item.path}
                          className={`flex items-center gap-3 px-3 py-2 transition-colors hover:bg-gray-50 ${
                            index !== 0 ? "border-t border-gray-50" : ""
                          }`}
                        >
                          <span
                            className="text-xs font-sans tabular-nums w-5 text-center"
                            style={{
                              color: index < 3 ? accentColor : "#9CA3AF",
                              fontWeight: index < 3 ? 600 : 400,
                            }}
                          >
                            {index + 1}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p
                              className="text-sm truncate font-sans"
                              style={{ color: "#4B5563" }}
                            >
                              {item.path}
                            </p>
                          </div>
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
                  </section>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}
