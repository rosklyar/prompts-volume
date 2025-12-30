/**
 * GroupSelector - Inline dropdown for selecting a target group when adding prompts
 * Editorial/magazine-inspired design matching the existing aesthetic
 * Supports keyboard navigation with Arrow keys and Enter
 * Requires brands when creating new groups
 */

import { useState, useRef, useEffect, useCallback } from "react"
import type { GroupSummary, BrandVariation } from "@/types/groups"
import { getGroupColor, MAX_GROUPS } from "./constants"
import { X, Plus, Check, Loader2, FolderPlus } from "lucide-react"

interface GroupSelectorProps {
  groups: GroupSummary[]
  isLoadingGroups: boolean
  onSelectGroup: (groupId: number) => void
  onCreateGroup: (title: string, brands: BrandVariation[]) => Promise<void>
  onCancel: () => void
  isAddingPrompt: boolean
  isCreatingGroup: boolean
  addingToGroupId?: number | null
  maxGroups?: number
}

export function GroupSelector({
  groups,
  isLoadingGroups,
  onSelectGroup,
  onCreateGroup,
  onCancel,
  isAddingPrompt,
  isCreatingGroup,
  addingToGroupId,
  maxGroups = MAX_GROUPS,
}: GroupSelectorProps) {
  const [isCreatingNew, setIsCreatingNew] = useState(false)
  const [newGroupTitle, setNewGroupTitle] = useState("")
  const [brands, setBrands] = useState<BrandVariation[]>([])
  const [newBrandName, setNewBrandName] = useState("")
  const [newBrandVariations, setNewBrandVariations] = useState("")
  const [highlightedIndex, setHighlightedIndex] = useState(0) // Start with first group highlighted
  const [isReady, setIsReady] = useState(false) // Prevent capturing the Enter that opened this selector
  const inputRef = useRef<HTMLInputElement>(null)
  const brandInputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const canCreateMore = groups.length < maxGroups
  const showEmptyState = !isLoadingGroups && groups.length === 0

  // Delay enabling keyboard handling to avoid capturing the Enter that opened the selector
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsReady(true)
    }, 100)
    return () => clearTimeout(timer)
  }, [])

  // Total items: groups + "Create new group" option (if allowed)
  const totalItems = groups.length + (canCreateMore ? 1 : 0)
  const isCreateOptionHighlighted = highlightedIndex === groups.length && canCreateMore

  // Focus input when entering create mode
  useEffect(() => {
    if ((isCreatingNew || showEmptyState) && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isCreatingNew, showEmptyState])

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll("[data-group-item]")
      const item = items[highlightedIndex] as HTMLElement
      if (item) {
        item.scrollIntoView({ block: "nearest", behavior: "smooth" })
      }
    }
  }, [highlightedIndex])

  // Handle keyboard navigation
  useEffect(() => {
    // Don't handle keyboard when in create mode (input handles its own keys)
    // Also wait until isReady to avoid capturing the Enter that opened the selector
    if (isCreatingNew || showEmptyState || isAddingPrompt || !isReady) return

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault()
          setHighlightedIndex((prev) => {
            if (totalItems === 0) return 0
            return prev < totalItems - 1 ? prev + 1 : 0
          })
          break

        case "ArrowUp":
          e.preventDefault()
          setHighlightedIndex((prev) => {
            if (totalItems === 0) return 0
            return prev > 0 ? prev - 1 : totalItems - 1
          })
          break

        case "Enter":
          e.preventDefault()
          if (isCreateOptionHighlighted) {
            setIsCreatingNew(true)
          } else if (highlightedIndex < groups.length) {
            onSelectGroup(groups[highlightedIndex].id)
          }
          break

        case "Escape":
          e.preventDefault()
          onCancel()
          break
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [isCreatingNew, showEmptyState, isAddingPrompt, isReady, highlightedIndex, totalItems, groups, canCreateMore, isCreateOptionHighlighted, onSelectGroup, onCancel])

  const handleAddBrand = useCallback(() => {
    if (!newBrandName.trim()) return
    const variations = newBrandVariations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)
    setBrands((prev) => [...prev, { name: newBrandName.trim(), variations }])
    setNewBrandName("")
    setNewBrandVariations("")
    // Focus back to brand name input for adding more
    brandInputRef.current?.focus()
  }, [newBrandName, newBrandVariations])

  const handleRemoveBrand = useCallback((index: number) => {
    setBrands((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const handleCreateGroup = useCallback(async () => {
    const trimmed = newGroupTitle.trim()
    if (!trimmed || brands.length === 0) return

    await onCreateGroup(trimmed, brands)
    setNewGroupTitle("")
    setBrands([])
    setNewBrandName("")
    setNewBrandVariations("")
    setIsCreatingNew(false)
  }, [newGroupTitle, brands, onCreateGroup])

  const handleTitleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault()
      e.stopPropagation()
      handleCancelCreate()
    }
  }

  const handleBrandKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleAddBrand()
    } else if (e.key === "Escape") {
      e.preventDefault()
      e.stopPropagation()
      handleCancelCreate()
    }
  }

  const handleCancelCreate = () => {
    if (showEmptyState) {
      onCancel()
    } else {
      setIsCreatingNew(false)
      setNewGroupTitle("")
      setBrands([])
      setNewBrandName("")
      setNewBrandVariations("")
    }
  }

  const canCreate = newGroupTitle.trim() && brands.length > 0

  // Render inline form for creating a group with required brands
  const renderCreateForm = (isEmptyState: boolean = false) => (
    <div className={`${isEmptyState ? "p-5" : "p-4 border-t border-[#F3F4F6]"}`}>
      {isEmptyState && (
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-1">
            <FolderPlus className="w-5 h-5 text-[#C4553D]" strokeWidth={1.5} />
            <h3 className="font-['Fraunces'] text-lg font-medium text-[#1F2937]">
              Create your first group
            </h3>
          </div>
          <p className="text-sm text-[#6B7280] pl-7">
            Organize prompts into groups by topic.
          </p>
        </div>
      )}
      <div className="space-y-4">
        {/* Title input */}
        <div>
          <label className="block text-xs uppercase tracking-widest text-gray-400 font-sans mb-1.5">
            Group name
          </label>
          <input
            ref={inputRef}
            type="text"
            value={newGroupTitle}
            onChange={(e) => setNewGroupTitle(e.target.value)}
            onKeyDown={handleTitleKeyDown}
            placeholder="Enter group name..."
            disabled={isCreatingGroup}
            className="w-full px-3 py-2 font-['Fraunces'] text-base
              bg-white border border-gray-200 rounded-lg
              focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
              placeholder:text-gray-400 disabled:opacity-50
              transition-all duration-200"
            maxLength={50}
          />
        </div>

        {/* Brands section */}
        <div>
          <label className="block text-xs uppercase tracking-widest text-gray-400 font-sans mb-1.5">
            Brands to Track <span className="text-[#C4553D]">*</span>
          </label>

          {/* Added brands */}
          {brands.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {brands.map((brand, index) => (
                <div
                  key={index}
                  className="flex items-center gap-1.5 px-2 py-1 bg-white border border-gray-200 rounded-md group"
                >
                  <span className="text-xs font-medium text-gray-700">{brand.name}</span>
                  {brand.variations.length > 0 && (
                    <span className="text-[10px] text-gray-400">
                      +{brand.variations.length}
                    </span>
                  )}
                  <button
                    onClick={() => handleRemoveBrand(index)}
                    className="p-0.5 rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add brand form */}
          <div className="flex gap-2">
            <div className="flex-1 space-y-1.5">
              <input
                ref={brandInputRef}
                type="text"
                value={newBrandName}
                onChange={(e) => setNewBrandName(e.target.value)}
                onKeyDown={handleBrandKeyDown}
                placeholder="Brand name (e.g., Nike)"
                disabled={isCreatingGroup}
                className="w-full px-2.5 py-1.5 text-sm
                  bg-white border border-gray-200 rounded-md
                  focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                  placeholder:text-gray-400 disabled:opacity-50"
              />
              <input
                type="text"
                value={newBrandVariations}
                onChange={(e) => setNewBrandVariations(e.target.value)}
                onKeyDown={handleBrandKeyDown}
                placeholder="Variations (optional, comma-separated)"
                disabled={isCreatingGroup}
                className="w-full px-2.5 py-1.5 text-sm
                  bg-white border border-gray-200 rounded-md
                  focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                  placeholder:text-gray-400 disabled:opacity-50"
              />
            </div>
            <button
              onClick={handleAddBrand}
              disabled={!newBrandName.trim() || isCreatingGroup}
              className="self-start px-3 py-1.5 text-sm font-medium
                bg-white border border-gray-200 rounded-md
                hover:bg-gray-50 hover:border-[#C4553D]/50 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Add
            </button>
          </div>

          {brands.length === 0 && (
            <p className="mt-1.5 text-[10px] text-gray-400 italic">
              Add at least one brand to track in reports
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
          <button
            onClick={handleCancelCreate}
            disabled={isCreatingGroup}
            className="py-2 px-3 text-sm font-medium text-gray-600
              bg-white border border-gray-200 rounded-lg
              hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleCreateGroup}
            disabled={isCreatingGroup || !canCreate}
            className="py-2 px-4 text-sm font-medium text-white
              bg-[#C4553D] rounded-lg hover:bg-[#B34835]
              transition-colors disabled:opacity-50 disabled:cursor-not-allowed
              flex items-center gap-2 min-w-[100px] justify-center"
          >
            {isCreatingGroup ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Creating...</span>
              </>
            ) : (
              "Create group"
            )}
          </button>
        </div>
      </div>
    </div>
  )

  // Loading state
  if (isLoadingGroups) {
    return (
      <div
        ref={containerRef}
        className="bg-white rounded-2xl border border-[#F3F4F6]
          shadow-[0_8px_40px_-8px_rgba(0,0,0,0.12)]
          animate-in fade-in slide-in-from-top-2 duration-200
          overflow-hidden"
        role="dialog"
        aria-label="Select a group"
      >
        <div className="flex items-center justify-center gap-3 px-6 py-8">
          <Loader2 className="w-5 h-5 text-[#C4553D] animate-spin" />
          <span className="text-[#6B7280] text-sm">Loading groups...</span>
        </div>
      </div>
    )
  }

  // Empty state - no groups exist
  if (showEmptyState) {
    return (
      <div
        ref={containerRef}
        className="bg-white rounded-2xl border border-[#F3F4F6]
          shadow-[0_8px_40px_-8px_rgba(0,0,0,0.12)]
          animate-in fade-in slide-in-from-top-2 duration-200
          overflow-hidden"
        role="dialog"
        aria-label="Create your first group"
      >
        {renderCreateForm(true)}
      </div>
    )
  }

  // Adding prompt to a specific group
  const addingToGroup = addingToGroupId
    ? groups.find((g) => g.id === addingToGroupId)
    : null

  if (isAddingPrompt && addingToGroup) {
    const groupIndex = groups.findIndex((g) => g.id === addingToGroupId)
    const color = getGroupColor(groupIndex)

    return (
      <div
        ref={containerRef}
        className="bg-white rounded-2xl border border-[#F3F4F6]
          shadow-[0_8px_40px_-8px_rgba(0,0,0,0.12)]
          animate-in fade-in slide-in-from-top-2 duration-200
          overflow-hidden"
        role="dialog"
        aria-label="Adding prompt"
      >
        <div className="flex items-center justify-center gap-3 px-6 py-6">
          <div
            className="w-5 h-5 rounded-full flex items-center justify-center"
            style={{ backgroundColor: `${color.accent}20` }}
          >
            <Loader2
              className="w-3 h-3 animate-spin"
              style={{ color: color.accent }}
            />
          </div>
          <span className="text-[#1F2937] text-sm">
            Adding to{" "}
            <span className="font-medium" style={{ color: color.accent }}>
              {addingToGroup.title}
            </span>
            ...
          </span>
        </div>
      </div>
    )
  }

  // Groups list with keyboard navigation
  return (
    <div
      ref={containerRef}
      className="bg-white rounded-2xl border border-[#F3F4F6]
        shadow-[0_8px_40px_-8px_rgba(0,0,0,0.12)]
        animate-in fade-in slide-in-from-top-2 duration-200
        overflow-hidden"
      role="listbox"
      aria-label="Select a group to add this prompt"
      aria-activedescendant={`group-option-${highlightedIndex}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#F3F4F6]">
        <span className="text-sm font-medium text-[#6B7280]">Add to group:</span>
        <button
          onClick={onCancel}
          className="p-1 rounded-md text-[#9CA3AF] hover:text-[#6B7280]
            hover:bg-[#F3F4F6] transition-colors"
          aria-label="Close"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Group list */}
      <div ref={listRef} className="max-h-[240px] overflow-y-auto">
        {groups.map((group, index) => {
          const color = getGroupColor(index)
          const isHighlighted = highlightedIndex === index

          return (
            <button
              key={group.id}
              id={`group-option-${index}`}
              data-group-item
              onClick={() => onSelectGroup(group.id)}
              onMouseEnter={() => setHighlightedIndex(index)}
              disabled={isAddingPrompt}
              className={`w-full px-4 py-3 flex items-center gap-3
                transition-all duration-150 group
                border-b border-[#F3F4F6] last:border-b-0
                disabled:opacity-50 disabled:cursor-not-allowed
                ${isHighlighted ? "bg-[#FEF7F5]" : "hover:bg-[#FEF7F5]"}`}
              role="option"
              aria-selected={isHighlighted}
            >
              {/* Color dot */}
              <span
                className={`w-2.5 h-2.5 rounded-full shrink-0 transition-transform duration-150
                  ${isHighlighted ? "scale-125" : "group-hover:scale-125"}`}
                style={{ backgroundColor: color.accent }}
              />

              {/* Group info */}
              <div className="flex-1 text-left min-w-0">
                <span
                  className={`block text-sm font-medium truncate transition-colors duration-150
                    ${isHighlighted ? "text-[#C4553D]" : "text-[#1F2937]"}`}
                >
                  {group.title}
                </span>
                <span className="text-xs text-[#9CA3AF]">
                  {group.prompt_count} prompt{group.prompt_count !== 1 ? "s" : ""}
                </span>
              </div>

              {/* Add button - visible when highlighted */}
              <span
                className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center
                  transition-all duration-150
                  ${isHighlighted
                    ? "bg-[#C4553D] text-white scale-100 opacity-100"
                    : "bg-[#F3F4F6] text-[#9CA3AF] scale-90 opacity-0 group-hover:opacity-100 group-hover:scale-100"
                  }`}
              >
                <Plus className="w-4 h-4" strokeWidth={2.5} />
              </span>
            </button>
          )
        })}

        {/* Create new group option - keyboard navigable */}
        {canCreateMore && !isCreatingNew && (
          <button
            id={`group-option-${groups.length}`}
            data-group-item
            onClick={() => setIsCreatingNew(true)}
            onMouseEnter={() => setHighlightedIndex(groups.length)}
            className={`w-full px-4 py-3 flex items-center gap-3
              text-left border-t border-[#F3F4F6]
              transition-colors group
              ${isCreateOptionHighlighted ? "bg-[#F3F4F6]" : "bg-[#FAFAFA] hover:bg-[#F3F4F6]"}`}
            role="option"
            aria-selected={isCreateOptionHighlighted}
          >
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center
                transition-colors duration-150
                ${isCreateOptionHighlighted ? "bg-[#C4553D] text-white" : "bg-[#E5E7EB] text-[#6B7280] group-hover:bg-[#C4553D] group-hover:text-white"}`}
            >
              <Plus className="w-3 h-3" strokeWidth={2.5} />
            </span>
            <span className={`text-sm transition-colors ${isCreateOptionHighlighted ? "text-[#1F2937]" : "text-[#6B7280] group-hover:text-[#1F2937]"}`}>
              Create new group...
            </span>
          </button>
        )}
      </div>

      {/* Footer - Create form when active, or max reached message */}
      {isCreatingNew ? (
        renderCreateForm(false)
      ) : !canCreateMore ? (
        <div className="px-4 py-3 border-t border-[#F3F4F6] bg-[#FAFAFA]">
          <span className="text-xs text-[#9CA3AF] flex items-center gap-2">
            <Check className="w-3 h-3" />
            Maximum {maxGroups} groups reached
          </span>
        </div>
      ) : null}

      {/* Keyboard hint */}
      {!isCreatingNew && (
        <div className="border-t border-[#F3F4F6] bg-[#FAFAFA] px-4 py-2 text-center">
          <span className="text-xs text-[#9CA3AF]">
            <kbd className="px-1 py-0.5 bg-white border border-[#D1D5DB] rounded text-[10px] font-mono">↑↓</kbd>
            {" "}navigate{" "}
            <kbd className="px-1 py-0.5 bg-white border border-[#D1D5DB] rounded text-[10px] font-mono">⏎</kbd>
            {" "}select
          </span>
        </div>
      )}
    </div>
  )
}
