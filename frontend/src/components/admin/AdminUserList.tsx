/**
 * Searchable user list for admin dashboard
 */

import { useState, useEffect } from "react"
import { useAdminUsers } from "@/hooks/useAdminUsers"
import { AdminUserCard } from "./AdminUserCard"
import type { UserWithBalance } from "@/types/admin"

interface AdminUserListProps {
  onSelectUser: (user: UserWithBalance) => void
}

export function AdminUserList({ onSelectUser }: AdminUserListProps) {
  const [search, setSearch] = useState("")
  const [debouncedSearch, setDebouncedSearch] = useState("")

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(timer)
  }, [search])

  const { data, isLoading, error } = useAdminUsers(
    debouncedSearch || undefined
  )

  return (
    <div className="space-y-4">
      {/* Search input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <svg
            className="w-5 h-5 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by email or name..."
          className="w-full pl-12 pr-4 py-3 bg-white rounded-xl border border-gray-200
            focus:ring-2 focus:ring-[#C4553D]/20 focus:border-[#C4553D]/30
            placeholder:text-gray-400 outline-none transition-all"
        />
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-20 bg-gray-100 rounded-xl animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-50 rounded-xl border border-red-100 text-red-600 text-sm">
          Failed to load users. Please try again.
        </div>
      )}

      {/* User list */}
      {data && (
        <>
          <div className="text-sm text-gray-500">
            {data.total} user{data.total !== 1 ? "s" : ""} found
          </div>
          <div className="grid gap-3">
            {data.users.map((user) => (
              <AdminUserCard
                key={user.id}
                user={user}
                onClick={() => onSelectUser(user)}
              />
            ))}
          </div>
          {data.users.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No users found matching your search.
            </div>
          )}
        </>
      )}
    </div>
  )
}
