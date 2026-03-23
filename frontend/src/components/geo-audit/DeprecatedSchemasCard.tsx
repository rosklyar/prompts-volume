import { AlertTriangle, CheckCircle2 } from "lucide-react"
import type { DeprecatedSchema } from "@/types/geo-audit"

interface DeprecatedSchemasCardProps {
  deprecatedSchemas: DeprecatedSchema[]
}

export function DeprecatedSchemasCard({ deprecatedSchemas }: DeprecatedSchemasCardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="font-['DM_Sans'] font-semibold text-gray-900 mb-3">Deprecated Schemas</h3>

      {deprecatedSchemas.length === 0 ? (
        <p className="text-sm text-green-600 flex items-center gap-1.5">
          <CheckCircle2 className="w-4 h-4" /> No deprecated schemas found
        </p>
      ) : (
        <div className="space-y-2">
          {deprecatedSchemas.map((d, i) => (
            <div
              key={i}
              className="flex items-start gap-2 border-l-2 border-l-yellow-500 pl-3 py-1.5"
            >
              <AlertTriangle className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
              <div>
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-medium text-gray-700">{d.schema_type}</span>
                  <span className="text-xs text-yellow-600 bg-yellow-50 px-1.5 py-0.5 rounded">
                    {d.status}
                  </span>
                </div>
                <p className="text-sm text-gray-600">{d.message}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
