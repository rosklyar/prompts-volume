/**
 * Utility functions for report calculations
 */

import type {
  EnrichedEvaluationResultItem,
  BrandVariation,
  BrandVisibilityScore,
} from "@/types/groups"
import type { GeneratedReportItem } from "@/types/billing"

/**
 * Calculate visibility scores for each brand based on enriched results
 * Visibility = (prompts with at least one brand mention / total prompts) * 100
 */
export function calculateVisibilityScores(
  results: EnrichedEvaluationResultItem[],
  brands: BrandVariation[]
): BrandVisibilityScore[] {
  // Only count prompts that have answers (non-empty evaluations)
  const promptsWithAnswers = results.filter((r) => r.answer !== null)
  const totalPrompts = promptsWithAnswers.length

  if (totalPrompts === 0 || brands.length === 0) {
    return brands.map((brand) => ({
      brand_name: brand.name,
      prompts_with_mentions: 0,
      total_prompts: 0,
      visibility_percentage: 0,
    }))
  }

  return brands.map((brand) => {
    let promptsWithMentions = 0

    promptsWithAnswers.forEach((result) => {
      if (!result.brand_mentions) return

      const brandMention = result.brand_mentions.find(
        (bm) => bm.brand_name === brand.name
      )

      if (brandMention && brandMention.mentions.length > 0) {
        promptsWithMentions++
      }
    })

    const visibility_percentage =
      totalPrompts > 0
        ? Math.round((promptsWithMentions / totalPrompts) * 100)
        : 0

    return {
      brand_name: brand.name,
      prompts_with_mentions: promptsWithMentions,
      total_prompts: totalPrompts,
      visibility_percentage,
    }
  })
}

/**
 * Aggregated domain mention stats
 */
export interface AggregatedDomainMention {
  name: string
  domain: string
  is_brand: boolean
  total_mentions: number
  prompts_with_mentions: number
}

/**
 * Aggregate domain mentions across all report items
 * Returns sorted array: target brand first, then by total_mentions descending
 */
export function aggregateDomainMentions(
  items: GeneratedReportItem[]
): AggregatedDomainMention[] {
  const domainStats = new Map<string, AggregatedDomainMention>()

  for (const item of items) {
    if (!item.domain_mentions) continue
    for (const dm of item.domain_mentions) {
      const existing = domainStats.get(dm.domain)
      if (existing) {
        existing.total_mentions += dm.mentions.length
        if (dm.mentions.length > 0) {
          existing.prompts_with_mentions++
        }
      } else {
        domainStats.set(dm.domain, {
          name: dm.name,
          domain: dm.domain,
          is_brand: dm.is_brand,
          total_mentions: dm.mentions.length,
          prompts_with_mentions: dm.mentions.length > 0 ? 1 : 0,
        })
      }
    }
  }

  // Convert to array and sort: target brand first, then by mentions descending
  return Array.from(domainStats.values()).sort((a, b) => {
    if (a.is_brand && !b.is_brand) return -1
    if (!a.is_brand && b.is_brand) return 1
    return b.total_mentions - a.total_mentions
  })
}

/**
 * Brand domain info for citation counting
 */
export interface BrandDomain {
  name: string
  domain: string
  is_brand: boolean
}

/**
 * Citation domain count result
 */
export interface CitationDomainCount {
  name: string
  domain: string
  is_brand: boolean
  count: number
}

/**
 * Count how many times each brand's domain appears in citations
 * Returns sorted array: target brand first, then by count descending
 */
export function countBrandDomainsInCitations(
  items: GeneratedReportItem[],
  brandDomains: BrandDomain[]
): CitationDomainCount[] {
  const counts = new Map<string, number>()

  // Initialize all domains with 0 count
  for (const bd of brandDomains) {
    counts.set(bd.domain, 0)
  }

  // Count occurrences
  for (const item of items) {
    if (!item.answer?.citations) continue
    for (const citation of item.answer.citations) {
      for (const bd of brandDomains) {
        if (citation.url.includes(bd.domain)) {
          counts.set(bd.domain, (counts.get(bd.domain) || 0) + 1)
        }
      }
    }
  }

  // Build result array
  const results: CitationDomainCount[] = brandDomains.map((bd) => ({
    name: bd.name,
    domain: bd.domain,
    is_brand: bd.is_brand,
    count: counts.get(bd.domain) || 0,
  }))

  // Sort: target brand first, then by count descending
  return results.sort((a, b) => {
    if (a.is_brand && !b.is_brand) return -1
    if (!a.is_brand && b.is_brand) return 1
    return b.count - a.count
  })
}

/**
 * Calculate brand mention order (which brand was mentioned first in text)
 * Returns array sorted by first mention position
 */
export function getBrandMentionOrder(
  brandMentions: Array<{
    brand_name: string
    mentions: Array<{ start: number }>
  }> | null
): Array<{ brand_name: string; position: number }> {
  if (!brandMentions) return []

  const brandsWithFirstPosition = brandMentions
    .filter((bm) => bm.mentions.length > 0)
    .map((bm) => ({
      brand_name: bm.brand_name,
      first_position: Math.min(...bm.mentions.map((m) => m.start)),
    }))
    .sort((a, b) => a.first_position - b.first_position)

  return brandsWithFirstPosition.map((b, idx) => ({
    brand_name: b.brand_name,
    position: idx + 1, // 1-indexed
  }))
}
