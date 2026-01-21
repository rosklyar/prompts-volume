import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { onboardingApi } from "@/client/api"
import type {
  OnboardingStatusResponse,
  UserPreferencesResponse,
  CompleteOnboardingRequest,
  SavePreferencesRequest,
} from "@/types/onboarding"
import { isLoggedIn } from "./useAuth"

export function useOnboardingStatus() {
  return useQuery<OnboardingStatusResponse, Error>({
    queryKey: ["onboardingStatus"],
    queryFn: onboardingApi.getStatus,
    enabled: isLoggedIn(),
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useUserPreferences() {
  return useQuery<UserPreferencesResponse, Error>({
    queryKey: ["userPreferences"],
    queryFn: onboardingApi.getPreferences,
    enabled: isLoggedIn(),
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useCompleteOnboarding() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CompleteOnboardingRequest) => onboardingApi.complete(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["onboardingStatus"] })
      queryClient.invalidateQueries({ queryKey: ["userPreferences"] })
    },
  })
}

export function useUpdatePreferences() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: SavePreferencesRequest) => onboardingApi.updatePreferences(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userPreferences"] })
    },
  })
}

/**
 * Check if user needs to complete onboarding
 * Returns true if user hasn't completed onboarding
 */
export function needsOnboarding(status: OnboardingStatusResponse | undefined): boolean {
  if (!status) return false
  return !status.is_completed
}
