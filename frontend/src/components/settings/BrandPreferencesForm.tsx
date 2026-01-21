import { useState } from "react"
import { Globe, Plus, Trash2, Check, MapPin, Briefcase } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useUserPreferences, useUpdatePreferences } from "@/hooks/useOnboarding"
import { useCountries, useBusinessDomains } from "@/hooks/useTopics"
import { normalizeDomain } from "@/lib/domain"
import type { BrandInfo, CompetitorInfo } from "@/types/groups"

const ACCENT_COLOR = "#C4553D"
const MAX_COMPETITORS = 10

export function BrandPreferencesForm() {
  const { data: preferences, isLoading } = useUserPreferences()

  // Show loading state while preferences are being fetched
  if (isLoading) {
    return (
      <div className="text-center py-8 text-gray-500">
        Loading preferences...
      </div>
    )
  }

  // Render the form once preferences are loaded
  return (
    <BrandPreferencesFormInner
      initialCountryId={preferences?.default_country_id ?? undefined}
      initialBusinessDomainId={preferences?.default_business_domain_id ?? undefined}
      initialBrand={preferences?.default_brand ?? null}
      initialCompetitors={preferences?.default_competitors ?? []}
    />
  )
}

interface BrandPreferencesFormInnerProps {
  initialCountryId: number | undefined
  initialBusinessDomainId: number | undefined
  initialBrand: BrandInfo | null
  initialCompetitors: CompetitorInfo[]
}

function BrandPreferencesFormInner({
  initialCountryId,
  initialBusinessDomainId,
  initialBrand,
  initialCompetitors,
}: BrandPreferencesFormInnerProps) {
  const updatePreferences = useUpdatePreferences()
  const { data: countriesData, isLoading: isLoadingCountries } = useCountries()
  const { data: businessDomainsData, isLoading: isLoadingDomains } = useBusinessDomains()

  // Market state
  const [countryId, setCountryId] = useState<number | undefined>(initialCountryId)
  const [businessDomainId, setBusinessDomainId] = useState<number | undefined>(
    initialBusinessDomainId
  )

  // Brand state - initialized from props
  const [brandName, setBrandName] = useState(initialBrand?.name ?? "")
  const [brandDomain, setBrandDomain] = useState(initialBrand?.domain ?? "")
  const [brandVariations, setBrandVariations] = useState(
    initialBrand?.variations.join(", ") ?? ""
  )

  // Competitors state
  const [competitors, setCompetitors] = useState<CompetitorInfo[]>(initialCompetitors)
  const [newCompName, setNewCompName] = useState("")
  const [newCompDomain, setNewCompDomain] = useState("")
  const [newCompVariations, setNewCompVariations] = useState("")
  const [newCompVariationsTouched, setNewCompVariationsTouched] = useState(false)

  // UI state
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  // Handle new competitor name change with prefill logic
  const handleNewCompNameChange = (value: string) => {
    setNewCompName(value)
    if (!newCompVariationsTouched) {
      setNewCompVariations(value.trim())
    }
  }

  const handleAddCompetitor = () => {
    if (!newCompName.trim()) return
    if (competitors.length >= MAX_COMPETITORS) {
      setError(`Maximum ${MAX_COMPETITORS} competitors allowed`)
      return
    }
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
    setError(null)
  }

  const handleRemoveCompetitor = (index: number) => {
    setCompetitors(competitors.filter((_, i) => i !== index))
  }

  const handleSave = () => {
    if (!countryId) {
      setError("Please select a country")
      return
    }
    if (!brandName.trim()) {
      setError("Please enter your brand name")
      return
    }

    const variations = brandVariations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)

    const brand: BrandInfo = {
      name: brandName.trim(),
      domain: normalizeDomain(brandDomain) || null,
      variations,
    }

    setError(null)
    setSuccess(false)

    updatePreferences.mutate(
      {
        default_country_id: countryId,
        default_business_domain_id: businessDomainId,
        default_brand: brand,
        default_competitors: competitors.length > 0 ? competitors : undefined,
      },
      {
        onSuccess: () => {
          setSuccess(true)
          setTimeout(() => setSuccess(false), 3000)
        },
        onError: (err) => {
          setError(err.message || "Failed to save preferences")
        },
      }
    )
  }

  return (
    <div className="space-y-6">
      {/* Market Section */}
      <div>
        <p className="text-xs uppercase tracking-widest text-gray-400 font-sans mb-3">
          Default Market
        </p>
        <p className="text-sm text-gray-500 mb-4">
          These settings will be pre-filled when creating new prompt groups
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Country selector */}
          <div>
            <label className="flex items-center gap-1.5 text-xs text-gray-500 mb-2">
              <MapPin className="w-3.5 h-3.5" />
              Country
            </label>
            <select
              value={countryId ?? ""}
              onChange={(e) =>
                setCountryId(e.target.value ? parseInt(e.target.value, 10) : undefined)
              }
              disabled={isLoadingCountries}
              className="w-full px-3 py-2.5 text-sm bg-white border border-gray-200 rounded-lg
                focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                disabled:opacity-50 disabled:bg-gray-50"
            >
              <option value="">Select country...</option>
              {countriesData?.countries.map((country) => (
                <option key={country.id} value={country.id}>
                  {country.name}
                </option>
              ))}
            </select>
          </div>

          {/* Business Domain selector */}
          <div>
            <label className="flex items-center gap-1.5 text-xs text-gray-500 mb-2">
              <Briefcase className="w-3.5 h-3.5" />
              Business Domain
            </label>
            <select
              value={businessDomainId ?? ""}
              onChange={(e) =>
                setBusinessDomainId(
                  e.target.value ? parseInt(e.target.value, 10) : undefined
                )
              }
              disabled={isLoadingDomains}
              className="w-full px-3 py-2.5 text-sm bg-white border border-gray-200 rounded-lg
                focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                disabled:opacity-50 disabled:bg-gray-50"
            >
              <option value="">Select industry...</option>
              {businessDomainsData?.business_domains.map((domain) => (
                <option key={domain.id} value={domain.id}>
                  {domain.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Brand Section */}
      <div>
        <p className="text-xs uppercase tracking-widest text-gray-400 font-sans mb-3">
          Your Brand
        </p>
        <div className="space-y-3">
          <input
            type="text"
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
            placeholder="Brand name"
          />
          <div className="relative">
            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={brandDomain}
              onChange={(e) => setBrandDomain(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
              placeholder="Website (e.g., nike.com)"
            />
          </div>
          <textarea
            value={brandVariations}
            onChange={(e) => setBrandVariations(e.target.value)}
            className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D] resize-none"
            rows={2}
            placeholder="Name variations (comma-separated)"
          />
        </div>
      </div>

      {/* Competitors Section */}
      <div>
        <p className="text-xs uppercase tracking-widest text-gray-400 font-sans mb-3">
          Competitors{" "}
          <span className="text-gray-300">(max {MAX_COMPETITORS})</span>
        </p>

        {/* Existing competitors */}
        {competitors.length > 0 && (
          <div className="space-y-2 mb-4">
            {competitors.map((comp, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-800 text-sm">{comp.name}</p>
                  {comp.domain && (
                    <p className="text-xs text-gray-500 flex items-center gap-1">
                      <Globe className="w-3 h-3" />
                      {comp.domain}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => handleRemoveCompetitor(index)}
                  className="p-1.5 rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                  disabled={updatePreferences.isPending}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Add competitor form */}
        {competitors.length < MAX_COMPETITORS && (
          <div className="space-y-2 p-4 border-2 border-dashed border-gray-200 rounded-lg">
            <input
              type="text"
              value={newCompName}
              onChange={(e) => handleNewCompNameChange(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
              placeholder="Competitor name"
              onKeyDown={(e) => e.key === "Enter" && handleAddCompetitor()}
              disabled={updatePreferences.isPending}
            />
            <div className="relative">
              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={newCompDomain}
                onChange={(e) => setNewCompDomain(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
                placeholder="Website (optional)"
                disabled={updatePreferences.isPending}
              />
            </div>
            <textarea
              value={newCompVariations}
              onChange={(e) => {
                setNewCompVariations(e.target.value)
                setNewCompVariationsTouched(true)
              }}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D] resize-none"
              rows={2}
              placeholder="Name variations (optional, comma-separated)"
              disabled={updatePreferences.isPending}
            />
            <button
              onClick={handleAddCompetitor}
              disabled={!newCompName.trim() || updatePreferences.isPending}
              className="w-full py-2 text-sm text-white rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 flex items-center justify-center gap-2"
              style={{ backgroundColor: ACCENT_COLOR }}
            >
              <Plus className="w-4 h-4" />
              Add competitor
            </button>
          </div>
        )}
      </div>

      {/* Error display */}
      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      {/* Success display */}
      {success && (
        <div className="flex items-center gap-2 text-sm text-green-600">
          <Check className="w-4 h-4" />
          Preferences saved successfully
        </div>
      )}

      {/* Save button */}
      <Button
        onClick={handleSave}
        disabled={!brandName.trim() || updatePreferences.isPending}
        className="w-full"
        style={{ backgroundColor: ACCENT_COLOR }}
      >
        {updatePreferences.isPending ? "Saving..." : "Save Preferences"}
      </Button>
    </div>
  )
}
