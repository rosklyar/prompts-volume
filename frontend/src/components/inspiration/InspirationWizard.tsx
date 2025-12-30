/**
 * InspirationWizard - Main wizard container with step orchestration
 */

import { WizardStepIndicator } from "./WizardStepIndicator"
import { ConfigurationStep } from "./steps/ConfigurationStep"
import { MatchedTopicsStep } from "./steps/MatchedTopicsStep"
import { GenerationStep } from "./steps/GenerationStep"
import { GeneratedReviewStep } from "./steps/GeneratedReviewStep"
import type { WizardAction } from "./InspirationModal"
import type { WizardState, InspirationStep } from "@/types/inspiration"

interface InspirationWizardProps {
  state: WizardState
  dispatch: React.Dispatch<WizardAction>
  onReset: () => void
  onClose: () => void
}

const STEPS: InspirationStep[] = ["configure", "matched", "generate", "review"]

const STEP_LABELS: Record<InspirationStep, string> = {
  configure: "Configure",
  matched: "Matched Topics",
  generate: "Generate",
  review: "Review",
}

export function InspirationWizard({ state, dispatch, onClose }: InspirationWizardProps) {
  return (
    <div className="space-y-8">
      {/* Step indicator */}
      <WizardStepIndicator
        steps={STEPS}
        currentStep={state.step}
        stepLabels={STEP_LABELS}
      />

      {/* Step content */}
      <div className="relative">
        {state.step === "configure" && (
          <ConfigurationStep state={state} dispatch={dispatch} />
        )}

        {state.step === "matched" && (
          <MatchedTopicsStep state={state} dispatch={dispatch} onClose={onClose} />
        )}

        {state.step === "generate" && (
          <GenerationStep state={state} dispatch={dispatch} onClose={onClose} />
        )}

        {state.step === "review" && (
          <GeneratedReviewStep state={state} dispatch={dispatch} onClose={onClose} />
        )}
      </div>

      {/* Error display */}
      {state.error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-100 animate-in fade-in slide-in-from-top-2 duration-200">
          <p className="text-sm text-red-600 font-['DM_Sans']">{state.error}</p>
        </div>
      )}
    </div>
  )
}
