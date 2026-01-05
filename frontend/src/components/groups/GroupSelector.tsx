/**
 * GroupSelector - Inline dropdown for selecting a target group when adding prompts
 * Editorial/magazine-inspired design matching the existing aesthetic
 * Supports keyboard navigation with Arrow keys and Enter
 * Requires brands when creating new groups
 */

import { useState, useRef, useEffect, useCallback, useMemo } from "react"
import type { GroupSummary, BrandInfo, CompetitorInfo, TopicInput } from "@/types/groups"
import { getGroupColor, MAX_GROUPS } from "./constants"
import { X, Plus, Check, Loader2, FolderPlus, Globe, MapPin, Briefcase, Tag, ChevronRight } from "lucide-react"
import { useCountries, useBusinessDomains, useTopicsFiltered } from "@/hooks/useTopics"

interface GroupSelectorProps {
  groups: GroupSummary[]
  isLoadingGroups: boolean
  onSelectGroup: (groupId: number) => void
  onCreateGroup: (title: string, topic: TopicInput, brand: BrandInfo, competitors?: CompetitorInfo[]) => Promise<void>
  onCancel: () => void
  isAddingPrompt: boolean
  isCreatingGroup: boolean
  addingToGroupId?: number | null
  maxGroups?: number
  /** Default topic ID to use when creating a group (from inspiration flow) */
  defaultTopicId?: number
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
  defaultTopicId,
}: GroupSelectorProps) {
  const [isCreatingNew, setIsCreatingNew] = useState(false)
  const [creationStep, setCreationStep] = useState<"topic" | "details">("topic")
  const [newGroupTitle, setNewGroupTitle] = useState("")
  const [brandName, setBrandName] = useState("")
  const [brandDomain, setBrandDomain] = useState("")
  const [brandVariations, setBrandVariations] = useState("")
  const [brandVariationsTouched, setBrandVariationsTouched] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(0) // Start with first group highlighted
  const [isReady, setIsReady] = useState(false) // Prevent capturing the Enter that opened this selector

  // Topic selection state (used when defaultTopicId is not provided)
  const [selectedCountryId, setSelectedCountryId] = useState<number | undefined>()
  const [selectedBusinessDomainId, setSelectedBusinessDomainId] = useState<number | undefined>()
  const [selectedTopicId, setSelectedTopicId] = useState<number | undefined>()
  const [isCreatingNewTopic, setIsCreatingNewTopic] = useState(false)
  const [newTopicTitle, setNewTopicTitle] = useState("")
  const [newTopicDescription, setNewTopicDescription] = useState("")

  const inputRef = useRef<HTMLInputElement>(null)
  const brandInputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  // Fetch topic reference data (only when defaultTopicId is not provided)
  const needsTopicSelection = defaultTopicId === undefined
  const { data: countriesData, isLoading: isLoadingCountries } = useCountries()
  const { data: businessDomainsData, isLoading: isLoadingDomains } = useBusinessDomains()
  const { data: topicsData, isLoading: isLoadingTopics } = useTopicsFiltered(
    selectedCountryId,
    selectedBusinessDomainId
  )

  // Get selected topic info for display
  const selectedTopic = useMemo(() => {
    if (!topicsData?.topics || !selectedTopicId) return null
    return topicsData.topics.find(t => t.id === selectedTopicId)
  }, [topicsData, selectedTopicId])

  const selectedCountry = useMemo(() => {
    if (!countriesData?.countries || !selectedCountryId) return null
    return countriesData.countries.find(c => c.id === selectedCountryId)
  }, [countriesData, selectedCountryId])

  const selectedBusinessDomain = useMemo(() => {
    if (!businessDomainsData?.business_domains || !selectedBusinessDomainId) return null
    return businessDomainsData.business_domains.find(b => b.id === selectedBusinessDomainId)
  }, [businessDomainsData, selectedBusinessDomainId])

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

  function normalizeDomain(url: string): string {
    let domain = url.trim().toLowerCase()
    if (!domain) return ""
    if (domain.startsWith("http://") || domain.startsWith("https://")) {
      domain = domain.split("://")[1]
    }
    domain = domain.replace(/\/$/, "")
    return domain
  }

  // Handle brand name change with prefill logic
  const handleBrandNameChange = (value: string) => {
    setBrandName(value)
    if (!brandVariationsTouched) {
      setBrandVariations(value.trim())
    }
  }

  const handleCreateGroup = useCallback(async () => {
    const trimmed = newGroupTitle.trim()
    const trimmedBrandName = brandName.trim()
    if (!trimmed || !trimmedBrandName) return

    // Build topic input - either from defaultTopicId or from user selection
    let topicInput: TopicInput
    if (defaultTopicId !== undefined) {
      topicInput = { existing_topic_id: defaultTopicId }
    } else if (isCreatingNewTopic && selectedCountryId && selectedBusinessDomainId) {
      topicInput = {
        new_topic: {
          title: newTopicTitle.trim(),
          description: newTopicDescription.trim(),
          business_domain_id: selectedBusinessDomainId,
          country_id: selectedCountryId,
        },
      }
    } else if (selectedTopicId) {
      topicInput = { existing_topic_id: selectedTopicId }
    } else {
      console.error("Cannot create group without a topic")
      return
    }

    const variations = brandVariations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)

    const brand: BrandInfo = {
      name: trimmedBrandName,
      domain: normalizeDomain(brandDomain) || null,
      variations,
    }

    await onCreateGroup(trimmed, topicInput, brand)
    // Reset all state
    setNewGroupTitle("")
    setBrandName("")
    setBrandDomain("")
    setBrandVariations("")
    setBrandVariationsTouched(false)
    setIsCreatingNew(false)
    setCreationStep("topic")
    setSelectedCountryId(undefined)
    setSelectedBusinessDomainId(undefined)
    setSelectedTopicId(undefined)
    setIsCreatingNewTopic(false)
    setNewTopicTitle("")
    setNewTopicDescription("")
  }, [newGroupTitle, brandName, brandDomain, brandVariations, onCreateGroup, defaultTopicId, isCreatingNewTopic, selectedCountryId, selectedBusinessDomainId, selectedTopicId, newTopicTitle, newTopicDescription])

  const handleTitleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault()
      e.stopPropagation()
      handleCancelCreate()
    }
  }

  const handleBrandKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && brandName.trim()) {
      e.preventDefault()
      handleCreateGroup()
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
      setCreationStep("topic")
      setNewGroupTitle("")
      setBrandName("")
      setBrandDomain("")
      setBrandVariations("")
      setBrandVariationsTouched(false)
      // Reset topic selection state
      setSelectedCountryId(undefined)
      setSelectedBusinessDomainId(undefined)
      setSelectedTopicId(undefined)
      setIsCreatingNewTopic(false)
      setNewTopicTitle("")
      setNewTopicDescription("")
    }
  }

  // Validation for topic selection step
  const canProceedToDetails =
    defaultTopicId !== undefined ||
    selectedTopicId !== undefined ||
    (isCreatingNewTopic && newTopicTitle.trim() && newTopicDescription.trim() && selectedCountryId && selectedBusinessDomainId)

  const canCreate = newGroupTitle.trim() && brandName.trim() && canProceedToDetails

  // Render topic selection step (when no defaultTopicId)
  const renderTopicSelectionStep = () => (
    <div className="space-y-3">
      {/* Country selector */}
      <div>
        <label className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-400 font-sans mb-1.5">
          <MapPin className="w-3 h-3" />
          Country
        </label>
        <select
          value={selectedCountryId ?? ""}
          onChange={(e) => {
            setSelectedCountryId(e.target.value ? parseInt(e.target.value, 10) : undefined)
            setSelectedTopicId(undefined)
            setIsCreatingNewTopic(false)
          }}
          disabled={isLoadingCountries}
          className="w-full px-2.5 py-1.5 text-sm bg-white border border-gray-200 rounded-md
            focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
            disabled:opacity-50 disabled:bg-gray-50"
        >
          <option value="">Select a country...</option>
          {countriesData?.countries.map((country) => (
            <option key={country.id} value={country.id}>
              {country.name}
            </option>
          ))}
        </select>
      </div>

      {/* Business Domain selector */}
      <div>
        <label className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-400 font-sans mb-1.5">
          <Briefcase className="w-3 h-3" />
          Business Domain
        </label>
        <select
          value={selectedBusinessDomainId ?? ""}
          onChange={(e) => {
            setSelectedBusinessDomainId(e.target.value ? parseInt(e.target.value, 10) : undefined)
            setSelectedTopicId(undefined)
            setIsCreatingNewTopic(false)
          }}
          disabled={isLoadingDomains || !selectedCountryId}
          className="w-full px-2.5 py-1.5 text-sm bg-white border border-gray-200 rounded-md
            focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
            disabled:opacity-50 disabled:bg-gray-50"
        >
          <option value="">Select a business domain...</option>
          {businessDomainsData?.business_domains.map((domain) => (
            <option key={domain.id} value={domain.id}>
              {domain.name}
            </option>
          ))}
        </select>
      </div>

      {/* Topic selector or create new */}
      {selectedCountryId && selectedBusinessDomainId && (
        <div className="animate-in slide-in-from-top-2 duration-200">
          <label className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-400 font-sans mb-1.5">
            <Tag className="w-3 h-3" />
            Topic
          </label>

          {isLoadingTopics ? (
            <div className="flex items-center gap-2 py-2 text-sm text-gray-400">
              <div className="w-3 h-3 border-2 border-gray-300 border-t-[#C4553D] rounded-full animate-spin" />
              Loading topics...
            </div>
          ) : (
            <>
              {!isCreatingNewTopic ? (
                <div className="space-y-2">
                  <select
                    value={selectedTopicId ?? ""}
                    onChange={(e) => setSelectedTopicId(e.target.value ? parseInt(e.target.value, 10) : undefined)}
                    className="w-full px-2.5 py-1.5 text-sm bg-white border border-gray-200 rounded-md
                      focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
                  >
                    <option value="">Select an existing topic...</option>
                    {topicsData?.topics.map((topic) => (
                      <option key={topic.id} value={topic.id}>
                        {topic.title}
                      </option>
                    ))}
                  </select>

                  {/* Show topic description if selected */}
                  {selectedTopic && (
                    <div className="p-2 bg-gray-50 rounded text-xs text-gray-600 line-clamp-2">
                      {selectedTopic.description}
                    </div>
                  )}

                  {/* Create new topic button */}
                  <button
                    onClick={() => setIsCreatingNewTopic(true)}
                    className="flex items-center gap-1.5 text-xs text-[#C4553D] hover:text-[#B34835] transition-colors"
                  >
                    <Plus className="w-3 h-3" />
                    Create a new topic
                  </button>
                </div>
              ) : (
                <div className="space-y-2 p-2.5 bg-gray-50 rounded-lg border border-[#C4553D]/20">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-700">New Topic</span>
                    <button
                      onClick={() => {
                        setIsCreatingNewTopic(false)
                        setNewTopicTitle("")
                        setNewTopicDescription("")
                      }}
                      className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>

                  <input
                    type="text"
                    value={newTopicTitle}
                    onChange={(e) => setNewTopicTitle(e.target.value)}
                    placeholder="Topic title"
                    className="w-full px-2 py-1.5 text-sm bg-white border border-gray-200 rounded
                      focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                      placeholder:text-gray-400"
                  />

                  <textarea
                    value={newTopicDescription}
                    onChange={(e) => setNewTopicDescription(e.target.value)}
                    placeholder="Brief description..."
                    rows={2}
                    className="w-full px-2 py-1.5 text-sm bg-white border border-gray-200 rounded
                      focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                      placeholder:text-gray-400 resize-none"
                  />

                  <div className="flex gap-1.5 text-[10px] text-gray-400">
                    <span className="px-1.5 py-0.5 bg-white rounded border border-gray-200">{selectedCountry?.name}</span>
                    <span className="px-1.5 py-0.5 bg-white rounded border border-gray-200">{selectedBusinessDomain?.name}</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )

  // Render brand details step
  const renderBrandDetailsStep = () => (
    <div className="space-y-3">
      {/* Selected topic summary (when topic was selected in step 1) */}
      {needsTopicSelection && (
        <div className="p-2 bg-gray-50 rounded-lg border border-gray-100 flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-[#C4553D]/10 flex items-center justify-center flex-shrink-0">
            <Tag className="w-3 h-3 text-[#C4553D]" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-gray-700 truncate">
              {isCreatingNewTopic ? newTopicTitle : selectedTopic?.title}
            </p>
            <p className="text-[10px] text-gray-400">
              {selectedCountry?.name} · {selectedBusinessDomain?.name}
            </p>
          </div>
          <button
            onClick={() => setCreationStep("topic")}
            className="text-[10px] text-[#C4553D] hover:underline flex-shrink-0"
          >
            Change
          </button>
        </div>
      )}

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

      {/* Brand section - single brand */}
      <div>
        <label className="block text-xs uppercase tracking-widest text-gray-400 font-sans mb-1.5">
          Brand to Track <span className="text-[#C4553D]">*</span>
        </label>

        <div className="space-y-1.5">
          <input
            ref={brandInputRef}
            type="text"
            value={brandName}
            onChange={(e) => handleBrandNameChange(e.target.value)}
            onKeyDown={handleBrandKeyDown}
            placeholder="Brand name (e.g., Nike)"
            disabled={isCreatingGroup}
            className="w-full px-2.5 py-1.5 text-sm
              bg-white border border-gray-200 rounded-md
              focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
              placeholder:text-gray-400 disabled:opacity-50"
          />
          <div className="relative">
            <Globe className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input
              type="text"
              value={brandDomain}
              onChange={(e) => setBrandDomain(e.target.value)}
              onKeyDown={handleBrandKeyDown}
              placeholder="Domain (optional, e.g., nike.com)"
              disabled={isCreatingGroup}
              className="w-full pl-8 pr-2.5 py-1.5 text-sm
                bg-white border border-gray-200 rounded-md
                focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                placeholder:text-gray-400 disabled:opacity-50"
            />
          </div>
          <input
            type="text"
            value={brandVariations}
            onChange={(e) => {
              setBrandVariations(e.target.value)
              setBrandVariationsTouched(true)
            }}
            onKeyDown={handleBrandKeyDown}
            placeholder="Variations (optional, comma-separated)"
            disabled={isCreatingGroup}
            className="w-full px-2.5 py-1.5 text-sm
              bg-white border border-gray-200 rounded-md
              focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
              placeholder:text-gray-400 disabled:opacity-50"
          />
        </div>
      </div>
    </div>
  )

  // Render inline form for creating a group with required brand
  const renderCreateForm = (isEmptyState: boolean = false) => {
    // Determine which step to show based on whether topic selection is needed
    const showTopicStep = needsTopicSelection && creationStep === "topic"
    const showDetailsStep = !needsTopicSelection || creationStep === "details"

    return (
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

        {/* Step indicator (only when topic selection is needed) */}
        {needsTopicSelection && (
          <div className="flex items-center gap-2 mb-3">
            <button
              onClick={() => setCreationStep("topic")}
              className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-medium transition-all ${
                creationStep === "topic"
                  ? "bg-[#C4553D] text-white"
                  : "bg-gray-100 text-gray-500 hover:bg-gray-200"
              }`}
            >
              <Tag className="w-2.5 h-2.5" />
              Topic
            </button>
            <div className="w-3 h-px bg-gray-300" />
            <button
              onClick={() => canProceedToDetails && setCreationStep("details")}
              disabled={!canProceedToDetails}
              className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-medium transition-all ${
                creationStep === "details"
                  ? "bg-[#C4553D] text-white"
                  : canProceedToDetails
                  ? "bg-gray-100 text-gray-500 hover:bg-gray-200"
                  : "bg-gray-100 text-gray-300 cursor-not-allowed"
              }`}
            >
              <Briefcase className="w-2.5 h-2.5" />
              Brand
            </button>
          </div>
        )}

        {/* Step content */}
        {showTopicStep && renderTopicSelectionStep()}
        {showDetailsStep && renderBrandDetailsStep()}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-3 mt-3 border-t border-gray-100">
          {/* Back button (only in details step when topic selection was needed) */}
          {needsTopicSelection && creationStep === "details" && (
            <button
              onClick={() => setCreationStep("topic")}
              disabled={isCreatingGroup}
              className="py-2 px-3 text-sm font-medium text-gray-600
                bg-white border border-gray-200 rounded-lg
                hover:bg-gray-50 transition-colors disabled:opacity-50 mr-auto"
            >
              Back
            </button>
          )}
          <button
            onClick={handleCancelCreate}
            disabled={isCreatingGroup}
            className="py-2 px-3 text-sm font-medium text-gray-600
              bg-white border border-gray-200 rounded-lg
              hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          {/* Continue button (topic step) or Create button (details step) */}
          {showTopicStep ? (
            <button
              onClick={() => {
                // Prefill group name with topic name
                const topicName = isCreatingNewTopic ? newTopicTitle.trim() : selectedTopic?.title
                if (topicName && !newGroupTitle.trim()) {
                  setNewGroupTitle(topicName)
                }
                setCreationStep("details")
              }}
              disabled={!canProceedToDetails}
              className="py-2 px-4 text-sm font-medium text-white
                bg-[#C4553D] rounded-lg hover:bg-[#B34835]
                transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                flex items-center gap-2"
            >
              Continue
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
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
          )}
        </div>
      </div>
    )
  }

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
