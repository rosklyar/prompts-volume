/**
 * AddGroupCard - Full-width card for creating a new group
 * Four-step flow:
 * 1. Topic Selection (optional) - cascading dropdowns or skip
 * 2. Brand & Competitors info
 * 3. Topic Prompts Selection (only if topic selected in step 1)
 * 4. GSC Prompts (skippable)
 */

import { useState, useRef, useEffect, useMemo, useCallback } from "react"
import { ChevronDown, ChevronRight, Plus, X, Globe, Sparkles, MapPin, Briefcase, Tag, Check, Search } from "lucide-react"
import type { BrandInfo, CompetitorInfo, TopicInput } from "@/types/groups"
import { useCountries, useBusinessDomains, useTopicsFiltered } from "@/hooks/useTopics"
import { useUserPreferences } from "@/hooks/useOnboarding"
import { promptsApi } from "@/client/api"
import { useQuery } from "@tanstack/react-query"
import { normalizeDomain } from "@/lib/domain"
import { MAX_GROUPS } from "./constants"
import { PromptSelector } from "./shared/PromptSelector"
import { GSCPromptsStep } from "./shared/GSCPromptsStep"

interface AddGroupCardProps {
  onAdd: (
    title: string,
    topic: TopicInput | null,
    brand: BrandInfo,
    competitors?: CompetitorInfo[],
    topicTitle?: string | null,
    selectedTopicPromptIds?: number[],
    selectedGSCPrompts?: string[]
  ) => void
  isLoading: boolean
}

type CreationStep = "topic" | "details" | "topic-prompts" | "gsc-prompts"

export function AddGroupCard({ onAdd, isLoading }: AddGroupCardProps) {
  const [isCreating, setIsCreating] = useState(false)
  const [step, setStep] = useState<CreationStep>("topic")
  const [title, setTitle] = useState("")

  // Topic selection state - default to "no topic" (skipTopicBinding = true)
  const [selectedCountryId, setSelectedCountryId] = useState<number | undefined>()
  const [selectedBusinessDomainId, setSelectedBusinessDomainId] = useState<number | undefined>()
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null)
  const [skipTopicBinding, setSkipTopicBinding] = useState(true)

  // Brand state
  const [brandName, setBrandName] = useState("")
  const [brandDomain, setBrandDomain] = useState("")
  const [brandVariations, setBrandVariations] = useState("")
  const [brandVariationsTouched, setBrandVariationsTouched] = useState(false)

  // Competitors state
  const [showCompetitors, setShowCompetitors] = useState(false)
  const [competitors, setCompetitors] = useState<CompetitorInfo[]>([])
  const [newCompName, setNewCompName] = useState("")
  const [newCompDomain, setNewCompDomain] = useState("")
  const [newCompVariations, setNewCompVariations] = useState("")
  const [newCompVariationsTouched, setNewCompVariationsTouched] = useState(false)

  // Topic prompts selection state (step 3)
  const [selectedTopicPromptIds, setSelectedTopicPromptIds] = useState<Set<number>>(new Set())

  // GSC prompts selection state (step 4)
  const [selectedGSCPrompts, setSelectedGSCPrompts] = useState<Set<string>>(new Set())

  const titleInputRef = useRef<HTMLInputElement>(null)
  const topicStepRef = useRef<HTMLDivElement>(null)
  const hasPrefilledRef = useRef(false)

  // Fetch user preferences for prefilling brand/competitor data
  const { data: userPreferences } = useUserPreferences()

  // Fetch reference data
  const { data: countriesData, isLoading: isLoadingCountries } = useCountries()
  const { data: businessDomainsData, isLoading: isLoadingDomains } = useBusinessDomains()
  const { data: topicsData, isLoading: isLoadingTopics } = useTopicsFiltered(
    selectedCountryId,
    selectedBusinessDomainId
  )

  // Fetch topic prompts when we have a selected topic (for step 3)
  const { data: topicPromptsData, isLoading: isLoadingTopicPrompts } = useQuery({
    queryKey: ["topicPrompts", selectedTopicId],
    queryFn: () => promptsApi.getPromptsByTopicIds([selectedTopicId!]),
    enabled: !skipTopicBinding && selectedTopicId !== null,
  })

  // Get prompts for selected topic
  const topicPrompts = useMemo(() => {
    if (!topicPromptsData?.topics || !selectedTopicId) return []
    const topicGroup = topicPromptsData.topics.find((t) => t.topic_id === selectedTopicId)
    return topicGroup?.prompts ?? []
  }, [topicPromptsData, selectedTopicId])

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

  useEffect(() => {
    if (isCreating && step === "details" && titleInputRef.current) {
      titleInputRef.current.focus()
    }
  }, [isCreating, step])

  // Auto-select all topic prompts when prompts load
  // Track the last topic id for which we auto-selected prompts
  const lastAutoSelectTopicIdRef = useRef<number | null>(null)
  useEffect(() => {
    // Only auto-select if:
    // 1. We have topic prompts
    // 2. We haven't already auto-selected for this topic
    // 3. Current selection is empty (user hasn't manually changed anything)
    if (
      topicPrompts.length > 0 &&
      selectedTopicId !== null &&
      lastAutoSelectTopicIdRef.current !== selectedTopicId &&
      selectedTopicPromptIds.size === 0
    ) {
      lastAutoSelectTopicIdRef.current = selectedTopicId
      setSelectedTopicPromptIds(new Set(topicPrompts.map((p) => p.id)))
    }
    // Reset when topic is cleared
    if (selectedTopicId === null) {
      lastAutoSelectTopicIdRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topicPrompts, selectedTopicId])

  // Prefill brand, competitors, and market from user preferences
  const applyPrefill = useCallback(() => {
    if (!userPreferences || hasPrefilledRef.current) return

    hasPrefilledRef.current = true

    // Prefill market (country and business domain)
    if (userPreferences.default_country_id) {
      setSelectedCountryId(userPreferences.default_country_id)
      if (userPreferences.default_business_domain_id) {
        setSkipTopicBinding(false)
      }
    }
    if (userPreferences.default_business_domain_id) {
      setSelectedBusinessDomainId(userPreferences.default_business_domain_id)
    }

    // Prefill brand
    if (userPreferences.default_brand) {
      const brand = userPreferences.default_brand
      setBrandName(brand.name)
      setBrandDomain(brand.domain ?? "")
      setBrandVariations(brand.variations.join(", "))
      setBrandVariationsTouched(true)
    }

    // Prefill competitors
    if (userPreferences.default_competitors && userPreferences.default_competitors.length > 0) {
      setCompetitors(userPreferences.default_competitors)
      setShowCompetitors(true)
    }
  }, [userPreferences])

  // Handle async loading of userPreferences - applies prefill when data arrives after form opens
  useEffect(() => {
    if (isCreating && userPreferences && !hasPrefilledRef.current) {
      queueMicrotask(applyPrefill)
    }
    if (!isCreating) {
      hasPrefilledRef.current = false
    }
  }, [isCreating, userPreferences, applyPrefill])

  // Handle brand name change with prefill logic
  const handleBrandNameChange = (value: string) => {
    setBrandName(value)
    if (!brandVariationsTouched) {
      setBrandVariations(value.trim())
    }
  }

  // Handle new competitor name change with prefill logic
  const handleNewCompNameChange = (value: string) => {
    setNewCompName(value)
    if (!newCompVariationsTouched) {
      setNewCompVariations(value.trim())
    }
  }

  const handleAddCompetitor = () => {
    if (!newCompName.trim()) return
    const variations = newCompVariations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)
    setCompetitors([
      ...competitors,
      {
        name: newCompName.trim(),
        domain: normalizeDomain(newCompDomain) || null,
        variations,
      },
    ])
    setNewCompName("")
    setNewCompDomain("")
    setNewCompVariations("")
    setNewCompVariationsTouched(false)
  }

  const handleRemoveCompetitor = (index: number) => {
    setCompetitors(competitors.filter((_, i) => i !== index))
  }

  const handleSubmit = () => {
    const trimmedTitle = title.trim()
    const trimmedBrandName = brandName.trim()

    if (trimmedTitle && trimmedBrandName) {
      const variations = brandVariations
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean)

      const brand: BrandInfo = {
        name: trimmedBrandName,
        domain: normalizeDomain(brandDomain) || null,
        variations,
      }

      // Build topic input - null if skipping
      let topicInput: TopicInput | null = null
      if (!skipTopicBinding && selectedTopicId) {
        topicInput = { existing_topic_id: selectedTopicId }
      }

      // Get the topic title to pass to the modal (null if skipping)
      const topicTitleForModal = skipTopicBinding ? null : selectedTopic?.title

      // Collect selected prompts
      const topicPromptIds = !skipTopicBinding && selectedTopicPromptIds.size > 0
        ? Array.from(selectedTopicPromptIds)
        : undefined

      const gscPrompts = selectedGSCPrompts.size > 0
        ? Array.from(selectedGSCPrompts)
        : undefined

      onAdd(
        trimmedTitle,
        topicInput,
        brand,
        competitors.length > 0 ? competitors : undefined,
        topicTitleForModal,
        topicPromptIds,
        gscPrompts
      )
      resetForm()
    }
  }

  const resetForm = () => {
    setStep("topic")
    setTitle("")
    setSelectedCountryId(undefined)
    setSelectedBusinessDomainId(undefined)
    setSelectedTopicId(null)
    setSkipTopicBinding(true)
    setBrandName("")
    setBrandDomain("")
    setBrandVariations("")
    setBrandVariationsTouched(false)
    setCompetitors([])
    setNewCompName("")
    setNewCompDomain("")
    setNewCompVariations("")
    setNewCompVariationsTouched(false)
    setShowCompetitors(false)
    setSelectedTopicPromptIds(new Set())
    setSelectedGSCPrompts(new Set())
    setIsCreating(false)
    // Note: hasPrefilledRef is reset in the useEffect when isCreating becomes false
  }

  const handleCancel = () => {
    resetForm()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      handleCancel()
    }
  }

  const handleCompetitorKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleAddCompetitor()
    } else if (e.key === "Escape") {
      handleCancel()
    }
  }

  // Topic prompts handlers
  const handleToggleTopicPrompt = (promptId: number | string) => {
    if (typeof promptId !== "number") return
    setSelectedTopicPromptIds((prev) => {
      const next = new Set(prev)
      if (next.has(promptId)) {
        next.delete(promptId)
      } else {
        next.add(promptId)
      }
      return next
    })
  }

  const handleSelectAllTopicPrompts = () => {
    if (selectedTopicPromptIds.size === topicPrompts.length) {
      setSelectedTopicPromptIds(new Set())
    } else {
      setSelectedTopicPromptIds(new Set(topicPrompts.map((p) => p.id)))
    }
  }

  // GSC prompts handlers
  const handleToggleGSCPrompt = (prompt: string) => {
    setSelectedGSCPrompts((prev) => {
      const next = new Set(prev)
      if (next.has(prompt)) {
        next.delete(prompt)
      } else {
        next.add(prompt)
      }
      return next
    })
  }


  const canProceedToDetails =
    skipTopicBinding || (selectedTopicId !== null)

  const canProceedToTopicPrompts =
    title.trim() && brandName.trim() && canProceedToDetails

  // Determine if we should show the topic prompts step
  const showTopicPromptsStep = !skipTopicBinding && selectedTopicId !== null

  // Determine the next step after details
  const getNextStepAfterDetails = () => {
    if (showTopicPromptsStep) return "topic-prompts"
    return "gsc-prompts"
  }

  const canCreate = title.trim() && brandName.trim() && canProceedToDetails

  if (isCreating) {
    return (
      <section
        className="w-full rounded-2xl overflow-hidden
          border-2 border-[#C4553D]/30 bg-[#FEF7F5]
          animate-in fade-in duration-200"
      >
        {/* Accent bar */}
        <div className="h-1.5 w-full bg-[#C4553D]" />

        <div className="px-5 py-5 space-y-5">
          {/* Step indicator */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <button
              onClick={() => setStep("topic")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                step === "topic"
                  ? "bg-[#C4553D] text-white"
                  : "bg-white text-gray-500 hover:bg-gray-50"
              }`}
            >
              <Tag className="w-3.5 h-3.5" />
              Topic
            </button>
            <div className="w-3 h-px bg-gray-300" />
            <button
              onClick={() => canProceedToDetails && setStep("details")}
              disabled={!canProceedToDetails}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                step === "details"
                  ? "bg-[#C4553D] text-white"
                  : canProceedToDetails
                  ? "bg-white text-gray-500 hover:bg-gray-50"
                  : "bg-gray-100 text-gray-300 cursor-not-allowed"
              }`}
            >
              <Briefcase className="w-3.5 h-3.5" />
              Brand
            </button>
            {showTopicPromptsStep && (
              <>
                <div className="w-3 h-px bg-gray-300" />
                <button
                  onClick={() => canProceedToTopicPrompts && setStep("topic-prompts")}
                  disabled={!canProceedToTopicPrompts}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                    step === "topic-prompts"
                      ? "bg-[#C4553D] text-white"
                      : canProceedToTopicPrompts
                      ? "bg-white text-gray-500 hover:bg-gray-50"
                      : "bg-gray-100 text-gray-300 cursor-not-allowed"
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Prompts
                </button>
              </>
            )}
            <div className="w-3 h-px bg-gray-300" />
            <button
              onClick={() => canProceedToTopicPrompts && setStep("gsc-prompts")}
              disabled={!canProceedToTopicPrompts}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                step === "gsc-prompts"
                  ? "bg-[#C4553D] text-white"
                  : canProceedToTopicPrompts
                  ? "bg-white text-gray-500 hover:bg-gray-50"
                  : "bg-gray-100 text-gray-300 cursor-not-allowed"
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              GSC
            </button>
          </div>

          {/* Step 1: Topic Selection */}
          {step === "topic" && (
            <div ref={topicStepRef} className="space-y-4 animate-in fade-in duration-200">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-[#C4553D]" />
                <span className="text-sm font-medium text-gray-700">Topic binding (optional)</span>
              </div>

              {/* Topic selection options */}
              <div className="space-y-2">
                {/* No topic option - selected by default */}
                <div
                  onClick={() => {
                    setSkipTopicBinding(true)
                    setSelectedTopicId(null)
                  }}
                  className={`p-3 rounded-xl border-2 cursor-pointer transition-all flex items-center gap-3 ${
                    skipTopicBinding
                      ? "border-[#C4553D] bg-[#C4553D]/5"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center ${
                      skipTopicBinding
                        ? "border-[#C4553D] bg-[#C4553D]"
                        : "border-gray-300"
                    }`}
                  >
                    {skipTopicBinding && <Check className="w-2.5 h-2.5 text-white" />}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-900 text-sm">No topic</p>
                    <p className="text-xs text-gray-500">Add custom prompts manually</p>
                  </div>
                </div>

                {/* Select topic option */}
                <div
                  onClick={() => setSkipTopicBinding(false)}
                  className={`p-3 rounded-xl border-2 cursor-pointer transition-all flex items-center gap-3 ${
                    !skipTopicBinding
                      ? "border-[#C4553D] bg-[#C4553D]/5"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center ${
                      !skipTopicBinding
                        ? "border-[#C4553D] bg-[#C4553D]"
                        : "border-gray-300"
                    }`}
                  >
                    {!skipTopicBinding && <Check className="w-2.5 h-2.5 text-white" />}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-900 text-sm">Select a topic</p>
                    <p className="text-xs text-gray-500">Get suggested prompts from a topic</p>
                  </div>
                </div>
              </div>

              {/* Topic selection dropdowns - only shown when "Select a topic" is chosen */}
              {!skipTopicBinding && (
                <div className="space-y-3 pt-2 animate-in slide-in-from-top-2 duration-200">
                  {/* Country selector */}
                  <div>
                    <label className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-400 font-sans mb-2">
                      <MapPin className="w-3.5 h-3.5" />
                      Country
                    </label>
                    <select
                      value={selectedCountryId ?? ""}
                      onChange={(e) => {
                        setSelectedCountryId(e.target.value ? parseInt(e.target.value, 10) : undefined)
                        setSelectedTopicId(null)
                      }}
                      disabled={isLoadingCountries}
                      className="w-full px-3 py-2.5 text-sm bg-white border border-gray-200 rounded-lg
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
                    <label className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-400 font-sans mb-2">
                      <Briefcase className="w-3.5 h-3.5" />
                      Business Domain
                    </label>
                    <select
                      value={selectedBusinessDomainId ?? ""}
                      onChange={(e) => {
                        setSelectedBusinessDomainId(e.target.value ? parseInt(e.target.value, 10) : undefined)
                        setSelectedTopicId(null)
                      }}
                      disabled={isLoadingDomains || !selectedCountryId}
                      className="w-full px-3 py-2.5 text-sm bg-white border border-gray-200 rounded-lg
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

                  {/* Topic selector - only when country and domain selected */}
                  {selectedCountryId && selectedBusinessDomainId && (
                    <div className="animate-in slide-in-from-top-2 duration-200">
                      <label className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-400 font-sans mb-2">
                        <Tag className="w-3.5 h-3.5" />
                        Topic
                      </label>

                      {isLoadingTopics ? (
                        <div className="flex items-center gap-2 py-4 text-sm text-gray-400">
                          <div className="w-4 h-4 border-2 border-gray-300 border-t-[#C4553D] rounded-full animate-spin" />
                          Loading topics...
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <select
                            value={selectedTopicId ?? ""}
                            onChange={(e) => setSelectedTopicId(e.target.value ? parseInt(e.target.value, 10) : null)}
                            className="w-full px-3 py-2.5 text-sm bg-white border border-gray-200 rounded-lg
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
                            <div className="p-3 bg-white rounded-lg border border-gray-100 text-sm text-gray-600">
                              {selectedTopic.description}
                            </div>
                          )}

                          {/* Note about topic creation */}
                          {topicsData?.topics.length === 0 && (
                            <p className="text-sm text-gray-500 italic">
                              No topics available for this combination. Select "No topic" above or contact an administrator.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Next button */}
              <div className="flex justify-end pt-3 border-t border-gray-200">
                <button
                  onClick={handleCancel}
                  className="py-2.5 px-4 text-sm font-medium text-gray-600
                    bg-white border border-gray-200 rounded-lg
                    hover:bg-gray-50 transition-colors mr-2"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    // Prefill group name with topic name (don't prefill if skipping)
                    if (!skipTopicBinding && selectedTopic?.title && !title.trim()) {
                      setTitle(selectedTopic.title)
                    }
                    setStep("details")
                  }}
                  disabled={!canProceedToDetails}
                  className="py-2.5 px-5 text-sm font-medium text-white
                    bg-[#C4553D] rounded-lg hover:bg-[#B34835]
                    transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                    flex items-center gap-2"
                >
                  Continue
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Group Details (Title, Brand, Competitors) */}
          {step === "details" && (
            <div className="space-y-5 animate-in fade-in duration-200">
              {/* Selected topic summary OR skipped topic warning */}
              {skipTopicBinding ? (
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                    <Tag className="w-4 h-4 text-gray-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-700">No topic selected</p>
                    <p className="text-xs text-gray-500">Custom prompts</p>
                  </div>
                  <button
                    onClick={() => setStep("topic")}
                    className="text-xs text-gray-600 hover:underline flex-shrink-0"
                  >
                    Change
                  </button>
                </div>
              ) : (
                <div className="p-3 bg-white rounded-lg border border-gray-100 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-[#C4553D]/10 flex items-center justify-center flex-shrink-0">
                    <Tag className="w-4 h-4 text-[#C4553D]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-700 truncate">
                      {selectedTopic?.title}
                    </p>
                    <p className="text-xs text-gray-400">
                      {selectedCountry?.name} &middot; {selectedBusinessDomain?.name}
                    </p>
                  </div>
                  <button
                    onClick={() => setStep("topic")}
                    className="text-xs text-[#C4553D] hover:underline flex-shrink-0"
                  >
                    Change
                  </button>
                </div>
              )}

              {/* Title input */}
              <div>
                <label className="block text-xs uppercase tracking-widest text-gray-400 font-sans mb-2">
                  Group name
                </label>
                <input
                  ref={titleInputRef}
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Enter group name..."
                  disabled={isLoading}
                  className="w-full px-4 py-2.5 font-['Fraunces'] text-lg
                    bg-white border border-gray-200 rounded-lg
                    focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                    placeholder:text-gray-400 disabled:opacity-50"
                  maxLength={50}
                />
              </div>

              {/* Brand section */}
              <div>
                <label className="block text-xs uppercase tracking-widest text-gray-400 font-sans mb-2">
                  Brand to Track <span className="text-[#C4553D]">*</span>
                </label>

                <div className="space-y-2">
                  <input
                    type="text"
                    value={brandName}
                    onChange={(e) => handleBrandNameChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Brand name (e.g., Nike)"
                    disabled={isLoading}
                    className="w-full px-3 py-2 text-sm
                      bg-white border border-gray-200 rounded-lg
                      focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                      placeholder:text-gray-400 disabled:opacity-50"
                  />
                  <div className="relative">
                    <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={brandDomain}
                      onChange={(e) => setBrandDomain(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Domain URL (e.g., nike.com)"
                      disabled={isLoading}
                      className="w-full pl-9 pr-3 py-2 text-sm
                        bg-white border border-gray-200 rounded-lg
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
                    onKeyDown={handleKeyDown}
                    placeholder="Name variations, comma-separated (optional)"
                    disabled={isLoading}
                    className="w-full px-3 py-2 text-sm
                      bg-white border border-gray-200 rounded-lg
                      focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                      placeholder:text-gray-400 disabled:opacity-50"
                  />
                </div>
              </div>

              {/* Competitors section (collapsible) */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowCompetitors(!showCompetitors)}
                  className="flex items-center gap-2 text-xs uppercase tracking-widest text-gray-400 font-sans mb-2 hover:text-gray-600 transition-colors"
                >
                  {showCompetitors ? (
                    <ChevronDown className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5" />
                  )}
                  Competitors (optional)
                  {competitors.length > 0 && (
                    <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-gray-200 text-gray-600 rounded-full">
                      {competitors.length}
                    </span>
                  )}
                </button>

                {showCompetitors && (
                  <div className="space-y-3 animate-in slide-in-from-top-2 duration-200">
                    {/* Added competitors */}
                    {competitors.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {competitors.map((comp, index) => (
                          <div
                            key={index}
                            className="flex items-center gap-2 px-3 py-1.5 bg-white border border-gray-200 rounded-lg group"
                          >
                            <span className="text-sm font-medium text-gray-700">{comp.name}</span>
                            {comp.domain && (
                              <span className="text-xs text-gray-400">{comp.domain}</span>
                            )}
                            <button
                              onClick={() => handleRemoveCompetitor(index)}
                              className="p-0.5 rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Add competitor form */}
                    <div className="p-3 bg-white/50 rounded-lg border border-gray-100 space-y-2">
                      <input
                        type="text"
                        value={newCompName}
                        onChange={(e) => handleNewCompNameChange(e.target.value)}
                        onKeyDown={handleCompetitorKeyDown}
                        placeholder="Competitor name"
                        disabled={isLoading}
                        className="w-full px-3 py-2 text-sm
                          bg-white border border-gray-200 rounded-lg
                          focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                          placeholder:text-gray-400 disabled:opacity-50"
                      />
                      <div className="relative">
                        <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="text"
                          value={newCompDomain}
                          onChange={(e) => setNewCompDomain(e.target.value)}
                          onKeyDown={handleCompetitorKeyDown}
                          placeholder="Domain (optional)"
                          disabled={isLoading}
                          className="w-full pl-9 pr-3 py-2 text-sm
                            bg-white border border-gray-200 rounded-lg
                            focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                            placeholder:text-gray-400 disabled:opacity-50"
                        />
                      </div>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={newCompVariations}
                          onChange={(e) => {
                            setNewCompVariations(e.target.value)
                            setNewCompVariationsTouched(true)
                          }}
                          onKeyDown={handleCompetitorKeyDown}
                          placeholder="Variations (optional)"
                          disabled={isLoading}
                          className="flex-1 px-3 py-2 text-sm
                            bg-white border border-gray-200 rounded-lg
                            focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                            placeholder:text-gray-400 disabled:opacity-50"
                        />
                        <button
                          onClick={handleAddCompetitor}
                          disabled={!newCompName.trim() || isLoading}
                          className="px-3 py-2 text-sm font-medium
                            bg-white border border-gray-200 rounded-lg
                            hover:bg-gray-50 hover:border-[#C4553D]/50 transition-colors
                            disabled:opacity-50 disabled:cursor-not-allowed
                            flex items-center gap-1"
                        >
                          <Plus className="w-4 h-4" />
                          Add
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex justify-between pt-2 border-t border-gray-200">
                <button
                  onClick={() => setStep("topic")}
                  disabled={isLoading}
                  className="py-2.5 px-4 text-sm font-medium text-gray-600
                    bg-white border border-gray-200 rounded-lg
                    hover:bg-gray-50 transition-colors disabled:opacity-50
                    flex items-center gap-2"
                >
                  <ChevronDown className="w-4 h-4 -rotate-90" />
                  Back
                </button>
                <div className="flex gap-2">
                  <button
                    onClick={handleCancel}
                    disabled={isLoading}
                    className="py-2.5 px-4 text-sm font-medium text-gray-600
                      bg-white border border-gray-200 rounded-lg
                      hover:bg-gray-50 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => setStep(getNextStepAfterDetails())}
                    disabled={isLoading || !canProceedToTopicPrompts}
                    className="py-2.5 px-5 text-sm font-medium text-white
                      bg-[#C4553D] rounded-lg hover:bg-[#B34835]
                      transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                      flex items-center gap-2"
                  >
                    Continue
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Topic Prompts Selection (only if topic selected) */}
          {step === "topic-prompts" && showTopicPromptsStep && (
            <div className="space-y-5 animate-in fade-in duration-200">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-[#C4553D]" />
                <span className="text-sm font-medium text-gray-700">
                  Select prompts from "{selectedTopic?.title}"
                </span>
              </div>

              <PromptSelector
                prompts={topicPrompts.map((p) => ({ id: p.id, text: p.prompt_text }))}
                selectedIds={selectedTopicPromptIds}
                onToggle={handleToggleTopicPrompt}
                onSelectAll={handleSelectAllTopicPrompts}
                accentColor="#C4553D"
                isLoading={isLoadingTopicPrompts}
                emptyMessage="No prompts available"
                emptySubtitle="This topic doesn't have any prompts yet"
                maxHeight="280px"
              />

              {/* Actions */}
              <div className="flex justify-between pt-2 border-t border-gray-200">
                <button
                  onClick={() => setStep("details")}
                  disabled={isLoading}
                  className="py-2.5 px-4 text-sm font-medium text-gray-600
                    bg-white border border-gray-200 rounded-lg
                    hover:bg-gray-50 transition-colors disabled:opacity-50
                    flex items-center gap-2"
                >
                  <ChevronDown className="w-4 h-4 -rotate-90" />
                  Back
                </button>
                <div className="flex gap-2">
                  <button
                    onClick={handleCancel}
                    disabled={isLoading}
                    className="py-2.5 px-4 text-sm font-medium text-gray-600
                      bg-white border border-gray-200 rounded-lg
                      hover:bg-gray-50 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => setStep("gsc-prompts")}
                    disabled={isLoading}
                    className="py-2.5 px-5 text-sm font-medium text-white
                      bg-[#C4553D] rounded-lg hover:bg-[#B34835]
                      transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                      flex items-center gap-2"
                  >
                    Continue
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: GSC Prompts */}
          {step === "gsc-prompts" && (
            <div className="space-y-5 animate-in fade-in duration-200">
              <GSCPromptsStep
                brandDomain={normalizeDomain(brandDomain) || null}
                countryId={selectedCountryId ?? 1}
                businessDomain={selectedBusinessDomain?.name}
                selectedPrompts={selectedGSCPrompts}
                onTogglePrompt={handleToggleGSCPrompt}
                accentColor="#C4553D"
                redirectUri={window.location.href}
              />

              {/* Actions */}
              <div className="flex justify-between pt-2 border-t border-gray-200">
                <button
                  onClick={() => setStep(showTopicPromptsStep ? "topic-prompts" : "details")}
                  disabled={isLoading}
                  className="py-2.5 px-4 text-sm font-medium text-gray-600
                    bg-white border border-gray-200 rounded-lg
                    hover:bg-gray-50 transition-colors disabled:opacity-50
                    flex items-center gap-2"
                >
                  <ChevronDown className="w-4 h-4 -rotate-90" />
                  Back
                </button>
                <div className="flex gap-2">
                  {/* Show Skip & Create only when GSC prompts are selected */}
                  {selectedGSCPrompts.size > 0 && (
                    <button
                      onClick={() => {
                        setSelectedGSCPrompts(new Set())
                        handleSubmit()
                      }}
                      disabled={isLoading || !canCreate}
                      className="py-2.5 px-4 text-sm font-medium text-gray-600
                        bg-white border border-gray-200 rounded-lg
                        hover:bg-gray-50 transition-colors disabled:opacity-50"
                    >
                      Skip & Create
                    </button>
                  )}
                  <button
                    onClick={handleSubmit}
                    disabled={isLoading || !canCreate}
                    className="py-2.5 px-5 text-sm font-medium text-white
                      bg-[#C4553D] rounded-lg hover:bg-[#B34835]
                      transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                      flex items-center gap-2"
                  >
                    {isLoading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Creating...
                      </>
                    ) : (
                      "Create group"
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    )
  }

  const handleStartCreating = () => {
    setIsCreating(true)
    // Apply prefill immediately if data is already loaded
    applyPrefill()
  }

  return (
    <button
      onClick={handleStartCreating}
      className="w-full flex items-center justify-center gap-3 rounded-2xl
        border-2 border-dashed border-gray-200 bg-gray-50/50
        py-6 transition-all duration-300
        hover:border-[#C4553D]/40 hover:bg-[#FEF7F5]/50
        focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30
        group"
    >
      <div
        className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center
          transition-all duration-300
          group-hover:bg-[#C4553D]/10 group-hover:scale-110"
      >
        <Plus className="w-5 h-5 text-gray-400 transition-colors group-hover:text-[#C4553D]" />
      </div>
      <div className="text-left">
        <span className="text-sm font-medium text-gray-500 group-hover:text-[#C4553D] transition-colors block">
          Add new group
        </span>
        <span className="text-xs text-gray-400">
          Up to {MAX_GROUPS} total
        </span>
      </div>
    </button>
  )
}
