/**
 * LinearOnboarding - Traditional multi-step wizard
 * Clean progression through steps with clear navigation
 */

import { useState, useCallback, useRef } from "react"
import { useNavigate } from "@tanstack/react-router"
import {
  Globe,
  MapPin,
  Briefcase,
  Tag,
  Users,
  ChevronLeft,
  ChevronRight,
  Plus,
  X,
  Check,
  Sparkles
} from "lucide-react"
import { useCountries, useBusinessDomains } from "@/hooks/useTopics"
import { useCompleteOnboarding } from "@/hooks/useOnboarding"
import { normalizeDomain } from "@/lib/domain"
import type { CompetitorInfo } from "@/types/groups"

type OnboardingStep = 1 | 2 | 3 | 4 | 5

const TOTAL_STEPS = 5

interface BrandData {
  name: string
  domain: string
  variations: string
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

export function LinearOnboarding() {
  const navigate = useNavigate()
  const hasSubmittedRef = useRef(false)
  const completeOnboarding = useCompleteOnboarding()

  // Step state
  const [currentStep, setCurrentStep] = useState<OnboardingStep>(1)

  // Form data
  const [countryId, setCountryId] = useState<number | undefined>()
  const [businessDomainId, setBusinessDomainId] = useState<number | undefined>()
  const [brand, setBrand] = useState<BrandData>({
    name: "",
    domain: "",
    variations: "",
  })
  const [brandVariationsTouched, setBrandVariationsTouched] = useState(false)
  const [competitors, setCompetitors] = useState<CompetitorInfo[]>([])
  const [newCompName, setNewCompName] = useState("")
  const [newCompDomain, setNewCompDomain] = useState("")
  const [newCompVariations, setNewCompVariations] = useState("")
  const [newCompVariationsTouched, setNewCompVariationsTouched] = useState(false)

  // Error state
  const [error, setError] = useState<string | null>(null)

  // Reference data
  const { data: countriesData, isLoading: isLoadingCountries } = useCountries()
  const { data: businessDomainsData, isLoading: isLoadingDomains } = useBusinessDomains()

  const isPending = completeOnboarding.isPending

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

  // Brand name change with auto-fill variations
  const handleBrandNameChange = (value: string) => {
    setBrand((prev) => ({ ...prev, name: value }))
    if (!brandVariationsTouched) {
      setBrand((prev) => ({ ...prev, variations: value.trim() }))
    }
  }

  // Competitor handlers
  const handleNewCompNameChange = (value: string) => {
    setNewCompName(value)
    if (!newCompVariationsTouched) {
      setNewCompVariations(value.trim())
    }
  }

  const handleAddCompetitor = () => {
    if (!newCompName.trim()) return
    if (competitors.length >= 10) return

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

  // Validation per step
  const canProceed = useCallback(() => {
    switch (currentStep) {
      case 1: return true // Welcome - always can proceed
      case 2: return countryId !== undefined // Industry is optional
      case 3: return brand.name.trim().length > 0
      case 4: return true // Competitors - optional
      default: return true
    }
  }, [currentStep, countryId, brand.name])

  // Submit handler
  const handleSubmit = useCallback(() => {
    if (hasSubmittedRef.current) return
    hasSubmittedRef.current = true

    const variations = brand.variations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)

    completeOnboarding.mutate(
      {
        default_country_id: countryId!,
        default_business_domain_id: businessDomainId,
        default_brand: {
          name: brand.name.trim(),
          domain: normalizeDomain(brand.domain) || null,
          variations,
        },
        default_competitors: competitors.length > 0 ? competitors : undefined,
      },
      {
        onSuccess: () => {
          navigate({ to: "/" })
        },
        onError: (err) => {
          hasSubmittedRef.current = false
          setError(err.message || "Failed to save preferences")
        },
      }
    )
  }, [brand, competitors, countryId, businessDomainId, completeOnboarding, navigate])

  // Handle step 4 continue -> submit
  const handleStep4Continue = useCallback(() => {
    handleSubmit()
  }, [handleSubmit])

  // Get country and domain names for summary
  const selectedCountry = countriesData?.countries.find((c) => c.id === countryId)
  const selectedDomain = businessDomainsData?.business_domains.find((d) => d.id === businessDomainId)

  return (
    <div className="min-h-screen bg-[#FDFBF7] font-['DM_Sans']">
      <div className="max-w-xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="font-['Fraunces'] text-3xl font-semibold text-[#1F2937] mb-2">
            LLMHERO
          </h1>
          <p className="text-[#6B7280]">AI search analytics for your brand</p>
        </div>

        {/* Step indicator */}
        {currentStep < 5 && (
          <StepIndicator currentStep={currentStep} totalSteps={4} />
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
                    <input
                      type="text"
                      value={brand.variations}
                      onChange={(e) => {
                        setBrand((prev) => ({ ...prev, variations: e.target.value }))
                        setBrandVariationsTouched(true)
                      }}
                      placeholder="Nike, Nike Inc, Just Do It"
                      className="w-full px-4 py-3 text-base bg-white border-2 border-gray-200 rounded-xl
                        focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                        placeholder:text-gray-400"
                    />
                    <p className="mt-1.5 text-xs text-gray-400">
                      Different ways people might refer to your brand, comma-separated
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Step 4: Competitors */}
            {currentStep === 4 && (
              <div className="animate-in fade-in duration-300">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
                    <Users className="w-5 h-5 text-[#C4553D]" />
                  </div>
                  <div>
                    <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
                      Add competitors
                    </h2>
                    <p className="text-sm text-[#6B7280]">
                      Track how your brand compares · Optional
                    </p>
                  </div>
                </div>

                {/* Existing competitors */}
                {competitors.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {competitors.map((comp, index) => (
                      <div
                        key={index}
                        className="flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl"
                      >
                        <span className="text-sm font-medium text-gray-700">{comp.name}</span>
                        {comp.domain && (
                          <span className="text-xs text-gray-400">{comp.domain}</span>
                        )}
                        <button
                          onClick={() => handleRemoveCompetitor(index)}
                          className="p-1 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Add competitor form */}
                {competitors.length < 10 && (
                  <div className="p-4 bg-gray-50/70 rounded-xl border-2 border-dashed border-gray-200 space-y-3">
                    <input
                      type="text"
                      value={newCompName}
                      onChange={(e) => handleNewCompNameChange(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAddCompetitor()}
                      placeholder="Competitor name"
                      className="w-full px-4 py-2.5 text-sm bg-white border border-gray-200 rounded-lg
                        focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
                    />
                    <div className="relative">
                      <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        value={newCompDomain}
                        onChange={(e) => setNewCompDomain(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleAddCompetitor()}
                        placeholder="Website (optional)"
                        className="w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-gray-200 rounded-lg
                          focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
                      />
                    </div>
                    <input
                      type="text"
                      value={newCompVariations}
                      onChange={(e) => {
                        setNewCompVariations(e.target.value)
                        setNewCompVariationsTouched(true)
                      }}
                      onKeyDown={(e) => e.key === "Enter" && handleAddCompetitor()}
                      placeholder="Name variations (optional)"
                      className="w-full px-4 py-2.5 text-sm bg-white border border-gray-200 rounded-lg
                        focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
                    />
                    <button
                      onClick={handleAddCompetitor}
                      disabled={!newCompName.trim()}
                      className="w-full py-2.5 text-sm font-medium text-white bg-[#C4553D] rounded-lg
                        hover:bg-[#B34835] transition-colors disabled:opacity-40 disabled:cursor-not-allowed
                        flex items-center justify-center gap-2"
                    >
                      <Plus className="w-4 h-4" />
                      Add competitor
                    </button>
                  </div>
                )}

                {competitors.length >= 10 && (
                  <p className="text-sm text-gray-500 text-center">
                    Maximum 10 competitors reached
                  </p>
                )}
              </div>
            )}

            {/* Step 5: Complete */}
            {currentStep === 5 && (
              <div className="text-center animate-in fade-in duration-300">
                {isPending ? (
                  <>
                    <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
                      <div className="w-8 h-8 border-3 border-gray-300 border-t-[#C4553D] rounded-full animate-spin" />
                    </div>
                    <p className="text-gray-600">Saving your preferences...</p>
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
                            {competitors.length === 0 ? "None" : competitors.length}
                          </span>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => navigate({ to: "/" })}
                      className="px-8 py-3 bg-[#C4553D] text-white font-medium rounded-xl
                        hover:bg-[#B34835] transition-colors shadow-lg shadow-[#C4553D]/20
                        flex items-center gap-2 mx-auto"
                    >
                      Go to Dashboard
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

            {/* Navigation buttons (steps 2-4) */}
            {currentStep >= 2 && currentStep <= 4 && (
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
                <button
                  onClick={currentStep === 4 ? handleStep4Continue : goNext}
                  disabled={!canProceed() || isPending}
                  className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white
                    bg-[#C4553D] rounded-xl hover:bg-[#B34835] transition-colors
                    disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {currentStep === 4 ? "Finish Setup" : "Continue"}
                  <ChevronRight className="w-4 h-4" />
                </button>
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
