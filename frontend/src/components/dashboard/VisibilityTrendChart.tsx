/**
 * VisibilityTrendChart - Line chart showing brand visibility over time
 * Uses Recharts with one line per brand (target + competitors)
 */

import { useState, useEffect, useMemo } from "react"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts"
import type { TimelineDataPoint } from "@/types/dashboard"

const SHOW_COMPETITORS_KEY = "show_competitor_trends"

function loadShowCompetitors(): boolean {
  try {
    const saved = localStorage.getItem(SHOW_COMPETITORS_KEY)
    if (saved === null) return true
    return saved === "true"
  } catch {
    return true
  }
}

function saveShowCompetitors(value: boolean): void {
  try {
    localStorage.setItem(SHOW_COMPETITORS_KEY, String(value))
  } catch {
    // localStorage unavailable
  }
}

interface BrandKey {
  name: string
  isTarget: boolean
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{ dataKey?: string | number; value?: number }>
  label?: string
  brandKeys: BrandKey[]
  colorMap: Map<string, string>
}

function CustomTooltip({
  active,
  payload,
  label,
  brandKeys,
  colorMap,
}: CustomTooltipProps) {
  if (!active || !payload?.length) return null

  const targetName = brandKeys.find((b) => b.isTarget)?.name
  const sorted = [...payload].sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
  // Move target brand to top regardless of value
  const targetIdx = sorted.findIndex((p) => p.dataKey === targetName)
  if (targetIdx > 0) {
    const [target] = sorted.splice(targetIdx, 1)
    sorted.unshift(target)
  }

  return (
    <div
      className="rounded-lg bg-white"
      style={{
        border: "1px solid #F3F4F6",
        boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
        padding: "10px 14px",
      }}
    >
      <p className="font-['Fraunces'] text-xs text-[#9CA3AF] mb-1">{label}</p>
      <div className="border-t border-[#F3F4F6] pt-1.5 flex flex-col gap-1.5">
        {sorted.map((entry) => {
          const isTarget = entry.dataKey === targetName
          const color = colorMap.get(entry.dataKey as string) ?? "#6B7280"
          return (
            <div key={entry.dataKey} className="flex items-center justify-between gap-4 text-xs">
              <span className="flex items-center gap-1.5">
                <span
                  className="inline-block w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span className={isTarget ? "font-semibold text-[#1E1E1E]" : "text-[#6B7280]"}>
                  {entry.dataKey}
                </span>
              </span>
              <span
                className={isTarget ? "font-semibold text-[#1E1E1E]" : "text-[#6B7280]"}
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {((entry.value as number) ?? 0).toFixed(1)}%
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface VisibilityTrendChartProps {
  timeline: TimelineDataPoint[]
  hasData: boolean
  colorMap: Map<string, string>
  className?: string
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

export function VisibilityTrendChart({ timeline, hasData, colorMap, className = "" }: VisibilityTrendChartProps) {
  const [showCompetitors, setShowCompetitors] = useState(loadShowCompetitors)

  useEffect(() => {
    saveShowCompetitors(showCompetitors)
  }, [showCompetitors])

  // Transform timeline into flat rows for Recharts: { date, brandA: 45, brandB: 20, ... }
  const { chartData, brandKeys, yAxisMax } = useMemo(() => {
    if (timeline.length < 2) return { chartData: [], brandKeys: [], yAxisMax: 10 }

    const keys = new Map<string, { isTarget: boolean; index: number }>()

    const rows = timeline.map((point) => {
      const row: Record<string, string | number> = {
        date: formatDate(point.timestamp),
      }
      for (const brand of point.brands) {
        row[brand.name] = brand.visibility_percent
        if (!keys.has(brand.name)) {
          keys.set(brand.name, {
            isTarget: brand.is_target_brand,
            index: keys.size,
          })
        }
      }
      return row
    })

    // Target brand first, then competitors
    const sorted = [...keys.entries()].sort((a, b) => {
      if (a[1].isTarget && !b[1].isTarget) return -1
      if (!a[1].isTarget && b[1].isTarget) return 1
      return a[1].index - b[1].index
    })

    const maxValue = Math.max(
      0,
      ...rows.flatMap(row =>
        [...keys.keys()].map(name => (row[name] as number) || 0)
      )
    )
    const computedMax = maxValue <= 0 ? 10
      : Math.min(100, Math.ceil((maxValue * 1.05) / 5) * 5)

    return {
      chartData: rows,
      brandKeys: sorted.map(([name, meta]) => ({
        name,
        isTarget: meta.isTarget,
      })),
      yAxisMax: computedMax,
    }
  }, [timeline])

  const hasCompetitors = brandKeys.some((b) => !b.isTarget)
  const visibleBrandKeys = showCompetitors
    ? brandKeys
    : brandKeys.filter((b) => b.isTarget)

  if (!hasData || timeline.length < 2) {
    return (
      <div className={`bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full flex flex-col ${className}`}>
        <h3 className="font-['Fraunces'] text-sm font-semibold text-[#1E1E1E] shrink-0">
          VISIBILITY TREND
        </h3>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-xs text-[#9CA3AF]">
            Need at least 2 reports to show trend
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full flex flex-col ${className}`}>
      <div className="flex items-center justify-between mb-4 shrink-0">
        <h3 className="font-['Fraunces'] text-sm font-semibold text-[#1E1E1E]">
          VISIBILITY TREND
        </h3>
        {hasCompetitors && (
          <button
            onClick={() => setShowCompetitors((prev) => !prev)}
            className="flex items-center gap-1.5 text-[10px] text-[#9CA3AF] hover:text-[#6B7280] transition-colors"
          >
            <span
              className={`relative inline-flex h-3.5 w-7 items-center rounded-full transition-colors ${
                showCompetitors ? "bg-[#C4553D]" : "bg-[#D1D5DB]"
              }`}
            >
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full bg-white transition-transform ${
                  showCompetitors ? "translate-x-3.5" : "translate-x-0.5"
                }`}
              />
            </span>
            Competitors
          </button>
        )}
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: "#9CA3AF" }}
              axisLine={{ stroke: "#F3F4F6" }}
              tickLine={false}
            />
            <YAxis
              domain={[0, yAxisMax]}
              tick={{ fontSize: 10, fill: "#9CA3AF" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `${v}%`}
            />
            <Tooltip
              content={<CustomTooltip brandKeys={visibleBrandKeys} colorMap={colorMap} />}
            />
            <Legend
              verticalAlign="top"
              align="right"
              iconSize={8}
              wrapperStyle={{ fontSize: 10, paddingBottom: 8 }}
            />
            {visibleBrandKeys.map((brand) => {
              const isTarget = brand.isTarget
              const color = colorMap.get(brand.name) ?? "#6B7280"
              return (
                <Line
                  key={brand.name}
                  type="monotone"
                  dataKey={brand.name}
                  stroke={color}
                  strokeWidth={isTarget ? 2.5 : 1.5}
                  strokeDasharray={isTarget ? undefined : "4 3"}
                  dot={false}
                  activeDot={{ r: 3, strokeWidth: 0 }}
                />
              )
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
