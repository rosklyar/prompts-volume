/**
 * Admin tab for managing business domains
 */

import { useState } from "react"
import { ChevronDown, ChevronUp, Globe, Plus, Pencil, XCircle } from "lucide-react"
import { useAdminBusinessDomains } from "@/hooks/useAdminDomains"
import { AdminDomainFormModal } from "./AdminDomainFormModal"
import { AdminDomainDeactivateDialog } from "./AdminDomainDeactivateDialog"
import type { AdminBusinessDomain } from "@/types/admin"

type ModalMode = "create" | "edit" | "deactivate" | null

export function AdminDomainsTab() {
  const { data, isLoading } = useAdminBusinessDomains()
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [modalMode, setModalMode] = useState<ModalMode>(null)
  const [selectedDomain, setSelectedDomain] = useState<AdminBusinessDomain | null>(null)

  const handleEdit = (domain: AdminBusinessDomain) => {
    setSelectedDomain(domain)
    setModalMode("edit")
  }

  const handleDeactivate = (domain: AdminBusinessDomain) => {
    setSelectedDomain(domain)
    setModalMode("deactivate")
  }

  const handleCloseModal = () => {
    setModalMode(null)
    setSelectedDomain(null)
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse"
          >
            <div className="flex items-center gap-3">
              <div className="w-16 h-5 bg-gray-200 rounded-full" />
              <div className="w-32 h-5 bg-gray-200 rounded" />
            </div>
            <div className="w-48 h-4 bg-gray-100 rounded mt-2" />
          </div>
        ))}
      </div>
    )
  }

  if (!data?.business_domains.length) {
    return (
      <div>
        <div className="flex justify-end mb-4">
          <button
            onClick={() => setModalMode("create")}
            className="flex items-center gap-2 px-4 py-2.5 bg-[#C4553D] text-white rounded-xl
              font-medium hover:bg-[#B04A35] transition-colors text-sm"
          >
            <Plus className="w-4 h-4" />
            Add Domain
          </button>
        </div>
        <div className="text-center py-12">
          <Globe className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No business domains yet</p>
        </div>

        {modalMode === "create" && (
          <AdminDomainFormModal onClose={handleCloseModal} onSuccess={handleCloseModal} />
        )}
      </div>
    )
  }

  return (
    <div>
      {/* Header with Add button */}
      <div className="flex justify-end mb-4">
        <button
          onClick={() => setModalMode("create")}
          className="flex items-center gap-2 px-4 py-2.5 bg-[#C4553D] text-white rounded-xl
            font-medium hover:bg-[#B04A35] transition-colors text-sm"
        >
          <Plus className="w-4 h-4" />
          Add Domain
        </button>
      </div>

      {/* Domain list */}
      <div className="space-y-3">
        {data.business_domains.map((domain) => {
          const isExpanded = expandedId === domain.id
          return (
            <div
              key={domain.id}
              className="bg-white rounded-xl border border-gray-200 overflow-hidden"
            >
              {/* Header row */}
              <div className="flex items-center px-5 py-4">
                {/* Expand toggle */}
                <button
                  onClick={() => setExpandedId(isExpanded ? null : domain.id)}
                  className="flex-1 flex items-center gap-3 min-w-0 text-left hover:opacity-80 transition-opacity"
                >
                  {domain.is_active ? (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 shrink-0">
                      Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500 shrink-0">
                      Inactive
                    </span>
                  )}
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900 truncate">{domain.name}</p>
                    <p className="text-xs text-gray-400 mt-0.5 truncate">{domain.description}</p>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-gray-400 shrink-0" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
                  )}
                </button>

                {/* Action buttons — always visible */}
                <div className="flex items-center gap-1.5 ml-3 shrink-0">
                  <button
                    onClick={() => handleEdit(domain)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                      border border-blue-200 text-blue-700 hover:bg-blue-50 transition-colors text-xs font-medium"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                    Edit
                  </button>
                  {domain.is_active && (
                    <button
                      onClick={() => handleDeactivate(domain)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                        border border-red-200 text-red-600 hover:bg-red-50 transition-colors text-xs font-medium"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Deactivate
                    </button>
                  )}
                </div>
              </div>

              {/* Expanded details */}
              {isExpanded && (
                <div className="border-t border-gray-100">
                  {domain.system_prompt_template && (
                    <div className="px-5 py-4">
                      <span className="text-xs text-gray-400 block mb-1">System Prompt Template</span>
                      <pre className="bg-gray-50 rounded-xl p-3 text-xs text-gray-700 font-mono whitespace-pre-wrap max-h-32 overflow-y-auto">
                        {domain.system_prompt_template}
                      </pre>
                    </div>
                  )}

                  {!!domain.keyword_filter_config?.length && (
                    <div className="px-5 py-4 border-t border-gray-100">
                      <span className="text-xs text-gray-400 block mb-2">Keyword Filters</span>
                      <div className="flex flex-wrap gap-2">
                        {domain.keyword_filter_config.map((entry, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-2.5 py-1 rounded-full text-xs
                              font-medium bg-blue-50 text-blue-700 border border-blue-100"
                          >
                            {entry.type}{" "}
                            {entry.operator === "gt" && ">"}
                            {entry.operator === "gte" && ">="}
                            {entry.operator === "lt" && "<"}
                            {entry.operator === "lte" && "<="}
                            {entry.operator === "eq" && "="}{" "}
                            {entry.value}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Modals */}
      {modalMode === "create" && (
        <AdminDomainFormModal onClose={handleCloseModal} onSuccess={handleCloseModal} />
      )}
      {modalMode === "edit" && selectedDomain && (
        <AdminDomainFormModal
          domain={selectedDomain}
          onClose={handleCloseModal}
          onSuccess={handleCloseModal}
        />
      )}
      {modalMode === "deactivate" && selectedDomain && (
        <AdminDomainDeactivateDialog
          domain={selectedDomain}
          onClose={handleCloseModal}
          onSuccess={handleCloseModal}
        />
      )}
    </div>
  )
}
