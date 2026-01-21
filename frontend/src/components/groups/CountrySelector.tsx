/**
 * CountrySelector - Popover for selecting a country for unlocked groups
 * Follows the editorial/magazine aesthetic of BrandEditor
 */

import { useState, useRef, useEffect } from "react"
import { X, Search, Check, MapPin } from "lucide-react"
import { useCountries } from "@/hooks/useTopics"
import type { CountryInfo } from "@/types/groups"

interface CountrySelectorProps {
  currentCountry: CountryInfo
  accentColor: string
  onCountryChange: (countryId: number) => void
  isUpdating: boolean
  onClose: () => void
}

export function CountrySelector({
  currentCountry,
  accentColor,
  onCountryChange,
  isUpdating,
  onClose,
}: CountrySelectorProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const { data: countriesData, isLoading } = useCountries()
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Auto-focus search on open
  useEffect(() => {
    searchInputRef.current?.focus()
  }, [])

  // Filter countries by search term
  const filteredCountries =
    countriesData?.countries.filter(
      (c) =>
        c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.iso_code.toLowerCase().includes(searchTerm.toLowerCase())
    ) || []

  const handleSelect = (countryId: number) => {
    if (countryId !== currentCountry.id && !isUpdating) {
      onCountryChange(countryId)
      onClose()
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Popover */}
      <div className="relative w-full max-w-sm mx-4 bg-white rounded-xl shadow-2xl overflow-hidden">
        {/* Header accent bar */}
        <div className="h-1 w-full" style={{ backgroundColor: accentColor }} />

        <div className="p-4">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4" style={{ color: accentColor }} />
              <h3
                className="text-lg font-['Fraunces'] tracking-tight"
                style={{ color: accentColor }}
              >
                Change Country
              </h3>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-full hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Search */}
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search countries..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-1 font-sans"
              style={{ "--tw-ring-color": accentColor } as React.CSSProperties}
            />
          </div>

          {/* Countries list */}
          <div className="max-h-[300px] overflow-y-auto space-y-1">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div
                  className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin"
                  style={{ borderColor: `${accentColor} transparent transparent transparent` }}
                />
              </div>
            ) : (
              filteredCountries.map((country) => (
                <button
                  key={country.id}
                  onClick={() => handleSelect(country.id)}
                  disabled={isUpdating}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left
                    ${country.id === currentCountry.id ? "bg-blue-50" : "hover:bg-gray-50"}
                    disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-gray-100 text-gray-600 uppercase">
                    {country.iso_code}
                  </span>
                  <span className="flex-1 text-sm text-gray-700">{country.name}</span>
                  {country.id === currentCountry.id && (
                    <Check className="w-4 h-4 text-blue-600" />
                  )}
                </button>
              ))
            )}
            {filteredCountries.length === 0 && !isLoading && (
              <p className="text-sm text-gray-400 text-center py-4 font-sans">
                No countries found
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
