import { Check, X } from "lucide-react"
import { Tooltip } from "@/components/ui/tooltip"
import type { GeoReadiness } from "@/types/geo-audit"

interface GeoReadinessCardProps {
  geoReadiness: GeoReadiness
}

export function GeoReadinessCard({ geoReadiness }: GeoReadinessCardProps) {
  const overallPct = Math.round(geoReadiness.overall_readiness * 100)

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-['DM_Sans'] font-semibold text-gray-900">GEO Readiness</h3>
        <span className="text-sm font-semibold text-gray-700">{overallPct}%</span>
      </div>

      {/* Overall readiness bar */}
      <div className="h-2 rounded-full bg-gray-100 mb-4">
        <div
          className="h-2 rounded-full bg-[#C4553D] transition-all"
          style={{ width: `${overallPct}%` }}
        />
      </div>

      {/* Signals */}
      <div className="space-y-2.5 mb-4">
        {geoReadiness.signals.map((signal) => (
          <div key={signal.name} className="flex items-center gap-2.5">
            {signal.present ? (
              <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
            ) : (
              <X className="w-4 h-4 text-red-400 flex-shrink-0" />
            )}
            <span className="text-sm text-gray-700 w-36 flex-shrink-0 truncate">{signal.name}</span>
            <div className="flex-1 h-1.5 rounded-full bg-gray-100">
              <div
                className={`h-1.5 rounded-full ${signal.present ? "bg-green-500" : "bg-gray-300"}`}
                style={{ width: `${Math.round(signal.completeness * 100)}%` }}
              />
            </div>
            <span className="text-xs text-gray-400 w-8 text-right">
              {Math.round(signal.completeness * 100)}%
            </span>
          </div>
        ))}
      </div>

      {/* SameAs links */}
      {geoReadiness.same_as_links.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">SameAs Links</p>
          <div className="flex flex-wrap gap-1.5">
            {geoReadiness.same_as_links.map((link) => (
              <Tooltip
                key={link.platform}
                content={link.url ?? `${link.platform} not linked`}
              >
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium border cursor-default ${
                    link.linked
                      ? "bg-[#C4553D]/10 text-[#C4553D] border-[#C4553D]/30"
                      : "bg-gray-50 text-gray-400 border-gray-200"
                  }`}
                >
                  {link.linked ? <Check className="w-3 h-3 inline mr-0.5" /> : null}
                  {link.platform}
                </span>
              </Tooltip>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
