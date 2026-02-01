/**
 * GSCOnboardingStep - Google Search Console integration step
 *
 * Two-step flow:
 * 1. Select keywords from GSC (no word filter, all keywords shown)
 * 2. Generate and select prompts from selected keywords, then create group
 */

import { useState, useMemo, useCallback } from "react"
import {
  Search,
  ChevronDown,
  Check,
  AlertCircle,
  Loader2,
  ExternalLink,
  ArrowLeft,
} from "lucide-react"
import {
  useGSCStatus,
  useGSCConnect,
  useGSCMatchProperty,
  useGSCFetchKeywords,
  useGSCGeneratePrompts,
  useGSCCreatePrompts,
} from "@/hooks/useGSC"
import { KeywordSelector } from "@/components/groups/shared/KeywordSelector"
import type { GSCSortBy } from "@/client/api"

type GSCSubState =
  | "connect"
  | "matching"
  | "select-site"
  | "loading-keywords"
  | "select-keywords"
  | "generating-prompts"
  | "select-prompts"
  | "creating"
  | "no-data"

interface GSCOnboardingStepProps {
  brandDomain: string | null
  countryId: number
  businessDomain?: string
  brand: { name: string; domain?: string | null; variations: string[] }
  competitors: { name: string; domain?: string | null; variations: string[] }[]
  onComplete: (result: { groupId: number; promptCount: number } | null) => void
  onSkip: () => void
  onBeforeConnect?: () => void  // Save state before OAuth redirect
}

export function GSCOnboardingStep({
  brandDomain,
  countryId,
  businessDomain,
  brand,
  competitors,
  onComplete,
  onSkip,
  onBeforeConnect,
}: GSCOnboardingStepProps) {
  // User-driven state
  const [userSelectedSite, setUserSelectedSite] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<GSCSortBy>("clicks")
  const [selectedKeywords, setSelectedKeywords] = useState<Set<string>>(new Set())
  const [generatedPrompts, setGeneratedPrompts] = useState<string[]>([])
  const [isInPromptsStep, setIsInPromptsStep] = useState(false)
  const [manualPromptSelection, setManualPromptSelection] = useState<Set<string> | null>(null)
  const [groupName, setGroupName] = useState("GSC Keywords")
  const [error, setError] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  // Hooks
  const { data: gscStatus, isLoading: isLoadingStatus } = useGSCStatus()
  const connectMutation = useGSCConnect(`${window.location.origin}/onboarding`)
  const generatePromptsMutation = useGSCGeneratePrompts()
  const createPromptsMutation = useGSCCreatePrompts()

  // Determine if GSC is connected
  const isConnected = gscStatus?.is_connected ?? false

  // Start matching when connected
  const shouldMatch = isConnected && !isLoadingStatus

  // Match property query - enabled when connected
  const { data: matchResult, isLoading: isMatching } = useGSCMatchProperty(
    brandDomain,
    shouldMatch && !userSelectedSite
  )

  // Determine selected site URL (auto-matched or user-selected)
  const selectedSiteUrl = useMemo(() => {
    if (userSelectedSite) return userSelectedSite
    if (matchResult?.match_type === "exact" || matchResult?.match_type === "partial") {
      return matchResult.matched_property
    }
    return null
  }, [userSelectedSite, matchResult])

  // Fetch keywords query - enabled when we have a site and not in prompts step
  const { data: keywordsResult, isLoading: isLoadingKeywords } = useGSCFetchKeywords(
    selectedSiteUrl,
    sortBy,
    100,
    selectedSiteUrl !== null && !isInPromptsStep
  )

  // Get keywords from the result
  const keywords = useMemo(
    () => keywordsResult?.keywords ?? [],
    [keywordsResult?.keywords]
  )

  // Derive selected prompts - default to all selected, unless user has manually changed
  const selectedPrompts = useMemo(() => {
    if (manualPromptSelection !== null) return manualPromptSelection
    if (generatedPrompts.length > 0) {
      return new Set(generatedPrompts)
    }
    return new Set<string>()
  }, [manualPromptSelection, generatedPrompts])

  // Derive the current sub-state from data
  const subState: GSCSubState = useMemo(() => {
    if (isCreating) return "creating"
    if (isLoadingStatus) return "connect"
    if (!isConnected) return "connect"
    if (isMatching) return "matching"
    if (!matchResult) return "matching"

    // If user selected a site or auto-matched
    if (selectedSiteUrl) {
      if (isLoadingKeywords) return "loading-keywords"
      if (keywordsResult) {
        if (keywords.length === 0) return "no-data"

        // Check if we're in the prompts step
        if (isInPromptsStep) {
          if (generatePromptsMutation.isPending) return "generating-prompts"
          return "select-prompts"
        }

        return "select-keywords"
      }
      return "loading-keywords"
    }

    // No site selected - check match result
    if (matchResult.available_properties.length === 0) return "no-data"
    return "select-site"
  }, [
    isCreating,
    isLoadingStatus,
    isConnected,
    isMatching,
    matchResult,
    selectedSiteUrl,
    isLoadingKeywords,
    keywordsResult,
    keywords,
    isInPromptsStep,
    generatePromptsMutation.isPending,
  ])

  // Handlers
  const handleConnect = useCallback(() => {
    onBeforeConnect?.()
    connectMutation.mutate()
  }, [connectMutation, onBeforeConnect])

  const handleSelectSite = useCallback((siteUrl: string) => {
    setUserSelectedSite(siteUrl)
    setSelectedKeywords(new Set())
    setGeneratedPrompts([])
    setIsInPromptsStep(false)
    setManualPromptSelection(null)
  }, [])

  const handleToggleKeyword = useCallback((query: string) => {
    setSelectedKeywords((prev) => {
      const next = new Set(prev)
      if (next.has(query)) {
        next.delete(query)
      } else {
        next.add(query)
      }
      return next
    })
  }, [])

  const handleSortChange = useCallback((newSortBy: GSCSortBy) => {
    setSortBy(newSortBy)
  }, [])

  const handleGeneratePrompts = useCallback(() => {
    if (selectedKeywords.size === 0) return

    generatePromptsMutation.mutate(
      {
        keywords: Array.from(selectedKeywords),
        countryId,
        businessDomain,
      },
      {
        onSuccess: (data) => {
          setGeneratedPrompts(data.prompts)
          setIsInPromptsStep(true)
          setManualPromptSelection(null) // Auto-select all
        },
      }
    )
  }, [selectedKeywords, countryId, businessDomain, generatePromptsMutation])

  const handleBackToKeywords = useCallback(() => {
    setIsInPromptsStep(false)
  }, [])

  const handleTogglePrompt = useCallback((prompt: string) => {
    setManualPromptSelection((prev) => {
      const current = prev ?? selectedPrompts
      const next = new Set(current)
      if (next.has(prompt)) {
        next.delete(prompt)
      } else {
        next.add(prompt)
      }
      return next
    })
  }, [selectedPrompts])

  const handleToggleAll = useCallback(() => {
    if (generatedPrompts.length === 0) return
    if (selectedPrompts.size === generatedPrompts.length) {
      setManualPromptSelection(new Set())
    } else {
      setManualPromptSelection(new Set(generatedPrompts))
    }
  }, [generatedPrompts, selectedPrompts])

  const handleCreateGroup = useCallback(async () => {
    if (selectedPrompts.size === 0 || !groupName.trim()) return

    setIsCreating(true)
    setError(null)

    try {
      const result = await createPromptsMutation.mutateAsync({
        prompts: Array.from(selectedPrompts),
        groupTitle: groupName.trim(),
        countryId,
        brand,
        competitors: competitors.length > 0 ? competitors : null,
      })
      onComplete({
        groupId: result.group_id,
        promptCount: result.prompts_created,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create group")
      setIsCreating(false)
    }
  }, [selectedPrompts, groupName, createPromptsMutation, onComplete, countryId, brand, competitors])

  // Loading state
  if (isLoadingStatus) {
    return (
      <div className="text-center py-8">
        <Loader2 className="w-8 h-8 animate-spin text-[#C4553D] mx-auto mb-4" />
        <p className="text-gray-500">Checking GSC connection...</p>
      </div>
    )
  }

  return (
    <div className="animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
          <Search className="w-5 h-5 text-[#C4553D]" />
        </div>
        <div>
          <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
            Import from Search Console
          </h2>
          <p className="text-sm text-[#6B7280]">
            {subState === "connect" && "Connect to import your top keywords"}
            {subState === "matching" && "Finding your website..."}
            {subState === "select-site" && "Select your website property"}
            {subState === "loading-keywords" && "Fetching keywords..."}
            {subState === "select-keywords" && "Select keywords to generate prompts"}
            {subState === "generating-prompts" && "Generating prompts..."}
            {subState === "select-prompts" && "Select prompts to track"}
            {subState === "creating" && "Creating your group..."}
            {subState === "no-data" && "No keywords found"}
          </p>
        </div>
      </div>

      {/* Connect State */}
      {subState === "connect" && (
        <div className="text-center py-6">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
            <Search className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-600 mb-2">
            Connect Google Search Console to import
            <br />
            keywords from your website's search data.
          </p>
          <p className="text-xs text-gray-400 mb-6">
            Make sure your GSC account has access to your brand's website
          </p>
          <button
            onClick={handleConnect}
            disabled={connectMutation.isPending}
            className="inline-flex items-center gap-2 px-6 py-3 bg-[#C4553D] text-white font-medium rounded-xl
              hover:bg-[#B34835] transition-colors shadow-lg shadow-[#C4553D]/20
              disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {connectMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Connecting...
              </>
            ) : (
              <>
                <ExternalLink className="w-4 h-4" />
                Connect Google Search Console
              </>
            )}
          </button>
        </div>
      )}

      {/* Matching State */}
      {subState === "matching" && (
        <div className="text-center py-8">
          <Loader2 className="w-8 h-8 animate-spin text-[#C4553D] mx-auto mb-4" />
          <p className="text-gray-600">Matching your website...</p>
        </div>
      )}

      {/* Select Site State */}
      {subState === "select-site" && matchResult && (
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            {matchResult.match_type === "none"
              ? "We couldn't auto-detect your website. Please select it:"
              : "Multiple properties found. Please select one:"}
          </p>
          <div className="space-y-2">
            {matchResult.available_properties.map((site) => (
              <button
                key={site.site_url}
                onClick={() => handleSelectSite(site.site_url)}
                className="w-full flex items-center justify-between px-4 py-3 bg-gray-50
                  border border-gray-200 rounded-xl hover:border-[#C4553D] hover:bg-[#C4553D]/5
                  transition-colors text-left"
              >
                <div>
                  <p className="font-medium text-gray-800">{site.site_url}</p>
                  <p className="text-xs text-gray-400 capitalize">
                    {site.permission_level.replace("site", "")}
                  </p>
                </div>
                <ChevronDown className="w-4 h-4 text-gray-400 -rotate-90" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Loading Keywords State */}
      {subState === "loading-keywords" && (
        <div className="text-center py-8">
          <Loader2 className="w-8 h-8 animate-spin text-[#C4553D] mx-auto mb-4" />
          <p className="text-gray-600">Fetching keywords...</p>
        </div>
      )}

      {/* Select Keywords State (Step 1) */}
      {subState === "select-keywords" && keywords.length > 0 && (
        <KeywordSelector
          keywords={keywords}
          selectedKeywords={selectedKeywords}
          onToggleKeyword={handleToggleKeyword}
          sortBy={sortBy}
          onSortChange={handleSortChange}
          onGeneratePrompts={handleGeneratePrompts}
          isGenerating={generatePromptsMutation.isPending}
          accentColor="#C4553D"
          maxHeight="280px"
        />
      )}

      {/* Generating Prompts State */}
      {subState === "generating-prompts" && (
        <div className="text-center py-8">
          <Loader2 className="w-8 h-8 animate-spin text-[#C4553D] mx-auto mb-4" />
          <p className="text-gray-600">Generating prompts from keywords...</p>
          <p className="text-xs text-gray-400 mt-1">
            Creating 3 prompts per keyword
          </p>
        </div>
      )}

      {/* Select Prompts State (Step 2) */}
      {subState === "select-prompts" && generatedPrompts.length > 0 && (
        <div className="space-y-4">
          {/* Back button and Select All */}
          <div className="flex items-center justify-between">
            <button
              onClick={handleBackToKeywords}
              className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to keywords
            </button>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedPrompts.size === generatedPrompts.length}
                onChange={handleToggleAll}
                className="w-4 h-4 rounded border-gray-300 text-[#C4553D] focus:ring-[#C4553D]/30"
              />
              <span className="text-sm font-medium text-gray-700">
                Select All
              </span>
            </label>
          </div>

          {/* Prompts List */}
          <div className="max-h-64 overflow-y-auto space-y-2 border border-gray-200 rounded-xl p-2">
            {generatedPrompts.map((prompt) => (
              <PromptItem
                key={prompt}
                prompt={prompt}
                isSelected={selectedPrompts.has(prompt)}
                onToggle={() => handleTogglePrompt(prompt)}
              />
            ))}
          </div>

          {/* Selection count */}
          <p className="text-sm text-gray-500">
            {selectedPrompts.size} prompt{selectedPrompts.size !== 1 ? "s" : ""} selected
          </p>

          {/* Group Name Input */}
          <div>
            <label className="block text-xs uppercase tracking-widest text-gray-400 mb-2">
              Group name
            </label>
            <input
              type="text"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              placeholder="Enter group name"
              className="w-full px-4 py-3 text-base bg-white border-2 border-gray-200 rounded-xl
                focus:outline-none focus:ring-2 focus:ring-[#C4553D]/30 focus:border-[#C4553D]"
            />
          </div>

          {/* Error display */}
          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}
        </div>
      )}

      {/* Creating State */}
      {subState === "creating" && (
        <div className="text-center py-8">
          <Loader2 className="w-8 h-8 animate-spin text-[#C4553D] mx-auto mb-4" />
          <p className="text-gray-600">Creating your group...</p>
        </div>
      )}

      {/* No Data State */}
      {subState === "no-data" && (
        <div className="text-center py-6">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
            <Search className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-600 mb-2">
            No keywords found
          </p>
          <p className="text-xs text-gray-400 mb-6">
            We couldn't find any keywords in the last 28 days.
            <br />
            You can skip this step and add keywords manually later.
          </p>
        </div>
      )}

      {/* Action Buttons */}
      {(subState === "select-prompts" || subState === "select-keywords" || subState === "no-data" || subState === "connect" || subState === "select-site") && (
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-100">
          <button
            onClick={onSkip}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Skip this step
          </button>
          {subState === "select-prompts" && (
            <button
              onClick={handleCreateGroup}
              disabled={selectedPrompts.size === 0 || !groupName.trim()}
              className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white
                bg-[#C4553D] rounded-xl hover:bg-[#B34835] transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Create Group
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// Prompt item component (without source keyword)
interface PromptItemProps {
  prompt: string
  isSelected: boolean
  onToggle: () => void
}

function PromptItem({ prompt, isSelected, onToggle }: PromptItemProps) {
  return (
    <label
      className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors
        ${isSelected ? "bg-[#C4553D]/5 border border-[#C4553D]/20" : "bg-gray-50 border border-transparent hover:bg-gray-100"}`}
    >
      <input
        type="checkbox"
        checked={isSelected}
        onChange={onToggle}
        className="mt-0.5 w-4 h-4 rounded border-gray-300 text-[#C4553D] focus:ring-[#C4553D]/30"
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 break-words">
          {prompt}
        </p>
      </div>
      {isSelected && <Check className="w-4 h-4 text-[#C4553D] mt-0.5 flex-shrink-0" />}
    </label>
  )
}
