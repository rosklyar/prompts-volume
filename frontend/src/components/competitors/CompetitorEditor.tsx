import { useState } from "react"
import { Globe, Plus, Trash2 } from "lucide-react"
import { normalizeDomain } from "@/lib/domain"
import { VariationsInput } from "@/components/onboarding/VariationsInput"
import { BrandLogo } from "@/components/BrandLogo"
import type { CompetitorInfo } from "@/types/groups"

const ACCENT_COLOR = "#C4553D"

interface CompetitorEditorProps {
  competitors: CompetitorInfo[]
  onCompetitorsChange: (competitors: CompetitorInfo[]) => void
  maxCompetitors?: number
  disabled?: boolean
}

export function CompetitorEditor({
  competitors,
  onCompetitorsChange,
  maxCompetitors = 10,
  disabled = false,
}: CompetitorEditorProps) {
  const [newCompName, setNewCompName] = useState("")
  const [newCompDomain, setNewCompDomain] = useState("")
  const [newCompVariations, setNewCompVariations] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  const handleAddCompetitor = () => {
    if (!newCompName.trim()) return
    if (competitors.length >= maxCompetitors) {
      setError(`Maximum ${maxCompetitors} competitors allowed`)
      return
    }
    onCompetitorsChange([
      ...competitors,
      {
        name: newCompName.trim(),
        domain: normalizeDomain(newCompDomain) || null,
        variations: newCompVariations,
      },
    ])
    setNewCompName("")
    setNewCompDomain("")
    setNewCompVariations([])
    setError(null)
  }

  const handleRemoveCompetitor = (index: number) => {
    onCompetitorsChange(competitors.filter((_, i) => i !== index))
  }

  return (
    <div>
      {error && <p className="text-sm text-red-600 mb-3">{error}</p>}

      {competitors.length > 0 && (
        <div className="space-y-2 mb-4">
          {competitors.map((comp, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100"
            >
              <div className="flex items-start gap-2.5 flex-1 min-w-0">
                <BrandLogo domain={comp.domain} name={comp.name} size={24} />
                <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-800 text-sm">{comp.name}</p>
                {comp.domain && (
                  <p className="text-xs text-gray-500 flex items-center gap-1">
                    <Globe className="w-3 h-3" />
                    {comp.domain}
                  </p>
                )}
                {comp.variations.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {comp.variations.map((v, i) => (
                      <span
                        key={i}
                        className="inline-flex px-2 py-0.5 bg-white text-gray-600 text-xs rounded border border-gray-200"
                      >
                        {v}
                      </span>
                    ))}
                  </div>
                )}
                </div>
              </div>
              <button
                onClick={() => handleRemoveCompetitor(index)}
                className="p-1.5 rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                disabled={disabled}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {competitors.length < maxCompetitors && (
        <div className="space-y-2 p-4 border-2 border-dashed border-gray-200 rounded-lg">
          <input
            type="text"
            value={newCompName}
            onChange={(e) => setNewCompName(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
            placeholder="Competitor name"
            onKeyDown={(e) => e.key === "Enter" && handleAddCompetitor()}
            disabled={disabled}
          />
          <div className="relative">
            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={newCompDomain}
              onChange={(e) => setNewCompDomain(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
              placeholder="Website (optional)"
              disabled={disabled}
            />
          </div>
          <VariationsInput
            variations={newCompVariations}
            onChange={setNewCompVariations}
            primaryValue={newCompName.trim() || undefined}
            placeholder="+ add variation"
          />
          <button
            onClick={handleAddCompetitor}
            disabled={!newCompName.trim() || disabled}
            className="w-full py-2 text-sm text-white rounded-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 flex items-center justify-center gap-2"
            style={{ backgroundColor: ACCENT_COLOR }}
          >
            <Plus className="w-4 h-4" />
            Add competitor
          </button>
        </div>
      )}
    </div>
  )
}
