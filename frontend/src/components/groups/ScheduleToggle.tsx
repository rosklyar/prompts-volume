/**
 * ScheduleToggle - Toggle for enabling/disabling daily scheduled reports
 * Features assistant selection popover and shows selected assistant logos when enabled
 */

import { useState } from "react"
import { useGroupSchedule, useSetGroupSchedule } from "@/hooks/useGroups"
import { useAssistants } from "@/hooks/useAssistants"
import { Tooltip } from "@/components/ui/tooltip"
import { Popover } from "@/components/ui/popover"
import chatgptLogo from "@/assets/chatgpt-logo.svg"
import perplexityLogo from "@/assets/perplexity-logo.svg"
import geminiLogo from "@/assets/gemini-logo.svg"

interface ScheduleToggleProps {
  groupId: number
  accentColor: string
}

// Assistant logo mapping
const ASSISTANT_LOGOS: Record<string, string> = {
  chatgpt: chatgptLogo,
  perplexity: perplexityLogo,
  gemini: geminiLogo,
}

function getAssistantLogo(name: string): string | undefined {
  const key = name.toLowerCase()
  return ASSISTANT_LOGOS[key]
}

export function ScheduleToggle({ groupId, accentColor }: ScheduleToggleProps) {
  const { data: schedule, isLoading } = useGroupSchedule(groupId)
  const { data: assistantsData } = useAssistants()
  const setScheduleMutation = useSetGroupSchedule()

  const [popoverOpen, setPopoverOpen] = useState(false)
  const [selectedAssistants, setSelectedAssistants] = useState<number[]>([])

  const isEnabled = schedule?.enabled ?? false
  const isPending = setScheduleMutation.isPending
  const assistants = assistantsData?.assistants ?? []

  const handleToggleClick = () => {
    if (isPending || isLoading) return

    if (isEnabled) {
      // Disable directly without popover
      setScheduleMutation.mutate({ groupId, enabled: false })
    } else {
      // Show assistant selection popover
      // Pre-select ChatGPT (id=1) if available
      const defaultSelection = assistants.find((a) => a.id === 1) ? [1] : []
      setSelectedAssistants(defaultSelection)
      setPopoverOpen(true)
    }
  }

  const handleAssistantToggle = (assistantId: number) => {
    setSelectedAssistants((prev) =>
      prev.includes(assistantId)
        ? prev.filter((id) => id !== assistantId)
        : [...prev, assistantId]
    )
  }

  const handleEnable = () => {
    if (selectedAssistants.length === 0) return
    setScheduleMutation.mutate(
      { groupId, enabled: true, assistantIds: selectedAssistants },
      { onSuccess: () => setPopoverOpen(false) }
    )
  }

  const handleCancel = () => {
    setPopoverOpen(false)
    setSelectedAssistants([])
  }

  const tooltipContent = (
    <span className="flex items-center gap-2">
      <span>
        {isEnabled
          ? "Reports generated daily at 6 AM UTC"
          : "Enable for daily reports at 6 AM UTC"}
      </span>
    </span>
  )

  // Get selected assistant info for display when enabled
  const selectedAssistantInfo =
    schedule?.assistant_ids
      ?.map((id) => assistants.find((a) => a.id === id))
      .filter(Boolean) ?? []

  const triggerButton = (
    <Tooltip content={tooltipContent} side="bottom" disabled={isLoading}>
      <button
        onClick={handleToggleClick}
        disabled={isLoading || isPending}
        className={`
          flex items-center gap-1.5 px-2 py-1 rounded-full
          transition-all duration-200 cursor-pointer
          border
          disabled:opacity-50 disabled:cursor-not-allowed
          ${isPending ? "animate-pulse" : ""}
          ${
            isEnabled
              ? "border-transparent"
              : "border-gray-300 bg-gray-50 hover:bg-gray-100"
          }
        `}
        style={
          isEnabled
            ? {
                backgroundColor: `${accentColor}15`,
                borderColor: `${accentColor}40`,
              }
            : undefined
        }
        aria-label={
          isEnabled ? "Disable daily schedule" : "Enable daily schedule"
        }
        aria-pressed={isEnabled}
      >
        {/* Mini toggle switch */}
        <span
          className="relative w-7 h-4 rounded-full transition-colors duration-200"
          style={{
            backgroundColor: isEnabled ? accentColor : "#D1D5DB",
          }}
        >
          <span
            className={`
              absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full shadow-sm
              transition-transform duration-200 ease-in-out
              ${isEnabled ? "translate-x-3" : "translate-x-0"}
            `}
          />
        </span>

        {/* Daily label */}
        <span
          className={`
            text-xs font-medium uppercase tracking-wide
            transition-colors duration-200
            ${isEnabled ? "" : "text-gray-500"}
          `}
          style={isEnabled ? { color: accentColor } : undefined}
        >
          Daily
        </span>

        {/* Show selected assistant logos when enabled */}
        {isEnabled && selectedAssistantInfo.length > 0 && (
          <span className="flex items-center gap-0.5 ml-0.5">
            {selectedAssistantInfo.map((assistant) => {
              const logo = getAssistantLogo(assistant!.name)
              return logo ? (
                <img
                  key={assistant!.id}
                  src={logo}
                  alt={assistant!.name}
                  className="w-4 h-4"
                />
              ) : (
                <span
                  key={assistant!.id}
                  className="text-xs"
                  title={assistant!.name}
                >
                  {assistant!.name.charAt(0)}
                </span>
              )
            })}
          </span>
        )}
      </button>
    </Tooltip>
  )

  return (
    <Popover
      open={popoverOpen}
      onOpenChange={setPopoverOpen}
      trigger={triggerButton}
      side="bottom"
      align="start"
    >
      <div className="p-4 min-w-[280px]">
        <p className="text-sm font-medium text-gray-700 mb-3">
          Select assistants for daily reports
        </p>

        {/* Assistant selection grid */}
        <div className="flex gap-2 flex-wrap mb-4">
          {assistants.map((assistant) => {
            const isSelected = selectedAssistants.includes(assistant.id)
            const logo = getAssistantLogo(assistant.name)
            return (
              <button
                key={assistant.id}
                onClick={() => handleAssistantToggle(assistant.id)}
                className={`
                  flex flex-col items-center gap-1 p-3 rounded-lg border-2
                  transition-all duration-150 cursor-pointer min-w-[80px]
                  ${
                    isSelected
                      ? "border-current"
                      : "border-gray-200 bg-gray-50 hover:bg-gray-100"
                  }
                `}
                style={
                  isSelected
                    ? {
                        backgroundColor: `${accentColor}15`,
                        borderColor: accentColor,
                        color: accentColor,
                      }
                    : undefined
                }
              >
                {/* Checkbox indicator */}
                <div
                  className={`
                    w-4 h-4 rounded border-2 flex items-center justify-center
                    ${
                      isSelected
                        ? "bg-current border-current"
                        : "border-gray-300 bg-white"
                    }
                  `}
                  style={
                    isSelected
                      ? { backgroundColor: accentColor, borderColor: accentColor }
                      : undefined
                  }
                >
                  {isSelected && (
                    <svg
                      className="w-3 h-3 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={3}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  )}
                </div>

                {/* Logo */}
                {logo ? (
                  <img
                    src={logo}
                    alt={assistant.name}
                    className="w-5 h-5"
                  />
                ) : (
                  <span className="w-5 h-5 flex items-center justify-center text-sm font-medium">
                    {assistant.name.charAt(0)}
                  </span>
                )}

                {/* Name */}
                <span
                  className={`text-xs font-medium ${isSelected ? "" : "text-gray-600"}`}
                >
                  {assistant.name}
                </span>
              </button>
            )
          })}
        </div>

        {/* Action buttons */}
        <div className="flex justify-end gap-2">
          <button
            onClick={handleCancel}
            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800
                       hover:bg-gray-100 rounded-md transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleEnable}
            disabled={selectedAssistants.length === 0 || isPending}
            className="px-3 py-1.5 text-sm text-white rounded-md
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
            style={{
              backgroundColor:
                selectedAssistants.length > 0 ? accentColor : "#9CA3AF",
            }}
          >
            {isPending ? "Enabling..." : "Enable"}
          </button>
        </div>
      </div>
    </Popover>
  )
}
