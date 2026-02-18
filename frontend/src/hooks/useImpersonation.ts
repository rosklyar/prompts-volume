/**
 * Impersonation utilities for admin users.
 *
 * When impersonating, the admin's real token is saved to `admin_token`
 * and the impersonation token replaces `access_token`.
 *
 * Uses useSyncExternalStore so the root-layout banner re-renders
 * when localStorage changes within the same tab.
 */

import { useCallback, useSyncExternalStore } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { adminApi } from "@/client/api"

const ADMIN_TOKEN_KEY = "admin_token"
const IMPERSONATED_EMAIL_KEY = "impersonated_email"

// --- Tiny reactive store around two localStorage keys ---

type Listener = () => void
let listeners: Listener[] = []

function emitChange() {
  listeners.forEach((l) => l())
}

function subscribe(listener: Listener) {
  listeners = [...listeners, listener]
  return () => {
    listeners = listeners.filter((l) => l !== listener)
  }
}

function getIsImpersonating() {
  return localStorage.getItem(ADMIN_TOKEN_KEY) !== null
}

function getEmail() {
  return localStorage.getItem(IMPERSONATED_EMAIL_KEY)
}

// Exported for non-hook contexts (route guards, etc.)
export const isImpersonating = getIsImpersonating

export function useImpersonation() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const active = useSyncExternalStore(subscribe, getIsImpersonating)
  const impersonatedEmail = useSyncExternalStore(subscribe, getEmail)

  const startImpersonation = useCallback(
    async (userId: string, userEmail: string) => {
      const currentToken = localStorage.getItem("access_token")
      if (!currentToken) throw new Error("No active session")

      const { access_token } = await adminApi.impersonateUser(userId)

      localStorage.setItem(ADMIN_TOKEN_KEY, currentToken)
      localStorage.setItem(IMPERSONATED_EMAIL_KEY, userEmail)
      localStorage.setItem("access_token", access_token)

      emitChange()
      queryClient.clear()
      navigate({ to: "/" })
    },
    [queryClient, navigate]
  )

  const exitImpersonation = useCallback(() => {
    const adminToken = localStorage.getItem(ADMIN_TOKEN_KEY)
    if (!adminToken) return

    localStorage.setItem("access_token", adminToken)
    localStorage.removeItem(ADMIN_TOKEN_KEY)
    localStorage.removeItem(IMPERSONATED_EMAIL_KEY)

    emitChange()
    queryClient.clear()
    navigate({ to: "/admin" })
  }, [queryClient, navigate])

  return {
    isImpersonating: active,
    impersonatedEmail,
    startImpersonation,
    exitImpersonation,
  }
}
