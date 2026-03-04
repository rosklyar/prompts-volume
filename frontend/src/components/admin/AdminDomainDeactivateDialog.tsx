/**
 * Confirmation dialog for deactivating a business domain
 */

import { toast } from "sonner"
import { useDeactivateAdminBusinessDomain } from "@/hooks/useAdminDomains"
import type { AdminBusinessDomain } from "@/types/admin"

interface AdminDomainDeactivateDialogProps {
  domain: AdminBusinessDomain
  onClose: () => void
  onSuccess: () => void
}

export function AdminDomainDeactivateDialog({
  domain,
  onClose,
  onSuccess,
}: AdminDomainDeactivateDialogProps) {
  const deactivateMutation = useDeactivateAdminBusinessDomain()

  const handleDeactivate = () => {
    deactivateMutation.mutate(domain.id, {
      onSuccess: () => {
        toast.success("Domain deactivated")
        onSuccess()
        onClose()
      },
    })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div
        className="bg-white rounded-2xl w-full max-w-md shadow-xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Red danger accent bar */}
        <div className="h-1 w-full bg-red-500" />

        <div className="p-6">
          <h2 className="font-['Fraunces'] text-xl font-medium text-gray-900 mb-4">
            Deactivate Domain
          </h2>

          {/* Domain name */}
          <div className="bg-gray-50 rounded-xl p-4 mb-4">
            <p className="font-medium text-gray-900">{domain.name}</p>
            <p className="text-sm text-gray-500 mt-0.5">{domain.description}</p>
          </div>

          {/* Warning */}
          <div className="bg-red-50 rounded-xl p-4 mb-6">
            <ul className="text-sm text-red-700 space-y-1.5">
              <li>Domain will no longer appear for new users</li>
              <li>Existing assignments are unaffected</li>
            </ul>
          </div>

          {/* Error message */}
          {deactivateMutation.isError && (
            <div className="p-3 bg-red-50 rounded-lg border border-red-100 text-red-600 text-sm mb-4">
              {deactivateMutation.error?.message || "Failed to deactivate. Please try again."}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={deactivateMutation.isPending}
              className="flex-1 px-4 py-3 border border-gray-200 rounded-xl
                text-gray-700 font-medium hover:bg-gray-50 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleDeactivate}
              disabled={deactivateMutation.isPending}
              className="flex-1 px-4 py-3 bg-red-600 text-white rounded-xl
                font-medium hover:bg-red-700 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {deactivateMutation.isPending ? "Deactivating..." : "Deactivate Domain"}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
