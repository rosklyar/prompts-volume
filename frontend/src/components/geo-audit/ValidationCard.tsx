import { AlertTriangle, CheckCircle2, Info } from "lucide-react"
import type { ValidationResult } from "@/types/geo-audit"

const SEVERITY_STYLES: Record<string, { border: string; icon: typeof AlertTriangle; color: string }> = {
  error: { border: "border-l-red-500", icon: AlertTriangle, color: "text-red-500" },
  warning: { border: "border-l-yellow-500", icon: AlertTriangle, color: "text-yellow-500" },
  info: { border: "border-l-blue-500", icon: Info, color: "text-blue-500" },
}

interface ValidationCardProps {
  validation: ValidationResult
}

export function ValidationCard({ validation }: ValidationCardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="font-['DM_Sans'] font-semibold text-gray-900 mb-3">Schema Validation</h3>

      <div className="flex gap-4 mb-3">
        <div className="flex items-center gap-1.5 text-sm">
          <CheckCircle2 className="w-4 h-4 text-green-500" />
          <span className="text-gray-700">{validation.valid_count} valid</span>
        </div>
        {validation.invalid_count > 0 && (
          <div className="flex items-center gap-1.5 text-sm">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <span className="text-gray-700">{validation.invalid_count} invalid</span>
          </div>
        )}
      </div>

      {validation.issues.length > 0 && (
        <div className="space-y-2">
          {validation.issues.map((issue, i) => {
            const style = SEVERITY_STYLES[issue.severity] ?? SEVERITY_STYLES.info
            const Icon = style.icon
            return (
              <div key={i} className={`border-l-2 ${style.border} pl-3 py-1.5`}>
                <div className="flex items-center gap-2 mb-0.5">
                  <Icon className={`w-3.5 h-3.5 ${style.color}`} />
                  <span className="text-xs font-medium text-gray-500">{issue.schema_type}</span>
                  {issue.field && (
                    <span className="text-xs font-mono text-gray-400">{issue.field}</span>
                  )}
                </div>
                <p className="text-sm text-gray-700">{issue.message}</p>
              </div>
            )
          })}
        </div>
      )}

      {validation.issues.length === 0 && (
        <p className="text-sm text-green-600 flex items-center gap-1.5">
          <CheckCircle2 className="w-4 h-4" /> All schemas valid
        </p>
      )}
    </div>
  )
}
