import { useState, useEffect } from "react"
import { useSearch } from "@tanstack/react-router"
import { ExternalLink, Link2, Link2Off, Globe, CheckCircle2, XCircle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useGSCStatus, useGSCConnect, useGSCDisconnect } from "@/hooks/useGSC"
import { GSCSearchKeysPanel } from "./GSCSearchKeysPanel"

const ACCENT_COLOR = "#C4553D"

interface GSCConnectionContentProps {
  searchParams?: { gsc?: string; reason?: string }
}

/**
 * GSC connection content without Card wrapper - for use in tabs
 */
export function GSCConnectionContent({ searchParams }: GSCConnectionContentProps) {
  const { data: status, isLoading, refetch } = useGSCStatus()
  const connectMutation = useGSCConnect()
  const disconnectMutation = useGSCDisconnect()
  const routeSearchParams = useSearch({ from: "/settings" })

  // Use passed searchParams or fall back to route search params
  const params = searchParams ?? routeSearchParams

  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null)

  // Handle OAuth callback query params - compute initial feedback from URL
  const getInitialFeedback = () => {
    const gscParam = params.gsc as string | undefined
    if (gscParam === "connected") {
      return { type: "success" as const, message: "Google Search Console connected successfully!" }
    } else if (gscParam === "error") {
      const reason = params.reason as string | undefined
      let message = "Failed to connect Google Search Console."
      if (reason === "invalid_state") {
        message = "Connection expired. Please try again."
      } else if (reason === "token_exchange_failed") {
        message = "Authorization failed. Please try again."
      } else if (reason === "no_refresh_token") {
        message = "Unable to get long-term access. Please try again."
      }
      return { type: "error" as const, message }
    }
    return null
  }

  // Process callback params once on mount
  useEffect(() => {
    const initialFeedback = getInitialFeedback()
    if (initialFeedback) {
      setFeedback(initialFeedback)
      if (initialFeedback.type === "success") {
        refetch()
      }
      // Clear the query param
      window.history.replaceState({}, "", "/settings")
    }
    // Only run once on mount - params is read synchronously
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Clear feedback after 5 seconds
  useEffect(() => {
    if (feedback) {
      const timer = setTimeout(() => setFeedback(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [feedback])

  const handleConnect = () => {
    setFeedback(null)
    connectMutation.mutate()
  }

  const handleDisconnect = () => {
    disconnectMutation.mutate(undefined, {
      onSuccess: () => {
        setFeedback({ type: "success", message: "Google Search Console disconnected." })
      },
      onError: (error) => {
        setFeedback({ type: "error", message: error.message || "Failed to disconnect" })
      },
    })
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  const getPermissionLabel = (level: string) => {
    switch (level) {
      case "siteOwner":
        return "Owner"
      case "siteFullUser":
        return "Full"
      case "siteRestrictedUser":
        return "Restricted"
      default:
        return level
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        Loading...
      </div>
    )
  }

  return (
    <div className="space-y-4">
        {/* Feedback message */}
        {feedback && (
          <div
            className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
              feedback.type === "success"
                ? "bg-green-50 text-green-700"
                : "bg-red-50 text-red-700"
            }`}
          >
            {feedback.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            ) : (
              <XCircle className="w-4 h-4 flex-shrink-0" />
            )}
            {feedback.message}
          </div>
        )}

        {status?.is_connected ? (
          <>
            {/* Connection status */}
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-100">
              <div className="flex items-center gap-2">
                <Link2 className="w-4 h-4 text-green-600" />
                <span className="text-sm text-green-700 font-medium">Connected</span>
              </div>
              {status.connected_at && (
                <span className="text-xs text-green-600">
                  since {formatDate(status.connected_at)}
                </span>
              )}
            </div>

            {/* Sites list */}
            {status.sites && status.sites.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-widest text-gray-400 font-sans mb-2">
                  Your Properties ({status.sites.length})
                </p>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {status.sites.map((site) => (
                    <div
                      key={site.site_url}
                      className="flex items-center justify-between p-2.5 bg-gray-50 rounded-lg border border-gray-100"
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <Globe className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                        <span className="text-sm text-gray-700 truncate">{site.site_url}</span>
                      </div>
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded flex-shrink-0 ml-2">
                        {getPermissionLabel(site.permission_level)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {status.sites && status.sites.length === 0 && (
              <p className="text-sm text-gray-500 py-2">
                No properties found. Add sites to your Google Search Console first.
              </p>
            )}

            {/* Search Keys Panel */}
            {status.sites && status.sites.length > 0 && (
              <GSCSearchKeysPanel sites={status.sites} />
            )}

            {/* Disconnect button */}
            <Button
              variant="outline"
              onClick={handleDisconnect}
              disabled={disconnectMutation.isPending}
              className="w-full text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300"
            >
              {disconnectMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Disconnecting...
                </>
              ) : (
                <>
                  <Link2Off className="w-4 h-4 mr-2" />
                  Disconnect
                </>
              )}
            </Button>
          </>
        ) : (
          <>
            {/* Not connected */}
            <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
              <Link2Off className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-600">Not connected</span>
            </div>

            <p className="text-sm text-gray-500">
              Connect your Google Search Console to import keyword data and analyze your search
              visibility alongside AI responses.
            </p>

            {/* Connect button */}
            <Button
              onClick={handleConnect}
              disabled={connectMutation.isPending}
              className="w-full"
              style={{ backgroundColor: ACCENT_COLOR }}
            >
              {connectMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Connecting...
                </>
              ) : (
                <>
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Connect Google Search Console
                </>
              )}
            </Button>
          </>
        )}
    </div>
  )
}

/**
 * GSC connection Card wrapper - for standalone use
 */
export function GSCConnectionCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg text-[#1F2937] flex items-center gap-2">
          <Globe className="w-5 h-5 text-gray-400" />
          Google Search Console
        </CardTitle>
        <CardDescription>Connect your GSC to analyze search performance</CardDescription>
      </CardHeader>
      <CardContent>
        <GSCConnectionContent />
      </CardContent>
    </Card>
  )
}
