/**
 * HighlightedResponse - Renders response text with highlighted brand and domain mentions
 * Editorial aesthetic with subtle annotation styling
 */

import { useMemo } from "react"
import type { BrandMentionResult, DomainMentionResult } from "@/types/groups"
import { getBrandColor } from "./constants"

interface HighlightedResponseProps {
  response: string
  brandMentions: BrandMentionResult[] | null
  domainMentions?: DomainMentionResult[] | null
  accentColor: string
  targetBrandName?: string | null
  competitorNames?: string[]
}

interface TextSegment {
  text: string
  isHighlight: boolean
  highlightType?: "brand" | "domain"
  brandName?: string
  matchedText?: string
  isBrand?: boolean // For domain mentions: is it the target brand's domain?
}

/**
 * Convert Python code point index to JavaScript string index.
 *
 * Python strings use Unicode code points (emojis = 1 char).
 * JavaScript strings use UTF-16 code units (emojis = 2 chars as surrogate pairs).
 *
 * This function converts a code point index to the corresponding string index.
 */
function codePointIndexToStringIndex(str: string, codePointIndex: number): number {
  let stringIndex = 0
  let codePointCount = 0

  while (codePointCount < codePointIndex && stringIndex < str.length) {
    const codePoint = str.codePointAt(stringIndex)
    if (codePoint === undefined) break

    // Characters outside BMP (code point > 0xFFFF) use 2 code units (surrogate pair)
    stringIndex += codePoint > 0xffff ? 2 : 1
    codePointCount++
  }

  return stringIndex
}

export function HighlightedResponse({
  response,
  brandMentions,
  domainMentions,
  accentColor,
  targetBrandName,
  competitorNames = [],
}: HighlightedResponseProps) {
  // Parse response into segments with highlights
  const segments = useMemo((): TextSegment[] => {
    const hasBrandMentions = brandMentions && brandMentions.length > 0
    const hasDomainMentions = domainMentions && domainMentions.length > 0

    if (!hasBrandMentions && !hasDomainMentions) {
      return [{ text: response, isHighlight: false }]
    }

    // Collect all mention positions with brand/domain info
    // Convert Python code point indices to JavaScript string indices
    const allMentions: Array<{
      start: number
      end: number
      brandName: string
      matchedText: string
      highlightType: "brand" | "domain"
      isBrand?: boolean
    }> = []

    // Add brand mentions
    if (hasBrandMentions) {
      brandMentions!.forEach((brandResult) => {
        brandResult.mentions.forEach((mention) => {
          allMentions.push({
            start: codePointIndexToStringIndex(response, mention.start),
            end: codePointIndexToStringIndex(response, mention.end),
            brandName: brandResult.brand_name,
            matchedText: mention.matched_text,
            highlightType: "brand",
          })
        })
      })
    }

    // Add domain mentions
    if (hasDomainMentions) {
      domainMentions!.forEach((domainResult) => {
        domainResult.mentions.forEach((mention) => {
          allMentions.push({
            start: codePointIndexToStringIndex(response, mention.start),
            end: codePointIndexToStringIndex(response, mention.end),
            brandName: domainResult.name,
            matchedText: mention.matched_text,
            highlightType: "domain",
            isBrand: domainResult.is_brand,
          })
        })
      })
    }

    // Sort by start position
    allMentions.sort((a, b) => a.start - b.start)

    // Handle overlapping mentions by merging them
    // Prefer brand mentions over domain mentions (brand takes precedence in styling)
    const mergedMentions: typeof allMentions = []
    for (const mention of allMentions) {
      const last = mergedMentions[mergedMentions.length - 1]
      if (last && mention.start < last.end) {
        // Overlapping - extend the previous mention
        last.end = Math.max(last.end, mention.end)
        // Brand mentions take precedence over domain mentions
        if (mention.highlightType === "brand" && last.highlightType === "domain") {
          last.highlightType = "brand"
          last.brandName = mention.brandName
        } else if (last.highlightType === mention.highlightType && mention.brandName !== last.brandName) {
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
        highlightType: mention.highlightType,
        brandName: mention.brandName,
        matchedText: mention.matchedText,
        isBrand: mention.isBrand,
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
  }, [response, brandMentions, domainMentions])

  return (
    <div
      className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap"
      style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}
    >
      {segments.map((segment, index) => {
        if (!segment.isHighlight) {
          return <span key={index}>{segment.text}</span>
        }

        // Get the first brand name for color (in case of merged overlapping mentions)
        const primaryBrandName = segment.brandName?.split(", ")[0] ?? ""
        const brandColor = getBrandColor(primaryBrandName, targetBrandName, competitorNames, accentColor)

        // Different styling for brand vs domain mentions
        if (segment.highlightType === "domain") {
          // Domain mentions: underline style (link-like)
          return (
            <mark
              key={index}
              className="inline rounded-sm px-0.5 -mx-0.5 cursor-default transition-colors"
              style={{
                backgroundColor: `${brandColor.bg}`,
                color: brandColor.text,
                textDecoration: "underline",
                textDecorationColor: `${brandColor.text}60`,
                textDecorationThickness: "1px",
                textUnderlineOffset: "2px",
              }}
              title={`${segment.brandName} domain: ${segment.matchedText}`}
            >
              {segment.text}
            </mark>
          )
        }

        // Brand mentions: background highlight + bottom border
        return (
          <mark
            key={index}
            className="inline rounded-sm px-0.5 -mx-0.5 cursor-default transition-colors"
            style={{
              backgroundColor: brandColor.bg,
              color: "inherit",
              borderBottom: `1.5px solid ${brandColor.text}50`,
            }}
            title={segment.brandName}
          >
            {segment.text}
          </mark>
        )
      })}
    </div>
  )
}
