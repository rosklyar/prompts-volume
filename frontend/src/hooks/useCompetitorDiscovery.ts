import { useMutation } from "@tanstack/react-query"
import { onboardingApi } from "@/client/api"
import type { DiscoverCompetitorsRequest, DiscoverCompetitorsResponse } from "@/types/onboarding"

export function useDiscoverCompetitors() {
  return useMutation<DiscoverCompetitorsResponse, Error, DiscoverCompetitorsRequest>({
    mutationFn: (request) => onboardingApi.discoverCompetitors(request),
  })
}
