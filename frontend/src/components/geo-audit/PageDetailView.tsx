import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { PageAuditResult } from "@/types/geo-audit"
import { ExtractionCard } from "./ExtractionCard"
import { ValidationCard } from "./ValidationCard"
import { RichResultsCard } from "./RichResultsCard"
import { GeoReadinessCard } from "./GeoReadinessCard"
import { DeprecatedSchemasCard } from "./DeprecatedSchemasCard"
import { JsWarningsCard } from "./JsWarningsCard"
import { ScoreBreakdownCard } from "./ScoreBreakdownCard"

interface PageDetailViewProps {
  pageUrl: string
  result: PageAuditResult
  onBack: () => void
}

export function PageDetailView({ pageUrl, result, onBack }: PageDetailViewProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack} className="gap-1.5">
          <ArrowLeft className="w-4 h-4" />
          Back
        </Button>
        <p className="text-sm text-gray-500 font-mono truncate">{pageUrl}</p>
        <span className="text-xs font-medium text-gray-400 flex-shrink-0">
          {Math.round(result.score.total)}/100
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ExtractionCard extraction={result.extraction} />
        <ValidationCard validation={result.validation} />
        <RichResultsCard richResults={result.rich_results} />
        <GeoReadinessCard geoReadiness={result.geo_readiness} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DeprecatedSchemasCard deprecatedSchemas={result.deprecated_schemas} />
        <JsWarningsCard warnings={result.js_rendering_warnings} />
      </div>

      <ScoreBreakdownCard breakdown={result.score.breakdown} />
    </div>
  )
}
