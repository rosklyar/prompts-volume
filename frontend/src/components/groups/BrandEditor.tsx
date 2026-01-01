/**
 * BrandEditor - Modal for configuring brand and competitors
 * Editorial/magazine aesthetic with refined typography
 */

import { useState } from "react"
import { Globe, X, Plus, Pencil, Trash2, ChevronDown, ChevronRight } from "lucide-react"
import type { BrandInfo, CompetitorInfo } from "@/types/groups"

interface BrandEditorProps {
  brand: BrandInfo
  competitors: CompetitorInfo[]
  onBrandChange: (brand: BrandInfo) => void
  onCompetitorsChange: (competitors: CompetitorInfo[]) => void
  accentColor: string
  onClose: () => void
}

function normalizeDomain(url: string): string {
  let domain = url.trim().toLowerCase()
  if (!domain) return ""
  if (domain.startsWith("http://") || domain.startsWith("https://")) {
    domain = domain.split("://")[1]
  }
  domain = domain.replace(/\/$/, "")
  return domain
}

export function BrandEditor({
  brand,
  competitors,
  onBrandChange,
  onCompetitorsChange,
  accentColor,
  onClose,
}: BrandEditorProps) {
  // Brand editing state
  const [editingBrand, setEditingBrand] = useState(false)
  const [brandName, setBrandName] = useState(brand.name)
  const [brandDomain, setBrandDomain] = useState(brand.domain || "")
  const [brandVariations, setBrandVariations] = useState(brand.variations.join(", "))

  // Competitors section
  const [showCompetitors, setShowCompetitors] = useState(competitors.length > 0)
  const [editingCompIndex, setEditingCompIndex] = useState<number | null>(null)
  const [editCompName, setEditCompName] = useState("")
  const [editCompDomain, setEditCompDomain] = useState("")
  const [editCompVariations, setEditCompVariations] = useState("")

  // New competitor form
  const [newCompName, setNewCompName] = useState("")
  const [newCompDomain, setNewCompDomain] = useState("")
  const [newCompVariations, setNewCompVariations] = useState("")

  const handleSaveBrand = () => {
    if (!brandName.trim()) return
    const variations = brandVariations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)
    onBrandChange({
      name: brandName.trim(),
      domain: normalizeDomain(brandDomain) || null,
      variations,
    })
    setEditingBrand(false)
  }

  const handleCancelBrandEdit = () => {
    setBrandName(brand.name)
    setBrandDomain(brand.domain || "")
    setBrandVariations(brand.variations.join(", "))
    setEditingBrand(false)
  }

  const handleAddCompetitor = () => {
    if (!newCompName.trim()) return
    const variations = newCompVariations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)
    onCompetitorsChange([
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
    onCompetitorsChange(competitors.filter((_, i) => i !== index))
  }

  const handleStartEditCompetitor = (index: number) => {
    setEditingCompIndex(index)
    setEditCompName(competitors[index].name)
    setEditCompDomain(competitors[index].domain || "")
    setEditCompVariations(competitors[index].variations.join(", "))
  }

  const handleSaveCompetitor = () => {
    if (editingCompIndex === null || !editCompName.trim()) return
    const variations = editCompVariations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)
    const updated = [...competitors]
    updated[editingCompIndex] = {
      name: editCompName.trim(),
      domain: normalizeDomain(editCompDomain) || null,
      variations,
    }
    onCompetitorsChange(updated)
    setEditingCompIndex(null)
  }

  const handleCancelEditCompetitor = () => {
    setEditingCompIndex(null)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-white rounded-xl shadow-2xl overflow-hidden max-h-[90vh] overflow-y-auto">
        {/* Header accent bar */}
        <div
          className="h-1 w-full"
          style={{ backgroundColor: accentColor }}
        />

        <div className="p-6">
          {/* Title */}
          <div className="flex items-center justify-between mb-6">
            <h2
              className="text-xl font-['Fraunces'] tracking-tight"
              style={{ color: accentColor }}
            >
              Brand & Competitors
            </h2>
            <button
              onClick={onClose}
              className="p-1.5 rounded-full hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Brand Section */}
          <div className="mb-6">
            <p className="text-xs uppercase tracking-widest text-gray-400 font-sans mb-3">
              Your Brand
            </p>

            {editingBrand ? (
              <div className="space-y-3 p-4 bg-gray-50 rounded-lg border border-gray-100">
                <input
                  type="text"
                  value={brandName}
                  onChange={(e) => setBrandName(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans"
                  placeholder="Brand name"
                />
                <div className="relative">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    value={brandDomain}
                    onChange={(e) => setBrandDomain(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans"
                    placeholder="Domain (e.g., nike.com)"
                  />
                </div>
                <textarea
                  value={brandVariations}
                  onChange={(e) => setBrandVariations(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans resize-none"
                  rows={2}
                  placeholder="Variations (comma-separated)"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleSaveBrand}
                    disabled={!brandName.trim()}
                    className="px-4 py-1.5 text-sm font-sans text-white rounded-md transition-colors disabled:opacity-50"
                    style={{ backgroundColor: accentColor }}
                  >
                    Save
                  </button>
                  <button
                    onClick={handleCancelBrandEdit}
                    className="px-4 py-1.5 text-sm font-sans text-gray-500 hover:text-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="group rounded-lg border border-gray-100 bg-gray-50/50 p-4 transition-all hover:border-gray-200">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-800">{brand.name}</p>
                    {brand.domain && (
                      <p className="text-sm text-gray-500 mt-0.5 flex items-center gap-1.5">
                        <Globe className="w-3.5 h-3.5" />
                        {brand.domain}
                      </p>
                    )}
                    {brand.variations.length > 0 && (
                      <p className="text-xs text-gray-400 mt-1 font-sans">
                        {brand.variations.join(", ")}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => setEditingBrand(true)}
                    className="p-2 rounded hover:bg-white text-gray-400 hover:text-gray-600 transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Competitors Section */}
          <div>
            <button
              type="button"
              onClick={() => setShowCompetitors(!showCompetitors)}
              className="flex items-center gap-2 text-xs uppercase tracking-widest text-gray-400 font-sans mb-3 hover:text-gray-600 transition-colors"
            >
              {showCompetitors ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5" />
              )}
              Competitors
              {competitors.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-[10px] bg-gray-200 text-gray-600 rounded-full">
                  {competitors.length}
                </span>
              )}
            </button>

            {showCompetitors && (
              <div className="space-y-3 animate-in slide-in-from-top-2 duration-200">
                {/* Existing competitors list */}
                {competitors.length > 0 && (
                  <div className="space-y-2">
                    {competitors.map((comp, index) => (
                      <div
                        key={index}
                        className="group rounded-lg border border-gray-100 bg-gray-50/50 p-3 transition-all hover:border-gray-200"
                      >
                        {editingCompIndex === index ? (
                          <div className="space-y-2">
                            <input
                              type="text"
                              value={editCompName}
                              onChange={(e) => setEditCompName(e.target.value)}
                              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans"
                              placeholder="Competitor name"
                            />
                            <div className="relative">
                              <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                              <input
                                type="text"
                                value={editCompDomain}
                                onChange={(e) => setEditCompDomain(e.target.value)}
                                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans"
                                placeholder="Domain"
                              />
                            </div>
                            <textarea
                              value={editCompVariations}
                              onChange={(e) => setEditCompVariations(e.target.value)}
                              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans resize-none"
                              rows={2}
                              placeholder="Variations"
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={handleSaveCompetitor}
                                className="px-3 py-1.5 text-xs font-sans text-white rounded-md transition-colors"
                                style={{ backgroundColor: accentColor }}
                              >
                                Save
                              </button>
                              <button
                                onClick={handleCancelEditCompetitor}
                                className="px-3 py-1.5 text-xs font-sans text-gray-500 hover:text-gray-700 transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-gray-800 text-sm">{comp.name}</p>
                              {comp.domain && (
                                <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
                                  <Globe className="w-3 h-3" />
                                  {comp.domain}
                                </p>
                              )}
                              {comp.variations.length > 0 && (
                                <p className="text-xs text-gray-400 mt-1 font-sans truncate">
                                  {comp.variations.join(", ")}
                                </p>
                              )}
                            </div>
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={() => handleStartEditCompetitor(index)}
                                className="p-1.5 rounded hover:bg-white text-gray-400 hover:text-gray-600 transition-colors"
                              >
                                <Pencil className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleRemoveCompetitor(index)}
                                className="p-1.5 rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Add new competitor form */}
                <div
                  className="rounded-lg border-2 border-dashed p-4 transition-colors"
                  style={{ borderColor: `${accentColor}30` }}
                >
                  <p className="text-xs uppercase tracking-widest text-gray-400 font-sans mb-3">
                    Add competitor
                  </p>
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={newCompName}
                      onChange={(e) => setNewCompName(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans bg-white"
                      placeholder="Competitor name"
                      onKeyDown={(e) => e.key === "Enter" && handleAddCompetitor()}
                    />
                    <div className="relative">
                      <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        value={newCompDomain}
                        onChange={(e) => setNewCompDomain(e.target.value)}
                        className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans bg-white"
                        placeholder="Domain (optional)"
                      />
                    </div>
                    <textarea
                      value={newCompVariations}
                      onChange={(e) => setNewCompVariations(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans resize-none bg-white"
                      rows={2}
                      placeholder="Variations (optional, comma-separated)"
                    />
                    <button
                      onClick={handleAddCompetitor}
                      disabled={!newCompName.trim()}
                      className="w-full py-2.5 text-sm font-sans text-white rounded-md transition-all disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 flex items-center justify-center gap-2"
                      style={{ backgroundColor: accentColor }}
                    >
                      <Plus className="w-4 h-4" />
                      Add competitor
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer hint */}
          <p className="mt-6 text-xs text-gray-400 text-center font-sans italic">
            Brand and competitors will be detected in evaluation responses
          </p>
        </div>
      </div>
    </div>
  )
}
