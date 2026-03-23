import { CheckCircle2, XCircle } from "lucide-react"
import type { RichResultCheck } from "@/types/geo-audit"

interface RichResultsCardProps {
  richResults: RichResultCheck
}

export function RichResultsCard({ richResults }: RichResultsCardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="font-['DM_Sans'] font-semibold text-gray-900 mb-3">
        Rich Results Eligibility
      </h3>

      {richResults.eligible.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1.5">Eligible</p>
          <div className="flex flex-wrap gap-1.5">
            {richResults.eligible.map((e) => (
              <span
                key={e}
                className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200"
              >
                <CheckCircle2 className="w-3 h-3" /> {e}
              </span>
            ))}
          </div>
        </div>
      )}

      {richResults.gaps.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Gaps</p>
          {richResults.gaps.map((gap) => (
            <div key={gap.schema_type} className="border-l-2 border-l-gray-300 pl-3 py-1">
              <div className="flex items-center gap-2 mb-1">
                <XCircle className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-sm font-medium text-gray-700">{gap.schema_type}</span>
                <span className="text-xs text-gray-400">{gap.status}</span>
              </div>
              {gap.missing_required.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-1">
                  {gap.missing_required.map((f) => (
                    <span key={f} className="px-1.5 py-0.5 rounded text-xs bg-red-50 text-red-600">
                      {f}
                    </span>
                  ))}
                </div>
              )}
              {gap.missing_recommended.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {gap.missing_recommended.map((f) => (
                    <span key={f} className="px-1.5 py-0.5 rounded text-xs bg-yellow-50 text-yellow-600">
                      {f}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {richResults.eligible.length === 0 && richResults.gaps.length === 0 && (
        <p className="text-sm text-gray-500">No rich result types detected</p>
      )}
    </div>
  )
}
