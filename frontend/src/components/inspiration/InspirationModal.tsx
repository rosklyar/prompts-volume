/**
 * InspirationModal - DataForSEO Inspiration feature as a modal dialog
 * Multi-step wizard for discovering and organizing prompts
 */

import { useCallback, useReducer, useEffect } from "react"
import { InspirationWizard } from "./InspirationWizard"
import { X, Sparkles } from "lucide-react"
import type {
  WizardState,
  InspirationStep,
  MetaInfoResponse,
  TopicWithPrompts,
  GeneratedTopicReview,
} from "@/types/inspiration"

// ===== Reducer for Wizard State =====

export type WizardAction =
  | { type: "SET_STEP"; step: InspirationStep }
  | { type: "SET_COMPANY_URL"; url: string }
  | { type: "SET_COUNTRY_CODE"; code: string }
  | { type: "SET_META_INFO"; metaInfo: MetaInfoResponse }
  | { type: "SET_MATCHED_TOPICS"; topics: TopicWithPrompts[] }
  | { type: "UPDATE_MATCHED_TOPIC"; topicId: number; updates: Partial<TopicWithPrompts> }
  | { type: "TOGGLE_PROMPT_SELECTION"; topicId: number; promptId: number }
  | { type: "SELECT_ALL_PROMPTS"; topicId: number }
  | { type: "DESELECT_ALL_PROMPTS"; topicId: number }
  | { type: "TOGGLE_UNMATCHED_TOPIC"; topicTitle: string }
  | { type: "SET_BRAND_VARIATIONS"; variations: string[] }
  | { type: "SET_GENERATED_TOPICS"; topics: GeneratedTopicReview[] }
  | { type: "UPDATE_GENERATED_TOPIC"; topicTitle: string; updates: Partial<GeneratedTopicReview> }
  | { type: "UPDATE_GENERATED_PROMPT"; topicTitle: string; promptIndex: number; selectedOption: "keep-original" | "use-match"; matchId: number | null }
  | { type: "SET_ERROR"; error: string | null }
  | { type: "RESET" }

const initialState: WizardState = {
  step: "configure",
  companyUrl: "",
  isoCountryCode: "",
  metaInfo: null,
  matchedTopics: [],
  selectedUnmatchedTopics: new Set<string>(),
  brandVariations: [],
  generatedTopics: [],
  error: null,
}

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, step: action.step, error: null }

    case "SET_COMPANY_URL":
      return { ...state, companyUrl: action.url }

    case "SET_COUNTRY_CODE":
      return { ...state, isoCountryCode: action.code }

    case "SET_META_INFO":
      return {
        ...state,
        metaInfo: action.metaInfo,
        brandVariations: action.metaInfo.brand_variations,
      }

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
            ? {
                ...t,
                prompts: t.prompts.map((p) => ({ ...p, isSelected: true })),
              }
            : t
        ),
      }

    case "DESELECT_ALL_PROMPTS":
      return {
        ...state,
        matchedTopics: state.matchedTopics.map((t) =>
          t.topicId === action.topicId
            ? {
                ...t,
                prompts: t.prompts.map((p) => ({ ...p, isSelected: false })),
              }
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

    case "SET_BRAND_VARIATIONS":
      return { ...state, brandVariations: action.variations }

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

    case "SET_ERROR":
      return { ...state, error: action.error }

    case "RESET":
      return initialState

    default:
      return state
  }
}

// ===== Modal Props =====

interface InspirationModalProps {
  isOpen: boolean
  onClose: () => void
}

// ===== Main Component =====

export function InspirationModal({ isOpen, onClose }: InspirationModalProps) {
  const [state, dispatch] = useReducer(wizardReducer, initialState)

  const handleReset = useCallback(() => {
    dispatch({ type: "RESET" })
  }, [])

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      // Small delay to allow close animation
      const timer = setTimeout(() => {
        dispatch({ type: "RESET" })
      }, 200)
      return () => clearTimeout(timer)
    }
  }, [isOpen])

  // Handle close - could add confirmation dialog here for mid-wizard close
  const handleClose = useCallback(() => {
    onClose()
  }, [onClose])

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleClose()
      }
    }

    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [isOpen, handleClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={handleClose}
      />

      {/* Modal */}
      <div
        className="relative bg-[#FDFBF7] rounded-2xl shadow-2xl w-full max-w-5xl mx-4 overflow-hidden animate-in fade-in zoom-in-95 duration-200"
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
                  Prompt Inspiration
                </h2>
                <p className="text-sm text-[#6B7280] font-['DM_Sans']">
                  Discover SEO-powered prompts for your business
                </p>
              </div>
            </div>
            <button
              onClick={handleClose}
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
          <InspirationWizard state={state} dispatch={dispatch} onReset={handleReset} onClose={onClose} />
        </div>
      </div>
    </div>
  )
}
