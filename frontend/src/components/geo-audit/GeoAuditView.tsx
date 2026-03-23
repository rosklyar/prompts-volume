import { useEffect, useRef, useState } from "react"
import { useLatestGeoAudit, useRunGeoAudit } from "@/hooks/useGeoAudit"
import { ApiError } from "@/client/api"
import { ScoreHeader } from "./ScoreHeader"
import { ExtractionCard } from "./ExtractionCard"
import { ValidationCard } from "./ValidationCard"
import { RichResultsCard } from "./RichResultsCard"
import { GeoReadinessCard } from "./GeoReadinessCard"
import { DeprecatedSchemasCard } from "./DeprecatedSchemasCard"
import { JsWarningsCard } from "./JsWarningsCard"
import { TemplatesCard } from "./TemplatesCard"
import { ScoreBreakdownCard } from "./ScoreBreakdownCard"
import type { GeoAuditStoredResponse } from "@/types/geo-audit"

export function GeoAuditView() {
  const latestQuery = useLatestGeoAudit()
  const runAudit = useRunGeoAudit()
  const [cooldownSeconds, setCooldownSeconds] = useState<number | null>(null)
  const autoTriggered = useRef(false)

  // Auto-trigger on first visit when no prior audit exists
  useEffect(() => {
    if (autoTriggered.current) return
    if (latestQuery.isLoading) return

    const is404 =
      latestQuery.isError &&
      latestQuery.error instanceof ApiError &&
      latestQuery.error.status === 404

    if (is404 && runAudit.isIdle) {
      autoTriggered.current = true
      runAudit.mutate(undefined)
    }
  }, [latestQuery.isLoading, latestQuery.isError, latestQuery.error, runAudit])

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldownSeconds === null || cooldownSeconds <= 0) return
    const timer = setInterval(() => {
      setCooldownSeconds((prev) => {
        if (prev === null || prev <= 1) {
          clearInterval(timer)
          return null
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [cooldownSeconds])

  const handleRerun = () => {
    runAudit.mutate(undefined, {
      onError: (err) => {
        if (err instanceof ApiError && err.status === 429 && err.retryAfter) {
          setCooldownSeconds(err.retryAfter)
        }
      },
    })
  }

  // Determine what data to show: mutation result, query result, or nothing
  const audit: GeoAuditStoredResponse | undefined = runAudit.data ?? latestQuery.data

  // Loading: initial query loading
  if (latestQuery.isLoading) {
    return <LoadingState message="Loading..." />
  }

  // Running audit (auto-triggered or manual re-run)
  if (runAudit.isPending) {
    return <LoadingState message="Running GEO audit on your brand domain..." />
  }

  // Error from auto-trigger (non-429)
  if (!audit && runAudit.isError) {
    const err = runAudit.error
    if (err instanceof ApiError && err.status === 400) {
      return (
        <ErrorState message="No brand domain configured. Please set up your brand in Settings to run a GEO audit." />
      )
    }
    if (err instanceof ApiError && err.status === 422) {
      return (
        <ErrorState
          message="Could not fetch the URL. Please check it is accessible."
          onRetry={handleRerun}
        />
      )
    }
    return <ErrorState message={err.message} onRetry={handleRerun} />
  }

  // No audit data at all (shouldn't normally happen given auto-trigger)
  if (!audit) {
    return <LoadingState message="Preparing audit..." />
  }

  // Show results
  const result = audit.result
  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <ScoreHeader
        audit={audit}
        onRerun={handleRerun}
        isRerunning={runAudit.isPending}
        cooldownSeconds={cooldownSeconds}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ExtractionCard extraction={result.extraction} />
        <ValidationCard validation={result.validation} />
        <RichResultsCard richResults={result.rich_results} />
        <GeoReadinessCard geoReadiness={result.geo_readiness} />
      </div>

      <TemplatesCard templates={result.recommended_templates} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DeprecatedSchemasCard deprecatedSchemas={result.deprecated_schemas} />
        <JsWarningsCard warnings={result.js_rendering_warnings} />
      </div>

      <ScoreBreakdownCard breakdown={result.score.breakdown} />
    </div>
  )
}

function LoadingState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-gray-500">
      <div className="w-8 h-8 border-2 border-gray-300 border-t-[#C4553D] rounded-full animate-spin mb-4" />
      <p className="text-sm">{message}</p>
    </div>
  )
}

function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="text-center py-16">
      <p className="text-sm text-red-600 mb-3">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-sm text-[#C4553D] hover:underline"
        >
          Try again
        </button>
      )}
    </div>
  )
}
