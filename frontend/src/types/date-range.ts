/**
 * Date range picker types and presets
 */

export interface DateRange {
  from: Date
  to: Date
}

export interface DateRangePreset {
  label: string
  value: string
  days: number
}

export const DEFAULT_PRESETS: DateRangePreset[] = [
  { label: "24h", value: "1d", days: 1 },
  { label: "7d", value: "7d", days: 7 },
  { label: "30d", value: "30d", days: 30 },
]
