/**
 * DiscoveredCompetitorCard - Selectable, editable card for discovered competitors
 * Supports selection toggle and inline editing of name, domain, and variations
 */

import { useState, useCallback, type KeyboardEvent, type ChangeEvent } from "react"
import { Check, Pencil, X, Globe } from "lucide-react"
import type { CompetitorInfo } from "@/types/groups"

interface DiscoveredCompetitorCardProps {
  competitor: CompetitorInfo
  isSelected: boolean
  onToggleSelect: () => void
  onUpdate: (updated: CompetitorInfo) => void
}

const MAX_VISIBLE_VARIATIONS = 3

export function DiscoveredCompetitorCard({
  competitor,
  isSelected,
  onToggleSelect,
  onUpdate,
}: DiscoveredCompetitorCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  // Edit state - only used when expanded, initialized when entering edit mode
  const [editedName, setEditedName] = useState("")
  const [editedDomain, setEditedDomain] = useState("")
  const [editedVariations, setEditedVariations] = useState<string[]>([])
  const [newVariation, setNewVariation] = useState("")

  const handleEditClick = useCallback(() => {
    if (isExpanded) {
      // Save changes
      onUpdate({
        name: editedName.trim() || competitor.name,
        domain: editedDomain.trim() || null,
        variations: editedVariations,
      })
      setIsExpanded(false)
    } else {
      // Enter edit mode - copy current values to state
      setEditedName(competitor.name)
      setEditedDomain(competitor.domain || "")
      setEditedVariations(competitor.variations || [])
      setNewVariation("")
      setIsExpanded(true)
    }
  }, [isExpanded, editedName, editedDomain, editedVariations, competitor, onUpdate])

  const handleRemoveVariation = useCallback((index: number) => {
    setEditedVariations((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleAddVariation = useCallback(() => {
    const trimmed = newVariation.trim()
    if (trimmed && !editedVariations.includes(trimmed)) {
      setEditedVariations((prev) => [...prev, trimmed])
      setNewVariation("")
    }
  }, [newVariation, editedVariations])

  const handleVariationKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault()
        handleAddVariation()
      }
    },
    [handleAddVariation]
  )

  const handleNewVariationChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setNewVariation(e.target.value)
  }, [])

  // Use props directly for display (no stale state issues)
  const variations = competitor.variations || []
  const visibleVariations = variations.slice(0, MAX_VISIBLE_VARIATIONS)
  const hiddenCount = variations.length - MAX_VISIBLE_VARIATIONS

  return (
    <div
      className={`
        rounded-xl border-2 transition-all duration-200
        ${
          isSelected
            ? "border-[#C4553D]/30 bg-white shadow-sm"
            : "border-gray-200 bg-gray-50/50 opacity-60"
        }
        ${isExpanded ? "ring-2 ring-[#C4553D]/20" : ""}
      `}
    >
      {/* Header row */}
      <div className="flex items-start gap-3 p-4">
        {/* Checkbox */}
        <button
          type="button"
          onClick={onToggleSelect}
          className={`
            flex-shrink-0 w-5 h-5 rounded border-2 transition-all duration-150
            flex items-center justify-center mt-0.5
            ${
              isSelected
                ? "bg-[#C4553D] border-[#C4553D]"
                : "border-gray-300 hover:border-gray-400"
            }
          `}
        >
          {isSelected && <Check className="w-3 h-3 text-white" />}
        </button>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {isExpanded ? (
            /* Expanded edit mode */
            <div className="space-y-3">
              {/* Name input */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Brand name</label>
                <input
                  type="text"
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  className="w-full px-3 py-2 text-sm font-medium bg-white border border-gray-200
                             rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30
                             focus:border-[#C4553D]"
                  placeholder="Competitor name"
                />
              </div>

              {/* Domain input */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Website</label>
                <div className="relative">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    value={editedDomain}
                    onChange={(e) => setEditedDomain(e.target.value)}
                    className="w-full pl-10 pr-3 py-2 text-sm bg-white border border-gray-200
                               rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30
                               focus:border-[#C4553D]"
                    placeholder="website.com"
                  />
                </div>
              </div>

              {/* Variations */}
              <div>
                <label className="block text-xs text-gray-500 mb-1">Name variations</label>
                <div className="flex flex-wrap gap-1.5 p-2 bg-gray-50 rounded-lg border border-gray-200 min-h-[60px]">
                  {editedVariations.map((v, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 px-2 py-1
                                 bg-white text-gray-700 text-xs rounded-md border border-gray-200
                                 group hover:border-gray-300 transition-colors"
                    >
                      {v}
                      <button
                        type="button"
                        onClick={() => handleRemoveVariation(i)}
                        className="text-gray-400 hover:text-red-500 transition-colors"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                  {/* Add new variation input */}
                  <input
                    type="text"
                    value={newVariation}
                    onChange={handleNewVariationChange}
                    onKeyDown={handleVariationKeyDown}
                    onBlur={handleAddVariation}
                    placeholder="+ add variation"
                    className="px-2 py-1 text-xs bg-white border border-dashed
                               border-gray-300 rounded-md min-w-[100px] flex-1
                               focus:border-[#C4553D] focus:outline-none"
                  />
                </div>
              </div>
            </div>
          ) : (
            /* Collapsed view - uses props directly */
            <div>
              <div className="flex items-center gap-2 mb-1">
                <p className="font-medium text-gray-800">{competitor.name}</p>
                <span
                  className="flex-shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-full
                             bg-purple-50 text-purple-600 border border-purple-100"
                >
                  AI
                </span>
              </div>
              {competitor.domain && (
                <p className="text-sm text-gray-500 mb-2">{competitor.domain}</p>
              )}
              {visibleVariations.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {visibleVariations.map((v, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-md"
                    >
                      {v}
                    </span>
                  ))}
                  {hiddenCount > 0 && (
                    <span className="px-2 py-0.5 text-gray-400 text-xs">
                      +{hiddenCount} more
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Edit button */}
        <button
          type="button"
          onClick={handleEditClick}
          className={`
            flex-shrink-0 p-2 rounded-lg transition-colors
            ${isExpanded
              ? "bg-[#C4553D] text-white hover:bg-[#B34835]"
              : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
            }
          `}
        >
          {isExpanded ? (
            <Check className="w-4 h-4" />
          ) : (
            <Pencil className="w-4 h-4" />
          )}
        </button>
      </div>
    </div>
  )
}
