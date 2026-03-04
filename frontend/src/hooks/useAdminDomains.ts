/**
 * React Query hooks for admin business domain management
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { adminApi } from "@/client/api"
import type {
  CreateAdminBusinessDomainRequest,
  UpdateAdminBusinessDomainRequest,
} from "@/types/admin"

const domainKeys = {
  all: ["admin", "business-domains"] as const,
  list: () => [...domainKeys.all, "list"] as const,
}

export function useAdminBusinessDomains() {
  return useQuery({
    queryKey: domainKeys.list(),
    queryFn: () => adminApi.listBusinessDomains(),
    staleTime: 30 * 1000,
  })
}

export function useCreateAdminBusinessDomain() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: CreateAdminBusinessDomainRequest) =>
      adminApi.createBusinessDomain(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: domainKeys.all })
    },
  })
}

export function useUpdateAdminBusinessDomain() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      domainId,
      request,
    }: {
      domainId: number
      request: UpdateAdminBusinessDomainRequest
    }) => adminApi.updateBusinessDomain(domainId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: domainKeys.all })
    },
  })
}

export function useDeactivateAdminBusinessDomain() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (domainId: number) => adminApi.deactivateBusinessDomain(domainId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: domainKeys.all })
    },
  })
}
