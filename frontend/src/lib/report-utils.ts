/**
 * Utility functions for report calculations
 */

import type {
  EnrichedEvaluationResultItem,
  BrandVariation,
  BrandVisibilityScore,
} from "@/types/groups"

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
