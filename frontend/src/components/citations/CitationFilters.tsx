/**
 * CitationFilters - Date range picker and assistant filter
 * Uses the new DateRangePicker component with preset buttons and calendar
 */

import { DateRangePicker } from "@/components/ui/date-range-picker"
import type { DateRange } from "@/types/date-range"

type PresetPeriod = "1d" | "7d" | "30d"

interface CitationFiltersProps {
  dateRange: DateRange | null
  activePreset: PresetPeriod | null
  onDateRangeChange: (range: DateRange, preset: string | null) => void
  assistantId: number | undefined
  onAssistantChange: (assistantId: number | undefined) => void
  assistants: { id: number; name: string }[]
  isLoadingAssistants: boolean
}

export function CitationFilters({
  dateRange,
  activePreset,
  onDateRangeChange,
  assistantId,
  onAssistantChange,
  assistants,
  isLoadingAssistants,
}: CitationFiltersProps) {
  return (
    <div className="flex items-center gap-2 flex-shrink-0">
      <DateRangePicker
        value={dateRange}
        onChange={onDateRangeChange}
        activePreset={activePreset}
      />

      <select
        value={assistantId ?? ""}
        onChange={(e) =>
          onAssistantChange(e.target.value ? Number(e.target.value) : undefined)
        }
        disabled={isLoadingAssistants}
        className="text-[10px] h-6 px-2 py-0.5 rounded border bg-white text-gray-600 focus:outline-none focus:ring-1 cursor-pointer disabled:opacity-50"
        style={{ borderColor: "#C4553D30" }}
      >
        <option value="">All assistants</option>
        {assistants.map((a) => (
          <option key={a.id} value={a.id}>
            {a.name}
          </option>
        ))}
      </select>
    </div>
  )
}
