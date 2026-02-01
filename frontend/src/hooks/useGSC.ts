import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  gscApi,
  type GSCConnectionStatus,
  type GSCSearchAnalyticsResponse,
  type GSCPropertyMatchResponse,
  type GSCKeywordExtractResponse,
  type GSCCreatePromptsResponse,
} from "@/client/api"
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

export function useGSCConnect(redirectUri?: string) {
  return useMutation({
    mutationFn: async () => {
      const response = await gscApi.initiateAuth(redirectUri)
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

// ===== GSC Onboarding Hooks =====

export function useGSCMatchProperty(brandDomain: string | null, enabled: boolean = true) {
  return useQuery<GSCPropertyMatchResponse, Error>({
    queryKey: ["gscMatchProperty", brandDomain],
    queryFn: () => gscApi.matchProperty({ brand_domain: brandDomain! }),
    enabled: isLoggedIn() && brandDomain !== null && enabled,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useGSCExtractKeywords(
  siteUrl: string | null,
  options?: {
    minWordCount?: number
    resultLimit?: number
    generatePrompts?: boolean
    countryId?: number
    businessDomain?: string
  },
  enabled: boolean = true
) {
  return useQuery<GSCKeywordExtractResponse, Error>({
    queryKey: [
      "gscExtractKeywords",
      siteUrl,
      options?.minWordCount,
      options?.resultLimit,
      options?.generatePrompts,
      options?.countryId,
      options?.businessDomain,
    ],
    queryFn: () =>
      gscApi.extractKeywords({
        site_url: siteUrl!,
        min_word_count: options?.minWordCount ?? 3,
        result_limit: options?.resultLimit ?? 10,
        generate_prompts: options?.generatePrompts,
        country_id: options?.countryId,
        business_domain: options?.businessDomain,
      }),
    enabled: isLoggedIn() && siteUrl !== null && enabled,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useGSCCreatePrompts() {
  const queryClient = useQueryClient()

  return useMutation<
    GSCCreatePromptsResponse,
    Error,
    {
      prompts: string[]
      groupTitle: string
      countryId: number
      brand: { name: string; domain?: string | null; variations: string[] }
      competitors?: { name: string; domain?: string | null; variations: string[] }[] | null
    }
  >({
    mutationFn: ({ prompts, groupTitle, countryId, brand, competitors }) =>
      gscApi.createPromptsFromGSC({
        prompts,
        group_title: groupTitle,
        country_id: countryId,
        brand,
        competitors,
      }),
    onSuccess: () => {
      // Invalidate groups list so the new group appears
      queryClient.invalidateQueries({ queryKey: ["groups"] })
    },
  })
}
