import { AlertTriangle, CheckCircle2 } from "lucide-react"
import type { JsRenderingWarning } from "@/types/geo-audit"

interface JsWarningsCardProps {
  warnings: JsRenderingWarning[]
}

export function JsWarningsCard({ warnings }: JsWarningsCardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="font-['DM_Sans'] font-semibold text-gray-900 mb-3">
        JS Rendering Warnings
      </h3>

      {warnings.length === 0 ? (
        <p className="text-sm text-green-600 flex items-center gap-1.5">
          <CheckCircle2 className="w-4 h-4" /> No JS rendering issues detected
        </p>
      ) : (
        <div className="space-y-2">
          {warnings.map((w, i) => (
            <div
              key={i}
              className="flex items-start gap-2 border-l-2 border-l-orange-400 pl-3 py-1.5"
            >
              <AlertTriangle className="w-4 h-4 text-orange-500 mt-0.5 flex-shrink-0" />
              <div>
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-medium text-gray-700">{w.framework}</span>
                  <span className="text-xs text-orange-600 bg-orange-50 px-1.5 py-0.5 rounded">
                    {w.confidence}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{w.message}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
