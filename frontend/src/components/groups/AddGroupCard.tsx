/**
 * AddGroupCard - Full-width card for creating a new group
 * Two-step flow:
 * 1. Topic Selection (required) - cascading dropdowns or create new
 * 2. Brand & Competitors info
 */

import { useState, useRef, useEffect, useMemo } from "react"
import { ChevronDown, ChevronRight, Plus, X, Globe, Sparkles, MapPin, Briefcase, Tag } from "lucide-react"
import type { BrandInfo, CompetitorInfo, TopicInput } from "@/types/groups"
import { useCountries, useBusinessDomains, useTopicsFiltered } from "@/hooks/useTopics"
import { MAX_GROUPS } from "./constants"

interface AddGroupCardProps {
  onAdd: (title: string, topic: TopicInput, brand: BrandInfo, competitors?: CompetitorInfo[], topicTitle?: string) => void
  isLoading: boolean
}

type CreationStep = "topic" | "details"

function normalizeDomain(url: string): string {
  let domain = url.trim().toLowerCase()
  if (!domain) return ""
  if (domain.startsWith("http://") || domain.startsWith("https://")) {
    domain = domain.split("://")[1]
  }
  domain = domain.replace(/\/$/, "")
  return domain
}

export function AddGroupCard({ onAdd, isLoading }: AddGroupCardProps) {
  const [isCreating, setIsCreating] = useState(false)
  const [step, setStep] = useState<CreationStep>("topic")
  const [title, setTitle] = useState("")

  // Topic selection state
  const [selectedCountryId, setSelectedCountryId] = useState<number | undefined>()
  const [selectedBusinessDomainId, setSelectedBusinessDomainId] = useState<number | undefined>()
  const [selectedTopicId, setSelectedTopicId] = useState<number | undefined>()
  const [isCreatingNewTopic, setIsCreatingNewTopic] = useState(false)
  const [newTopicTitle, setNewTopicTitle] = useState("")
  const [newTopicDescription, setNewTopicDescription] = useState("")

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

  const titleInputRef = useRef<HTMLInputElement>(null)
  const topicStepRef = useRef<HTMLDivElement>(null)

  // Fetch reference data
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

  useEffect(() => {
    if (isCreating && step === "details" && titleInputRef.current) {
      titleInputRef.current.focus()
    }
  }, [isCreating, step])

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

      // Build topic input
      let topicInput: TopicInput
      if (isCreatingNewTopic && selectedCountryId && selectedBusinessDomainId) {
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
        return // Should not happen if validation is correct
      }

      // Get the topic title to pass to the modal
      const topicTitleForModal = isCreatingNewTopic ? newTopicTitle.trim() : selectedTopic?.title

      onAdd(trimmedTitle, topicInput, brand, competitors.length > 0 ? competitors : undefined, topicTitleForModal)
      resetForm()
    }
  }

  const resetForm = () => {
    setStep("topic")
    setTitle("")
    setSelectedCountryId(undefined)
    setSelectedBusinessDomainId(undefined)
    setSelectedTopicId(undefined)
    setIsCreatingNewTopic(false)
    setNewTopicTitle("")
    setNewTopicDescription("")
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
    setIsCreating(false)
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

  const canProceedToDetails =
    (selectedTopicId !== undefined) ||
    (isCreatingNewTopic && newTopicTitle.trim() && newTopicDescription.trim() && selectedCountryId && selectedBusinessDomainId)

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
          <div className="flex items-center gap-3 mb-2">
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
            <div className="w-4 h-px bg-gray-300" />
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
          </div>

          {/* Step 1: Topic Selection */}
          {step === "topic" && (
            <div ref={topicStepRef} className="space-y-4 animate-in fade-in duration-200">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-[#C4553D]" />
                <span className="text-sm font-medium text-gray-700">Select or create a topic for your group</span>
              </div>

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
                    setSelectedTopicId(undefined)
                    setIsCreatingNewTopic(false)
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
                    setSelectedTopicId(undefined)
                    setIsCreatingNewTopic(false)
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

              {/* Topic selector or create new */}
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
                    <>
                      {!isCreatingNewTopic ? (
                        <div className="space-y-2">
                          <select
                            value={selectedTopicId ?? ""}
                            onChange={(e) => setSelectedTopicId(e.target.value ? parseInt(e.target.value, 10) : undefined)}
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

                          {/* Create new topic button */}
                          <button
                            onClick={() => setIsCreatingNewTopic(true)}
                            className="flex items-center gap-2 text-sm text-[#C4553D] hover:text-[#B34835] transition-colors"
                          >
                            <Plus className="w-4 h-4" />
                            Create a new topic
                          </button>
                        </div>
                      ) : (
                        <div className="space-y-3 p-4 bg-white rounded-lg border border-[#C4553D]/20">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-gray-700">New Topic</span>
                            <button
                              onClick={() => {
                                setIsCreatingNewTopic(false)
                                setNewTopicTitle("")
                                setNewTopicDescription("")
                              }}
                              className="text-gray-400 hover:text-gray-600 transition-colors"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>

                          <input
                            type="text"
                            value={newTopicTitle}
                            onChange={(e) => setNewTopicTitle(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Topic title"
                            className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg
                              focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                              placeholder:text-gray-400"
                          />

                          <textarea
                            value={newTopicDescription}
                            onChange={(e) => setNewTopicDescription(e.target.value)}
                            onKeyDown={(e) => { if (e.key === "Escape") handleCancel() }}
                            placeholder="Brief description of this topic..."
                            rows={2}
                            className="w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg
                              focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                              placeholder:text-gray-400 resize-none"
                          />

                          <div className="flex gap-2 text-xs text-gray-400">
                            <span className="px-2 py-1 bg-gray-100 rounded">{selectedCountry?.name}</span>
                            <span className="px-2 py-1 bg-gray-100 rounded">{selectedBusinessDomain?.name}</span>
                          </div>
                        </div>
                      )}
                    </>
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
                    // Prefill group name with topic name
                    const topicName = isCreatingNewTopic ? newTopicTitle.trim() : selectedTopic?.title
                    if (topicName && !title.trim()) {
                      setTitle(topicName)
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
              {/* Selected topic summary */}
              <div className="p-3 bg-white rounded-lg border border-gray-100 flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-[#C4553D]/10 flex items-center justify-center flex-shrink-0">
                  <Tag className="w-4 h-4 text-[#C4553D]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-700 truncate">
                    {isCreatingNewTopic ? newTopicTitle : selectedTopic?.title}
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

  return (
    <button
      onClick={() => setIsCreating(true)}
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
