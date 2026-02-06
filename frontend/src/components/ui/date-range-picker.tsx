/**
 * DateRangePicker - Compact date range selector with presets and custom calendar
 * Matches existing filter styling (h-6, text-[10px], #C4553D30 border)
 */

import { useState, useMemo } from "react"
import { ChevronLeft, ChevronRight, Calendar } from "lucide-react"
import { cn } from "@/lib/utils"
import { Popover } from "./popover"
import {
  DEFAULT_PRESETS,
  type DateRange,
  type DateRangePreset,
} from "@/types/date-range"

interface DateRangePickerProps {
  value: DateRange | null
  onChange: (range: DateRange, preset: string | null) => void
  presets?: DateRangePreset[]
  /** Currently active preset value (e.g., "7d") */
  activePreset?: string | null
  className?: string
}

// Date utilities
function startOfDay(date: Date): Date {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  return d
}

function endOfDay(date: Date): Date {
  const d = new Date(date)
  d.setHours(23, 59, 59, 999)
  return d
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

function subDays(date: Date, days: number): Date {
  return addDays(date, -days)
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function isWithinInterval(date: Date, start: Date, end: Date): boolean {
  const d = date.getTime()
  return d >= start.getTime() && d <= end.getTime()
}

function formatShortDate(date: Date): string {
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  })
}

function formatMonthYear(date: Date): string {
  return date.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  })
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 1).getDay()
}

// Mini Calendar component
function MiniCalendar({
  selectedRange,
  onSelectDate,
  selectionStart,
}: {
  selectedRange: DateRange | null
  onSelectDate: (date: Date) => void
  selectionStart: Date | null
}) {
  const [viewDate, setViewDate] = useState(() => new Date())

  const year = viewDate.getFullYear()
  const month = viewDate.getMonth()
  const daysInMonth = getDaysInMonth(year, month)
  const firstDayOfMonth = getFirstDayOfMonth(year, month)

  const prevMonth = () => {
    setViewDate(new Date(year, month - 1, 1))
  }

  const nextMonth = () => {
    setViewDate(new Date(year, month + 1, 1))
  }

  const today = startOfDay(new Date())

  const days = useMemo(() => {
    const result: (Date | null)[] = []
    // Empty slots before first day
    for (let i = 0; i < firstDayOfMonth; i++) {
      result.push(null)
    }
    // Days of month
    for (let i = 1; i <= daysInMonth; i++) {
      result.push(new Date(year, month, i))
    }
    return result
  }, [year, month, daysInMonth, firstDayOfMonth])

  const isInRange = (date: Date): boolean => {
    if (!selectedRange) return false
    return isWithinInterval(date, startOfDay(selectedRange.from), endOfDay(selectedRange.to))
  }

  const isRangeStart = (date: Date): boolean => {
    if (!selectedRange) return false
    return isSameDay(date, selectedRange.from)
  }

  const isRangeEnd = (date: Date): boolean => {
    if (!selectedRange) return false
    return isSameDay(date, selectedRange.to)
  }

  const isSelectionStart = (date: Date): boolean => {
    if (!selectionStart) return false
    return isSameDay(date, selectionStart)
  }

  return (
    <div className="w-[240px]">
      {/* Month navigation */}
      <div className="flex items-center justify-between mb-2">
        <button
          type="button"
          onClick={prevMonth}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
        >
          <ChevronLeft className="w-4 h-4 text-gray-500" />
        </button>
        <span className="text-xs font-medium text-gray-700">
          {formatMonthYear(viewDate)}
        </span>
        <button
          type="button"
          onClick={nextMonth}
          className="p-1 hover:bg-gray-100 rounded transition-colors"
        >
          <ChevronRight className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 gap-0 mb-1">
        {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((day) => (
          <div
            key={day}
            className="text-center text-[9px] font-medium text-gray-400 py-1"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Days grid */}
      <div className="grid grid-cols-7 gap-0">
        {days.map((date, idx) => {
          if (!date) {
            return <div key={`empty-${idx}`} className="h-7" />
          }

          const isToday = isSameDay(date, today)
          const inRange = isInRange(date)
          const isStart = isRangeStart(date)
          const isEnd = isRangeEnd(date)
          const isSelectStart = isSelectionStart(date)
          const isFuture = date > today

          return (
            <button
              key={date.toISOString()}
              type="button"
              disabled={isFuture}
              onClick={() => onSelectDate(date)}
              className={cn(
                "h-7 text-[10px] relative transition-colors",
                "hover:bg-[#C4553D15] disabled:opacity-40 disabled:cursor-not-allowed",
                // Range styling
                inRange && !isStart && !isEnd && "bg-[#C4553D10]",
                (isStart || isEnd) && "bg-[#C4553D] text-white",
                isStart && "rounded-l",
                isEnd && "rounded-r",
                isSelectStart && !inRange && "ring-1 ring-[#C4553D] rounded",
                // Today indicator
                isToday && !inRange && "font-semibold text-[#C4553D]",
                // Default text
                !inRange && !isToday && "text-gray-700"
              )}
            >
              {date.getDate()}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function DateRangePicker({
  value,
  onChange,
  presets = DEFAULT_PRESETS,
  activePreset,
  className,
}: DateRangePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectionStart, setSelectionStart] = useState<Date | null>(null)

  const handlePresetClick = (preset: DateRangePreset) => {
    const now = new Date()
    const from = subDays(startOfDay(now), preset.days - 1)
    const to = endOfDay(now)
    onChange({ from, to }, preset.value)
  }

  const handleDateSelect = (date: Date) => {
    if (!selectionStart) {
      // First click: start selection
      setSelectionStart(date)
    } else {
      // Second click: complete selection
      const from = date < selectionStart ? date : selectionStart
      const to = date > selectionStart ? date : selectionStart
      onChange({ from: startOfDay(from), to: endOfDay(to) }, null)
      setSelectionStart(null)
      setIsOpen(false)
    }
  }

  // Format display text
  const displayText = useMemo(() => {
    if (activePreset) {
      const preset = presets.find((p) => p.value === activePreset)
      if (preset) return `Last ${preset.label}`
    }
    if (value) {
      return `${formatShortDate(value.from)} - ${formatShortDate(value.to)}`
    }
    return "Select dates"
  }, [value, activePreset, presets])

  const trigger = (
    <button
      type="button"
      onClick={() => setIsOpen(!isOpen)}
      className={cn(
        "text-[10px] h-6 px-2 py-0.5 rounded border bg-white text-gray-600",
        "focus:outline-none focus:ring-1 cursor-pointer",
        "flex items-center gap-1.5 min-w-[100px]",
        className
      )}
      style={{ borderColor: "#C4553D30" }}
    >
      <Calendar className="w-3 h-3 text-gray-400 flex-shrink-0" />
      <span className="truncate">{displayText}</span>
    </button>
  )

  return (
    <Popover
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={trigger}
      side="bottom"
      align="end"
    >
      <div className="p-3">
        {/* Preset buttons */}
        <div className="flex gap-1 mb-3">
          {presets.map((preset) => (
            <button
              key={preset.value}
              type="button"
              onClick={() => handlePresetClick(preset)}
              className={cn(
                "px-2 py-1 text-[10px] rounded border transition-colors",
                activePreset === preset.value
                  ? "bg-[#C4553D] text-white border-[#C4553D]"
                  : "bg-white text-gray-600 border-[#C4553D30] hover:bg-[#C4553D10]"
              )}
            >
              {preset.label}
            </button>
          ))}
        </div>

        {/* Divider */}
        <div className="border-t border-gray-100 mb-3" />

        {/* Calendar */}
        <MiniCalendar
          selectedRange={value}
          onSelectDate={handleDateSelect}
          selectionStart={selectionStart}
        />

        {/* Selection hint */}
        {selectionStart && (
          <p className="text-[9px] text-gray-400 mt-2 text-center">
            Click another date to complete range
          </p>
        )}
      </div>
    </Popover>
  )
}
