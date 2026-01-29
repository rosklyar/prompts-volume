/**
 * CitationFilters - Period and assistant filter dropdowns
 * Matches the existing ReportHistoryPanel filter styling
 */

interface CitationFiltersProps {
  period: "1d" | "7d" | "30d"
  onPeriodChange: (period: "1d" | "7d" | "30d") => void
  assistantId: number | undefined
  onAssistantChange: (assistantId: number | undefined) => void
  assistants: { id: number; name: string }[]
  isLoadingAssistants: boolean
}

const PERIOD_OPTIONS: { value: "1d" | "7d" | "30d"; label: string }[] = [
  { value: "1d", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
]

export function CitationFilters({
  period,
  onPeriodChange,
  assistantId,
  onAssistantChange,
  assistants,
  isLoadingAssistants,
}: CitationFiltersProps) {
  return (
    <div className="flex items-center gap-2 flex-shrink-0">
      <select
        value={period}
        onChange={(e) => onPeriodChange(e.target.value as "1d" | "7d" | "30d")}
        className="text-[10px] h-6 px-2 py-0.5 rounded border bg-white text-gray-600 focus:outline-none focus:ring-1 cursor-pointer"
        style={{ borderColor: "#C4553D30" }}
      >
        {PERIOD_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

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
