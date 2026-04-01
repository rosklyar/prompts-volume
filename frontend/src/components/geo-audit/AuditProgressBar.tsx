import type { GeoAuditProgressResponse } from "@/types/geo-audit"

const STATUS_LABELS: Record<string, string> = {
  pending: "Starting audit...",
  discovering: "Discovering pages...",
  auditing: "Auditing pages...",
  completed: "Audit complete",
  failed: "Audit failed",
}

interface AuditProgressBarProps {
  progress: GeoAuditProgressResponse
}

export function AuditProgressBar({ progress }: AuditProgressBarProps) {
  const { status, pages_discovered, pages_audited, pages_total } = progress

  const pct = pages_total > 0 ? Math.round((pages_audited / pages_total) * 100) : 0
  const label = STATUS_LABELS[status] ?? status

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-gray-700">{label}</p>
        {status === "discovering" && (
          <p className="text-xs text-gray-400">{pages_discovered} pages found</p>
        )}
        {status === "auditing" && (
          <p className="text-xs text-gray-400">
            {pages_audited} / {pages_total} pages
          </p>
        )}
      </div>

      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            status === "failed" ? "bg-red-500" : "bg-[#C4553D]"
          }`}
          style={{
            width:
              status === "pending"
                ? "5%"
                : status === "discovering"
                  ? "15%"
                  : status === "completed"
                    ? "100%"
                    : `${Math.max(20, pct)}%`,
          }}
        />
      </div>

      {status === "failed" && progress.error_message && (
        <p className="text-xs text-red-600 mt-2">{progress.error_message}</p>
      )}

      <p className="text-xs text-gray-400 mt-2 font-mono truncate">{progress.url}</p>
    </div>
  )
}
