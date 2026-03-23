import type { ScoreBreakdown } from "@/types/geo-audit"

interface ScoreBreakdownCardProps {
  breakdown: ScoreBreakdown[]
}

function barColor(pct: number): string {
  if (pct >= 75) return "bg-green-500"
  if (pct >= 50) return "bg-yellow-500"
  return "bg-red-500"
}

export function ScoreBreakdownCard({ breakdown }: ScoreBreakdownCardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="font-['DM_Sans'] font-semibold text-gray-900 mb-4">Score Breakdown</h3>

      <div className="space-y-3">
        {breakdown.map((b) => {
          const pct = b.max_points > 0 ? (b.earned_points / b.max_points) * 100 : 0
          return (
            <div key={b.component}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-700">{b.component}</span>
                <span className="text-xs text-gray-500">
                  {b.earned_points}/{b.max_points}
                </span>
              </div>
              <div className="h-2 rounded-full bg-gray-100">
                <div
                  className={`h-2 rounded-full transition-all ${barColor(pct)}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
