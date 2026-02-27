import { useState, useEffect, useCallback } from "react"
import { Search, ChevronDown, ChevronUp, ArrowLeft, Check } from "lucide-react"
import { useDiscoverClusters } from "@/hooks/useKeywordInspiration"
import type { ScoredCluster } from "@/types/keyword-inspiration"

interface ClusterDiscoveryStepProps {
  domains: string[]
  countryCode: string
  languageName: string
  brandNames: string[]
  onClustersSelected: (clusters: ScoredCluster[]) => void
  onSkip: () => void
  onGoBackToBrand: () => void
}

export function ClusterDiscoveryStep({
  domains,
  countryCode,
  languageName,
  brandNames,
  onClustersSelected,
  onSkip,
  onGoBackToBrand,
}: ClusterDiscoveryStepProps) {
  const discoverClusters = useDiscoverClusters()
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())

  const hasDomains = domains.length > 0

  // Auto-trigger discovery on mount (only when domains exist)
  useEffect(() => {
    if (hasDomains && !discoverClusters.data && !discoverClusters.isPending && !discoverClusters.isError) {
      discoverClusters.mutate(
        {
          domains,
          country_code: countryCode,
          language_name: languageName,
          brand_names: brandNames,
        },
        {
          onSuccess: (data) => {
            if (data.clusters.length === 0) {
              onSkip()
              return
            }
            // Select all clusters by default
            setSelectedIds(new Set(data.clusters.map((c) => c.cluster_id)))
          },
        }
      )
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleCluster = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const toggleExpand = useCallback((id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const handleRetry = useCallback(() => {
    discoverClusters.mutate(
      {
        domains,
        country_code: countryCode,
        language_name: languageName,
        brand_names: brandNames,
      },
      {
        onSuccess: (data) => {
          setSelectedIds(new Set(data.clusters.map((c) => c.cluster_id)))
        },
      }
    )
  }, [discoverClusters, domains, countryCode, languageName, brandNames])

  const handleContinue = () => {
    if (!discoverClusters.data) return
    const selected = discoverClusters.data.clusters.filter((c) => selectedIds.has(c.cluster_id))
    onClustersSelected(selected)
  }

  // No domain — show prompt
  if (!hasDomains) {
    return (
      <div className="text-center animate-in fade-in duration-300">
        <div className="w-16 h-16 rounded-full bg-[#C4553D]/10 flex items-center justify-center mx-auto mb-6">
          <Search className="w-8 h-8 text-[#C4553D]" />
        </div>
        <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-3">
          Keyword Discovery Needs a Website
        </h2>
        <p className="text-[#6B7280] mb-6 max-w-md mx-auto">
          To discover keyword clusters from your competitors, we need at least one website domain.
          Go back to add your brand's website, or skip this step.
        </p>
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={onGoBackToBrand}
            className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white
              bg-[#C4553D] rounded-xl hover:bg-[#B34835] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Go Back to Add Website
          </button>
          <button
            onClick={onSkip}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Skip this step
          </button>
        </div>
      </div>
    )
  }

  // Discovering state
  if (discoverClusters.isPending) {
    return (
      <div className="text-center animate-in fade-in duration-300">
        <div className="w-16 h-16 rounded-full bg-[#C4553D]/10 flex items-center justify-center mx-auto mb-6 relative">
          <Search className="w-8 h-8 text-[#C4553D]" />
          <div className="absolute inset-0 rounded-full border-2 border-[#C4553D]/30 animate-ping" />
          <div className="absolute inset-[-4px] rounded-full border border-[#C4553D]/15 animate-ping [animation-delay:0.5s]" />
        </div>
        <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-3">
          Analyzing Competitor Keywords...
        </h2>
        <p className="text-[#6B7280] mb-8 max-w-md mx-auto">
          We're scanning your competitors' websites to find relevant keyword clusters.
          This may take a moment.
        </p>
        <div className="space-y-3 max-w-sm mx-auto">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-12 bg-gray-100 rounded-xl animate-pulse"
              style={{ animationDelay: `${i * 200}ms` }}
            />
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (discoverClusters.isError) {
    return (
      <div className="text-center animate-in fade-in duration-300">
        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-6">
          <Search className="w-8 h-8 text-red-400" />
        </div>
        <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-3">
          Discovery Failed
        </h2>
        <p className="text-[#6B7280] mb-6 max-w-md mx-auto">
          {discoverClusters.error instanceof Error
            ? discoverClusters.error.message
            : "Something went wrong while discovering keywords."}
        </p>
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={handleRetry}
            className="px-6 py-2.5 text-sm font-medium text-white bg-[#C4553D] rounded-xl
              hover:bg-[#B34835] transition-colors"
          >
            Try Again
          </button>
          <button
            onClick={onSkip}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Skip this step
          </button>
        </div>
      </div>
    )
  }

  // No results
  const clusters = discoverClusters.data?.clusters || []
  if (clusters.length === 0) {
    return (
      <div className="text-center animate-in fade-in duration-300">
        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-6">
          <Search className="w-8 h-8 text-gray-400" />
        </div>
        <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-3">
          No Clusters Found
        </h2>
        <p className="text-[#6B7280] mb-6 max-w-md mx-auto">
          We couldn't find meaningful keyword clusters from the provided domains.
          You can continue with other setup steps.
        </p>
        <button
          onClick={onSkip}
          className="px-6 py-2.5 text-sm font-medium text-white bg-[#C4553D] rounded-xl
            hover:bg-[#B34835] transition-colors"
        >
          Continue
        </button>
      </div>
    )
  }

  // Cluster selection
  const maxScore = Math.max(...clusters.map((c) => c.score), 1)

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
          <Search className="w-5 h-5 text-[#C4553D]" />
        </div>
        <div>
          <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
            Keyword Clusters Discovered
          </h2>
          <p className="text-sm text-[#6B7280]">
            {discoverClusters.data!.total_keywords} keywords grouped into {clusters.length} clusters
          </p>
        </div>
      </div>

      {/* Cluster list */}
      <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
        {clusters.map((cluster, i) => (
          <div
            key={cluster.cluster_id}
            className="animate-in fade-in duration-300"
            style={{ animationDelay: `${i * 50}ms` }}
          >
            <div
              className={`border rounded-xl transition-colors ${
                selectedIds.has(cluster.cluster_id)
                  ? "border-[#C4553D]/30 bg-[#C4553D]/5"
                  : "border-gray-200 bg-white"
              }`}
            >
              {/* Header */}
              <div className="flex items-center gap-3 p-3">
                <input
                  type="checkbox"
                  checked={selectedIds.has(cluster.cluster_id)}
                  onChange={() => toggleCluster(cluster.cluster_id)}
                  className="w-4 h-4 rounded border-gray-300 text-[#C4553D] focus:ring-[#C4553D]/30"
                />
                <button
                  onClick={() => toggleExpand(cluster.cluster_id)}
                  className="flex-1 flex items-center gap-2 text-left min-w-0"
                >
                  <span className="text-sm font-medium text-gray-800 truncate">
                    {cluster.title}
                  </span>
                  <span className="flex-shrink-0 text-xs font-medium text-[#C4553D] bg-[#C4553D]/10 px-2 py-0.5 rounded-full">
                    {cluster.keyword_count} keywords
                  </span>
                  {expandedIds.has(cluster.cluster_id) ? (
                    <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  )}
                </button>
                {selectedIds.has(cluster.cluster_id) && (
                  <Check className="w-4 h-4 text-[#C4553D] flex-shrink-0" />
                )}
              </div>

              {/* Score bar */}
              <div className="px-3 pb-2">
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#C4553D]/60 rounded-full transition-all"
                    style={{ width: `${(cluster.score / maxScore) * 100}%` }}
                  />
                </div>
              </div>

              {/* Expanded keywords */}
              {expandedIds.has(cluster.cluster_id) && (
                <div className="px-3 pb-3 border-t border-gray-100 pt-2">
                  <div className="flex flex-wrap gap-1.5">
                    {cluster.keywords.slice(0, 5).map((kw) => (
                      <span
                        key={kw}
                        className="text-xs text-gray-600 bg-gray-50 px-2 py-1 rounded-md"
                      >
                        {kw}
                      </span>
                    ))}
                    {cluster.keywords.length > 5 && (
                      <span className="text-xs text-gray-400 px-2 py-1">
                        +{cluster.keywords.length - 5} more
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-100">
        <button
          onClick={onSkip}
          className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          Skip
        </button>
        <button
          onClick={handleContinue}
          disabled={selectedIds.size === 0}
          className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white
            bg-[#C4553D] rounded-xl hover:bg-[#B34835] transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Continue with {selectedIds.size} cluster{selectedIds.size !== 1 ? "s" : ""}
        </button>
      </div>
    </div>
  )
}
