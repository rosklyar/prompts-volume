/**
 * CompetitorDiscoveryStep - Main Step 4 component with AI discovery integration
 * Allows users to discover competitors via AI or add them manually
 */

import { useState, useCallback, useEffect, useRef } from "react"
import { Users, Search, Plus, X, Globe } from "lucide-react"
import { onboardingApi } from "@/client/api"
import { CompetitorDiscoveryLoader } from "./CompetitorDiscoveryLoader"
import { DiscoveredCompetitorCard } from "./DiscoveredCompetitorCard"
import { BrandLogo } from "./BrandLogo"
import { normalizeDomain } from "@/lib/domain"
import type { BrandInfo, CompetitorInfo } from "@/types/groups"
import type { DiscoveredCompetitor, DiscoverCompetitorsRequest } from "@/types/onboarding"

const DISCOVERY_CACHE_KEY = "competitorDiscoveryCache"

interface CachedDiscovery {
  request: DiscoverCompetitorsRequest
  competitors: DiscoveredCompetitor[]
}

function getCacheKey(request: DiscoverCompetitorsRequest): string {
  return JSON.stringify({
    country_id: request.country_id,
    business_domain_id: request.business_domain_id,
    brand_name: request.brand.name.toLowerCase(),
    brand_domain: request.brand.domain?.toLowerCase() || null,
  })
}

function getCachedDiscovery(request: DiscoverCompetitorsRequest): DiscoveredCompetitor[] | null {
  try {
    const cached = sessionStorage.getItem(DISCOVERY_CACHE_KEY)
    if (!cached) return null

    const data: CachedDiscovery = JSON.parse(cached)
    const currentKey = getCacheKey(request)
    const cachedKey = getCacheKey(data.request)

    if (currentKey === cachedKey) {
      return data.competitors
    }
    return null
  } catch {
    return null
  }
}

function setCachedDiscovery(request: DiscoverCompetitorsRequest, competitors: DiscoveredCompetitor[]): void {
  try {
    const data: CachedDiscovery = { request, competitors }
    sessionStorage.setItem(DISCOVERY_CACHE_KEY, JSON.stringify(data))
  } catch {
    // Ignore storage errors
  }
}

interface CompetitorDiscoveryStepProps {
  countryId: number
  businessDomainId?: number
  brand: BrandInfo
  // Manual competitors (existing)
  competitors: CompetitorInfo[]
  onAddCompetitor: (competitor: CompetitorInfo) => void
  onRemoveCompetitor: (index: number) => void
  // Discovered competitors state
  discoveredCompetitors: DiscoveredCompetitor[]
  selectedDiscovered: Set<number>
  editedDiscovered: Record<number, CompetitorInfo>
  isDiscoveryDone: boolean
  onDiscoveryComplete: (competitors: DiscoveredCompetitor[]) => void
  onToggleDiscoveredSelection: (index: number) => void
  onUpdateDiscovered: (index: number, updated: CompetitorInfo) => void
}

export function CompetitorDiscoveryStep({
  countryId,
  businessDomainId,
  brand,
  competitors,
  onAddCompetitor,
  onRemoveCompetitor,
  discoveredCompetitors,
  selectedDiscovered,
  editedDiscovered,
  isDiscoveryDone,
  onDiscoveryComplete,
  onToggleDiscoveredSelection,
  onUpdateDiscovered,
}: CompetitorDiscoveryStepProps) {
  // Manual form state
  const [newCompName, setNewCompName] = useState("")
  const [newCompDomain, setNewCompDomain] = useState("")
  const [newCompVariations, setNewCompVariations] = useState("")
  const [newCompVariationsTouched, setNewCompVariationsTouched] = useState(false)
  const [showManualForm, setShowManualForm] = useState(false)

  // Local discovery state - track the brand we last triggered discovery for
  const [discoveredBrandKey, setDiscoveredBrandKey] = useState<string | null>(null)
  const [isFetching, setIsFetching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Ref to track in-flight request and prevent duplicate calls
  const pendingBrandKeyRef = useRef<string | null>(null)

  // Total competitors (manual + selected discovered)
  const totalSelected = competitors.length + selectedDiscovered.size
  const canAddMore = totalSelected < 10

  // Create a stable brand key for comparison
  const brandKey = `${brand.name.toLowerCase()}|${brand.domain?.toLowerCase() || ""}`

  // Determine if we need to show loading state
  const needsDiscovery = !isDiscoveryDone && discoveredBrandKey !== brandKey
  const isLoading = needsDiscovery || isFetching

  // Auto-trigger discovery when brand changes or component mounts
  useEffect(() => {
    // Skip if discovery is already done for current brand
    if (isDiscoveryDone) {
      return
    }

    // Skip if we already triggered or completed discovery for this exact brand
    if (discoveredBrandKey === brandKey || pendingBrandKeyRef.current === brandKey) {
      return
    }

    // Mark this brand as pending (prevents duplicate calls before state updates)
    pendingBrandKeyRef.current = brandKey

    const request = {
      country_id: countryId,
      business_domain_id: businessDomainId,
      brand,
    }

    // Check cache first
    const cached = getCachedDiscovery(request)
    if (cached) {
      // Use setTimeout to call callbacks after render (avoids sync setState in effect)
      setTimeout(() => {
        setDiscoveredBrandKey(brandKey)
        onDiscoveryComplete(cached)
      }, 0)
      return
    }

    // No cache - fetch from API
    // Use setTimeout to batch state updates and avoid sync setState in effect
    setTimeout(() => {
      setDiscoveredBrandKey(brandKey)
      setIsFetching(true)
      setError(null)

      onboardingApi
        .discoverCompetitors(request)
        .then((data) => {
          setCachedDiscovery(request, data.competitors)
          onDiscoveryComplete(data.competitors)
        })
        .catch((err) => {
          setError(err.message || "Discovery failed")
        })
        .finally(() => {
          setIsFetching(false)
        })
    }, 0)
  }, [isDiscoveryDone, discoveredBrandKey, brandKey, countryId, businessDomainId, brand, onDiscoveryComplete])

  const handleRetryDiscover = useCallback(() => {
    setIsFetching(true)
    setError(null)

    const request = {
      country_id: countryId,
      business_domain_id: businessDomainId,
      brand,
    }

    // Retry always fetches fresh (ignores cache)
    onboardingApi
      .discoverCompetitors(request)
      .then((data) => {
        setCachedDiscovery(request, data.competitors)
        onDiscoveryComplete(data.competitors)
      })
      .catch((err) => {
        setError(err.message || "Discovery failed")
      })
      .finally(() => {
        setIsFetching(false)
      })
  }, [countryId, businessDomainId, brand, onDiscoveryComplete])

  const handleNewCompNameChange = (value: string) => {
    setNewCompName(value)
    if (!newCompVariationsTouched) {
      setNewCompVariations(value.trim())
    }
  }

  const handleAddManualCompetitor = useCallback(() => {
    if (!newCompName.trim()) return
    if (!canAddMore) return

    const variations = newCompVariations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)

    onAddCompetitor({
      name: newCompName.trim(),
      domain: normalizeDomain(newCompDomain) || null,
      variations,
    })

    setNewCompName("")
    setNewCompDomain("")
    setNewCompVariations("")
    setNewCompVariationsTouched(false)
    setShowManualForm(false)
  }, [newCompName, newCompDomain, newCompVariations, canAddMore, onAddCompetitor])

  // Show loading state
  if (isLoading) {
    return (
      <div className="animate-in fade-in duration-300">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
            <Users className="w-5 h-5 text-[#C4553D]" />
          </div>
          <div>
            <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
              Discovering competitors
            </h2>
            <p className="text-sm text-[#6B7280]">
              Our AI is finding your top competitors
            </p>
          </div>
        </div>

        <CompetitorDiscoveryLoader />
      </div>
    )
  }

  // Only show first 5 discovered competitors
  const visibleDiscovered = discoveredCompetitors.slice(0, 5)

  return (
    <div className="animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
          <Users className="w-5 h-5 text-[#C4553D]" />
        </div>
        <div>
          <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
            Add competitors
          </h2>
          <p className="text-sm text-[#6B7280]">
            You can add up to 10 competitors
          </p>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-100 rounded-xl">
          <p className="text-sm text-red-600">
            {error}. You can try again or add competitors manually.
          </p>
          <button
            type="button"
            onClick={handleRetryDiscover}
            className="mt-2 text-sm text-red-700 underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Discovered competitors */}
      {isDiscoveryDone && discoveredCompetitors.length > 0 && (
        <div className="mb-6">
          <p className="text-xs uppercase tracking-widest text-gray-400 mb-3">
            AI Discovered ({selectedDiscovered.size} selected)
          </p>
          <div className="grid gap-3 max-h-[400px] overflow-y-auto pr-1">
            {visibleDiscovered.map((comp, idx) => {
              const edited = editedDiscovered[idx]
              const displayCompetitor: CompetitorInfo = edited || {
                name: comp.brand_name,
                domain: comp.domain,
                variations: comp.variations || [],
              }

              return (
                <DiscoveredCompetitorCard
                  key={`${comp.brand_name}-${comp.domain || idx}`}
                  competitor={displayCompetitor}
                  isSelected={selectedDiscovered.has(idx)}
                  onToggleSelect={() => onToggleDiscoveredSelection(idx)}
                  onUpdate={(updated) => onUpdateDiscovered(idx, updated)}
                />
              )
            })}
          </div>
        </div>
      )}

      {/* Empty discovery state */}
      {isDiscoveryDone && discoveredCompetitors.length === 0 && (
        <div className="text-center py-8 mb-6 bg-gray-50 rounded-xl">
          <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
            <Search className="w-6 h-6 text-gray-400" />
          </div>
          <p className="text-gray-600 font-medium mb-1">No competitors found</p>
          <p className="text-sm text-gray-500 mb-4">
            We couldn't find competitors automatically. Add them manually below.
          </p>
        </div>
      )}

      {/* Divider */}
      {(isDiscoveryDone || competitors.length > 0) && (
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 h-px bg-gray-200" />
          <span className="text-xs text-gray-400">or add manually</span>
          <div className="flex-1 h-px bg-gray-200" />
        </div>
      )}

      {/* Manual competitors list */}
      {competitors.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {competitors.map((comp, index) => (
            <div
              key={index}
              className="flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl"
            >
              <BrandLogo domain={comp.domain} name={comp.name} size={20} />
              <span className="text-sm font-medium text-gray-700">{comp.name}</span>
              {comp.domain && (
                <span className="text-xs text-gray-400">{comp.domain}</span>
              )}
              <button
                type="button"
                onClick={() => onRemoveCompetitor(index)}
                className="p-1 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add manual competitor */}
      {canAddMore && (
        <>
          {!showManualForm ? (
            <button
              type="button"
              onClick={() => setShowManualForm(true)}
              className="w-full py-3 text-sm font-medium text-gray-600 bg-gray-50/70
                         rounded-xl border-2 border-dashed border-gray-200
                         hover:border-gray-300 hover:text-gray-700 transition-colors
                         flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add competitor manually
            </button>
          ) : (
            <div className="p-4 bg-gray-50/70 rounded-xl border-2 border-dashed border-gray-200 space-y-3">
              <input
                type="text"
                value={newCompName}
                onChange={(e) => handleNewCompNameChange(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddManualCompetitor()}
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
                  onKeyDown={(e) => e.key === "Enter" && handleAddManualCompetitor()}
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
                onKeyDown={(e) => e.key === "Enter" && handleAddManualCompetitor()}
                placeholder="Name variations (optional)"
                className="w-full px-4 py-2.5 text-sm bg-white border border-gray-200 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setShowManualForm(false)}
                  className="flex-1 py-2.5 text-sm font-medium text-gray-600 bg-white rounded-lg
                             border border-gray-200 hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleAddManualCompetitor}
                  disabled={!newCompName.trim()}
                  className="flex-1 py-2.5 text-sm font-medium text-white bg-[#C4553D] rounded-lg
                             hover:bg-[#B34835] transition-colors disabled:opacity-40 disabled:cursor-not-allowed
                             flex items-center justify-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  Add
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {!canAddMore && (
        <p className="text-sm text-gray-500 text-center">
          Maximum 10 competitors reached
        </p>
      )}
    </div>
  )
}
