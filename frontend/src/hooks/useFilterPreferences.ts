/**
 * Hook for persisting filter preferences (time period, assistant) in sessionStorage.
 * Shared across Dashboard and Sources tabs.
 */

import { useState, useEffect, useCallback } from "react"
import type { DashboardPeriod } from "@/types/dashboard"
import type { DateRange } from "@/types/date-range"

const STORAGE_KEY = "filter_preferences"

interface StoredPreferences {
  activePreset: DashboardPeriod | null
  dateRange: { from: string; to: string } | null
  assistantId: number | undefined
}

interface FilterPreferences {
  activePreset: DashboardPeriod | null
  dateRange: DateRange | null
  assistantId: number | undefined
  setActivePreset: (preset: DashboardPeriod | null) => void
  setDateRange: (range: DateRange | null) => void
  setAssistantId: (id: number | undefined) => void
  handleDateRangeChange: (range: DateRange, preset: string | null) => void
}

const VALID_PRESETS: DashboardPeriod[] = ["1d", "7d", "30d"]

function isValidPreset(value: unknown): value is DashboardPeriod {
  return typeof value === "string" && VALID_PRESETS.includes(value as DashboardPeriod)
}

function parseStoredDateRange(stored: { from: string; to: string } | null): DateRange | null {
  if (!stored) return null
  try {
    const from = new Date(stored.from)
    const to = new Date(stored.to)
    if (isNaN(from.getTime()) || isNaN(to.getTime())) return null
    return { from, to }
  } catch {
    return null
  }
}

function loadPreferences(): { activePreset: DashboardPeriod | null; dateRange: DateRange | null; assistantId: number | undefined } {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY)
    if (!stored) {
      return { activePreset: "30d", dateRange: null, assistantId: undefined }
    }
    const parsed: StoredPreferences = JSON.parse(stored)

    const activePreset = isValidPreset(parsed.activePreset) ? parsed.activePreset : "30d"
    const dateRange = parseStoredDateRange(parsed.dateRange)
    const assistantId = typeof parsed.assistantId === "number" ? parsed.assistantId : undefined

    return { activePreset, dateRange, assistantId }
  } catch {
    return { activePreset: "30d", dateRange: null, assistantId: undefined }
  }
}

function savePreferences(prefs: StoredPreferences): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  } catch {
    // sessionStorage unavailable - silently ignore
  }
}

export function useFilterPreferences(): FilterPreferences {
  const [state, setState] = useState(() => loadPreferences())

  // Persist to sessionStorage on every change
  useEffect(() => {
    const stored: StoredPreferences = {
      activePreset: state.activePreset,
      dateRange: state.dateRange
        ? { from: state.dateRange.from.toISOString(), to: state.dateRange.to.toISOString() }
        : null,
      assistantId: state.assistantId,
    }
    savePreferences(stored)
  }, [state.activePreset, state.dateRange, state.assistantId])

  const setActivePreset = useCallback((preset: DashboardPeriod | null) => {
    setState(prev => ({ ...prev, activePreset: preset }))
  }, [])

  const setDateRange = useCallback((range: DateRange | null) => {
    setState(prev => ({ ...prev, dateRange: range }))
  }, [])

  const setAssistantId = useCallback((id: number | undefined) => {
    setState(prev => ({ ...prev, assistantId: id }))
  }, [])

  const handleDateRangeChange = useCallback((range: DateRange, preset: string | null) => {
    setState(prev => ({
      ...prev,
      dateRange: range,
      activePreset: preset as DashboardPeriod | null,
    }))
  }, [])

  return {
    activePreset: state.activePreset,
    dateRange: state.dateRange,
    assistantId: state.assistantId,
    setActivePreset,
    setDateRange,
    setAssistantId,
    handleDateRangeChange,
  }
}
