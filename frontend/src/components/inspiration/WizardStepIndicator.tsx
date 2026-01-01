/**
 * WizardStepIndicator - Visual progress indicator for wizard steps
 * Editorial/magazine-inspired design with animated transitions
 */

import { Check } from "lucide-react"

interface WizardStepIndicatorProps<T extends string> {
  steps: T[]
  currentStep: T
  stepLabels: Record<T, string>
}

export function WizardStepIndicator<T extends string>({
  steps,
  currentStep,
  stepLabels,
}: WizardStepIndicatorProps<T>) {
  const currentIndex = steps.indexOf(currentStep)

  return (
    <div className="relative">
      {/* Background line */}
      <div className="absolute top-5 left-0 right-0 h-0.5 bg-[#E5E7EB]" />

      {/* Progress line */}
      <div
        className="absolute top-5 left-0 h-0.5 bg-[#C4553D] transition-all duration-500 ease-out"
        style={{
          width: `${(currentIndex / (steps.length - 1)) * 100}%`,
        }}
      />

      {/* Step dots and labels */}
      <div className="relative flex justify-between">
        {steps.map((step, index) => {
          const isCompleted = index < currentIndex
          const isCurrent = index === currentIndex

          return (
            <div key={step} className="flex flex-col items-center">
              {/* Step circle */}
              <div
                className={`
                  relative z-10 w-10 h-10 rounded-full flex items-center justify-center
                  transition-all duration-300 ease-out
                  ${
                    isCompleted
                      ? "bg-[#C4553D] text-white shadow-md shadow-[#C4553D]/30"
                      : isCurrent
                      ? "bg-white border-2 border-[#C4553D] text-[#C4553D] shadow-lg shadow-[#C4553D]/20 scale-110"
                      : "bg-white border-2 border-[#E5E7EB] text-[#9CA3AF]"
                  }
                `}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5" strokeWidth={2.5} />
                ) : (
                  <span className="font-['Fraunces'] text-sm font-semibold">
                    {index + 1}
                  </span>
                )}

                {/* Pulse animation for current step */}
                {isCurrent && (
                  <span className="absolute inset-0 rounded-full border-2 border-[#C4553D] animate-ping opacity-20" />
                )}
              </div>

              {/* Step label */}
              <span
                className={`
                  mt-3 text-xs font-['DM_Sans'] font-medium transition-colors duration-200
                  ${
                    isCompleted || isCurrent
                      ? "text-[#1F2937]"
                      : "text-[#9CA3AF]"
                  }
                `}
              >
                {stepLabels[step]}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
