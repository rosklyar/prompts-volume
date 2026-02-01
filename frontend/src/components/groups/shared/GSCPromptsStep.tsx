/**
 * GSCPromptsStep - GSC integration step for prompts selection
 *
 * Reusable component for both group creation wizard and existing group modal.
 * Key difference from GSCOnboardingStep: doesn't create group, just returns selected prompts.
 */

import { useState, useMemo, useCallback } from "react"
import { useNavigate } from "@tanstack/react-router"
import {
  Search,
  ChevronDown,
  Loader2,
  ExternalLink,
  RefreshCw,
} from "lucide-react"
import {
  useGSCStatus,
  useGSCConnect,
  useGSCMatchProperty,
  useGSCExtractKeywords,
} from "@/hooks/useGSC"
import { PromptSelector } from "./PromptSelector"
import type { GeneratedPromptResponse } from "@/client/api"

type GSCSubState =
  | "connect"
  | "matching"
  | "select-site"
  | "loading-keywords"
  | "select-prompts"
  | "no-data"

interface GSCPromptsStepProps {
  brandDomain: string | null
  countryId: number
  businessDomain?: string
  selectedPrompts: Set<string>
  onTogglePrompt: (prompt: string) => void
  accentColor?: string
  redirectUri?: string
}

export function GSCPromptsStep({
  brandDomain,
  countryId,
  businessDomain,
  selectedPrompts,
  onTogglePrompt,
  accentColor = "#C4553D",
  redirectUri,
}: GSCPromptsStepProps) {
  const [userSelectedSite, setUserSelectedSite] = useState<string | null>(null)
  const navigate = useNavigate()

  // Hooks
  const { data: gscStatus, isLoading: isLoadingStatus } = useGSCStatus()
  const connectMutation = useGSCConnect(redirectUri)

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

  // Extract keywords query - enabled when we have a site
  const { data: keywordsResult, isLoading: isLoadingKeywords } = useGSCExtractKeywords(
    selectedSiteUrl,
    {
      minWordCount: 3,
      resultLimit: 10,
      generatePrompts: true,
      countryId,
      businessDomain,
    },
    selectedSiteUrl !== null
  )

  // Get generated prompts from the result
  const generatedPrompts = useMemo(
    () => keywordsResult?.generated_prompts ?? [],
    [keywordsResult?.generated_prompts]
  )

  // Derive the current sub-state from data
  const subState: GSCSubState = useMemo(() => {
    if (isLoadingStatus) return "connect"
    if (!isConnected) return "connect"
    if (isMatching) return "matching"
    if (!matchResult) return "matching"

    // If user selected a site or auto-matched
    if (selectedSiteUrl) {
      if (isLoadingKeywords) return "loading-keywords"
      if (keywordsResult) {
        if (generatedPrompts.length === 0 && keywordsResult.keywords.length === 0) return "no-data"
        return "select-prompts"
      }
      return "loading-keywords"
    }

    // No site selected - check match result
    if (matchResult.available_properties.length === 0) return "no-data"
    return "select-site"
  }, [
    isLoadingStatus,
    isConnected,
    isMatching,
    matchResult,
    selectedSiteUrl,
    isLoadingKeywords,
    keywordsResult,
    generatedPrompts,
  ])

  // Handlers
  const handleConnect = useCallback(() => {
    connectMutation.mutate()
  }, [connectMutation])

  const handleSwitchAccount = useCallback(() => {
    // Redirect to settings GSC tab - user will start fresh after connecting different account
    navigate({ to: "/settings", search: { tab: "gsc" } })
  }, [navigate])

  const handleSelectSite = useCallback((siteUrl: string) => {
    setUserSelectedSite(siteUrl)
  }, [])

  // Handle select all for GSC prompts
  const handleSelectAllGSC = useCallback(() => {
    if (generatedPrompts.length === 0) return

    const allPromptTexts = generatedPrompts.map((p) => p.prompt)
    const allSelected = allPromptTexts.every((text) => selectedPrompts.has(text))

    if (allSelected) {
      // Deselect all
      allPromptTexts.forEach((text) => {
        if (selectedPrompts.has(text)) {
          onTogglePrompt(text)
        }
      })
    } else {
      // Select all
      allPromptTexts.forEach((text) => {
        if (!selectedPrompts.has(text)) {
          onTogglePrompt(text)
        }
      })
    }
  }, [generatedPrompts, selectedPrompts, onTogglePrompt])

  // Convert generated prompts to PromptSelector format
  const promptsForSelector = useMemo(
    () =>
      generatedPrompts.map((p: GeneratedPromptResponse) => ({
        id: p.prompt,
        text: p.prompt,
        subtitle: `From: "${p.source_keyword}"`,
      })),
    [generatedPrompts]
  )

  // Loading state
  if (isLoadingStatus) {
    return (
      <div className="text-center py-8">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" style={{ color: accentColor }} />
        <p className="text-gray-500">Checking GSC connection...</p>
      </div>
    )
  }

  return (
    <div className="animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center"
          style={{ backgroundColor: `${accentColor}10` }}
        >
          <Search className="w-5 h-5" style={{ color: accentColor }} />
        </div>
        <div>
          <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
            Import from Search Console
          </h2>
          <p className="text-sm text-[#6B7280]">
            {subState === "connect" && "Connect to import your top keywords"}
            {subState === "matching" && "Finding your website..."}
            {subState === "select-site" && "Select your website property"}
            {subState === "loading-keywords" && "Generating prompts from keywords..."}
            {subState === "select-prompts" && "Select prompts to add"}
            {subState === "no-data" && "No matching keywords found"}
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
          {!brandDomain && (
            <p className="text-xs text-amber-600 mb-4">
              Add a brand domain in the previous step for best results
            </p>
          )}
          <p className="text-xs text-gray-400 mb-6">
            Make sure your GSC account has access to your brand's website
          </p>
          <button
            onClick={handleConnect}
            disabled={connectMutation.isPending}
            className="inline-flex items-center gap-2 px-6 py-3 text-white font-medium rounded-xl
              transition-colors shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: accentColor,
              boxShadow: `0 10px 25px -5px ${accentColor}33`,
            }}
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
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" style={{ color: accentColor }} />
          <p className="text-gray-600">Matching your website...</p>
        </div>
      )}

      {/* Select Site State */}
      {subState === "select-site" && matchResult && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600">
              {matchResult.match_type === "none"
                ? "We couldn't auto-detect your website. Please select it:"
                : "Multiple properties found. Please select one:"}
            </p>
            <button
              onClick={handleSwitchAccount}
              className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
            >
              <RefreshCw className="w-3 h-3" />
              Use different account
            </button>
          </div>
          <div className="space-y-2">
            {matchResult.available_properties.map((site) => (
              <button
                key={site.site_url}
                onClick={() => handleSelectSite(site.site_url)}
                className="w-full flex items-center justify-between px-4 py-3 bg-gray-50
                  border border-gray-200 rounded-xl hover:border-gray-400 transition-colors text-left"
                style={{
                  ["--hover-border" as string]: accentColor,
                }}
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
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" style={{ color: accentColor }} />
          <p className="text-gray-600">Generating prompts from keywords...</p>
          <p className="text-xs text-gray-400 mt-1">
            Looking for long-tail keywords (3+ words)
          </p>
        </div>
      )}

      {/* Select Prompts State */}
      {subState === "select-prompts" && generatedPrompts.length > 0 && (
        <div className="space-y-4">
          {/* Switch account option */}
          <div className="flex justify-end">
            <button
              onClick={handleSwitchAccount}
              className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
            >
              <RefreshCw className="w-3 h-3" />
              Use different account
            </button>
          </div>

          <PromptSelector
            prompts={promptsForSelector}
            selectedIds={selectedPrompts}
            onToggle={onTogglePrompt}
            onSelectAll={handleSelectAllGSC}
            accentColor={accentColor}
            maxHeight="240px"
          />
        </div>
      )}

      {/* No Data State */}
      {subState === "no-data" && (
        <div className="text-center py-6">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
            <Search className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-600 mb-2">
            No long-tail keywords found
          </p>
          <p className="text-xs text-gray-400 mb-4">
            We couldn't find keywords with 3+ words in the last 28 days.
          </p>
          <button
            onClick={handleSwitchAccount}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 mx-auto"
          >
            <RefreshCw className="w-3 h-3" />
            Try different account
          </button>
        </div>
      )}
    </div>
  )
}

