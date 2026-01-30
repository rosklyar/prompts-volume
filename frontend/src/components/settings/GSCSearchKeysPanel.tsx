import { useState, useMemo } from "react"
import { Search, Loader2, AlertCircle, TrendingUp, MousePointer, Eye, MapPin } from "lucide-react"
import type { GSCSiteInfo } from "@/client/api"
import { useGSCSearchAnalytics } from "@/hooks/useGSC"

interface GSCSearchKeysPanelProps {
  sites: GSCSiteInfo[]
}

function getDefaultDateRange(): { startDate: string; endDate: string } {
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - 28)

  return {
    startDate: startDate.toISOString().split("T")[0],
    endDate: endDate.toISOString().split("T")[0],
  }
}

function formatCTR(ctr: number): string {
  return `${(ctr * 100).toFixed(1)}%`
}

function formatPosition(position: number): string {
  return position.toFixed(1)
}

export function GSCSearchKeysPanel({ sites }: GSCSearchKeysPanelProps) {
  const [selectedSiteUrl, setSelectedSiteUrl] = useState<string | null>(
    sites.length > 0 ? sites[0].site_url : null
  )

  const { startDate, endDate } = useMemo(() => getDefaultDateRange(), [])

  const { data, isLoading, error } = useGSCSearchAnalytics(
    selectedSiteUrl,
    startDate,
    endDate
  )

  const handleSiteChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedSiteUrl(e.target.value || null)
  }

  return (
    <div className="mt-6 pt-6 border-t border-gray-200">
      <div className="flex items-center gap-2 mb-4">
        <Search className="w-4 h-4 text-gray-400" />
        <h3 className="text-sm font-medium text-gray-900">Search Queries</h3>
      </div>

      {/* Property selector */}
      <div className="mb-4">
        <label htmlFor="site-select" className="block text-xs text-gray-500 mb-1">
          Property
        </label>
        <select
          id="site-select"
          value={selectedSiteUrl || ""}
          onChange={handleSiteChange}
          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-gray-200"
        >
          {sites.map((site) => (
            <option key={site.site_url} value={site.site_url}>
              {site.site_url}
            </option>
          ))}
        </select>
      </div>

      {/* Date range display */}
      <div className="mb-4 text-xs text-gray-500">
        Last 28 days ({startDate} to {endDate})
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8 text-gray-400">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading search queries...
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error.message || "Failed to load search queries"}
        </div>
      )}

      {/* Empty state */}
      {data && data.rows.length === 0 && !isLoading && (
        <div className="text-center py-8 text-gray-500 text-sm">
          No search queries found for this period.
        </div>
      )}

      {/* Data table */}
      {data && data.rows.length > 0 && !isLoading && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 px-2 font-medium text-gray-600">
                  <div className="flex items-center gap-1">
                    <Search className="w-3 h-3" />
                    Query
                  </div>
                </th>
                <th className="text-right py-2 px-2 font-medium text-gray-600">
                  <div className="flex items-center justify-end gap-1">
                    <MousePointer className="w-3 h-3" />
                    Clicks
                  </div>
                </th>
                <th className="text-right py-2 px-2 font-medium text-gray-600">
                  <div className="flex items-center justify-end gap-1">
                    <Eye className="w-3 h-3" />
                    Impr.
                  </div>
                </th>
                <th className="text-right py-2 px-2 font-medium text-gray-600">
                  <div className="flex items-center justify-end gap-1">
                    <TrendingUp className="w-3 h-3" />
                    CTR
                  </div>
                </th>
                <th className="text-right py-2 px-2 font-medium text-gray-600">
                  <div className="flex items-center justify-end gap-1">
                    <MapPin className="w-3 h-3" />
                    Pos.
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, index) => (
                <tr
                  key={row.keys[0] || index}
                  className="border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="py-2 px-2 text-gray-900 max-w-[200px] truncate" title={row.keys[0]}>
                    {row.keys[0]}
                  </td>
                  <td className="py-2 px-2 text-right text-gray-700 tabular-nums">
                    {row.clicks.toLocaleString()}
                  </td>
                  <td className="py-2 px-2 text-right text-gray-700 tabular-nums">
                    {row.impressions.toLocaleString()}
                  </td>
                  <td className="py-2 px-2 text-right text-gray-700 tabular-nums">
                    {formatCTR(row.ctr)}
                  </td>
                  <td className="py-2 px-2 text-right text-gray-700 tabular-nums">
                    {formatPosition(row.position)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
