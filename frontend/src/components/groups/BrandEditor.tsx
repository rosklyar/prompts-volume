/**
 * BrandEditor - Modal for configuring brands with variations
 * Editorial/magazine aesthetic with refined typography
 */

import { useState } from "react"
import type { BrandVariation } from "@/types/groups"

interface BrandEditorProps {
  brands: BrandVariation[]
  onBrandsChange: (brands: BrandVariation[]) => void
  accentColor: string
  onClose: () => void
}

export function BrandEditor({
  brands,
  onBrandsChange,
  accentColor,
  onClose,
}: BrandEditorProps) {
  const [newName, setNewName] = useState("")
  const [newVariations, setNewVariations] = useState("")
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editName, setEditName] = useState("")
  const [editVariations, setEditVariations] = useState("")

  const handleAdd = () => {
    if (!newName.trim()) return
    const variations = newVariations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)
    onBrandsChange([...brands, { name: newName.trim(), variations }])
    setNewName("")
    setNewVariations("")
  }

  const handleRemove = (index: number) => {
    onBrandsChange(brands.filter((_, i) => i !== index))
  }

  const handleStartEdit = (index: number) => {
    setEditingIndex(index)
    setEditName(brands[index].name)
    setEditVariations(brands[index].variations.join(", "))
  }

  const handleSaveEdit = () => {
    if (editingIndex === null || !editName.trim()) return
    const variations = editVariations
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)
    const updated = [...brands]
    updated[editingIndex] = { name: editName.trim(), variations }
    onBrandsChange(updated)
    setEditingIndex(null)
  }

  const handleCancelEdit = () => {
    setEditingIndex(null)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="relative w-full max-w-md mx-4 bg-white rounded-xl shadow-2xl overflow-hidden"
        style={{
          fontFamily: "'Georgia', 'Times New Roman', serif",
        }}
      >
        {/* Header accent bar */}
        <div
          className="h-1 w-full"
          style={{ backgroundColor: accentColor }}
        />

        <div className="p-6">
          {/* Title */}
          <div className="flex items-center justify-between mb-6">
            <h2
              className="text-xl tracking-tight"
              style={{ color: accentColor }}
            >
              Brand Configuration
            </h2>
            <button
              onClick={onClose}
              className="p-1.5 rounded-full hover:bg-gray-100 transition-colors text-gray-400 hover:text-gray-600"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Existing brands list */}
          {brands.length > 0 && (
            <div className="mb-6 space-y-3">
              <p className="text-xs uppercase tracking-widest text-gray-400 font-sans">
                Configured Brands
              </p>
              <div className="space-y-2">
                {brands.map((brand, index) => (
                  <div
                    key={index}
                    className="group rounded-lg border border-gray-100 bg-gray-50/50 p-3 transition-all hover:border-gray-200"
                  >
                    {editingIndex === index ? (
                      <div className="space-y-3">
                        <input
                          type="text"
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans"
                          style={{
                            focusRing: accentColor,
                            borderColor: accentColor
                          } as React.CSSProperties}
                          placeholder="Brand name"
                        />
                        <textarea
                          value={editVariations}
                          onChange={(e) => setEditVariations(e.target.value)}
                          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans resize-none"
                          rows={2}
                          placeholder="Variations (comma-separated)"
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={handleSaveEdit}
                            className="px-3 py-1.5 text-xs font-sans text-white rounded-md transition-colors"
                            style={{ backgroundColor: accentColor }}
                          >
                            Save
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="px-3 py-1.5 text-xs font-sans text-gray-500 hover:text-gray-700 transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-gray-800 text-sm">
                            {brand.name}
                          </p>
                          {brand.variations.length > 0 && (
                            <p className="text-xs text-gray-400 mt-1 font-sans truncate">
                              {brand.variations.join(", ")}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => handleStartEdit(index)}
                            className="p-1.5 rounded hover:bg-white text-gray-400 hover:text-gray-600 transition-colors"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleRemove(index)}
                            className="p-1.5 rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Add new brand form */}
          <div
            className="rounded-lg border-2 border-dashed p-4 transition-colors"
            style={{ borderColor: `${accentColor}30` }}
          >
            <p className="text-xs uppercase tracking-widest text-gray-400 font-sans mb-3">
              Add New Brand
            </p>
            <div className="space-y-3">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans bg-white"
                placeholder="Brand name (e.g., Rozetka)"
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              />
              <textarea
                value={newVariations}
                onChange={(e) => setNewVariations(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-1 font-sans resize-none bg-white"
                rows={2}
                placeholder="Variations, comma-separated (e.g., rozetka, Розетка, rozetka.com.ua)"
              />
              <button
                onClick={handleAdd}
                disabled={!newName.trim()}
                className="w-full py-2.5 text-sm font-sans text-white rounded-md transition-all disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90"
                style={{ backgroundColor: accentColor }}
              >
                Add Brand
              </button>
            </div>
          </div>

          {/* Footer hint */}
          <p className="mt-4 text-xs text-gray-400 text-center font-sans italic">
            Brands will be detected in evaluation responses
          </p>
        </div>
      </div>
    </div>
  )
}
