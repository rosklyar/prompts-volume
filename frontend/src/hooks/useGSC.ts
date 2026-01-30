import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { gscApi, type GSCConnectionStatus, type GSCSearchAnalyticsResponse } from "@/client/api"
import { isLoggedIn } from "./useAuth"

export function useGSCStatus() {
  return useQuery<GSCConnectionStatus, Error>({
    queryKey: ["gscStatus"],
    queryFn: gscApi.getStatus,
    enabled: isLoggedIn(),
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useGSCConnect() {
  return useMutation({
    mutationFn: async () => {
      const response = await gscApi.initiateAuth()
      // Redirect user to Google OAuth
      window.location.href = response.auth_url
    },
  })
}

export function useGSCDisconnect() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: gscApi.disconnect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["gscStatus"] })
    },
  })
}

export function useGSCSearchAnalytics(
  siteUrl: string | null,
  startDate: string,
  endDate: string,
  rowLimit: number = 100
) {
  return useQuery<GSCSearchAnalyticsResponse, Error>({
    queryKey: ["gscSearchAnalytics", siteUrl, startDate, endDate, rowLimit],
    queryFn: () =>
      gscApi.getSearchAnalytics({
        site_url: siteUrl!,
        start_date: startDate,
        end_date: endDate,
        row_limit: rowLimit,
      }),
    enabled: isLoggedIn() && siteUrl !== null,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
