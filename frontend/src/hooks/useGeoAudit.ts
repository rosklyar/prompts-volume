import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { geoAuditApi } from "@/client/api"
import { isLoggedIn } from "./useAuth"
import type { GeoAuditStoredResponse } from "@/types/geo-audit"

const geoAuditKeys = {
  all: ["geoAudit"] as const,
  latest: () => [...geoAuditKeys.all, "latest"] as const,
}

export function useLatestGeoAudit() {
  return useQuery<GeoAuditStoredResponse, Error>({
    queryKey: geoAuditKeys.latest(),
    queryFn: geoAuditApi.getLatest,
    enabled: isLoggedIn(),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useRunGeoAudit() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (url?: string) => geoAuditApi.runAudit(url),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: geoAuditKeys.all })
    },
  })
}
