/**
 * HighlightedResponse - Renders response text with highlighted brand mentions
 * Editorial aesthetic with subtle annotation styling
 */

import { useMemo } from "react"
import type { BrandMentionResult } from "@/types/groups"

interface HighlightedResponseProps {
  response: string
  brandMentions: BrandMentionResult[] | null
  accentColor: string
}

interface TextSegment {
  text: string
  isHighlight: boolean
  brandName?: string
  matchedText?: string
}

export function HighlightedResponse({
  response,
  brandMentions,
  accentColor,
}: HighlightedResponseProps) {
  // Parse response into segments with highlights
  const segments = useMemo((): TextSegment[] => {
    if (!brandMentions || brandMentions.length === 0) {
      return [{ text: response, isHighlight: false }]
    }

    // Collect all mention positions with brand info
    const allMentions: Array<{
      start: number
      end: number
      brandName: string
      matchedText: string
    }> = []

    brandMentions.forEach((brandResult) => {
      brandResult.mentions.forEach((mention) => {
        allMentions.push({
          start: mention.start,
          end: mention.end,
          brandName: brandResult.brand_name,
          matchedText: mention.matched_text,
        })
      })
    })

    // Sort by start position
    allMentions.sort((a, b) => a.start - b.start)

    // Handle overlapping mentions by merging them
    const mergedMentions: typeof allMentions = []
    for (const mention of allMentions) {
      const last = mergedMentions[mergedMentions.length - 1]
      if (last && mention.start < last.end) {
        // Overlapping - extend the previous mention
        last.end = Math.max(last.end, mention.end)
        // Keep the longer matched text or combine brand names
        if (mention.brandName !== last.brandName) {
          last.brandName = `${last.brandName}, ${mention.brandName}`
        }
      } else {
        mergedMentions.push({ ...mention })
      }
    }

    // Build segments
    const result: TextSegment[] = []
    let currentPos = 0

    for (const mention of mergedMentions) {
      // Add text before this mention
      if (mention.start > currentPos) {
        result.push({
          text: response.slice(currentPos, mention.start),
          isHighlight: false,
        })
      }

      // Add the highlighted mention
      result.push({
        text: response.slice(mention.start, mention.end),
        isHighlight: true,
        brandName: mention.brandName,
        matchedText: mention.matchedText,
      })

      currentPos = mention.end
    }

    // Add remaining text
    if (currentPos < response.length) {
      result.push({
        text: response.slice(currentPos),
        isHighlight: false,
      })
    }

    return result
  }, [response, brandMentions])

  return (
    <div
      className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap"
      style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}
    >
      {segments.map((segment, index) =>
        segment.isHighlight ? (
          <mark
            key={index}
            className="relative group inline rounded-sm px-0.5 -mx-0.5 cursor-default transition-colors"
            style={{
              backgroundColor: `${accentColor}20`,
              color: "inherit",
              borderBottom: `1.5px solid ${accentColor}50`,
            }}
            title={segment.brandName}
          >
            {segment.text}
            {/* Tooltip on hover */}
            <span
              className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2 py-1 text-xs font-sans bg-gray-800 text-white rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10"
              style={{ maxWidth: "200px" }}
            >
              {segment.brandName}
            </span>
          </mark>
        ) : (
          <span key={index}>{segment.text}</span>
        )
      )}
    </div>
  )
}
