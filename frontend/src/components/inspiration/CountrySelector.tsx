/**
 * CountrySelector - Searchable dropdown for selecting ISO country codes
 * Editorial design with flag icons and keyboard navigation
 */

import { useState, useRef, useEffect } from "react"
import { ChevronDown, Check, Search } from "lucide-react"
import { COUNTRY_OPTIONS, type CountryOption } from "@/types/inspiration"

interface CountrySelectorProps {
  value: string
  onChange: (code: string) => void
}

export function CountrySelector({ value, onChange }: CountrySelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [highlightedIndex, setHighlightedIndex] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const selectedOption = COUNTRY_OPTIONS.find((o) => o.code === value)

  const filteredOptions = COUNTRY_OPTIONS.filter(
    (option) =>
      option.name.toLowerCase().includes(search.toLowerCase()) ||
      option.code.toLowerCase().includes(search.toLowerCase())
  )


  // Focus input when opening
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  // Click outside handler
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
        setSearch("")
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  // Scroll highlighted item into view
  useEffect(() => {
    if (isOpen && listRef.current) {
      const items = listRef.current.querySelectorAll("[data-country-item]")
      const item = items[highlightedIndex] as HTMLElement
      if (item) {
        item.scrollIntoView({ block: "nearest" })
      }
    }
  }, [highlightedIndex, isOpen])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
        e.preventDefault()
        setIsOpen(true)
      }
      return
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault()
        setHighlightedIndex((prev) =>
          prev < filteredOptions.length - 1 ? prev + 1 : 0
        )
        break
      case "ArrowUp":
        e.preventDefault()
        setHighlightedIndex((prev) =>
          prev > 0 ? prev - 1 : filteredOptions.length - 1
        )
        break
      case "Enter":
        e.preventDefault()
        if (filteredOptions[highlightedIndex]) {
          onChange(filteredOptions[highlightedIndex].code)
          setIsOpen(false)
          setSearch("")
        }
        break
      case "Escape":
        e.preventDefault()
        setIsOpen(false)
        setSearch("")
        break
    }
  }

  const handleSelect = (option: CountryOption) => {
    onChange(option.code)
    setIsOpen(false)
    setSearch("")
  }

  return (
    <div ref={containerRef} className="relative">
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        className={`
          w-full px-4 py-3.5 text-left font-['DM_Sans'] text-base
          bg-[#FAFAFA] border border-[#E5E7EB] rounded-xl
          flex items-center justify-between gap-3
          focus:outline-none focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D] focus:bg-white
          transition-all duration-200
          ${isOpen ? "ring-2 ring-[#C4553D]/20 border-[#C4553D] bg-white" : ""}
        `}
      >
        {selectedOption ? (
          <span className="flex items-center gap-3">
            <span className="text-xl">{selectedOption.flag}</span>
            <span className="text-[#1F2937]">{selectedOption.name}</span>
            <span className="text-[#9CA3AF] text-sm">({selectedOption.code})</span>
          </span>
        ) : (
          <span className="text-[#9CA3AF]">Select a country...</span>
        )}
        <ChevronDown
          className={`w-5 h-5 text-[#9CA3AF] transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 mt-2 w-full bg-white rounded-xl border border-[#E5E7EB] shadow-xl shadow-black/10 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          {/* Search input */}
          <div className="p-3 border-b border-[#E5E7EB]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
              <input
                ref={inputRef}
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setHighlightedIndex(0)
                }}
                onKeyDown={handleKeyDown}
                placeholder="Search countries..."
                className="w-full pl-10 pr-4 py-2.5 text-sm font-['DM_Sans']
                  bg-[#FAFAFA] border border-[#E5E7EB] rounded-lg
                  focus:outline-none focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D] focus:bg-white
                  placeholder:text-[#9CA3AF] transition-all duration-200"
              />
            </div>
          </div>

          {/* Options list */}
          <div ref={listRef} className="max-h-64 overflow-y-auto py-2">
            {filteredOptions.length === 0 ? (
              <div className="px-4 py-8 text-center text-[#9CA3AF] text-sm font-['DM_Sans']">
                No countries found
              </div>
            ) : (
              filteredOptions.map((option, index) => {
                const isSelected = option.code === value
                const isHighlighted = index === highlightedIndex

                return (
                  <button
                    key={option.code}
                    data-country-item
                    type="button"
                    onClick={() => handleSelect(option)}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    className={`
                      w-full px-4 py-3 flex items-center gap-3 text-left
                      transition-colors duration-100
                      ${
                        isHighlighted
                          ? "bg-[#FEF7F5]"
                          : isSelected
                          ? "bg-[#FAFAFA]"
                          : "hover:bg-[#FAFAFA]"
                      }
                    `}
                  >
                    <span className="text-xl flex-shrink-0">{option.flag}</span>
                    <span className="flex-1 min-w-0">
                      <span
                        className={`font-['DM_Sans'] text-sm ${
                          isSelected ? "text-[#C4553D] font-medium" : "text-[#1F2937]"
                        }`}
                      >
                        {option.name}
                      </span>
                      <span className="text-[#9CA3AF] text-xs ml-2">
                        {option.code}
                      </span>
                    </span>
                    {isSelected && (
                      <Check className="w-4 h-4 text-[#C4553D] flex-shrink-0" />
                    )}
                  </button>
                )
              })
            )}
          </div>

          {/* Keyboard hint */}
          <div className="px-4 py-2 border-t border-[#E5E7EB] bg-[#FAFAFA]">
            <span className="text-xs text-[#9CA3AF] font-['DM_Sans']">
              <kbd className="px-1.5 py-0.5 bg-white border border-[#E5E7EB] rounded text-[10px] font-mono">
                ↑↓
              </kbd>{" "}
              navigate{" "}
              <kbd className="px-1.5 py-0.5 bg-white border border-[#E5E7EB] rounded text-[10px] font-mono">
                ⏎
              </kbd>{" "}
              select
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
