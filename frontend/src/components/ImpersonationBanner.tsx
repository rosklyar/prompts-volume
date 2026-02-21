/**
 * Fixed banner shown when an admin is impersonating a user.
 */

import { useImpersonation } from "@/hooks/useImpersonation"

export function ImpersonationBanner() {
  const { isImpersonating, impersonatedEmail, exitImpersonation } =
    useImpersonation()

  if (!isImpersonating) return null

  return (
    <div className="sticky top-0 z-50 bg-amber-500 text-white px-4 py-2 flex items-center justify-center gap-3 text-sm font-medium shadow-md">
      <span>
        Impersonating: <strong>{impersonatedEmail}</strong>
      </span>
      <button
        onClick={exitImpersonation}
        className="px-3 py-1 bg-white/20 hover:bg-white/30 rounded-md transition-colors text-white font-medium"
      >
        Exit
      </button>
    </div>
  )
}
