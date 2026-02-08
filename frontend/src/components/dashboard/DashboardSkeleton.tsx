/**
 * DashboardSkeleton - Loading skeleton for dashboard components
 */

export function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 lg:grid-rows-2 gap-6 flex-1 min-h-0" style={{ height: "calc(100vh - 280px)" }}>
      {/* Brand Visibility Card Skeleton */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full flex flex-col">
        <div className="h-4 w-32 bg-gray-100 rounded animate-pulse mb-6 shrink-0" />
        <div className="flex-1 flex items-center justify-center">
          <div className="w-40 h-40 rounded-full bg-gray-100 animate-pulse" />
        </div>
        <div className="h-4 w-24 bg-gray-100 rounded animate-pulse mx-auto mt-4 shrink-0" />
      </div>

      {/* Competitors Skeleton */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full flex flex-col">
        <div className="h-4 w-28 bg-gray-100 rounded animate-pulse mb-6 shrink-0" />
        <div className="space-y-3 flex-1 overflow-hidden">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="w-6 h-6 rounded-full bg-gray-100 animate-pulse" />
              <div className="flex-1 h-4 bg-gray-100 rounded animate-pulse" />
              <div className="w-12 h-4 bg-gray-100 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>

      {/* Sources Skeleton */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full flex flex-col">
        <div className="h-4 w-24 bg-gray-100 rounded animate-pulse mb-6 shrink-0" />
        <div className="space-y-3 flex-1 overflow-hidden">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="w-4 h-4 bg-gray-100 rounded animate-pulse" />
              <div className="flex-1 h-4 bg-gray-100 rounded animate-pulse" />
              <div className="w-16 h-4 bg-gray-100 rounded animate-pulse" />
            </div>
          ))}
        </div>
      </div>

      {/* Prompt Gaps Skeleton */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6] h-full flex flex-col">
        <div className="h-4 w-28 bg-gray-100 rounded animate-pulse mb-6 shrink-0" />
        <div className="space-y-3 flex-1 overflow-hidden">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="p-3 bg-gray-50 rounded-lg border-l-2 border-gray-200"
            >
              <div className="h-4 bg-gray-100 rounded animate-pulse" />
              <div className="h-3 w-3/4 bg-gray-100 rounded animate-pulse mt-2" />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
