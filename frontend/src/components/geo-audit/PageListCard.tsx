import type { PageSummary } from "@/types/geo-audit"

const RATING_DOT_COLORS: Record<string, string> = {
  Critical: "bg-red-500",
  Poor: "bg-orange-500",
  Fair: "bg-yellow-500",
  Good: "bg-green-500",
  Excellent: "bg-emerald-500",
}

interface PageListCardProps {
  pages: PageSummary[]
  onPageClick: (page: PageSummary) => void
}

export function PageListCard({ pages, onPageClick }: PageListCardProps) {
  if (pages.length === 0) return null

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Audited Pages ({pages.length})
      </h3>
      <div className="space-y-1">
        {pages.map((page, idx) => (
          <button
            key={idx}
            onClick={() => onPageClick(page)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-gray-50 transition-colors text-left"
          >
            <span
              className={`w-2 h-2 rounded-full flex-shrink-0 ${RATING_DOT_COLORS[page.score_rating] ?? "bg-gray-300"}`}
            />
            <span className="text-sm text-gray-600 truncate flex-1 font-mono">
              {formatPageUrl(page.url)}
            </span>
            <span className="text-xs font-medium text-gray-500 flex-shrink-0">
              {Math.round(page.score_total)}/100
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

function formatPageUrl(url: string): string {
  try {
    const parsed = new URL(url)
    return parsed.pathname === "/" ? parsed.hostname : parsed.pathname
  } catch {
    return url
  }
}
