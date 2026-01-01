/**
 * AddGroupCard - Full-width card for creating a new group with brand and competitors
 * Requires a brand for meaningful reports, competitors are optional
 */

import { useState, useRef, useEffect } from "react"
import { ChevronDown, ChevronRight, Plus, X, Globe } from "lucide-react"
import type { BrandInfo, CompetitorInfo } from "@/types/groups"
import { MAX_GROUPS } from "./constants"

interface AddGroupCardProps {
  onAdd: (title: string, brand: BrandInfo, competitors?: CompetitorInfo[]) => void
  isLoading: boolean
}

function normalizeDomain(url: string): string {
  let domain = url.trim().toLowerCase()
  if (!domain) return ""
  // Remove protocol
  if (domain.startsWith("http://") || domain.startsWith("https://")) {
    domain = domain.split("://")[1]
  }
  // Remove trailing slash
  domain = domain.replace(/\/$/, "")
  return domain
}

export function AddGroupCard({ onAdd, isLoading }: AddGroupCardProps) {
  const [isCreating, setIsCreating] = useState(false)
  const [title, setTitle] = useState("")

  // Brand state
  const [brandName, setBrandName] = useState("")
  const [brandDomain, setBrandDomain] = useState("")
  const [brandVariations, setBrandVariations] = useState("")

  // Competitors state
  const [showCompetitors, setShowCompetitors] = useState(false)
  const [competitors, setCompetitors] = useState<CompetitorInfo[]>([])
  const [newCompName, setNewCompName] = useState("")
  const [newCompDomain, setNewCompDomain] = useState("")
  const [newCompVariations, setNewCompVariations] = useState("")

  const titleInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isCreating && titleInputRef.current) {
      titleInputRef.current.focus()
    }
  }, [isCreating])

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

      onAdd(trimmedTitle, brand, competitors.length > 0 ? competitors : undefined)
      resetForm()
    }
  }

  const resetForm = () => {
    setTitle("")
    setBrandName("")
    setBrandDomain("")
    setBrandVariations("")
    setCompetitors([])
    setNewCompName("")
    setNewCompDomain("")
    setNewCompVariations("")
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

  const canCreate = title.trim() && brandName.trim()

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
                onChange={(e) => setBrandName(e.target.value)}
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
                onChange={(e) => setBrandVariations(e.target.value)}
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
                    onChange={(e) => setNewCompName(e.target.value)}
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
                      onChange={(e) => setNewCompVariations(e.target.value)}
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
          <div className="flex justify-end gap-2 pt-2 border-t border-gray-200">
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
