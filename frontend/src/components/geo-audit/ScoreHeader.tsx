import { RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { ScoreRating } from "@/types/geo-audit"

const RATING_COLORS: Record<ScoreRating, string> = {
  Critical: "text-red-600 bg-red-50 border-red-200",
  Poor: "text-orange-600 bg-orange-50 border-orange-200",
  Fair: "text-yellow-600 bg-yellow-50 border-yellow-200",
  Good: "text-green-600 bg-green-50 border-green-200",
  Excellent: "text-emerald-600 bg-emerald-50 border-emerald-200",
}

const SCORE_RING_COLORS: Record<ScoreRating, string> = {
  Critical: "#dc2626",
  Poor: "#ea580c",
  Fair: "#ca8a04",
  Good: "#16a34a",
  Excellent: "#059669",
}

interface ScoreHeaderAudit {
  url: string
  score_total: number | null
  score_rating: string | null
  created_at: string
}

interface ScoreHeaderProps {
  audit: ScoreHeaderAudit
  onRerun: () => void
  isRerunning: boolean
  cooldownSeconds: number | null
  pageCount?: number
}

export function ScoreHeader({ audit, onRerun, isRerunning, cooldownSeconds, pageCount }: ScoreHeaderProps) {
  if (audit.score_total === null || !audit.score_rating) return null

  const rating = audit.score_rating as ScoreRating
  const ringColor = SCORE_RING_COLORS[rating]
  const pct = Math.round(audit.score_total)
  const conicGradient = `conic-gradient(${ringColor} ${pct * 3.6}deg, #e5e7eb ${pct * 3.6}deg)`

  const auditDate = new Date(audit.created_at)
  const relativeTime = formatRelative(auditDate)

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 flex items-center gap-8">
      {/* Score ring */}
      <div
        className="relative w-28 h-28 rounded-full flex-shrink-0"
        style={{ background: conicGradient }}
      >
        <div className="absolute inset-2 bg-white rounded-full flex items-center justify-center">
          <span className="text-3xl font-bold font-['DM_Sans']" style={{ color: ringColor }}>
            {pct}
          </span>
        </div>
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 mb-1">
          <span
            className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${RATING_COLORS[rating]}`}
          >
            {rating}
          </span>
          <span className="text-sm text-gray-400">{relativeTime}</span>
        </div>
        <p className="text-sm text-gray-500 truncate font-mono">{audit.url}</p>
        {pageCount !== undefined && pageCount > 0 && (
          <p className="text-xs text-gray-400">{pageCount} pages audited</p>
        )}
      </div>

      {/* Re-run button */}
      <Button
        variant="outline"
        size="sm"
        onClick={onRerun}
        disabled={isRerunning || cooldownSeconds !== null}
        className="flex-shrink-0 gap-2"
      >
        <RefreshCw className={`w-4 h-4 ${isRerunning ? "animate-spin" : ""}`} />
        {cooldownSeconds !== null
          ? `${cooldownSeconds}s`
          : isRerunning
            ? "Running..."
            : "Re-run"}
      </Button>
    </div>
  )
}

function formatRelative(date: Date): string {
  const now = Date.now()
  const diff = now - date.getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}
