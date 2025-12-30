/**
 * AddGroupCard - Full-width card for creating a new group with brands
 * Requires at least one brand for meaningful reports
 */

import { useState, useRef, useEffect } from "react"
import type { BrandVariation } from "@/types/groups"
import { MAX_GROUPS } from "./constants"

interface AddGroupCardProps {
  onAdd: (title: string, brands: BrandVariation[]) => void
  isLoading: boolean
}

export function AddGroupCard({ onAdd, isLoading }: AddGroupCardProps) {
  const [isCreating, setIsCreating] = useState(false)
  const [title, setTitle] = useState("")
  const [brands, setBrands] = useState<BrandVariation[]>([])
  const [newBrandName, setNewBrandName] = useState("")
  const [newBrandVariations, setNewBrandVariations] = useState("")
  const titleInputRef = useRef<HTMLInputElement>(null)
  const brandInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isCreating && titleInputRef.current) {
      titleInputRef.current.focus()
    }
  }, [isCreating])

  const handleAddBrand = () => {
    if (!newBrandName.trim()) return
    const variations = newBrandVariations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)
    setBrands([...brands, { name: newBrandName.trim(), variations }])
    setNewBrandName("")
    setNewBrandVariations("")
    // Focus back to brand name input for adding more
    brandInputRef.current?.focus()
  }

  const handleRemoveBrand = (index: number) => {
    setBrands(brands.filter((_, i) => i !== index))
  }

  const handleSubmit = () => {
    const trimmedTitle = title.trim()
    if (trimmedTitle && brands.length > 0) {
      onAdd(trimmedTitle, brands)
      setTitle("")
      setBrands([])
      setNewBrandName("")
      setNewBrandVariations("")
      setIsCreating(false)
    }
  }

  const handleCancel = () => {
    setTitle("")
    setBrands([])
    setNewBrandName("")
    setNewBrandVariations("")
    setIsCreating(false)
  }

  const handleTitleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      handleCancel()
    }
  }

  const handleBrandKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleAddBrand()
    } else if (e.key === "Escape") {
      handleCancel()
    }
  }

  const canCreate = title.trim() && brands.length > 0

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
              onKeyDown={handleTitleKeyDown}
              placeholder="Enter group name..."
              disabled={isLoading}
              className="w-full px-4 py-2.5 font-['Fraunces'] text-lg
                bg-white border border-gray-200 rounded-lg
                focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                placeholder:text-gray-400 disabled:opacity-50"
              maxLength={50}
            />
          </div>

          {/* Brands section */}
          <div>
            <label className="block text-xs uppercase tracking-widest text-gray-400 font-sans mb-2">
              Brands to Track <span className="text-[#C4553D]">*</span>
            </label>

            {/* Added brands */}
            {brands.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {brands.map((brand, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 px-3 py-1.5 bg-white border border-gray-200 rounded-lg group"
                  >
                    <span className="text-sm font-medium text-gray-700">{brand.name}</span>
                    {brand.variations.length > 0 && (
                      <span className="text-xs text-gray-400">
                        +{brand.variations.length}
                      </span>
                    )}
                    <button
                      onClick={() => handleRemoveBrand(index)}
                      className="p-0.5 rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Add brand form */}
            <div className="flex gap-2">
              <div className="flex-1 space-y-2">
                <input
                  ref={brandInputRef}
                  type="text"
                  value={newBrandName}
                  onChange={(e) => setNewBrandName(e.target.value)}
                  onKeyDown={handleBrandKeyDown}
                  placeholder="Brand name (e.g., Nike)"
                  disabled={isLoading}
                  className="w-full px-3 py-2 text-sm
                    bg-white border border-gray-200 rounded-lg
                    focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                    placeholder:text-gray-400 disabled:opacity-50"
                />
                <input
                  type="text"
                  value={newBrandVariations}
                  onChange={(e) => setNewBrandVariations(e.target.value)}
                  onKeyDown={handleBrandKeyDown}
                  placeholder="Variations, comma-separated (optional)"
                  disabled={isLoading}
                  className="w-full px-3 py-2 text-sm
                    bg-white border border-gray-200 rounded-lg
                    focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]
                    placeholder:text-gray-400 disabled:opacity-50"
                />
              </div>
              <button
                onClick={handleAddBrand}
                disabled={!newBrandName.trim() || isLoading}
                className="self-start px-4 py-2 text-sm font-medium
                  bg-white border border-gray-200 rounded-lg
                  hover:bg-gray-50 hover:border-[#C4553D]/50 transition-colors
                  disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add
              </button>
            </div>

            {brands.length === 0 && (
              <p className="mt-2 text-xs text-gray-400 italic">
                Add at least one brand to track in reports
              </p>
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
        <svg
          className="w-5 h-5 text-gray-400 transition-colors group-hover:text-[#C4553D]"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
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
