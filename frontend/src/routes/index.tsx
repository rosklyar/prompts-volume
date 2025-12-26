import { createFileRoute, redirect } from "@tanstack/react-router"
import { useState, useRef, useEffect, useCallback, useMemo } from "react"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { useSimilarPrompts } from "@/hooks/useSimilarPrompts"
import {
  useGroups,
  useAllGroupDetails,
  useAddPromptsToGroup,
  useAddPriorityPrompt,
  useCreateGroup,
} from "@/hooks/useGroups"
import { Button } from "@/components/ui/button"
import { GroupsGrid, GroupSelector } from "@/components/groups"
import { BalanceIndicator } from "@/components/billing"
import { Check } from "lucide-react"

export const Route = createFileRoute("/")({
  component: PromptDiscovery,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
  },
})

// Type for pending prompts (supports both single and multiple)
interface PendingPrompts {
  prompts: Array<{ id: number; text: string }>
  isCustom: boolean
}

function PromptDiscovery() {
  const { logout, isUserLoading } = useAuth()
  const [searchQuery, setSearchQuery] = useState("")
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const [justAddedIds, setJustAddedIds] = useState<Set<number>>(new Set())
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Multi-select state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [anchorIndex, setAnchorIndex] = useState<number | null>(null)

  // State for inline group selection
  const [pendingPrompts, setPendingPrompts] = useState<PendingPrompts | null>(null)
  const [showGroupSelector, setShowGroupSelector] = useState(false)
  const [addingToGroupId, setAddingToGroupId] = useState<number | null>(null)

  const { suggestions, isLoading, isFetching, shouldSearch } =
    useSimilarPrompts(searchQuery)

  // Groups data and mutations
  const { data: groupsData, isLoading: isLoadingGroups } = useGroups()
  const groups = groupsData?.groups ?? []
  const groupIds = useMemo(() => groups.map((g) => g.id), [groups])
  const { data: groupDetails } = useAllGroupDetails(groupIds)

  const addPromptsToGroup = useAddPromptsToGroup()
  const addPriorityPrompt = useAddPriorityPrompt()
  const createGroup = useCreateGroup()

  // Track which prompts are already in any group
  const alreadyAddedIds = useMemo(() => {
    const ids = new Set<number>()
    groupDetails?.forEach((group) => {
      group.prompts.forEach((p) => ids.add(p.prompt_id))
    })
    return ids
  }, [groupDetails])

  // Get selectable suggestions (not already in any group)
  const selectableSuggestions = useMemo(
    () => suggestions.filter((s) => !alreadyAddedIds.has(s.id)),
    [suggestions, alreadyAddedIds]
  )

  // Total selectable items: suggestions + custom option (if query exists)
  const hasCustomOption = searchQuery.trim().length > 0
  const totalItems = suggestions.length + (hasCustomOption ? 1 : 0)

  // Derive dropdown visibility from search state
  const shouldShowDropdown =
    shouldSearch && (suggestions.length > 0 || isLoading || searchQuery.trim())

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsDropdownOpen(false)
        setHighlightedIndex(-1)
        setShowGroupSelector(false)
        setPendingPrompts(null)
        setSelectedIds(new Set())
        setAnchorIndex(null)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll("[data-suggestion-item]")
      const item = items[highlightedIndex] as HTMLElement
      if (item) {
        item.scrollIntoView({ block: "nearest", behavior: "smooth" })
      }
    }
  }, [highlightedIndex])

  // Clear "just added" animation state after delay
  useEffect(() => {
    if (justAddedIds.size > 0) {
      const timer = setTimeout(() => {
        setJustAddedIds(new Set())
      }, 1500)
      return () => clearTimeout(timer)
    }
  }, [justAddedIds])


  // Handle clicking a prompt from search results - opens group selector
  const handlePromptClick = useCallback(
    (prompt: { id: number; prompt_text: string }) => {
      // Skip if already added to a group
      if (alreadyAddedIds.has(prompt.id)) return

      setPendingPrompts({
        prompts: [{ id: prompt.id, text: prompt.prompt_text }],
        isCustom: false,
      })
      setShowGroupSelector(true)
      setSelectedIds(new Set())
      setAnchorIndex(null)
    },
    [alreadyAddedIds]
  )

  // Handle adding selected prompts (batch) - opens group selector
  const handleAddSelected = useCallback(() => {
    if (selectedIds.size === 0) return

    const promptsToAdd = suggestions.filter(
      (s) => selectedIds.has(s.id) && !alreadyAddedIds.has(s.id)
    )
    if (promptsToAdd.length > 0) {
      setPendingPrompts({
        prompts: promptsToAdd.map((p) => ({ id: p.id, text: p.prompt_text })),
        isCustom: false,
      })
      setShowGroupSelector(true)
    }
    setSelectedIds(new Set())
    setAnchorIndex(null)
  }, [selectedIds, suggestions, alreadyAddedIds])

  // Handle clicking "Add custom prompt" - opens group selector
  const handleAddCustomClick = useCallback(() => {
    const trimmed = searchQuery.trim()
    if (!trimmed) return

    setPendingPrompts({
      prompts: [{ id: -1, text: trimmed }],
      isCustom: true,
    })
    setShowGroupSelector(true)
    setSelectedIds(new Set())
    setAnchorIndex(null)
  }, [searchQuery])

  // Handle selecting a group - adds prompt(s) to that group
  const handleSelectGroup = useCallback(
    async (groupId: number) => {
      if (!pendingPrompts || pendingPrompts.prompts.length === 0) return

      setAddingToGroupId(groupId)

      try {
        if (pendingPrompts.isCustom) {
          // Create custom prompt and add to group in one operation
          await addPriorityPrompt.mutateAsync({
            promptText: pendingPrompts.prompts[0].text,
            targetGroupId: groupId,
          })
        } else {
          // Add existing prompt(s) to group
          const promptIds = pendingPrompts.prompts.map((p) => p.id)
          await addPromptsToGroup.mutateAsync({
            groupId,
            promptIds,
          })
          // Show "just added" animation
          setJustAddedIds((prev) => new Set([...prev, ...promptIds]))
        }

        // Success - reset state
        setShowGroupSelector(false)
        setPendingPrompts(null)
        setAddingToGroupId(null)
        // Reset highlight so Shift+Down starts fresh from first selectable
        setHighlightedIndex(-1)
        // Keep dropdown open for continued discovery - defer focus to after re-render
        setTimeout(() => inputRef.current?.focus(), 0)
      } catch (error) {
        console.error("Failed to add prompt(s) to group:", error)
        setAddingToGroupId(null)
      }
    },
    [pendingPrompts, addPriorityPrompt, addPromptsToGroup]
  )

  // Handle creating a new group (from GroupSelector)
  const handleCreateGroup = useCallback(
    async (title: string) => {
      const result = await createGroup.mutateAsync({ title })
      // After creating, auto-select the new group
      if (result?.id && pendingPrompts) {
        await handleSelectGroup(result.id)
      }
    },
    [createGroup, pendingPrompts, handleSelectGroup]
  )

  // Handle canceling group selection
  const handleCancelGroupSelection = useCallback(() => {
    setShowGroupSelector(false)
    setPendingPrompts(null)
    setAddingToGroupId(null)
    inputRef.current?.focus()
  }, [])

  // Helper to find next selectable index (skipping already-added items)
  const findNextSelectableIndex = useCallback(
    (startIndex: number, direction: "up" | "down"): number => {
      const step = direction === "down" ? 1 : -1
      let index = startIndex + step

      while (index >= 0 && index < suggestions.length) {
        const prompt = suggestions[index]
        if (prompt && !alreadyAddedIds.has(prompt.id)) {
          return index
        }
        index += step
      }
      return -1 // No selectable item found
    },
    [suggestions, alreadyAddedIds]
  )

  // Helper to extend selection in a direction
  const extendSelection = useCallback(
    (direction: "up" | "down") => {
      // Find current starting position
      let currentIndex = highlightedIndex >= 0 ? highlightedIndex : -1

      // If no highlight or current is already-added, find first selectable
      if (currentIndex === -1 || alreadyAddedIds.has(suggestions[currentIndex]?.id)) {
        const firstSelectable = suggestions.findIndex(
          (s) => !alreadyAddedIds.has(s.id)
        )
        if (firstSelectable === -1) return // No selectable items
        currentIndex = firstSelectable
      }

      // Find next selectable item in the direction
      const newIndex = findNextSelectableIndex(currentIndex, direction)

      if (newIndex === -1) {
        // No more selectable items in that direction, just highlight current
        setHighlightedIndex(currentIndex)
        if (anchorIndex === null) {
          const currentPrompt = suggestions[currentIndex]
          if (currentPrompt) {
            setAnchorIndex(currentIndex)
            setSelectedIds(new Set([currentPrompt.id]))
          }
        }
        return
      }

      const targetPrompt = suggestions[newIndex]

      // Set anchor if not set
      if (anchorIndex === null) {
        const currentPrompt = suggestions[currentIndex]
        if (currentPrompt && !alreadyAddedIds.has(currentPrompt.id)) {
          setAnchorIndex(currentIndex)
          setSelectedIds(new Set([currentPrompt.id, targetPrompt.id]))
        } else {
          setAnchorIndex(newIndex)
          setSelectedIds(new Set([targetPrompt.id]))
        }
      } else {
        // Extend selection from anchor to new index
        const start = Math.min(anchorIndex, newIndex)
        const end = Math.max(anchorIndex, newIndex)
        const newSelected = new Set<number>()
        for (let i = start; i <= end; i++) {
          const prompt = suggestions[i]
          if (prompt && !alreadyAddedIds.has(prompt.id)) {
            newSelected.add(prompt.id)
          }
        }
        setSelectedIds(newSelected)
      }
      setHighlightedIndex(newIndex)
    },
    [highlightedIndex, suggestions, alreadyAddedIds, anchorIndex, findNextSelectableIndex]
  )

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // If group selector is open, let it handle its own keys
    if (showGroupSelector) {
      if (e.key === "Escape") {
        e.preventDefault()
        // Close everything and clear text
        handleCancelGroupSelection()
        setIsDropdownOpen(false)
        setHighlightedIndex(-1)
        setSelectedIds(new Set())
        setAnchorIndex(null)
        setSearchQuery("")
      }
      return
    }

    if (!isDropdownOpen && e.key !== "Escape") {
      if (searchQuery.trim().length >= 2) {
        setIsDropdownOpen(true)
      }
      return
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault()
        if (e.shiftKey && suggestions.length > 0) {
          // Extend selection downward
          extendSelection("down")
        } else {
          // Normal navigation - clear selection
          setSelectedIds(new Set())
          setAnchorIndex(null)
          setHighlightedIndex((prev) => {
            if (totalItems === 0) return -1
            return prev < totalItems - 1 ? prev + 1 : 0
          })
        }
        break

      case "ArrowUp":
        e.preventDefault()
        if (e.shiftKey && suggestions.length > 0) {
          // Extend selection upward
          extendSelection("up")
        } else {
          // Normal navigation - clear selection
          setSelectedIds(new Set())
          setAnchorIndex(null)
          setHighlightedIndex((prev) => {
            if (totalItems === 0) return -1
            return prev > 0 ? prev - 1 : totalItems - 1
          })
        }
        break

      case "Enter":
        e.preventDefault()
        if (selectedIds.size > 0) {
          // Batch add all selected - opens group selector
          handleAddSelected()
        } else if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
          handlePromptClick(suggestions[highlightedIndex])
        } else if (
          highlightedIndex === suggestions.length &&
          hasCustomOption
        ) {
          handleAddCustomClick()
        } else if (searchQuery.trim()) {
          // No selection, select first or add custom
          if (suggestions.length > 0) {
            handlePromptClick(suggestions[0])
          } else {
            handleAddCustomClick()
          }
        }
        break

      case "Escape":
        e.preventDefault()
        // Close dropdown, clear selection and text field
        setIsDropdownOpen(false)
        setHighlightedIndex(-1)
        setSelectedIds(new Set())
        setAnchorIndex(null)
        setSearchQuery("")
        break

      case "Tab":
        setIsDropdownOpen(false)
        setHighlightedIndex(-1)
        setSelectedIds(new Set())
        setAnchorIndex(null)
        break
    }
  }

  if (isUserLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FDFBF7]">
        <div className="animate-pulse text-[#6B7280] font-['DM_Sans']">
          Loading...
        </div>
      </div>
    )
  }

  const showDropdown = isDropdownOpen && shouldShowDropdown
  const isAddingPrompt =
    addPromptsToGroup.isPending || addPriorityPrompt.isPending

  return (
    <div className="min-h-screen bg-[#FDFBF7] font-['DM_Sans']">
      {/* Minimal header */}
      <header className="absolute top-0 right-0 p-6 z-10 flex items-center gap-3">
        <BalanceIndicator />
        <Button
          variant="ghost"
          onClick={logout}
          className="text-[#9CA3AF] hover:text-[#1F2937] hover:bg-transparent transition-colors text-sm"
        >
          Sign out
        </Button>
      </header>

      {/* Main content */}
      <main className="pt-20 pb-12 px-4 md:px-8 lg:px-12">
        {/* Title and search - centered at top */}
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="font-['Fraunces'] text-3xl md:text-4xl font-medium text-[#1F2937] tracking-tight">
              Prompt Discovery
            </h1>
            <p className="mt-2 text-[#6B7280] text-base">
              Find and organize prompts that matter to your business
            </p>
          </div>

          {/* Search container */}
          <div className="max-w-2xl mx-auto relative mb-10">
            {/* Search input */}
            <div className="relative">
              <input
                ref={inputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  setHighlightedIndex(-1)
                  // Clear selection when search query changes
                  setSelectedIds(new Set())
                  setAnchorIndex(null)
                  // Close group selector when typing
                  if (showGroupSelector) {
                    setShowGroupSelector(false)
                    setPendingPrompts(null)
                  }
                  if (e.target.value.trim().length >= 2) {
                    setIsDropdownOpen(true)
                  }
                }}
                onFocus={() => shouldShowDropdown && setIsDropdownOpen(true)}
                onKeyDown={handleKeyDown}
                placeholder="Search for prompts to track..."
                disabled={isAddingPrompt}
                className="w-full px-6 py-4 text-lg bg-white rounded-2xl border-0
                  shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)]
                  focus:shadow-[0_4px_32px_-4px_rgba(196,85,61,0.15)]
                  focus:outline-none focus:ring-2 focus:ring-[#C4553D]/20
                  placeholder:text-[#9CA3AF] text-[#1F2937]
                  transition-all duration-300
                  disabled:opacity-50"
                role="combobox"
                aria-expanded={!!showDropdown}
                aria-haspopup="listbox"
                aria-activedescendant={
                  highlightedIndex >= 0
                    ? `suggestion-${highlightedIndex}`
                    : undefined
                }
                aria-describedby="selection-status"
              />
              {/* Screen reader announcement for selection */}
              <div id="selection-status" className="sr-only" aria-live="polite">
                {selectedIds.size > 0
                  ? `${selectedIds.size} item${selectedIds.size > 1 ? "s" : ""} selected`
                  : ""}
              </div>
              {/* Loading indicator */}
              {(isFetching || isAddingPrompt) && (
                <div className="absolute right-5 top-1/2 -translate-y-1/2">
                  <div className="w-5 h-5 border-2 border-[#C4553D]/30 border-t-[#C4553D] rounded-full animate-spin" />
                </div>
              )}
            </div>

            {/* Dropdown - either suggestions or group selector */}
            {showDropdown && (
              <div
                ref={dropdownRef}
                className="absolute top-full left-0 right-0 mt-2 z-50"
              >
                {showGroupSelector ? (
                  // Group selector inline
                  <GroupSelector
                    groups={groups}
                    isLoadingGroups={isLoadingGroups}
                    onSelectGroup={handleSelectGroup}
                    onCreateGroup={handleCreateGroup}
                    onCancel={handleCancelGroupSelection}
                    isAddingPrompt={isAddingPrompt}
                    isCreatingGroup={createGroup.isPending}
                    addingToGroupId={addingToGroupId}
                  />
                ) : (
                  // Suggestions dropdown
                  <div
                    className="bg-white rounded-2xl
                      shadow-[0_8px_40px_-8px_rgba(0,0,0,0.12)]
                      border border-[#F3F4F6] overflow-hidden
                      animate-in fade-in slide-in-from-top-2 duration-200
                      max-h-80 flex flex-col"
                    role="listbox"
                    aria-multiselectable="true"
                    aria-label="Search results"
                  >
                    {isLoading && suggestions.length === 0 ? (
                      <div className="px-6 py-4 text-[#9CA3AF] text-center">
                        Searching...
                      </div>
                    ) : (
                      <>
                        <div ref={listRef} className="overflow-y-auto flex-1">
                          {/* Suggestion items */}
                          {suggestions.map((prompt, index) => {
                            const isHighlighted = index === highlightedIndex
                            const isSelected = selectedIds.has(prompt.id)
                            const isAlreadyAdded = alreadyAddedIds.has(prompt.id)
                            const wasJustAdded = justAddedIds.has(prompt.id)

                            return (
                              <button
                                key={prompt.id}
                                id={`suggestion-${index}`}
                                data-suggestion-item
                                onClick={() =>
                                  !isAlreadyAdded && handlePromptClick(prompt)
                                }
                                onMouseEnter={() => setHighlightedIndex(index)}
                                disabled={isAlreadyAdded}
                                className={`w-full px-4 py-3 text-left
                                  transition-all duration-150 flex items-center gap-3
                                  border-b border-[#F3F4F6] last:border-b-0 group
                                  ${
                                    isAlreadyAdded
                                      ? "opacity-50 cursor-default"
                                      : isSelected
                                        ? "bg-[#C4553D]/10 border-l-2 border-l-[#C4553D]"
                                        : isHighlighted
                                          ? "bg-[#FEF7F5]"
                                          : "hover:bg-[#FEF7F5]"
                                  }
                                  ${wasJustAdded ? "animate-[addedFlash_0.5s_ease-out]" : ""}`}
                                role="option"
                                aria-selected={isSelected || isHighlighted}
                                aria-disabled={isAlreadyAdded}
                              >
                                {/* Selection indicator */}
                                <span
                                  className={`w-5 h-5 rounded flex items-center justify-center shrink-0 transition-all duration-150
                                    ${
                                      isAlreadyAdded
                                        ? "bg-[#E5E7EB] text-[#9CA3AF]"
                                        : isSelected
                                          ? "bg-[#C4553D] text-white scale-110"
                                          : "border-2 border-[#D1D5DB] group-hover:border-[#C4553D]/50"
                                    }`}
                                >
                                  {(isAlreadyAdded || isSelected) && (
                                    <Check className="w-3 h-3" strokeWidth={3} />
                                  )}
                                </span>

                                {/* Prompt text */}
                                <span
                                  className={`flex-1 transition-colors line-clamp-2 text-sm
                                    ${
                                      isAlreadyAdded
                                        ? "text-[#9CA3AF]"
                                        : isSelected
                                          ? "text-[#C4553D] font-medium"
                                          : isHighlighted
                                            ? "text-[#C4553D]"
                                            : "text-[#1F2937] group-hover:text-[#C4553D]"
                                    }`}
                                >
                                  {prompt.prompt_text}
                                </span>

                                {/* Status badges */}
                                <div className="flex items-center gap-2 shrink-0">
                                  {isAlreadyAdded ? (
                                    <span className="text-xs text-[#9CA3AF] bg-[#F3F4F6] px-2 py-0.5 rounded-full">
                                      Added
                                    </span>
                                  ) : (
                                    <span className="text-xs font-medium text-[#C4553D] bg-[#FEF7F5] px-2 py-0.5 rounded-full">
                                      {Math.round(prompt.similarity * 100)}%
                                    </span>
                                  )}
                                </div>
                              </button>
                            )
                          })}

                          {/* Add custom option */}
                          {hasCustomOption && (
                            <button
                              id={`suggestion-${suggestions.length}`}
                              data-suggestion-item
                              onClick={handleAddCustomClick}
                              onMouseEnter={() =>
                                setHighlightedIndex(suggestions.length)
                              }
                              className={`w-full px-4 py-3 text-left
                                transition-colors duration-100 flex items-center gap-3
                                border-t border-[#E5E7EB]
                                ${highlightedIndex === suggestions.length ? "bg-[#F3F4F6]" : "bg-[#FAFAFA] hover:bg-[#F3F4F6]"}`}
                              role="option"
                              aria-selected={
                                highlightedIndex === suggestions.length
                              }
                            >
                              <span
                                className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium transition-colors
                                ${highlightedIndex === suggestions.length ? "bg-[#C4553D] text-white" : "bg-[#E5E7EB] text-[#6B7280]"}`}
                              >
                                +
                              </span>
                              <span className="text-[#6B7280] text-sm">
                                Add &ldquo;
                                <span
                                  className={`font-medium transition-colors
                                  ${highlightedIndex === suggestions.length ? "text-[#C4553D]" : "text-[#1F2937]"}`}
                                >
                                  {searchQuery.trim()}
                                </span>
                                &rdquo; as priority prompt
                              </span>
                            </button>
                          )}

                          {/* No results state */}
                          {!isLoading &&
                            suggestions.length === 0 &&
                            searchQuery.trim() && (
                              <div className="px-4 py-3 text-[#9CA3AF] text-sm border-b border-[#F3F4F6]">
                                No similar prompts found
                              </div>
                            )}
                        </div>

                        {/* Action bar - shows when items are selected */}
                        {selectedIds.size > 0 && (
                          <div className="sticky bottom-0 border-t border-[#E5E7EB] bg-[#FAFAFA] px-4 py-2.5 flex items-center justify-between">
                            <span className="text-sm text-[#6B7280]">
                              <kbd className="px-1.5 py-0.5 bg-white border border-[#D1D5DB] rounded text-xs font-mono mr-1">⏎</kbd>
                              Add {selectedIds.size} prompt{selectedIds.size > 1 ? "s" : ""} to a group
                            </span>
                            <span className="text-sm text-[#9CA3AF]">
                              <kbd className="px-1.5 py-0.5 bg-white border border-[#D1D5DB] rounded text-xs font-mono mr-1">Esc</kbd>
                              Cancel
                            </span>
                          </div>
                        )}

                        {/* Hint for multi-select when no selection */}
                        {selectedIds.size === 0 && selectableSuggestions.length > 1 && (
                          <div className="border-t border-[#F3F4F6] bg-[#FAFAFA] px-4 py-2 text-center">
                            <span className="text-xs text-[#9CA3AF]">
                              <kbd className="px-1 py-0.5 bg-white border border-[#D1D5DB] rounded text-[10px] font-mono">Shift</kbd>
                              +
                              <kbd className="px-1 py-0.5 bg-white border border-[#D1D5DB] rounded text-[10px] font-mono">↓</kbd>
                              to select multiple
                            </span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Groups Grid Section */}
          <div className="mt-8">
            <GroupsGrid />
          </div>
        </div>
      </main>
    </div>
  )
}
