/**
 * React Query hooks for admin user management
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { adminApi } from "@/client/api"
import type { AdminTopUpRequest } from "@/types/admin"

export const adminKeys = {
  all: ["admin"] as const,
  users: (search?: string) => [...adminKeys.all, "users", search] as const,
}

/**
 * Fetch users with balances for admin dashboard
 */
export function useAdminUsers(
  search?: string,
  limit: number = 20,
  offset: number = 0
) {
  return useQuery({
    queryKey: adminKeys.users(search),
    queryFn: () => adminApi.getUsers(search, limit, offset),
    staleTime: 30 * 1000, // 30 seconds
  })
}

/**
 * Admin top-up mutation
 */
export function useAdminTopUp() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      userId,
      request,
    }: {
      userId: string
      request: AdminTopUpRequest
    }) => adminApi.topUpUser(userId, request),
    onSuccess: () => {
      // Invalidate user list to refresh balances
      queryClient.invalidateQueries({ queryKey: adminKeys.all })
    },
  })
}
