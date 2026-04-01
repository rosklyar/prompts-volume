import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { geoAuditApi } from "@/client/api"
import { isLoggedIn } from "./useAuth"
import type {
  GeoAuditProgressResponse,
  PageAuditStoredResponse,
  SiteAuditStoredResponse,
} from "@/types/geo-audit"

const geoAuditKeys = {
  all: ["geoAudit"] as const,
  latest: () => [...geoAuditKeys.all, "latest"] as const,
  progress: (auditId: number) => [...geoAuditKeys.all, "progress", auditId] as const,
  pages: (auditId: number) => [...geoAuditKeys.all, "pages", auditId] as const,
  page: (auditId: number, pageId: number) => [...geoAuditKeys.all, "page", auditId, pageId] as const,
}

export function useLatestGeoAudit() {
  return useQuery<SiteAuditStoredResponse, Error>({
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

export function useAuditProgress(auditId: number | null) {
  const queryClient = useQueryClient()

  return useQuery<GeoAuditProgressResponse, Error>({
    queryKey: geoAuditKeys.progress(auditId!),
    queryFn: () => geoAuditApi.getProgress(auditId!),
    enabled: auditId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === "completed" || status === "failed") {
        // Refresh latest audit data when done
        queryClient.invalidateQueries({ queryKey: geoAuditKeys.latest() })
        return false
      }
      return 3000
    },
    staleTime: 1000,
  })
}

export function useAuditPages(auditId: number | null) {
  return useQuery<PageAuditStoredResponse[], Error>({
    queryKey: geoAuditKeys.pages(auditId!),
    queryFn: () => geoAuditApi.getPages(auditId!),
    enabled: auditId !== null,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAuditPage(auditId: number | null, pageId: number | null) {
  return useQuery<PageAuditStoredResponse, Error>({
    queryKey: geoAuditKeys.page(auditId!, pageId!),
    queryFn: () => geoAuditApi.getPage(auditId!, pageId!),
    enabled: auditId !== null && pageId !== null,
    staleTime: 5 * 60 * 1000,
  })
}
