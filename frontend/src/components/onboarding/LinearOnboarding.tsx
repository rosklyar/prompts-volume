/**
 * LinearOnboarding - Traditional multi-step wizard
 * Clean progression through steps with clear navigation
 */

import { useState, useCallback, useRef, useMemo, useEffect } from "react"
import { useNavigate } from "@tanstack/react-router"
import {
  Globe,
  MapPin,
  Briefcase,
  Tag,
  ChevronLeft,
  ChevronRight,
  Check,
  Sparkles
} from "lucide-react"
import { useCountries, useBusinessDomains, useTopicsFiltered } from "@/hooks/useTopics"
import { useCompleteOnboarding } from "@/hooks/useOnboarding"
import { useCreateGroup, useAddPromptsToGroup } from "@/hooks/useGroups"
import { normalizeDomain } from "@/lib/domain"
import { TopicSelectionStep } from "./TopicSelectionStep"
import { PromptSelectionStep } from "./PromptSelectionStep"
import { GSCOnboardingStep } from "./GSCOnboardingStep"
import { CompetitorDiscoveryStep } from "./CompetitorDiscoveryStep"
import { VariationsInput } from "./VariationsInput"
import { BrandLogo } from "./BrandLogo"
import type { CompetitorInfo } from "@/types/groups"
import type { Topic } from "@/types/admin"
import type { DiscoveredCompetitor } from "@/types/onboarding"

type OnboardingStep = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8

const TOTAL_STEPS = 8
const ONBOARDING_STATE_KEY = "onboardingState"

interface BrandData {
  name: string
  domain: string
  variations: string[]
}

interface SavedOnboardingState {
  countryId?: number
  businessDomainId?: number
  brand: BrandData
  competitors: CompetitorInfo[]
  selectedTopics: Topic[]
  selectedPromptsByTopic: Record<number, number[]>
  groupsCreatedCount: number
  // Discovery state
  discoveredCompetitors: DiscoveredCompetitor[]
  selectedDiscovered: number[]
  editedDiscovered: Record<number, CompetitorInfo>
  isDiscoveryDone: boolean
}

interface LinearOnboardingProps {
  initialGscConnected?: boolean
}

// Step indicator component
function StepIndicator({ currentStep, totalSteps }: { currentStep: number; totalSteps: number }) {
  return (
    <div className="flex items-center justify-center gap-2 mb-8">
      {Array.from({ length: totalSteps }, (_, i) => i + 1).map((step) => (
        <div
          key={step}
          className={`
            w-2.5 h-2.5 rounded-full transition-all duration-300
            ${step === currentStep
              ? "w-8 bg-[#C4553D]"
              : step < currentStep
                ? "bg-[#C4553D]"
                : "bg-gray-200"
            }
          `}
        />
      ))}
    </div>
  )
}

export function LinearOnboarding({ initialGscConnected }: LinearOnboardingProps) {
  const navigate = useNavigate()
  const hasSubmittedRef = useRef(false)
  const completeOnboarding = useCompleteOnboarding()
  const createGroup = useCreateGroup()
  const addPromptsToGroup = useAddPromptsToGroup()

  // Restore state from sessionStorage if returning from OAuth
  const savedState = useMemo<SavedOnboardingState | null>(() => {
    if (!initialGscConnected) return null
    const saved = sessionStorage.getItem(ONBOARDING_STATE_KEY)
    if (saved) {
      sessionStorage.removeItem(ONBOARDING_STATE_KEY)  // Clear after use
      try {
        return JSON.parse(saved) as SavedOnboardingState
      } catch {
        return null
      }
    }
    return null
  }, [initialGscConnected])

  // Step state - go to step 7 (GSC) if returning from OAuth
  const [currentStep, setCurrentStep] = useState<OnboardingStep>(
    savedState ? 7 : 1
  )

  // Form data - restore from saved state if available
  const [countryId, setCountryId] = useState<number | undefined>(savedState?.countryId)
  const [businessDomainId, setBusinessDomainId] = useState<number | undefined>(savedState?.businessDomainId)
  const [brand, setBrand] = useState<BrandData>(
    savedState?.brand || { name: "", domain: "", variations: [] }
  )
  const [competitors, setCompetitors] = useState<CompetitorInfo[]>(savedState?.competitors || [])

  // Discovery state
  const [discoveredCompetitors, setDiscoveredCompetitors] = useState<DiscoveredCompetitor[]>(
    savedState?.discoveredCompetitors || []
  )
  const [selectedDiscovered, setSelectedDiscovered] = useState<Set<number>>(
    new Set(savedState?.selectedDiscovered || [])
  )
  const [editedDiscovered, setEditedDiscovered] = useState<Record<number, CompetitorInfo>>(
    savedState?.editedDiscovered || {}
  )
  const [isDiscoveryDone, setIsDiscoveryDone] = useState(savedState?.isDiscoveryDone || false)

  // Track previous brand to detect changes and reset discovery state
  const prevBrandRef = useRef({ name: brand.name, domain: brand.domain })

  useEffect(() => {
    const prevBrand = prevBrandRef.current
    const brandChanged =
      prevBrand.name !== brand.name ||
      prevBrand.domain !== brand.domain

    // Update ref for next comparison
    prevBrandRef.current = { name: brand.name, domain: brand.domain }

    // Skip if no actual change or initial empty state
    if (!brandChanged || (!prevBrand.name && !prevBrand.domain)) return

    // Reset ALL competitor/discovery state when brand changes
    setIsDiscoveryDone(false)
    setDiscoveredCompetitors([])
    setSelectedDiscovered(new Set())
    setEditedDiscovered({})
    setCompetitors([])
  }, [brand.name, brand.domain])

  // Topic/Prompt selection state (steps 5-6) - restore from saved state
  const [selectedTopics, setSelectedTopics] = useState<Topic[]>(savedState?.selectedTopics || [])
  const [selectedPromptsByTopic, setSelectedPromptsByTopic] = useState<Record<number, number[]>>(
    savedState?.selectedPromptsByTopic || {}
  )
  const [isCreatingGroups, setIsCreatingGroups] = useState(false)
  const [groupsCreatedCount, setGroupsCreatedCount] = useState(savedState?.groupsCreatedCount || 0)

  // GSC state (step 7)
  const [gscGroupCreated, setGscGroupCreated] = useState<{ groupId: number; promptCount: number } | null>(null)

  // Error state
  const [error, setError] = useState<string | null>(null)

  // Reference data
  const { data: countriesData, isLoading: isLoadingCountries } = useCountries()
  const { data: businessDomainsData, isLoading: isLoadingDomains } = useBusinessDomains()
  const { data: topicsData, isLoading: isLoadingTopics } = useTopicsFiltered(countryId, businessDomainId)

  const isPending = completeOnboarding.isPending || isCreatingGroups

  // Check if topic steps should be shown
  const shouldShowTopicSteps = countryId !== undefined && businessDomainId !== undefined

  // Navigation
  const goNext = useCallback(() => {
    setError(null)
    if (currentStep < TOTAL_STEPS) {
      setCurrentStep((prev) => (prev + 1) as OnboardingStep)
    }
  }, [currentStep])

  const goBack = useCallback(() => {
    setError(null)
    if (currentStep > 1) {
      setCurrentStep((prev) => (prev - 1) as OnboardingStep)
    }
  }, [currentStep])

  // Brand name change
  const handleBrandNameChange = (value: string) => {
    setBrand((prev) => ({ ...prev, name: value }))
  }

  // Brand variations change
  const handleBrandVariationsChange = useCallback((variations: string[]) => {
    setBrand((prev) => ({ ...prev, variations }))
  }, [])

  // Competitor handlers
  const handleAddCompetitor = useCallback((competitor: CompetitorInfo) => {
    setCompetitors((prev) => [...prev, competitor])
  }, [])

  const handleRemoveCompetitor = useCallback((index: number) => {
    setCompetitors((prev) => prev.filter((_, i) => i !== index))
  }, [])

  // Discovery handlers
  const handleDiscoveryComplete = useCallback((competitors: DiscoveredCompetitor[]) => {
    setDiscoveredCompetitors(competitors)
    // Select all by default
    setSelectedDiscovered(new Set(competitors.map((_, idx) => idx)))
    setIsDiscoveryDone(true)
  }, [])

  const handleToggleDiscoveredSelection = useCallback((index: number) => {
    setSelectedDiscovered((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }, [])

  const handleUpdateDiscovered = useCallback((index: number, updated: CompetitorInfo) => {
    setEditedDiscovered((prev) => ({
      ...prev,
      [index]: updated,
    }))
  }, [])

  // Get merged competitors list (manual + selected discovered)
  const getFinalCompetitors = useCallback((): CompetitorInfo[] => {
    // Helper to ensure lowercase name is in variations
    const withLowercaseName = (comp: CompetitorInfo): CompetitorInfo => ({
      ...comp,
      variations: [comp.name.trim().toLowerCase(), ...(comp.variations || [])],
    })

    // Start with manually added competitors (add lowercase name to variations)
    const manual = competitors.map(withLowercaseName)

    // Add selected discovered competitors (with any edits applied)
    const discovered: CompetitorInfo[] = []
    discoveredCompetitors.forEach((dc, idx) => {
      if (selectedDiscovered.has(idx)) {
        const edited = editedDiscovered[idx]
        const base = edited || {
          name: dc.brand_name,
          domain: dc.domain,
          variations: dc.variations || [],
        }
        discovered.push(withLowercaseName(base))
      }
    })

    return [...manual, ...discovered].slice(0, 10) // Max 10
  }, [competitors, discoveredCompetitors, selectedDiscovered, editedDiscovered])

  // Topic selection handlers
  const handleToggleTopic = useCallback((topic: Topic) => {
    setSelectedTopics((prev) => {
      const isSelected = prev.some((t) => t.id === topic.id)
      if (isSelected) {
        // Also clear selected prompts for this topic
        setSelectedPromptsByTopic((prevPrompts) => {
          const { [topic.id]: _removed, ...rest } = prevPrompts
          void _removed // silence unused var warning
          return rest
        })
        return prev.filter((t) => t.id !== topic.id)
      } else {
        return [...prev, topic]
      }
    })
  }, [])

  // Prompt selection handlers
  const handleTogglePrompt = useCallback((topicId: number, promptId: number) => {
    setSelectedPromptsByTopic((prev) => {
      const currentIds = prev[topicId] || []
      const isSelected = currentIds.includes(promptId)
      return {
        ...prev,
        [topicId]: isSelected
          ? currentIds.filter((id) => id !== promptId)
          : [...currentIds, promptId],
      }
    })
  }, [])

  const handleSelectAllForTopic = useCallback((topicId: number, promptIds: number[]) => {
    setSelectedPromptsByTopic((prev) => ({
      ...prev,
      [topicId]: promptIds,
    }))
  }, [])

  const handleDeselectAllForTopic = useCallback((topicId: number) => {
    setSelectedPromptsByTopic((prev) => ({
      ...prev,
      [topicId]: [],
    }))
  }, [])

  // Validation per step
  const canProceed = useCallback(() => {
    switch (currentStep) {
      case 1: return true // Welcome - always can proceed
      case 2: return countryId !== undefined // Industry is optional
      case 3: return brand.name.trim().length > 0
      case 4: return true // Competitors - optional
      case 5: return true // Topics - can always proceed (skip or with selection)
      case 6: return true // Prompts - can always proceed
      default: return true
    }
  }, [currentStep, countryId, brand.name])

  // Create groups from selected topics and prompts
  const createGroupsFromSelection = useCallback(async () => {
    const topicsWithPrompts = selectedTopics.filter(
      (topic) => (selectedPromptsByTopic[topic.id] || []).length > 0
    )

    if (topicsWithPrompts.length === 0) {
      return 0
    }

    const brandInfo = {
      name: brand.name.trim(),
      domain: normalizeDomain(brand.domain) || null,
      variations: [brand.name.trim().toLowerCase(), ...brand.variations],
    }

    const finalCompetitors = getFinalCompetitors()
    let createdCount = 0

    for (const topic of topicsWithPrompts) {
      const promptIds = selectedPromptsByTopic[topic.id] || []
      if (promptIds.length === 0) continue

      try {
        // Create group with topic title as name
        const group = await createGroup.mutateAsync({
          title: topic.title,
          topic: { existing_topic_id: topic.id },
          brand: brandInfo,
          competitors: finalCompetitors.length > 0 ? finalCompetitors : undefined,
          countryId,
        })

        // Add selected prompts
        await addPromptsToGroup.mutateAsync({
          groupId: group.id,
          promptIds,
        })

        createdCount++
      } catch {
        // Continue with other groups even if one fails
        console.error(`Failed to create group for topic ${topic.title}`)
      }
    }

    return createdCount
  }, [selectedTopics, selectedPromptsByTopic, brand, countryId, createGroup, addPromptsToGroup, getFinalCompetitors])

  // Submit handler
  const handleSubmit = useCallback(async () => {
    if (hasSubmittedRef.current) return
    hasSubmittedRef.current = true
    setIsCreatingGroups(true)

    try {
      // First create groups if there are selected prompts
      const groupsCreated = await createGroupsFromSelection()
      setGroupsCreatedCount(groupsCreated)

      const finalCompetitors = getFinalCompetitors()

      // Complete onboarding
      await completeOnboarding.mutateAsync({
        default_country_id: countryId!,
        default_business_domain_id: businessDomainId,
        default_brand: {
          name: brand.name.trim(),
          domain: normalizeDomain(brand.domain) || null,
          variations: [brand.name.trim().toLowerCase(), ...brand.variations],
        },
        default_competitors: finalCompetitors.length > 0 ? finalCompetitors : undefined,
      })

      // Go to complete step
      setCurrentStep(8)
    } catch (err) {
      hasSubmittedRef.current = false
      setError(err instanceof Error ? err.message : "Failed to save preferences")
    } finally {
      setIsCreatingGroups(false)
    }
  }, [brand, countryId, businessDomainId, completeOnboarding, createGroupsFromSelection, getFinalCompetitors])

  // Handle step 4 continue -> go to topics or GSC
  const handleStep4Continue = useCallback(() => {
    if (shouldShowTopicSteps) {
      setCurrentStep(5) // Go to topic selection
    } else {
      setCurrentStep(7) // Skip to GSC step
    }
  }, [shouldShowTopicSteps])

  // Handle step 5 continue -> go to prompts or GSC
  const handleStep5Continue = useCallback(() => {
    if (selectedTopics.length > 0) {
      setCurrentStep(6) // Go to prompt selection
    } else {
      setCurrentStep(7) // No topics selected, skip to GSC
    }
  }, [selectedTopics])

  // Handle step 6 continue -> go to GSC step
  const handleStep6Continue = useCallback(() => {
    setCurrentStep(7) // Go to GSC step
  }, [])

  // Handle GSC step completion
  const handleGSCComplete = useCallback((result: { groupId: number; promptCount: number } | null) => {
    setGscGroupCreated(result)
    handleSubmit()
  }, [handleSubmit])

  // Handle GSC step skip
  const handleGSCSkip = useCallback(() => {
    setGscGroupCreated(null)
    handleSubmit()
  }, [handleSubmit])

  // Save onboarding state before OAuth redirect
  const saveOnboardingState = useCallback(() => {
    const stateToSave: SavedOnboardingState = {
      countryId,
      businessDomainId,
      brand,
      competitors,
      selectedTopics,
      selectedPromptsByTopic,
      groupsCreatedCount,
      discoveredCompetitors,
      selectedDiscovered: Array.from(selectedDiscovered),
      editedDiscovered,
      isDiscoveryDone,
    }
    sessionStorage.setItem(ONBOARDING_STATE_KEY, JSON.stringify(stateToSave))
  }, [countryId, businessDomainId, brand, competitors, selectedTopics, selectedPromptsByTopic, groupsCreatedCount, discoveredCompetitors, selectedDiscovered, editedDiscovered, isDiscoveryDone])

  // Get the appropriate handler for each step's continue button
  const getStepContinueHandler = (step: number) => {
    switch (step) {
      case 4: return handleStep4Continue
      case 5: return handleStep5Continue
      case 6: return handleStep6Continue
      default: return goNext
    }
  }

  // Skip handler for topic/prompt steps -> go to GSC
  const handleSkipTopics = useCallback(() => {
    setSelectedTopics([])
    setSelectedPromptsByTopic({})
    setCurrentStep(7) // Go to GSC step
  }, [])

  // Get country and domain names for summary
  const selectedCountry = countriesData?.countries.find((c) => c.id === countryId)
  const selectedDomain = businessDomainsData?.business_domains.find((d) => d.id === businessDomainId)

  // Calculate visible steps (4 base + topic steps + GSC step if applicable)
  const visibleSteps = shouldShowTopicSteps ? 7 : 5 // Exclude complete step from indicator

  return (
    <div className="min-h-screen bg-[#FDFBF7] font-['DM_Sans']">
      <div className="max-w-2xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="font-['Fraunces'] text-3xl font-semibold text-[#1F2937] mb-2">
            LLMHERO
          </h1>
          <p className="text-[#6B7280]">AI search analytics for your brand</p>
        </div>

        {/* Step indicator */}
        {currentStep < 8 && (
          <StepIndicator
            currentStep={shouldShowTopicSteps ? currentStep : Math.min(currentStep, 5)}
            totalSteps={visibleSteps}
          />
        )}

        {/* Main card */}
        <div className="bg-white rounded-2xl shadow-lg shadow-gray-200/50 border border-gray-100 overflow-hidden">
          {/* Accent bar */}
          <div className="h-1 bg-[#C4553D]" />

          <div className="p-8">
            {/* Step 1: Welcome */}
            {currentStep === 1 && (
              <div className="text-center animate-in fade-in duration-300">
                <div className="w-16 h-16 rounded-full bg-[#C4553D]/10 flex items-center justify-center mx-auto mb-6">
                  <Sparkles className="w-8 h-8 text-[#C4553D]" />
                </div>
                <h2 className="font-['Fraunces'] text-2xl font-semibold text-[#1F2937] mb-3">
                  Welcome to LLMHERO
                </h2>
                <p className="text-[#6B7280] mb-8 max-w-md mx-auto">
                  Let's set up your brand tracking in just a few steps.
                  This helps us personalize your experience.
                </p>
                <button
                  onClick={goNext}
                  className="px-8 py-3 bg-[#C4553D] text-white font-medium rounded-xl
                    hover:bg-[#B34835] transition-colors shadow-lg shadow-[#C4553D]/20"
                >
                  Get Started
                </button>
              </div>
            )}

            {/* Step 2: Market Selection */}
            {currentStep === 2 && (
              <div className="animate-in fade-in duration-300">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
                    <Globe className="w-5 h-5 text-[#C4553D]" />
                  </div>
                  <div>
                    <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
                      Where is your business based?
                    </h2>
                    <p className="text-sm text-[#6B7280]">
                      This helps us show relevant topics
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  {/* Country */}
                  <div>
                    <label className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-400 mb-2">
                      <MapPin className="w-3.5 h-3.5" />
                      Country
                    </label>
                    <select
                      value={countryId ?? ""}
                      onChange={(e) => setCountryId(e.target.value ? parseInt(e.target.value, 10) : undefined)}
                      disabled={isLoadingCountries}
                      className="w-full px-4 py-3 text-sm bg-white border-2 border-gray-200 rounded-xl
                        focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                        disabled:opacity-50"
                    >
                      <option value="">Select your country...</option>
                      {countriesData?.countries.map((country) => (
                        <option key={country.id} value={country.id}>
                          {country.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Business Domain */}
                  <div>
                    <label className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-400 mb-2">
                      <Briefcase className="w-3.5 h-3.5" />
                      Industry
                    </label>
                    <select
                      value={businessDomainId ?? ""}
                      onChange={(e) => setBusinessDomainId(e.target.value ? parseInt(e.target.value, 10) : undefined)}
                      disabled={isLoadingDomains}
                      className="w-full px-4 py-3 text-sm bg-white border-2 border-gray-200 rounded-xl
                        focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                        disabled:opacity-50"
                    >
                      <option value="">Select your industry...</option>
                      {businessDomainsData?.business_domains.map((domain) => (
                        <option key={domain.id} value={domain.id}>
                          {domain.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Brand Info */}
            {currentStep === 3 && (
              <div className="animate-in fade-in duration-300">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
                    <Tag className="w-5 h-5 text-[#C4553D]" />
                  </div>
                  <div>
                    <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
                      What brand are you tracking?
                    </h2>
                    <p className="text-sm text-[#6B7280]">
                      We'll monitor how this brand appears in AI search
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  {/* Brand name */}
                  <div>
                    <label className="block text-xs uppercase tracking-widest text-gray-400 mb-2">
                      Brand name <span className="text-[#C4553D]">*</span>
                    </label>
                    <input
                      type="text"
                      value={brand.name}
                      onChange={(e) => handleBrandNameChange(e.target.value)}
                      placeholder="e.g., Nike"
                      className="w-full px-4 py-3 text-base bg-white border-2 border-gray-200 rounded-xl
                        focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                        placeholder:text-gray-400"
                    />
                  </div>

                  {/* Website */}
                  <div>
                    <label className="block text-xs uppercase tracking-widest text-gray-400 mb-2">
                      Website <span className="text-gray-300">(optional)</span>
                    </label>
                    <div className="relative">
                      <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        value={brand.domain}
                        onChange={(e) => setBrand((prev) => ({ ...prev, domain: e.target.value }))}
                        placeholder="e.g., nike.com"
                        className="w-full pl-11 pr-4 py-3 text-base bg-white border-2 border-gray-200 rounded-xl
                          focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                          placeholder:text-gray-400"
                      />
                    </div>
                  </div>

                  {/* Variations */}
                  <div>
                    <label className="block text-xs uppercase tracking-widest text-gray-400 mb-2">
                      Name variations <span className="text-gray-300">(optional)</span>
                    </label>
                    <VariationsInput
                      variations={brand.variations}
                      onChange={handleBrandVariationsChange}
                      primaryValue={brand.name.trim() || undefined}
                      placeholder="+ add variation"
                    />
                    <p className="mt-1.5 text-xs text-gray-400">
                      Different ways people might refer to your brand
                    </p>
                  </div>

                  {/* Brand preview */}
                  {brand.domain.trim() && (
                    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl border border-gray-100">
                      <BrandLogo domain={brand.domain} name={brand.name || brand.domain} size={36} />
                      <div className="min-w-0">
                        {brand.name.trim() && (
                          <p className="text-sm font-medium text-gray-800 truncate">{brand.name}</p>
                        )}
                        <p className="text-xs text-gray-500 truncate">{brand.domain}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Step 4: Competitors with Discovery */}
            {currentStep === 4 && countryId && (
              <CompetitorDiscoveryStep
                countryId={countryId}
                businessDomainId={businessDomainId}
                brand={{
                  name: brand.name.trim(),
                  domain: normalizeDomain(brand.domain) || null,
                  variations: [brand.name.trim().toLowerCase(), ...brand.variations],
                }}
                competitors={competitors}
                onAddCompetitor={handleAddCompetitor}
                onRemoveCompetitor={handleRemoveCompetitor}
                discoveredCompetitors={discoveredCompetitors}
                selectedDiscovered={selectedDiscovered}
                editedDiscovered={editedDiscovered}
                isDiscoveryDone={isDiscoveryDone}
                onDiscoveryComplete={handleDiscoveryComplete}
                onToggleDiscoveredSelection={handleToggleDiscoveredSelection}
                onUpdateDiscovered={handleUpdateDiscovered}
              />
            )}

            {/* Step 5: Topic Selection */}
            {currentStep === 5 && (
              <TopicSelectionStep
                topics={topicsData?.topics || []}
                isLoading={isLoadingTopics}
                selectedTopics={selectedTopics}
                onToggleTopic={handleToggleTopic}
              />
            )}

            {/* Step 6: Prompt Selection */}
            {currentStep === 6 && (
              <PromptSelectionStep
                selectedTopics={selectedTopics}
                selectedPromptsByTopic={selectedPromptsByTopic}
                onTogglePrompt={handleTogglePrompt}
                onSelectAllForTopic={handleSelectAllForTopic}
                onDeselectAllForTopic={handleDeselectAllForTopic}
              />
            )}

            {/* Step 7: GSC Integration */}
            {currentStep === 7 && countryId && (
              <GSCOnboardingStep
                brandDomain={normalizeDomain(brand.domain) || brand.name}
                countryId={countryId}
                businessDomain={selectedDomain?.name}
                brand={{
                  name: brand.name.trim(),
                  domain: normalizeDomain(brand.domain) || null,
                  variations: [brand.name.trim().toLowerCase(), ...brand.variations],
                }}
                competitors={getFinalCompetitors()}
                onComplete={handleGSCComplete}
                onSkip={handleGSCSkip}
                onBeforeConnect={saveOnboardingState}
              />
            )}

            {/* Step 8: Complete */}
            {currentStep === 8 && (
              <div className="text-center animate-in fade-in duration-300">
                {isPending ? (
                  <>
                    <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
                      <div className="w-8 h-8 border-3 border-gray-300 border-t-[#C4553D] rounded-full animate-spin" />
                    </div>
                    <p className="text-gray-600">
                      {isCreatingGroups ? "Creating your monitoring groups..." : "Saving your preferences..."}
                    </p>
                  </>
                ) : (
                  <>
                    <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-6">
                      <Check className="w-8 h-8 text-green-600" />
                    </div>
                    <h2 className="font-['Fraunces'] text-2xl font-semibold text-[#1F2937] mb-3">
                      You're all set!
                    </h2>
                    <p className="text-[#6B7280] mb-6">
                      Your preferences have been saved. You can update them anytime in Settings.
                    </p>

                    {/* Summary */}
                    <div className="inline-block bg-gray-50 rounded-xl p-4 text-left mb-8">
                      <div className="space-y-2 text-sm">
                        {selectedCountry && selectedDomain && (
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400">Market:</span>
                            <span className="text-gray-700">{selectedCountry.name} · {selectedDomain.name}</span>
                          </div>
                        )}
                        <div className="flex items-center gap-2">
                          <span className="text-gray-400">Brand:</span>
                          <span className="font-medium text-gray-700">{brand.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-gray-400">Competitors:</span>
                          <span className="text-gray-700">
                            {(() => {
                              const total = competitors.length + selectedDiscovered.size
                              return total === 0 ? "None" : total
                            })()}
                          </span>
                        </div>
                        {(groupsCreatedCount > 0 || gscGroupCreated) && (
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400">Groups created:</span>
                            <span className="text-[#C4553D] font-medium">
                              {groupsCreatedCount + (gscGroupCreated ? 1 : 0)}
                            </span>
                          </div>
                        )}
                        {gscGroupCreated && (
                          <div className="flex items-center gap-2">
                            <span className="text-gray-400">GSC keywords:</span>
                            <span className="text-[#C4553D] font-medium">{gscGroupCreated.promptCount}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <button
                      onClick={() => navigate({ to: "/", search: { tab: "prompts" } })}
                      className="px-8 py-3 bg-[#C4553D] text-white font-medium rounded-xl
                        hover:bg-[#B34835] transition-colors shadow-lg shadow-[#C4553D]/20
                        flex items-center gap-2 mx-auto"
                    >
                      Start Tracking
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </>
                )}
              </div>
            )}

            {/* Error display */}
            {error && (
              <p className="mt-4 text-sm text-red-600 text-center">{error}</p>
            )}

            {/* Navigation buttons (steps 2-6) */}
            {currentStep >= 2 && currentStep <= 6 && (
              <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-100">
                <button
                  onClick={goBack}
                  disabled={isPending}
                  className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-600
                    hover:text-gray-800 transition-colors disabled:opacity-50"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Back
                </button>
                <div className="flex items-center gap-3">
                  {/* Skip link for step 6 only - allows undoing topic selection */}
                  {currentStep === 6 && (
                    <button
                      onClick={handleSkipTopics}
                      disabled={isPending}
                      className="text-sm text-gray-500 hover:text-gray-700 transition-colors disabled:opacity-50"
                    >
                      Skip this step
                    </button>
                  )}
                  <button
                    onClick={getStepContinueHandler(currentStep)}
                    disabled={!canProceed() || isPending}
                    className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white
                      bg-[#C4553D] rounded-xl hover:bg-[#B34835] transition-colors
                      disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Continue
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer hint */}
        <p className="mt-6 text-xs text-gray-400 text-center italic">
          You can change these settings anytime from your account settings
        </p>
      </div>
    </div>
  )
}
