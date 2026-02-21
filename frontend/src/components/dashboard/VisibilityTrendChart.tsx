/**
 * VisibilityTrendChart - Line chart showing brand visibility over time
 * Uses Recharts with one line per brand (target + competitors)
 */

import { useMemo } from "react"
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
      <h3 className="font-['Fraunces'] text-sm font-semibold text-[#1E1E1E] mb-4 shrink-0">
        VISIBILITY TREND
      </h3>
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
              contentStyle={{
                fontSize: 11,
                borderRadius: 8,
                border: "1px solid #F3F4F6",
                boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
              }}
              formatter={(value: number | undefined) => [`${(value ?? 0).toFixed(1)}%`]}
            />
            <Legend
              verticalAlign="top"
              align="right"
              iconSize={8}
              wrapperStyle={{ fontSize: 10, paddingBottom: 8 }}
            />
            {brandKeys.map((brand) => {
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
