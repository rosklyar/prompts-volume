/**
 * PromptItem - Draggable prompt with full-screen dialog for answer
 */

import { useState } from "react"
import type { PromptInGroup, EvaluationAnswer } from "@/client/api"
import type { BrandMentionResult, DomainMentionResult } from "@/types/groups"
import type { PromptSelectionInfo } from "@/types/billing"
import { getBrandColor } from "./constants"
import { getBrandMentionOrder } from "@/lib/report-utils"
import { PromptDialog } from "./PromptDialog"

interface PromptItemProps {
  prompt: PromptInGroup & {
    answer?: EvaluationAnswer | null
    brand_mentions?: BrandMentionResult[] | null
    domain_mentions?: DomainMentionResult[] | null
    isLoading?: boolean
  }
  accentColor: string
  targetBrandName?: string | null
  competitorNames?: string[]
  onDelete: (promptId: number) => void
  selectionInfo?: PromptSelectionInfo
}


export function PromptItem({
  prompt,
  accentColor,
  targetBrandName,
  competitorNames = [],
  onDelete,
  selectionInfo,
}: PromptItemProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  // Get all brands that are mentioned in the answer
  const mentionedBrands = prompt.brand_mentions?.filter(
    (bm) => bm.mentions.length > 0
  ) || []

  // Check if target brand is among mentioned brands
  const hasTargetBrandMention = mentionedBrands.some(
    (bm) => bm.brand_name === targetBrandName
  )

  // Get brand mention order (which brand was mentioned first)
  const brandMentionOrder = getBrandMentionOrder(prompt.brand_mentions || null)

  // Get domains that are mentioned in the answer
  const mentionedDomains = prompt.domain_mentions?.filter(
    (dm) => dm.mentions.length > 0
  ) || []

  // Check if target brand's domain was mentioned
  const hasBrandDomainMention = mentionedDomains.some((dm) => dm.is_brand)

  const hasAnswer = !!prompt.answer

  return (
    <div
      style={{
        ...(hasTargetBrandMention ? { borderLeftColor: accentColor, borderLeftWidth: "3px" } : {}),
      }}
      className={`
        group relative bg-white rounded-xl border border-gray-100
        transition-all duration-200 hover:shadow-md
        ${hasTargetBrandMention ? "shadow-sm" : ""}
      `}
    >
      {/* Main prompt row */}
      <div className="flex items-start gap-3 p-3">
        {/* Prompt content - clickable when answer exists */}
        <div
          className={`flex-1 min-w-0 ${hasAnswer ? "cursor-pointer" : ""}`}
          onClick={hasAnswer ? () => setIsDialogOpen(true) : undefined}
        >
          <div className="flex items-start gap-2">
            <p className="text-[14px] leading-relaxed text-gray-800 line-clamp-2 flex-1">
              {prompt.prompt_text}
            </p>
            {/* Brand mention tags with position and domain indicators */}
            <div className="shrink-0 flex items-center gap-1.5 justify-end max-w-[220px] flex-wrap">
              {/* All brand mention tags with position rank */}
              {brandMentionOrder.map((bm) => {
                const isTargetBrand = bm.brand_name === targetBrandName
                const brandColor = getBrandColor(bm.brand_name, targetBrandName, competitorNames, accentColor)

                return (
                  <span
                    key={bm.brand_name}
                    className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] ${
                      isTargetBrand ? "font-semibold" : "font-normal"
                    }`}
                    style={{
                      backgroundColor: brandColor.bg,
                      color: brandColor.text,
                    }}
                    title={`${bm.brand_name} mentioned at position ${bm.position}`}
                  >
                    [{bm.position}] {bm.brand_name}
                  </span>
                )
              })}

              {/* Domain mention indicator - link icon if brand domain mentioned */}
              {hasBrandDomainMention && (
                <span
                  className="inline-flex items-center justify-center w-5 h-5 rounded"
                  style={{ backgroundColor: `${accentColor}15`, color: accentColor }}
                  title="Brand domain mentioned in answer"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                </span>
              )}

              {/* Domain dots for mentioned domains */}
              {mentionedDomains.length > 0 && (
                <div className="flex items-center gap-0.5">
                  {mentionedDomains.map((dm) => {
                    const brandColor = getBrandColor(dm.name, targetBrandName, competitorNames, accentColor)
                    return (
                      <span
                        key={dm.domain}
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: dm.is_brand ? accentColor : brandColor.text }}
                        title={`${dm.name} (${dm.domain}) mentioned`}
                      />
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Selection/status info */}
          {selectionInfo && (
            <div className="mt-1.5 flex items-center gap-2 text-[10px]">
              {/* Fresh options available badge */}
              {selectionInfo.available_options.some((opt) => opt.is_fresh) && (
                <span
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-medium"
                  style={{ backgroundColor: "#dcfce7", color: "#16a34a" }}
                >
                  <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  Fresh
                </span>
              )}
              {/* Options count */}
              {selectionInfo.available_options.length > 0 && (
                <span className="text-gray-400">
                  {selectionInfo.available_options.length} option{selectionInfo.available_options.length !== 1 ? "s" : ""}
                </span>
              )}
              {/* No options - awaiting */}
              {selectionInfo.available_options.length === 0 && !selectionInfo.has_in_progress_evaluation && (
                <span className="text-gray-400">
                  Awaiting evaluation
                </span>
              )}
              {/* In progress indicator */}
              {selectionInfo.has_in_progress_evaluation && (
                <span className="inline-flex items-center gap-1 text-amber-600">
                  <div
                    className="w-2 h-2 border border-amber-600 border-t-transparent rounded-full animate-spin"
                  />
                  In progress
                </span>
              )}
            </div>
          )}

          {/* Loading indicator */}
          {prompt.isLoading && (
            <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
              <div
                className="w-3 h-3 border-2 rounded-full animate-spin"
                style={{
                  borderColor: `${accentColor}30`,
                  borderTopColor: accentColor,
                }}
              />
              Loading answer...
            </div>
          )}
        </div>

        {/* Delete button */}
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDelete(prompt.prompt_id)
          }}
          className="shrink-0 w-7 h-7 rounded-md flex items-center justify-center
            text-gray-300 hover:text-red-500 hover:bg-red-50
            transition-all duration-150 opacity-0 group-hover:opacity-100
            focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-red-200"
          aria-label="Delete prompt"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Full-screen dialog for answer */}
      {hasAnswer && prompt.answer && (
        <PromptDialog
          isOpen={isDialogOpen}
          onClose={() => setIsDialogOpen(false)}
          promptText={prompt.prompt_text}
          answer={prompt.answer}
          brandMentions={prompt.brand_mentions}
          domainMentions={prompt.domain_mentions}
          accentColor={accentColor}
          targetBrandName={targetBrandName}
          competitorNames={competitorNames}
        />
      )}
    </div>
  )
}
