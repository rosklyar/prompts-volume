/**
 * BrandVariationsEditor - Editable list of brand variation chips
 * Allows adding, removing, and editing brand variations
 */

import { useState, useRef, useEffect } from "react"
import { X, Plus } from "lucide-react"

interface BrandVariationsEditorProps {
  variations: string[]
  onChange: (variations: string[]) => void
}

export function BrandVariationsEditor({
  variations,
  onChange,
}: BrandVariationsEditorProps) {
  const [isAdding, setIsAdding] = useState(false)
  const [newVariation, setNewVariation] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  // Focus input when adding
  useEffect(() => {
    if (isAdding && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isAdding])

  const handleAdd = () => {
    const trimmed = newVariation.trim()
    if (trimmed && !variations.includes(trimmed)) {
      onChange([...variations, trimmed])
    }
    setNewVariation("")
    setIsAdding(false)
  }

  const handleRemove = (index: number) => {
    const newVariations = [...variations]
    newVariations.splice(index, 1)
    onChange(newVariations)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleAdd()
    } else if (e.key === "Escape") {
      e.preventDefault()
      setIsAdding(false)
      setNewVariation("")
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {/* Existing variations */}
      {variations.map((variation, index) => (
        <div
          key={`${variation}-${index}`}
          className="group flex items-center gap-1.5 px-3 py-1.5 rounded-full
            bg-[#F3F4F6] text-[#4B5563] text-sm font-['DM_Sans']
            hover:bg-[#E5E7EB] transition-colors"
        >
          <span>{variation}</span>
          <button
            onClick={() => handleRemove(index)}
            className="w-4 h-4 rounded-full flex items-center justify-center
              text-[#9CA3AF] hover:text-[#EF4444] hover:bg-red-50
              transition-all opacity-0 group-hover:opacity-100"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      ))}

      {/* Add new variation */}
      {isAdding ? (
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={newVariation}
            onChange={(e) => setNewVariation(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => {
              if (!newVariation.trim()) {
                setIsAdding(false)
              }
            }}
            placeholder="Enter variation..."
            className="px-3 py-1.5 text-sm font-['DM_Sans']
              border border-[#C4553D] rounded-full
              focus:outline-none focus:ring-2 focus:ring-[#C4553D]/20
              placeholder:text-[#9CA3AF]"
            maxLength={50}
          />
          <button
            onClick={handleAdd}
            disabled={!newVariation.trim()}
            className="px-3 py-1.5 text-sm font-medium text-white
              bg-[#C4553D] rounded-full hover:bg-[#B34835]
              transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Add
          </button>
          <button
            onClick={() => {
              setIsAdding(false)
              setNewVariation("")
            }}
            className="px-3 py-1.5 text-sm text-[#6B7280] hover:text-[#1F2937]
              transition-colors"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => setIsAdding(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full
            border-2 border-dashed border-[#D1D5DB] text-[#6B7280]
            text-sm font-['DM_Sans'] hover:border-[#C4553D] hover:text-[#C4553D]
            transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Add variation</span>
        </button>
      )}

      {/* Empty state */}
      {variations.length === 0 && !isAdding && (
        <p className="text-sm text-[#9CA3AF] font-['DM_Sans'] italic">
          No brand variations defined
        </p>
      )}
    </div>
  )
}
