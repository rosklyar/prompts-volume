/**
 * React Query hooks for Billing/Credits management
 * Provides balance queries, report preview/generation, and top-up mutations
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { billingApi, reportsApi } from "@/client/api"
import type { GenerateReportRequest, TopUpRequest } from "@/types/billing"
import { reportKeys } from "./useReports"

// ===== Query Keys =====

export const billingKeys = {
  all: ["billing"] as const,
  balance: () => [...billingKeys.all, "balance"] as const,
  transactions: () => [...billingKeys.all, "transactions"] as const,
  generationPrice: () => [...billingKeys.all, "generation-price"] as const,
  reportPreview: (groupId: number) =>
    [...billingKeys.all, "preview", groupId] as const,
}

// ===== Queries =====

/**
 * Fetch user balance - refreshes on mount and when balance changes
 */
export function useBalance() {
  return useQuery({
    queryKey: billingKeys.balance(),
    queryFn: () => billingApi.getBalance(),
    staleTime: 30 * 1000, // 30 seconds - balance can change frequently
    refetchOnWindowFocus: true,
  })
}

/**
 * Fetch report preview for a specific group
 * Shows cost breakdown before generating
 */
export function useReportPreview(groupId: number, enabled: boolean = true) {
  return useQuery({
    queryKey: billingKeys.reportPreview(groupId),
    queryFn: () => reportsApi.getPreview(groupId),
    enabled: enabled && groupId > 0,
    staleTime: 60 * 1000, // 1 minute
  })
}

/**
 * Fetch transaction history
 */
export function useTransactions(limit: number = 20, offset: number = 0) {
  return useQuery({
    queryKey: [...billingKeys.transactions(), limit, offset],
    queryFn: () => billingApi.getTransactions(limit, offset),
    staleTime: 60 * 1000, // 1 minute
  })
}

/**
 * Fetch generation price - for confirmation dialog before generating prompts
 */
export function useGenerationPrice(enabled: boolean = true) {
  return useQuery({
    queryKey: billingKeys.generationPrice(),
    queryFn: () => billingApi.getGenerationPrice(),
    enabled,
    staleTime: 30 * 1000, // 30 seconds
  })
}

// ===== Mutations =====

/**
 * Top up balance mutation
 */
export function useTopUp() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: TopUpRequest) => billingApi.topUp(request),
    onSuccess: () => {
      // Invalidate balance query to refetch new balance
      queryClient.invalidateQueries({ queryKey: billingKeys.balance() })
      // Invalidate transactions to show the new top-up
      queryClient.invalidateQueries({ queryKey: billingKeys.transactions() })
    },
  })
}

/**
 * Generate report mutation - charges for fresh evaluations
 */
export function useGenerateReport() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      groupId,
      request,
    }: {
      groupId: number
      request?: GenerateReportRequest
    }) => reportsApi.generate(groupId, request),
    onSuccess: (_, { groupId }) => {
      // Refetch balance (report may have been charged)
      queryClient.refetchQueries({ queryKey: billingKeys.balance() })
      // Refetch preview for this group (fresh counts changed)
      queryClient.refetchQueries({
        queryKey: billingKeys.reportPreview(groupId),
      })
      // Refetch transactions
      queryClient.refetchQueries({ queryKey: billingKeys.transactions() })
      // Refetch report history to show new report immediately
      queryClient.refetchQueries({
        queryKey: reportKeys.history(groupId),
      })
      // Refetch comparison to update fresh data status
      queryClient.refetchQueries({
        queryKey: reportKeys.compare(groupId),
      })
    },
  })
}

// ===== Helper Hooks =====

/**
 * Check if user can afford a given cost
 */
export function useCanAfford(cost: number): boolean {
  const { data: balance } = useBalance()
  if (!balance) return false
  return balance.available_balance >= cost
}

/**
 * Format currency for display
 * Handles both number and string inputs (API may return strings for decimals)
 */
export function formatCredits(amount: number | string | undefined | null): string {
  if (amount === undefined || amount === null) return "0.00"
  const numAmount = typeof amount === "string" ? parseFloat(amount) : amount
  if (isNaN(numAmount)) return "0.00"
  return numAmount.toFixed(2)
}

/**
 * Format relative time for expiration
 */
export function formatExpirationTime(expiresAt: string | null): string | null {
  if (!expiresAt) return null

  const now = new Date()
  const expiry = new Date(expiresAt)
  const diffMs = expiry.getTime() - now.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays <= 0) return "today"
  if (diffDays === 1) return "tomorrow"
  if (diffDays <= 7) return `in ${diffDays} days`
  if (diffDays <= 30) {
    const weeks = Math.floor(diffDays / 7)
    return `in ${weeks} week${weeks > 1 ? "s" : ""}`
  }
  return expiry.toLocaleDateString()
}
