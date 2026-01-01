/**
 * GroupInspirationModal - Inspiration modal for a specific group
 * Flow: Country → Select Matched → Generate (optional) → Review → Confirm
 */

import { useCallback, useReducer, useEffect, useState, useMemo } from "react"
import { Link } from "@tanstack/react-router"
import {
  X,
  Sparkles,
  Loader2,
  ArrowRight,
  ArrowLeft,
  Check,
  Package,
  Globe,
  Plus,
  AlertCircle,
} from "lucide-react"
import {
  useAnalyzeCompany,
  useLoadTopicPrompts,
  useAddPromptsToGroupFromInspiration,
  useGeneratePrompts,
  useBatchSimilarPrompts,
} from "@/hooks/useInspiration"
import { useGenerationPrice, formatCredits } from "@/hooks/useBilling"
import { evaluationsApi } from "@/client/api"
import { CountrySelector } from "@/components/inspiration/CountrySelector"
import { TopicCard } from "@/components/inspiration/TopicCard"
import { WizardStepIndicator } from "@/components/inspiration/WizardStepIndicator"
import type {
  WizardState,
  TopicWithPrompts,
  PromptSelectionState,
  GeneratedTopicReview,
  GeneratedPromptReview,
} from "@/types/inspiration"

// ===== Types =====

// Local step type for this modal's specific flow
type GroupInspirationStep = "configure" | "select" | "generate" | "review" | "confirm"

interface GroupInspirationModalProps {
  groupId: number
  groupTitle: string
  brandDomain: string
  brandVariations: string[]
  onClose: () => void
}

// Selected prompt for final review
interface SelectedPrompt {
  id: number // prompt_id for existing, negative for generated
  text: string
  source: "matched" | "generated"
  topicTitle: string
  isNew?: boolean // true if this is a brand new prompt (not from DB)
}

// ===== Reducer =====

interface ModalState {
  step: GroupInspirationStep
  isoCountryCode: string
  metaInfo: WizardState["metaInfo"]
  matchedTopics: TopicWithPrompts[]
  selectedUnmatchedTopics: Set<string>
  selectedMatchedTopicsForGeneration: Set<number>
  generatedTopics: GeneratedTopicReview[]
  finalSelectedPrompts: SelectedPrompt[]
  error: string | null
  isAnalyzing: boolean
  isGenerating: boolean
  isSubmitting: boolean
}

type ModalAction =
  | { type: "SET_STEP"; step: GroupInspirationStep }
  | { type: "SET_COUNTRY_CODE"; code: string }
  | { type: "SET_META_INFO"; metaInfo: WizardState["metaInfo"] }
  | { type: "SET_MATCHED_TOPICS"; topics: TopicWithPrompts[] }
  | { type: "UPDATE_MATCHED_TOPIC"; topicId: number; updates: Partial<TopicWithPrompts> }
  | { type: "TOGGLE_PROMPT_SELECTION"; topicId: number; promptId: number }
  | { type: "SELECT_ALL_PROMPTS"; topicId: number }
  | { type: "DESELECT_ALL_PROMPTS"; topicId: number }
  | { type: "TOGGLE_UNMATCHED_TOPIC"; topicTitle: string }
  | { type: "TOGGLE_MATCHED_TOPIC_FOR_GENERATION"; topicId: number }
  | { type: "SET_GENERATED_TOPICS"; topics: GeneratedTopicReview[] }
  | { type: "UPDATE_GENERATED_TOPIC"; topicTitle: string; updates: Partial<GeneratedTopicReview> }
  | { type: "UPDATE_GENERATED_PROMPT"; topicTitle: string; promptIndex: number; selectedOption: "keep-original" | "use-match"; matchId: number | null }
  | { type: "TOGGLE_GENERATED_PROMPT"; topicTitle: string; promptIndex: number }
  | { type: "SET_FINAL_SELECTED_PROMPTS"; prompts: SelectedPrompt[] }
  | { type: "TOGGLE_FINAL_PROMPT"; promptId: number }
  | { type: "SET_ERROR"; error: string | null }
  | { type: "SET_ANALYZING"; analyzing: boolean }
  | { type: "SET_GENERATING"; generating: boolean }
  | { type: "SET_SUBMITTING"; submitting: boolean }
  | { type: "RESET" }

const initialState: ModalState = {
  step: "configure",
  isoCountryCode: "",
  metaInfo: null,
  matchedTopics: [],
  selectedUnmatchedTopics: new Set<string>(),
  selectedMatchedTopicsForGeneration: new Set<number>(),
  generatedTopics: [],
  finalSelectedPrompts: [],
  error: null,
  isAnalyzing: false,
  isGenerating: false,
  isSubmitting: false,
}

function modalReducer(state: ModalState, action: ModalAction): ModalState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, step: action.step, error: null }

    case "SET_COUNTRY_CODE":
      return { ...state, isoCountryCode: action.code }

    case "SET_META_INFO":
      return { ...state, metaInfo: action.metaInfo }

    case "SET_MATCHED_TOPICS":
      return { ...state, matchedTopics: action.topics }

    case "UPDATE_MATCHED_TOPIC":
      return {
        ...state,
        matchedTopics: state.matchedTopics.map((t) =>
          t.topicId === action.topicId ? { ...t, ...action.updates } : t
        ),
      }

    case "TOGGLE_PROMPT_SELECTION":
      return {
        ...state,
        matchedTopics: state.matchedTopics.map((t) =>
          t.topicId === action.topicId
            ? {
                ...t,
                prompts: t.prompts.map((p) =>
                  p.promptId === action.promptId
                    ? { ...p, isSelected: !p.isSelected }
                    : p
                ),
              }
            : t
        ),
      }

    case "SELECT_ALL_PROMPTS":
      return {
        ...state,
        matchedTopics: state.matchedTopics.map((t) =>
          t.topicId === action.topicId
            ? { ...t, prompts: t.prompts.map((p) => ({ ...p, isSelected: true })) }
            : t
        ),
      }

    case "DESELECT_ALL_PROMPTS":
      return {
        ...state,
        matchedTopics: state.matchedTopics.map((t) =>
          t.topicId === action.topicId
            ? { ...t, prompts: t.prompts.map((p) => ({ ...p, isSelected: false })) }
            : t
        ),
      }

    case "TOGGLE_UNMATCHED_TOPIC": {
      const newSet = new Set(state.selectedUnmatchedTopics)
      if (newSet.has(action.topicTitle)) {
        newSet.delete(action.topicTitle)
      } else {
        newSet.add(action.topicTitle)
      }
      return { ...state, selectedUnmatchedTopics: newSet }
    }

    case "TOGGLE_MATCHED_TOPIC_FOR_GENERATION": {
      const newSet = new Set(state.selectedMatchedTopicsForGeneration)
      if (newSet.has(action.topicId)) {
        newSet.delete(action.topicId)
      } else {
        newSet.add(action.topicId)
      }
      return { ...state, selectedMatchedTopicsForGeneration: newSet }
    }

    case "SET_GENERATED_TOPICS":
      return { ...state, generatedTopics: action.topics }

    case "UPDATE_GENERATED_TOPIC":
      return {
        ...state,
        generatedTopics: state.generatedTopics.map((t) =>
          t.topicTitle === action.topicTitle ? { ...t, ...action.updates } : t
        ),
      }

    case "UPDATE_GENERATED_PROMPT":
      return {
        ...state,
        generatedTopics: state.generatedTopics.map((t) =>
          t.topicTitle === action.topicTitle
            ? {
                ...t,
                prompts: t.prompts.map((p, i) =>
                  i === action.promptIndex
                    ? {
                        ...p,
                        selectedOption: action.selectedOption,
                        selectedMatchId: action.matchId,
                      }
                    : p
                ),
              }
            : t
        ),
      }

    case "TOGGLE_GENERATED_PROMPT":
      return {
        ...state,
        generatedTopics: state.generatedTopics.map((t) =>
          t.topicTitle === action.topicTitle
            ? {
                ...t,
                prompts: t.prompts.map((p, i) =>
                  i === action.promptIndex
                    ? { ...p, isSelected: !p.isSelected }
                    : p
                ),
              }
            : t
        ),
      }

    case "SET_FINAL_SELECTED_PROMPTS":
      return { ...state, finalSelectedPrompts: action.prompts }

    case "TOGGLE_FINAL_PROMPT":
      return {
        ...state,
        finalSelectedPrompts: state.finalSelectedPrompts.filter(
          (p) => p.id !== action.promptId
        ),
      }

    case "SET_ERROR":
      return { ...state, error: action.error }

    case "SET_ANALYZING":
      return { ...state, isAnalyzing: action.analyzing }

    case "SET_GENERATING":
      return { ...state, isGenerating: action.generating }

    case "SET_SUBMITTING":
      return { ...state, isSubmitting: action.submitting }

    case "RESET":
      return initialState

    default:
      return state
  }
}

// ===== Step Config =====

const STEPS: GroupInspirationStep[] = ["select", "generate", "review", "confirm"]

const STEP_LABELS: Record<GroupInspirationStep, string> = {
  configure: "Setup",
  select: "Select",
  generate: "Generate",
  review: "Review",
  confirm: "Confirm",
}

// ===== Main Component =====

export function GroupInspirationModal({
  groupId,
  groupTitle,
  brandDomain,
  brandVariations: initialBrandVariations,
  onClose,
}: GroupInspirationModalProps) {
  const [state, dispatch] = useReducer(modalReducer, initialState)
  const [countryCode, setCountryCode] = useState("")

  const analyzeCompany = useAnalyzeCompany()
  const loadTopicPrompts = useLoadTopicPrompts()
  const addPromptsToGroup = useAddPromptsToGroupFromInspiration()
  const generatePrompts = useGeneratePrompts()
  const batchSimilarPrompts = useBatchSimilarPrompts()
  const { data: priceInfo } = useGenerationPrice(state.step === "generate")

  const hasUnmatchedTopics = (state.metaInfo?.topics.unmatched_topics.length ?? 0) > 0
  const hasMatchedTopics = state.matchedTopics.length > 0

  // Count selected prompts from matched topics
  const selectedMatchedCount = useMemo(() => {
    let count = 0
    state.matchedTopics.forEach((topic) => {
      count += topic.prompts.filter((p) => p.isSelected).length
    })
    return count
  }, [state.matchedTopics])

  // Count topics selected for generation
  const topicsForGenerationCount =
    state.selectedUnmatchedTopics.size + state.selectedMatchedTopicsForGeneration.size

  // Handle country selection and analyze
  const handleAnalyze = useCallback(async () => {
    if (!countryCode) return

    dispatch({ type: "SET_ANALYZING", analyzing: true })
    dispatch({ type: "SET_COUNTRY_CODE", code: countryCode })

    try {
      const metaInfo = await analyzeCompany.mutateAsync({
        companyUrl: brandDomain,
        countryCode,
      })

      dispatch({ type: "SET_META_INFO", metaInfo })

      // Initialize matched topics
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
      dispatch({ type: "SET_STEP", step: "select" })
    } catch (error) {
      dispatch({
        type: "SET_ERROR",
        error:
          error instanceof Error
            ? error.message
            : "Failed to analyze company. Please try again.",
      })
    } finally {
      dispatch({ type: "SET_ANALYZING", analyzing: false })
    }
  }, [brandDomain, countryCode, analyzeCompany])

  // Handle loading prompts for a topic
  const handleLoadPrompts = async (topic: TopicWithPrompts) => {
    dispatch({
      type: "UPDATE_MATCHED_TOPIC",
      topicId: topic.topicId,
      updates: { isLoading: true, isExpanded: true },
    })

    try {
      const response = await loadTopicPrompts.mutateAsync([topic.topicId])
      const topicData = response.topics.find((t) => t.topic_id === topic.topicId)

      const prompts: PromptSelectionState[] =
        topicData?.prompts.map((p) => ({
          promptId: p.id,
          promptText: p.prompt_text,
          isSelected: false,
        })) ?? []

      dispatch({
        type: "UPDATE_MATCHED_TOPIC",
        topicId: topic.topicId,
        updates: { prompts, isLoading: false },
      })
    } catch {
      dispatch({
        type: "UPDATE_MATCHED_TOPIC",
        topicId: topic.topicId,
        updates: { isLoading: false },
      })
      dispatch({
        type: "SET_ERROR",
        error: "Failed to load prompts for this topic",
      })
    }
  }

  // Handle toggle expand
  const handleToggleExpand = (topicId: number) => {
    const topic = state.matchedTopics.find((t) => t.topicId === topicId)
    if (!topic) return

    if (topic.prompts.length === 0 && !topic.isLoading) {
      handleLoadPrompts(topic)
    } else {
      dispatch({
        type: "UPDATE_MATCHED_TOPIC",
        topicId,
        updates: { isExpanded: !topic.isExpanded },
      })
    }
  }

  // Proceed to generation step
  const handleProceedToGenerate = () => {
    dispatch({ type: "SET_STEP", step: "generate" })
  }

  // Skip generation and go to review (collect selected from matched topics only)
  const handleSkipGeneration = () => {
    collectSelectedPromptsAndProceed()
  }

  // Handle actual generation
  const handleGenerate = async () => {
    if (topicsForGenerationCount === 0) return

    dispatch({ type: "SET_GENERATING", generating: true })

    try {
      // Collect topic titles for generation
      const topicsToGenerate: string[] = []

      // Add unmatched topics
      state.selectedUnmatchedTopics.forEach((title) => {
        topicsToGenerate.push(title)
      })

      // Add matched topics selected for generation
      state.selectedMatchedTopicsForGeneration.forEach((topicId) => {
        const topic = state.matchedTopics.find((t) => t.topicId === topicId)
        if (topic) {
          topicsToGenerate.push(topic.topicTitle)
        }
      })

      const result = await generatePrompts.mutateAsync({
        company_url: brandDomain,
        iso_country_code: state.isoCountryCode,
        topics: topicsToGenerate,
        brand_variations: initialBrandVariations,
      })

      // Flatten prompts and find similar ones
      const allGeneratedPrompts = result.topics.flatMap((t) =>
        t.clusters.flatMap((c) => c.prompts)
      )

      const similarResults = await batchSimilarPrompts.mutateAsync(allGeneratedPrompts)

      // Create review state with isSelected flag
      const generatedTopics: (GeneratedTopicReview & { prompts: (GeneratedPromptReview & { isSelected: boolean })[] })[] = result.topics.map(
        (topic) => {
          const prompts = topic.clusters.flatMap((cluster) =>
            cluster.prompts.map((promptText) => {
              const similarResult = similarResults.find(
                (r) => r.query_text === promptText
              )
              return {
                inputText: promptText,
                keywords: cluster.keywords,
                matches: (similarResult?.prompts || []).map((p) => ({
                  promptId: p.id,
                  promptText: p.prompt_text,
                  similarity: p.similarity,
                })),
                selectedOption: "keep-original" as const,
                selectedMatchId: null,
                isSelected: true, // Default to selected
              }
            })
          )
          return {
            topicTitle: topic.topic,
            prompts,
            isExpanded: true,
            addedToGroupId: null,
            addedToGroupTitle: null,
          }
        }
      )

      dispatch({ type: "SET_GENERATED_TOPICS", topics: generatedTopics as GeneratedTopicReview[] })
      dispatch({ type: "SET_STEP", step: "review" })
    } catch (error) {
      dispatch({
        type: "SET_ERROR",
        error: error instanceof Error ? error.message : "Failed to generate prompts",
      })
    } finally {
      dispatch({ type: "SET_GENERATING", generating: false })
    }
  }

  // Collect all selected prompts and proceed to review
  const collectSelectedPromptsAndProceed = () => {
    const selected: SelectedPrompt[] = []

    // Collect from matched topics
    state.matchedTopics.forEach((topic) => {
      topic.prompts.forEach((prompt) => {
        if (prompt.isSelected) {
          selected.push({
            id: prompt.promptId,
            text: prompt.promptText,
            source: "matched",
            topicTitle: topic.topicTitle,
            isNew: false,
          })
        }
      })
    })

    dispatch({ type: "SET_FINAL_SELECTED_PROMPTS", prompts: selected })
    dispatch({ type: "SET_STEP", step: "review" })
  }

  // Collect from generated topics for final review
  const collectAllForConfirm = () => {
    const selected: SelectedPrompt[] = []

    // Collect from matched topics
    state.matchedTopics.forEach((topic) => {
      topic.prompts.forEach((prompt) => {
        if (prompt.isSelected) {
          selected.push({
            id: prompt.promptId,
            text: prompt.promptText,
            source: "matched",
            topicTitle: topic.topicTitle,
            isNew: false,
          })
        }
      })
    })

    // Collect from generated topics
    let generatedIdCounter = -1
    state.generatedTopics.forEach((topic) => {
      topic.prompts.forEach((prompt) => {
        const p = prompt as GeneratedPromptReview & { isSelected?: boolean }
        if (p.isSelected !== false) { // Default to selected if undefined
          if (p.selectedOption === "use-match" && p.selectedMatchId) {
            // Use existing prompt from DB
            const match = p.matches.find((m) => m.promptId === p.selectedMatchId)
            if (match) {
              selected.push({
                id: match.promptId,
                text: match.promptText,
                source: "generated",
                topicTitle: topic.topicTitle,
                isNew: false,
              })
            }
          } else {
            // New generated prompt
            selected.push({
              id: generatedIdCounter--,
              text: p.inputText,
              source: "generated",
              topicTitle: topic.topicTitle,
              isNew: true,
            })
          }
        }
      })
    })

    dispatch({ type: "SET_FINAL_SELECTED_PROMPTS", prompts: selected })
    dispatch({ type: "SET_STEP", step: "confirm" })
  }

  // Handle final submission
  const handleConfirmAdd = async () => {
    if (state.finalSelectedPrompts.length === 0) return

    dispatch({ type: "SET_SUBMITTING", submitting: true })

    try {
      // Separate existing prompts from new ones
      const existingPromptIds = state.finalSelectedPrompts
        .filter((p) => !p.isNew)
        .map((p) => p.id)

      const newPromptTexts = state.finalSelectedPrompts
        .filter((p) => p.isNew)
        .map((p) => p.text)

      // Add new prompts via priority prompts API
      if (newPromptTexts.length > 0) {
        const result = await evaluationsApi.addPriorityPrompts(newPromptTexts)
        const newPromptIds = result.prompts.map((p) => p.prompt_id)
        existingPromptIds.push(...newPromptIds)
      }

      // Add all prompts to group
      if (existingPromptIds.length > 0) {
        await addPromptsToGroup.mutateAsync({
          groupId,
          promptIds: existingPromptIds,
        })
      }

      onClose()
    } catch (error) {
      dispatch({
        type: "SET_ERROR",
        error: error instanceof Error ? error.message : "Failed to add prompts",
      })
    } finally {
      dispatch({ type: "SET_SUBMITTING", submitting: false })
    }
  }

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose()
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [onClose])

  const canAfford = priceInfo?.can_afford ?? false

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="relative bg-[#FDFBF7] rounded-2xl shadow-2xl w-full max-w-4xl mx-4 overflow-hidden animate-in fade-in zoom-in-95 duration-200"
        style={{ maxHeight: "90vh" }}
      >
        {/* Subtle texture overlay */}
        <div
          className="absolute inset-0 pointer-events-none opacity-[0.02]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%' height='100%' filter='url(%23noise)'/%3E%3C/svg%3E")`,
          }}
        />

        {/* Header */}
        <div className="relative z-10 px-6 py-4 border-b border-[#E5E7EB]/60 bg-white/80 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#C4553D] to-[#B34835] flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937]">
                  Prompt inspiration
                </h2>
                <p className="text-sm text-[#6B7280] font-['DM_Sans'] flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5" />
                  {brandDomain}
                  <span className="text-[#9CA3AF]">•</span>
                  Adding to {groupTitle}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-[#9CA3AF] hover:text-[#1F2937] hover:bg-[#F3F4F6] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div
          className="relative z-10 px-6 py-6 overflow-y-auto"
          style={{ maxHeight: "calc(90vh - 80px)" }}
        >
          <div className="space-y-6">
            {/* Step indicator (hidden on configure) */}
            {state.step !== "configure" && (
              <WizardStepIndicator
                steps={STEPS}
                currentStep={state.step}
                stepLabels={STEP_LABELS}
              />
            )}

            {/* ===== STEP: Configure (Country Selection) ===== */}
            {state.step === "configure" && (
              <div className="max-w-lg mx-auto">
                <div className="bg-white rounded-2xl shadow-xl shadow-black/5 overflow-hidden border border-[#E5E7EB]/60">
                  <div className="p-8 space-y-6">
                    <div className="text-center mb-6">
                      <h3 className="font-['Fraunces'] text-lg font-semibold text-[#1F2937] mb-1">
                        Select target country
                      </h3>
                      <p className="text-sm text-[#6B7280] font-['DM_Sans']">
                        We'll find SEO topics for your brand in this market
                      </p>
                    </div>

                    <CountrySelector value={countryCode} onChange={setCountryCode} />

                    <button
                      onClick={handleAnalyze}
                      disabled={!countryCode || state.isAnalyzing}
                      className={`
                        w-full py-4 px-6 rounded-xl font-['DM_Sans'] font-medium text-base
                        flex items-center justify-center gap-3 transition-all duration-200
                        ${
                          countryCode && !state.isAnalyzing
                            ? "bg-[#C4553D] text-white hover:bg-[#B34835] shadow-lg shadow-[#C4553D]/25"
                            : "bg-[#E5E7EB] text-[#9CA3AF] cursor-not-allowed"
                        }
                      `}
                    >
                      {state.isAnalyzing ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          <span>Analyzing...</span>
                        </>
                      ) : (
                        <>
                          <span>Find topics</span>
                          <ArrowRight className="w-5 h-5" />
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ===== STEP: Select from Matched Topics ===== */}
            {state.step === "select" && (
              <div className="space-y-6">
                {!hasMatchedTopics ? (
                  <div className="max-w-lg mx-auto">
                    <div className="bg-white rounded-2xl shadow-lg shadow-black/5 border border-[#E5E7EB]/60 p-8 text-center">
                      <div className="w-16 h-16 rounded-full bg-[#FEF7F5] flex items-center justify-center mx-auto mb-4">
                        <Package className="w-8 h-8 text-[#C4553D]" />
                      </div>
                      <h3 className="font-['Fraunces'] text-xl font-semibold text-[#1F2937] mb-2">
                        No matched topics found
                      </h3>
                      <p className="text-[#6B7280] font-['DM_Sans'] mb-6">
                        {hasUnmatchedTopics
                          ? "We couldn't find existing prompts, but we can generate new ones!"
                          : "Try a different country."}
                      </p>
                      <div className="flex justify-center gap-3">
                        <button
                          onClick={() => dispatch({ type: "SET_STEP", step: "configure" })}
                          className="px-5 py-2.5 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] font-['DM_Sans'] transition-colors"
                        >
                          Change country
                        </button>
                        {hasUnmatchedTopics && (
                          <button
                            onClick={handleProceedToGenerate}
                            className="px-5 py-2.5 text-sm font-medium text-white bg-[#C4553D] hover:bg-[#B34835] rounded-lg font-['DM_Sans'] transition-colors flex items-center gap-2"
                          >
                            <Sparkles className="w-4 h-4" />
                            Generate prompts
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Topic cards */}
                    <div className="lg:col-span-2 space-y-4">
                      <div className="flex items-center justify-between mb-2">
                        <h2 className="font-['Fraunces'] text-lg font-semibold text-[#1F2937]">
                          Select prompts from topics ({state.matchedTopics.length})
                        </h2>
                        <p className="text-sm text-[#6B7280] font-['DM_Sans']">
                          Click topics to expand
                        </p>
                      </div>

                      {state.matchedTopics.map((topic, index) => (
                        <TopicCard
                          key={topic.topicId}
                          topic={topic}
                          colorIndex={index}
                          onToggleExpand={() => handleToggleExpand(topic.topicId)}
                          onTogglePrompt={(promptId) =>
                            dispatch({
                              type: "TOGGLE_PROMPT_SELECTION",
                              topicId: topic.topicId,
                              promptId,
                            })
                          }
                          onSelectAll={() =>
                            dispatch({ type: "SELECT_ALL_PROMPTS", topicId: topic.topicId })
                          }
                          onDeselectAll={() =>
                            dispatch({ type: "DESELECT_ALL_PROMPTS", topicId: topic.topicId })
                          }
                        />
                      ))}
                    </div>

                    {/* Summary panel */}
                    <div className="lg:col-span-1">
                      <div className="bg-white rounded-2xl shadow-lg shadow-black/5 border border-[#E5E7EB]/60 overflow-hidden sticky top-6">
                        <div className="px-5 py-4 border-b border-[#E5E7EB]/60 bg-gradient-to-br from-[#FAFAFA] to-white">
                          <h3 className="font-['Fraunces'] text-base font-semibold text-[#1F2937]">
                            Selection
                          </h3>
                        </div>

                        <div className="p-5 space-y-4">
                          <div className="flex items-center justify-between">
                            <span className="text-sm text-[#6B7280] font-['DM_Sans']">
                              Selected prompts
                            </span>
                            <span className="font-['Fraunces'] text-2xl font-semibold text-[#C4553D]">
                              {selectedMatchedCount}
                            </span>
                          </div>

                          {(hasUnmatchedTopics || hasMatchedTopics) && (
                            <div className="pt-4 border-t border-[#E5E7EB]/60">
                              <div className="flex items-center gap-2 text-sm text-[#6B7280] font-['DM_Sans']">
                                <Sparkles className="w-4 h-4 text-[#C4553D]" />
                                <span>
                                  {(state.metaInfo?.topics.unmatched_topics.length ?? 0) +
                                    state.matchedTopics.length}{" "}
                                  topics available for generation
                                </span>
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="p-5 border-t border-[#E5E7EB]/60 space-y-3">
                          <button
                            onClick={handleProceedToGenerate}
                            className="w-full py-3 px-4 text-sm font-medium text-white bg-[#C4553D] hover:bg-[#B34835] rounded-xl font-['DM_Sans'] transition-colors flex items-center justify-center gap-2"
                          >
                            <span>Continue to Generation</span>
                            <ArrowRight className="w-4 h-4" />
                          </button>

                          {selectedMatchedCount > 0 && (
                            <button
                              onClick={handleSkipGeneration}
                              className="w-full py-3 px-4 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] hover:bg-[#FAFAFA] rounded-xl font-['DM_Sans'] transition-colors"
                            >
                              Skip generation, review selection
                            </button>
                          )}

                          <button
                            onClick={() => dispatch({ type: "SET_STEP", step: "configure" })}
                            className="w-full py-3 px-4 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] hover:bg-[#FAFAFA] rounded-xl font-['DM_Sans'] transition-colors flex items-center justify-center gap-2"
                          >
                            <ArrowLeft className="w-4 h-4" />
                            <span>Change country</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ===== STEP: Generate ===== */}
            {state.step === "generate" && (
              <div className="max-w-2xl mx-auto">
                <div className="bg-white rounded-2xl shadow-xl shadow-black/5 overflow-hidden border border-[#E5E7EB]/60">
                  <div className="p-8 space-y-6">
                    <div className="text-center mb-4">
                      <h3 className="font-['Fraunces'] text-lg font-semibold text-[#1F2937] mb-1">
                        Generate new prompts
                      </h3>
                      <p className="text-sm text-[#6B7280] font-['DM_Sans']">
                        Select topics to generate AI-powered prompts
                      </p>
                    </div>

                    {/* Price info */}
                    <div className="flex items-center justify-between p-4 rounded-xl bg-violet-50 border border-violet-100">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-violet-500" />
                        <span className="text-sm text-violet-700 font-['DM_Sans']">
                          Generation costs{" "}
                          <span className="font-semibold">
                            ${formatCredits(priceInfo?.price)}
                          </span>
                        </span>
                      </div>
                      {priceInfo && (
                        <span
                          className={`text-sm font-['DM_Sans'] ${
                            canAfford ? "text-violet-600" : "text-amber-600"
                          }`}
                        >
                          Balance: ${formatCredits(priceInfo.user_balance)}
                        </span>
                      )}
                    </div>

                    {/* Unmatched topics */}
                    {hasUnmatchedTopics && (
                      <div className="space-y-2">
                        <p className="text-xs uppercase tracking-widest text-gray-400 font-['DM_Sans']">
                          New topics
                        </p>
                        {state.metaInfo?.topics.unmatched_topics.map((topic) => (
                          <button
                            key={topic.title}
                            onClick={() =>
                              dispatch({ type: "TOGGLE_UNMATCHED_TOPIC", topicTitle: topic.title })
                            }
                            className={`
                              w-full px-4 py-3 rounded-xl text-left text-sm font-['DM_Sans']
                              border transition-all duration-200
                              ${
                                state.selectedUnmatchedTopics.has(topic.title)
                                  ? "border-[#C4553D] bg-[#FEF7F5] text-[#1F2937]"
                                  : "border-[#E5E7EB] bg-white hover:border-[#C4553D]/50 text-[#6B7280]"
                              }
                            `}
                          >
                            <div className="flex items-center justify-between">
                              <span>{topic.title}</span>
                              {state.selectedUnmatchedTopics.has(topic.title) && (
                                <Check className="w-4 h-4 text-[#C4553D]" />
                              )}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Matched topics (can also generate for) */}
                    {hasMatchedTopics && (
                      <div className="space-y-2">
                        <p className="text-xs uppercase tracking-widest text-gray-400 font-['DM_Sans']">
                          Existing topics (generate more)
                        </p>
                        {state.matchedTopics.map((topic) => (
                          <button
                            key={topic.topicId}
                            onClick={() =>
                              dispatch({
                                type: "TOGGLE_MATCHED_TOPIC_FOR_GENERATION",
                                topicId: topic.topicId,
                              })
                            }
                            className={`
                              w-full px-4 py-3 rounded-xl text-left text-sm font-['DM_Sans']
                              border transition-all duration-200
                              ${
                                state.selectedMatchedTopicsForGeneration.has(topic.topicId)
                                  ? "border-[#C4553D] bg-[#FEF7F5] text-[#1F2937]"
                                  : "border-[#E5E7EB] bg-white hover:border-[#C4553D]/50 text-[#6B7280]"
                              }
                            `}
                          >
                            <div className="flex items-center justify-between">
                              <span>{topic.topicTitle}</span>
                              {state.selectedMatchedTopicsForGeneration.has(topic.topicId) && (
                                <Check className="w-4 h-4 text-[#C4553D]" />
                              )}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Generate button */}
                    {canAfford ? (
                      <button
                        onClick={handleGenerate}
                        disabled={topicsForGenerationCount === 0 || state.isGenerating}
                        className={`
                          w-full py-4 px-6 rounded-xl font-['DM_Sans'] font-medium text-base
                          flex items-center justify-center gap-3 transition-all duration-200
                          ${
                            topicsForGenerationCount > 0 && !state.isGenerating
                              ? "bg-[#C4553D] text-white hover:bg-[#B34835] shadow-lg shadow-[#C4553D]/25"
                              : "bg-[#E5E7EB] text-[#9CA3AF] cursor-not-allowed"
                          }
                        `}
                      >
                        {state.isGenerating ? (
                          <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span>Generating prompts...</span>
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-5 h-5" />
                            <span>
                              Generate ({topicsForGenerationCount} topic
                              {topicsForGenerationCount !== 1 ? "s" : ""}) — $
                              {formatCredits(priceInfo?.price)}
                            </span>
                          </>
                        )}
                      </button>
                    ) : (
                      <Link
                        to="/top-up"
                        className="w-full py-4 px-6 rounded-xl font-['DM_Sans'] font-medium text-base bg-amber-500 hover:bg-amber-600 text-white flex items-center justify-center gap-2 transition-colors"
                      >
                        Add credits to generate
                      </Link>
                    )}

                    {/* Skip if already have selections */}
                    {selectedMatchedCount > 0 && (
                      <button
                        onClick={handleSkipGeneration}
                        className="w-full py-3 px-4 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] hover:bg-[#FAFAFA] rounded-xl font-['DM_Sans'] transition-colors"
                      >
                        Skip generation, review {selectedMatchedCount} selected prompt
                        {selectedMatchedCount !== 1 ? "s" : ""}
                      </button>
                    )}

                    <button
                      onClick={() => dispatch({ type: "SET_STEP", step: "select" })}
                      className="w-full py-3 px-4 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] hover:bg-[#FAFAFA] rounded-xl font-['DM_Sans'] transition-colors flex items-center justify-center gap-2"
                    >
                      <ArrowLeft className="w-4 h-4" />
                      <span>Back to selection</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ===== STEP: Review Generated ===== */}
            {state.step === "review" && (
              <div className="max-w-3xl mx-auto space-y-6">
                <div className="text-center mb-4">
                  <h3 className="font-['Fraunces'] text-lg font-semibold text-[#1F2937] mb-1">
                    Review generated prompts
                  </h3>
                  <p className="text-sm text-[#6B7280] font-['DM_Sans']">
                    Deselect any prompts you don't want to add
                  </p>
                </div>

                {/* Selected from matched topics */}
                {selectedMatchedCount > 0 && (
                  <div className="bg-white rounded-2xl shadow-lg shadow-black/5 border border-[#E5E7EB]/60 p-6">
                    <h4 className="font-['Fraunces'] text-base font-semibold text-[#1F2937] mb-4">
                      From existing topics ({selectedMatchedCount})
                    </h4>
                    <div className="space-y-2 max-h-[200px] overflow-y-auto">
                      {state.matchedTopics.flatMap((topic) =>
                        topic.prompts
                          .filter((p) => p.isSelected)
                          .map((prompt) => (
                            <div
                              key={prompt.promptId}
                              className="flex items-start gap-3 p-3 bg-[#FAFAFA] rounded-lg group"
                            >
                              <button
                                onClick={() =>
                                  dispatch({
                                    type: "TOGGLE_PROMPT_SELECTION",
                                    topicId: topic.topicId,
                                    promptId: prompt.promptId,
                                  })
                                }
                                className="mt-0.5 w-5 h-5 rounded border-2 border-[#C4553D] bg-[#C4553D] flex items-center justify-center shrink-0"
                              >
                                <Check className="w-3 h-3 text-white" />
                              </button>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm text-[#374151] font-['DM_Sans']">
                                  {prompt.promptText}
                                </p>
                                <p className="text-xs text-[#9CA3AF] mt-1">{topic.topicTitle}</p>
                              </div>
                            </div>
                          ))
                      )}
                    </div>
                  </div>
                )}

                {/* Generated prompts */}
                {state.generatedTopics.length > 0 && (
                  <div className="bg-white rounded-2xl shadow-lg shadow-black/5 border border-[#E5E7EB]/60 p-6">
                    <h4 className="font-['Fraunces'] text-base font-semibold text-[#1F2937] mb-4">
                      Generated prompts
                    </h4>
                    <div className="space-y-4 max-h-[400px] overflow-y-auto">
                      {state.generatedTopics.map((topic) => (
                        <div key={topic.topicTitle}>
                          <p className="text-xs uppercase tracking-widest text-gray-400 font-['DM_Sans'] mb-2">
                            {topic.topicTitle}
                          </p>
                          <div className="space-y-2">
                            {topic.prompts.map((prompt, i) => {
                              const p = prompt as GeneratedPromptReview & { isSelected?: boolean }
                              const isSelected = p.isSelected !== false
                              return (
                                <div
                                  key={i}
                                  className={`flex items-start gap-3 p-3 rounded-lg group ${
                                    isSelected ? "bg-[#FAFAFA]" : "bg-gray-100 opacity-60"
                                  }`}
                                >
                                  <button
                                    onClick={() =>
                                      dispatch({
                                        type: "TOGGLE_GENERATED_PROMPT",
                                        topicTitle: topic.topicTitle,
                                        promptIndex: i,
                                      })
                                    }
                                    className={`mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 ${
                                      isSelected
                                        ? "border-[#C4553D] bg-[#C4553D]"
                                        : "border-gray-300 bg-white"
                                    }`}
                                  >
                                    {isSelected && <Check className="w-3 h-3 text-white" />}
                                  </button>
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm text-[#374151] font-['DM_Sans']">
                                      {p.inputText}
                                    </p>
                                    {p.matches.length > 0 && (
                                      <div className="mt-2 space-y-1">
                                        <p className="text-xs text-[#9CA3AF]">Similar existing:</p>
                                        {p.matches.slice(0, 2).map((match) => (
                                          <button
                                            key={match.promptId}
                                            onClick={() =>
                                              dispatch({
                                                type: "UPDATE_GENERATED_PROMPT",
                                                topicTitle: topic.topicTitle,
                                                promptIndex: i,
                                                selectedOption:
                                                  p.selectedMatchId === match.promptId
                                                    ? "keep-original"
                                                    : "use-match",
                                                matchId:
                                                  p.selectedMatchId === match.promptId
                                                    ? null
                                                    : match.promptId,
                                              })
                                            }
                                            className={`w-full text-left px-2 py-1.5 rounded text-xs font-['DM_Sans'] ${
                                              p.selectedMatchId === match.promptId
                                                ? "bg-[#C4553D]/10 text-[#C4553D] border border-[#C4553D]/30"
                                                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                                            }`}
                                          >
                                            {match.promptText}
                                            <span className="text-[10px] ml-1 opacity-60">
                                              ({Math.round(match.similarity * 100)}%)
                                            </span>
                                          </button>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex justify-center gap-3">
                  <button
                    onClick={() =>
                      dispatch({
                        type: "SET_STEP",
                        step: state.generatedTopics.length > 0 ? "generate" : "select",
                      })
                    }
                    className="px-5 py-3 text-sm font-medium text-[#6B7280] hover:text-[#1F2937] hover:bg-[#FAFAFA] rounded-xl font-['DM_Sans'] transition-colors flex items-center gap-2"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    Back
                  </button>
                  <button
                    onClick={collectAllForConfirm}
                    className="px-8 py-3 text-sm font-medium text-white bg-[#C4553D] hover:bg-[#B34835] rounded-xl font-['DM_Sans'] transition-colors flex items-center gap-2"
                  >
                    Continue to confirm
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* ===== STEP: Confirm ===== */}
            {state.step === "confirm" && (
              <div className="max-w-2xl mx-auto">
                <div className="bg-white rounded-2xl shadow-xl shadow-black/5 overflow-hidden border border-[#E5E7EB]/60">
                  <div className="p-8 space-y-6">
                    <div className="text-center mb-4">
                      <div className="w-16 h-16 rounded-full bg-[#FEF7F5] flex items-center justify-center mx-auto mb-4">
                        <Plus className="w-8 h-8 text-[#C4553D]" />
                      </div>
                      <h3 className="font-['Fraunces'] text-lg font-semibold text-[#1F2937] mb-1">
                        Add {state.finalSelectedPrompts.length} prompts to {groupTitle}?
                      </h3>
                      <p className="text-sm text-[#6B7280] font-['DM_Sans']">
                        {state.finalSelectedPrompts.filter((p) => !p.isNew).length} existing +{" "}
                        {state.finalSelectedPrompts.filter((p) => p.isNew).length} new prompts
                      </p>
                    </div>

                    {/* Prompt list */}
                    <div className="max-h-[300px] overflow-y-auto space-y-2 border rounded-xl p-4 bg-[#FAFAFA]">
                      {state.finalSelectedPrompts.map((prompt) => (
                        <div
                          key={prompt.id}
                          className="flex items-start gap-3 p-3 bg-white rounded-lg border border-[#E5E7EB]"
                        >
                          <button
                            onClick={() =>
                              dispatch({ type: "TOGGLE_FINAL_PROMPT", promptId: prompt.id })
                            }
                            className="mt-0.5 p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-[#374151] font-['DM_Sans']">{prompt.text}</p>
                            <p className="text-xs text-[#9CA3AF] mt-1 flex items-center gap-1">
                              {prompt.isNew && (
                                <span className="px-1.5 py-0.5 bg-[#C4553D]/10 text-[#C4553D] rounded text-[10px] font-medium">
                                  NEW
                                </span>
                              )}
                              {prompt.topicTitle}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3">
                      <button
                        onClick={() => dispatch({ type: "SET_STEP", step: "review" })}
                        disabled={state.isSubmitting}
                        className="flex-1 py-3 px-4 text-sm font-medium text-[#6B7280] bg-gray-100 hover:bg-gray-200 rounded-xl font-['DM_Sans'] transition-colors"
                      >
                        Back
                      </button>
                      <button
                        onClick={handleConfirmAdd}
                        disabled={state.isSubmitting || state.finalSelectedPrompts.length === 0}
                        className="flex-1 py-3 px-4 text-sm font-medium text-white bg-[#C4553D] hover:bg-[#B34835] rounded-xl font-['DM_Sans'] transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        {state.isSubmitting ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Adding...
                          </>
                        ) : (
                          <>
                            <Check className="w-4 h-4" />
                            Add to group
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Error display */}
            {state.error && (
              <div className="max-w-2xl mx-auto p-4 rounded-xl bg-red-50 border border-red-100 animate-in fade-in slide-in-from-top-2 duration-200">
                <p className="text-sm text-red-600 font-['DM_Sans']">{state.error}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
