import { useState, useEffect, useCallback } from "react"
import { Sparkles, ChevronDown, ChevronUp, Check, Loader2 } from "lucide-react"
import { useGeneratePrompts, useCreateInspirationGroups } from "@/hooks/useKeywordInspiration"
import type { ScoredCluster, ClusterPrompts, CreateGroupsResponse } from "@/types/keyword-inspiration"
import type { CompetitorInfo } from "@/types/groups"

interface PromptReviewStepProps {
  selectedClusters: ScoredCluster[]
  businessDomain: string
  language: string
  countryId: number
  brand: { name: string; domain?: string | null; variations: string[] }
  competitors: CompetitorInfo[]
  onComplete: (result: CreateGroupsResponse) => void
  onBack: () => void
  onSkip: () => void
}

// Per-prompt checkbox reusing the GSCOnboardingStep pattern
function PromptItem({
  prompt,
  isSelected,
  onToggle,
}: {
  prompt: string
  isSelected: boolean
  onToggle: () => void
}) {
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
        <p className="text-sm font-medium text-gray-800 break-words">{prompt}</p>
      </div>
      {isSelected && <Check className="w-4 h-4 text-[#C4553D] mt-0.5 flex-shrink-0" />}
    </label>
  )
}

export function PromptReviewStep({
  selectedClusters,
  businessDomain,
  language,
  countryId,
  brand,
  competitors,
  onComplete,
  onBack,
  onSkip,
}: PromptReviewStepProps) {
  const generatePrompts = useGeneratePrompts()
  const createGroups = useCreateInspirationGroups()

  // Track selected prompts per cluster: { [cluster_id]: Set<prompt_text> }
  const [selectedPrompts, setSelectedPrompts] = useState<Record<number, Set<string>>>({})
  const [collapsedClusters, setCollapsedClusters] = useState<Set<number>>(new Set())

  // Auto-trigger generation on mount, initialize selections on success
  useEffect(() => {
    if (!generatePrompts.data && !generatePrompts.isPending && !generatePrompts.isError) {
      generatePrompts.mutate(
        {
          clusters: selectedClusters.map((c) => ({
            cluster_id: c.cluster_id,
            keywords: c.keywords,
            title: c.title,
          })),
          business_domain: businessDomain,
          language,
        },
        {
          onSuccess: (data) => {
            const initial: Record<number, Set<string>> = {}
            const collapsed = new Set<number>()
            data.clusters.forEach((cluster, i) => {
              initial[cluster.cluster_id] = new Set(cluster.prompts.map((p) => p.prompt_text))
              if (i >= 3) collapsed.add(cluster.cluster_id)
            })
            setSelectedPrompts(initial)
            setCollapsedClusters(collapsed)
          },
        }
      )
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const togglePrompt = useCallback((clusterId: number, promptText: string) => {
    setSelectedPrompts((prev) => {
      const clusterSet = new Set(prev[clusterId] || [])
      if (clusterSet.has(promptText)) clusterSet.delete(promptText)
      else clusterSet.add(promptText)
      return { ...prev, [clusterId]: clusterSet }
    })
  }, [])

  const selectAllForCluster = useCallback(
    (cluster: ClusterPrompts) => {
      setSelectedPrompts((prev) => ({
        ...prev,
        [cluster.cluster_id]: new Set(cluster.prompts.map((p) => p.prompt_text)),
      }))
    },
    []
  )

  const deselectAllForCluster = useCallback((clusterId: number) => {
    setSelectedPrompts((prev) => ({
      ...prev,
      [clusterId]: new Set<string>(),
    }))
  }, [])

  const toggleCollapse = useCallback((clusterId: number) => {
    setCollapsedClusters((prev) => {
      const next = new Set(prev)
      if (next.has(clusterId)) next.delete(clusterId)
      else next.add(clusterId)
      return next
    })
  }, [])

  // Count totals
  const totalSelectedPrompts = Object.values(selectedPrompts).reduce(
    (sum, set) => sum + set.size,
    0
  )
  const clustersWithPrompts = Object.entries(selectedPrompts).filter(
    ([, set]) => set.size > 0
  ).length

  const handleCreate = async () => {
    const clustersToCreate = (generatePrompts.data?.clusters || [])
      .map((cluster) => ({
        title: cluster.title,
        prompts: Array.from(selectedPrompts[cluster.cluster_id] || []),
      }))
      .filter((c) => c.prompts.length > 0)

    if (clustersToCreate.length === 0) return

    const result = await createGroups.mutateAsync({
      clusters: clustersToCreate,
      country_id: countryId,
      brand,
      competitors: competitors.length > 0 ? competitors : null,
    })
    onComplete(result)
  }

  // Generating state (also covers idle → pending race on first render)
  if (generatePrompts.isPending || (!generatePrompts.data && !generatePrompts.isError)) {
    return (
      <div className="text-center animate-in fade-in duration-300">
        <div className="w-16 h-16 rounded-full bg-[#C4553D]/10 flex items-center justify-center mx-auto mb-6">
          <Loader2 className="w-8 h-8 text-[#C4553D] animate-spin" />
        </div>
        <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-3">
          Generating Prompts...
        </h2>
        <p className="text-[#6B7280] mb-8 max-w-md mx-auto">
          Creating prompts for {selectedClusters.length} cluster
          {selectedClusters.length !== 1 ? "s" : ""}. This may take a moment.
        </p>
      </div>
    )
  }

  // Error state
  if (generatePrompts.isError) {
    return (
      <div className="text-center animate-in fade-in duration-300">
        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-6">
          <Sparkles className="w-8 h-8 text-red-400" />
        </div>
        <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-3">
          Generation Failed
        </h2>
        <p className="text-[#6B7280] mb-6 max-w-md mx-auto">
          {generatePrompts.error instanceof Error
            ? generatePrompts.error.message
            : "Something went wrong while generating prompts."}
        </p>
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={() =>
              generatePrompts.mutate(
                {
                  clusters: selectedClusters.map((c) => ({
                    cluster_id: c.cluster_id,
                    keywords: c.keywords,
                    title: c.title,
                  })),
                  business_domain: businessDomain,
                  language,
                },
                {
                  onSuccess: (data) => {
                    const initial: Record<number, Set<string>> = {}
                    const collapsed = new Set<number>()
                    data.clusters.forEach((cluster, i) => {
                      initial[cluster.cluster_id] = new Set(cluster.prompts.map((p) => p.prompt_text))
                      if (i >= 3) collapsed.add(cluster.cluster_id)
                    })
                    setSelectedPrompts(initial)
                    setCollapsedClusters(collapsed)
                  },
                }
              )
            }
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

  // Creating groups state
  if (createGroups.isPending) {
    return (
      <div className="text-center animate-in fade-in duration-300">
        <div className="w-16 h-16 rounded-full bg-[#C4553D]/10 flex items-center justify-center mx-auto mb-6">
          <Loader2 className="w-8 h-8 text-[#C4553D] animate-spin" />
        </div>
        <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-3">
          Creating Groups...
        </h2>
        <p className="text-[#6B7280] mb-8 max-w-md mx-auto">
          Setting up your monitoring groups with the selected prompts.
        </p>
      </div>
    )
  }

  // Create groups error
  if (createGroups.isError) {
    return (
      <div className="text-center animate-in fade-in duration-300">
        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-6">
          <Sparkles className="w-8 h-8 text-red-400" />
        </div>
        <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-3">
          Failed to Create Groups
        </h2>
        <p className="text-[#6B7280] mb-6">
          {createGroups.error instanceof Error
            ? createGroups.error.message
            : "Something went wrong."}
        </p>
        <div className="flex flex-col items-center gap-3">
          <button
            onClick={handleCreate}
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

  // Review state
  const clusterData = generatePrompts.data?.clusters || []

  return (
    <div className="animate-in fade-in duration-300">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-full bg-[#C4553D]/10 flex items-center justify-center">
          <Sparkles className="w-5 h-5 text-[#C4553D]" />
        </div>
        <div>
          <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
            Review Generated Prompts
          </h2>
          <p className="text-sm text-[#6B7280]">
            {generatePrompts.data!.total_prompts} prompts generated across {clusterData.length} clusters
          </p>
        </div>
      </div>

      {/* Cluster sections */}
      <div className="space-y-4 max-h-[450px] overflow-y-auto pr-1">
        {clusterData.map((cluster) => {
          const clusterSelected = selectedPrompts[cluster.cluster_id] || new Set()
          const allSelected = clusterSelected.size === cluster.prompts.length
          const isCollapsed = collapsedClusters.has(cluster.cluster_id)

          return (
            <div key={cluster.cluster_id} className="border border-gray-200 rounded-xl overflow-hidden">
              {/* Section header */}
              <div className="flex items-center justify-between px-4 py-3 bg-gray-50">
                <button
                  onClick={() => toggleCollapse(cluster.cluster_id)}
                  className="flex items-center gap-2 text-left min-w-0 flex-1"
                >
                  {isCollapsed ? (
                    <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  ) : (
                    <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  )}
                  <span className="text-sm font-medium text-gray-800 truncate">
                    {cluster.title}
                  </span>
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    ({clusterSelected.size}/{cluster.prompts.length})
                  </span>
                </button>
                <button
                  onClick={() =>
                    allSelected
                      ? deselectAllForCluster(cluster.cluster_id)
                      : selectAllForCluster(cluster)
                  }
                  className="text-xs text-[#C4553D] hover:text-[#B34835] font-medium flex-shrink-0 ml-2"
                >
                  {allSelected ? "Deselect all" : "Select all"}
                </button>
              </div>

              {/* Prompts */}
              {!isCollapsed && (
                <div className="p-3 space-y-2">
                  {cluster.prompts.map((item) => (
                    <PromptItem
                      key={item.prompt_text}
                      prompt={item.prompt_text}
                      isSelected={clusterSelected.has(item.prompt_text)}
                      onToggle={() => togglePrompt(cluster.cluster_id, item.prompt_text)}
                    />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-100">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="text-sm text-gray-600 hover:text-gray-800 font-medium transition-colors"
          >
            Back
          </button>
          <button
            onClick={onSkip}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            Skip
          </button>
        </div>
        <button
          onClick={handleCreate}
          disabled={totalSelectedPrompts === 0}
          className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white
            bg-[#C4553D] rounded-xl hover:bg-[#B34835] transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Create {clustersWithPrompts} group{clustersWithPrompts !== 1 ? "s" : ""} with{" "}
          {totalSelectedPrompts} prompt{totalSelectedPrompts !== 1 ? "s" : ""}
        </button>
      </div>
    </div>
  )
}
