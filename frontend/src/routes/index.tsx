import { createFileRoute, redirect } from "@tanstack/react-router"
import { useState, useRef, useEffect } from "react"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { useSimilarPrompts } from "@/hooks/useSimilarPrompts"
import { Button } from "@/components/ui/button"

export const Route = createFileRoute("/")({
  component: PromptDiscovery,
  beforeLoad: async () => {
    if (!isLoggedIn()) {
      throw redirect({ to: "/login" })
    }
  },
})

interface SelectedPrompt {
  id: number | string
  text: string
  isCustom: boolean
}

function PromptDiscovery() {
  const { logout, isUserLoading } = useAuth()
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedPrompts, setSelectedPrompts] = useState<SelectedPrompt[]>([])
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { suggestions, isLoading, isFetching, shouldSearch } =
    useSimilarPrompts(searchQuery)

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
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const handleSelectPrompt = (prompt: { id: number; prompt_text: string }) => {
    if (!selectedPrompts.some((p) => p.id === prompt.id)) {
      setSelectedPrompts((prev) => [
        ...prev,
        { id: prompt.id, text: prompt.prompt_text, isCustom: false },
      ])
    }
    setSearchQuery("")
    setIsDropdownOpen(false)
    inputRef.current?.focus()
  }

  const handleAddCustom = () => {
    const trimmed = searchQuery.trim()
    if (trimmed && !selectedPrompts.some((p) => p.text === trimmed)) {
      setSelectedPrompts((prev) => [
        ...prev,
        { id: `custom-${Date.now()}`, text: trimmed, isCustom: true },
      ])
    }
    setSearchQuery("")
    setIsDropdownOpen(false)
    inputRef.current?.focus()
  }

  const handleRemovePrompt = (id: number | string) => {
    setSelectedPrompts((prev) => prev.filter((p) => p.id !== id))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && searchQuery.trim()) {
      e.preventDefault()
      if (suggestions.length > 0) {
        handleSelectPrompt(suggestions[0])
      } else {
        handleAddCustom()
      }
    }
    if (e.key === "Escape") {
      setIsDropdownOpen(false)
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

  return (
    <div className="min-h-screen bg-[#FDFBF7] font-['DM_Sans']">
      {/* Minimal header */}
      <header className="absolute top-0 right-0 p-6">
        <Button
          variant="ghost"
          onClick={logout}
          className="text-[#9CA3AF] hover:text-[#1F2937] hover:bg-transparent transition-colors text-sm"
        >
          Sign out
        </Button>
      </header>

      {/* Main content - centered */}
      <main className="min-h-screen flex flex-col items-center justify-center px-4 -mt-16">
        {/* Title */}
        <div className="text-center mb-12">
          <h1 className="font-['Fraunces'] text-4xl md:text-5xl font-medium text-[#1F2937] tracking-tight">
            Prompt Discovery
          </h1>
          <p className="mt-3 text-[#6B7280] text-lg">
            Find and track prompts that matter to your business
          </p>
        </div>

        {/* Search container */}
        <div className="w-full max-w-2xl relative">
          {/* Search input */}
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                if (e.target.value.trim().length >= 2) {
                  setIsDropdownOpen(true)
                }
              }}
              onFocus={() => shouldShowDropdown && setIsDropdownOpen(true)}
              onKeyDown={handleKeyDown}
              placeholder="Search for prompts to track..."
              className="w-full px-6 py-4 text-lg bg-white rounded-2xl border-0
                shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08)]
                focus:shadow-[0_4px_32px_-4px_rgba(196,85,61,0.15)]
                focus:outline-none focus:ring-2 focus:ring-[#C4553D]/20
                placeholder:text-[#9CA3AF] text-[#1F2937]
                transition-all duration-300"
            />
            {/* Loading indicator */}
            {isFetching && (
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
                animate-in fade-in slide-in-from-top-2 duration-200"
            >
              {isLoading && suggestions.length === 0 ? (
                <div className="px-6 py-4 text-[#9CA3AF] text-center">
                  Searching...
                </div>
              ) : (
                <>
                  {/* Suggestion items */}
                  {suggestions.map((prompt, index) => (
                    <button
                      key={prompt.id}
                      onClick={() => handleSelectPrompt(prompt)}
                      className="w-full px-6 py-4 text-left hover:bg-[#FEF7F5]
                        transition-colors duration-150 flex items-center justify-between gap-4
                        border-b border-[#F3F4F6] last:border-b-0 group"
                      style={{
                        animationDelay: `${index * 30}ms`,
                      }}
                    >
                      <span className="text-[#1F2937] group-hover:text-[#C4553D] transition-colors line-clamp-2">
                        {prompt.prompt_text}
                      </span>
                      <span className="text-xs font-medium text-[#C4553D] bg-[#FEF7F5] px-2 py-1 rounded-full shrink-0">
                        {Math.round(prompt.similarity * 100)}%
                      </span>
                    </button>
                  ))}

                  {/* Add custom option */}
                  {searchQuery.trim() && (
                    <button
                      onClick={handleAddCustom}
                      className="w-full px-6 py-4 text-left hover:bg-[#F9FAFB]
                        transition-colors duration-150 flex items-center gap-3
                        border-t border-[#E5E7EB] bg-[#FAFAFA]"
                    >
                      <span className="w-6 h-6 rounded-full bg-[#C4553D] text-white flex items-center justify-center text-sm font-medium">
                        +
                      </span>
                      <span className="text-[#6B7280]">
                        Add &ldquo;
                        <span className="text-[#1F2937] font-medium">
                          {searchQuery.trim()}
                        </span>
                        &rdquo; as custom prompt
                      </span>
                    </button>
                  )}

                  {/* No results state */}
                  {!isLoading && suggestions.length === 0 && searchQuery.trim() && (
                    <div className="px-6 py-3 text-[#9CA3AF] text-sm border-b border-[#F3F4F6]">
                      No similar prompts found
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* Selected prompts */}
        {selectedPrompts.length > 0 && (
          <div className="w-full max-w-2xl mt-10">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="font-['Fraunces'] text-lg text-[#1F2937]">
                Selected Prompts
              </h2>
              <span className="text-sm text-[#9CA3AF]">
                ({selectedPrompts.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-3">
              {selectedPrompts.map((prompt, index) => (
                <div
                  key={prompt.id}
                  className="group flex items-center gap-2 px-4 py-2.5 bg-white rounded-xl
                    shadow-[0_2px_8px_-2px_rgba(0,0,0,0.06)]
                    border border-[#F3F4F6] hover:border-[#E5E7EB]
                    transition-all duration-200
                    animate-in fade-in slide-in-from-bottom-2"
                  style={{
                    animationDelay: `${index * 50}ms`,
                  }}
                >
                  {prompt.isCustom && (
                    <span className="w-1.5 h-1.5 rounded-full bg-[#C4553D]" />
                  )}
                  <span className="text-[#1F2937] text-sm max-w-xs truncate">
                    {prompt.text}
                  </span>
                  <button
                    onClick={() => handleRemovePrompt(prompt.id)}
                    className="ml-1 w-5 h-5 rounded-full flex items-center justify-center
                      text-[#9CA3AF] hover:text-[#C4553D] hover:bg-[#FEF7F5]
                      transition-colors duration-150 opacity-0 group-hover:opacity-100"
                    aria-label="Remove prompt"
                  >
                    <svg
                      className="w-3 h-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Hint text */}
        {selectedPrompts.length === 0 && (
          <p className="mt-8 text-[#9CA3AF] text-sm">
            Start typing to discover similar prompts from our database
          </p>
        )}
      </main>
    </div>
  )
}
