import { useState } from "react"
import { Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useUserPreferences, useUpdatePreferences } from "@/hooks/useOnboarding"
import { CompetitorEditor } from "./CompetitorEditor"
import type { CompetitorInfo } from "@/types/groups"

const ACCENT_COLOR = "#C4553D"

export function CompetitorsView() {
  const { data: preferences, isLoading } = useUserPreferences()

  if (isLoading) {
    return (
      <div className="text-center py-8 text-gray-500">Loading...</div>
    )
  }

  return (
    <CompetitorsViewInner
      initialCompetitors={preferences?.default_competitors ?? []}
      preferences={preferences}
    />
  )
}

interface CompetitorsViewInnerProps {
  initialCompetitors: CompetitorInfo[]
  preferences: {
    default_country_id: number | null
    default_business_domain_id: number | null
    default_brand: import("@/types/groups").BrandInfo | null
  } | undefined
}

function CompetitorsViewInner({ initialCompetitors, preferences }: CompetitorsViewInnerProps) {
  const updatePreferences = useUpdatePreferences()

  const [competitors, setCompetitors] = useState<CompetitorInfo[]>(initialCompetitors)
  const [hasChanges, setHasChanges] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCompetitorsChange = (updated: CompetitorInfo[]) => {
    setCompetitors(updated)
    setHasChanges(true)
  }

  const handleSave = () => {
    if (!preferences) return

    setError(null)
    setSuccess(false)

    updatePreferences.mutate(
      {
        default_country_id: preferences.default_country_id!,
        default_business_domain_id: preferences.default_business_domain_id ?? undefined,
        default_brand: preferences.default_brand!,
        default_competitors: competitors.length > 0 ? competitors : undefined,
      },
      {
        onSuccess: () => {
          setHasChanges(false)
          setSuccess(true)
          setTimeout(() => setSuccess(false), 3000)
        },
        onError: (err) => {
          setError(err.message || "Failed to save competitors")
        },
      }
    )
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="font-['Fraunces'] text-3xl text-[#1F2937] text-center mb-2">
        Competitors
      </h1>
      <p className="text-sm text-gray-500 text-center mb-8">
        Manage your default competitors list. These will be pre-filled when creating new prompt groups.
      </p>

      {competitors.length === 0 && !hasChanges && (
        <div className="text-center py-12 text-gray-400 border-2 border-dashed border-gray-200 rounded-lg mb-6">
          <p className="text-lg mb-1">No competitors yet</p>
          <p className="text-sm">Add competitors below to track how they appear in AI responses</p>
        </div>
      )}

      <CompetitorEditor
        competitors={competitors}
        onCompetitorsChange={handleCompetitorsChange}
        disabled={updatePreferences.isPending}
      />

      {error && <p className="text-sm text-red-600 mt-4">{error}</p>}

      {success && (
        <div className="flex items-center gap-2 text-sm text-green-600 mt-4">
          <Check className="w-4 h-4" />
          Competitors saved successfully
        </div>
      )}

      {hasChanges && (
        <Button
          onClick={handleSave}
          disabled={updatePreferences.isPending}
          className="w-full mt-6"
          style={{ backgroundColor: ACCENT_COLOR }}
        >
          {updatePreferences.isPending ? "Saving..." : "Save Competitors"}
        </Button>
      )}
    </div>
  )
}
