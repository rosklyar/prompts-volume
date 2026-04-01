import { useEffect, useMemo, useRef, useState } from "react"
import { useLatestGeoAudit, useRunGeoAudit, useAuditProgress, useAuditPages } from "@/hooks/useGeoAudit"
import { ApiError } from "@/client/api"
import { ScoreHeader } from "./ScoreHeader"
import { AuditProgressBar } from "./AuditProgressBar"
import { PageListCard } from "./PageListCard"
import { PageDetailView } from "./PageDetailView"
import { TemplatesCard } from "./TemplatesCard"
import { ScoreBreakdownCard } from "./ScoreBreakdownCard"
import type { PageAuditStoredResponse, PageSummary, SiteAuditStoredResponse } from "@/types/geo-audit"

export function GeoAuditView() {
  const latestQuery = useLatestGeoAudit()
  const runAudit = useRunGeoAudit()
  const [cooldownSeconds, setCooldownSeconds] = useState<number | null>(null)
  const [manualAuditId, setManualAuditId] = useState<number | null>(null)
  const [selectedPage, setSelectedPage] = useState<PageAuditStoredResponse | null>(null)
  const autoTriggered = useRef(false)

  // Derive active audit ID from latest query or manual trigger (no setState in effect)
  const activeAuditId = useMemo(() => {
    if (manualAuditId) return manualAuditId
    if (latestQuery.data) {
      const status = latestQuery.data.status
      if (status === "pending" || status === "discovering" || status === "auditing") {
        return latestQuery.data.id
      }
    }
    return null
  }, [manualAuditId, latestQuery.data])

  // Track in-progress audit for polling
  const progressQuery = useAuditProgress(activeAuditId)
  const pagesQuery = useAuditPages(
    activeAuditId && progressQuery.data?.status === "completed" ? activeAuditId : null
  )

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
      runAudit.mutate(undefined, {
        onSuccess: (data) => {
          setManualAuditId(data.id)
        },
      })
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
      onSuccess: (data) => {
        setManualAuditId(data.id)
        setSelectedPage(null)
      },
      onError: (err) => {
        if (err instanceof ApiError && err.status === 429 && err.retryAfter) {
          setCooldownSeconds(err.retryAfter)
        }
      },
    })
  }

  const handlePageClick = (page: PageSummary) => {
    const stored = pagesQuery.data?.find((p) => p.url === page.url)
    if (stored) {
      setSelectedPage(stored)
    }
  }

  // Loading: initial query loading
  if (latestQuery.isLoading) {
    return <LoadingState message="Loading..." />
  }

  // Show progress if audit is running
  if (progressQuery.data && progressQuery.data.status !== "completed" && progressQuery.data.status !== "failed") {
    return (
      <div className="max-w-4xl mx-auto">
        <AuditProgressBar progress={progressQuery.data} />
      </div>
    )
  }

  // Running audit (auto-triggered, before we have an audit ID)
  if (runAudit.isPending) {
    return <LoadingState message="Starting GEO audit on your brand domain..." />
  }

  // Error from auto-trigger (non-429)
  if (!latestQuery.data && runAudit.isError) {
    const err = runAudit.error
    if (err instanceof ApiError && err.status === 400) {
      return (
        <ErrorState message="No brand domain configured. Please set up your brand in Settings to run a GEO audit." />
      )
    }
    return <ErrorState message={err.message} onRetry={handleRerun} />
  }

  // Failed progress
  if (progressQuery.data?.status === "failed") {
    return (
      <div className="max-w-4xl mx-auto space-y-4">
        <AuditProgressBar progress={progressQuery.data} />
        <ErrorState
          message={progressQuery.data.error_message ?? "Audit failed unexpectedly."}
          onRetry={handleRerun}
        />
      </div>
    )
  }

  // No audit data at all
  const audit = latestQuery.data
  if (!audit || audit.status !== "completed" || !audit.result) {
    return <LoadingState message="Preparing audit..." />
  }

  // Page detail drill-down
  if (selectedPage) {
    return (
      <div className="max-w-4xl mx-auto">
        <PageDetailView
          pageUrl={selectedPage.url}
          result={selectedPage.result}
          onBack={() => setSelectedPage(null)}
        />
      </div>
    )
  }

  // Show completed site-level results
  const siteResult = audit.result
  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <SiteScoreHeader
        audit={audit}
        onRerun={handleRerun}
        isRerunning={runAudit.isPending}
        cooldownSeconds={cooldownSeconds}
      />

      <PageListCard pages={siteResult.pages} onPageClick={handlePageClick} />

      <TemplatesCard templates={siteResult.recommended_templates} />

      {siteResult.site_score && (
        <ScoreBreakdownCard breakdown={siteResult.site_score.breakdown} />
      )}
    </div>
  )
}

function SiteScoreHeader({
  audit,
  onRerun,
  isRerunning,
  cooldownSeconds,
}: {
  audit: SiteAuditStoredResponse
  onRerun: () => void
  isRerunning: boolean
  cooldownSeconds: number | null
}) {
  if (!audit.score_total || !audit.score_rating) return null

  return (
    <ScoreHeader
      audit={audit}
      onRerun={onRerun}
      isRerunning={isRerunning}
      cooldownSeconds={cooldownSeconds}
      pageCount={audit.pages_total}
    />
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
