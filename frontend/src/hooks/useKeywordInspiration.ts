import { useMutation } from "@tanstack/react-query"
import { keywordInspirationApi } from "@/client/api"
import type {
  DiscoverClustersRequest,
  GeneratePromptsRequest,
  ConfirmGroupsRequest,
} from "@/types/keyword-inspiration"

export function useDiscoverClusters() {
  return useMutation({
    mutationFn: (request: DiscoverClustersRequest) =>
      keywordInspirationApi.discoverClusters(request),
  })
}

export function useGeneratePrompts() {
  return useMutation({
    mutationFn: (request: GeneratePromptsRequest) =>
      keywordInspirationApi.generatePrompts(request),
  })
}

export function useCreateInspirationGroups() {
  return useMutation({
    mutationFn: (request: ConfirmGroupsRequest) =>
      keywordInspirationApi.createGroups(request),
  })
}
