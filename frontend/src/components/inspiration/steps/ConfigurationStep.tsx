/**
 * ConfigurationStep - Step 1: Enter company URL and country
 * Editorial design with warm accents and subtle animations
 */

import { useState } from "react"
import { useAnalyzeCompany } from "@/hooks/useInspiration"
import { CountrySelector } from "../CountrySelector"
import { Globe, Loader2, ArrowRight, Building2, Sparkles } from "lucide-react"
import type { WizardAction } from "../InspirationModal"
import type { WizardState, TopicWithPrompts } from "@/types/inspiration"

interface ConfigurationStepProps {
  state: WizardState
  dispatch: React.Dispatch<WizardAction>
}

export function ConfigurationStep({ state, dispatch }: ConfigurationStepProps) {
  const [localUrl, setLocalUrl] = useState(state.companyUrl)
  const [localCountry, setLocalCountry] = useState(state.isoCountryCode)
  const [urlError, setUrlError] = useState<string | null>(null)

  const analyzeCompany = useAnalyzeCompany()

  const validateUrl = (url: string): boolean => {
    if (!url.trim()) {
      setUrlError("Please enter a company URL")
      return false
    }
    // Simple validation - just needs to look like a domain
    const domainPattern = /^(https?:\/\/)?[\w.-]+\.[a-z]{2,}(\/.*)?$/i
    if (!domainPattern.test(url.trim())) {
      setUrlError("Please enter a valid URL (e.g., example.com)")
      return false
    }
    setUrlError(null)
    return true
  }

  const handleAnalyze = async () => {
    if (!validateUrl(localUrl) || !localCountry) return

    dispatch({ type: "SET_COMPANY_URL", url: localUrl.trim() })
    dispatch({ type: "SET_COUNTRY_CODE", code: localCountry })

    try {
      const metaInfo = await analyzeCompany.mutateAsync({
        companyUrl: localUrl.trim(),
        countryCode: localCountry,
      })

      dispatch({ type: "SET_META_INFO", metaInfo })

      // Initialize matched topics with loading state
      const matchedTopics: TopicWithPrompts[] = metaInfo.topics.matched_topics.map(
        (topic) => ({
          topicId: topic.id,
          topicTitle: topic.title,
          prompts: [],
          isExpanded: false,
          isLoading: false,
          addedToGroupId: null,
          addedToGroupTitle: null,
        })
      )
      dispatch({ type: "SET_MATCHED_TOPICS", topics: matchedTopics })

      // Move to next step
      dispatch({ type: "SET_STEP", step: "matched" })
    } catch (error) {
      dispatch({
        type: "SET_ERROR",
        error:
          error instanceof Error
            ? error.message
            : "Failed to analyze company. Please try again.",
      })
    }
  }

  const isValid = localUrl.trim() && localCountry

  return (
    <div className="max-w-2xl mx-auto">
      {/* Hero card */}
      <div className="bg-white rounded-2xl shadow-xl shadow-black/5 overflow-hidden border border-[#E5E7EB]/60">
        {/* Decorative header */}
        <div className="relative h-32 bg-gradient-to-br from-[#C4553D] via-[#B34835] to-[#9A3D2A] overflow-hidden">
          {/* Geometric pattern */}
          <div className="absolute inset-0 opacity-10">
            <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              <defs>
                <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
                  <path d="M 10 0 L 0 0 0 10" fill="none" stroke="white" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100" height="100" fill="url(#grid)" />
            </svg>
          </div>

          {/* Floating icons */}
          <div className="absolute top-4 right-4 w-16 h-16 rounded-full bg-white/10 flex items-center justify-center backdrop-blur-sm">
            <Sparkles className="w-8 h-8 text-white/80" />
          </div>
          <div className="absolute bottom-4 left-4 w-12 h-12 rounded-full bg-white/10 flex items-center justify-center backdrop-blur-sm">
            <Building2 className="w-6 h-6 text-white/80" />
          </div>

          {/* Title overlay */}
          <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/30 to-transparent">
            <h2 className="font-['Fraunces'] text-2xl font-semibold text-white">
              Let's find your prompts
            </h2>
            <p className="text-white/80 text-sm font-['DM_Sans'] mt-1">
              Enter your company details to discover SEO-relevant topics
            </p>
          </div>
        </div>

        {/* Form content */}
        <div className="p-8 space-y-6">
          {/* Company URL */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-[#374151] font-['DM_Sans']">
              Company URL
            </label>
            <div className="relative">
              <div className="absolute left-4 top-1/2 -translate-y-1/2 text-[#9CA3AF]">
                <Globe className="w-5 h-5" />
              </div>
              <input
                type="text"
                value={localUrl}
                onChange={(e) => {
                  setLocalUrl(e.target.value)
                  setUrlError(null)
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && isValid) {
                    handleAnalyze()
                  }
                }}
                placeholder="example.com or https://example.com"
                className={`
                  w-full pl-12 pr-4 py-3.5 text-base font-['DM_Sans']
                  bg-[#FAFAFA] border rounded-xl
                  focus:outline-none focus:ring-2 focus:bg-white
                  placeholder:text-[#9CA3AF] transition-all duration-200
                  ${
                    urlError
                      ? "border-red-300 focus:ring-red-200 focus:border-red-400"
                      : "border-[#E5E7EB] focus:ring-[#C4553D]/20 focus:border-[#C4553D]"
                  }
                `}
              />
            </div>
            {urlError && (
              <p className="text-sm text-red-500 font-['DM_Sans'] animate-in fade-in slide-in-from-top-1 duration-150">
                {urlError}
              </p>
            )}
          </div>

          {/* Country selector */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-[#374151] font-['DM_Sans']">
              Target Country
            </label>
            <CountrySelector
              value={localCountry}
              onChange={setLocalCountry}
            />
          </div>

          {/* Info note */}
          <div className="flex items-start gap-3 p-4 rounded-xl bg-[#FEF7F5] border border-[#C4553D]/10">
            <div className="w-8 h-8 rounded-full bg-[#C4553D]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Sparkles className="w-4 h-4 text-[#C4553D]" />
            </div>
            <div>
              <p className="text-sm font-medium text-[#1F2937] font-['DM_Sans']">
                How it works
              </p>
              <p className="text-sm text-[#6B7280] font-['DM_Sans'] mt-0.5">
                We'll analyze your domain to find relevant SEO topics and generate
                AI-powered prompts based on real search data from DataForSEO.
              </p>
            </div>
          </div>

          {/* Action button */}
          <button
            onClick={handleAnalyze}
            disabled={!isValid || analyzeCompany.isPending}
            className={`
              w-full py-4 px-6 rounded-xl font-['DM_Sans'] font-medium text-base
              flex items-center justify-center gap-3
              transition-all duration-200
              ${
                isValid && !analyzeCompany.isPending
                  ? "bg-[#C4553D] text-white hover:bg-[#B34835] shadow-lg shadow-[#C4553D]/25 hover:shadow-xl hover:shadow-[#C4553D]/30 hover:-translate-y-0.5"
                  : "bg-[#E5E7EB] text-[#9CA3AF] cursor-not-allowed"
              }
            `}
          >
            {analyzeCompany.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Analyzing company...</span>
              </>
            ) : (
              <>
                <span>Analyze & Find Topics</span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Decorative elements */}
      <div className="mt-8 flex justify-center gap-2">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="w-2 h-2 rounded-full bg-[#E5E7EB]"
            style={{
              animationDelay: `${i * 0.15}s`,
            }}
          />
        ))}
      </div>
    </div>
  )
}
