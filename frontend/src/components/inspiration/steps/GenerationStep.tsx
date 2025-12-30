/**
 * GenerationStep - Step 3: Select unmatched topics and generate prompts
 * Three sub-states: selection, progress, success
 */

import { useState } from "react"
import { useGeneratePrompts, useBatchSimilarPrompts } from "@/hooks/useInspiration"
import { ApiError } from "@/client/api"
import { BrandVariationsEditor } from "../BrandVariationsEditor"
import { GenerationConfirmModal } from "../GenerationConfirmModal"
import {
  ArrowLeft,
  Sparkles,
  Loader2,
  Check,
  Zap,
  Clock,
  AlertCircle,
} from "lucide-react"
import type { WizardAction } from "../InspirationModal"
import type { WizardState, GeneratedTopicReview, GeneratedPromptReview } from "@/types/inspiration"

interface GenerationStepProps {
  state: WizardState
  dispatch: React.Dispatch<WizardAction>
  onClose: () => void
}

// Auto-selection threshold for similar prompts
const AUTO_SELECT_THRESHOLD = 0.98

export function GenerationStep({ state, dispatch, onClose }: GenerationStepProps) {
  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressMessage, setProgressMessage] = useState("")
  const [showConfirmModal, setShowConfirmModal] = useState(false)

  const generatePrompts = useGeneratePrompts()
  const batchSimilarPrompts = useBatchSimilarPrompts()

  const unmatchedTopics = state.metaInfo?.topics.unmatched_topics ?? []
  const selectedCount = state.selectedUnmatchedTopics.size

  // Handle topic toggle
  const handleToggleTopic = (topicTitle: string) => {
    dispatch({ type: "TOGGLE_UNMATCHED_TOPIC", topicTitle })
  }

  // Handle select all
  const handleSelectAll = () => {
    unmatchedTopics.forEach((topic) => {
      if (!state.selectedUnmatchedTopics.has(topic.title)) {
        dispatch({ type: "TOGGLE_UNMATCHED_TOPIC", topicTitle: topic.title })
      }
    })
  }

  // Handle deselect all
  const handleDeselectAll = () => {
    state.selectedUnmatchedTopics.forEach((title) => {
      dispatch({ type: "TOGGLE_UNMATCHED_TOPIC", topicTitle: title })
    })
  }

  // Show confirmation modal before generating
  const handleGenerateClick = () => {
    if (selectedCount === 0) return
    setShowConfirmModal(true)
  }

  // Handle confirmed generation
  const handleConfirmGenerate = async () => {
    setShowConfirmModal(false)
    setIsGenerating(true)
    setProgress(10)
    setProgressMessage("Fetching keywords from DataForSEO...")

    try {
      // Generate prompts
      setProgress(30)
      setProgressMessage("Analyzing keyword clusters...")

      const selectedTopics = Array.from(state.selectedUnmatchedTopics)
      const response = await generatePrompts.mutateAsync({
        company_url: state.companyUrl,
        iso_country_code: state.isoCountryCode,
        topics: selectedTopics,
        brand_variations: state.brandVariations,
      })

      setProgress(70)
      setProgressMessage("Finding similar prompts in database...")

      // Collect all generated prompts for similarity matching
      const allPromptTexts: string[] = []
      const promptToTopicMap: Map<string, { topic: string; index: number }> = new Map()

      response.topics.forEach((topic) => {
        topic.clusters.forEach((cluster) => {
          cluster.prompts.forEach((promptText, idx) => {
            allPromptTexts.push(promptText)
            promptToTopicMap.set(promptText, { topic: topic.topic, index: idx })
          })
        })
      })

      // Batch fetch similar prompts
      const similarResults = await batchSimilarPrompts.mutateAsync(allPromptTexts)

      setProgress(90)
      setProgressMessage("Preparing review...")

      // Build generated topics for review
      const generatedTopics: GeneratedTopicReview[] = response.topics.map((topic) => {
        const prompts: GeneratedPromptReview[] = []

        topic.clusters.forEach((cluster) => {
          cluster.prompts.forEach((promptText) => {
            const similarResult = similarResults.find(
              (r) => r.query_text === promptText
            )
            const matches =
              similarResult?.prompts.map((p) => ({
                promptId: p.id,
                promptText: p.prompt_text,
                similarity: p.similarity,
              })) ?? []

            // Auto-select if high similarity match exists
            const bestMatch = matches[0]
            const autoSelectMatch =
              bestMatch && bestMatch.similarity >= AUTO_SELECT_THRESHOLD

            prompts.push({
              inputText: promptText,
              keywords: cluster.keywords,
              matches,
              selectedOption: autoSelectMatch ? "use-match" : "keep-original",
              selectedMatchId: autoSelectMatch ? bestMatch.promptId : null,
            })
          })
        })

        return {
          topicTitle: topic.topic,
          prompts,
          isExpanded: true,
          addedToGroupId: null,
          addedToGroupTitle: null,
        }
      })

      dispatch({ type: "SET_GENERATED_TOPICS", topics: generatedTopics })
      setProgress(100)
      setProgressMessage("Complete!")

      // Move to review step
      setTimeout(() => {
        dispatch({ type: "SET_STEP", step: "review" })
        setIsGenerating(false)
      }, 500)
    } catch (error) {
      setIsGenerating(false)

      // Handle insufficient balance (402) - show confirm modal again
      if (error instanceof ApiError && error.status === 402) {
        setShowConfirmModal(true)
        return
      }

      dispatch({
        type: "SET_ERROR",
        error:
          error instanceof Error
            ? error.message
            : "Failed to generate prompts. Please try again.",
      })
    }
  }

  // Go back
  const handleBack = () => {
    dispatch({ type: "SET_STEP", step: "matched" })
  }

  // Skip generation - close modal and return to dashboard
  const handleSkip = () => {
    onClose()
  }

  // Generating state
  if (isGenerating) {
    return (
      <div className="max-w-xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl shadow-black/5 border border-[#E5E7EB]/60 p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#C4553D] to-[#B34835] flex items-center justify-center mx-auto mb-4 relative">
              <Sparkles className="w-10 h-10 text-white" />
              <div className="absolute inset-0 rounded-full border-4 border-[#C4553D]/30 animate-ping" />
            </div>
            <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-2">
              Generating prompts
            </h2>
            <p className="text-[#6B7280] font-['DM_Sans'] text-sm">
              This may take 30-60 seconds
            </p>
          </div>

          {/* Progress bar */}
          <div className="mb-6">
            <div className="h-3 bg-[#E5E7EB] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[#C4553D] to-[#B34835] transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex items-center justify-between mt-2">
              <span className="text-sm text-[#6B7280] font-['DM_Sans']">
                {progressMessage}
              </span>
              <span className="text-sm font-medium text-[#C4553D] font-['DM_Sans']">
                {progress}%
              </span>
            </div>
          </div>

          {/* Topics being processed */}
          <div className="space-y-2">
            {Array.from(state.selectedUnmatchedTopics).map((topic, index) => (
              <div
                key={topic}
                className="flex items-center gap-3 px-4 py-3 rounded-xl bg-[#FAFAFA]"
              >
                {progress > 30 + (index * 40) / selectedCount ? (
                  <Check className="w-4 h-4 text-[#10B981]" />
                ) : (
                  <Loader2 className="w-4 h-4 text-[#C4553D] animate-spin" />
                )}
                <span className="text-sm text-[#6B7280] font-['DM_Sans'] truncate">
                  {topic}
                </span>
              </div>
            ))}
          </div>

          {/* Time estimate */}
          <div className="flex items-center justify-center gap-2 mt-6 text-sm text-[#9CA3AF] font-['DM_Sans']">
            <Clock className="w-4 h-4" />
            <span>Please wait, we're analyzing real search data...</span>
          </div>
        </div>
      </div>
    )
  }

  // No unmatched topics
  if (unmatchedTopics.length === 0) {
    return (
      <div className="max-w-xl mx-auto">
        <div className="bg-white rounded-2xl shadow-lg shadow-black/5 border border-[#E5E7EB]/60 p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-[#FEF7F5] flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-[#C4553D]" />
          </div>
          <h3 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-2">
            No topics to generate
          </h3>
          <p className="text-[#6B7280] font-['DM_Sans'] mb-6">
            All topics for your domain are already in our database.
            You can use the matched topics from the previous step.
          </p>
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={handleBack}
              className="px-5 py-2.5 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] font-['DM_Sans'] transition-colors flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>
            <button
              onClick={handleSkip}
              className="px-5 py-2.5 text-sm font-medium text-white bg-[#C4553D] hover:bg-[#B34835] rounded-lg font-['DM_Sans'] transition-colors flex items-center gap-2"
            >
              <span>Complete</span>
              <Check className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Selection state
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header card */}
      <div className="bg-white rounded-2xl shadow-lg shadow-black/5 border border-[#E5E7EB]/60 overflow-hidden">
        <div className="px-6 py-5 border-b border-[#E5E7EB]/60 bg-gradient-to-br from-[#FAFAFA] to-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#C4553D] to-[#B34835] flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-['Fraunces'] text-lg font-semibold text-[#1F2937]">
                Generate new prompts
              </h2>
              <p className="text-sm text-[#6B7280] font-['DM_Sans']">
                Select topics to generate AI-powered prompts from DataForSEO data
              </p>
            </div>
          </div>
        </div>

        {/* Topics selection */}
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-[#374151] font-['DM_Sans']">
              Available topics ({unmatchedTopics.length})
            </span>
            <button
              onClick={selectedCount === unmatchedTopics.length ? handleDeselectAll : handleSelectAll}
              className="text-sm text-[#C4553D] hover:text-[#B34835] font-['DM_Sans'] transition-colors"
            >
              {selectedCount === unmatchedTopics.length ? "Deselect all" : "Select all"}
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {unmatchedTopics.map((topic) => {
              const isSelected = state.selectedUnmatchedTopics.has(topic.title)
              return (
                <label
                  key={topic.title}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-xl border-2 cursor-pointer
                    transition-all duration-200
                    ${
                      isSelected
                        ? "border-[#C4553D] bg-[#FEF7F5]"
                        : "border-[#E5E7EB] hover:border-[#C4553D]/50 hover:bg-[#FAFAFA]"
                    }
                  `}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleToggleTopic(topic.title)}
                    className="sr-only"
                  />
                  <div
                    className={`
                      w-5 h-5 rounded border-2 flex items-center justify-center
                      transition-all duration-150
                      ${
                        isSelected
                          ? "border-[#C4553D] bg-[#C4553D]"
                          : "border-[#D1D5DB] bg-white"
                      }
                    `}
                  >
                    {isSelected && <Check className="w-3 h-3 text-white" strokeWidth={3} />}
                  </div>
                  <span
                    className={`text-sm font-['DM_Sans'] truncate ${
                      isSelected ? "text-[#1F2937] font-medium" : "text-[#6B7280]"
                    }`}
                  >
                    {topic.title}
                  </span>
                </label>
              )
            })}
          </div>
        </div>
      </div>

      {/* Brand variations editor */}
      <div className="bg-white rounded-2xl shadow-lg shadow-black/5 border border-[#E5E7EB]/60 overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E5E7EB]/60">
          <h3 className="font-['Fraunces'] text-base font-semibold text-[#1F2937]">
            Brand variations
          </h3>
          <p className="text-sm text-[#6B7280] font-['DM_Sans'] mt-0.5">
            These keywords will be filtered from the generated prompts
          </p>
        </div>
        <div className="p-6">
          <BrandVariationsEditor
            variations={state.brandVariations}
            onChange={(variations) =>
              dispatch({ type: "SET_BRAND_VARIATIONS", variations })
            }
          />
        </div>
      </div>

      {/* Info note */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 border border-amber-100">
        <Clock className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-amber-800 font-['DM_Sans']">
            Generation takes 30-60 seconds
          </p>
          <p className="text-sm text-amber-700 font-['DM_Sans'] mt-0.5">
            We'll fetch keywords from DataForSEO, cluster them, and generate
            relevant prompts using AI.
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={handleBack}
          className="px-5 py-3 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] font-['DM_Sans'] transition-colors flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSkip}
            className="px-5 py-3 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] font-['DM_Sans'] transition-colors"
          >
            Skip
          </button>
          <button
            onClick={handleGenerateClick}
            disabled={selectedCount === 0}
            className={`
              px-6 py-3 text-sm font-medium text-white rounded-xl font-['DM_Sans']
              flex items-center gap-2 transition-all duration-200
              ${
                selectedCount > 0
                  ? "bg-[#C4553D] hover:bg-[#B34835] shadow-lg shadow-[#C4553D]/25 hover:shadow-xl hover:shadow-[#C4553D]/30 hover:-translate-y-0.5"
                  : "bg-[#E5E7EB] cursor-not-allowed"
              }
            `}
          >
            <Sparkles className="w-4 h-4" />
            <span>Generate {selectedCount > 0 ? `${selectedCount} Topics` : "Prompts"}</span>
          </button>
        </div>
      </div>

      {/* Confirmation Modal */}
      <GenerationConfirmModal
        isOpen={showConfirmModal}
        topicsCount={selectedCount}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={handleConfirmGenerate}
        onNeedsTopUp={onClose}
      />
    </div>
  )
}
