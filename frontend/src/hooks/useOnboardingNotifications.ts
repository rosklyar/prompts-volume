/**
 * React Query hooks for admin onboarding notifications
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { adminApi } from "@/client/api"

export const onboardingKeys = {
  all: ["admin", "onboarding"] as const,
  list: (limit: number, offset: number) =>
    [...onboardingKeys.all, "list", { limit, offset }] as const,
  count: [...["admin", "onboarding"], "count"] as const,
}

/**
 * Fetch onboarding users awaiting admin setup
 */
export function useOnboardingNotifications(limit: number = 20, offset: number = 0) {
  return useQuery({
    queryKey: onboardingKeys.list(limit, offset),
    queryFn: () => adminApi.getOnboardingNotifications(limit, offset),
    staleTime: 30 * 1000,
  })
}

/**
 * Lightweight count for badge — polls every 60s
 */
export function useOnboardingBadgeCount() {
  return useQuery({
    queryKey: onboardingKeys.count,
    queryFn: () => adminApi.getOnboardingNotificationsCount(),
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
    refetchOnWindowFocus: true,
  })
}

/**
 * Mark user setup as complete
 */
export function useMarkUserSetup() {
  const queryClient = useQueryClient()

  return useMutation<{ message: string }, Error, string>({
    mutationFn: (userId) => adminApi.markUserSetupComplete(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.all })
    },
  })
}
