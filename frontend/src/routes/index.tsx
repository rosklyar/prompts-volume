import { createFileRoute, redirect } from "@tanstack/react-router"
import { useState, useRef, useEffect, useCallback, useMemo } from "react"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { useSimilarPrompts } from "@/hooks/useSimilarPrompts"
import {
  useGroups,
  useAddPromptsToGroup,
  useAddPriorityPrompt,
} from "@/hooks/useGroups"
import { Button } from "@/components/ui/button"
import { GroupsGrid } from "@/components/groups"

export const Route = createFileRoute("/")({
  component: PromptDiscovery,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
  },
})

function PromptDiscovery() {
  const { logout, isUserLoading } = useAuth()
  const [searchQuery, setSearchQuery] = useState("")
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const { suggestions, isLoading, isFetching, shouldSearch } =
    useSimilarPrompts(searchQuery)

  // Get groups to find the common group
  const { data: groupsData } = useGroups()
  const commonGroup = useMemo(
    () => groupsData?.groups.find((g) => g.is_common),
    [groupsData]
  )

  // Mutations
  const addToGroup = useAddPromptsToGroup()
  const addPriorityPrompt = useAddPriorityPrompt()

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

  // Handle selecting an existing prompt from suggestions
  const handleSelectPrompt = useCallback(
    (prompt: { id: number; prompt_text: string }) => {
      if (commonGroup) {
        addToGroup.mutate({
          groupId: commonGroup.id,
          promptIds: [prompt.id],
        })
      }
      setSearchQuery("")
      setIsDropdownOpen(false)
      setHighlightedIndex(-1)
      inputRef.current?.focus()
    },
    [commonGroup, addToGroup]
  )

  // Handle adding a custom prompt
  const handleAddCustom = useCallback(() => {
    const trimmed = searchQuery.trim()
    if (trimmed && commonGroup) {
      addPriorityPrompt.mutate({
        promptText: trimmed,
        targetGroupId: commonGroup.id,
      })
    }
    setSearchQuery("")
    setIsDropdownOpen(false)
    setHighlightedIndex(-1)
    inputRef.current?.focus()
  }, [searchQuery, commonGroup, addPriorityPrompt])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isDropdownOpen && e.key !== "Escape") {
      if (searchQuery.trim().length >= 2) {
        setIsDropdownOpen(true)
      }
      return
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault()
        setHighlightedIndex((prev) => {
          if (totalItems === 0) return -1
          return prev < totalItems - 1 ? prev + 1 : 0
        })
        break

      case "ArrowUp":
        e.preventDefault()
        setHighlightedIndex((prev) => {
          if (totalItems === 0) return -1
          return prev > 0 ? prev - 1 : totalItems - 1
        })
        break

      case "Enter":
        e.preventDefault()
        if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
          handleSelectPrompt(suggestions[highlightedIndex])
        } else if (
          highlightedIndex === suggestions.length &&
          hasCustomOption
        ) {
          handleAddCustom()
        } else if (searchQuery.trim()) {
          // No selection, select first or add custom
          if (suggestions.length > 0) {
            handleSelectPrompt(suggestions[0])
          } else {
            handleAddCustom()
          }
        }
        break

      case "Escape":
        e.preventDefault()
        setIsDropdownOpen(false)
        setHighlightedIndex(-1)
        break

      case "Tab":
        setIsDropdownOpen(false)
        setHighlightedIndex(-1)
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
  const isAddingPrompt = addToGroup.isPending || addPriorityPrompt.isPending

  return (
    <div className="min-h-screen bg-[#FDFBF7] font-['DM_Sans']">
      {/* Minimal header */}
      <header className="absolute top-0 right-0 p-6 z-10">
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
              />
              {/* Loading indicator */}
              {(isFetching || isAddingPrompt) && (
                <div className="absolute right-5 top-1/2 -translate-y-1/2">
                  <div className="w-5 h-5 border-2 border-[#C4553D]/30 border-t-[#C4553D] rounded-full animate-spin" />
                </div>
              )}
            </div>

            {/* Suggestions dropdown */}
            {showDropdown && (
              <div
                ref={dropdownRef}
                className="absolute top-full left-0 right-0 mt-2 bg-white rounded-2xl
                  shadow-[0_8px_40px_-8px_rgba(0,0,0,0.12)]
                  border border-[#F3F4F6] overflow-hidden z-50
                  animate-in fade-in slide-in-from-top-2 duration-200
                  max-h-80 overflow-y-auto"
                role="listbox"
              >
                {isLoading && suggestions.length === 0 ? (
                  <div className="px-6 py-4 text-[#9CA3AF] text-center">
                    Searching...
                  </div>
                ) : (
                  <div ref={listRef}>
                    {/* Suggestion items */}
                    {suggestions.map((prompt, index) => {
                      const isHighlighted = index === highlightedIndex
                      return (
                        <button
                          key={prompt.id}
                          id={`suggestion-${index}`}
                          data-suggestion-item
                          onClick={() => handleSelectPrompt(prompt)}
                          onMouseEnter={() => setHighlightedIndex(index)}
                          className={`w-full px-6 py-4 text-left
                            transition-colors duration-100 flex items-center justify-between gap-4
                            border-b border-[#F3F4F6] last:border-b-0 group
                            ${isHighlighted ? "bg-[#FEF7F5]" : "hover:bg-[#FEF7F5]"}`}
                          role="option"
                          aria-selected={isHighlighted}
                        >
                          <span
                            className={`transition-colors line-clamp-2
                            ${isHighlighted ? "text-[#C4553D]" : "text-[#1F2937] group-hover:text-[#C4553D]"}`}
                          >
                            {prompt.prompt_text}
                          </span>
                          <span className="text-xs font-medium text-[#C4553D] bg-[#FEF7F5] px-2 py-1 rounded-full shrink-0">
                            {Math.round(prompt.similarity * 100)}%
                          </span>
                        </button>
                      )
                    })}

                    {/* Add custom option */}
                    {hasCustomOption && (
                      <button
                        id={`suggestion-${suggestions.length}`}
                        data-suggestion-item
                        onClick={handleAddCustom}
                        onMouseEnter={() =>
                          setHighlightedIndex(suggestions.length)
                        }
                        className={`w-full px-6 py-4 text-left
                          transition-colors duration-100 flex items-center gap-3
                          border-t border-[#E5E7EB]
                          ${highlightedIndex === suggestions.length ? "bg-[#F3F4F6]" : "bg-[#FAFAFA] hover:bg-[#F3F4F6]"}`}
                        role="option"
                        aria-selected={highlightedIndex === suggestions.length}
                      >
                        <span
                          className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium transition-colors
                          ${highlightedIndex === suggestions.length ? "bg-[#C4553D] text-white" : "bg-[#E5E7EB] text-[#6B7280]"}`}
                        >
                          +
                        </span>
                        <span className="text-[#6B7280]">
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
                        <div className="px-6 py-3 text-[#9CA3AF] text-sm border-b border-[#F3F4F6]">
                          No similar prompts found
                        </div>
                      )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Groups Grid Section */}
          <div className="mt-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-['Fraunces'] text-xl text-[#1F2937]">
                Your Prompt Groups
              </h2>
              <span className="text-xs text-[#9CA3AF]">
                Drag prompts between groups to organize
              </span>
            </div>
            <GroupsGrid />
          </div>
        </div>
      </main>
    </div>
  )
}
