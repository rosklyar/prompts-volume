/**
 * ScheduleToggle - Toggle for enabling/disabling daily scheduled reports
 * Features "Daily" label and tooltip on hover
 */

import { useGroupSchedule, useSetGroupSchedule } from "@/hooks/useGroups"
import { Tooltip } from "@/components/ui/tooltip"

interface ScheduleToggleProps {
  groupId: number
  accentColor: string
}

export function ScheduleToggle({ groupId, accentColor }: ScheduleToggleProps) {
  const { data: schedule, isLoading } = useGroupSchedule(groupId)
  const setScheduleMutation = useSetGroupSchedule()

  const isEnabled = schedule?.enabled ?? false
  const isPending = setScheduleMutation.isPending

  const handleToggle = () => {
    if (isPending || isLoading) return
    setScheduleMutation.mutate({ groupId, enabled: !isEnabled })
  }

  const tooltipContent = (
    <span className="flex items-center gap-2">
      <span>⏰</span>
      <span>
        {isEnabled
          ? "Reports generated daily at 6 AM UTC"
          : "Enable for daily reports at 6 AM UTC"
        }
      </span>
    </span>
  )

  return (
    <Tooltip
      content={tooltipContent}
      side="bottom"
      disabled={isLoading}
    >
      <button
        onClick={handleToggle}
        disabled={isLoading || isPending}
        className={`
          flex items-center gap-1.5 px-2 py-1 rounded-full
          transition-all duration-200 cursor-pointer
          border
          disabled:opacity-50 disabled:cursor-not-allowed
          ${isPending ? "animate-pulse" : ""}
          ${isEnabled
            ? "border-transparent"
            : "border-gray-300 bg-gray-50 hover:bg-gray-100"
          }
        `}
        style={isEnabled ? {
          backgroundColor: `${accentColor}15`,
          borderColor: `${accentColor}40`,
        } : undefined}
        aria-label={isEnabled ? "Disable daily schedule" : "Enable daily schedule"}
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
      </button>
    </Tooltip>
  )
}
