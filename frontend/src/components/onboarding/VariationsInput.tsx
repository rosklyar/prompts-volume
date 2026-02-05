/**
 * VariationsInput - Chip-based input for brand name variations
 * Supports adding/removing variations with a clean tag-based UI
 */

import { useState, useCallback, type KeyboardEvent, type ChangeEvent } from "react"
import { X } from "lucide-react"

interface VariationsInputProps {
  variations: string[]
  onChange: (variations: string[]) => void
  placeholder?: string
  /** If provided, this value is always shown as the first (non-removable) variation */
  primaryValue?: string
}

export function VariationsInput({
  variations,
  onChange,
  placeholder = "+ add variation",
  primaryValue,
}: VariationsInputProps) {
  const [newVariation, setNewVariation] = useState("")

  const handleRemoveVariation = useCallback(
    (index: number) => {
      onChange(variations.filter((_, i) => i !== index))
    },
    [variations, onChange]
  )

  const handleAddVariation = useCallback(() => {
    const trimmed = newVariation.trim().toLowerCase()
    if (trimmed && !variations.includes(trimmed)) {
      // Also check against primaryValue
      if (primaryValue && trimmed === primaryValue.toLowerCase()) {
        setNewVariation("")
        return
      }
      onChange([...variations, trimmed])
      setNewVariation("")
    }
  }, [newVariation, variations, onChange, primaryValue])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault()
        handleAddVariation()
      }
    },
    [handleAddVariation]
  )

  const handleChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setNewVariation(e.target.value)
  }, [])

  return (
    <div className="flex flex-wrap gap-1.5 p-3 bg-gray-50 rounded-xl border-2 border-gray-200 min-h-[52px] focus-within:border-[#C4553D] focus-within:ring-2 focus-within:ring-[#C4553D]/30 transition-all">
      {/* Primary value (brand name) - always first, not removable */}
      {primaryValue && (
        <span
          className="inline-flex items-center gap-1 px-2.5 py-1
                     bg-[#C4553D]/10 text-[#C4553D] text-sm font-medium rounded-lg border border-[#C4553D]/20"
        >
          {primaryValue}
        </span>
      )}

      {/* Editable variations */}
      {variations.map((v, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-1 px-2.5 py-1
                     bg-white text-gray-700 text-sm rounded-lg border border-gray-200
                     group hover:border-gray-300 transition-colors"
        >
          {v}
          <button
            type="button"
            onClick={() => handleRemoveVariation(i)}
            className="text-gray-400 hover:text-red-500 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </span>
      ))}

      {/* Add new variation input */}
      <input
        type="text"
        value={newVariation}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onBlur={handleAddVariation}
        placeholder={placeholder}
        className="px-2 py-1 text-sm bg-transparent border-none min-w-[120px] flex-1
                   focus:outline-none placeholder:text-gray-400"
      />
    </div>
  )
}
