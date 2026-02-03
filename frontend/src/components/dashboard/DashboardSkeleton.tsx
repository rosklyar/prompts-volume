/**
 * DashboardSkeleton - Loading skeleton for dashboard components
 */

export function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Brand Visibility Card Skeleton */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6]">
        <div className="h-4 w-32 bg-gray-100 rounded animate-pulse mb-6" />
        <div className="flex justify-center">
          <div className="w-40 h-40 rounded-full bg-gray-100 animate-pulse" />
        </div>
        <div className="h-4 w-24 bg-gray-100 rounded animate-pulse mx-auto mt-4" />
      </div>

      {/* Competitors Skeleton */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6]">
        <div className="h-4 w-28 bg-gray-100 rounded animate-pulse mb-6" />
        <div className="space-y-3">
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
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6]">
        <div className="h-4 w-24 bg-gray-100 rounded animate-pulse mb-6" />
        <div className="space-y-3">
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
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-[#F3F4F6]">
        <div className="h-4 w-28 bg-gray-100 rounded animate-pulse mb-6" />
        <div className="space-y-3">
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
