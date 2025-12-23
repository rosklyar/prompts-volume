/**
 * Report Cache Storage Utility
 * Caches report data in localStorage for persistence across page refreshes
 */

import type {
  BrandVisibilityScore,
  CitationLeaderboard,
  PromptWithAnswer,
} from "@/types/groups"

interface CachedReportData {
  groupId: number
  timestamp: string
  prompts: PromptWithAnswer[]
  visibilityScores: BrandVisibilityScore[] | null
  citationLeaderboard: CitationLeaderboard | null
}

const REPORT_CACHE_PREFIX = "report_cache_"

/**
 * Get the localStorage key for a group's cached report
 */
function getReportCacheKey(groupId: number): string {
  return `${REPORT_CACHE_PREFIX}${groupId}`
}

/**
 * Save report data to localStorage for a specific group
 */
export function saveReportCache(
  groupId: number,
  prompts: PromptWithAnswer[],
  visibilityScores: BrandVisibilityScore[] | null,
  citationLeaderboard: CitationLeaderboard | null
): void {
  try {
    const cacheData: CachedReportData = {
      groupId,
      timestamp: new Date().toISOString(),
      prompts,
      visibilityScores,
      citationLeaderboard,
    }
    localStorage.setItem(getReportCacheKey(groupId), JSON.stringify(cacheData))
  } catch (error) {
    // Silently fail if localStorage is full or unavailable
    console.warn("Failed to cache report data:", error)
  }
}

/**
 * Load cached report data for a specific group
 * Returns null if no cache exists or cache is corrupted
 */
export function loadReportCache(groupId: number): CachedReportData | null {
  try {
    const cached = localStorage.getItem(getReportCacheKey(groupId))
    if (!cached) return null

    const data = JSON.parse(cached) as CachedReportData

    // Validate the cached data has required fields
    if (
      data.groupId !== groupId ||
      !data.timestamp ||
      !Array.isArray(data.prompts)
    ) {
      return null
    }

    return data
  } catch (error) {
    // Return null if parsing fails
    console.warn("Failed to load cached report:", error)
    return null
  }
}

/**
 * Clear cached report for a specific group
 */
export function clearReportCache(groupId: number): void {
  localStorage.removeItem(getReportCacheKey(groupId))
}

/**
 * Clear all cached reports
 */
export function clearAllReportCaches(): void {
  const keysToRemove: string[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith(REPORT_CACHE_PREFIX)) {
      keysToRemove.push(key)
    }
  }
  keysToRemove.forEach((key) => localStorage.removeItem(key))
}

/**
 * Get cache timestamp for a group (useful for displaying "last updated")
 */
export function getReportCacheTimestamp(groupId: number): Date | null {
  const cached = loadReportCache(groupId)
  return cached ? new Date(cached.timestamp) : null
}
